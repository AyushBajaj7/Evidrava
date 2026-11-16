"""Seed sensitivity simulation utility for evidrava-group-draw-v1."""
from collections import Counter
import json
from pathlib import Path

from .frame import inspect_frame, _select_groups


def simulate_seeds(frame_path, target_matters=40, seed_count=100, seed_start=1):
    """Simulate group draws across a range of seeds to inspect selection properties."""
    frame = inspect_frame(frame_path)
    if frame["status"] != "READY_TO_FREEZE":
        raise ValueError(f"Candidate frame is not READY_TO_FREEZE (status={frame['status']})")

    groups = frame["eligible_groups"]
    total_eligible = sum(len(members) for members in groups.values())
    total_groups = len(groups)

    if total_eligible < target_matters:
        raise ValueError(f"Insufficient eligible matters: {total_eligible} < {target_matters}")

    group_sizes = {g: len(members) for g, members in groups.items()}
    size_distribution_in_frame = Counter(group_sizes.values())

    selected_group_counts = Counter()
    size_selection_counts = Counter()
    unreachable_seeds = []

    for seed in range(seed_start, seed_start + seed_count):
        try:
            selected_groups, _ = _select_groups(groups, target_matters, seed)
            for g in selected_groups:
                selected_group_counts[g] += 1
                size_selection_counts[group_sizes[g]] += 1
        except ValueError:
            unreachable_seeds.append(seed)

    successful_runs = seed_count - len(unreachable_seeds)
    if successful_runs == 0:
        return {
            "report_kind": "seed-sensitivity-simulation",
            "status": "UNREACHABLE",
            "research_decision": "NOT_EVALUATED",
            "target_matters": target_matters,
            "seed_count": seed_count,
            "successful_runs": 0,
            "unreachable_seeds": unreachable_seeds,
            "diagnostics": [{"code": "TARGET_NEVER_REACHABLE", "message": "No evaluated seed found a whole-group combination"}],
            "limitations": ["Simulation evaluates selection probability; it does not replace protocol pre-registration."],
        }

    empirical_group_probs = {
        g: selected_group_counts[g] / successful_runs for g in sorted(groups)
    }

    avg_groups_selected_per_run = sum(selected_group_counts.values()) / successful_runs

    return {
        "report_kind": "seed-sensitivity-simulation",
        "status": "COMPLETED",
        "research_decision": "NOT_EVALUATED",
        "frame_name": Path(frame_path).name,
        "frame_sha256": frame["frame_sha256"],
        "summary": {
            "target_matters": target_matters,
            "total_eligible_matters": total_eligible,
            "total_eligible_groups": total_groups,
            "seed_count": seed_count,
            "successful_runs": successful_runs,
            "unreachable_seeds_count": len(unreachable_seeds),
            "avg_groups_selected_per_run": round(avg_groups_selected_per_run, 2),
        },
        "frame_group_size_distribution": dict(sorted(size_distribution_in_frame.items())),
        "selected_group_size_counts": dict(sorted(size_selection_counts.items())),
        "empirical_group_selection_probabilities": empirical_group_probs,
        "unreachable_seeds": unreachable_seeds,
        "diagnostics": [],
        "limitations": [
            "Simulation inspects empirical cluster-selection probabilities under evidrava-group-draw-v1.",
            "It is not simple random sampling (SRS); knapsack constraints may favor certain group size combinations.",
            "Pre-registration requires committing the frame hash and deriving the actual seed externally after commit.",
        ],
    }
