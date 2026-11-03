"""Python half of the character ``creature`` renderer: the body plan, HUD conclusions and hover text.

The browser draws only from the scene. The body plan (torso, limbs, segments, posture) is a pure
function of the ``VisualSpec`` computed here, so it can be tested without a browser and reused by
the prompt composer later (stage 5 spec C2). Constants are those of stage 5 spec C11.
"""

import math
from random import Random

from gitgeist.render.captions import conclusions, hover_details
from gitgeist.schemas.features import RepositoryFeatures
from gitgeist.schemas.live_state import (
    CreatureBody,
    CreatureLimb,
    CreatureScene,
    CreatureSegment,
    CreatureTorso,
)
from gitgeist.schemas.visual_spec import VisualSpec
from gitgeist.visual.seeds import sub_seed

BODY_LABEL = "body"
TORSO_ROTATION_DEG = 270.0  # upright: the major axis is vertical, the head is at the top
TORSO_ELONGATION = 1.2
PAD_MIN_RATIO = 0.12
PAD_RATIO_SCALE = 0.8
REACH_BASE = 0.8
REACH_CHURN = 1.6
STALK_MIN = 0.35  # a limb is at least its pad radius plus this share of R long
HALF_WIDTH_ROOT = 0.5
HALF_WIDTH_TIP = 0.3
SINGLE_PAIR_POSITION = 0.3
PAIR_POSITION_RANGE = 0.85
PAIR_SWEEP_DEG = 55.0  # pairs near the head reach forward, pairs near the tail reach back
CURL_BASE_DEG = 10.0
CURL_SPAN_DEG = 60.0
CURL_TOTAL_CAP_DEG = 100.0
SWAY_BASE_DEG = 2.0
SWAY_SPAN_DEG = 10.0
TENDRIL_LENGTH = 0.12
TENDRIL_SPAN = 0.18
DIGITS = 6


def _pair_positions(pairs: int) -> list[float]:
    if pairs == 1:
        return [SINGLE_PAIR_POSITION]
    step = 2 * PAIR_POSITION_RANGE / (pairs - 1)
    return [PAIR_POSITION_RANGE - step * p for p in range(pairs)]


def _ellipse_radius(rx: float, ry: float, psi: float) -> float:
    return rx * ry / math.hypot(ry * math.cos(psi), rx * math.sin(psi))


def _round(value: float) -> float:
    return round(value, DIGITS) + 0.0  # + 0.0 turns -0.0 into 0.0


def _raw_plan(spec: VisualSpec) -> dict | None:
    """Rest pose in unscaled units: torso, limbs and every (x, y, radius) the fit has to contain."""
    masses = spec.masses
    if not masses:
        return None
    rng = Random(sub_seed(spec.seeds.effective_seed, BODY_LABEL))
    mirror = rng.choice([1, -1])
    torso_index = max(range(len(masses)), key=lambda i: (masses[i].file_share, -i))
    torso_share = masses[torso_index].file_share
    ry = math.sqrt(torso_share) if torso_share > 0 else 1.0
    rx = TORSO_ELONGATION * ry
    beta = math.radians(TORSO_ROTATION_DEG)
    alive = spec.traits.alive
    segments = 1 + spec.topology.nesting_levels
    others = [i for i in range(len(masses)) if i != torso_index]
    positions = _pair_positions((len(others) + 1) // 2) if others else []
    curl = min(CURL_BASE_DEG + CURL_SPAN_DEG * (1 - alive), CURL_TOTAL_CAP_DEG / segments)
    sway = SWAY_BASE_DEG + SWAY_SPAN_DEG * alive
    limbs: list[dict] = []
    contained: list[tuple[float, float, float]] = []
    for k, mass_index in enumerate(others):
        mass = masses[mass_index]
        side = mirror if k % 2 == 0 else -mirror
        u = positions[k // 2]
        ratio = math.sqrt(mass.file_share / torso_share) if torso_share > 0 else 1.0
        pad = ry * max(PAD_MIN_RATIO, PAD_RATIO_SCALE * ratio)
        reach = max(ry * (REACH_BASE + REACH_CHURN * math.sqrt(mass.churn_share)), pad + STALK_MIN * ry)
        lx, ly = u * rx, side * ry * math.sqrt(max(0.0, 1 - u * u))
        root = (lx * math.cos(beta) - ly * math.sin(beta), lx * math.sin(beta) + ly * math.cos(beta))
        angle = TORSO_ROTATION_DEG + side * (90.0 - PAIR_SWEEP_DEG * u)
        bend = side * curl
        phase = rng.random()
        parts = []
        x, y, heading = root[0], root[1], angle
        for j in range(segments):
            half = pad * (HALF_WIDTH_ROOT - (HALF_WIDTH_ROOT - HALF_WIDTH_TIP) * j / max(1, segments - 1))
            parts.append({"length": reach / segments, "half_width": half, "bend_deg": bend})
            heading += bend
            x += reach / segments * math.cos(math.radians(heading))
            y += reach / segments * math.sin(math.radians(heading))
            contained.append((x, y, half))
        contained.append((x, y, pad))
        limbs.append({"mass_index": mass_index, "root": root, "angle": angle, "segments": parts, "pad": pad,
                      "phase": phase, "sway": sway})
    for step in range(72):
        t = step / 72 * 2 * math.pi
        px, py = rx * math.cos(t), ry * math.sin(t)
        contained.append((px * math.cos(beta) - py * math.sin(beta), px * math.sin(beta) + py * math.cos(beta), 0.0))
    return {"torso_index": torso_index, "rx": rx, "ry": ry, "limbs": limbs, "contained": contained}


def _tendril_roots(spec: VisualSpec, rx: float, ry: float) -> list[tuple[float, float, float]]:
    """Root point and length of each tendril: the torso outline at the polar angle ``phase * 360``."""
    beta = math.radians(TORSO_ROTATION_DEG)
    roots = []
    for path in spec.strands.paths:
        psi = path.phase * 2 * math.pi
        radius = _ellipse_radius(rx, ry, psi)
        px, py = radius * math.cos(psi), radius * math.sin(psi)
        roots.append((px * math.cos(beta) - py * math.sin(beta), px * math.sin(beta) + py * math.cos(beta),
                      TENDRIL_LENGTH + TENDRIL_SPAN * abs(path.curvature)))
    return roots


def build_creature_body(spec: VisualSpec) -> CreatureBody:
    """Body plan of the creature: upright torso, limbs in left/right pairs, curl and sway by ``alive``.

    Everything is in footprint units: the rest pose is centred and scaled so that its farthest
    point, and the tip of every tendril, lies inside the unit circle.
    """
    plan = _raw_plan(spec)
    if plan is None:
        return CreatureBody(torso=None, limbs=[])
    contained = plan["contained"]
    x0 = min(x - r for x, y, r in contained)
    x1 = max(x + r for x, y, r in contained)
    y0 = min(y - r for x, y, r in contained)
    y1 = max(y + r for x, y, r in contained)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    scale = 1 / max(math.hypot(x - cx, y - cy) + r for x, y, r in contained)
    for root_x, root_y, length in _tendril_roots(spec, plan["rx"], plan["ry"]):
        distance = math.hypot(root_x - cx, root_y - cy)
        if distance > 1e-12:
            scale = min(scale, (1 - length) / distance)
    torso = CreatureTorso(
        mass_index=plan["torso_index"], x=_round(-cx * scale), y=_round(-cy * scale),
        rx=_round(plan["rx"] * scale), ry=_round(plan["ry"] * scale), rotation_deg=TORSO_ROTATION_DEG,
    )
    limbs = [
        CreatureLimb(
            mass_index=limb["mass_index"], root_x=_round((limb["root"][0] - cx) * scale),
            root_y=_round((limb["root"][1] - cy) * scale), root_angle_deg=_round(limb["angle"]),
            segments=[CreatureSegment(length=_round(s["length"] * scale), half_width=_round(s["half_width"] * scale),
                                      bend_deg=_round(s["bend_deg"])) for s in limb["segments"]],
            pad_radius=_round(limb["pad"] * scale), sway_phase=_round(limb["phase"]) % 1.0,
            sway_amplitude_deg=_round(limb["sway"]),
        )
        for limb in plan["limbs"]
    ]
    return CreatureBody(torso=torso, limbs=limbs)


def rest_pose_extent(body: CreatureBody) -> float:
    """Distance of the farthest point of the rest pose (parts only, no tendrils) from the origin."""
    if body.torso is None:
        return 0.0
    beta = math.radians(body.torso.rotation_deg)
    far = 0.0
    for step in range(72):
        t = step / 72 * 2 * math.pi
        px, py = body.torso.rx * math.cos(t), body.torso.ry * math.sin(t)
        far = max(far, math.hypot(body.torso.x + px * math.cos(beta) - py * math.sin(beta),
                                  body.torso.y + px * math.sin(beta) + py * math.cos(beta)))
    for limb in body.limbs:
        x, y, heading = limb.root_x, limb.root_y, limb.root_angle_deg
        for segment in limb.segments:
            heading += segment.bend_deg
            x += segment.length * math.cos(math.radians(heading))
            y += segment.length * math.sin(math.radians(heading))
            far = max(far, math.hypot(x, y) + segment.half_width)
        far = max(far, math.hypot(x, y) + limb.pad_radius)
    return far


def build_creature_scene(
    features: RepositoryFeatures,
    spec: VisualSpec,
    *,
    repository_name: str | None = None,
    caption: bool = True,
) -> CreatureScene:
    """Build the character live scene: the VisualSpec, the body plan, HUD conclusions and hover details.

    Raises:
        TypeError: If features or spec have the wrong type.
        ValueError: If spec is not a character ``creature`` scene or its masses do not match
            ``features.structure.masses``.
    """
    if not isinstance(features, RepositoryFeatures):
        raise TypeError(f"Expected RepositoryFeatures, got {type(features).__name__}")
    if not isinstance(spec, VisualSpec):
        raise TypeError(f"Expected VisualSpec, got {type(spec).__name__}")
    if spec.representation != "character":
        raise ValueError(f"creature draws the character representation, got {spec.representation!r}")
    if spec.style != "creature":
        raise ValueError(f"creature draws style 'creature', got {spec.style!r}")
    if len(spec.masses) != len(features.structure.masses):
        raise ValueError("spec masses do not match features masses")
    return CreatureScene(
        schema_version="1",
        representation="character",
        repository_name=repository_name,
        caption=caption,
        conclusions=conclusions(features, spec) if caption else [],
        hover=hover_details(features, spec) if caption else [],
        body=build_creature_body(spec),
        spec=spec,
    )
