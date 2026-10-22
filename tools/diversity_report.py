"""Visual diversity report for gitgeist (dev tool, not part of the package).

Runs the gitgeist pipeline on a list of repositories and measures how different
the results are, as in docs/features/visual-diversity/analysis.md:

- per-layer JSON for every repository (features, scores, nouls, choices, axes,
  materiality, live states, prompts),
- how many repositories hit each saturating rule,
- participation ratios (effective number of independent dimensions) of the
  scores and the visual axes,
- prompt line overlap,
- live screenshots taken with headless Chrome at a frozen animation time of
  1.5 s (repeatable), a contact sheet per representation, and the image
  distance D between every pair.

The repositories are only read. No network, image backend or LLM is called.

Usage (from the repository root, with the package importable):

    python tools/diversity_report.py run --out tmp/diversity NAME=PATH [NAME=PATH ...]
    python tools/diversity_report.py run --out tmp/diversity --no-images PATH [PATH ...]
    python tools/diversity_report.py distance --out tmp/mockup NAME=IMAGE [NAME=IMAGE ...]

`run` needs Pillow (the `dev` or `image` extra) and Chrome or Chromium for the
images; pass --chrome when it is not on PATH. `distance` measures existing
images, for example a mockup, with the same D.

Image distance D (version 1):

    each image is resized to 256x256 and blurred (Gaussian, radius 12);
    layout = the blurred image reduced to 8x8 RGB, values in [0, 1];
    hue = 12-bin hue histogram of the saturated pixels (HSV saturation > 0.25
          and value > 0.15) of the unblurred image, normalised to sum 1; all
          zeros when no pixel is saturated;
    D = 0.5 * mean(|layout_a - layout_b|) / 0.25 + 0.5 * sum(|hue_a - hue_b|)

Higher is more different. A portrait set is as diverse as its nearest-neighbour
median: the median, over repositories, of the distance to the closest other
repository.
"""

from __future__ import annotations

import argparse
import colorsys
import inspect
import itertools
import json
import math
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

D_VERSION = 1
SHOT_SIZE = 520
VIRTUAL_TIME_MS = 1500
SNAPSHOT_SECONDS = 1.5
# Injected into a copy of live-preview.html: the first animation frame gets
# timestamp 1 ms and every later frame SNAPSHOT_SECONDS later, so the canvas
# always shows the same moment. Real frame timing in headless Chrome varies
# from run to run and moved D by up to 0.025 between identical runs.
FROZEN_CLOCK = (
    "<script>(function(){var raf=window.requestAnimationFrame.bind(window);var first=true;"
    "window.requestAnimationFrame=function(cb){return raf(function(){"
    f"var t=first?1:{1 + SNAPSHOT_SECONDS * 1000:.0f};first=false;cb(t);}});}};}})();</script>"
)
REPRESENTATIONS = ("abstract", "character")
CHROME_CANDIDATES = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "chrome",
    "msedge",
)


# ---------------------------------------------------------------- statistics


def pearson(xs: list[float], ys: list[float]) -> float:
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy)


def symmetric_eigenvalues(matrix: list[list[float]], sweeps: int = 100) -> list[float]:
    """Eigenvalues of a symmetric matrix (cyclic Jacobi), largest first."""
    a = [row[:] for row in matrix]
    n = len(a)
    for _ in range(sweeps):
        off = sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j)
        if off < 1e-22:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if abs(a[p][q]) < 1e-300:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
                t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p], a[k][q] = c * akp - s * akq, s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k], a[q][k] = c * apk - s * aqk, s * apk + c * aqk
    return sorted((a[i][i] for i in range(n)), reverse=True)


def spread(rows: dict[str, dict[str, float]]) -> dict[str, Any]:
    """Participation ratio and correlated pairs of a set of named variables.

    Constant variables have no correlation and are listed apart.
    """
    names = list(rows)
    keys = list(rows[names[0]])
    columns = {k: [float(rows[n][k]) for n in names] for k in keys}
    constant = [k for k, v in columns.items() if max(v) - min(v) < 1e-12]
    varying = [k for k in keys if k not in constant]
    corr = [[pearson(columns[a], columns[b]) if a != b else 1.0 for b in varying] for a in varying]
    cov = [
        [statistics.fmean(
            (x - statistics.fmean(columns[a])) * (y - statistics.fmean(columns[b]))
            for x, y in zip(columns[a], columns[b])
        ) for b in varying]
        for a in varying
    ]

    def ratio(m: list[list[float]]) -> tuple[float, float]:
        ev = [max(0.0, e) for e in symmetric_eigenvalues(m)]
        total = sum(ev)
        shares = [e / total for e in ev]
        return 1.0 / sum(s * s for s in shares), shares[0]

    pr_corr, first_corr = ratio(corr)
    pr_cov, first_cov = ratio(cov)
    pairs = sorted(
        (
            (varying[i], varying[j], corr[i][j])
            for i in range(len(varying))
            for j in range(i + 1, len(varying))
            if abs(corr[i][j]) > 0.8
        ),
        key=lambda p: -abs(p[2]),
    )
    return {
        "variables": len(keys),
        "constant": constant,
        "participation_ratio": round(pr_corr, 2),
        "first_component": round(first_corr, 3),
        "participation_ratio_covariance": round(pr_cov, 2),
        "first_component_covariance": round(first_cov, 3),
        "pairs_above_0_8": [[a, b, round(r, 3)] for a, b, r in pairs],
        "p90_p10_range": {
            k: round(_quantile(columns[k], 0.9) - _quantile(columns[k], 0.1), 3) for k in keys
        },
    }


def _quantile(values: list[float], q: float) -> float:
    """Linear interpolation quantile (same as numpy's default)."""
    s = sorted(values)
    pos = (len(s) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


# ---------------------------------------------------------------- image distance


def image_features(path: Path) -> tuple[list[float], list[float]]:
    from PIL import Image, ImageFilter

    image = Image.open(path).convert("RGB").resize((256, 256), Image.LANCZOS)
    blurred = image.filter(ImageFilter.GaussianBlur(12)).resize((8, 8), Image.BILINEAR)
    layout = [channel / 255.0 for channel in blurred.tobytes()]
    hue = [0.0] * 12
    data = image.tobytes()
    for i in range(0, len(data), 3):
        h, s, v = colorsys.rgb_to_hsv(data[i] / 255.0, data[i + 1] / 255.0, data[i + 2] / 255.0)
        if s > 0.25 and v > 0.15:
            hue[min(11, int(h * 12))] += 1.0
    total = sum(hue)
    return layout, [c / total for c in hue] if total else hue


def image_distance(a: tuple[list[float], list[float]], b: tuple[list[float], list[float]]) -> float:
    layout = statistics.fmean(abs(x - y) for x, y in zip(a[0], b[0]))
    hue = sum(abs(x - y) for x, y in zip(a[1], b[1]))
    return 0.5 * layout / 0.25 + 0.5 * hue


def distance_summary(features: dict[str, tuple[list[float], list[float]]]) -> dict[str, Any]:
    pairs = {
        (a, b): image_distance(features[a], features[b])
        for a, b in itertools.combinations(features, 2)
    }
    nearest = {}
    for name in features:
        other, d = min(
            ((b if a == name else a, d) for (a, b), d in pairs.items() if name in (a, b)),
            key=lambda item: item[1],
        )
        nearest[name] = {"closest": other, "distance": round(d, 3)}
    closest_pair = min(pairs, key=pairs.get)
    return {
        "d_version": D_VERSION,
        "nearest_neighbour_median": round(statistics.median(v["distance"] for v in nearest.values()), 3),
        "pair_mean": round(statistics.fmean(pairs.values()), 3),
        "closest_pair": [*closest_pair, round(pairs[closest_pair], 3)],
        "nearest": nearest,
        "pairs": {f"{a}|{b}": round(d, 3) for (a, b), d in sorted(pairs.items())},
    }


def contact_sheet(images: dict[str, Path], out: Path, tile: int = 260, columns: int = 6) -> None:
    from PIL import Image, ImageDraw

    rows = (len(images) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * tile, rows * (tile + 22)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (name, path) in enumerate(images.items()):
        x, y = (i % columns) * tile, (i // columns) * (tile + 22)
        sheet.paste(Image.open(path).convert("RGB").resize((tile, tile)), (x, y + 22))
        draw.text((x + 6, y + 4), name, fill="black")
    sheet.save(out, optimize=True)


# ---------------------------------------------------------------- pipeline


def _render_live(profile: Any, mode: str, name: str, repo: Path, output_dir: Path) -> Any:
    """Call render_live with or without the identity seed (added in plan stage 1).

    Keeps the tool usable on commits before stage 1 for baseline runs.
    """
    from gitgeist.render.facade import render_live

    kwargs: dict[str, Any] = {"mode": mode, "repository_name": name, "output_dir": output_dir}
    if "identity" in inspect.signature(render_live).parameters:
        from gitgeist.ingest.identity import compute_identity_seed

        kwargs["identity"] = compute_identity_seed(repo)
    return render_live(profile, **kwargs)


def analyse(name: str, repo: Path, live_dir: Path, source_commit: str) -> dict[str, Any]:
    from gitgeist.features.extractor import extract_features
    from gitgeist.interpretation.emotional_model import evaluate_emotional_state
    from gitgeist.mapping.latent_mapper import map_emotional_to_latent
    from gitgeist.render.prompt_composer import compose_prompt

    features = extract_features(repo)
    state = evaluate_emotional_state(features, source_commit=source_commit)
    profile = map_emotional_to_latent(state)
    live = {}
    for mode in REPRESENTATIONS:
        artifacts = _render_live(profile, mode, name, repo, live_dir / f"{name}-{mode}")
        live[mode] = json.loads(
            artifacts.state.model_dump_json(exclude={"engine_version", "repository_name"})
        )
    return {
        "path": str(repo),
        "features": json.loads(
            features.model_dump_json(exclude={"docs": {"readme_snippet"}, "extracted_at": True})
        ),
        "scores": state.scores.model_dump(),
        "nouls": state.nouls.model_dump(),
        "choices": {k: v.dominant for k, v in state.choices},
        "axes": profile.axes.model_dump(),
        "materiality": profile.materiality.model_dump(),
        "dominant_features": profile.dominant_features,
        "live_abstract": live["abstract"],
        "live_character": live["character"],
        "prompt_abstract": compose_prompt(state, profile, mode="abstract"),
        "prompt_character": compose_prompt(state, profile, mode="character"),
    }


def _qualifier(value: float) -> str:
    return "low" if value <= 0.33 else "medium" if value <= 0.66 else "high"


# Rules from the scoring code that cap or flatten real repositories
# (analysis.md "Saturated inputs"). Each entry: label, predicate on one layer dict.
SATURATION_RULES: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
    ("maturity: age_days >= 180 (sensors/scores.py)", lambda r: r["features"]["history"]["repository_age_days"] >= 180),
    ("maturity: commits >= 30 (sensors/scores.py)", lambda r: r["features"]["history"]["commit_count"] >= 30),
    ("volatility: velocity >= 5/week (sensors/scores.py)", lambda r: r["features"]["history"]["velocity"] >= 5),
    ("novelty: floor 0.25 when age >= 90 and commits >= 10 (sensors/scores.py)",
     lambda r: r["features"]["history"]["is_git_repo"] and r["features"]["history"]["repository_age_days"] >= 90 and r["features"]["history"]["commit_count"] >= 10),
    ("identity: README >= 200 chars (sensors/scores.py)", lambda r: r["features"]["docs"]["readme_length_chars"] >= 200),
    ("identity: commits >= 2 (sensors/scores.py)", lambda r: r["features"]["history"]["commit_count"] >= 2),
    ("visual tone: size >= 50 kB (sensors/choices.py)", lambda r: r["features"]["static"]["total_size_bytes"] >= 50_000),
    ("visual tone: files >= 50 (sensors/choices.py)", lambda r: r["features"]["static"]["file_count"] >= 50),
    ("tension: authors >= 5 (sensors/scores.py)", lambda r: r["features"]["history"]["unique_authors_count"] >= 5),
    ("tension: velocity >= 3/week (sensors/scores.py)", lambda r: r["features"]["history"]["velocity"] >= 3),
    ("conflict: more than 3 languages (sensors/scores.py)", lambda r: len(r["features"]["static"]["languages"]) > 3),
    ("tension_curvature > 0.5 forces a warm accent (render/palette.py)", lambda r: r["axes"]["tension_curvature"] > 0.5),
    ("feels_overloaded is true", lambda r: r["nouls"]["feels_overloaded"]),
    ("identity_strength >= 0.9", lambda r: r["scores"]["identity_strength"] >= 0.9),
    ("luminosity qualifier 'medium'", lambda r: _qualifier(r["axes"]["luminosity"]) == "medium"),
    ("contrast qualifier 'high'", lambda r: _qualifier(r["axes"]["contrast"]) == "high"),
    ("materiality mechanical or crystalline", lambda r: r["materiality"]["dominant"] in ("mechanical", "crystalline")),
    ("character symmetry_order == 2", lambda r: r["live_character"]["geometry"]["symmetry_order"] == 2),
    ("abstract symmetry_order >= 6", lambda r: r["live_abstract"]["geometry"]["symmetry_order"] >= 6),
    ("temperament proud", lambda r: r["choices"]["temperament"] == "proud"),
]


def saturation(layers: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"rule": label, "count": sum(1 for r in layers.values() if rule(r)), "of": len(layers)}
        for label, rule in SATURATION_RULES
    ]


def prompt_overlap(layers: dict[str, dict[str, Any]], mode: str) -> dict[str, Any]:
    prompts = {n: r[f"prompt_{mode}"].splitlines() for n, r in layers.items()}
    lengths = {len(p) for p in prompts.values()}
    shared = set.intersection(*(set(p) for p in prompts.values()))
    shared_lines = sum(1 for line in next(iter(prompts.values())) if line in shared)
    differing = {}
    for a, b in itertools.combinations(prompts, 2):
        pa, pb = prompts[a], prompts[b]
        differing[f"{a}|{b}"] = sum(1 for x, y in itertools.zip_longest(pa, pb) if x != y)
    return {
        "lines_per_prompt": sorted(lengths),
        "lines_identical_for_all": shared_lines,
        "mean_differing_lines": round(statistics.fmean(differing.values()), 1),
        "fewest_differing": sorted(differing.items(), key=lambda kv: kv[1])[:3],
    }


# ---------------------------------------------------------------- screenshots


def find_chrome(explicit: str | None) -> str:
    if explicit:
        return explicit
    for candidate in CHROME_CANDIDATES:
        found = shutil.which(candidate)
        if found:
            return found
    raise SystemExit("error: Chrome or Chromium not found; pass --chrome PATH or use --no-images")


def frozen_copy(html: Path) -> Path:
    """Write snapshot.html next to html with the animation clock frozen."""
    content = html.read_text(encoding="utf-8")
    if content.count("<head>") != 1:
        raise SystemExit(f"error: cannot freeze the clock in {html}: expected one <head>")
    snapshot = html.with_name("snapshot.html")
    snapshot.write_text(content.replace("<head>", "<head>" + FROZEN_CLOCK, 1), encoding="utf-8")
    return snapshot


def screenshot(chrome: str, html: Path, png: Path) -> None:
    page = frozen_copy(html)
    with tempfile.TemporaryDirectory() as profile_dir:
        result = subprocess.run(
            [
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--no-first-run",
                "--no-default-browser-check",
                f"--user-data-dir={profile_dir}",
                f"--window-size={SHOT_SIZE},{SHOT_SIZE}",
                f"--virtual-time-budget={VIRTUAL_TIME_MS}",
                f"--screenshot={png}",
                page.resolve().as_uri(),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    if result.returncode != 0 or not png.is_file():
        raise SystemExit(f"error: screenshot of {html} failed: {result.stderr.strip()[-500:]}")


# ---------------------------------------------------------------- report


def _parse_targets(raw: list[str]) -> dict[str, Path]:
    targets: dict[str, Path] = {}
    for item in raw:
        name, sep, path = item.partition("=")
        target = Path(path if sep else item)
        key = name if sep else target.resolve().name
        if key in targets:
            raise SystemExit(f"error: duplicate name {key!r}; use NAME=PATH")
        if not target.exists():
            raise SystemExit(f"error: not found: {target}")
        targets[key] = target
    return targets


def _table(header: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return lines


def write_report(out: Path, report: dict[str, Any], layers: dict[str, dict[str, Any]]) -> None:
    lines = [f"# Visual diversity report", "", f"Repositories: {len(layers)}. Image distance D version {D_VERSION}.", ""]
    lines += ["## Extracted features", ""]
    rows = []
    for name, r in layers.items():
        s, h, d = r["features"]["static"], r["features"]["history"], r["features"]["docs"]
        rows.append([name, s["file_count"], s["total_size_bytes"] // 1024, h["commit_count"],
                     h["unique_authors_count"], h["repository_age_days"], h["velocity"],
                     "yes" if s["has_tests"] else "no", "yes" if s["has_ci"] else "no"])
    lines += _table(["repo", "files", "size kB", "commits", "authors", "age days", "velocity/week", "tests", "CI"], rows)
    lines += ["", "## Saturated rules", ""]
    lines += _table(["rule", "repos"], [[s["rule"], f"{s['count']}/{s['of']}"] for s in report["saturation"]])
    lines += ["", "## Collapsed dimensions", ""]
    rows = []
    for layer in ("scores", "axes"):
        sp = report["spread"][layer]
        rows.append([layer, f"{sp['participation_ratio']} of {sp['variables']}", f"{sp['first_component']:.0%}",
                     len(sp["pairs_above_0_8"]), f"{sp['participation_ratio_covariance']} ({sp['first_component_covariance']:.1%})",
                     ", ".join(sp["constant"]) or "-"])
    lines += _table(["layer", "participation ratio", "first component", "pairs with |r| > 0.8", "covariance PCA", "constant"], rows)
    lines += ["", "## Prompts", ""]
    for mode, po in report["prompts"].items():
        lines.append(f"- {mode}: {po['lines_identical_for_all']} of {po['lines_per_prompt']} lines identical for all; "
                     f"mean differing lines {po['mean_differing_lines']}; closest {po['fewest_differing']}")
    if report.get("distance"):
        lines += ["", "## Image distance D", ""]
        rows = [[mode, d["nearest_neighbour_median"], f"{d['closest_pair'][2]} ({d['closest_pair'][0]}, {d['closest_pair'][1]})", d["pair_mean"]]
                for mode, d in report["distance"].items()]
        lines += _table(["render", "nearest-neighbour median", "closest pair", "pair mean"], rows)
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


def command_run(args: argparse.Namespace) -> int:
    targets = _parse_targets(args.repos)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    live_dir = out / "live"
    layers = {}
    for name, repo in targets.items():
        print(f"analysing {name} ({repo})", file=sys.stderr)
        layers[name] = analyse(name, repo, live_dir, args.source_commit)
    (out / "layers.json").write_text(json.dumps(layers, indent=1, default=str), encoding="utf-8")
    report: dict[str, Any] = {
        "saturation": saturation(layers),
        "spread": {
            "scores": spread({n: r["scores"] for n, r in layers.items()}),
            "axes": spread({n: r["axes"] for n, r in layers.items()}),
        },
        "prompts": {mode: prompt_overlap(layers, mode) for mode in REPRESENTATIONS},
    }
    if not args.no_images:
        chrome = find_chrome(args.chrome)
        shots = out / "shots"
        shots.mkdir(exist_ok=True)
        report["distance"] = {}
        for mode in REPRESENTATIONS:
            images = {}
            for name in layers:
                png = shots / f"{name}-{mode}.png"
                screenshot(chrome, live_dir / f"{name}-{mode}" / "live-preview.html", png)
                images[name] = png
            contact_sheet(images, out / f"contact-live-{mode}.png")
            report["distance"][f"live {mode}"] = distance_summary(
                {n: image_features(p) for n, p in images.items()}
            )
    write_report(out, report, layers)
    print((out / "report.md").read_text(encoding="utf-8"))
    return 0


def command_distance(args: argparse.Namespace) -> int:
    images = _parse_targets(args.images)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    summary = distance_summary({n: image_features(p) for n, p in images.items()})
    contact_sheet(images, out / "contact.png")
    (out / "distance.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("pairs", "nearest")}, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run the pipeline on repositories and measure diversity")
    run.add_argument("repos", nargs="+", help="PATH or NAME=PATH, at least two")
    run.add_argument("--out", required=True, help="output directory (use the git-ignored tmp/)")
    run.add_argument("--chrome", help="Chrome or Chromium executable (default: search PATH)")
    run.add_argument("--no-images", action="store_true", help="skip screenshots and D")
    run.add_argument("--source-commit", default="fixed",
                     help="source_commit passed to the pipeline (default 'fixed', as in analysis.md)")
    run.set_defaults(func=command_run)
    dist = sub.add_parser("distance", help="measure D on existing images")
    dist.add_argument("images", nargs="+", help="IMAGE or NAME=IMAGE, at least two")
    dist.add_argument("--out", required=True, help="output directory")
    dist.set_defaults(func=command_distance)
    args = parser.parse_args(argv)
    if len(getattr(args, "repos", getattr(args, "images", []))) < 2:
        parser.error("at least two repositories or images are needed")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
