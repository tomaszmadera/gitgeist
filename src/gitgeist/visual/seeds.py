"""Independent, labelled seeds for the free choices of a scene."""

from hashlib import sha256


def validate_user_seed(user_seed: int | None) -> None:
    """Reject seeds outside the recorded, signed 63-bit integer domain."""
    if user_seed is not None and (type(user_seed) is not int or not 0 <= user_seed <= 2**63 - 1):
        raise ValueError("user_seed must be an integer from 0 to 2^63 - 1, or None")


def _digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def style_seed(identity: str, user_seed: int | None = None) -> int:
    """Pick a style before deriving the style-dependent effective seed."""
    validate_user_seed(user_seed)
    user = "" if user_seed is None else str(user_seed)
    return int(_digest(f"style:{identity}:{user}")[:16], 16)


def effective_seed(identity: str, user_seed: int | None, style: str) -> int:
    """Derive the 64-bit seed of the chosen style."""
    validate_user_seed(user_seed)
    user = "" if user_seed is None else str(user_seed)
    return int(_digest(f"spec:{identity}:{user}:{style}")[:16], 16)


def sub_seed(effective: int, label: str) -> int:
    """Give each free choice its own stream, independent of other choices."""
    return int(_digest(f"{effective}:{label}"), 16)
