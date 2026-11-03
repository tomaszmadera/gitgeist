"""Python half of the abstract ``orbits`` renderer: HUD conclusions and hover text.

The browser draws only from ``VisualSpec``. Everything it needs that the spec does
not carry (three plain conclusions about the repository and one hover entry per
mass) is computed here from the extracted features (spec O3, O4) by ``render.captions``,
which the character ``creature`` renderer shares.
"""

from gitgeist.render.captions import conclusions, hover_details
from gitgeist.schemas.features import RepositoryFeatures
from gitgeist.schemas.live_state import OrbitsScene
from gitgeist.schemas.visual_spec import VisualSpec


def build_orbits_scene(
    features: RepositoryFeatures,
    spec: VisualSpec,
    *,
    repository_name: str | None = None,
    caption: bool = True,
) -> OrbitsScene:
    """Build the abstract live scene: the VisualSpec plus HUD conclusions and hover details.

    Raises:
        TypeError: If features or spec have the wrong type.
        ValueError: If spec is not an abstract ``orbits`` scene or its masses do not
            match ``features.structure.masses``.
    """
    if not isinstance(features, RepositoryFeatures):
        raise TypeError(f"Expected RepositoryFeatures, got {type(features).__name__}")
    if not isinstance(spec, VisualSpec):
        raise TypeError(f"Expected VisualSpec, got {type(spec).__name__}")
    if spec.representation != "abstract":
        raise ValueError(f"orbits draws the abstract representation, got {spec.representation!r}")
    if spec.style != "orbits":
        raise ValueError(f"orbits draws style 'orbits', got {spec.style!r}")
    if len(spec.masses) != len(features.structure.masses):
        raise ValueError("spec masses do not match features masses")
    return OrbitsScene(
        schema_version="1",
        representation="abstract",
        repository_name=repository_name,
        caption=caption,
        conclusions=conclusions(features, spec) if caption else [],
        hover=hover_details(features, spec) if caption else [],
        spec=spec,
    )
