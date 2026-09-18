"""Abstract mode live simulation generator."""

import hashlib
import json
from gitgeist.render.dynamics import generate_dynamics
from gitgeist.render.palette import generate_palette
from gitgeist.schemas.live_state import GeometryParameters, LiveSimulationState
from gitgeist.schemas.visual_latent import VisualLatentProfile


def _compute_deterministic_seed(profile: VisualLatentProfile, salt: str = "abstract") -> int:
    """Derive an integer seed from invariant profile values (never timestamps)."""
    invariant = {
        "axes": profile.axes.model_dump(),
        "materiality": profile.materiality.model_dump(),
        "dominant_features": profile.dominant_features,
        "source_commit": profile.source_commit,
    }
    s = f"{salt}:{json.dumps(invariant, sort_keys=True)}"
    digest = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def generate_abstract_simulation(
    profile: VisualLatentProfile,
    repository_name: str | None = None,
) -> LiveSimulationState:
    """Generate a complete LiveSimulationState for Abstract mode."""
    axes = profile.axes
    palette = generate_palette(profile)
    dynamics = generate_dynamics(profile)
    seed = _compute_deterministic_seed(profile, salt="abstract")

    # Determine symmetry order: 1 (asymmetric) to 8 (high radial symmetry)
    if axes.symmetry > 0.85:
        symmetry_order = 8
    elif axes.symmetry > 0.70:
        symmetry_order = 6
    elif axes.symmetry > 0.50:
        symmetry_order = 4
    elif axes.symmetry > 0.30:
        symmetry_order = 2
    else:
        symmetry_order = 1

    # Geometry parameters
    layer_count = max(1, min(6, int(round(1.0 + axes.layering * 4.0))))
    curvature = round(max(0.0, min(1.0, 1.0 - axes.tension_curvature)), 3)
    organic_ratio = round(max(0.0, min(1.0, 1.0 - axes.biological_vs_mechanical)), 3)

    geometry = GeometryParameters(
        density=round(max(0.05, min(1.0, 0.15 + 0.85 * axes.texture_density)), 3),
        symmetry_order=symmetry_order,
        fragmentation=round(axes.fragmentation, 3),
        sharpness=round(axes.sharpness, 3),
        layer_count=layer_count,
        curvature=curvature,
        organic_ratio=organic_ratio,
    )

    return LiveSimulationState(
        representation_mode="abstract",
        seed=seed,
        palette=palette,
        dynamics=dynamics,
        geometry=geometry,
        dominant_material=profile.materiality.dominant,
        repository_name=repository_name,
    )
