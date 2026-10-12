#!/usr/bin/env python3
"""
Run the P5 release gate against a fresh perception and print the report.

Used by the Release Gate CI workflow to comment on pull requests. Perception
observers may be unavailable in CI; the gate reports those dimensions as
UNKNOWN rather than inventing a pass.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def main() -> int:
    from perception.layer import perceive
    from perception.release_gate import evaluate_release, format_gate_report

    try:
        report = perceive(save=False)
    except Exception as exc:
        print(f"perception unavailable: {type(exc).__name__}: {exc}")
        report = None

    result = evaluate_release(report)
    print(format_gate_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
