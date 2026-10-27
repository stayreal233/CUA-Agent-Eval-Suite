"""
OSWorld-Style Multi-Modal & Cross-Application Task Verifier.
Evaluates whether a CUA / GUI Agent actually completed the task by inspecting:
1. Final Browser DOM state & attributes
2. Cross-application local file artifacts (CSV, JSON, Markdown, .env)
3. Local SQLite database records
"""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any


class TaskVerifier:
    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)

    def evaluate(self, task_spec: dict[str, Any], final_dom_state: dict[str, str], workspace_dir: Path | None = None) -> dict[str, Any]:
        eval_spec = task_spec.get("evaluation", {})
        eval_type = eval_spec.get("evaluator_type", "dom_and_backend_state")
        base_dir = Path(workspace_dir) if workspace_dir else self.project_root

        checks: list[dict[str, Any]] = []

        # 1. Check required DOM state if present
        req_dom = eval_spec.get("required_dom_state", {})
        for selector, expected_val in req_dom.items():
            actual_val = str(final_dom_state.get(selector, "")).strip()
            passed = actual_val == str(expected_val).strip()
            checks.append({
                "check_type": "dom_state",
                "target": selector,
                "expected": expected_val,
                "actual": actual_val,
                "passed": passed,
            })

        # 2. Check cross-app file artifact if required
        if eval_type == "hybrid_dom_and_file" or "required_file" in eval_spec:
            rel_path = eval_spec["required_file"]
            file_path = base_dir / rel_path
            file_fmt = eval_spec.get("file_format", "text")
            file_check = self._verify_file_artifact(file_path, file_fmt, eval_spec)
            checks.append(file_check)

        # 3. Check cross-app SQLite state if required
        if eval_type == "hybrid_dom_and_sqlite" or "sqlite_db_path" in eval_spec:
            db_path = base_dir / eval_spec["sqlite_db_path"]
            query = eval_spec["sqlite_query"]
            expected_res = eval_spec["expected_query_result"]
            db_check = self._verify_sqlite_artifact(db_path, query, expected_res)
            checks.append(db_check)

        total_checks = len(checks)
        passed_checks = sum(1 for c in checks if c["passed"])
        all_passed = (total_checks > 0) and (passed_checks == total_checks)
        subgoal_score = round(passed_checks / max(1, total_checks), 3)

        return {
            "task_id": task_spec["task_id"],
            "evaluator_type": eval_type,
            "passed": all_passed,
            "score": 1.0 if all_passed else subgoal_score,
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "check_details": checks,
        }

    def _verify_file_artifact(self, file_path: Path, file_fmt: str, eval_spec: dict[str, Any]) -> dict[str, Any]:
        if not file_path.exists():
            return {
                "check_type": f"file_artifact ({file_fmt})",
                "target": str(file_path.name),
                "expected": "File exists and matches schema",
                "actual": "FILE_NOT_FOUND",
                "passed": False,
            }

        try:
            raw_text = file_path.read_text(encoding="utf-8")
            if file_fmt == "csv":
                lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
                reader = list(csv.DictReader(lines))
                expected_rows = eval_spec.get("expected_rows", len(reader))
                row_count_ok = len(reader) == expected_rows
                checksum_map = eval_spec.get("expected_checksum_values", {})
                checksum_ok = True
                actual_map = {}
                for r in reader:
                    clean_r = {k.strip(): v.strip() for k, v in r.items() if k}
                    inv_id = clean_r.get("invoice_id", "")
                    tot = clean_r.get("total_due", "")
                    if inv_id:
                        actual_map[inv_id] = tot
                for k, exp_v in checksum_map.items():
                    if k not in actual_map or abs(float(actual_map[k]) - float(exp_v)) > 1e-2:
                        checksum_ok = False
                passed = row_count_ok and checksum_ok
                return {
                    "check_type": "file_artifact (csv)",
                    "target": file_path.name,
                    "expected": f"rows={expected_rows}, totals={checksum_map}",
                    "actual": f"rows={len(reader)}, totals={actual_map}",
                    "passed": passed,
                }

            if file_fmt == "json":
                data = json.loads(raw_text)
                req_keys = eval_spec.get("expected_json_keys", [])
                keys_ok = all(k in data for k in req_keys)
                req_vals = eval_spec.get("expected_json_values", {})
                vals_ok = all(data.get(k) == v for k, v in req_vals.items())
                passed = keys_ok and vals_ok
                return {
                    "check_type": "file_artifact (json)",
                    "target": file_path.name,
                    "expected": f"keys={req_keys}, values={req_vals}",
                    "actual": json.dumps({k: data.get(k) for k in req_keys}, ensure_ascii=False),
                    "passed": passed,
                }

            if file_fmt == "markdown":
                req_subs = eval_spec.get("required_substrings", [])
                missing = [s for s in req_subs if s not in raw_text]
                passed = len(missing) == 0
                return {
                    "check_type": "file_artifact (markdown)",
                    "target": file_path.name,
                    "expected": f"Contains all {len(req_subs)} required sections",
                    "actual": "ALL_PRESENT" if passed else f"Missing: {missing}",
                    "passed": passed,
                }

            return {
                "check_type": "file_artifact (text)",
                "target": file_path.name,
                "expected": "Non-empty file",
                "actual": f"{len(raw_text)} bytes",
                "passed": len(raw_text.strip()) > 0,
            }
        except Exception as exc:
            return {
                "check_type": f"file_artifact ({file_fmt})",
                "target": file_path.name,
                "expected": "Valid artifact format",
                "actual": f"PARSE_ERROR: {exc}",
                "passed": False,
            }

    def _verify_sqlite_artifact(self, db_path: Path, query: str, expected_result: Any) -> dict[str, Any]:
        if not db_path.exists():
            return {
                "check_type": "sqlite_db_state",
                "target": db_path.name,
                "expected": str(expected_result),
                "actual": "DB_FILE_NOT_FOUND",
                "passed": False,
            }
        try:
            conn = sqlite3.connect(str(db_path))
            try:
                cur = conn.cursor()
                cur.execute(query)
                row = cur.fetchone()
                actual_val = row[0] if row else None
                passed = actual_val == expected_result
                return {
                    "check_type": "sqlite_db_state",
                    "target": f"{db_path.name} -> {query}",
                    "expected": str(expected_result),
                    "actual": str(actual_val),
                    "passed": passed,
                }
            finally:
                conn.close()
        except Exception as exc:
            return {
                "check_type": "sqlite_db_state",
                "target": db_path.name,
                "expected": str(expected_result),
                "actual": f"SQL_ERROR: {exc}",
                "passed": False,
            }
