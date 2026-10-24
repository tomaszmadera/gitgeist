"""Pin seed formulas and the accepted user seed domain."""

from hashlib import sha256

import pytest

from gitgeist.visual.seeds import effective_seed, style_seed, sub_seed

IDENTITY = "0123456789abcdef" * 4


@pytest.mark.parametrize("user", [None, 0, 1, 2**63 - 1])
def test_seed_formulas(user: int | None) -> None:
    text = "" if user is None else str(user)
    assert style_seed(IDENTITY, user) == int(sha256(f"style:{IDENTITY}:{text}".encode()).hexdigest()[:16], 16)
    effective = effective_seed(IDENTITY, user, "orbits")
    assert effective == int(sha256(f"spec:{IDENTITY}:{text}:orbits".encode()).hexdigest()[:16], 16)
    for label in ("layout", "hue", "strands", "cracks"):
        assert sub_seed(effective, label) == int(sha256(f"{effective}:{label}".encode()).hexdigest(), 16)
    assert len({sub_seed(effective, label) for label in ("layout", "hue", "strands", "cracks")}) == 4


@pytest.mark.parametrize("user", [-1, 2**63, 1.5, "random", True])
def test_invalid_user_seed(user) -> None:
    with pytest.raises(ValueError, match="user_seed"):
        style_seed(IDENTITY, user)
    with pytest.raises(ValueError, match="user_seed"):
        effective_seed(IDENTITY, user, "orbits")
