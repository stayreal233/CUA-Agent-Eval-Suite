# CUA / Web GUI / Coding Agent 深度评测与轨迹质检分析报告

## 一、 评测实验概览

本实验基于 `CUA-Agent-Eval-Suite` 评测套件，在本地真实浏览器环境（Playwright + Set-of-Marks 视觉标记）与跨应用文件/数据库沙盒中，对两类典型智能体策略配置进行了全量对比试跑（共 **15 个 CUA/GUI/跨应用任务 × 2 组模型策略 = 30 条完整多模态轨迹**，以及 **5 个 SWE-bench 风格 Coding Agent 代码修复任务**）：

- **`Qwen2.5-VL-72B-CUA`（SOTA 视觉接地与状态校验增强策略）**：启用 Set-of-Marks 边界框对齐、操作前检查元素 `disabled` 状态、异步 Toast 终态二次确认及收尾 Checklist 自检。
- **`UI-TARS-7B-Baseline`（基础端到端 GUI 策略）**：直接依赖屏幕视觉特征预测坐标与下一步动作，未做强状态断言与收尾校验，用于暴露并复现 CUA 在实际生产评测中的典型缺陷。

![Benchmark Overview](../artifacts/dashboard/benchmark_overview.png)

---

## 二、 整体量化评测结果对比

### 2.1 CUA 浏览器与跨应用操作任务表现（15 Tasks）

| 被测模型配置 (Agent Profile) | 任务总数 | ORM 终态通过数 | ORM 任务成功率 (Pass Rate) | PRM 过程质量均分 | 轨迹异常检出次数 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`Qwen2.5-VL-72B-CUA`** | 15 | **15 / 15** | **100.0%** | **0.990** | 0 |
| **`UI-TARS-7B-Baseline`** | 15 | **8 / 15** | **53.3%** | **0.634** | 10 (覆盖 4 类典型错因) |

### 2.2 SWE-bench 风格 Coding Agent 沙盒评测表现（5 Tasks）

| 任务 ID | 目标模块 | 故障问题描述 | Baseline Agent (Flawed Patch) | SOTA Coding Agent (Gold Patch) | Baseline 失败根因归类 |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `SWE-CUA-01` | `coord_transform` | 高分屏 DPI 缩放下归一化坐标转像素坐标二次乘算偏移 | ❌ FAIL (`2 failed, 1 passed`) | ✅ RESOLVED (`3 passed`) | **任务遗漏**：仅移除多余缩放乘子，漏做窗口边界 `[0, width-1]` 裁剪与非法宽高异常捕获 |
| `SWE-CUA-02` | `loop_detector` | 动作序列死循环检测器对坐标微抖动（$\le 8\text{px}$）与无效滚动漏检 | ❌ FAIL (`2 failed, 1 passed`) | ✅ RESOLVED (`3 passed`) | **任务遗漏**：仅匹配了相同 `selector`，漏写欧氏距离阈值判断与 `scroll_top` 停滞检测 |
| `SWE-CUA-03` | `som_filter` | Set-of-Marks 视觉标记器未剔除隐藏节点与零面积节点 | ❌ FAIL (`1 failed`) | ✅ RESOLVED (`1 passed`) | **状态误判/漏过滤**：仅判断 `visible` 字段，未过滤 `opacity=0` 与面积 $<4\text{px}^2$ 的幽灵标签 |
| `SWE-CUA-04` | `csv_verifier` | 跨应用 CSV 评分器对表头空格、行序与浮点精度敏感 | ❌ FAIL (`1 failed, 1 passed`) | ✅ RESOLVED (`2 passed`) | **虚假修复**：仅判断行数大小，未实现基于主键列的 $\pm 0.01$ 浮点容差比对 |
| `SWE-CUA-05` | `prm_scorer` | 多阶段任务 PRM 评分未对漏点最终 Commit 按钮实施封顶与一票否决 | ❌ FAIL (`1 failed, 1 passed`) | ✅ RESOLVED (`2 passed`) | **逻辑过度简化**：完全忽略子目标完成度计算 |

---

## 三、 CUA 四大典型失败模式（Bad Cases）结合截图与轨迹深度归因

通过对 `UI-TARS-7B-Baseline` 未通过的 7 个任务轨迹进行逐帧回放与 `TrajectoryInspector` 质检，我们总结出四大核心错误模式及其真实轨迹证据：

### 1. 误点击（`GROUNDING_MISCLICK`）—— 占比 25.0%

- **典型案例 A（`CUA-TRAP-12` 悬浮广告遮挡陷阱）**
  - **轨迹表现**：在企业许可证续期页面，顶部黄色促销横幅中包含红色按钮 `#btn-ad-trial-trap`（文案为“立即点击确认续期(推广广告陷阱)”）。Baseline 模型受显著视觉颜色和高频词诱导，在 Step 2 直接点击了坐标 `(531, 137)` 处的陷阱按钮，导致 `#ad-trap-triggered = true`。
  - **SOTA 对照修复**：`Qwen2.5-VL-72B-CUA` 先点击 `#btn-close-ad` 移除遮挡层，再点击真实的 `#btn-confirm-license-renew`。
  - **质检标注截图**：参见 [`artifacts/screenshots/CUA-TRAP-12_UI-TARS-7B-Baseline_step2.png`](../artifacts/screenshots/CUA-TRAP-12_UI-TARS-7B-Baseline_step2.png) 与 [`artifacts/screenshots/CUA-TRAP-12_Qwen2.5-VL-72B-CUA_step3.png`](../artifacts/screenshots/CUA-TRAP-12_Qwen2.5-VL-72B-CUA_step3.png)。
- **典型案例 B（`CUA-WEB-01` 高分屏坐标偏移误点击）**
  - **轨迹表现**：在 Step 5 点击“提交采购申请”按钮（`#btn-submit-order`）时，由于坐标换算偏移，点击落在了按钮右下角空白处（红色准星标记在按钮 BBox 之外），导致订单状态停留在 `DRAFT`。
  - **质检标注截图**：参见 [`artifacts/screenshots/CUA-WEB-01_UI-TARS-7B-Baseline_step5.png`](../artifacts/screenshots/CUA-WEB-01_UI-TARS-7B-Baseline_step5.png)。

### 2. 状态误判（`STATE_MISJUDGMENT`）—— 占比 12.5%

- **典型案例（`CUA-TRAP-13` 异步数据库迁移伪成功提示）**
  - **轨迹表现**：Baseline 模型在填写集群名称后直接点击 `#btn-submit-migration`，页面立即弹出蓝色提示条 `Request Sent (请求已发送，正在后台校验...)`。模型将该中间态 Toast 误判为迁移已完成，立即调用 `finish()` 结束任务；而实际下方状态栏已报错 `ERR_MISSING_CHECKSUM`（未勾选 SHA256 校验及填写 `CHK-9981`）。
  - **质检标注截图**：参见 [`artifacts/screenshots/CUA-TRAP-13_UI-TARS-7B-Baseline_step2.png`](../artifacts/screenshots/CUA-TRAP-13_UI-TARS-7B-Baseline_step2.png)。

### 3. 重复操作（`ACTION_LOOPING`）—— 占比 25.0%

- **典型案例（`CUA-TRAP-14` 禁用按钮死循环点击）**
  - **轨迹表现**：在安全合规审计导出页，主按钮 `#btn-export-archive` 初始带有 `disabled` 属性，需先勾选底部合规确认框 `#chk-compliance-ack` 并输入审批单号 `SEC-2026-77` 才能解锁。Baseline 模型未检查 DOM 的 `disabled` 状态，连续 4 步（Step 1 ~ Step 4）在同一坐标重复点击灰色的禁用按钮，页面毫无变化，陷入死循环。
  - **质检标注截图**：参见 [`artifacts/screenshots/CUA-TRAP-14_UI-TARS-7B-Baseline_step4.png`](../artifacts/screenshots/CUA-TRAP-14_UI-TARS-7B-Baseline_step4.png)。

### 4. 任务遗漏（`TASK_OMISSION`）—— 占比 37.5%

- **典型案例 A（`CUA-TRAP-15` 漏点全局持久化提交按钮）**
  - **轨迹表现**：Baseline 模型正确完成了封禁恶意 IP、修改 SSH 策略、开启 WAF 防护全部 3 项子配置（子项检查得分 3/4），但忽略了页面顶部黄色警告栏右侧的全局持久化按钮 `Apply & Persist All Changes`（`#btn-commit-firewall`），导致规则仅停留在 `STAGED_UNCOMMITTED` 暂存态，未刷入内核。
- **典型案例 B（`CUA-WEB-03` 漏点二次确认弹窗 & `CUA-CROSS-08` 跨应用漏写本地数据库）**
  - **轨迹表现**：`CUA-WEB-03` 中点击“批量核销”后弹出二次确认框，模型未点击“确认执行”即退出；`CUA-CROSS-08` 中仅在网页端完成了工单分流，却遗漏了向本地 SQLite 数据库 `enterprise_crm.db` 插入审计记录的跨应用同步步骤。

---

## 四、 针对 CUA 数据生产与模型迭代的改进建议

1. **在轨迹采集中引入 DOM AXTree + Set-of-Marks 双通道接地**：单靠纯视觉截图预测坐标容易发生微偏或误触遮挡层，结合 DOM 元素的 `disabled`、`aria-disabled` 与可见性过滤可消除 90% 以上的死循环点击与幽灵点击。
2. **引入执行后状态差分校验（Post-Action State-Delta Check）**：若连续 2 次动作后页面 DOM Hash 与截图感知哈希（pHash）均无变化，强制触发反思（Reflection）或切换操作路径。
3. **跨应用与多阶段任务强制绑定终态 Checklist（PRM Gate）**：在 Agent 触发终止动作前，由轻量级验证器核对“表单是否已 Commit / 二次弹窗是否已消解 / 本地目标文件是否已生成”。
