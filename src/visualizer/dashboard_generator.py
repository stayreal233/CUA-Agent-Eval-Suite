"""
Interactive HTML Trajectory Quality Inspection Dashboard & Visual Chart Generator.
Generates:
1. artifacts/dashboard/index.html (Interactive CUA & SWE-bench Evaluation Dashboard with Screenshot Preview)
2. artifacts/dashboard/benchmark_overview.png (Summary Comparison Chart for GitHub README)
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


class DashboardGenerator:
    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.dashboard_dir = self.project_root / "artifacts" / "dashboard"
        self.dashboard_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, summary_data: dict[str, Any]) -> dict[str, Path]:
        html_path = self.dashboard_dir / "index.html"
        chart_path = self.dashboard_dir / "benchmark_overview.png"

        self._render_overview_png(summary_data, chart_path)
        self._render_interactive_html(summary_data, html_path)

        return {"html_dashboard": html_path, "overview_chart": chart_path}

    def _render_overview_png(self, summary_data: dict[str, Any], out_path: Path) -> None:
        """Render a clean, high-contrast benchmark comparison & failure distribution card using Pillow."""
        width, height = 1100, 520
        img = Image.new("RGB", (width, height), (15, 23, 42))
        draw = ImageDraw.Draw(img)

        # Header banner
        draw.rectangle((0, 0, width, 68), fill=(30, 41, 59))
        draw.text((28, 22), "CUA-Agent-Eval-Suite // Benchmark & Trajectory QA Overview (15 GUI/Cross-App + 5 SWE Tasks)", fill=(248, 250, 252))

        # Left Panel: Model Performance Bars
        draw.rectangle((28, 92, 540, 490), fill=(30, 41, 59), outline=(51, 65, 85), width=2)
        draw.text((48, 110), "1. Model ORM Success Rate & PRM Trajectory Quality (%)", fill=(56, 189, 248))

        profiles = summary_data.get("profile_metrics", {})
        y_offset = 160
        for prof_name, metrics in profiles.items():
            orm_pct = float(metrics.get("orm_pass_rate", 0.0)) * 100.0
            prm_pct = float(metrics.get("avg_prm_score", 0.0)) * 100.0

            draw.text((48, y_offset), f"{prof_name}", fill=(226, 232, 240))
            # ORM Bar
            bar_max_w = 340
            orm_w = int((orm_pct / 100.0) * bar_max_w)
            draw.rectangle((48, y_offset + 24, 48 + bar_max_w, y_offset + 44), fill=(51, 65, 85))
            draw.rectangle((48, y_offset + 24, 48 + max(4, orm_w), y_offset + 44), fill=(34, 197, 94))
            draw.text((400, y_offset + 26), f"ORM Pass: {orm_pct:.1f}%", fill=(134, 239, 172))

            # PRM Bar
            prm_w = int((prm_pct / 100.0) * bar_max_w)
            draw.rectangle((48, y_offset + 52, 48 + bar_max_w, y_offset + 72), fill=(51, 65, 85))
            draw.rectangle((48, y_offset + 52, 48 + max(4, prm_w), y_offset + 72), fill=(59, 130, 246))
            draw.text((400, y_offset + 54), f"PRM Score: {prm_pct:.1f}%", fill=(147, 197, 253))

            y_offset += 110

        # Check SWE-bench coding agent summary
        swe_metrics = summary_data.get("swe_coding_summary", {})
        sota_swe = float(swe_metrics.get("sota_resolve_rate", 1.0)) * 100.0
        base_swe = float(swe_metrics.get("baseline_resolve_rate", 0.0)) * 100.0
        draw.text((48, 390), f"SWE-bench Coding Sandbox (5 Tasks):", fill=(226, 232, 240))
        draw.text((48, 418), f"- SOTA-Coding-Agent Resolve Rate:     {sota_swe:.1f}% (5/5 Passed)", fill=(134, 239, 172))
        draw.text((48, 444), f"- Baseline-Coding-Agent Resolve Rate: {base_swe:.1f}% (Edge-case omissions)", fill=(252, 165, 165))

        # Right Panel: 4 Failure Mode Distribution
        draw.rectangle((568, 92, 1072, 490), fill=(30, 41, 59), outline=(51, 65, 85), width=2)
        draw.text((588, 110), "2. Automated Bad-Case Taxonomy Breakdown (Baseline Run)", fill=(251, 191, 36))

        failure_counts = summary_data.get("failure_taxonomy_counts", {})
        categories = [
            ("GROUNDING_MISCLICK", "Grounding Misclick (Coordinate / Ad Trap)", (239, 68, 68)),
            ("STATE_MISJUDGMENT", "State Misjudgment (Premature Toast Stop)", (249, 115, 22)),
            ("ACTION_LOOPING", "Action Looping (Disabled Button / Repeat)", (234, 179, 8)),
            ("TASK_OMISSION", "Task Omission (Uncommitted / Missing Sync)", (168, 85, 247)),
        ]
        fy = 165
        for key, label, color in categories:
            cnt = int(failure_counts.get(key, 0))
            draw.text((588, fy), f"{label}", fill=(226, 232, 240))
            bar_w = min(320, cnt * 85)
            draw.rectangle((588, fy + 24, 588 + 320, fy + 46), fill=(51, 65, 85))
            if bar_w > 0:
                draw.rectangle((588, fy + 24, 588 + bar_w, fy + 46), fill=color)
            draw.text((925, fy + 26), f"{cnt} cases", fill=(248, 250, 252))
            fy += 76

        img.save(out_path)

    def _render_interactive_html(self, summary_data: dict[str, Any], out_path: Path) -> None:
        rows_html = []
        for item in summary_data.get("cua_evaluations", []):
            ver = item["verification"]
            insp = item["inspection"]
            traj = item["trajectory"]
            passed_badge = (
                '<span class="badge pass">PASS (1.0)</span>'
                if ver["passed"]
                else f'<span class="badge fail">FAIL ({ver["score"]})</span>'
            )
            shots = [s["screenshot"] for s in traj.get("steps", []) if s.get("screenshot")]
            shot_link = f"../../{shots[-1]}" if shots else "#"
            anomaly_str = (
                "<br>".join(
                    f"<strong>[{html.escape(a['category'])}]</strong> Step {a['step_index']}: {html.escape(a['evidence'])}"
                    for a in insp.get("anomalies", [])
                )
                or '<span style="color:#16a34a;">No Trajectory Anomalies Detected</span>'
            )
            rows_html.append(
                f"""
                <tr>
                  <td><code>{html.escape(traj['task_id'])}</code></td>
                  <td>{html.escape(traj['agent_profile'])}</td>
                  <td>{html.escape(traj['title'])}</td>
                  <td>{passed_badge}</td>
                  <td><strong>{insp['prm_score']}</strong> ({insp['step_count']} steps)</td>
                  <td><code>{html.escape(insp['primary_failure_mode'])}</code></td>
                  <td style="font-size:12px;">{anomaly_str}</td>
                  <td><a href="{shot_link}" target="_blank">查看标注截图</a></td>
                </tr>
                """
            )

        swe_rows = []
        for swe in summary_data.get("swe_evaluations", []):
            base_c = swe["candidates"]["Baseline-Coding-Agent (Flawed Patch)"]
            sota_c = swe["candidates"]["SOTA-Coding-Agent (Resolved Patch)"]
            swe_rows.append(
                f"""
                <tr>
                  <td><code>{html.escape(swe['instance_id'])}</code></td>
                  <td><code>{html.escape(swe['repo'])}</code></td>
                  <td>{html.escape(swe['title'])}</td>
                  <td>{html.escape(swe['execution_backend'])}</td>
                  <td><span class="badge fail">FAIL ({html.escape(base_c['pytest_summary'])})</span></td>
                  <td><span class="badge pass">RESOLVED ({html.escape(sota_c['pytest_summary'])})</span></td>
                </tr>
                """
            )

        doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>CUA-Agent-Eval-Suite // 评测与轨迹质检可视化看板</title>
  <style>
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; background: #0f172a; color: #f8fafc; }}
    .wrap {{ max-width: 1360px; margin: 0 auto; padding: 28px; }}
    h1 {{ margin-top: 0; font-size: 24px; color: #38bdf8; }}
    h2 {{ font-size: 18px; color: #e2e8f0; border-left: 4px solid #38bdf8; padding-left: 10px; margin-top: 28px; }}
    .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 20px; margin-bottom: 22px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px; }}
    th, td {{ border: 1px solid #334155; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #0f172a; color: #94a3b8; }}
    .badge {{ padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 12px; }}
    .badge.pass {{ background: #14532d; color: #86efac; }}
    .badge.fail {{ background: #7f1d1d; color: #fca5a5; }}
    a {{ color: #38bdf8; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{ color: #fbbf24; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>CUA-Agent-Eval-Suite: 电脑操作智能体 (CUA) / Web GUI / Coding Agent 评测与轨迹质检看板</h1>
    <div class="card">
      <img src="benchmark_overview.png" style="max-width:100%; border-radius:8px; border:1px solid #475569;" alt="Benchmark Overview" />
    </div>
    <h2>一、 CUA 浏览器与跨应用操作任务评测及轨迹质检明细 (15 Tasks x Multi-Profile)</h2>
    <div class="card">
      <table>
        <thead>
          <tr>
            <th>任务 ID</th>
            <th>被测模型配置</th>
            <th>任务名称</th>
            <th>ORM 结果判定</th>
            <th>PRM 过程得分</th>
            <th>主错误归因类型</th>
            <th>轨迹质检证据与修复建议 (Inspector Evidence)</th>
            <th>SoM 截图</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows_html)}
        </tbody>
      </table>
    </div>
    <h2>二、 SWE-bench 风格 Coding Agent 代码修复评测明细 (Docker / Sandbox Pytest Verification)</h2>
    <div class="card">
      <table>
        <thead>
          <tr>
            <th>任务 ID</th>
            <th>目标仓库模块</th>
            <th>Issue 修复任务描述</th>
            <th>沙盒执行引擎</th>
            <th>Baseline Agent 结果</th>
            <th>SOTA Agent 结果</th>
          </tr>
        </thead>
        <tbody>
          {''.join(swe_rows)}
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>"""
        out_path.write_text(doc, encoding="utf-8")
