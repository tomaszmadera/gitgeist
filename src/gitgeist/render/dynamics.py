"""Motion dynamics generator translating latent axes into animation parameters."""

from gitgeist.schemas.live_state import MotionDynamics
from gitgeist.schemas.visual_latent import VisualLatentProfile


def generate_dynamics(profile: VisualLatentProfile) -> MotionDynamics:
    """Derive simulation physics and motion dynamics from visual latent axes."""
    axes = profile.axes

    # Frequency ranges from 0.2 Hz (slow drift) to 2.2 Hz (rapid rhythmic pulse)
    pulse_freq = round(0.20 + 2.00 * axes.visual_rhythm, 3)

    # Flow drift speed depends on rhythm and tension
    flow_spd = round(0.30 + 1.20 * axes.visual_rhythm + 0.50 * axes.tension_curvature, 3)

    # Turbulence increases with tension and instability (1.0 - compositional_balance)
    turb = round(
        0.05 + 0.65 * axes.tension_curvature + 0.30 * (1.0 - axes.compositional_balance),
        3,
    )

    # Breathing / expansion scale amplitude
    breath_amp = round(
        0.05 + 0.15 * (1.0 - axes.sharpness) + 0.10 * axes.tension_curvature,
        3,
    )

    return MotionDynamics(
        pulse_frequency=pulse_freq,
        flow_speed=flow_spd,
        turbulence=turb,
        breathing_amplitude=breath_amp,
    )
