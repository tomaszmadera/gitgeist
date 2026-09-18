"""Deterministic color palette generator derived from VisualLatentProfile."""

import colorsys
from gitgeist.schemas.live_state import ColorPalette
from gitgeist.schemas.visual_latent import VisualLatentProfile


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    """Convert HSL values (0.0 to 1.0) to uppercase 6-digit hex string (#RRGGBB)."""
    h_clamped = h % 1.0
    s_clamped = max(0.0, min(1.0, s))
    l_clamped = max(0.0, min(1.0, l))
    r, g, b = colorsys.hls_to_rgb(h_clamped, l_clamped, s_clamped)
    ri = int(round(r * 255.0))
    gi = int(round(g * 255.0))
    bi = int(round(b * 255.0))
    return f"#{ri:02x}{gi:02x}{bi:02x}"


def _hsl_to_rgba(h: float, s: float, l: float, a: float) -> str:
    """Convert HSL values (0.0 to 1.0) and alpha to CSS rgba string."""
    h_clamped = h % 1.0
    s_clamped = max(0.0, min(1.0, s))
    l_clamped = max(0.0, min(1.0, l))
    r, g, b = colorsys.hls_to_rgb(h_clamped, l_clamped, s_clamped)
    ri = int(round(r * 255.0))
    gi = int(round(g * 255.0))
    bi = int(round(b * 255.0))
    a_clamped = max(0.0, min(1.0, a))
    return f"rgba({ri}, {gi}, {bi}, {a_clamped:.2f})"


def generate_palette(profile: VisualLatentProfile) -> ColorPalette:
    """Generate a harmonized CSS color palette deterministically from a VisualLatentProfile."""
    axes = profile.axes
    dominant_mat = profile.materiality.dominant

    # Base hue according to dominant materiality
    if dominant_mat == "crystalline":
        base_hue = 0.55  # ~198 deg: cyan/ice
    elif dominant_mat == "mechanical":
        base_hue = 0.60  # ~216 deg: slate/steel blue
    elif dominant_mat == "organic":
        base_hue = 0.35  # ~126 deg: viridian/emerald
    else:  # ethereal
        base_hue = 0.75  # ~270 deg: violet/mystic purple

    # Tension shifts hue towards higher energy (red/orange/magenta)
    hue_shift = (axes.tension_curvature - 0.5) * 0.25
    primary_hue = (base_hue + hue_shift) % 1.0
    secondary_hue = (primary_hue + 0.08 + axes.fragmentation * 0.1) % 1.0
    # Accent hue follows materiality: cool accents for crystalline/mechanical,
    # warm amber accents for organic; high tension_curvature always warms it.
    if dominant_mat in ("crystalline", "mechanical"):
        accent_hue = (0.50 + 0.08 * axes.contrast) % 1.0
    elif dominant_mat == "organic":
        accent_hue = 0.07  # amber/gold
    else:  # ethereal
        accent_hue = 0.72  # violet
    if axes.tension_curvature > 0.5:
        accent_hue = (0.03 + 0.10 * axes.tension_curvature) % 1.0

    # Saturation governed by contrast, sharpness and materiality
    base_sat = 0.35 + 0.50 * axes.contrast
    if dominant_mat == "mechanical":
        base_sat = max(0.15, base_sat * 0.7)  # muted, metallic
    elif dominant_mat == "organic":
        base_sat = min(0.95, base_sat * 1.1)  # rich vitality

    # Luminosity determines light vs dark palette
    if axes.luminosity < 0.5:
        # Dark theme
        bg_l = 0.03 + 0.12 * axes.luminosity
        fg_l = 0.85 + 0.10 * axes.contrast
        primary_l = 0.50 + 0.15 * axes.luminosity
        secondary_l = 0.40 + 0.10 * axes.luminosity
        accent_l = 0.60 + 0.20 * axes.contrast
    else:
        # Bright/Luminous theme
        bg_l = 0.88 + 0.10 * (axes.luminosity - 0.5) * 2.0
        fg_l = 0.12 - 0.08 * axes.contrast
        primary_l = 0.40 - 0.10 * (axes.luminosity - 0.5)
        secondary_l = 0.50 - 0.10 * (axes.luminosity - 0.5)
        accent_l = 0.35 - 0.15 * axes.contrast

    bg_sat = max(0.05, min(0.30, base_sat * 0.4))
    fg_sat = max(0.05, min(0.20, base_sat * 0.2))

    background = _hsl_to_hex(primary_hue, bg_sat, bg_l)
    foreground = _hsl_to_hex(primary_hue, fg_sat, fg_l)
    primary = _hsl_to_hex(primary_hue, base_sat, primary_l)
    secondary = _hsl_to_hex(secondary_hue, base_sat * 0.85, secondary_l)
    accent = _hsl_to_hex(accent_hue, min(1.0, base_sat * 1.2), accent_l)

    # Aura alpha: lower opacity makes the aura more visible, while ethereal
    # materiality increases its transparency (spec: ethereal => more diffuse/transparent).
    ethereal_weight = profile.materiality.weights.get("ethereal", 0.0)
    aura_alpha = max(0.0, 0.20 + 0.35 * (1.0 - axes.opacity) - 0.25 * ethereal_weight)
    aura = _hsl_to_rgba(accent_hue, base_sat, accent_l, aura_alpha)

    return ColorPalette(
        background=background,
        foreground=foreground,
        primary=primary,
        secondary=secondary,
        accent=accent,
        aura=aura,
    )
