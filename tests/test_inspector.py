"""Unit tests for TrajectoryInspector verifying detection of all 4 canonical CUA failure modes."""

from __future__ import annotations

from src.evaluator.trajectory_inspector import TrajectoryInspector


def test_detects_grounding_misclick_outside_bbox() -> None:
    inspector = TrajectoryInspector()
    trajectory = {
        "task_id": "T-MISCLICK",
        "expected_steps": 3,
        "agent_claimed_success": True,
        "steps": [
            {
                "step_index": 1,
                "action_type": "click",
                "selector": "#btn-submit",
                "coords": [500, 400],
                "target_bbox": {"x": 100, "y": 100, "width": 80, "height": 30},
            }
        ],
        "final_dom_state": {"#status": "DRAFT"},
    }
    verification = {"passed": False, "score": 0.0, "passed_checks": 0, "total_checks": 1, "check_details": []}
    res = inspector.inspect(trajectory, verification)
    assert "GROUNDING_MISCLICK" in res["failure_categories"]


def test_detects_state_misjudgment_on_premature_toast() -> None:
    inspector = TrajectoryInspector()
    trajectory = {
        "task_id": "T-HALLUCINATION",
        "expected_steps": 4,
        "agent_claimed_success": True,
        "premature_stop_on_toast": True,
        "steps": [{"step_index": 1, "action_type": "click", "selector": "#btn-migrate"}],
        "final_dom_state": {"#migration-final-state": "ERR_MISSING_CHECKSUM", "#toast-msg": "Request Sent"},
    }
    verification = {"passed": False, "score": 0.0, "passed_checks": 0, "total_checks": 1, "check_details": []}
    res = inspector.inspect(trajectory, verification)
    assert "STATE_MISJUDGMENT" in res["failure_categories"]


def test_detects_action_looping_on_disabled_button() -> None:
    inspector = TrajectoryInspector()
    trajectory = {
        "task_id": "T-LOOP",
        "expected_steps": 4,
        "agent_claimed_success": False,
        "steps": [
            {"step_index": 1, "action_type": "click", "selector": "#btn-export", "target_disabled": True},
            {"step_index": 2, "action_type": "click", "selector": "#btn-export", "target_disabled": True},
            {"step_index": 3, "action_type": "click", "selector": "#btn-export", "target_disabled": True},
        ],
        "final_dom_state": {"#export-status": "LOCKED"},
    }
    verification = {"passed": False, "score": 0.0, "passed_checks": 0, "total_checks": 1, "check_details": []}
    res = inspector.inspect(trajectory, verification)
    assert "ACTION_LOOPING" in res["failure_categories"]


def test_detects_task_omission_on_uncommitted_changes() -> None:
    inspector = TrajectoryInspector()
    trajectory = {
        "task_id": "T-OMISSION",
        "expected_steps": 5,
        "agent_claimed_success": True,
        "steps": [
            {"step_index": 1, "action_type": "fill", "selector": "#rule-1"},
            {"step_index": 2, "action_type": "check", "selector": "#rule-2"},
        ],
        "final_dom_state": {"#firewall-commit-state": "STAGED_UNCOMMITTED"},
    }
    verification = {
        "passed": False,
        "score": 0.75,
        "passed_checks": 3,
        "total_checks": 4,
        "check_details": [
            {"target": "#firewall-commit-state", "expected": "COMMITTED_TO_KERNEL", "actual": "STAGED_UNCOMMITTED", "passed": False}
        ],
    }
    res = inspector.inspect(trajectory, verification)
    assert "TASK_OMISSION" in res["failure_categories"]
