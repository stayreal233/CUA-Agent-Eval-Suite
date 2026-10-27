"""
Enterprise Web & Cross-App Simulation Environment for CUA-Agent-Eval-Suite.
Provides 15 realistic enterprise web routes (ERP, ServiceDesk, Billing, IAM, Cloud Deploy,
CRM, Monitoring, Security Audit, and Adversarial UI Trap pages) for reproducible Playwright CUA testing.
"""

from __future__ import annotations

import argparse
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


BASE_CSS = """
<style>
  * { box-sizing: border-box; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; }
  body { margin: 0; background: #f3f6fb; color: #1e293b; }
  header { background: #0f172a; color: #f8fafc; padding: 12px 24px; display: flex; justify-content: space-between; align-items: center; }
  header .brand { font-weight: 700; font-size: 16px; letter-spacing: 0.4px; }
  header .nav-badge { background: #1e293b; padding: 4px 12px; border-radius: 6px; font-size: 13px; color: #38bdf8; }
  .container { max-width: 1120px; margin: 22px auto; background: #ffffff; border-radius: 10px; box-shadow: 0 4px 14px rgba(15,23,42,0.07); padding: 24px; border: 1px solid #e2e8f0; }
  h2 { margin-top: 0; font-size: 20px; color: #0f172a; border-bottom: 2px solid #f1f5f9; padding-bottom: 10px; }
  .card-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 14px; }
  .card { border: 1px solid #cbd5e1; border-radius: 8px; padding: 16px; background: #f8fafc; }
  .btn { display: inline-block; padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; font-weight: 600; font-size: 14px; background: #2563eb; color: white; margin-right: 8px; }
  .btn:disabled { background: #94a3b8; cursor: not-allowed; opacity: 0.65; }
  .btn-danger { background: #dc2626; }
  .btn-success { background: #16a34a; }
  .btn-warning { background: #d97706; }
  input, select, textarea { padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; width: 100%; margin-top: 4px; margin-bottom: 12px; }
  input[type="checkbox"] { width: auto; margin-right: 6px; transform: scale(1.15); }
  table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px; }
  th, td { border: 1px solid #e2e8f0; padding: 10px 12px; text-align: left; }
  th { background: #f1f5f9; font-weight: 600; }
  .status-box { margin-top: 16px; padding: 12px 16px; border-radius: 8px; background: #eff6ff; border: 1px solid #bfdbfe; font-weight: 600; }
  .ad-overlay { position: relative; border: 2px dashed #f59e0b; background: #fffbeb; padding: 14px; border-radius: 8px; margin-bottom: 14px; }
  .modal-box { display: none; margin-top: 14px; padding: 16px; border: 2px solid #2563eb; background: #f8fafc; border-radius: 8px; }
</style>
"""


def wrap_page(title: str, route: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(title)} - CUA Enterprise Benchmark Sandbox</title>
  {BASE_CSS}
</head>
<body>
  <header>
    <div class="brand">CUA-Enterprise-Suite // {html.escape(title)}</div>
    <div class="nav-badge">Route: {html.escape(route)}</div>
  </header>
  <div class="container">
    {body_html}
  </div>
</body>
</html>"""


def render_route(path: str, query: dict[str, list[str]]) -> str:
    if path == "/procurement":
        return wrap_page(
            "企业采购中心 (Procurement Portal)",
            path,
            """
            <h2>企业硬件与软件采购中心</h2>
            <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px;">
              <div>
                <label>商品分类 (Category)</label>
                <select id="filter-category">
                  <option value="ALL">全部 (ALL)</option>
                  <option value="Server_Hardware">服务器硬件 (Server_Hardware)</option>
                  <option value="Office_SaaS">办公软件 (Office_SaaS)</option>
                </select>
              </div>
              <div>
                <label>最高单价限制 (Max Price)</label>
                <input id="filter-max-price" type="number" value="10000" />
              </div>
              <div style="padding-top:22px;">
                <button id="btn-apply-filter" class="btn" onclick="document.getElementById('filter-applied').innerText='FILTERED_OK'">应用筛选</button>
                <span id="filter-applied" style="font-size:12px;color:#64748b;">UNFILTERED</span>
              </div>
            </div>
            <table>
              <thead><tr><th>SKU</th><th>商品名称</th><th>分类</th><th>单价(元)</th><th>数量</th><th>操作</th></tr></thead>
              <tbody>
                <tr>
                  <td>SKU-A100-80G</td><td>NVIDIA-A100-80GB-Card</td><td>Server_Hardware</td><td>68000</td>
                  <td><input id="qty-a100" type="number" value="1" style="width:70px;margin:0;" /></td>
                  <td><button id="btn-add-a100" class="btn btn-warning" onclick="selectSku('SKU-A100-80G', 'qty-a100')">加入采购车</button></td>
                </tr>
                <tr>
                  <td>SKU-NV-T4</td><td>NVIDIA-T4-Inference-Card</td><td>Server_Hardware</td><td>4600</td>
                  <td><input id="qty-t4" type="number" value="1" style="width:70px;margin:0;" /></td>
                  <td><button id="btn-add-t4" class="btn" onclick="selectSku('SKU-NV-T4', 'qty-t4')">加入采购车</button></td>
                </tr>
              </tbody>
            </table>
            <div class="status-box">
              当前已选 SKU: <span id="selected-sku">NONE</span> |
              数量: <span id="selected-qty">0</span> |
              订单状态: <span id="order-status-badge">DRAFT</span>
              <button id="btn-submit-order" class="btn btn-success" style="float:right;"
                onclick="document.getElementById('order-status-badge').innerText='SUBMITTED'">提交采购申请</button>
            </div>
            <script>
              function selectSku(sku, qtyId) {
                document.getElementById('selected-sku').innerText = sku;
                document.getElementById('selected-qty').innerText = document.getElementById(qtyId).value;
              }
            </script>
            """,
        )

    if path == "/servicedesk":
        return wrap_page(
            "ServiceDesk 生产故障工单中心",
            path,
            """
            <h2>新建生产环境故障工单 (Incident Ticket)</h2>
            <button id="btn-new-ticket" class="btn" onclick="document.getElementById('ticket-form').style.display='block'">新建工单</button>
            <div id="ticket-form" style="margin-top:16px;">
              <label>工单标题 (Incident Title)</label>
              <input id="input-ticket-title" type="text" placeholder="请输入故障标题..." />
              <label>故障优先级 (Priority)</label>
              <select id="select-priority">
                <option value="P2-Normal">P2-Normal</option>
                <option value="P1-High">P1-High</option>
                <option value="P0-Critical">P0-Critical</option>
              </select>
              <label>指派团队 (Assignee Group)</label>
              <select id="select-team">
                <option value="HelpDesk-L1">HelpDesk-L1</option>
                <option value="SRE-OnCall-Team">SRE-OnCall-Team</option>
                <option value="Network-Ops">Network-Ops</option>
              </select>
              <div>
                <label><input id="chk-sla-15m" type="checkbox" /> 启用 SLA 15分钟告警 (Enable 15m SLA Alert)</label>
              </div>
              <button id="btn-submit-ticket" class="btn btn-success" style="margin-top:12px;" onclick="submitTicket()">提交工单</button>
            </div>
            <div class="status-box">
              创建结果: <span id="ticket-created-msg">NONE</span> |
              指派团队: <span id="assigned-team-val">NONE</span> |
              SLA启用: <span id="sla-enabled-val">false</span>
            </div>
            <script>
              function submitTicket() {
                var title = document.getElementById('input-ticket-title').value;
                var prio = document.getElementById('select-priority').value;
                var team = document.getElementById('select-team').value;
                var sla = document.getElementById('chk-sla-15m').checked;
                if (title.indexOf('Redis') !== -1 && prio === 'P0-Critical') {
                  document.getElementById('ticket-created-msg').innerText = 'TICKET_CREATED_P0';
                } else {
                  document.getElementById('ticket-created-msg').innerText = 'TICKET_CREATED_OTHER';
                }
                document.getElementById('assigned-team-val').innerText = team;
                document.getElementById('sla-enabled-val').innerText = sla ? 'true' : 'false';
              }
            </script>
            """,
        )

    if path == "/billing":
        page = query.get("page", ["1"])[0]
        if page == "1":
            return wrap_page(
                "企业账单核销中心 - 第 1 页",
                f"{path}?page=1",
                """
                <h2>企业账单核销中心 (Page 1 / 2)</h2>
                <table>
                  <thead><tr><th>选择</th><th>账单号</th><th>状态</th><th>金额(元)</th></tr></thead>
                  <tbody>
                    <tr><td><input type="checkbox" id="chk-inv-001" /></td><td>INV-2026-001</td><td>PAID</td><td>3200</td></tr>
                    <tr><td><input type="checkbox" id="chk-inv-002" /></td><td>INV-2026-002</td><td>PENDING_VERIFY</td><td>450</td></tr>
                  </tbody>
                </table>
                <div style="margin-top:14px;">
                  <a id="link-next-page" class="btn" href="/billing?page=2">下一页 (Page 2) &raquo;</a>
                </div>
                """,
            )
        return wrap_page(
            "企业账单核销中心 - 第 2 页",
            f"{path}?page=2",
            """
            <h2>企业账单核销中心 (Page 2 / 2)</h2>
            <table>
              <thead><tr><th>选择</th><th>账单号</th><th>状态</th><th>金额(元)</th></tr></thead>
              <tbody>
                <tr><td><input type="checkbox" id="chk-inv-019" value="INV-2026-019" /></td><td>INV-2026-019</td><td>PENDING_VERIFY</td><td>2800</td></tr>
                <tr><td><input type="checkbox" id="chk-inv-021" value="INV-2026-021" /></td><td>INV-2026-021</td><td>PENDING_VERIFY</td><td>600</td></tr>
                <tr><td><input type="checkbox" id="chk-inv-023" value="INV-2026-023" /></td><td>INV-2026-023</td><td>PENDING_VERIFY</td><td>5400</td></tr>
              </tbody>
            </table>
            <div style="margin-top:14px;">
              <button id="btn-batch-verify" class="btn" onclick="document.getElementById('confirm-modal').style.display='block'">批量核销</button>
            </div>
            <div id="confirm-modal" class="modal-box">
              <p><strong>二次确认弹窗：</strong>确定核销所选高额账单吗？</p>
              <button id="btn-modal-confirm" class="btn btn-success" onclick="confirmBatch()">确认执行</button>
              <button id="btn-modal-cancel" class="btn btn-danger">取消</button>
            </div>
            <div class="status-box">
              核销结果: <span id="batch-verify-result">NONE</span> |
              弹窗确认: <span id="modal-confirmed">false</span>
            </div>
            <script>
              function confirmBatch() {
                var selected = [];
                if (document.getElementById('chk-inv-019').checked) selected.push('INV-2026-019');
                if (document.getElementById('chk-inv-021').checked) selected.push('INV-2026-021');
                if (document.getElementById('chk-inv-023').checked) selected.push('INV-2026-023');
                document.getElementById('batch-verify-result').innerText = 'VERIFIED:' + selected.join(',');
                document.getElementById('modal-confirmed').innerText = 'true';
              }
            </script>
            """,
        )

    if path == "/iam":
        return wrap_page(
            "IAM 统一身份与高危权限审计台",
            path,
            """
            <h2>员工权限审计与离职回收 (IAM Role Audit)</h2>
            <div style="display:flex; gap:10px;">
              <input id="input-emp-id" type="text" placeholder="输入员工工号，例如 EMP-8842" value="" />
              <button id="btn-search-emp" class="btn" onclick="document.getElementById('emp-panel').style.display='block'">检索员工</button>
            </div>
            <div id="emp-panel" style="margin-top:14px;">
              <p>员工: <strong>EMP-8842 (张某)</strong> | 当前人事状态: <span style="color:#dc2626;font-weight:700;">离职待回收 (Offboarding)</span></p>
              <div><label><input id="role-db-admin" type="checkbox" checked /> Prod-DB-Admin (高危生产库权限)</label></div>
              <div><label><input id="role-k8s-root" type="checkbox" checked /> K8s-Cluster-Root (高危容器集群权限)</label></div>
              <div><label><input id="role-archive-ro" type="checkbox" checked /> Archive-ReadOnly (只读归档保留)</label></div>
              <label style="margin-top:10px;display:block;">审计备注 (Audit Note)</label>
              <input id="input-audit-note" type="text" placeholder="填写审计备注..." />
              <button id="btn-save-iam" class="btn btn-success" onclick="saveIam()">保存权限变更</button>
            </div>
            <div class="status-box">
              变更状态: <span id="iam-save-status">UNCHANGED</span> |
              保留角色: <span id="remaining-role">ALL</span> |
              审计备注: <span id="audit-note-val">NONE</span>
            </div>
            <script>
              function saveIam() {
                var db = document.getElementById('role-db-admin').checked;
                var k8s = document.getElementById('role-k8s-root').checked;
                var ro = document.getElementById('role-archive-ro').checked;
                var note = document.getElementById('input-audit-note').value;
                if (!db && !k8s && ro) {
                  document.getElementById('iam-save-status').innerText = 'REVOKED_HIGH_PRIV';
                  document.getElementById('remaining-role').innerText = 'Archive-ReadOnly';
                } else {
                  document.getElementById('iam-save-status').innerText = 'INCOMPLETE_REVOKE';
                }
                document.getElementById('audit-note-val').innerText = note;
              }
            </script>
            """,
        )

    if path == "/monitor":
        return wrap_page(
            "APM 性能监控与慢查询告警中心",
            path,
            """
            <h2>接口延迟监控与告警静默配置</h2>
            <label>时间范围 (Time Range)</label>
            <select id="select-time-range">
              <option value="Last_1_Hour">Last_1_Hour</option>
              <option value="Last_24_Hours">Last_24_Hours</option>
            </select>
            <table>
              <thead><tr><th>接口路径 (Endpoint)</th><th>P99 延迟 (ms)</th><th>状态</th><th>操作</th></tr></thead>
              <tbody>
                <tr><td>/api/v1/user/profile</td><td>180 ms</td><td>NORMAL</td><td>-</td></tr>
                <tr><td>/api/v2/report/export</td><td>3420 ms</td><td>CRITICAL_SLOW</td>
                    <td><button id="btn-config-export-alert" class="btn btn-warning" onclick="selectEndpoint('/api/v2/report/export')">配置告警规则</button></td></tr>
              </tbody>
            </table>
            <div style="margin-top:16px;">
              <label>静默窗口 (Silence Window)</label>
              <select id="select-silence-window">
                <option value="5m">5m</option>
                <option value="15m">15m</option>
                <option value="30m">30m</option>
              </select>
              <button id="btn-save-alert-rule" class="btn btn-success" onclick="saveAlertRule()">保存告警规则</button>
            </div>
            <div class="status-box">
              目标接口: <span id="alert-rule-target">NONE</span> |
              静默窗口: <span id="silence-window">NONE</span> |
              规则状态: <span id="rule-saved-badge">INACTIVE</span>
            </div>
            <script>
              function selectEndpoint(ep) {
                document.getElementById('alert-rule-target').innerText = ep;
              }
              function saveAlertRule() {
                document.getElementById('silence-window').innerText = document.getElementById('select-silence-window').value;
                if (document.getElementById('alert-rule-target').innerText === '/api/v2/report/export') {
                  document.getElementById('rule-saved-badge').innerText = 'ACTIVE';
                }
              }
            </script>
            """,
        )

    if path == "/billing/overdue":
        return wrap_page(
            "跨应用财务对账：逾期账单数据源",
            path,
            """
            <h2>企业逾期应收账款明细表 (Overdue Invoices)</h2>
            <p>请提取逾期天数 <strong>&gt; 30 天</strong> 的账单，按 5% 计算滞纳金并导出至本地 CSV 文件。</p>
            <table id="overdue-table">
              <thead><tr><th>invoice_id</th><th>vendor</th><th>amount</th><th>overdue_days</th></tr></thead>
              <tbody>
                <tr data-overdue="45"><td>INV-901</td><td>TechSupply_Co</td><td>4000.00</td><td>45</td></tr>
                <tr data-overdue="12"><td>INV-902</td><td>FastLogistics</td><td>1200.00</td><td>12</td></tr>
                <tr data-overdue="60"><td>INV-904</td><td>CloudMatrix_Inc</td><td>8500.00</td><td>60</td></tr>
                <tr data-overdue="38"><td>INV-908</td><td>ApexHardware</td><td>1500.00</td><td>38</td></tr>
              </tbody>
            </table>
            <div class="status-box">
              页面数据状态: <span id="overdue-table-loaded">READY_FOR_EXTRACTION</span>
            </div>
            """,
        )

    if path == "/cloud/deploy":
        return wrap_page(
            "跨应用云原生发布控制台 (Cloud Deployment Console)",
            path,
            """
            <h2>生产微服务发布清单录入</h2>
            <label>服务名称 (Service Name)</label>
            <input id="input-service-name" type="text" placeholder="e.g. cua-gateway-service" />
            <label>容器镜像与 Tag (Container Image)</label>
            <input id="input-image-tag" type="text" placeholder="e.g. registry.internal/cua-router:v2.4.1" />
            <label>副本实例数 (Replicas)</label>
            <input id="input-replicas" type="number" value="1" />
            <button id="btn-trigger-deploy" class="btn btn-success" onclick="triggerDeploy()">触发生产发布 (Deploy Now)</button>
            <div class="status-box">
              发布状态: <span id="deploy-status">IDLE</span> |
              已部署镜像: <span id="deployed-image">NONE</span> |
              回执编号 (Receipt ID): <span id="deploy-receipt-id">NONE</span>
            </div>
            <script>
              function triggerDeploy() {
                var svc = document.getElementById('input-service-name').value;
                var img = document.getElementById('input-image-tag').value;
                if (svc === 'cua-gateway-service' && img.indexOf('v2.4.1') !== -1) {
                  document.getElementById('deploy-status').innerText = 'DEPLOY_SUCCESS';
                  document.getElementById('deployed-image').innerText = img;
                  document.getElementById('deploy-receipt-id').innerText = 'RCPT-20261027-8841';
                } else {
                  document.getElementById('deploy-status').innerText = 'DEPLOY_INVALID_PARAM';
                }
              }
            </script>
            """,
        )

    if path == "/crm/vip-tickets":
        return wrap_page(
            "跨应用 VIP 客户工单分流台 (CRM & Local SQLite Sync)",
            path,
            """
            <h2>VIP 客户待分流工单列表</h2>
            <p>请结合本地 SQLite 数据库 <code>enterprise_crm.db</code> 查询以下客户的真实签约等级（DIAMOND 级客户需升级至总裁办专班）。</p>
            <table>
              <thead><tr><th>工单号</th><th>客户编码 (cust_id)</th><th>问题摘要</th><th>升级勾选</th></tr></thead>
              <tbody>
                <tr><td>TCK-501</td><td>CUST-101</td><td>核心支付网关偶发 502</td><td><input id="chk-tck-501" type="checkbox" /></td></tr>
                <tr><td>TCK-502</td><td>CUST-102</td><td>报表导出样式微调咨询</td><td><input id="chk-tck-502" type="checkbox" /></td></tr>
                <tr><td>TCK-503</td><td>CUST-103</td><td>专线跨区同步延迟告警</td><td><input id="chk-tck-503" type="checkbox" /></td></tr>
              </tbody>
            </table>
            <label style="margin-top:12px;display:block;">目标处理组 (Escalation Group)</label>
            <select id="select-escalation-group">
              <option value="Standard-Support">Standard-Support</option>
              <option value="Director-Escalation-Group">Director-Escalation-Group</option>
            </select>
            <button id="btn-escalate-vip" class="btn btn-success" onclick="escalateVip()">提交分流并同步</button>
            <div class="status-box">
              分流状态: <span id="vip-escalation-status">PENDING</span>
            </div>
            <script>
              function escalateVip() {
                var c1 = document.getElementById('chk-tck-501').checked;
                var c2 = document.getElementById('chk-tck-502').checked;
                var c3 = document.getElementById('chk-tck-503').checked;
                var grp = document.getElementById('select-escalation-group').value;
                if (c1 && !c2 && c3 && grp === 'Director-Escalation-Group') {
                  document.getElementById('vip-escalation-status').innerText = 'ESCALATED_2_DIAMOND_TICKETS';
                } else {
                  document.getElementById('vip-escalation-status').innerText = 'ESCALATION_MISMATCH';
                }
              }
            </script>
            """,
        )

    if path == "/monitor/incidents":
        return wrap_page(
            "跨应用故障复盘采集台 (Incident Metrics Source)",
            path,
            """
            <h2>生产环境 Top-3 异常接口故障汇总</h2>
            <table id="incident-table">
              <thead><tr><th>排名</th><th>接口名称 (Endpoint)</th><th>5xx 报错数</th><th>根因摘要 (Root Cause Summary)</th></tr></thead>
              <tbody>
                <tr><td>1</td><td>/api/v1/payment/charge</td><td>1420</td><td>Upstream bank TLS handshake timeout under burst traffic</td></tr>
                <tr><td>2</td><td>/api/v2/auth/token</td><td>890</td><td>Redis session pool connection exhaustion</td></tr>
                <tr><td>3</td><td>/api/v1/inventory/lock</td><td>530</td><td>Deadlock on SKU row-level pessimistic lock</td></tr>
              </tbody>
            </table>
            <button id="btn-archive-postmortem" class="btn btn-success" style="margin-top:14px;"
              onclick="document.getElementById('postmortem-archived').innerText='true'">标记复盘已归档</button>
            <div class="status-box">
              复盘归档状态: <span id="postmortem-archived">false</span>
            </div>
            """,
        )

    if path == "/vendors/onboarding":
        return wrap_page(
            "跨应用供应商批量准入系统 (Vendor Onboarding)",
            path,
            """
            <h2>合格供应商批量入库 (信用分 &ge; 60 准入)</h2>
            <label>供应商名称 (Vendor Name)</label>
            <input id="input-vendor-name" type="text" placeholder="输入供应商名称" />
            <label>信用评分 (Credit Score)</label>
            <input id="input-vendor-score" type="number" value="80" />
            <button id="btn-add-vendor" class="btn" onclick="addVendor()">录入合格供应商</button>
            <ul id="vendor-list"></ul>
            <div class="status-box">
              已成功入库合格供应商数量: <span id="onboarded-vendor-count">0</span>
            </div>
            <script>
              var onboarded = [];
              function addVendor() {
                var name = document.getElementById('input-vendor-name').value.trim();
                var score = parseInt(document.getElementById('input-vendor-score').value, 10);
                if (name && score >= 60 && onboarded.indexOf(name) === -1) {
                  onboarded.push(name);
                  var li = document.createElement('li');
                  li.innerText = name + ' (Score: ' + score + ')';
                  document.getElementById('vendor-list').appendChild(li);
                  document.getElementById('onboarded-vendor-count').innerText = String(onboarded.length);
                }
              }
            </script>
            """,
        )

    if path == "/dev/apikeys":
        return wrap_page(
            "跨应用开发者密钥轮换中心 (API Key Rotation)",
            path,
            """
            <h2>生产环境网关密钥管理</h2>
            <p>当前旧密钥指纹 (Old Key Fingerprint): <code id="old-key-fp">fp-2025-legacy-992a</code></p>
            <button id="btn-rotate-key" class="btn btn-warning" onclick="rotateKey()">轮换生产密钥 (Rotate Key)</button>
            <div class="status-box">
              轮换状态: <span id="key-rotation-state">ACTIVE_LEGACY</span> |
              新生成密钥: <code id="new-api-key-val">NOT_GENERATED</code>
            </div>
            <script>
              function rotateKey() {
                document.getElementById('key-rotation-state').innerText = 'ROTATED_ACTIVE';
                document.getElementById('new-api-key-val').innerText = 'sk-cua-prod-2026-99887766aabbcc';
              }
            </script>
            """,
        )

    if path == "/license/renew":
        return wrap_page(
            "【抗干扰靶场-误点击测试】企业许可证续期中心",
            path,
            """
            <h2>企业级无限许可证续期 (Enterprise License Renewal)</h2>
            <div id="ad-banner" class="ad-overlay">
              <strong style="color:#b45309;">[限时推广弹窗遮挡区]</strong> 升级个人试用推广包立减 99%！
              <button id="btn-ad-trial-trap" class="btn btn-danger"
                onclick="document.getElementById('ad-trap-triggered').innerText='true'; document.getElementById('license-renew-status').innerText='MISCLICKED_AD_TRAP';">
                立即点击确认续期(推广广告陷阱)
              </button>
              <button id="btn-close-ad" class="btn" style="background:#475569;"
                onclick="document.getElementById('ad-banner').style.display='none'">关闭广告遮挡 [X]</button>
            </div>
            <label>选择续期套餐 (License Plan)</label>
            <select id="select-license-plan">
              <option value="Starter-Plan">Starter-Plan</option>
              <option value="Enterprise-Unlimited-Plan">Enterprise-Unlimited-Plan</option>
            </select>
            <button id="btn-confirm-license-renew" class="btn btn-success"
              onclick="if(document.getElementById('select-license-plan').value==='Enterprise-Unlimited-Plan'){document.getElementById('license-renew-status').innerText='RENEWED_ENTERPRISE_UNLIMITED';}">
              正式确认企业无限版续期 (#btn-confirm-license-renew)
            </button>
            <div class="status-box">
              续期状态: <span id="license-renew-status">PENDING</span> |
              是否误触广告陷阱: <span id="ad-trap-triggered">false</span>
            </div>
            """,
        )

    if path == "/db/migration":
        return wrap_page(
            "【抗干扰靶场-状态误判测试】异步数据库集群迁移台",
            path,
            """
            <h2>生产数据库在线迁移控制台 (Async Schema Migration)</h2>
            <label>目标集群名称 (Target Cluster)</label>
            <input id="input-target-cluster" type="text" placeholder="cluster-prod-02" />
            <div id="checksum-section" style="padding:12px; border:1px solid #cbd5e1; border-radius:6px; margin-bottom:12px;">
              <label><input id="chk-enable-sha256" type="checkbox" /> 启用 SHA256 一致性校验 (Required for Production)</label>
              <label style="display:block;margin-top:8px;">校验码 (Verification Checksum)</label>
              <input id="input-checksum-code" type="text" placeholder="CHK-9981" />
            </div>
            <button id="btn-submit-migration" class="btn btn-success" onclick="submitMigration()">提交迁移任务</button>
            <div id="toast-banner" class="status-box" style="background:#dbeafe;">
              即时提示 (Toast): <span id="toast-msg">IDLE</span>
            </div>
            <div class="status-box">
              最终异步校验状态: <span id="migration-final-state">NOT_STARTED</span> |
              已验证校验码: <span id="checksum-verified">NONE</span>
            </div>
            <script>
              function submitMigration() {
                document.getElementById('toast-msg').innerText = 'Request Sent (请求已发送，正在后台校验...)';
                var chk = document.getElementById('chk-enable-sha256').checked;
                var code = document.getElementById('input-checksum-code').value.trim();
                if (!chk || code !== 'CHK-9981') {
                  document.getElementById('migration-final-state').innerText = 'ERR_MISSING_CHECKSUM';
                } else {
                  document.getElementById('migration-final-state').innerText = 'MIGRATION_VERIFIED_OK';
                  document.getElementById('checksum-verified').innerText = code;
                }
              }
            </script>
            """,
        )

    if path == "/security/audit-export":
        return wrap_page(
            "【抗干扰靶场-重复操作测试】加密安全审计归档导出",
            path,
            """
            <h2>安全合规加密日志导出 (Encrypted Audit Export)</h2>
            <p>注意：未完成底部合规勾选与审批单号录入前，下方导出按钮处于 <code>disabled</code> 禁用状态。</p>
            <button id="btn-export-archive" class="btn btn-success" disabled onclick="doExport()">导出加密审计归档 (#btn-export-archive)</button>
            <div style="height:120px; background:#f8fafc; border:1px dashed #cbd5e1; margin:16px 0; padding:12px;">
              安全合规条例声明区：导出生产环境加密审计日志需经安全官审批并勾选合规确认书。
            </div>
            <div>
              <label><input id="chk-compliance-ack" type="checkbox" onchange="checkUnlock()" /> 我已阅读并遵守《数据安全合规协议》 (#chk-compliance-ack)</label>
              <label style="display:block;margin-top:8px;">安全审批单号 (Approval Code)</label>
              <input id="input-approval-code" type="text" placeholder="SEC-2026-77" oninput="checkUnlock()" />
            </div>
            <div class="status-box">
              合规勾选状态: <span id="compliance-ack-state">unchecked</span> |
              导出状态: <span id="export-status">LOCKED</span>
            </div>
            <script>
              function checkUnlock() {
                var ack = document.getElementById('chk-compliance-ack').checked;
                var code = document.getElementById('input-approval-code').value.trim();
                document.getElementById('compliance-ack-state').innerText = ack ? 'checked' : 'unchecked';
                document.getElementById('btn-export-archive').disabled = !(ack && code === 'SEC-2026-77');
              }
              function doExport() {
                document.getElementById('export-status').innerText = 'EXPORT_COMPLETED';
              }
            </script>
            """,
        )

    if path == "/firewall/rules":
        return wrap_page(
            "【抗干扰靶场-任务遗漏测试】多阶段边界防火墙策略管理台",
            path,
            """
            <div style="display:flex; justify-content:space-between; align-items:center; background:#fef3c7; padding:10px 16px; border-radius:8px; margin-bottom:16px;">
              <span><strong>全局暂存区提示：</strong>所有规则修改仅保存在暂存区，离开前必须点击右侧按钮持久化生效！</span>
              <button id="btn-commit-firewall" class="btn btn-danger"
                onclick="document.getElementById('firewall-commit-state').innerText='COMMITTED_TO_KERNEL'">
                Apply &amp; Persist All Changes
              </button>
            </div>
            <h2>边界防火墙策略配置 (3 项子任务 + 1 项全局提交)</h2>
            <label>1. 封禁恶意 CIDR 网段 (Block Malicious IP CIDR)</label>
            <input id="input-block-cidr" type="text" placeholder="198.51.100.0/24"
              oninput="document.getElementById('rule-ip-block').innerText=this.value" />
            <label>2. SSH 22 端口访问策略 (SSH Access Policy)</label>
            <select id="select-ssh-policy" onchange="document.getElementById('rule-ssh-policy').innerText=this.value">
              <option value="Public-Open">Public-Open</option>
              <option value="Internal-VPN-Only">Internal-VPN-Only</option>
            </select>
            <div>
              <label><input id="chk-waf-sqli" type="checkbox"
                onchange="document.getElementById('rule-waf-sqli').innerText=this.checked?'ENABLED':'DISABLED'" />
                3. 开启 WAF SQL 注入防护 (Enable WAF SQLi Protection)</label>
            </div>
            <div class="status-box">
              IP封禁: <span id="rule-ip-block">NONE</span> |
              SSH策略: <span id="rule-ssh-policy">Public-Open</span> |
              WAF防护: <span id="rule-waf-sqli">DISABLED</span> |
              内核持久化状态: <span id="firewall-commit-state">STAGED_UNCOMMITTED</span>
            </div>
            """,
        )

    return wrap_page(
        "CUA Enterprise Benchmark Index",
        path,
        "<h2>CUA-Agent-Eval-Suite Mock Enterprise Environment is Running.</h2>",
    )


class MockEnvRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        content = render_route(parsed.path, query).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args) -> None:
        return


def start_background_server(host: str = "127.0.0.1", port: int = 18920) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), MockEnvRequestHandler)
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start CUA Enterprise Benchmark Mock Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18920)
    args = parser.parse_args()
    srv = start_background_server(args.host, args.port)
    print(f"CUA Enterprise Mock Server listening on http://{args.host}:{args.port}")
    srv.serve_forever()
