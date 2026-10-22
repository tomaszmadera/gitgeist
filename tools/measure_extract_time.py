"""Time extract_features on one repository with whichever gitgeist is importable.

Used for stage 2 acceptance criterion 2 (main vs branch). main has no
`diversity_report.py extract-time`, so both sides run this one script and
select the code under test with PYTHONPATH:

    PYTHONPATH=<checkout>/src python tools/measure_extract_time.py PATH --runs 5

One warm-up run, then --runs timed runs; prints the gitgeist module path and
version, every run time and the median in seconds. Standard library only.
"""

from __future__ import annotations

import argparse
import statistics
import time


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="repository path")
    parser.add_argument("--runs", type=int, default=5, help="timed runs after one warm-up run (default 5)")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be at least 1")

    import gitgeist
    from gitgeist.features.extractor import extract_features

    print(f"gitgeist: {gitgeist.__file__} version {getattr(gitgeist, '__version__', '?')}")
    extract_features(args.path)
    times = []
    for i in range(args.runs):
        start = time.perf_counter()
        extract_features(args.path)
        times.append(time.perf_counter() - start)
        print(f"run {i + 1}: {times[-1]:.4f} s")
    print(f"median: {statistics.median(times):.4f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
