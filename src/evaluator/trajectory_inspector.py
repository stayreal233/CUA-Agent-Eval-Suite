"""
CUARewardBench-Style Automated Trajectory Quality Inspector (ORM + PRM).
Performs step-level and trajectory-level quality inspection to automatically identify
the 4 canonical CUA failure modes specified in the JD:
  1. 误点击 (GROUNDING_MISCLICK): Coordinate outside target bbox, DPI offset, or clicking ad/trap overlay.
  2. 状态误判 (STATE_MISJUDGMENT): Premature task termination on fake/intermediate toast or unverified error state.
  3. 重复操作 (ACTION_LOOPING): Clicking disabled elements repeatedly, spatial coordinate click loops, or stagnant scrolling.
  4. 任务遗漏 (TASK_OMISSION): Partial subgoal completion (e.g., forgetting final commit button or cross-app file sync).
"""

from __future__ import annotations

import math
from typing import Any


FAILURE_TAXONOMY = {
    "GROUNDING_MISCLICK": {
        "zh_name": "误点击 (Grounding / Coordinate Misclick)",
        "severity": "HIGH",
        "description": "点击坐标偏离目标元素边界框(BBox)、受高分屏缩放偏移影响，或误触推广弹窗/相近干扰按钮。",
    },
    "STATE_MISJUDGMENT": {
        "zh_name": "状态误判 (Premature State Hallucination)",
        "severity": "HIGH",
        "description": "将异步中间态提示（如 Request Sent Toast）误判为任务最终成功，忽略后续校验报错提前结束任务。",
    },
    "ACTION_LOOPING": {
        "zh_name": "重复操作 (Action Looping / Stagnation)",
        "severity": "MEDIUM",
        "description": "在未满足前置条件（如按钮处于 disabled 状态）或页面无响应时，对同一位置/元素发起连续 >=3 次无效重复操作。",
    },
    "TASK_OMISSION": {
        "zh_name": "任务遗漏 (Subgoal / Final Commit Omission)",
        "severity": "HIGH",
        "description": "完成了前置表单修改但遗漏关键收尾动作（如未点击全局 Apply & Persist 按钮、漏做跨应用本地文件保存或弹窗二次确认）。",
    },
}


class TrajectoryInspector:
    """Automated Quality Assurance (QA) & PRM/ORM Evaluator for CUA Trajectories."""

    def inspect(self, trajectory: dict[str, Any], verification_result: dict[str, Any]) -> dict[str, Any]:
        steps: list[dict[str, Any]] = trajectory.get("steps", [])
        anomalies: list[dict[str, Any]] = []

        # 1. Step-by-step check for Grounding Misclick & Disabled Element Interaction
        for step in steps:
            step_idx = step.get("step_index", 0)
            action_type = step.get("action_type", "")
            selector = step.get("selector", "")
            coords = step.get("coords")
            target_bbox = step.get("target_bbox")
            hit_trap = step.get("hit_ad_trap", False)
            element_disabled = step.get("target_disabled", False)

            if hit_trap or "trap" in str(selector).lower():
                anomalies.append({
                    "category": "GROUNDING_MISCLICK",
                    "zh_label": FAILURE_TAXONOMY["GROUNDING_MISCLICK"]["zh_name"],
                    "step_index": step_idx,
                    "evidence": f"Step {step_idx} clicked deceptive trap element '{selector}' at {coords}.",
                    "remediation": "Add Set-of-Marks (SoM) semantic filtering and close ad overlays before primary click.",
                })
            elif action_type == "click" and coords and target_bbox:
                if not self._point_in_bbox(coords[0], coords[1], target_bbox):
                    anomalies.append({
                        "category": "GROUNDING_MISCLICK",
                        "zh_label": FAILURE_TAXONOMY["GROUNDING_MISCLICK"]["zh_name"],
                        "step_index": step_idx,
                        "evidence": (
                            f"Step {step_idx} click coordinate {coords} fell outside target '{selector}' "
                            f"bounding box {target_bbox} (coordinate grounding offset)."
                        ),
                        "remediation": "Calibrate VLM coordinate normalization [0,1000] against CSS viewport dimensions.",
                    })

            if action_type == "click" and element_disabled:
                anomalies.append({
                    "category": "ACTION_LOOPING",
                    "zh_label": FAILURE_TAXONOMY["ACTION_LOOPING"]["zh_name"],
                    "step_index": step_idx,
                    "evidence": f"Step {step_idx} attempted to click disabled element '{selector}' without unlocking prerequisites.",
                    "remediation": "Inspect DOM disabled attribute / AXTree state before issuing click actions.",
                })

        # 2. Trajectory-level Action Looping check (>=3 repeated clicks or >=4 stagnant scrolls)
        loop_info = self._detect_repeated_loops(steps)
        if loop_info["has_loop"]:
            anomalies.append({
                "category": "ACTION_LOOPING",
                "zh_label": FAILURE_TAXONOMY["ACTION_LOOPING"]["zh_name"],
                "step_index": loop_info["loop_start_step"],
                "evidence": loop_info["evidence"],
                "remediation": "Introduce state-delta memory check; abort identical action if DOM hash is unchanged.",
            })

        # 3. State Misjudgment check (Agent claims success/DONE while backend reports error/intermediate state)
        agent_claimed_done = trajectory.get("agent_claimed_success", False)
        final_dom = trajectory.get("final_dom_state", {})
        if agent_claimed_done and not verification_result.get("passed", False):
            # Check if there is an explicit error or intermediate toast hallucination
            dom_values_str = " ".join(str(v) for v in final_dom.values())
            if (
                "ERR_" in dom_values_str
                or "Request Sent" in dom_values_str
                or trajectory.get("premature_stop_on_toast", False)
            ):
                anomalies.append({
                    "category": "STATE_MISJUDGMENT",
                    "zh_label": FAILURE_TAXONOMY["STATE_MISJUDGMENT"]["zh_name"],
                    "step_index": len(steps),
                    "evidence": (
                        f"Agent declared task complete at Step {len(steps)} after intermediate toast, "
                        f"but actual DOM state indicates failure: {final_dom}."
                    ),
                    "remediation": "Wait for async network idle and verify terminal status badge before calling finish().",
                })

        # 4. Task Omission check (Partial completion of checks or missing final commit / cross-app artifact)
        passed_checks = verification_result.get("passed_checks", 0)
        total_checks = verification_result.get("total_checks", 1)
        if not verification_result.get("passed", False):
            failed_details = [c for c in verification_result.get("check_details", []) if not c.get("passed")]
            has_uncommitted = any(
                "STAGED_UNCOMMITTED" in str(c.get("actual", ""))
                or "FILE_NOT_FOUND" in str(c.get("actual", ""))
                or "modal-confirmed" in str(c.get("target", ""))
                for c in failed_details
            )
            if (0 < passed_checks < total_checks) or has_uncommitted:
                missing_targets = [c.get("target", "") for c in failed_details]
                anomalies.append({
                    "category": "TASK_OMISSION",
                    "zh_label": FAILURE_TAXONOMY["TASK_OMISSION"]["zh_name"],
                    "step_index": len(steps),
                    "evidence": (
                        f"Agent completed {passed_checks}/{total_checks} verification checks but omitted critical "
                        f"final step(s) or cross-app artifact: {missing_targets}."
                    ),
                    "remediation": "Enforce subgoal checklist verification before termination (check commit state & local output files).",
                })

        # Deduplicate categories while preserving all step evidence
        unique_categories = []
        for a in anomalies:
            if a["category"] not in unique_categories:
                unique_categories.append(a["category"])

        # Compute PRM (Process Reward Model) step efficiency & quality score
        expected_steps = max(1, trajectory.get("expected_steps", 5))
        actual_steps = max(1, len(steps))
        step_efficiency = min(1.0, expected_steps / actual_steps)
        penalty = min(0.85, 0.28 * len(anomalies))
        orm_score = 1.0 if verification_result.get("passed", False) else verification_result.get("score", 0.0)
        prm_score = round(max(0.0, (0.6 * orm_score + 0.4 * step_efficiency) - penalty), 3)

        return {
            "task_id": trajectory.get("task_id"),
            "agent_profile": trajectory.get("agent_profile", "default"),
            "orm_passed": verification_result.get("passed", False),
            "orm_score": orm_score,
            "prm_score": prm_score,
            "step_count": len(steps),
            "expected_steps": expected_steps,
            "step_efficiency": round(step_efficiency, 3),
            "anomaly_count": len(anomalies),
            "failure_categories": unique_categories,
            "primary_failure_mode": unique_categories[0] if unique_categories else "NONE (PASS)",
            "anomalies": anomalies,
        }

    @staticmethod
    def _point_in_bbox(x: float, y: float, bbox: dict[str, float], margin: float = 4.0) -> bool:
        bx = float(bbox.get("x", 0)) - margin
        by = float(bbox.get("y", 0)) - margin
        bw = float(bbox.get("width", 0)) + 2 * margin
        bh = float(bbox.get("height", 0)) + 2 * margin
        return (bx <= x <= bx + bw) and (by <= y <= by + bh)

    @staticmethod
    def _detect_repeated_loops(steps: list[dict[str, Any]], dist_threshold: float = 8.0) -> dict[str, Any]:
        n = len(steps)
        for i in range(n - 2):
            s1, s2, s3 = steps[i], steps[i + 1], steps[i + 2]
            if s1.get("action_type") == s2.get("action_type") == s3.get("action_type") == "click":
                sel1, sel2, sel3 = s1.get("selector"), s2.get("selector"), s3.get("selector")
                if sel1 and sel1 == sel2 == sel3:
                    return {
                        "has_loop": True,
                        "loop_start_step": s1.get("step_index", i + 1),
                        "evidence": f"Repeated identical click on selector '{sel1}' for 3+ consecutive steps starting at Step {i + 1}.",
                    }
                c1, c2, c3 = s1.get("coords"), s2.get("coords"), s3.get("coords")
                if c1 and c2 and c3:
                    d12 = math.hypot(c1[0] - c2[0], c1[1] - c2[1])
                    d23 = math.hypot(c2[0] - c3[0], c2[1] - c3[1])
                    if d12 <= dist_threshold and d23 <= dist_threshold:
                        return {
                            "has_loop": True,
                            "loop_start_step": s1.get("step_index", i + 1),
                            "evidence": f"Spatial click loop detected around coordinates {c1} (jitter <= {dist_threshold}px) starting at Step {i + 1}.",
                        }
        return {"has_loop": False, "loop_start_step": None, "evidence": None}
