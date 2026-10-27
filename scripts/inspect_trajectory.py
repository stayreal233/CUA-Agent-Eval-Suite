"""
CLI Tool to inspect an individual CUA Trajectory (.traj.json) or directory of trajectories,
printing a formatted Quality Inspection & Root-Cause Attribution Report.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect CUA trajectory logs and report failure modes.")
    parser.add_argument(
        "--path",
        default="artifacts/trajectories",
        help="Path to a .traj.json file or directory containing .traj.json files",
    )
    parser.add_argument(
        "--only-failures",
        action="store_true",
        help="Only display trajectories where ORM failed or anomalies were detected",
    )
    args = parser.parse_args()

    target = Path(args.path)
    files = [target] if target.is_file() else sorted(target.glob("*.traj.json"))
    if not files:
        print(f"No trajectory files found at {target}")
        return

    print("=" * 95)
    print(f"{'TASK_ID':<14} | {'AGENT_PROFILE':<20} | {'ORM_PASS':<8} | {'PRM':<6} | {'PRIMARY_FAILURE_MODE'}")
    print("=" * 95)
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        insp = data["inspection"]
        if args.only_failures and insp["orm_passed"] and insp["anomaly_count"] == 0:
            continue
        print(
            f"{insp['task_id']:<14} | {insp['agent_profile']:<20} | "
            f"{str(insp['orm_passed']):<8} | {insp['prm_score']:<6.3f} | {insp['primary_failure_mode']}"
        )
        for anom in insp.get("anomalies", []):
            print(f"   └── [Step {anom['step_index']}] {anom['zh_label']}: {anom['evidence']}")
    print("=" * 95)


if __name__ == "__main__":
    main()
