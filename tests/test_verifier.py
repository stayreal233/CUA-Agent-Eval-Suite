"""Unit tests for TaskVerifier (DOM, CSV, JSON, Markdown, and SQLite verification)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from src.evaluator.task_verifier import TaskVerifier


def test_verifier_dom_and_csv_pass(tmp_path: Path) -> None:
    csv_dir = tmp_path / "artifacts" / "workspace_outputs"
    csv_dir.mkdir(parents=True)
    csv_file = csv_dir / "overdue_audit_2026.csv"
    csv_file.write_text(
        "invoice_id,vendor,amount,overdue_days,penalty,total_due\n"
        "INV-901,TechSupply_Co,4000.00,45,200.00,4200.00\n"
        "INV-904,CloudMatrix_Inc,8500.00,60,425.00,8925.00\n",
        encoding="utf-8",
    )

    task_spec = {
        "task_id": "TEST-CROSS-CSV",
        "evaluation": {
            "evaluator_type": "hybrid_dom_and_file",
            "required_dom_state": {"#status": "OK"},
            "required_file": "artifacts/workspace_outputs/overdue_audit_2026.csv",
            "file_format": "csv",
            "expected_rows": 2,
            "expected_checksum_values": {"INV-901": "4200.00", "INV-904": "8925.00"},
        },
    }
    verifier = TaskVerifier(tmp_path)
    res = verifier.evaluate(task_spec, {"#status": "OK"}, workspace_dir=tmp_path)
    assert res["passed"] is True
    assert res["score"] == 1.0


def test_verifier_sqlite_check(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE audit (id INT, role TEXT);")
    conn.execute("INSERT INTO audit VALUES (1, 'DIAMOND'), (2, 'DIAMOND');")
    conn.commit()
    conn.close()

    task_spec = {
        "task_id": "TEST-SQLITE",
        "evaluation": {
            "evaluator_type": "hybrid_dom_and_sqlite",
            "required_dom_state": {"#vip": "DONE"},
            "sqlite_db_path": "test.db",
            "sqlite_query": "SELECT COUNT(*) FROM audit WHERE role='DIAMOND';",
            "expected_query_result": 2,
        },
    }
    verifier = TaskVerifier(tmp_path)
    res = verifier.evaluate(task_spec, {"#vip": "DONE"}, workspace_dir=tmp_path)
    assert res["passed"] is True
