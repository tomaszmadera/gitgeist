"""Deterministic layout of the anatomy scene: bodies, Louvain organs, cells, tendons, dust and cysts.

See ``docs/features/anatomy-representation/spec.md``, section "Layout". Every coordinate is computed
here; the page only draws. ``networkx`` and ``numpy`` come from the optional extra
``gitgeist[anatomy]`` and are imported only when a scene is built, so the base package imports
without them.

Determinism: graphs are built with integer nodes (the index of the file in the path-sorted scan) and
edges inserted in sorted order, so neither Louvain nor the spring layout depends on string hashing or
dict order. Every list is ordered by size (lines or radius, descending) and then by path. The same scan
and the same ``networkx`` and ``numpy`` versions give a byte-identical scene JSON; the versions are
recorded in the scene.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from typing import Any

from gitgeist.schemas.anatomy import AnatomyFile, AnatomyScan
from gitgeist.schemas.live_state import (
    AnatomyBlameYears,
    AnatomyBody,
    AnatomyCell,
    AnatomyCounts,
    AnatomyCyst,
    AnatomyCystFile,
    AnatomyDust,
    AnatomyLibraryVersions,
    AnatomyOrgan,
    AnatomyScene,
    AnatomyTendon,
)

ANATOMY_EXTRA_HINT = (
    "--representation anatomy requires networkx and numpy; install them with: pip install gitgeist[anatomy]"
)
LAYOUT_SEED = 7
ORGAN_ITERATIONS = 60
CONDENSED_ITERATIONS = 200
ORGAN_SPREAD = 0.8  # cell centres reach this share of the organ radius
ORGAN_GAP = 3.0
BODY_SPAN = 1.2
SEPARATION_ROUNDS = 10_000
PACK_GAP = 6.0
PACK_STEP = 0.15
PACK_RADIAL = 2.2
GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))
CYST_SKIN = 1.1
CYST_SEGMENTS = 3
DUST_INNER = 0.12
DUST_SPAN = 0.36
DECIMALS = 4


class AnatomyExtraMissing(ImportError):
    """``networkx`` or ``numpy`` is not importable; the message carries the install hint."""


def require_layout_libraries() -> tuple[Any, Any]:
    """Import and return ``(networkx, numpy)``.

    Raises:
        AnatomyExtraMissing: If either library cannot be imported.
    """
    try:
        import networkx
        import numpy
    except ImportError as exc:
        raise AnatomyExtraMissing(ANATOMY_EXTRA_HINT) from exc
    return networkx, numpy


def cell_radius(lines: int) -> float:
    """Cell radius in layout units: cell area grows linearly with the line count."""
    return 0.55 * math.sqrt(max(lines, 4))


def organ_radius(cell_radii: list[float]) -> float:
    return 1.15 * math.sqrt(sum(r * r for r in cell_radii)) + 2.0


def dust_position(path: str) -> tuple[float, float]:
    """Frame position of a dust speck, from the SHA-1 of its path only (fractions of the frame side)."""
    digest = int(hashlib.sha1(path.encode("utf-8")).hexdigest(), 16)
    angle = (digest % 3600) / 3600 * 2.0 * math.pi
    distance = DUST_INNER + DUST_SPAN * ((digest >> 12) % 1000) / 1000
    return _q(distance * math.cos(angle)), _q(distance * math.sin(angle))


def _q(value: float) -> float:
    """Round a coordinate for a compact, stable JSON; ``+ 0.0`` turns ``-0.0`` into ``0.0``."""
    return round(float(value), DECIMALS) + 0.0


def _graph(nx: Any, nodes: list[int], edges: list[tuple[int, int, int]]) -> Any:
    graph = nx.Graph()
    graph.add_nodes_from(nodes)
    graph.add_weighted_edges_from(edges)
    return graph


def _layout_organ(
    nx: Any, np: Any, nodes: list[int], edges: list[tuple[int, int, int]], radii: list[float]
) -> tuple[dict[int, tuple[float, float]], float]:
    """Cell offsets from the organ centre (spring layout scaled to the organ radius) and the radius."""
    radius = organ_radius([radii[node] for node in nodes])
    if len(nodes) == 1:
        return {nodes[0]: (0.0, 0.0)}, radius
    positions = nx.spring_layout(_graph(nx, nodes, edges), seed=LAYOUT_SEED, iterations=ORGAN_ITERATIONS)
    points = np.array([positions[node] for node in nodes], dtype=float)
    points -= points.mean(axis=0)
    scale = float(np.abs(points).max()) or 1.0
    points = points / scale * radius * ORGAN_SPREAD
    return {node: (float(points[i, 0]), float(points[i, 1])) for i, node in enumerate(nodes)}, radius


def _place_organs(nx: Any, np: Any, radii: list[float], cross: dict[tuple[int, int], int]) -> list[list[float]]:
    """Organ centres inside a body: condensed spring layout, then pairwise separation, then centring."""
    if len(radii) == 1:
        return [[0.0, 0.0]]
    count = len(radii)
    condensed = _graph(nx, list(range(count)), [(a, b, w) for (a, b), w in sorted(cross.items())])
    positions = nx.spring_layout(condensed, seed=LAYOUT_SEED, weight="weight", iterations=CONDENSED_ITERATIONS)
    span = math.sqrt(sum(r * r for r in radii)) * BODY_SPAN
    centres = [[float(positions[i][0]) * span, float(positions[i][1]) * span] for i in range(count)]
    for _ in range(SEPARATION_ROUNDS):
        moved = False
        for i in range(count):
            for j in range(i + 1, count):
                dx = centres[j][0] - centres[i][0]
                dy = centres[j][1] - centres[i][1]
                distance = math.hypot(dx, dy)
                need = radii[i] + radii[j] + ORGAN_GAP
                if distance < need:
                    ux, uy = (dx / distance, dy / distance) if distance > 0 else (1.0, 0.0)
                    push = (need - distance) / 2
                    centres[i][0] -= ux * push
                    centres[i][1] -= uy * push
                    centres[j][0] += ux * push
                    centres[j][1] += uy * push
                    moved = True
        if not moved:
            break
    else:
        raise RuntimeError(f"organ separation did not converge in {SEPARATION_ROUNDS} rounds ({count} organs)")
    mean_x = sum(c[0] for c in centres) / count
    mean_y = sum(c[1] for c in centres) / count
    return [[c[0] - mean_x, c[1] - mean_y] for c in centres]


def _pack(np: Any, radii: list[float]) -> list[tuple[float, float]]:
    """Place circles in the given order: the first at the origin, each next one on a golden-angle spiral
    around it at the first free spot."""
    if not radii:
        return []
    anchor = radii[0]
    centres = np.zeros((len(radii), 2))
    placed = np.array([anchor])
    for index in range(1, len(radii)):
        radius = radii[index]
        step = 0
        while True:
            t = step * PACK_STEP
            rho = anchor + radius + PACK_GAP + PACK_RADIAL * t
            candidate = np.array([rho * math.cos(t * GOLDEN_ANGLE), rho * math.sin(t * GOLDEN_ANGLE)])
            gaps = np.hypot(*(centres[:index] - candidate).T) - (placed + radius + PACK_GAP)
            if bool((gaps >= 0).all()):
                break
            step += 1
        centres[index] = candidate
        placed = np.append(placed, radius)
    return [(float(x), float(y)) for x, y in centres]


def _state(file: AnatomyFile, degree: int, test_edges: int) -> dict[str, Any]:
    return {
        "path": file.path,
        "r": _q(cell_radius(file.lines)),
        "lines": file.lines,
        "changes": file.changes,
        "line_years": file.line_years,
        "test": file.test,
        "edges": degree,
        "test_edges": test_edges,
        "facts": file.facts,
    }


def build_anatomy_scene(
    scan: AnatomyScan, *, repository_name: str | None = None, caption: bool = True
) -> AnatomyScene:
    """Lay out ``scan`` as an ``AnatomyScene``.

    Raises:
        TypeError: If scan is not an ``AnatomyScan``.
        AnatomyExtraMissing: If ``networkx`` or ``numpy`` is not importable.
    """
    if not isinstance(scan, AnatomyScan):
        raise TypeError(f"Expected AnatomyScan, got {type(scan).__name__}")
    nx, np = require_layout_libraries()

    files = scan.files  # sorted by path, so index order is path order
    index = {file.path: i for i, file in enumerate(files)}
    radii = [cell_radius(file.lines) for file in files]
    degree = [0] * len(files)
    test_edges = [0] * len(files)
    own_edges: list[tuple[int, int, int]] = []
    for edge in scan.edges:
        a, b = index[edge.source], index[edge.target]
        degree[a] += 1
        degree[b] += 1
        test_edges[a] += files[b].test
        test_edges[b] += files[a].test
        if not files[a].foreign and not files[b].foreign:
            own_edges.append((a, b, edge.weight))

    def lines_of(nodes: list[int]) -> int:
        return sum(files[node].lines for node in nodes)

    def by_size(nodes: list[int]) -> tuple[int, int]:
        return (-lines_of(nodes), nodes[0])

    own = [i for i, file in enumerate(files) if not file.foreign]
    components = sorted((sorted(c) for c in nx.connected_components(_graph(nx, own, own_edges))), key=by_size)
    groups = [c for c in components if len(c) >= 2]
    dust_nodes = [c[0] for c in components if len(c) == 1]

    component_of = {node: k for k, nodes in enumerate(groups) for node in nodes}
    group_edges: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
    for a, b, w in own_edges:
        if a in component_of:
            group_edges[component_of[a]].append((a, b, w))

    laid_out = []  # per body: organs as (nodes, centre, radius, offsets), cross counts, extent
    for k, nodes in enumerate(groups):
        edges = group_edges[k]
        communities = nx.community.louvain_communities(_graph(nx, nodes, edges), seed=LAYOUT_SEED)
        organs = sorted((sorted(c) for c in communities), key=by_size)
        owner = {node: o for o, members in enumerate(organs) for node in members}
        inner: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
        cross: Counter[tuple[int, int]] = Counter()
        for a, b, w in edges:
            oa, ob = owner[a], owner[b]
            if oa == ob:
                inner[oa].append((a, b, w))
            else:
                cross[(min(oa, ob), max(oa, ob))] += 1
        shapes = [_layout_organ(nx, np, members, inner[o], radii) for o, members in enumerate(organs)]
        centres = _place_organs(nx, np, [radius for _, radius in shapes], cross)
        extent = 0.0
        for (offsets, radius), centre in zip(shapes, centres):
            extent = max(extent, math.hypot(*centre) + radius)
            for node, (ox, oy) in offsets.items():
                extent = max(extent, math.hypot(centre[0] + ox, centre[1] + oy) + radii[node])
        laid_out.append((organs, shapes, centres, cross, extent))

    cyst_members: dict[str, list[int]] = defaultdict(list)
    for i, file in enumerate(files):
        if file.foreign:
            cyst_members["/".join(file.path.split("/")[:CYST_SEGMENTS])].append(i)
    cyst_keys = sorted(cyst_members, key=lambda key: (-lines_of(cyst_members[key]), key))
    cyst_radii = [
        CYST_SKIN * math.sqrt(sum(radii[node] ** 2 for node in cyst_members[key])) + 2.0 for key in cyst_keys
    ]

    # Packing order: the largest body (bodies[0]) at the origin, then bodies and cysts by radius
    # descending and then by path (first path of a body, key of a cyst).
    items = [(extent, files[groups[k][0]].path, "body", k) for k, (*_, extent) in enumerate(laid_out)]
    items += [(radius, key, "cyst", k) for k, (key, radius) in enumerate(zip(cyst_keys, cyst_radii))]
    if items:
        first = items[0]
        items = [first] + sorted(items[1:], key=lambda item: (-item[0], item[1]))
    where = dict(zip(((kind, k) for _, _, kind, k in items), _pack(np, [item[0] for item in items])))

    bodies: list[AnatomyBody] = []
    tendons: list[AnatomyTendon] = []
    for k, (organs, shapes, centres, cross, extent) in enumerate(laid_out):
        bx, by = where[("body", k)]
        organ_models = []
        for members, (offsets, radius), centre in zip(organs, shapes, centres):
            ox, oy = bx + centre[0], by + centre[1]
            cells = [
                AnatomyCell(
                    x=_q(ox + offsets[node][0]),
                    y=_q(oy + offsets[node][1]),
                    **_state(files[node], degree[node], test_edges[node]),
                )
                for node in sorted(members, key=lambda node: (-files[node].lines, node))
            ]
            organ_models.append(AnatomyOrgan(x=_q(ox), y=_q(oy), r=_q(radius), cells=cells))
        bodies.append(AnatomyBody(x=_q(bx), y=_q(by), r=_q(extent), organs=organ_models))
        for (a, b), count in sorted(cross.items()):
            tendons.append(AnatomyTendon(body=k, source=a, target=b, edges=count, width=_q(math.log1p(count))))

    dust = []
    for node in dust_nodes:
        x, y = dust_position(files[node].path)
        dust.append(AnatomyDust(x=x, y=y, **_state(files[node], degree[node], test_edges[node])))

    cysts = []
    for k, (key, radius) in enumerate(zip(cyst_keys, cyst_radii)):
        cx, cy = where[("cyst", k)]
        members = sorted(cyst_members[key], key=lambda node: (-files[node].lines, node))
        cysts.append(
            AnatomyCyst(
                key=key,
                x=_q(cx),
                y=_q(cy),
                r=_q(radius),
                files=[AnatomyCystFile(path=files[node].path, lines=files[node].lines) for node in members],
            )
        )

    years = sorted({year for file in files for year in file.line_years})
    return AnatomyScene(
        schema_version="1",
        representation="anatomy",
        repository_name=repository_name,
        caption=caption,
        library_versions=AnatomyLibraryVersions(networkx=nx.__version__, numpy=np.__version__),
        counts=AnatomyCounts(
            files=len(files),
            edges=len(scan.edges),
            bodies=len(bodies),
            organs_in_largest_body=len(bodies[0].organs) if bodies else 0,
            dust=len(dust),
            cysts=len(cysts),
            lines=sum(file.lines for file in files),
            foreign_lines=sum(file.lines for file in files if file.foreign),
            unblamed=scan.unblamed,
        ),
        blame_years=AnatomyBlameYears(first=years[0], last=years[-1]) if years else None,
        bodies=bodies,
        tendons=tendons,
        dust=dust,
        cysts=cysts,
        unresolved_references=scan.unresolved_references,
    )
