"""Seed sensitivity simulation utility for evidrava-group-draw-v1.

Evaluates selection distributions, group size frequencies, and empirical
cluster selection probabilities across multiple seeds on a candidate frame.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evidrava.seed_simulation import simulate_seeds


def main():
    parser = argparse.ArgumentParser(description="Simulate seed sensitivity for evidrava group draw")
    parser.add_argument("--frame", type=Path, required=True, help="Candidate frame CSV")
    parser.add_argument("--target", type=int, default=40, help="Target matters to draw (default 40)")
    parser.add_argument("--seeds", type=int, default=100, help="Number of seeds to simulate (default 100)")
    parser.add_argument("--start-seed", type=int, default=1, help="Starting integer seed (default 1)")
    parser.add_argument("--out", type=Path, help="Optional output JSON path")
    args = parser.parse_args()

    try:
        report = simulate_seeds(args.frame, args.target, args.seeds, args.start_seed)
    except Exception as exc:
        print(f"Simulation failed: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote simulation report to {args.out}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
