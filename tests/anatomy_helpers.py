"""A hand-built ``AnatomyScene`` for page tests: fixed coordinates, no layout libraries needed.

It covers every mark of the page: one body with two organs and a tendon, cells of all four languages
with every texture case, a test cell, a cell with test edges, superglobals and deprecated calls, an
unblamed cell, dust and a cyst.
"""

from __future__ import annotations

from gitgeist.schemas.anatomy import PhpFacts, PythonFacts, ScriptFacts
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


def _php(namespace: bool, strict: bool, superglobals: int = 0, globals_: int = 0, deprecated: int = 0) -> PhpFacts:
    return PhpFacts(
        language="php",
        namespace=namespace,
        strict_types=strict,
        superglobals=superglobals,
        globals=globals_,
        deprecated_calls=deprecated,
        includes=0,
    )


def make_anatomy_scene(*, caption: bool = True) -> AnatomyScene:
    organ_a = AnatomyOrgan(
        x=-6.5,
        y=0.25,
        r=9.75,
        cells=[
            AnatomyCell(
                path="app/Http/Controller.php", x=-8.0, y=1.5, r=5.5, lines=100, changes=16,
                line_years={2019: 60, 2024: 40}, test=False, edges=3, test_edges=1,
                facts=_php(True, True),
            ),
            AnatomyCell(
                path="legacy/helpers.php", x=-3.25, y=-2.0, r=3.025, lines=30, changes=1,
                line_years={2019: 30}, test=False, edges=1, test_edges=0,
                facts=_php(False, False, superglobals=3, globals_=1, deprecated=2),
            ),
            AnatomyCell(
                path="app/Models/User.php", x=-6.0, y=-4.5, r=2.2, lines=16, changes=4,
                line_years={2019: 10, 2021: 6}, test=False, edges=1, test_edges=0,
                facts=_php(True, False),
            ),
            AnatomyCell(
                path="tests/UserTest.php", x=-10.5, y=-3.0, r=1.65, lines=9, changes=2,
                line_years={2024: 9}, test=True, edges=1, test_edges=0,
                facts=_php(True, False),
            ),
        ],
    )
    organ_b = AnatomyOrgan(
        x=8.0,
        y=-0.25,
        r=7.5,
        cells=[
            AnatomyCell(
                path="web/app.ts", x=9.5, y=1.0, r=3.9, lines=50, changes=9,
                line_years={2021: 20, 2024: 30}, test=False, edges=2, test_edges=0,
                facts=ScriptFacts(language="typescript", typed=True, loose_marks=0),
            ),
            AnatomyCell(
                path="web/legacy.js", x=5.75, y=-3.5, r=2.75, lines=25, changes=0,
                line_years={}, test=False, edges=1, test_edges=0,
                facts=ScriptFacts(language="javascript", typed=False, loose_marks=0),
            ),
            AnatomyCell(
                path="web/lib/math.ts", x=7.0, y=3.75, r=2.2, lines=16, changes=3,
                line_years={2022: 16}, test=False, edges=1, test_edges=0,
                facts=ScriptFacts(language="typescript", typed=True, loose_marks=2),
            ),
            AnatomyCell(
                path="src/pkg/core.py", x=11.0, y=-3.0, r=2.0, lines=13, changes=5,
                line_years={2024: 13}, test=False, edges=1, test_edges=0,
                facts=PythonFacts(language="python", functions=4, annotated_functions=3),
            ),
        ],
    )
    return AnatomyScene(
        schema_version="1",
        representation="anatomy",
        repository_name="sample-repo",
        caption=caption,
        library_versions=AnatomyLibraryVersions(networkx="3.7", numpy="2.5.4", scipy="1.18.1"),
        counts=AnatomyCounts(
            files=11, edges=7, bodies=1, organs_in_largest_body=2, dust=2, cysts=1,
            lines=303, foreign_lines=40, unblamed=1,
        ),
        blame_years=AnatomyBlameYears(first=2019, last=2024),
        bodies=[AnatomyBody(x=0.5, y=0.0, r=17.25, organs=[organ_a, organ_b])],
        tendons=[AnatomyTendon(body=0, source=0, target=1, edges=2, width=1.0986)],
        dust=[
            AnatomyDust(
                path="src/pkg/__init__.py", x=0.3125, y=-0.25, r=1.1, lines=1, changes=1,
                line_years={2019: 1}, test=False, edges=0, test_edges=0,
                facts=PythonFacts(language="python", functions=0, annotated_functions=0),
            ),
            AnatomyDust(
                path="tools/run.js", x=-0.4, y=0.375, r=1.1, lines=3, changes=2,
                line_years={2024: 3}, test=False, edges=0, test_edges=0,
                facts=ScriptFacts(language="javascript", typed=False, loose_marks=0),
            ),
        ],
        cysts=[
            AnatomyCyst(
                key="lib/acme/Acme.php", x=30.0, y=4.0, r=6.5,
                files=[AnatomyCystFile(path="lib/acme/Acme.php", lines=40)],
            )
        ],
        unresolved_references=5,
    )
