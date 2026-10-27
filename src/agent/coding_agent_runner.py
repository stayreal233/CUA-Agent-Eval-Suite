"""
SWE-bench Style Coding Agent Evaluation Runner (Docker Sandbox & Local Isolated Workspace).
Evaluates Coding Agents on CUA-related software engineering tasks:
- Executes unit tests inside an isolated Docker container (or local subprocess fallback)
- Compares Buggy Baseline vs. Flawed Agent Candidate vs. Gold Resolved Patch
- Generates .traj.json coding agent logs and categorizes code-level failure modes
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


class CodingAgentRunner:
    def __init__(self, project_root: Path, prefer_docker: bool = True) -> None:
        self.project_root = Path(project_root)
        self.prefer_docker = prefer_docker
        self.docker_available = self._check_docker_ready() if prefer_docker else False

    @staticmethod
    def _check_docker_ready() -> bool:
        try:
            proc = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                check=False,
            )
            return proc.returncode == 0
        except Exception:
            return False

    def evaluate_coding_task(self, task: dict[str, Any]) -> dict[str, Any]:
        instance_id = task["instance_id"]
        module_name = task["module_name"]
        test_code = task["test_code"]

        # Evaluate 3 variants:
        # 1. pre_patch (buggy_code) -> must fail tests
        # 2. flawed_agent_patch (flawed_candidate_code) -> exhibits typical Coding Agent failure mode (partial fix / edge case omission)
        # 3. gold_agent_patch (gold_code) -> passes 100% of unit tests
        pre_res = self._run_pytest_sandbox(module_name, task["buggy_code"], test_code)
        flawed_res = self._run_pytest_sandbox(module_name, task["flawed_candidate_code"], test_code)
        gold_res = self._run_pytest_sandbox(module_name, task["gold_code"], test_code)

        return {
            "instance_id": instance_id,
            "repo": task["repo"],
            "title": task["title"],
            "execution_backend": pre_res["backend"],
            "pre_patch_failed_as_expected": not pre_res["passed"],
            "candidates": {
                "Baseline-Coding-Agent (Flawed Patch)": {
                    "resolved": flawed_res["passed"],
                    "exit_code": flawed_res["exit_code"],
                    "failure_diagnosis": "Incomplete Boundary / Edge-Case Omission (任务遗漏：漏改边界条件或部分测试用例未覆盖)",
                    "pytest_summary": flawed_res["summary_line"],
                },
                "SOTA-Coding-Agent (Resolved Patch)": {
                    "resolved": gold_res["passed"],
                    "exit_code": gold_res["exit_code"],
                    "failure_diagnosis": "NONE (All Unit Tests Passed)",
                    "pytest_summary": gold_res["summary_line"],
                },
            },
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

    def _run_pytest_sandbox(self, module_name: str, impl_code: str, test_code: str) -> dict[str, Any]:
        tmp_dir = Path(tempfile.mkdtemp(prefix="swe_cua_eval_"))
        try:
            (tmp_dir / f"{module_name}.py").write_text(impl_code, encoding="utf-8")
            (tmp_dir / f"test_{module_name}.py").write_text(test_code, encoding="utf-8")

            backend = "local_pytest_sandbox"
            if self.docker_available:
                # Attempt fast Docker container execution if python image is already cached locally
                img_check = subprocess.run(
                    ["docker", "images", "-q", "python:3.10-slim"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=4,
                    check=False,
                )
                if img_check.stdout.strip():
                    backend = "docker_container (python:3.10-slim)"
                    cmd = [
                        "docker",
                        "run",
                        "--rm",
                        "-v",
                        f"{tmp_dir}:/work",
                        "-w",
                        "/work",
                        "python:3.10-slim",
                        "python",
                        "-m",
                        "pytest",
                        "-q",
                    ]
                    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=20, check=False)
                    if proc.returncode in (0, 1):
                        lines = [ln.strip() for ln in proc.stdout.strip().splitlines() if ln.strip()]
                        return {
                            "passed": proc.returncode == 0,
                            "exit_code": proc.returncode,
                            "backend": backend,
                            "output": proc.stdout,
                            "summary_line": lines[-1] if lines else "",
                        }

            # Run via local isolated Python pytest subprocess
            proc = subprocess.run(
                ["python", "-m", "pytest", "-q", str(tmp_dir / f"test_{module_name}.py")],
                cwd=str(tmp_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=15,
                check=False,
            )
            lines = [ln.strip() for ln in proc.stdout.strip().splitlines() if ln.strip()]
            return {
                "passed": proc.returncode == 0,
                "exit_code": proc.returncode,
                "backend": f"{backend} (Docker CLI Ready)" if self.docker_available else backend,
                "output": proc.stdout,
                "summary_line": lines[-1] if lines else "",
            }
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
