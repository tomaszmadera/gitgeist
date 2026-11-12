"""Anatomy layout and scene: partition, determinism, dust stability, ordering ties and the scene schema.

These tests need the ``anatomy`` extra (``networkx`` and ``numpy``); without it they fail with the
install hint instead of being skipped.
"""

from __future__ import annotations

import itertools
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from gitgeist.ingest.anatomy import scan_anatomy
from gitgeist.render import anatomy as layout
from gitgeist.render.anatomy import (
    ANATOMY_EXTRA_HINT,
    AnatomyExtraMissing,
    build_anatomy_scene,
    cell_radius,
    dust_position,
)
from gitgeist.schemas.anatomy import AnatomyEdge, AnatomyFile, AnatomyScan, PythonFacts
from gitgeist.schemas.live_state import AnatomyScene
from tests.fixtures.builder import create_anatomy_repo

SRC = Path(__file__).resolve().parents[1] / "src"


def _file(path: str, lines: int = 10, *, foreign: bool = False, test: bool = False, years: dict[int, int] | None = None) -> AnatomyFile:
    return AnatomyFile(
        path=path,
        lines=lines,
        test=test,
        foreign=foreign,
        changes=1,
        line_years=years if years is not None else {2020: lines},
        unblamed=False,
        facts=PythonFacts(language="python", functions=0, annotated_functions=0),
    )


def _scan(files: list[AnatomyFile], edges: list[tuple[str, str, int]] = ()) -> AnatomyScan:
    return AnatomyScan(
        files=sorted(files, key=lambda f: f.path),
        edges=[AnatomyEdge(source=min(a, b), target=max(a, b), weight=w) for a, b, w in sorted(edges)],
        unresolved_references=0,
        unblamed=0,
    )


def _clique(prefix: str, size: int, lines: int = 20) -> tuple[list[AnatomyFile], list[tuple[str, str, int]]]:
    files = [_file(f"{prefix}/m{i:02d}.py", lines + i) for i in range(size)]
    edges = [(a.path, b.path, 1) for a, b in itertools.combinations(files, 2)]
    return files, edges


def _rich_scan() -> AnatomyScan:
    """Two dense communities joined by one bridge, a second body, dust, a test file and foreign files."""
    a_files, a_edges = _clique("pkg/a", 6)
    b_files, b_edges = _clique("pkg/b", 5, lines=40)
    c_files, c_edges = _clique("other", 3)
    files = a_files + b_files + c_files + [
        _file("tests/test_a.py", 12, test=True),
        _file("loose/one.py", 7),
        _file("loose/two.py", 300),
        _file("third_party/lib/x/core.py", 50, foreign=True),
        _file("third_party/lib/x/util.py", 5, foreign=True),
        _file("third_party/lib/y.py", 9, foreign=True),
    ]
    edges = a_edges + b_edges + c_edges + [
        ("pkg/a/m00.py", "pkg/b/m00.py", 1),
        ("pkg/a/m01.py", "tests/test_a.py", 2),
        ("loose/one.py", "third_party/lib/y.py", 1),
    ]
    return _scan(files, edges)


def _cells(scene: AnatomyScene) -> list:
    return [cell for body in scene.bodies for organ in body.organs for cell in organ.cells]


def _dump(scene: AnatomyScene) -> str:
    return scene.model_dump_json(indent=2)


@pytest.fixture(scope="module")
def fixture_scene(tmp_path_factory: pytest.TempPathFactory) -> AnatomyScene:
    return build_anatomy_scene(scan_anatomy(create_anatomy_repo(tmp_path_factory.mktemp("anatomy") / "repo")))


def test_fixture_partition_matches_the_expected_bodies_organs_dust_and_cysts(fixture_scene: AnatomyScene) -> None:
    assert [[[c.path for c in o.cells] for o in b.organs] for b in fixture_scene.bodies] == [
        [["app/Http/Controller.php", "legacy/helpers.php", "app/Models/User.php"]],
        [["src/pkg/cli.py", "src/pkg/core.py", "tests/test_core.py"]],
        [["web/app.ts", "web/lib/math.ts"], ["web/legacy.js", "web/lib/format.ts"]],
    ]
    assert [d.path for d in fixture_scene.dust] == [
        "legacy/latin.php",
        "app/license_check.php",
        "src/pkg/blob.py",
        "src/pkg/__init__.py",
    ]
    assert [(c.key, [f.path for f in c.files]) for c in fixture_scene.cysts] == [
        ("lib/acme/Acme.php", ["lib/acme/Acme.php"]),
        ("generated/schema.js", ["generated/schema.js"]),
        ("web/dist/app.min.js", ["web/dist/app.min.js"]),
    ]
    assert [(t.body, t.source, t.target, t.edges) for t in fixture_scene.tendons] == [(2, 0, 1, 1)]
    counts = fixture_scene.counts
    assert (counts.files, counts.edges, counts.bodies, counts.dust, counts.cysts) == (17, 8, 3, 4, 3)
    assert (counts.organs_in_largest_body, counts.unblamed) == (1, 1)
    assert (fixture_scene.blame_years.first, fixture_scene.blame_years.last) == (2019, 2024)
    assert fixture_scene.unresolved_references > 0


def test_every_own_file_is_once_in_an_organ_or_dust_and_foreign_files_only_in_cysts() -> None:
    scan = _rich_scan()
    scene = build_anatomy_scene(scan)
    organ_paths = [c.path for c in _cells(scene)]
    dust_paths = [d.path for d in scene.dust]
    cyst_paths = [f.path for c in scene.cysts for f in c.files]
    own = sorted(f.path for f in scan.files if not f.foreign)
    foreign = sorted(f.path for f in scan.files if f.foreign)
    assert sorted(organ_paths + dust_paths) == own
    assert len(organ_paths) + len(dust_paths) == len(own)
    assert sorted(cyst_paths) == foreign
    # loose/one.py depends only on a foreign file: among own files it is unconnected, so it is dust.
    assert dust_paths == ["loose/two.py", "loose/one.py"]
    one = next(d for d in scene.dust if d.path == "loose/one.py")
    assert one.edges == 1


def test_louvain_splits_two_dense_communities_and_a_tendon_counts_the_bridge() -> None:
    scene = build_anatomy_scene(_rich_scan())
    largest = scene.bodies[0]
    organ_sets = [{c.path.rsplit("/", 1)[0] for c in o.cells} for o in largest.organs]
    assert organ_sets == [{"pkg/a", "tests"}, {"pkg/b"}] or organ_sets == [{"pkg/b"}, {"pkg/a", "tests"}]
    tendon = next(t for t in scene.tendons if t.body == 0)
    assert tendon.edges == 1
    assert tendon.width == pytest.approx(math.log1p(1), abs=1e-4)


def test_cell_facts_radius_and_test_edges() -> None:
    scene = build_anatomy_scene(_rich_scan())
    cells = {c.path: c for c in _cells(scene)}
    assert cells["pkg/a/m01.py"].test_edges == 1
    assert cells["pkg/a/m01.py"].edges == 6
    assert cells["tests/test_a.py"].test and cells["tests/test_a.py"].test_edges == 0
    assert cells["pkg/b/m03.py"].r == pytest.approx(cell_radius(43), abs=1e-4)
    assert cell_radius(1) == cell_radius(4) == pytest.approx(1.1)


def test_organs_in_a_body_and_packed_bodies_and_cysts_do_not_overlap() -> None:
    scene = build_anatomy_scene(_rich_scan())
    for body in scene.bodies:
        for a, b in itertools.combinations(body.organs, 2):
            assert math.hypot(a.x - b.x, a.y - b.y) >= a.r + b.r + layout.ORGAN_GAP - 1e-3
    circles = [(b.x, b.y, b.r) for b in scene.bodies] + [(c.x, c.y, c.r) for c in scene.cysts]
    for (ax, ay, ar), (bx, by, br) in itertools.combinations(circles, 2):
        assert math.hypot(ax - bx, ay - by) >= ar + br + layout.PACK_GAP - 1e-3
    assert (scene.bodies[0].x, scene.bodies[0].y) == (0.0, 0.0)


def test_scene_json_is_byte_identical_across_runs_and_hash_seeds(tmp_path: Path) -> None:
    scan = _rich_scan()
    assert _dump(build_anatomy_scene(scan)) == _dump(build_anatomy_scene(scan))
    scan_path = tmp_path / "scan.json"
    scan_path.write_text(scan.model_dump_json(), encoding="utf-8")
    code = (
        "import sys; from pathlib import Path; from gitgeist.schemas.anatomy import AnatomyScan; "
        "from gitgeist.render.anatomy import build_anatomy_scene; "
        "scan = AnatomyScan.model_validate_json(Path(sys.argv[1]).read_text(encoding='utf-8')); "
        "sys.stdout.write(build_anatomy_scene(scan).model_dump_json(indent=2))"
    )
    outputs = []
    for hash_seed in ("0", "12345"):
        env = {**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": str(SRC)}
        result = subprocess.run(
            [sys.executable, "-c", code, str(scan_path)], env=env, capture_output=True, text=True, check=True
        )
        outputs.append(result.stdout)
    assert outputs[0] == outputs[1] == _dump(build_anatomy_scene(scan))


def test_fixture_scene_is_byte_identical_for_two_scans(tmp_path: Path, fixture_scene: AnatomyScene) -> None:
    again = build_anatomy_scene(scan_anatomy(create_anatomy_repo(tmp_path / "repo")))
    assert _dump(again) == _dump(fixture_scene)


def test_dust_positions_depend_only_on_the_path() -> None:
    before = build_anatomy_scene(_rich_scan())
    changed_files = [
        _file(f.path, f.lines + 90, foreign=f.foreign, test=f.test) if f.path == "pkg/a/m03.py" else f
        for f in _rich_scan().files
    ] + [_file("loose/three.py", 4), _file("pkg/b/m99.py", 30)]
    changed_edges = [(e.source, e.target, e.weight) for e in _rich_scan().edges] + [("pkg/b/m00.py", "pkg/b/m99.py", 1)]
    after = build_anatomy_scene(_scan(changed_files, changed_edges))
    positions_before = {d.path: (d.x, d.y) for d in before.dust}
    positions_after = {d.path: (d.x, d.y) for d in after.dust}
    assert set(positions_after) == set(positions_before) | {"loose/three.py"}
    for path, position in positions_before.items():
        assert positions_after[path] == position == dust_position(path)
    for x, y in positions_after.values():
        assert 0.1 <= math.hypot(x, y) < 0.5


def test_equal_sizes_are_ordered_by_path() -> None:
    files = [
        _file("z/a.py", 10), _file("z/b.py", 10),
        _file("a/a.py", 10), _file("a/b.py", 10),
        _file("big/a.py", 10), _file("big/b.py", 11),
        _file("dust/y.py", 5), _file("dust/x.py", 5), _file("dust/w.py", 6),
        _file("f1/q/r/s.py", 8, foreign=True), _file("f0/q/r/s.py", 8, foreign=True),
    ]
    edges = [("z/a.py", "z/b.py", 1), ("a/a.py", "a/b.py", 1), ("big/a.py", "big/b.py", 1)]
    scene = build_anatomy_scene(_scan(files, edges))
    assert [b.organs[0].cells[0].path for b in scene.bodies] == ["big/b.py", "a/a.py", "z/a.py"]
    assert [c.path for c in scene.bodies[1].organs[0].cells] == ["a/a.py", "a/b.py"]
    assert [d.path for d in scene.dust] == ["dust/w.py", "dust/x.py", "dust/y.py"]
    assert [c.key for c in scene.cysts] == ["f0/q/r", "f1/q/r"]


def test_cysts_group_foreign_files_by_their_first_three_path_segments() -> None:
    files = [
        _file("ext/lib/a/one.js", 30, foreign=True),
        _file("ext/lib/a/two.js", 40, foreign=True),
        _file("ext/lib/b.js", 5, foreign=True),
    ]
    scene = build_anatomy_scene(_scan(files))
    assert [(c.key, [f.path for f in c.files]) for c in scene.cysts] == [
        ("ext/lib/a", ["ext/lib/a/two.js", "ext/lib/a/one.js"]),
        ("ext/lib/b.js", ["ext/lib/b.js"]),
    ]


def test_empty_repository_gives_an_empty_scene() -> None:
    scene = build_anatomy_scene(_scan([]))
    assert (scene.bodies, scene.tendons, scene.dust, scene.cysts) == ([], [], [], [])
    assert scene.blame_years is None
    assert scene.counts.model_dump() == {
        "files": 0, "edges": 0, "bodies": 0, "organs_in_largest_body": 0, "dust": 0,
        "cysts": 0, "lines": 0, "foreign_lines": 0, "unblamed": 0,
    }


def test_foreign_only_repository_gives_cysts_only() -> None:
    files = [_file("lib/a/b/x.js", 20, foreign=True), _file("lib/c/d/y.js", 10, foreign=True)]
    scene = build_anatomy_scene(_scan(files, [("lib/a/b/x.js", "lib/c/d/y.js", 1)]))
    assert (scene.bodies, scene.tendons, scene.dust) == ([], [], [])
    assert [c.key for c in scene.cysts] == ["lib/a/b", "lib/c/d"]
    assert (scene.cysts[0].x, scene.cysts[0].y) == (0.0, 0.0)
    assert (scene.counts.lines, scene.counts.foreign_lines, scene.counts.edges) == (30, 30, 1)


def test_scene_records_installed_library_versions_and_its_inputs() -> None:
    import networkx
    import numpy

    scene = build_anatomy_scene(_rich_scan(), repository_name="demo", caption=False)
    assert scene.library_versions.model_dump() == {"networkx": networkx.__version__, "numpy": numpy.__version__}
    assert (scene.repository_name, scene.caption, scene.representation) == ("demo", False, "anatomy")


def test_scene_roundtrips_through_json_and_forbids_extra_fields() -> None:
    scene = build_anatomy_scene(_rich_scan())
    assert AnatomyScene.model_validate_json(scene.model_dump_json()) == scene
    data = json.loads(_dump(scene))
    assert AnatomyScene.model_validate(data) == scene
    with pytest.raises(ValidationError):
        AnatomyScene.model_validate({**data, "score": 1})
    with pytest.raises(ValidationError):
        scene.caption = False  # type: ignore[misc]
    organ = data["bodies"][0]["organs"][0]
    organ["cells"][0]["verdict"] = "bad"
    with pytest.raises(ValidationError):
        AnatomyScene.model_validate(data)


def test_scene_rejects_a_file_drawn_twice_or_miscounted() -> None:
    data = json.loads(_dump(build_anatomy_scene(_rich_scan())))
    duplicated = json.loads(json.dumps(data))
    duplicated["dust"].append({**duplicated["dust"][0]})
    duplicated["counts"]["dust"] += 1
    duplicated["counts"]["files"] += 1
    with pytest.raises(ValidationError, match="exactly once"):
        AnatomyScene.model_validate(duplicated)
    miscounted = json.loads(json.dumps(data))
    miscounted["counts"]["bodies"] += 1
    with pytest.raises(ValidationError, match="counts.bodies"):
        AnatomyScene.model_validate(miscounted)
    bad_tendon = json.loads(json.dumps(data))
    bad_tendon["tendons"][0]["target"] = 99
    with pytest.raises(ValidationError, match="tendon"):
        AnatomyScene.model_validate(bad_tendon)


def test_missing_extra_raises_the_install_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "networkx", None)
    with pytest.raises(AnatomyExtraMissing, match=r"pip install gitgeist\[anatomy\]"):
        build_anatomy_scene(_scan([]))
    assert "networkx and numpy" in ANATOMY_EXTRA_HINT


def test_base_package_imports_without_networkx_and_numpy() -> None:
    code = (
        "import sys; sys.modules['networkx'] = None; sys.modules['numpy'] = None; "
        "import gitgeist.cli, gitgeist.render, gitgeist.render.anatomy, gitgeist.schemas.live_state"
    )
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    subprocess.run([sys.executable, "-c", code], env=env, check=True)
