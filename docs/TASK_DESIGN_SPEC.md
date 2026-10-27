# CUA / GUI / Coding Agent 操作任务与评分标准（Rubric & Verifier）设计规范

本文档定义了 `CUA-Agent-Eval-Suite` 评测基准中 **15 个 CUA（电脑操作智能体 / Web GUI / 跨应用协同）任务** 与 **5 个 SWE-bench 风格 Coding Agent 代码修复任务** 的设计方法论、状态采集器（Getters）与结果/过程验证器（ORM & PRM Verifiers）规范。

---

## 一、 评测任务分层设计体系（对齐 OSWorld / Browser-Use / WorkArena）

为了全面评估智能体在真实业务场景下的电脑操作能力，我们将评测任务划分为四大维度：

| 任务编号区间 | 任务类别 | 核心考察能力 | 验证方式（Evaluator Type） |
| :--- | :--- | :--- | :--- |
| `CUA-WEB-01` ~ `05` | **企业级浏览器自动化** | 多条件筛选、动态弹窗确认、分页表格检索、IAM 权限勾选、监控告警配置 | `dom_and_backend_state` |
| `CUA-CROSS-06` ~ `11` | **跨应用协同操作 (Web ↔ OS/File/DB)** | 网页数据提取核算导出 CSV、读取本地 JSON 发布配置填入网页并回写回执、联合本地 SQLite 数据库分流 VIP 工单、抓取监控指标生成本地 Markdown 复盘报告、轮换密钥同步更新本地 `.env.production` | `hybrid_dom_and_file` / `hybrid_dom_and_sqlite` |
| `CUA-TRAP-12` ~ `15` | **抗干扰与典型错因压力测试** | 针对 **误点击、状态误判、重复操作、任务遗漏** 四大高频缺陷专门设计的对抗性 UI 靶场 | `dom_and_backend_state` + `TrajectoryInspector (PRM)` |
| `SWE-CUA-01` ~ `05` | **Coding Agent 代码修复评测** | 高分屏 DPI 坐标转换修复、死循环检测算法修复、Set-of-Marks 隐藏节点过滤、CSV 浮点容差校验器修复、PRM 漏提交封顶评分修复 | `docker_or_isolated_pytest_sandbox` |

---

## 二、 评分标准设计（Outcome Reward Model, ORM）

传统评测仅依赖大模型自评（LLM-as-a-Judge）容易出现幻觉。本仓库参考 `xlang-ai/OSWorld` 的 **Execution-based Verification（基于执行状态的确定性校验）**，设计了三类联合验证器（位于 [`src/evaluator/task_verifier.py`](../src/evaluator/task_verifier.py)）：

1. **DOM 终态断言（DOM Final State Getter）**
   - 在智能体终止任务后，直接读取页面关键状态节点（如 `#order-status-badge`、`#modal-confirmed`、`#firewall-commit-state`），校验是否真正触发后端状态变更，杜绝“只填表不提交”或“漏点二次确认弹窗”。
2. **跨应用本地文件产物校验（Cross-App File Artifact Verifier）**
   - **CSV 对账单校验（`CUA-CROSS-06`）**：解析本地导出的 `overdue_audit_2026.csv`，校验表头字段完整性、记录行数（过滤逾期 $\le 30$ 天的干扰行），并以 $\pm 0.01$ 浮点容差核对每笔逾期账单的 `5%` 滞纳金与应缴总额。
   - **JSON 结构化回执与日志校验（`CUA-CROSS-07 / 10 / 11 / 14`）**：验证 JSON Schema 必填字段与关键业务值（如 `receipt_id`、准入合格供应商计数 `onboarded_count == 3`、密钥前缀校验等）。
   - **Markdown 故障复盘报告校验（`CUA-CROSS-09`）**：验证生成的本地 `incident_postmortem.md` 是否完整包含 Top-3 报错接口路径与根因摘要章节。
3. **跨应用本地 SQLite 数据库状态校验（Cross-App SQLite Verifier）**
   - 在 `CUA-CROSS-08` 中，智能体必须先根据本地 `enterprise_crm.db` 的 `customer_contracts` 表识别出 `DIAMOND` 等级客户（`CUST-101` 与 `CUST-103`），不仅要在网页 CRM 端升级这两张工单，还必须向本地数据库 `ticket_escalation_audit` 表写入审计记录。评分器通过执行 SQL 查询 `SELECT COUNT(*) ...` 验证跨应用数据一致性。

---

## 三、 过程轨迹质检标准（Process Reward Model, PRM & 四大典型问题归因）

参考 `Tencent/CUARewardBench`，我们在 [`src/evaluator/trajectory_inspector.py`](../src/evaluator/trajectory_inspector.py) 中实现了结合 **Set-of-Marks (SoM) 标注截图、点击坐标、目标元素边界框（BBox）与动作轨迹序列** 的自动化质检器，重点识别以下四类问题：

1. **误点击（`GROUNDING_MISCLICK`）**
   - **判定规则**：动作类型为 `click` 时，实际点击像素坐标 $(x, y)$ 落在目标元素 `target_bbox` $[x_0, y_0, x_0+w, y_0+h]$ 之外（常见于高分屏 DPI 缩放偏移或归一化坐标换算错误）；或误触页面上的伪装推广按钮（如 `CUA-TRAP-12` 中的 `#btn-ad-trial-trap`）。
2. **状态误判（`STATE_MISJUDGMENT`）**
   - **判定规则**：智能体置位 `agent_claimed_success = True` 提前结束任务，但终态校验未通过，且页面存在异步中间态提示（如 `CUA-TRAP-13` 中点击提交后立即出现的蓝色 Toast `Request Sent`，1秒后实际返回 `ERR_MISSING_CHECKSUM`）。
3. **重复操作（`ACTION_LOOPING`）**
   - **判定规则**：
     - 对处于 `disabled` 禁用状态的按钮发起点击（如 `CUA-TRAP-14` 未勾选底部合规协议就直接点击 `#btn-export-archive`）；
     - 连续 $\ge 3$ 步对同一 DOM 选择器或欧氏距离 $\le 8\text{px}$ 的坐标发起重复点击且页面状态未发生改变；
     - 连续 $\ge 4$ 步执行滚动（`scroll`）但 `scroll_top` 保持不变。
4. **任务遗漏（`TASK_OMISSION`）**
   - **判定规则**：多阶段复合任务中完成了部分子目标（$0 < \text{passed\_checks} < \text{total\_checks}$），但遗漏了收尾持久化动作（如 `CUA-TRAP-15` 修改完 3 条防火墙规则后漏点顶部 `Apply & Persist All Changes`；或 `CUA-WEB-03` 漏点二次确认弹窗；或 `CUA-CROSS-08` 只操作了网页却漏写本地 SQLite 审计表）。
