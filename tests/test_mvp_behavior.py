"""Application-level behavior tests for the MVP product test plan (section 29).

Covers product test plan Tests 1, 2, 5 and 6 over the full pipeline:
extract -> emotional state -> visual latent profile -> artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path

from gitgeist import (
    compose_prompt,
    evaluate_emotional_state,
    explain,
    extract_features,
    map_emotional_to_latent,
    render_live,
    render_prompt,
)
from gitgeist.schemas.emotional import EmotionalState
from gitgeist.schemas.visual_latent import VisualLatentProfile

LOW_MEDIUM_BOUNDARY = 0.33
MEDIUM_HIGH_BOUNDARY = 0.66
DIFFERENCE_THRESHOLD = 0.1
MINIMUM_DIFFERING_COUNT = 3
VOLATILE_KEYS = {"calculated_at", "extracted_at", "source_commit", "engine_version"}


def _run_pipeline(repo_path: Path) -> tuple:
    features = extract_features(repo_path)
    state = evaluate_emotional_state(features, source_commit="pipeline-test")
    profile = map_emotional_to_latent(state)
    return features, state, profile


def _strip_volatile(value):
    if isinstance(value, dict):
        return {
            key: _strip_volatile(item)
            for key, item in sorted(value.items())
            if key not in VOLATILE_KEYS
        }
    if isinstance(value, list):
        return [_strip_volatile(item) for item in value]
    return value


def _qualifier(value: float) -> str:
    if value <= LOW_MEDIUM_BOUNDARY:
        return "low"
    if value <= MEDIUM_HIGH_BOUNDARY:
        return "medium"
    return "high"


def _drop_mode_block(prompt: str) -> str:
    lines = prompt.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("Representation mode: "):
            del lines[index : index + 2]
            break
    return "\n".join(lines)


def _parse_prompt_core(prompt: str) -> tuple[dict[str, str], dict[str, str], str]:
    scores: dict[str, str] = {}
    axes: dict[str, str] = {}
    dominant_material = ""
    section = ""
    for line in prompt.splitlines():
        if line == "":
            section = ""
            continue
        if line == "Emotional state:":
            section = "scores"
            continue
        if line == "Visual latent profile:":
            section = "axes"
            continue
        if line.startswith("- dominant material: "):
            dominant_material = line.removeprefix("- dominant material: ")
            continue
        if line.startswith("- ") and section in {"scores", "axes"}:
            name, _, value = line[2:].partition(": ")
            (scores if section == "scores" else axes)[name] = value
    return scores, axes, dominant_material


def test_test1_different_repos_produce_different_profiles(
    clean_modular_repo: Path, legacy_chaotic_repo: Path
) -> None:
    _, clean_state, clean_profile = _run_pipeline(clean_modular_repo)
    _, chaotic_state, chaotic_profile = _run_pipeline(legacy_chaotic_repo)

    clean_scores = clean_state.scores.model_dump()
    chaotic_scores = chaotic_state.scores.model_dump()
    score_diffs = [abs(clean_scores[k] - chaotic_scores[k]) for k in clean_scores]
    assert sum(diff >= DIFFERENCE_THRESHOLD for diff in score_diffs) >= MINIMUM_DIFFERING_COUNT

    clean_axes = clean_profile.axes.model_dump()
    chaotic_axes = chaotic_profile.axes.model_dump()
    axis_diffs = [abs(clean_axes[k] - chaotic_axes[k]) for k in clean_axes]
    assert sum(diff >= DIFFERENCE_THRESHOLD for diff in axis_diffs) >= MINIMUM_DIFFERING_COUNT

    assert clean_profile.materiality.dominant != chaotic_profile.materiality.dominant


def test_test2_same_snapshot_produces_stable_profile(clean_modular_repo: Path) -> None:
    features_a, state_a, profile_a = _run_pipeline(clean_modular_repo)
    features_b, state_b, profile_b = _run_pipeline(clean_modular_repo)

    assert state_a.scores == state_b.scores
    assert state_a.nouls == state_b.nouls
    assert state_a.choices == state_b.choices
    assert profile_a.axes == profile_b.axes
    assert profile_a.materiality == profile_b.materiality
    assert profile_a.dominant_features == profile_b.dominant_features

    artifacts_a = explain(features_a, state_a, profile_a, repository_name="same-repo")
    artifacts_b = explain(features_b, state_b, profile_b, repository_name="same-repo")
    assert artifacts_a.summary_md == artifacts_b.summary_md

    stable_a = _strip_volatile(json.loads(artifacts_a.profile_json))
    stable_b = _strip_volatile(json.loads(artifacts_b.profile_json))
    assert stable_a == stable_b

    live_a = render_live(profile_a, mode="character", repository_name="same-repo")
    live_b = render_live(profile_b, mode="character", repository_name="same-repo")
    assert live_a.state_json == live_b.state_json

    prompt_a = render_prompt(state_a, profile_a, mode="character").prompt_text
    prompt_b = render_prompt(state_b, profile_b, mode="character").prompt_text
    assert prompt_a == prompt_b


def test_test5_representation_modes_share_semantic_identity(
    clean_modular_repo: Path,
) -> None:
    _, state, profile = _run_pipeline(clean_modular_repo)

    live_character = render_live(profile, mode="character", repository_name="identity-repo")
    live_abstract = render_live(profile, mode="abstract", repository_name="identity-repo")
    assert isinstance(live_character.state, type(live_abstract.state))
    assert live_character.state.dominant_material == live_abstract.state.dominant_material
    assert live_character.state_json != live_abstract.state_json

    prompt_character = render_prompt(state, profile, mode="character").prompt_text
    prompt_abstract = render_prompt(state, profile, mode="abstract").prompt_text
    assert prompt_character != prompt_abstract
    assert _drop_mode_block(prompt_character) == _drop_mode_block(prompt_abstract)


def test_test6_live_and_prompt_share_core(clean_modular_repo: Path) -> None:
    _, state, profile = _run_pipeline(clean_modular_repo)
    prompt = compose_prompt(state, profile, mode="character", repository_name="core-repo")
    live = render_live(profile, mode="character", repository_name="core-repo")

    prompt_scores, prompt_axes, prompt_material = _parse_prompt_core(prompt)

    assert prompt_material == profile.materiality.dominant
    assert live.state.dominant_material == profile.materiality.dominant

    for name, qualifier in prompt_scores.items():
        assert _qualifier(getattr(state.scores, name)) == qualifier
    for name, qualifier in prompt_axes.items():
        assert _qualifier(getattr(profile.axes, name)) == qualifier
