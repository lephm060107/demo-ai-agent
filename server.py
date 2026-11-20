"""
server.py
UNIFIED BACKEND SERVER — NEXUS ANALYTICS (Universal AI-Powered Business Data Analytics & B2B RFQ Intelligence Platform)
Hợp nhất toàn diện:
1. Universal Data Analytics Platform (Ingestion, Multi-sheet Preview, Profiling, Quality, Cleaning, Versioning, 4-Level Analytics, ECharts, AI Agent, Reporting, RBAC).
2. B2B RFQ & Commercial Intelligence Module (Thiên Minh 6 Phases - 12 Steps - 5 Decision Gates - 4 Custom Skills - 4 Tools - HITL Approval - BoQ & Proposal Cover Page).
"""

import os
import json
import pandas as pd
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from nexus_analytics.core.config import settings
from nexus_analytics.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    check_role_permission,
    check_decision_permission,
    DECISION_ROLE_PERMISSIONS,
)
from nexus_analytics.db.database import db, new_uuid, now_iso
from nexus_analytics.services.ingestion_service import ingestion_service
from nexus_analytics.services.profiling_service import profiling_service
from nexus_analytics.services.quality_engine import quality_engine
from nexus_analytics.services.analytics_engine import analytics_engine
from nexus_analytics.services.ai_agent_orchestrator import ai_agent_orchestrator
from nexus_analytics.services.reporting_service import reporting_service, REPORT_SECTIONS_14_CATALOG
from nexus_analytics.services.platform_manager import platform_manager
from nexus_analytics.services.rfq_workflow_service import rfq_workflow_service
from nexus_analytics.services.version_lifecycle_service import (
    version_lifecycle_service,
    get_user_permissions,
    compute_bytes_sha256,
)
from nexus_analytics.services.semantic_gatekeeper_service import evaluate_workflow_gate
from nexus_analytics.services.profiling_service import is_text_series
from nexus_analytics.services.strategic_toolkit_service import (
    TOOLKIT_CATALOG,
    compute_analysis_readiness,
    recommend_analytical_methods,
    strategic_toolkit_service,
)
from nexus_analytics.services.decision_center_service import decision_center_service
from nexus_analytics.services.chart_intelligence_service import (
    detect_default_chart_config,
    build_custom_chart,
    get_chart_drilldown_rows,
)

app = FastAPI(
    title="NEXUS ANALYTICS – Universal AI Business Data Analytics & B2B RFQ Platform",
    version="2.0.0",
    description="Unified Enterprise SaaS Platform combining Universal Multi-Domain BI Analytics and Autonomous B2B RFQ Workflow Intelligence."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# UNIFIED REQUEST SCHEMAS
# =============================================================================
class ChartBuildRequest(BaseModel):
    dataset_id: str
    version_id: Optional[str] = None
    x_col: Optional[str] = None
    y_col: Optional[str] = None
    series_col: Optional[str] = None
    aggregation: str = "SUM"
    chart_type: str = "auto"
    sort_dir: str = "desc"
    filter_col: Optional[str] = None
    filter_val: Optional[str] = None
    date_col: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    color_mode: str = "rainbow_pastel"
    language: str = "vi"


class ChartDrilldownRequest(BaseModel):
    dataset_id: str
    version_id: Optional[str] = None
    filter_col: str
    filter_val: str
    limit: int = 100


class LoginRequest(BaseModel):
    email: str
    password: str = "nexus123"


class CreateProjectRequest(BaseModel):
    workspace_id: str = "ws-enterprise-001"
    name: str
    description: str = ""
    business_domain: str = "General Business"


class KpiDefinitionRequest(BaseModel):
    name: str
    definition: Optional[str] = None
    column: str
    secondary_column: Optional[str] = None
    agg: str = "sum"
    unit: str = "VND"
    formula: Optional[str] = None
    data_source: Optional[str] = None
    filters: Optional[str] = None
    time_range: Optional[str] = None
    missing_value_rule: Optional[str] = "exclude_nulls"


class ConfirmImportRequest(BaseModel):
    staging_id: str
    project_id: str = "proj-omni-001"
    dataset_name: Optional[str] = None
    selected_sheet: Optional[str] = None
    action: str = "NEW_DATASET"
    target_dataset_id: Optional[str] = None
    confirm_schema_change: bool = False
    report_type: str = "General Business"


class ArchiveDatasetRequest(BaseModel):
    reason: str = ""


class PermanentDeleteRequest(BaseModel):
    confirm: bool = False
    force_delete_referenced: bool = False


class TrashDatasetRequest(BaseModel):
    reason: str = ""
    confirm_referenced: bool = False


class ToolkitRunRequest(BaseModel):
    project_id: str = "proj-omni-001"
    dataset_id: str
    version_id: Optional[str] = None
    method_id: str = "pareto_root_cause"
    parameters: Dict[str, Any] = {}


class RecommendToolsRequest(BaseModel):
    dataset_id: str
    version_id: Optional[str] = None
    business_goal: str = ""


class CompareAnalyticsRequest(BaseModel):
    version_a_id: str
    version_b_id: str
    method_name: str = "summary_stats"
    metric_col: Optional[str] = None
    dimension_col: Optional[str] = None


class UpdateColumnRoleRequest(BaseModel):
    column_name: str
    semantic_role: str


class ColumnConfirmationItem(BaseModel):
    column_name: str
    status: str  # CONFIRMED_BUSINESS_DATA | CONFIRMED_SEQUENCE_INDEX | CONFIRMED_SPECIAL_CASE | UNRESOLVED
    unit: str = ""
    note: str = ""


class ConfirmColumnsRequest(BaseModel):
    confirmations: List[ColumnConfirmationItem]


class QualityWeightsRequest(BaseModel):
    completeness: float = 0.35
    uniqueness: float = 0.20
    validity: float = 0.25
    consistency: float = 0.20


class CleaningRequest(BaseModel):
    mode: str = "AI_ASSISTED"
    rules: List[Dict[str, Any]]


class RunAnalysisRequest(BaseModel):
    project_id: str = "proj-omni-001"
    dataset_id: str
    version_id: Optional[str] = None
    method_name: Optional[str] = None
    analysis_type: Optional[str] = None
    analysis_goal: Optional[str] = None
    metric_col: Optional[str] = None
    dimension_col: Optional[str] = None
    secondary_col: Optional[str] = None
    window: Optional[int] = None
    periods: Optional[int] = None
    granularity: Optional[str] = None
    language: str = "vi"
    parameters: Dict[str, Any] = {}


class AIChatRequest(BaseModel):
    project_id: str = "proj-omni-001"
    dataset_id: str
    version_id: Optional[str] = None
    analysis_run_id: Optional[str] = None
    question: Optional[str] = None
    prompt: Optional[str] = None
    language: str = "vi"
    rfq_context: Optional[Dict[str, Any]] = None


class AddWidgetRequest(BaseModel):
    dashboard_id: str = "dash-exec-001"
    widget_type: str = "CHART"
    title: str
    width_cols: int = 6
    config: Dict[str, Any]


class CreateDashboardRequest(BaseModel):
    project_id: str = "proj-omni-001"
    name: str
    description: str = ""


class GenerateReportRequest(BaseModel):
    project_id: str = "proj-omni-001"
    dataset_id: str
    version_id: Optional[str] = None
    analysis_run_id: Optional[str] = None
    report_type: str = "EXECUTIVE"
    language: str = "vi"
    title: Optional[str] = None
    author: Optional[str] = None
    custom_recommendations: Optional[str] = None
    sections_selected: Optional[List[str]] = None


class UserPreferenceRequest(BaseModel):
    preferred_language: str = "vi"
    full_name: Optional[str] = None
    user_id: Optional[str] = None


class CreateUserRequest(BaseModel):
    email: str
    full_name: str
    password: str = "nexus123"
    role: str = "ANALYST"
    preferred_language: str = "vi"


class UpdateUserRequest(BaseModel):
    default_role: Optional[str] = None
    is_active: Optional[int] = None
    preferred_language: Optional[str] = None


class WorkspaceRequest(BaseModel):
    name: str
    industry_context: str = "Universal Multi-Domain"


class PartnerRequest(BaseModel):
    partner_type: str  # CUSTOMER | SUPPLIER
    name: str
    code: Optional[str] = None
    contact_person: str = ""
    email: str = ""
    phone: str = ""
    region: str = ""
    category: str = ""
    sla_tier: str = "Standard"
    lead_time_days: int = 3
    notes: str = ""


class ProcurementCreateRequest(BaseModel):
    rfq_run_id: Optional[str] = None
    customer_name: str
    supplier_name: str
    sku_summary: str
    total_cost: float = 0.0
    expected_delivery_date: str = ""
    assigned_engineer: str = ""
    status: str = "ORDERED"
    notes: str = ""


class ProcurementStatusRequest(BaseModel):
    status: str
    notes: Optional[str] = None


class GoogleSheetsRequest(BaseModel):
    url: str


class ProcessRfpRequest(BaseModel):
    text: str
    custom_discount: Optional[float] = None
    source_type: Optional[str] = "TEXT"


class ManagerDecisionRequest(BaseModel):
    decision: str  # "APPROVED", "REJECTED", "ADJUST"
    comment: str = ""


# =============================================================================
# AUTH & RBAC GUARD
# =============================================================================
def get_current_user(x_nexus_role: Optional[str] = "ADMIN", authorization: Optional[str] = None) -> Dict[str, Any]:
    if isinstance(authorization, str) and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        decoded = decode_access_token(token)
        if decoded:
            return decoded
    role = (x_nexus_role if isinstance(x_nexus_role, str) else "ADMIN").upper()
    role_defaults = {
        "ADMIN": ("u-admin-001", "ceo@nexus.ai"),
        "CEO": ("u-ceo-004", "exec@nexus.ai"),
        "EXECUTIVE": ("u-ceo-004", "exec@nexus.ai"),
        "STRATEGIC_MANAGER": ("u-strat-005", "strategy@nexus.ai"),
        "DEPARTMENT_MANAGER": ("u-dept-006", "dept@nexus.ai"),
        "ANALYST": ("u-analyst-002", "analyst@nexus.ai"),
        "VIEWER": ("u-viewer-003", "viewer@nexus.ai"),
    }
    sub, email = role_defaults.get(role, ("u-admin-001", "ceo@nexus.ai"))
    return {"sub": sub, "email": email, "role": role, "workspace_id": "ws-enterprise-001"}


def _get_workspace_feature_flags(workspace_id: str = "ws-enterprise-001") -> Dict[str, Any]:
    flags = {"rfq_module_enabled": bool(settings.FEATURE_RFQ_MODULE)}
    try:
        with db.get_conn() as conn:
            row = conn.execute("SELECT feature_flags_json FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()
            if row and row["feature_flags_json"]:
                saved = json.loads(row["feature_flags_json"])
                if isinstance(saved, dict):
                    flags.update(saved)
    except Exception:
        pass
    return flags


def require_role(user: Dict[str, Any], min_role: str):
    if not check_role_permission(user.get("role", "VIEWER"), min_role):
        raise HTTPException(
            status_code=403,
            detail=f"RBAC Access Denied: Vai trò '{user.get('role')}' không có quyền thực hiện thao tác yêu cầu quyền '{min_role}'."
        )


# =============================================================================
# UNIFIED WEB FRONTEND
# =============================================================================
@app.get("/", response_class=HTMLResponse)
async def serve_unified_home():
    html_path = os.path.join(settings.BASE_DIR, "static", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


# =============================================================================
# 1. AUTHENTICATION, BOOTSTRAP, WORKSPACE & PROJECT ENDPOINTS
# =============================================================================
@app.post("/api/v1/auth/login")
async def login(req: LoginRequest):
    with db.get_conn() as conn:
        u = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (req.email.lower().strip(),)).fetchone()
        if not u or not verify_password(req.password, u["password_hash"]):
            raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không chính xác.")
        member = conn.execute("SELECT * FROM workspace_members WHERE user_id = ? LIMIT 1", (u["id"],)).fetchone()
        ws_id = member["workspace_id"] if member else "ws-enterprise-001"
        role = member["role"] if member else u["default_role"]

    token = create_access_token(u["id"], u["email"], role, ws_id)
    db.log_audit("USER_LOGIN", "user", u["id"], {"email": u["email"], "role": role}, workspace_id=ws_id, user_id=u["id"])
    return {
        "success": True,
        "access_token": token,
        "user": {"id": u["id"], "email": u["email"], "full_name": u["full_name"], "role": role, "workspace_id": ws_id}
    }


@app.get("/api/v1/bootstrap")
async def bootstrap_state(x_nexus_role: Optional[str] = Header(default="ADMIN"), authorization: Optional[str] = Header(default=None)):
    platform_manager._ensure_sample_benchmark_dataset()
    current_user = get_current_user(x_nexus_role, authorization)
    with db.get_conn() as conn:
        users = [dict(r) for r in conn.execute("SELECT id, email, full_name, default_role, is_active, preferred_language FROM users").fetchall()]
        active_u = next((u for u in users if u["id"] == current_user.get("sub")), users[0] if users else None)
        workspaces = [dict(r) for r in conn.execute("SELECT * FROM workspaces ORDER BY created_at ASC").fetchall()]
        projects = [dict(r) for r in conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()]
        for p in projects:
            p["kpi_definitions"] = json.loads(p.get("kpi_definitions_json") or "[]")
        datasets = [dict(r) for r in conn.execute("SELECT * FROM datasets ORDER BY created_at DESC").fetchall()]
        dashboards = [dict(r) for r in conn.execute("SELECT * FROM dashboards ORDER BY created_at DESC").fetchall()]
        for d in dashboards:
            widgets = [dict(w) for w in conn.execute(
                "SELECT * FROM dashboard_widgets WHERE dashboard_id = ? ORDER BY position_order ASC", (d["id"],)
            ).fetchall()]
            for w in widgets:
                w["config"] = json.loads(w.get("config_json") or "{}")
            d["widgets"] = widgets
        reports = [dict(r) for r in conn.execute("SELECT id, project_id, dataset_version_id, report_type, title, created_at FROM reports ORDER BY created_at DESC").fetchall()]
        audit_logs = [dict(r) for r in conn.execute("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 60").fetchall()]
        recent_analyses = [dict(r) for r in conn.execute("SELECT id, project_id, dataset_version_id, analytics_level, method_name, formula_used, duration_ms, created_at FROM analysis_runs ORDER BY created_at DESC LIMIT 20").fetchall()]
        ai_history = [dict(r) for r in conn.execute("SELECT id, conversation_id, role, content, created_at FROM ai_messages ORDER BY created_at DESC LIMIT 30").fetchall()]
        partners = [dict(r) for r in conn.execute("SELECT * FROM rfq_partners ORDER BY partner_type ASC, created_at DESC").fetchall()]
        procurement = [dict(r) for r in conn.execute("SELECT * FROM rfq_procurement ORDER BY created_at DESC LIMIT 40").fetchall()]

    non_rej_datasets = [d for d in datasets if d.get("validation_status") != "REJECTED" and not d.get("is_deleted") and d.get("current_version_id")]
    active_ds_bundle = platform_manager.get_dataset_bundle(non_rej_datasets[0]["id"]) if non_rej_datasets else None
    ds_listing = version_lifecycle_service.list_datasets_filtered(area="ALL", page=1, page_size=50)
    cur_role = str(current_user.get("role") or "ADMIN").upper()
    return {
        "active_user": active_u,
        "permissions": get_user_permissions(cur_role),
        "decision_permissions": sorted(list(DECISION_ROLE_PERMISSIONS.get(cur_role, DECISION_ROLE_PERMISSIONS["VIEWER"]))),
        "feature_flags": _get_workspace_feature_flags(),
        "toolkit_catalog": TOOLKIT_CATALOG,
        "report_sections_catalog": REPORT_SECTIONS_14_CATALOG,
        "preferred_language": active_u.get("preferred_language", "vi") if active_u else "vi",
        "users": users,
        "workspaces": workspaces,
        "projects": projects,
        "datasets": ds_listing["datasets"],
        "dataset_counts": ds_listing["counts"],
        "active_dataset_bundle": active_ds_bundle,
        "dashboards": dashboards,
        "reports": reports,
        "audit_logs": audit_logs,
        "recent_analyses": recent_analyses,
        "ai_history": ai_history,
        "rfq_history": rfq_workflow_service.get_rfq_history(),
        "rfq_partners": partners,
        "rfq_procurement": procurement
    }


@app.post("/api/v1/user/preferences")
async def save_user_preferences(
    req: UserPreferenceRequest,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    lang = req.preferred_language.lower().strip()
    if lang not in ("vi", "en", "ja"):
        raise HTTPException(status_code=400, detail="Unsupported language code. Allowed: vi, en, ja.")
    user = get_current_user(x_nexus_role, authorization)
    target_uid = req.user_id or user.get("sub") or "u-admin-001"
    with db.get_conn() as conn:
        if req.full_name is not None:
            conn.execute("UPDATE users SET preferred_language = ?, full_name = ?, updated_at = ? WHERE id = ?",
                         (lang, req.full_name.strip(), now_iso(), target_uid))
        else:
            conn.execute("UPDATE users SET preferred_language = ?, updated_at = ? WHERE id = ?", (lang, now_iso(), target_uid))
    db.log_audit("LANGUAGE_PREFERENCE_UPDATED", "user", target_uid, {"preferred_language": lang, "full_name": req.full_name}, user_id=target_uid)
    return {"success": True, "user_id": target_uid, "preferred_language": lang, "full_name": req.full_name}


@app.post("/api/v1/users")
async def create_user_account(req: CreateUserRequest, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    actor = get_current_user(x_nexus_role)
    require_role(actor, "ADMIN")
    uid = f"u-{new_uuid()[:8]}"
    ts = now_iso()
    allowed_roles = ("ADMIN", "CEO", "EXECUTIVE", "STRATEGIC_MANAGER", "DEPARTMENT_MANAGER", "ANALYST", "VIEWER")
    role = req.role.upper() if req.role.upper() in allowed_roles else "ANALYST"
    lang = req.preferred_language if req.preferred_language in ("vi", "en", "ja") else "vi"
    with db.get_conn() as conn:
        exists = conn.execute("SELECT id FROM users WHERE lower(email) = ?", (req.email.lower().strip(),)).fetchone()
        if exists:
            raise HTTPException(status_code=400, detail="Email đã tồn tại trong hệ thống.")
        conn.execute(
            "INSERT INTO users (id, email, full_name, password_hash, default_role, is_active, preferred_language, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (uid, req.email.lower().strip(), req.full_name.strip(), hash_password(req.password), role, 1, lang, ts, ts)
        )
        conn.execute(
            "INSERT INTO workspace_members (id, workspace_id, user_id, role, joined_at) VALUES (?,?,?,?,?)",
            (new_uuid(), "ws-enterprise-001", uid, role, ts)
        )
    db.log_audit("USER_CREATED", "user", uid, {"email": req.email, "role": role}, user_id=actor["sub"])
    return {"success": True, "user_id": uid}


@app.patch("/api/v1/users/{user_id}")
async def update_user_account(user_id: str, req: UpdateUserRequest, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    actor = get_current_user(x_nexus_role)
    require_role(actor, "ADMIN")
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Người dùng không tồn tại.")
        allowed_roles = ("ADMIN", "CEO", "EXECUTIVE", "STRATEGIC_MANAGER", "DEPARTMENT_MANAGER", "ANALYST", "VIEWER")
        new_role = req.default_role.upper() if (req.default_role and req.default_role.upper() in allowed_roles) else row["default_role"]
        new_active = req.is_active if req.is_active in (0, 1) else row["is_active"]
        new_lang = req.preferred_language if req.preferred_language in ("vi", "en", "ja") else row["preferred_language"]
        conn.execute(
            "UPDATE users SET default_role = ?, is_active = ?, preferred_language = ?, updated_at = ? WHERE id = ?",
            (new_role, new_active, new_lang, now_iso(), user_id)
        )
        conn.execute("UPDATE workspace_members SET role = ? WHERE user_id = ?", (new_role, user_id))
    db.log_audit("USER_UPDATED", "user", user_id, {"role": new_role, "is_active": new_active}, user_id=actor["sub"])
    return {"success": True, "user_id": user_id}


@app.post("/api/v1/workspaces")
async def create_workspace(req: WorkspaceRequest, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    actor = get_current_user(x_nexus_role)
    require_role(actor, "ADMIN")
    ws_id = f"ws-{new_uuid()[:8]}"
    slug = f"{ws_id}"
    ts = now_iso()
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO workspaces (id, name, slug, industry_context, owner_id, quality_weights_json, created_at) VALUES (?,?,?,?,?,?,?)",
            (ws_id, req.name.strip(), slug, req.industry_context.strip(), actor["sub"], json.dumps(settings.DEFAULT_QUALITY_WEIGHTS), ts)
        )
    db.log_audit("WORKSPACE_CREATED", "workspace", ws_id, {"name": req.name}, workspace_id=ws_id, user_id=actor["sub"])
    return {"success": True, "workspace_id": ws_id}


@app.put("/api/v1/workspaces/{workspace_id}")
async def update_workspace(workspace_id: str, req: WorkspaceRequest, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    actor = get_current_user(x_nexus_role)
    require_role(actor, "ADMIN")
    with db.get_conn() as conn:
        conn.execute("UPDATE workspaces SET name = ?, industry_context = ? WHERE id = ?", (req.name.strip(), req.industry_context.strip(), workspace_id))
    db.log_audit("WORKSPACE_UPDATED", "workspace", workspace_id, {"name": req.name}, workspace_id=workspace_id, user_id=actor["sub"])
    return {"success": True, "workspace_id": workspace_id}


@app.post("/api/v1/projects")
async def create_project(req: CreateProjectRequest, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    proj_id = f"proj-{new_uuid()[:10]}"
    ts = now_iso()
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO projects (id, workspace_id, name, description, business_domain, kpi_definitions_json, created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (proj_id, req.workspace_id, req.name, req.description, req.business_domain, "[]", user["sub"], ts, ts)
        )
    db.log_audit("PROJECT_CREATED", "project", proj_id, {"name": req.name, "domain": req.business_domain}, project_id=proj_id, user_id=user["sub"])
    return {"success": True, "project_id": proj_id, "name": req.name}


@app.post("/api/v1/projects/{project_id}/kpis")
async def add_project_kpi(project_id: str, req: KpiDefinitionRequest, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    with db.get_conn() as conn:
        row = conn.execute("SELECT kpi_definitions_json FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project không tồn tại.")
        kpis = json.loads(row["kpi_definitions_json"] or "[]")
        formula = req.formula or (
            f"SUM({req.column}) / SUM({req.secondary_column}) * 100"
            if req.agg == "ratio_pct" and req.secondary_column
            else f"{req.agg.upper()}({req.column})"
        )
        ts_now = now_iso()
        new_kpi = {
            "name": req.name,
            "definition": req.definition or f"{req.agg.upper()} on {req.column}",
            "column": req.column,
            "secondary_column": req.secondary_column,
            "agg": req.agg,
            "unit": req.unit,
            "formula": formula,
            "data_source": req.data_source or "Active Project Dataset",
            "filters": req.filters or "None (All valid records)",
            "time_range": req.time_range or "Full dataset range",
            "updated_at": ts_now,
            "missing_value_rule": req.missing_value_rule or "exclude_nulls"
        }
        kpis.append(new_kpi)
        conn.execute("UPDATE projects SET kpi_definitions_json = ?, updated_at = ? WHERE id = ?",
                     (json.dumps(kpis, ensure_ascii=False), now_iso(), project_id))
    db.log_audit("KPI_DEFINED", "project", project_id, new_kpi, project_id=project_id, user_id=user["sub"])
    return {"success": True, "kpis": kpis}


@app.delete("/api/v1/projects/{project_id}")
async def delete_project(project_id: str, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ADMIN")
    if project_id == "proj-omni-001":
        raise HTTPException(status_code=400, detail="Không thể xóa dự án mặc định hệ thống.")
    with db.get_conn() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    db.log_audit("PROJECT_DELETED", "project", project_id, {}, user_id=user["sub"])
    return {"success": True}


@app.delete("/api/v1/projects/{project_id}/kpis/{kpi_index}")
async def delete_project_kpi(project_id: str, kpi_index: int, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    with db.get_conn() as conn:
        row = conn.execute("SELECT kpi_definitions_json FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project không tồn tại.")
        kpis = json.loads(row["kpi_definitions_json"] or "[]")
        if 0 <= kpi_index < len(kpis):
            removed = kpis.pop(kpi_index)
            conn.execute("UPDATE projects SET kpi_definitions_json = ?, updated_at = ? WHERE id = ?",
                         (json.dumps(kpis, ensure_ascii=False), now_iso(), project_id))
            db.log_audit("KPI_DELETED", "project", project_id, removed, project_id=project_id, user_id=user["sub"])
    return {"success": True, "kpis": kpis}


# =============================================================================
# 2. DATA INGESTION, PREVIEW, QUALITY & CLEANING ENDPOINTS
# =============================================================================
@app.post("/api/v1/datasets/inspect-upload")
async def inspect_upload(
    file: UploadFile = File(...),
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    raw_bytes = await file.read()
    try:
        meta = ingestion_service.inspect_and_stage_file(file.filename, raw_bytes)
        dup = version_lifecycle_service.detect_duplicate_or_update(
            filename=file.filename,
            file_format=meta["file_format"],
            raw_bytes=raw_bytes,
            columns=meta.get("preview_columns", []),
        )
        meta["duplicate_detection"] = dup
        meta_path = os.path.join(settings.STORAGE_DIR, "staging", f"{meta['staging_id']}.json")
        if os.path.exists(meta_path):
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        return {
            "success": True,
            "staging": meta,
            "data_processing_report": meta.get("data_processing_report"),
            "duplicate_detection": dup,
        }
    except ValueError as e:
        crit = getattr(ingestion_service, "last_critical_error", None)
        rej_ds = version_lifecycle_service.record_rejected_upload(
            file.filename or "unknown",
            raw_bytes,
            crit or {"error_code": "INVALID_FILE", "reason_i18n": {"vi": str(e), "en": str(e), "ja": str(e)}},
            user=user,
        )
        db.log_audit("FILE_VALIDATION_CRITICAL_REJECTED", "upload", file.filename or "unknown", crit or {"error": str(e)}, user_id=user["sub"])
        if crit:
            payload = dict(crit)
            payload["rejected_dataset"] = rej_ds
            return JSONResponse(status_code=422, content=payload)
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/datasets/staging/{staging_id}/sheet")
async def preview_staged_sheet(staging_id: str, sheet_name: str):
    try:
        return {"success": True, "preview": ingestion_service.get_staging_preview_for_sheet(staging_id, sheet_name)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/datasets/confirm-import")
async def confirm_import(
    req: ConfirmImportRequest,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    try:
        res = platform_manager.confirm_staged_import(
            staging_id=req.staging_id,
            project_id=req.project_id,
            dataset_name=req.dataset_name,
            selected_sheet=req.selected_sheet,
            user_id=user["sub"],
            action=req.action,
            target_dataset_id=req.target_dataset_id,
            confirm_schema_change=req.confirm_schema_change,
            report_type=req.report_type,
            user_info=user,
        )
        if res.get("cancelled"):
            return {"success": True, "cancelled": True}
        return {"success": True, "bundle": res, "dataset": res.get("dataset")}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/datasets/{dataset_id}")
async def get_dataset(dataset_id: str, version_id: Optional[str] = None):
    try:
        return platform_manager.get_dataset_bundle(dataset_id, version_id=version_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/api/v1/datasets/{dataset_id}")
async def delete_dataset_endpoint(
    dataset_id: str,
    confirm: Optional[bool] = None,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ADMIN")
    if confirm is False:
        raise HTTPException(status_code=400, detail="Confirmation required (confirm=true) for permanent deletion.")
    try:
        return version_lifecycle_service.permanently_delete_dataset(dataset_id, user=user, confirm_permanent=True)
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@app.get("/api/v1/datasets/{dataset_id}/export")
async def export_dataset_file(
    dataset_id: str,
    fmt: str = "csv",
    version_id: Optional[str] = None,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        bundle = platform_manager.get_dataset_bundle(dataset_id, version_id=version_id)
        ver = bundle["active_version"]
        df = ingestion_service.load_version_dataframe(ver["id"])
        safe_df = df.copy()
        for col in safe_df.columns:
            if is_text_series(safe_df[col]):
                safe_df[col] = safe_df[col].map(reporting_service.sanitize_cell if hasattr(reporting_service, "sanitize_cell") else lambda x: x)
        fmt_l = (fmt or "csv").lower().strip()
        base_name = f"{bundle['dataset']['name']}_v{ver['version_number']}"
        version_lifecycle_service.log_activity(
            dataset_id=dataset_id,
            activity_type="EXPORTED",
            description=f"Xuất dữ liệu phiên bản v{ver['version_number']} ra định dạng {fmt_l.upper()}.",
            user=user,
            version_id=ver["id"],
            version_number=ver["version_number"],
            outcome="SUCCESS",
            detail={"format": fmt_l.upper()},
        )
        if fmt_l == "tsv":
            tsv_bytes = safe_df.to_csv(index=False, sep="\t").encode("utf-8-sig")
            return Response(
                content=tsv_bytes,
                media_type="text/tab-separated-values; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{base_name}.tsv"'}
            )
        if fmt_l == "xlsx":
            import io
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                safe_df.to_excel(writer, sheet_name="Cleaned_Data", index=False)
            return Response(
                content=buf.getvalue(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{base_name}.xlsx"'}
            )
        csv_bytes = safe_df.to_csv(index=False).encode("utf-8-sig")
        return Response(
            content=csv_bytes,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{base_name}.csv"'}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/v1/datasets/{dataset_id}/columns/roles")
async def update_column_role(dataset_id: str, req: UpdateColumnRoleRequest, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    bundle = platform_manager.get_dataset_bundle(dataset_id)
    ver_id = bundle["active_version"]["id"]
    profile = bundle["profile"]
    for c in profile.get("columns", []):
        if c["column_name"] == req.column_name:
            c["semantic_role"] = req.semantic_role
            c["is_user_confirmed"] = True
    profile["suggested_kpis"] = profiling_service.suggest_business_kpis(profile.get("columns", []))

    df = ingestion_service.load_version_dataframe(ver_id)
    quality = quality_engine.evaluate(df, profile, bundle["quality"]["weights"])
    with db.get_conn() as conn:
        platform_manager._save_profile_and_quality(conn, ver_id, profile, quality, now_iso())
        conn.execute("UPDATE dataset_columns SET is_user_confirmed = 1 WHERE dataset_version_id = ? AND column_name = ?",
                     (ver_id, req.column_name))
        conn.execute("UPDATE datasets SET changed_since_validation = 1, updated_at = ? WHERE id = ?", (now_iso(), dataset_id))
        conn.execute("UPDATE dataset_versions SET changed_since_validation = 1 WHERE id = ?", (ver_id,))
    db.log_audit("COLUMN_ROLE_CONFIRMED", "dataset_column", dataset_id, {"column": req.column_name, "role": req.semantic_role})
    return platform_manager.get_dataset_bundle(dataset_id)


@app.post("/api/v1/datasets/{dataset_id}/quality-config")
async def update_quality_weights(dataset_id: str, req: QualityWeightsRequest, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    bundle = platform_manager.get_dataset_bundle(dataset_id)
    ver_id = bundle["active_version"]["id"]
    df = ingestion_service.load_version_dataframe(ver_id)
    weights = {
        "completeness": req.completeness,
        "uniqueness": req.uniqueness,
        "validity": req.validity,
        "consistency": req.consistency
    }
    quality = quality_engine.evaluate(df, bundle["profile"], weights)
    ts = now_iso()
    with db.get_conn() as conn:
        platform_manager._save_profile_and_quality(conn, ver_id, bundle["profile"], quality, ts)
        conn.execute("UPDATE datasets SET quality_score = ?, changed_since_validation = 1, updated_at = ? WHERE id = ?",
                     (quality["overall_quality_score"], ts, dataset_id))
        conn.execute("UPDATE dataset_versions SET changed_since_validation = 1 WHERE id = ?", (ver_id,))
    return platform_manager.get_dataset_bundle(dataset_id)


@app.post("/api/v1/datasets/{dataset_id}/revalidate")
async def revalidate_dataset_endpoint(
    dataset_id: str,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    try:
        return platform_manager.revalidate_dataset(dataset_id, user=user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/v1/datasets/{dataset_id}/gate-status")
async def get_dataset_gate_status(
    dataset_id: str,
    version_id: Optional[str] = None,
    target_step: str = "analytics",
    method_name: Optional[str] = None,
    metric_col: Optional[str] = None,
):
    try:
        bundle = platform_manager.get_dataset_bundle(dataset_id, version_id=version_id)
        ver = bundle["active_version"]
        gate = evaluate_workflow_gate(
            dataset_id,
            version_id=ver.get("id"),
            target_step=target_step,
            requested_columns=[metric_col] if metric_col else None,
            method_name=method_name,
        )
        gate["bundle_summary"] = {
            "id": bundle["dataset"]["id"],
            "name": bundle["dataset"]["name"],
            "validation_status": bundle["dataset"].get("validation_status"),
            "quality_score": bundle["quality"].get("overall_quality_score"),
            "hitl_pending_count": bundle["dataset"].get("hitl_pending_count", 0),
            "analyzability_status": bundle["dataset"].get("analyzability_status", "ANALYZABLE"),
        }
        return gate
    except ValueError as ve:
        return JSONResponse(status_code=422, content={"allowed": False, "validation_status": "REJECTED", "detail": str(ve)})


@app.post("/api/v1/datasets/{dataset_id}/confirm-columns")
async def confirm_columns_endpoint(
    dataset_id: str,
    req: ConfirmColumnsRequest,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    try:
        items = [c.model_dump() if hasattr(c, "model_dump") else c.dict() for c in req.confirmations]
        return platform_manager.confirm_columns_hitl(dataset_id, items, user=user)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.post("/api/v1/datasets/{dataset_id}/clean/preview")
async def preview_cleaning(dataset_id: str, req: CleaningRequest, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    return platform_manager.preview_cleaning(dataset_id, req.rules)


@app.post("/api/v1/datasets/{dataset_id}/clean/apply")
async def apply_cleaning(
    dataset_id: str,
    req: CleaningRequest,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    bundle = platform_manager.apply_cleaning(dataset_id, req.rules, mode=req.mode, user_id=user["sub"])
    return {"success": True, "bundle": bundle}


@app.post("/api/v1/datasets/{dataset_id}/versions/{version_id}/restore")
async def restore_version(
    dataset_id: str,
    version_id: str,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    bundle = platform_manager.restore_dataset_version(dataset_id, version_id, user_id=user["sub"], user_info=user)
    return {"success": True, "bundle": bundle}


@app.get("/api/v1/datasets/{dataset_id}/detail")
async def get_dataset_detail_endpoint(
    dataset_id: str,
    version_id: Optional[str] = None,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        return version_lifecycle_service.get_dataset_detail(dataset_id, version_id=version_id, user=user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/v1/datasets/{dataset_id}/activities")
async def get_dataset_activities_endpoint(dataset_id: str):
    return {"success": True, "dataset_id": dataset_id, "activities": version_lifecycle_service.get_activities(dataset_id)}


@app.get("/api/v1/datasets/{dataset_id}/versions/compare")
async def compare_dataset_versions_endpoint(dataset_id: str, version_a_id: str, version_b_id: str):
    try:
        return version_lifecycle_service.compare_dataset_versions(dataset_id, version_a_id, version_b_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/datasets/{dataset_id}/compare-analytics")
async def compare_dataset_analytics_endpoint(dataset_id: str, req: CompareAnalyticsRequest):
    try:
        return version_lifecycle_service.compare_version_analytics(
            dataset_id=dataset_id,
            version_a_id=req.version_a_id,
            version_b_id=req.version_b_id,
            method_name=req.method_name,
            metric_col=req.metric_col,
            dimension_col=req.dimension_col,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/datasets/{dataset_id}/archive")
async def archive_dataset_endpoint(
    dataset_id: str,
    req: Optional[ArchiveDatasetRequest] = None,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    try:
        return version_lifecycle_service.archive_dataset(dataset_id, user=user, reason=(req.reason if req else ""))
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@app.post("/api/v1/datasets/{dataset_id}/restore-archive")
async def restore_archived_dataset_endpoint(
    dataset_id: str,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    try:
        return version_lifecycle_service.restore_from_archive(dataset_id, user=user)
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.post("/api/v1/datasets/{dataset_id}/permanent-delete")
async def permanent_delete_dataset_endpoint(
    dataset_id: str,
    req: PermanentDeleteRequest,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ADMIN")
    try:
        return version_lifecycle_service.permanently_delete_dataset(
            dataset_id,
            user=user,
            confirm_permanent=req.confirm,
            force_delete_referenced=req.force_delete_referenced,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.get("/api/v1/datasets/{dataset_id}/delete-impact")
async def get_dataset_delete_impact_endpoint(dataset_id: str):
    try:
        return {"success": True, **version_lifecycle_service.get_delete_impact(dataset_id)}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@app.post("/api/v1/datasets/{dataset_id}/trash")
async def trash_dataset_endpoint(
    dataset_id: str,
    req: Optional[TrashDatasetRequest] = None,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    try:
        return version_lifecycle_service.move_to_trash(
            dataset_id,
            user=user,
            reason=(req.reason if req else ""),
            confirm_referenced=bool(req.confirm_referenced) if req else False,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.post("/api/v1/datasets/{dataset_id}/restore-trash")
async def restore_dataset_from_trash_endpoint(
    dataset_id: str,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    try:
        return version_lifecycle_service.restore_from_trash(dataset_id, user=user)
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.get("/api/v1/datasets/{dataset_id}/analysis-readiness")
async def get_dataset_analysis_readiness_endpoint(dataset_id: str, version_id: Optional[str] = None):
    try:
        bundle = platform_manager.get_dataset_bundle(dataset_id, version_id=version_id)
        df = ingestion_service.load_version_dataframe(bundle["active_version"]["id"])
        readiness = compute_analysis_readiness(df, bundle["profile"])
        return {
            "success": True,
            "dataset_id": dataset_id,
            "dataset_version_id": bundle["active_version"]["id"],
            "version_number": bundle["active_version"]["version_number"],
            **readiness,
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@app.get("/api/v1/datasets/{dataset_id}/chart-defaults")
async def get_dataset_chart_defaults(
    dataset_id: str,
    version_id: Optional[str] = None,
    language: str = "vi",
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    get_current_user(x_nexus_role, authorization)
    try:
        bundle = platform_manager.get_dataset_bundle(dataset_id, version_id=version_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    ver = bundle["active_version"]
    df = ingestion_service.load_version_dataframe(ver["id"])
    cfg = detect_default_chart_config(df, bundle["profile"], lang=language)
    return {
        "success": True,
        "dataset_id": dataset_id,
        "dataset_version_id": ver["id"],
        "version_number": ver["version_number"],
        **cfg,
    }


@app.post("/api/v1/charts/build")
async def build_interactive_chart_endpoint(
    req: ChartBuildRequest,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        bundle = platform_manager.get_dataset_bundle(req.dataset_id, version_id=req.version_id)
    except ValueError as ve:
        return JSONResponse(status_code=422, content={"success": False, "detail": str(ve), "validation_status": "REJECTED"})
    ver = bundle["active_version"]
    req_cols = [c for c in [req.x_col, req.y_col, req.series_col] if c]
    gate = evaluate_workflow_gate(req.dataset_id, version_id=ver["id"], target_step="analytics", requested_columns=req_cols, method_name="chart_builder")
    if not gate.get("allowed"):
        return JSONResponse(status_code=422, content={
            "success": False,
            "gate_blocked": True,
            "detail": (gate.get("message_i18n") or {}).get(req.language or "vi", "Validation Gatekeeper blocked Chart Builder."),
            **gate,
        })
    df = ingestion_service.load_version_dataframe(ver["id"])
    ds_meta = {
        "dataset_id": req.dataset_id,
        "dataset_name": bundle["dataset"]["name"],
        "original_filename": bundle["dataset"].get("original_filename") or bundle["dataset"]["name"],
        "selected_sheet": bundle["dataset"].get("selected_sheet") or "Primary Sheet",
        "version_id": ver["id"],
        "version_number": ver["version_number"],
    }
    res = build_custom_chart(df, bundle["profile"], req.model_dump(), ds_meta, lang=req.language or "vi")
    if not res.get("success"):
        return JSONResponse(status_code=400, content=res)
    db.log_audit("CHART_BUILT", "dataset", req.dataset_id, {"x": res["x_col"], "y": res["y_col"], "agg": res["aggregation"], "type": res["selected_chart_type"]}, user_id=user["sub"])
    return res


@app.post("/api/v1/charts/drilldown")
async def chart_drilldown_endpoint(
    req: ChartDrilldownRequest,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    get_current_user(x_nexus_role, authorization)
    try:
        bundle = platform_manager.get_dataset_bundle(req.dataset_id, version_id=req.version_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    ver = bundle["active_version"]
    df = ingestion_service.load_version_dataframe(ver["id"])
    out = get_chart_drilldown_rows(df, req.filter_col, req.filter_val, limit=min(500, max(1, req.limit)))
    return {"success": True, "dataset_id": req.dataset_id, "version_id": ver["id"], "version_number": ver["version_number"], **out}


@app.post("/api/v1/charts/export")
async def chart_export_table_endpoint(
    req: ChartBuildRequest,
    fmt: str = "csv",
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    get_current_user(x_nexus_role, authorization)
    try:
        bundle = platform_manager.get_dataset_bundle(req.dataset_id, version_id=req.version_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    ver = bundle["active_version"]
    df = ingestion_service.load_version_dataframe(ver["id"])
    ds_meta = {
        "dataset_id": req.dataset_id,
        "dataset_name": bundle["dataset"]["name"],
        "version_id": ver["id"],
        "version_number": ver["version_number"],
    }
    res = build_custom_chart(df, bundle["profile"], req.model_dump(), ds_meta, lang=req.language or "vi")
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=(res.get("message_i18n") or {}).get("vi", "Cannot export chart table"))
    out_df = pd.DataFrame(res.get("table_rows", []))
    export_dir = os.path.join(settings.STORAGE_DIR, "exports")
    os.makedirs(export_dir, exist_ok=True)
    safe_base = f"chart_data_{req.dataset_id}_v{ver['version_number']}"
    if fmt.lower() == "xlsx":
        out_path = os.path.join(export_dir, f"{safe_base}.xlsx")
        out_df.to_excel(out_path, index=False)
        return FileResponse(out_path, filename=f"{safe_base}.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    out_path = os.path.join(export_dir, f"{safe_base}.csv")
    out_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    return FileResponse(out_path, filename=f"{safe_base}.csv", media_type="text/csv; charset=utf-8")


@app.get("/api/v1/evidence/{run_id}")
async def get_analysis_evidence_endpoint(
    run_id: str,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    get_current_user(x_nexus_role, authorization)
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi bằng chứng phân tích.")
        rec = dict(row)
        ds = conn.execute("SELECT name, original_filename, selected_sheet FROM datasets WHERE id = ?", (rec.get("dataset_id"),)).fetchone()
        res_j = json.loads(rec.get("result_json") or "{}")
        eb = res_j.get("evidence_bundle") if isinstance(res_j, dict) else None
        return {
            "success": True,
            "run_id": run_id,
            "dataset_id": rec.get("dataset_id"),
            "dataset_name": ds["name"] if ds else rec.get("dataset_id"),
            "version_id": rec.get("dataset_version_id"),
            "version_number": rec.get("version_number", 1),
            "method_name": rec.get("method_name"),
            "formula_used": rec.get("formula_used"),
            "columns_used": json.loads(rec.get("columns_used_json") or "[]"),
            "validation_checks": json.loads(rec.get("validation_checks_json") or "[]"),
            "created_at": rec.get("created_at"),
            "evidence_bundle": eb,
        }


@app.get("/api/v1/analytics/toolkit/catalog")
async def get_strategic_toolkit_catalog():
    return {"success": True, "methods": TOOLKIT_CATALOG}


@app.post("/api/v1/analytics/recommend-tools")
async def recommend_strategic_tools_endpoint(req: RecommendToolsRequest):
    try:
        bundle = platform_manager.get_dataset_bundle(req.dataset_id, version_id=req.version_id)
        ver = bundle["active_version"]
        gate = evaluate_workflow_gate(req.dataset_id, version_id=ver["id"], target_step="analytics")
        if not gate.get("allowed"):
            return JSONResponse(status_code=422, content={"success": False, "gate_blocked": True, **gate})
        df = ingestion_service.load_version_dataframe(ver["id"])
        rec = recommend_analytical_methods(df, bundle["profile"], req.business_goal)
        return {"success": True, "dataset_id": req.dataset_id, "dataset_version_id": ver["id"], **rec}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@app.post("/api/v1/analytics/toolkit/run")
async def run_strategic_toolkit_endpoint(
    req: ToolkitRunRequest,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        bundle = platform_manager.get_dataset_bundle(req.dataset_id, version_id=req.version_id)
    except ValueError as ve:
        return JSONResponse(status_code=422, content={"success": False, "detail": str(ve), "validation_status": "REJECTED"})
    ver = bundle["active_version"]
    gate = evaluate_workflow_gate(req.dataset_id, version_id=ver["id"], target_step="analytics", method_name=req.method_id)
    if not gate.get("allowed"):
        return JSONResponse(status_code=422, content={
            "success": False,
            "gate_blocked": True,
            "detail": (gate.get("message_i18n") or {}).get("vi", "Validation Gatekeeper blocked Strategic Toolkit."),
            **gate,
        })
    df = ingestion_service.load_version_dataframe(ver["id"])
    ds_meta = {
        "dataset_id": req.dataset_id,
        "version_id": ver["id"],
        "dataset_name": bundle["dataset"]["name"],
        "version_number": ver["version_number"],
    }
    out = strategic_toolkit_service.run_toolkit_method(df, bundle["profile"], req.method_id, req.parameters, ds_meta)
    run_id = out.get("analysis_id") or f"tk-{new_uuid()[:12]}"
    ts = now_iso()
    with db.get_conn() as conn:
        conn.execute(
            """INSERT INTO analysis_runs (id, project_id, dataset_id, dataset_version_id, version_number, analytics_level, method_name,
               analysis_goal, columns_used_json, kpis_computed_json, assumptions_json, parameters_json, formula_used, validation_checks_json,
               result_json, duration_ms, engine_version, created_by, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id, req.project_id, req.dataset_id, ver["id"], ver["version_number"],
                (out.get("interpretation_8parts") or {}).get("analytics_level", "DIAGNOSTIC"),
                req.method_id, f"Strategic Toolkit: {req.method_id}",
                json.dumps(out.get("columns_used", []), ensure_ascii=False),
                json.dumps({}, ensure_ascii=False),
                json.dumps(out.get("assumptions", []), ensure_ascii=False),
                json.dumps(req.parameters or {}, ensure_ascii=False),
                str(out.get("formula_used", "")),
                json.dumps(out.get("chart_validation", {}), ensure_ascii=False),
                json.dumps({k: v for k, v in out.items() if k != "drilldown_rows"}, ensure_ascii=False, default=str),
                float(out.get("duration_ms") or 0.0), "toolkit-v3.0", user["sub"], ts,
            )
        )
    db.log_audit("STRATEGIC_TOOLKIT_EXECUTED", "analysis_run", run_id, {"method": req.method_id, "dataset_id": req.dataset_id}, project_id=req.project_id, user_id=user["sub"])
    out["success"] = True
    out["analysis_run_id"] = run_id
    out["dataset_version"] = {"id": ver["id"], "version_number": ver["version_number"]}
    return out


# =============================================================================
# 3. UNIVERSAL ANALYTICS ENGINE (4 LEVELS), AI AGENT, DASHBOARDS & REPORTS
# =============================================================================
@app.post("/api/v1/analytics/run")
async def run_analytics(
    req: RunAnalysisRequest,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        bundle = platform_manager.get_dataset_bundle(req.dataset_id, version_id=req.version_id)
    except ValueError as ve:
        return JSONResponse(status_code=422, content={"success": False, "detail": str(ve), "validation_status": "REJECTED"})
    ver = bundle["active_version"]
    df = ingestion_service.load_version_dataframe(ver["id"])

    raw_method = req.method_name or req.analysis_type or "summary_stats"
    method_aliases = {
        "descriptive_stats": "summary_stats",
        "trend_analysis": "trend_analysis",
        "period_comparison": "period_variance",
        "abc_xyz_classification": "abc_analysis",
        "variance_root_cause": "variance_decomposition",
        "rfm_segmentation": "rfm_analysis",
        "cohort_retention": "cohort_analysis",
        "funnel_conversion": "funnel_conversion",
        "forecasting": "time_series_forecast",
        "moving_average": "moving_average",
        "regression_driver": "linear_regression",
        "what_if_simulation": "what_if_scenario",
        "Reorder_optimization": "eoq_reorder_optimization",
        "reorder_optimization": "eoq_reorder_optimization",
        "price_elasticity": "price_elasticity",
    }
    resolved_method = method_aliases.get(raw_method, raw_method)

    # Central Workflow & Dependency Gatekeeper Enforcement (Never allow invalid/un-analyzable/unconfirmed runs!)
    strict_gate = bool((req.parameters or {}).get("strict_readiness_gate", False))
    req_cols = [c for c in [req.metric_col, req.dimension_col, req.secondary_col] if c]
    gate = evaluate_workflow_gate(
        req.dataset_id,
        version_id=ver["id"],
        target_step="analytics",
        requested_columns=req_cols,
        method_name=resolved_method,
        strict_readiness_gate=strict_gate,
    )
    if not gate.get("allowed"):
        db.log_audit("GATEKEEPER_BLOCKED_ANALYTICS", "dataset", req.dataset_id, {"gate": gate, "method": resolved_method}, project_id=req.project_id, user_id=user["sub"])
        return JSONResponse(status_code=gate.get("http_status", 422), content={
            "success": False,
            "gate_blocked": True,
            "blocked_by_dependency_gate": bool(gate.get("blocked_by_dependency_gate", True)),
            "detail": (gate.get("message_i18n") or {}).get("vi", "Validation Gatekeeper blocked analysis."),
            **gate,
        })

    with db.get_conn() as conn:
        p_row = conn.execute("SELECT kpi_definitions_json FROM projects WHERE id = ?", (req.project_id,)).fetchone()
        kpis = json.loads(p_row["kpi_definitions_json"] or "[]") if p_row else []

    enriched_params = dict(req.parameters or {})
    if req.metric_col:
        enriched_params.setdefault("metric", req.metric_col)
        enriched_params.setdefault("column", req.metric_col)
    if req.dimension_col:
        enriched_params.setdefault("dimension", req.dimension_col)
        enriched_params.setdefault("group_col", req.dimension_col)
    if req.secondary_col:
        enriched_params.setdefault("secondary_column", req.secondary_col)
    if req.window:
        enriched_params.setdefault("window", req.window)
    if req.periods:
        enriched_params.setdefault("horizon", req.periods)
    if req.granularity:
        enriched_params.setdefault("granularity", req.granularity)
    enriched_params.setdefault("language", req.language or "vi")

    enriched_params.setdefault("dataset_id", req.dataset_id)
    enriched_params.setdefault("dataset_version_id", ver["id"])
    enriched_params.setdefault("dataset_version_number", ver["version_number"])
    enriched_params.setdefault("original_filename", bundle["dataset"].get("original_filename") or bundle["dataset"]["name"])
    enriched_params.setdefault("dataset_name", bundle["dataset"]["name"])
    enriched_params.setdefault("selected_sheet", bundle["dataset"].get("selected_sheet", "Sheet1"))
    enriched_params.setdefault("dataset_version_label", f"v{ver['version_number']} ({ver.get('checksum_sha256', '')[:8]})")

    try:
        out = analytics_engine.run_analysis(df, bundle["profile"], resolved_method, enriched_params, kpis)
    except ValueError as ve:
        msg_str = str(ve)
        return JSONResponse(status_code=400, content={
            "success": False,
            "not_applicable": True,
            "error_code": "METHOD_PRECONDITION_NOT_MET",
            "method_name": resolved_method,
            "dataset_id": req.dataset_id,
            "version_id": ver["id"],
            "detail": msg_str,
            "message_i18n": {
                "vi": msg_str,
                "en": f"Cannot run '{resolved_method}' on current dataset: {msg_str}",
                "ja": f"現在のデータセットでは「{resolved_method}」を実行できません: {msg_str}",
            },
        })

    # Dependency-Aware Readiness Inspection (Section 9)
    proc_rep = bundle.get("data_processing_report") or {}
    audit_16 = proc_rep.get("audit_16_domains") or {}
    dep_ready = audit_16.get("dependency_readiness") or {}
    col_ready_map = dep_ready.get("column_readiness") or {}
    target_metric = req.metric_col or enriched_params.get("metric")
    blocked_notices = []
    if target_metric and target_metric in col_ready_map and col_ready_map[target_metric].get("status") == "BLOCKED_BY_CELL_ERRORS":
        blocked_notices.append({
            "scope": "COLUMN",
            "column": target_metric,
            "unresolved_count": col_ready_map[target_metric].get("unresolved_user_edit_count", 0),
            "blocking_cells": col_ready_map[target_metric].get("blocking_cells", []),
            "message_i18n": {
                "vi": f"Cột '{target_metric}' đang có ô lỗi màu đỏ chưa sửa ({col_ready_map[target_metric].get('blocking_cells', [])}). Các kết quả tổng hợp có thể chưa phản ánh đủ những dòng này.",
                "en": f"Column '{target_metric}' has unresolved red cell errors ({col_ready_map[target_metric].get('blocking_cells', [])}). Aggregations exclude or flag those cells.",
                "ja": f"列「{target_metric}」に未修正の赤色セルエラーがあります。"
            }
        })
    if resolved_method in ("time_series_forecast", "period_variance") and dep_ready.get("blocked_date_columns"):
        blocked_notices.append({
            "scope": "ANALYTICAL_TASK",
            "task": resolved_method,
            "blocked_columns": dep_ready.get("blocked_date_columns"),
            "message_i18n": (dep_ready.get("analytical_task_readiness", {}).get("time_series_trend_and_forecast", {}) or {}).get("reason_i18n", {})
        })
    if enriched_params.get("strict_readiness_gate") and blocked_notices:
        return JSONResponse(status_code=422, content={
            "success": False,
            "blocked_by_dependency_gate": True,
            "blocked_notices": blocked_notices,
            "dependency_readiness": dep_ready
        })

    run_id = f"ana-{new_uuid()[:12]}"
    chart_id = f"cht-{new_uuid()[:12]}"
    ts = now_iso()

    cols_used = [c for c in [req.metric_col, req.dimension_col, req.secondary_col] if c]
    kpis_snap = {}
    for c_name in ([req.metric_col] if req.metric_col else []):
        if c_name in df.columns:
            num_s = pd.to_numeric(df[c_name], errors="coerce").dropna()
            if len(num_s) > 0:
                kpis_snap[c_name] = {"sum": round(float(num_s.sum()), 2), "mean": round(float(num_s.mean()), 2), "count": int(len(num_s))}
    assumptions_list = out.get("validation_checks", [])
    goal_str = req.analysis_goal or f"{out['analytics_level']}: {resolved_method}"

    persisted_result = dict(out.get("results") or {}) if isinstance(out.get("results"), dict) else {"data": out.get("results")}
    persisted_result["_snapshot"] = {
        "analytics_level": out["analytics_level"],
        "method_name": out["method_name"],
        "formula_used": out["formula_used"],
        "interpretation": out.get("interpretation"),
        "interpretation_i18n": out.get("interpretation_i18n"),
        "structured_explanation": out.get("structured_explanation"),
        "structured_explanation_i18n": out.get("structured_explanation_i18n"),
        "verification_report": out.get("verification_report"),
        "verification_state": out.get("verification_state"),
        "formulas": out.get("formulas"),
        "evidence_bundle": out.get("evidence_bundle"),
        "traceability": out.get("traceability"),
        "recommendations": out.get("recommendations", []),
        "missing_value_notices": out.get("missing_value_notices", []),
        "echarts_option": out.get("echarts_option"),
    }

    with db.get_conn() as conn:
        conn.execute(
            """INSERT INTO analysis_runs (id, project_id, dataset_id, dataset_version_id, version_number, analytics_level, method_name,
               analysis_goal, columns_used_json, kpis_computed_json, assumptions_json, parameters_json, formula_used, validation_checks_json,
               result_json, duration_ms, engine_version, created_by, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (run_id, req.project_id, req.dataset_id, ver["id"], ver["version_number"], out["analytics_level"], out["method_name"],
             goal_str, json.dumps(cols_used, ensure_ascii=False), json.dumps(kpis_snap, ensure_ascii=False),
             json.dumps(assumptions_list, ensure_ascii=False), json.dumps(enriched_params, ensure_ascii=False), out["formula_used"],
             json.dumps(out["validation_checks"], ensure_ascii=False), json.dumps(persisted_result, ensure_ascii=False, default=str),
             out["duration_ms"], out["engine_version"], user["sub"], ts)
        )
        version_lifecycle_service.log_activity(
            dataset_id=req.dataset_id,
            activity_type="ANALYSIS_EXECUTED",
            description=f"Chạy phân tích '{out['method_name']}' trên phiên bản v{ver['version_number']} (cột: {', '.join(cols_used) or 'auto'}).",
            user=user,
            version_id=ver["id"],
            version_number=ver["version_number"],
            outcome="SUCCESS" if not blocked_notices else "WARNING",
            detail={"analysis_run_id": run_id, "method": resolved_method, "columns_used": cols_used, "kpis": kpis_snap},
            conn=conn,
            created_at=ts,
        )
        if out.get("echarts_option"):
            conn.execute(
                """INSERT INTO charts (id, project_id, dataset_version_id, analysis_run_id, title, chart_type, echarts_option_json, explanation, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (chart_id, req.project_id, ver["id"], run_id,
                 out["echarts_option"].get("title", {}).get("text", resolved_method),
                 resolved_method, json.dumps(out["echarts_option"], ensure_ascii=False), out["interpretation"], ts)
            )
        conn.execute(
            """INSERT INTO insights (id, project_id, dataset_version_id, analysis_run_id, category, severity, title, finding_text, evidence_ref_json, recommendation_json, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (new_uuid(), req.project_id, ver["id"], run_id, out["analytics_level"], "INFO",
             f"Analysis: {out['method_name']}", out["interpretation"],
             json.dumps({"version_id": ver["id"], "version_number": ver["version_number"], "formula": out["formula_used"]}, ensure_ascii=False),
             json.dumps(out.get("recommendations", []), ensure_ascii=False), ts)
        )

    db.log_audit("ANALYSIS_EXECUTED", "analysis_run", run_id, {"method": resolved_method, "level": out["analytics_level"]}, project_id=req.project_id)
    out["success"] = True
    out["analysis_run_id"] = run_id
    out["dataset_version"] = {"id": ver["id"], "version_number": ver["version_number"]}
    out["chart"] = out.get("echarts_option")
    out["dependency_readiness"] = dep_ready
    out["dependency_blocked_notices"] = blocked_notices
    return out


@app.get("/api/v1/analytics/history")
async def list_analytics_history(
    dataset_id: Optional[str] = None,
    limit: int = 30,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    get_current_user(x_nexus_role, authorization)
    lim = max(1, min(100, limit))
    with db.get_conn() as conn:
        if dataset_id:
            rows = conn.execute(
                """SELECT ar.id, ar.dataset_id, ar.dataset_version_id, ar.version_number, ar.analytics_level,
                          ar.method_name, ar.analysis_goal, ar.columns_used_json, ar.formula_used,
                          ar.duration_ms, ar.created_by, ar.created_at,
                          d.name AS dataset_name, dv_cur.version_number AS current_version_number
                   FROM analysis_runs ar
                   LEFT JOIN datasets d ON d.id = ar.dataset_id
                   LEFT JOIN dataset_versions dv_cur ON dv_cur.id = d.current_version_id
                   WHERE ar.dataset_id = ?
                   ORDER BY ar.created_at DESC LIMIT ?""",
                (dataset_id, lim),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT ar.id, ar.dataset_id, ar.dataset_version_id, ar.version_number, ar.analytics_level,
                          ar.method_name, ar.analysis_goal, ar.columns_used_json, ar.formula_used,
                          ar.duration_ms, ar.created_by, ar.created_at,
                          d.name AS dataset_name, dv_cur.version_number AS current_version_number
                   FROM analysis_runs ar
                   LEFT JOIN datasets d ON d.id = ar.dataset_id
                   LEFT JOIN dataset_versions dv_cur ON dv_cur.id = d.current_version_id
                   ORDER BY ar.created_at DESC LIMIT ?""",
                (lim,),
            ).fetchall()
    runs = []
    for r in rows:
        rec = dict(r)
        rec["columns_used"] = json.loads(rec.pop("columns_used_json", "[]") or "[]")
        cur_v = int(rec.get("current_version_number") or rec.get("version_number") or 1)
        run_v = int(rec.get("version_number") or 1)
        rec["is_outdated_version"] = cur_v > run_v
        runs.append(rec)
    return {"success": True, "runs": runs}


@app.get("/api/v1/analytics/runs/{run_id}")
async def get_saved_analysis_run(
    run_id: str,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    get_current_user(x_nexus_role, authorization)
    with db.get_conn() as conn:
        row = conn.execute(
            """SELECT ar.*, d.name AS dataset_name, dv_cur.version_number AS current_version_number
               FROM analysis_runs ar
               LEFT JOIN datasets d ON d.id = ar.dataset_id
               LEFT JOIN dataset_versions dv_cur ON dv_cur.id = d.current_version_id
               WHERE ar.id = ?""",
            (run_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy lịch sử phân tích.")
        rec = dict(row)
        raw_res = json.loads(rec.get("result_json") or "{}")
        snap = raw_res.pop("_snapshot", {}) if isinstance(raw_res, dict) else {}
        chart_row = conn.execute("SELECT echarts_option_json, explanation FROM charts WHERE analysis_run_id = ? LIMIT 1", (run_id,)).fetchone()
        ech = snap.get("echarts_option") or (json.loads(chart_row["echarts_option_json"]) if chart_row and chart_row["echarts_option_json"] else {})
        cur_v = int(rec.get("current_version_number") or rec.get("version_number") or 1)
        run_v = int(rec.get("version_number") or 1)
        return {
            "success": True,
            "is_historical_replay": True,
            "is_outdated_version": cur_v > run_v,
            "current_version_number": cur_v,
            "analysis_run_id": rec["id"],
            "dataset_id": rec["dataset_id"],
            "dataset_name": rec.get("dataset_name") or rec["dataset_id"],
            "dataset_version": {"id": rec["dataset_version_id"], "version_number": run_v},
            "analytics_level": rec["analytics_level"],
            "method_name": rec["method_name"],
            "columns_used": json.loads(rec.get("columns_used_json") or "[]"),
            "parameters": json.loads(rec.get("parameters_json") or "{}"),
            "formula_used": rec.get("formula_used") or "",
            "validation_checks": json.loads(rec.get("validation_checks_json") or "[]"),
            "results": raw_res,
            "interpretation": snap.get("interpretation") or (chart_row["explanation"] if chart_row else ""),
            "interpretation_i18n": snap.get("interpretation_i18n") or {},
            "structured_explanation": snap.get("structured_explanation") or {},
            "structured_explanation_i18n": snap.get("structured_explanation_i18n") or {},
            "verification_report": snap.get("verification_report") or {},
            "verification_state": snap.get("verification_state") or {},
            "formulas": snap.get("formulas") or [],
            "evidence_bundle": snap.get("evidence_bundle"),
            "traceability": snap.get("traceability") or {},
            "recommendations": snap.get("recommendations") or [],
            "missing_value_notices": snap.get("missing_value_notices") or [],
            "echarts_option": ech,
            "chart": ech,
            "created_by": rec.get("created_by"),
            "created_at": rec.get("created_at"),
        }


@app.post("/api/v1/ai/chat")
@app.post("/api/v1/ai/query")
async def ai_chat(req: AIChatRequest):
    question_text = (req.question or req.prompt or "Tóm tắt bộ dữ liệu").strip()
    try:
        bundle = platform_manager.get_dataset_bundle(req.dataset_id, version_id=req.version_id)
    except ValueError as ve:
        return JSONResponse(status_code=422, content={"success": False, "detail": str(ve), "validation_status": "REJECTED"})
    ver = bundle["active_version"]
    gate = evaluate_workflow_gate(req.dataset_id, version_id=ver["id"], target_step="ai_chat")
    if not gate.get("allowed"):
        db.log_audit("GATEKEEPER_BLOCKED_AI_CHAT", "dataset", req.dataset_id, {"gate": gate}, project_id=req.project_id)
        return JSONResponse(status_code=422, content={
            "success": False,
            "gate_blocked": True,
            "detail": (gate.get("message_i18n") or {}).get("vi", "Validation Gatekeeper blocked AI Chat."),
            **gate,
        })
    df = ingestion_service.load_version_dataframe(ver["id"])

    linked_run = None
    with db.get_conn() as conn:
        p_row = conn.execute("SELECT kpi_definitions_json FROM projects WHERE id = ?", (req.project_id,)).fetchone()
        kpis = json.loads(p_row["kpi_definitions_json"] or "[]") if p_row else []
        if req.analysis_run_id:
            r_row = conn.execute("SELECT * FROM analysis_runs WHERE id = ?", (req.analysis_run_id,)).fetchone()
            if r_row:
                r_dict = dict(r_row)
                r_res = json.loads(r_dict.get("result_json") or "{}")
                linked_run = {
                    "id": r_dict["id"],
                    "method_name": r_dict["method_name"],
                    "version_number": r_dict.get("version_number", ver["version_number"]),
                    "columns_used": json.loads(r_dict.get("columns_used_json") or "[]"),
                    "formula_used": r_dict.get("formula_used", ""),
                    "snapshot": r_res.get("_snapshot", {}) if isinstance(r_res, dict) else {},
                }

    ds_meta = {
        "id": bundle["dataset"]["id"],
        "name": bundle["dataset"]["name"],
        "version_id": ver["id"],
        "version_number": ver["version_number"]
    }
    agent_res = ai_agent_orchestrator.answer_question(
        question=question_text,
        df=df,
        profile=bundle["profile"],
        quality_report=bundle["quality"],
        dataset_meta=ds_meta,
        kpi_definitions=kpis,
        language=req.language or "vi",
        rfq_context=req.rfq_context,
        linked_analysis_run=linked_run,
    )
    if linked_run:
        agent_res["linked_analysis_run_id"] = linked_run["id"]
    agent_res["answer"] = agent_res.get("answer_markdown", "")
    agent_res["chart"] = agent_res.get("echarts_option")
    agent_res["evidence"] = {
        "dataset_name": bundle["dataset"]["name"],
        "formula": ", ".join(tc.get("tool", "") for tc in agent_res.get("tool_calls", [])) or "Pandas / NumPy Direct Verification"
    }

    conv_id = f"conv-{req.dataset_id}"
    ts = now_iso()
    with db.get_conn() as conn:
        exists = conn.execute("SELECT id FROM ai_conversations WHERE id = ?", (conv_id,)).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO ai_conversations (id, project_id, dataset_version_id, title, provider_mode, created_by, created_at) VALUES (?,?,?,?,?,?,?)",
                (conv_id, req.project_id, ver["id"], f"AI Session - {bundle['dataset']['name']}", settings.AI_PROVIDER, "u-admin-001", ts)
            )
        conn.execute(
            "INSERT INTO ai_messages (id, conversation_id, role, content, reasoning_trace_json, tool_calls_json, evidence_refs_json, chart_json, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (new_uuid(), conv_id, "user", question_text, "{}", "[]", "[]", "{}", ts)
        )
        conn.execute(
            "INSERT INTO ai_messages (id, conversation_id, role, content, reasoning_trace_json, tool_calls_json, evidence_refs_json, chart_json, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (new_uuid(), conv_id, "assistant", agent_res["answer_markdown"],
             json.dumps({"goal": agent_res["goal"], "plan": agent_res["plan"], "reflection": agent_res["reflection"]}, ensure_ascii=False),
             json.dumps(agent_res["tool_calls"], ensure_ascii=False),
             json.dumps(agent_res["evidence_references"], ensure_ascii=False),
             json.dumps(agent_res["echarts_option"], ensure_ascii=False), ts)
        )

    db.log_audit("AI_AGENT_QUERY", "ai_conversation", conv_id, {"question": question_text, "tools_called": len(agent_res["tool_calls"])}, project_id=req.project_id)
    return agent_res


@app.post("/api/v1/dashboards")
async def create_dashboard(req: CreateDashboardRequest, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    did = f"dash-{new_uuid()[:10]}"
    ts = now_iso()
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO dashboards (id, project_id, name, description, filters_json, created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (did, req.project_id, req.name.strip(), req.description.strip(), "{}", user["sub"], ts, ts)
        )
    db.log_audit("DASHBOARD_CREATED", "dashboard", did, {"name": req.name}, project_id=req.project_id, user_id=user["sub"])
    return {"success": True, "dashboard_id": did}


@app.post("/api/v1/dashboards/widgets")
async def add_dashboard_widget(req: AddWidgetRequest, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    wid = f"wdg-{new_uuid()[:10]}"
    with db.get_conn() as conn:
        cnt = conn.execute("SELECT COUNT(*) as c FROM dashboard_widgets WHERE dashboard_id = ?", (req.dashboard_id,)).fetchone()["c"]
        conn.execute(
            "INSERT INTO dashboard_widgets (id, dashboard_id, widget_type, title, position_order, width_cols, config_json, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (wid, req.dashboard_id, req.widget_type, req.title, cnt + 1, req.width_cols, json.dumps(req.config, ensure_ascii=False), now_iso())
        )
    db.log_audit("DASHBOARD_WIDGET_ADDED", "dashboard_widget", wid, {"title": req.title})
    return {"success": True, "widget_id": wid}


@app.delete("/api/v1/dashboards/widgets/{widget_id}")
async def remove_dashboard_widget(widget_id: str, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    with db.get_conn() as conn:
        conn.execute("DELETE FROM dashboard_widgets WHERE id = ?", (widget_id,))
    db.log_audit("DASHBOARD_WIDGET_DELETED", "dashboard_widget", widget_id, {}, user_id=user["sub"])
    return {"success": True}


@app.get("/api/v1/insights/summary")
async def get_grounded_ai_insights(dataset_id: str, project_id: str = "proj-omni-001", lang: str = "vi"):
    lang_code = lang if lang in ("vi", "en", "ja") else "vi"
    try:
        bundle = platform_manager.get_dataset_bundle(dataset_id)
    except ValueError as ve:
        return JSONResponse(status_code=422, content={"success": False, "gate_blocked": True, "detail": str(ve), "validation_status": "REJECTED"})
    ver = bundle["active_version"]
    gate = evaluate_workflow_gate(dataset_id, version_id=ver["id"], target_step="insights")
    if not gate.get("allowed"):
        return JSONResponse(status_code=422, content={
            "success": False,
            "gate_blocked": True,
            "detail": (gate.get("message_i18n") or {}).get("vi", "Validation Gatekeeper blocked insights."),
            **gate,
        })
    df = ingestion_service.load_version_dataframe(ver["id"])
    prof = bundle["profile"]
    qual = bundle["quality"]

    with db.get_conn() as conn:
        p_row = conn.execute("SELECT kpi_definitions_json FROM projects WHERE id = ?", (project_id,)).fetchone()
        kpis = json.loads(p_row["kpi_definitions_json"] or "[]") if p_row else []

    pareto_res = None
    anom_res = None
    trend_res = None
    try:
        pareto_res = analytics_engine.run_analysis(df, prof, "pareto_analysis", {}, kpis)
    except Exception:
        pass
    try:
        anom_res = analytics_engine.run_analysis(df, prof, "anomaly_detection", {}, kpis)
    except Exception:
        pass
    try:
        trend_res = analytics_engine.run_analysis(df, prof, "period_variance", {}, kpis)
    except Exception:
        pass

    anom_cnt = anom_res["results"].get("anomaly_count", 0) if anom_res else 0
    anom_col = anom_res["results"].get("column", "") if anom_res else ""
    pct_var = trend_res["results"].get("percentage_variance", 0.0) if trend_res else None
    cur_p = trend_res["results"].get("current_period", "") if trend_res else ""
    prev_p = trend_res["results"].get("previous_period", "") if trend_res else ""
    top_item = pareto_res["results"]["items"][0] if (pareto_res and pareto_res["results"].get("items")) else None
    p_dim = pareto_res["results"].get("dimension", "") if pareto_res else ""
    p_met = pareto_res["results"].get("metric", "") if pareto_res else ""

    cards_by_lang = {
        "vi": [
            {
                "kind": "anomaly",
                "title": "Phát hiện bất thường",
                "metric": f"{anom_cnt} điểm bất thường",
                "detail": f"Kiểm tra Z-Score/IQR trên cột '{anom_col or 'chỉ số'}' (Chất lượng dữ liệu: {qual['overall_quality_score']}/100, {qual['issues_count']} vấn đề).",
                "action_view": "bi_analytics",
                "action_method": "anomaly_detection"
            },
            {
                "kind": "trend",
                "title": "Xu hướng đáng chú ý",
                "metric": f"{pct_var:+.2f}%" if pct_var is not None else f"{len(df)} bản ghi",
                "detail": f"Biến động kỳ {cur_p} so với {prev_p}." if pct_var is not None else "Dữ liệu danh mục / phi chuỗi thời gian sẵn sàng phân tích cơ cấu.",
                "action_view": "bi_analytics",
                "action_method": "time_series_forecast" if pct_var is not None else "summary_stats"
            },
            {
                "kind": "opportunity",
                "title": "Cơ hội kinh doanh",
                "metric": f"{top_item['share_pct']}%" if top_item else "--",
                "detail": f"Nhóm dẫn đầu '{top_item['item']}' ({p_dim}) đạt {top_item['value']:,.0f} cho chỉ số '{p_met}'." if top_item else "Sẵn sàng chạy phân tích Pareto 80/20.",
                "action_view": "bi_analytics",
                "action_method": "pareto_analysis"
            },
            {
                "kind": "action",
                "title": "Đề xuất hành động",
                "metric": f"v{ver['version_number']}",
                "detail": (f"Ưu tiên xử lý {qual['issues_count']} lỗi chất lượng dữ liệu trước khi dự báo." if qual["issues_count"] > 0 else "Dữ liệu sạch chuẩn; nên chạy mô phỏng What-If hoặc hỏi Trợ lý AI."),
                "action_view": "data_cleaning" if qual["issues_count"] > 0 else "ai_assistant",
                "action_method": "what_if_scenario"
            }
        ],
        "en": [
            {
                "kind": "anomaly",
                "title": "Anomaly Detection",
                "metric": f"{anom_cnt} outliers",
                "detail": f"Tukey IQR & Z-Score scan on '{anom_col or 'metric'}' (Quality Score: {qual['overall_quality_score']}/100, {qual['issues_count']} issues).",
                "action_view": "bi_analytics",
                "action_method": "anomaly_detection"
            },
            {
                "kind": "trend",
                "title": "Notable Trends",
                "metric": f"{pct_var:+.2f}%" if pct_var is not None else f"{len(df)} rows",
                "detail": f"Variance from {prev_p} to {cur_p}." if pct_var is not None else "Cross-sectional catalog dataset ready for structural breakdown.",
                "action_view": "bi_analytics",
                "action_method": "time_series_forecast" if pct_var is not None else "summary_stats"
            },
            {
                "kind": "opportunity",
                "title": "Business Opportunity",
                "metric": f"{top_item['share_pct']}%" if top_item else "--",
                "detail": f"Top driver '{top_item['item']}' ({p_dim}) contributes {top_item['value']:,.0f} of '{p_met}'." if top_item else "Run Pareto 80/20 ranking to isolate top value drivers.",
                "action_view": "bi_analytics",
                "action_method": "pareto_analysis"
            },
            {
                "kind": "action",
                "title": "Recommended Action",
                "metric": f"v{ver['version_number']}",
                "detail": (f"Resolve {qual['issues_count']} data quality flags before forecasting." if qual["issues_count"] > 0 else "Dataset is clean; run What-If simulation or ask AI Assistant."),
                "action_view": "data_cleaning" if qual["issues_count"] > 0 else "ai_assistant",
                "action_method": "what_if_scenario"
            }
        ],
        "ja": [
            {
                "kind": "anomaly",
                "title": "異常検知",
                "metric": f"{anom_cnt}件の異常値",
                "detail": f"「{anom_col or '主要指標'}」のIQR/Zスコア検証（データ品質スコア: {qual['overall_quality_score']}/100、課題 {qual['issues_count']}件）。",
                "action_view": "bi_analytics",
                "action_method": "anomaly_detection"
            },
            {
                "kind": "trend",
                "title": "注目トレンド",
                "metric": f"{pct_var:+.2f}%" if pct_var is not None else f"{len(df)}件",
                "detail": f"前期（{prev_p}）比 最新期（{cur_p}）の変化率。" if pct_var is not None else "クロスセクション構造分析に対応したデータセットです。",
                "action_view": "bi_analytics",
                "action_method": "time_series_forecast" if pct_var is not None else "summary_stats"
            },
            {
                "kind": "opportunity",
                "title": "ビジネス機会",
                "metric": f"{top_item['share_pct']}%" if top_item else "--",
                "detail": f"「{p_dim}」首位「{top_item['item']}」が {p_met} の {top_item['value']:,.0f} を創出。" if top_item else "パレート80/20分析で成長ドライバーを特定できます。",
                "action_view": "bi_analytics",
                "action_method": "pareto_analysis"
            },
            {
                "kind": "action",
                "title": "推奨アクション",
                "metric": f"v{ver['version_number']}",
                "detail": (f"予測分析の前に {qual['issues_count']}件の品質課題をクレンジングしてください。" if qual["issues_count"] > 0 else "データは健全です。What-If分析またはAIアシスタントを活用してください。"),
                "action_view": "data_cleaning" if qual["issues_count"] > 0 else "ai_assistant",
                "action_method": "what_if_scenario"
            }
        ]
    }
    return {"dataset_id": dataset_id, "language": lang_code, "cards": cards_by_lang[lang_code]}


@app.post("/api/v1/reports/generate")
async def generate_report(
    req: GenerateReportRequest,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    try:
        bundle = platform_manager.get_dataset_bundle(req.dataset_id, version_id=req.version_id)
    except ValueError as ve:
        return JSONResponse(status_code=422, content={"success": False, "detail": str(ve), "validation_status": "REJECTED"})
    ver = bundle["active_version"]
    gate = evaluate_workflow_gate(req.dataset_id, version_id=ver["id"], target_step="report")
    if not gate.get("allowed"):
        db.log_audit("GATEKEEPER_BLOCKED_REPORT", "dataset", req.dataset_id, {"gate": gate}, project_id=req.project_id, user_id=user["sub"])
        return JSONResponse(status_code=422, content={
            "success": False,
            "gate_blocked": True,
            "detail": (gate.get("message_i18n") or {}).get("vi", "Validation Gatekeeper blocked report export."),
            **gate,
        })
    df = ingestion_service.load_version_dataframe(ver["id"])

    with db.get_conn() as conn:
        proj = dict(conn.execute("SELECT * FROM projects WHERE id = ?", (req.project_id,)).fetchone() or {"name": "Enterprise Project"})
        kpis = json.loads(proj.get("kpi_definitions_json") or "[]")

    ds_meta = {
        "id": bundle["dataset"]["id"],
        "name": bundle["dataset"]["name"],
        "original_filename": bundle["dataset"]["original_filename"],
        "version_id": ver["id"],
        "version_number": ver["version_number"]
    }
    payload = reporting_service.generate_report_payload(
        report_type=req.report_type,
        project_meta=proj,
        dataset_meta=ds_meta,
        df=df,
        profile=bundle["profile"],
        quality=bundle["quality"],
        kpis=kpis,
        language=req.language or "vi",
        sections_selected=req.sections_selected,
    )
    if req.title:
        payload["title"] = req.title
    if req.author:
        payload["author"] = req.author
    if req.custom_recommendations:
        payload["custom_recommendations"] = req.custom_recommendations
    payload["dataset_id"] = req.dataset_id
    payload["dataset_version_id"] = ver["id"]
    payload["version_number"] = ver["version_number"]

    rep_id = f"rep-{new_uuid()[:10]}"
    files = reporting_service.export_report_files(rep_id, payload, df)
    ts = now_iso()

    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO reports (id, project_id, dataset_id, dataset_version_id, version_number, analysis_run_id, report_type, title, report_payload_json, excel_path, docx_path, created_by, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (rep_id, req.project_id, req.dataset_id, ver["id"], ver["version_number"], req.analysis_run_id,
             payload["report_type"], payload["title"], json.dumps(payload, ensure_ascii=False),
             files["excel_path"], files["docx_path"], user["sub"], ts)
        )
        version_lifecycle_service.log_activity(
            dataset_id=req.dataset_id,
            activity_type="REPORT_GENERATED",
            description=f"Tạo báo cáo '{payload['title']}' gắn cố định với phiên bản dữ liệu v{ver['version_number']} ({ver['id']}).",
            user=user,
            version_id=ver["id"],
            version_number=ver["version_number"],
            outcome="SUCCESS",
            detail={"report_id": rep_id, "report_type": payload["report_type"]},
            conn=conn,
            created_at=ts,
        )

    db.log_audit("REPORT_GENERATED", "report", rep_id, {"report_type": payload["report_type"], "title": payload["title"], "dataset_version_id": ver["id"], "version_number": ver["version_number"]}, project_id=req.project_id, user_id=user["sub"])
    return {
        "success": True,
        "report_id": rep_id,
        "dataset_id": req.dataset_id,
        "dataset_version_id": ver["id"],
        "version_number": ver["version_number"],
        "report": payload,
        "download_excel_url": f"/api/v1/reports/{rep_id}/download/xlsx",
        "download_docx_url": f"/api/v1/reports/{rep_id}/download/docx",
        "download_pdf_url": f"/api/v1/reports/{rep_id}/download/pdf",
        "download_csv_url": f"/api/v1/reports/{rep_id}/download/csv",
        "download_tsv_url": f"/api/v1/reports/{rep_id}/download/tsv"
    }


@app.get("/api/v1/reports/{report_id}/download/{fmt}")
async def download_report(report_id: str, fmt: str):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Báo cáo không tồn tại.")
    fmt_l = fmt.lower().strip()
    rep_dir = os.path.join(settings.STORAGE_DIR, "reports")
    if fmt_l == "xlsx":
        return FileResponse(row["excel_path"], filename=f"Nexus_{row['report_type']}_{report_id}.xlsx")
    elif fmt_l == "docx":
        return FileResponse(row["docx_path"], filename=f"Nexus_{row['report_type']}_{report_id}.docx")
    elif fmt_l == "pdf":
        pdf_p = os.path.join(rep_dir, f"Nexus_Report_{report_id}.pdf")
        if not os.path.exists(pdf_p):
            payload = json.loads(row["report_payload_json"] or "{}")
            reporting_service._write_simple_pdf(pdf_p, [payload.get("title", "Report"), payload.get("executive_summary", "")])
        return FileResponse(pdf_p, media_type="application/pdf", filename=f"Nexus_{row['report_type']}_{report_id}.pdf")
    elif fmt_l in ("csv", "tsv"):
        ext_p = os.path.join(rep_dir, f"Nexus_Report_{report_id}.{fmt_l}")
        if os.path.exists(ext_p):
            return FileResponse(ext_p, filename=f"Nexus_{row['report_type']}_{report_id}.{fmt_l}")
    raise HTTPException(status_code=400, detail="Định dạng tải xuống chỉ hỗ trợ 'xlsx', 'docx', 'pdf', 'csv', 'tsv'.")


@app.get("/api/v1/audit-logs")
async def get_audit_logs():
    with db.get_conn() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100").fetchall()]
        runs = [dict(r) for r in conn.execute("SELECT id, analytics_level, method_name, formula_used, duration_ms, created_at FROM analysis_runs ORDER BY created_at DESC LIMIT 50").fetchall()]
    return {"audit_logs": rows, "analysis_runs": runs, "rfq_history": rfq_workflow_service.get_rfq_history()}


# =============================================================================
# 4. INTEGRATED B2B RFQ & COMMERCIAL INTELLIGENCE ENDPOINTS (UNIFIED + BACKWARD COMPATIBLE)
# =============================================================================
@app.get("/api/rules")
@app.get("/api/v1/rfq/rules")
async def get_rfq_rules():
    return rfq_workflow_service.get_rules()


@app.post("/api/rules")
@app.post("/api/v1/rfq/rules")
async def update_rfq_rules(new_rules: Dict[str, Any], x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    return rfq_workflow_service.update_rules(new_rules, user_id=user["sub"])


@app.get("/api/master-data")
@app.get("/api/v1/rfq/master-data")
async def get_rfq_master_data():
    return rfq_workflow_service.get_master_data_dict()


@app.get("/api/samples/{case_id}")
@app.get("/api/v1/rfq/samples/{case_id}")
async def get_sample_rfp(case_id: int):
    try:
        return rfq_workflow_service.get_sample_rfp(case_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/load-google-sheets")
@app.post("/api/v1/rfq/load-google-sheets")
async def load_google_sheets_endpoint(req: GoogleSheetsRequest, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    res = rfq_workflow_service.load_google_sheets_catalog(req.url, user_id=user["sub"])
    if not res["success"]:
        return JSONResponse(status_code=400, content=res)
    return res


@app.post("/api/upload-master-file")
@app.post("/api/v1/rfq/upload-master-file")
async def upload_master_file_endpoint(file: UploadFile = File(...), x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    content = await file.read()
    res = rfq_workflow_service.upload_master_file(file.filename, content, user_id=user["sub"])
    if not res["success"]:
        return JSONResponse(status_code=400, content=res)
    return res


@app.post("/api/upload-rfp-file")
@app.post("/api/v1/rfq/upload-rfp-file")
async def upload_rfp_file_endpoint(file: UploadFile = File(...)):
    content = await file.read()
    res = rfq_workflow_service.read_rfp_file(file.filename, content)
    if not res["success"]:
        return JSONResponse(status_code=400, content=res)
    return res


@app.post("/api/process-rfp")
@app.post("/api/v1/rfq/process-rfp")
async def process_rfp_endpoint(req: ProcessRfpRequest):
    try:
        return rfq_workflow_service.process_rfp(
            text=req.text,
            custom_discount=req.custom_discount,
            source_type=req.source_type or "TEXT"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/manager-decision")
@app.post("/api/v1/rfq/manager-decision")
async def submit_manager_decision_endpoint(req: ManagerDecisionRequest):
    return rfq_workflow_service.submit_manager_decision(decision=req.decision, comment=req.comment)


@app.get("/api/execution-logs")
@app.get("/api/v1/rfq/execution-logs")
async def get_execution_logs_endpoint():
    wf = rfq_workflow_service.last_workflow_result or {}
    return {
        "logs": wf.get("execution_logs", []),
        "tool_calls": wf.get("tool_calls", []),
        "gate_decisions": wf.get("gate_decisions", []),
        "rfq_history": rfq_workflow_service.get_rfq_history()
    }


@app.get("/api/download/boq-excel")
@app.get("/api/v1/rfq/download/boq-excel")
async def download_boq_excel_endpoint():
    try:
        excel_bytes, filename = rfq_workflow_service.export_current_boq_excel()
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/download/proposal-word")
@app.get("/api/v1/rfq/download/proposal-word")
async def download_proposal_word_endpoint():
    try:
        docx_bytes, filename = rfq_workflow_service.export_current_proposal_word()
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/rfq/sync-boq-dataset")
async def sync_rfq_boq_to_dataset(x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    try:
        bundle = rfq_workflow_service.sync_current_boq_to_dataset(user_id=user["sub"])
        return {"success": True, "bundle": bundle}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/rfq/runs/{run_db_id}")
async def get_rfq_run_detail_endpoint(run_db_id: str):
    try:
        return {"success": True, "run": rfq_workflow_service.get_rfq_run_detail(run_db_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/v1/rfq/partners")
async def list_rfq_partners(partner_type: Optional[str] = None):
    with db.get_conn() as conn:
        if partner_type in ("CUSTOMER", "SUPPLIER"):
            rows = conn.execute("SELECT * FROM rfq_partners WHERE partner_type = ? ORDER BY created_at DESC", (partner_type,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM rfq_partners ORDER BY partner_type ASC, created_at DESC").fetchall()
    return {"partners": [dict(r) for r in rows]}


@app.post("/api/v1/rfq/partners")
async def create_rfq_partner(req: PartnerRequest, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    ptype = req.partner_type.upper() if req.partner_type.upper() in ("CUSTOMER", "SUPPLIER") else "CUSTOMER"
    pid = f"prt-{new_uuid()[:10]}"
    code = req.code or f"{'CUST' if ptype == 'CUSTOMER' else 'SUP'}-{new_uuid()[:5].upper()}"
    ts = now_iso()
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO rfq_partners (id, partner_type, name, code, contact_person, email, phone, region, category, sla_tier, lead_time_days, notes, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (pid, ptype, req.name.strip(), code, req.contact_person.strip(), req.email.strip(), req.phone.strip(),
             req.region.strip(), req.category.strip(), req.sla_tier.strip(), int(req.lead_time_days), req.notes.strip(), ts, ts)
        )
    db.log_audit("RFQ_PARTNER_CREATED", "rfq_partner", pid, {"type": ptype, "name": req.name}, user_id=user["sub"])
    return {"success": True, "partner_id": pid}


@app.put("/api/v1/rfq/partners/{partner_id}")
async def update_rfq_partner(partner_id: str, req: PartnerRequest, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM rfq_partners WHERE id = ?", (partner_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Đối tác không tồn tại.")
        conn.execute(
            "UPDATE rfq_partners SET name = ?, contact_person = ?, email = ?, phone = ?, region = ?, category = ?, sla_tier = ?, lead_time_days = ?, notes = ?, updated_at = ? WHERE id = ?",
            (req.name.strip(), req.contact_person.strip(), req.email.strip(), req.phone.strip(),
             req.region.strip(), req.category.strip(), req.sla_tier.strip(), int(req.lead_time_days), req.notes.strip(), now_iso(), partner_id)
        )
    db.log_audit("RFQ_PARTNER_UPDATED", "rfq_partner", partner_id, {"name": req.name}, user_id=user["sub"])
    return {"success": True, "partner_id": partner_id}


@app.delete("/api/v1/rfq/partners/{partner_id}")
async def delete_rfq_partner(partner_id: str, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ADMIN")
    with db.get_conn() as conn:
        conn.execute("DELETE FROM rfq_partners WHERE id = ?", (partner_id,))
    db.log_audit("RFQ_PARTNER_DELETED", "rfq_partner", partner_id, {}, user_id=user["sub"])
    return {"success": True}


@app.get("/api/v1/rfq/procurement")
async def list_rfq_procurement():
    with db.get_conn() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM rfq_procurement ORDER BY created_at DESC LIMIT 50").fetchall()]
    return {"procurement": rows}


@app.post("/api/v1/rfq/procurement")
async def create_rfq_procurement(req: ProcurementCreateRequest, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    proc_id = f"po-{new_uuid()[:10]}"
    po_code = f"PO-TM-{new_uuid()[:6].upper()}"
    ts = now_iso()
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO rfq_procurement (id, po_code, rfq_run_id, customer_name, supplier_name, sku_summary, total_cost, expected_delivery_date, assigned_engineer, status, notes, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (proc_id, po_code, req.rfq_run_id, req.customer_name.strip(), req.supplier_name.strip(), req.sku_summary.strip(),
             float(req.total_cost), req.expected_delivery_date.strip(), req.assigned_engineer.strip(), req.status.upper(), req.notes.strip(), ts, ts)
        )
    db.log_audit("RFQ_PROCUREMENT_CREATED", "rfq_procurement", po_code, {"customer": req.customer_name, "cost": req.total_cost}, user_id=user["sub"])
    return {"success": True, "procurement_id": proc_id, "po_code": po_code}


@app.patch("/api/v1/rfq/procurement/{proc_id}")
async def update_rfq_procurement_status(proc_id: str, req: ProcurementStatusRequest, x_nexus_role: Optional[str] = Header(default="ADMIN")):
    user = get_current_user(x_nexus_role)
    require_role(user, "ANALYST")
    allowed = ("PLANNED", "ORDERED", "IN_TRANSIT", "DELIVERED", "DEPLOYED")
    new_status = req.status.upper().strip()
    if new_status not in allowed:
        raise HTTPException(status_code=400, detail=f"Trạng thái không hợp lệ. Chỉ chấp nhận: {allowed}")
    with db.get_conn() as conn:
        conn.execute("UPDATE rfq_procurement SET status = ?, notes = COALESCE(?, notes), updated_at = ? WHERE id = ?",
                     (new_status, req.notes, now_iso(), proc_id))
    db.log_audit("RFQ_PROCUREMENT_UPDATED", "rfq_procurement", proc_id, {"status": new_status}, user_id=user["sub"])
    return {"success": True, "status": new_status}


# =============================================================================
# 5. HUMAN-CENTERED FRONTEND GRANULAR REST ENDPOINTS
# =============================================================================
@app.post("/api/v1/users/preferences")
async def save_user_preferences_alias(
    req: UserPreferenceRequest,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    return await save_user_preferences(req, x_nexus_role, authorization)


@app.get("/api/v1/datasets")
async def list_datasets_endpoint(
    area: str = "ALL",
    search: str = "",
    status: str = "ALL",
    file_format: str = "ALL",
    date_range: str = "ALL",
    date_from: str = "",
    date_to: str = "",
    uploaded_by: str = "",
    report_type: str = "",
    severity: str = "",
    changed_since_validation: Optional[bool] = None,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 50
):
    platform_manager._ensure_sample_benchmark_dataset()
    return version_lifecycle_service.list_datasets_filtered(
        area=area,
        search=search,
        status=status,
        file_format=file_format,
        date_range=date_range,
        date_from=date_from,
        date_to=date_to,
        uploaded_by=uploaded_by,
        report_type=report_type,
        severity=severity,
        changed_since_validation=changed_since_validation,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )


@app.post("/api/v1/datasets/upload")
async def direct_upload_dataset(
    file: UploadFile = File(...),
    name: Optional[str] = Form(default=None),
    domain: Optional[str] = Form(default="General Business"),
    sheet_name: Optional[str] = Form(default=None),
    conflict_resolution: Optional[str] = Form(default="ALLOW_DUPLICATE"),
    target_dataset_id: Optional[str] = Form(default=None),
    confirm_schema_change: Optional[bool] = Form(default=False),
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    raw_bytes = await file.read()
    try:
        meta = ingestion_service.inspect_and_stage_file(file.filename, raw_bytes)
        dup = version_lifecycle_service.detect_duplicate_or_update(
            filename=file.filename,
            file_format=meta["file_format"],
            raw_bytes=raw_bytes,
            columns=meta.get("preview_columns", []),
        )
        meta["duplicate_detection"] = dup

        res_mode = (conflict_resolution or "ALLOW_DUPLICATE").upper().strip()
        if res_mode == "PROMPT" and dup.get("has_conflict"):
            return {
                "success": False,
                "requires_decision": True,
                "staging_id": meta["staging_id"],
                "staging": meta,
                "duplicate_detection": dup,
                "data_processing_report": meta.get("data_processing_report"),
            }

        chosen_sheet = sheet_name or meta.get("default_sheet", "Sheet1")
        action = "NEW_VERSION" if res_mode == "NEW_VERSION" else "NEW_DATASET"
        tgt_id = target_dataset_id or (dup.get("matched_dataset_id") if action == "NEW_VERSION" else None)

        bundle = platform_manager.confirm_staged_import(
            staging_id=meta["staging_id"],
            project_id="proj-omni-001",
            dataset_name=name or os.path.splitext(file.filename)[0],
            selected_sheet=chosen_sheet,
            user_id=user["sub"],
            action=action,
            target_dataset_id=tgt_id,
            confirm_schema_change=bool(confirm_schema_change),
            report_type=domain or "General Business",
            user_info=user,
        )
    except ValueError as e:
        crit = getattr(ingestion_service, "last_critical_error", None)
        rej_ds = version_lifecycle_service.record_rejected_upload(
            file.filename or "unknown",
            raw_bytes,
            crit or {"error_code": "INVALID_FILE", "reason_i18n": {"vi": str(e), "en": str(e), "ja": str(e)}},
            user=user,
            report_type=domain or "General Business",
        )
        db.log_audit("FILE_VALIDATION_CRITICAL_REJECTED", "upload", file.filename or "unknown", crit or {"error": str(e)}, user_id=user["sub"])
        if crit:
            payload = dict(crit)
            payload["rejected_dataset"] = rej_ds
            return JSONResponse(status_code=422, content=payload)
        raise HTTPException(status_code=400, detail=str(e))

    ds = bundle["dataset"]
    ds["filename"] = ds.get("original_filename", file.filename)
    ds["col_count"] = ds.get("column_count", ds.get("col_count", 0))
    ds["current_version"] = bundle["active_version"]["version_number"]
    prof = bundle["profile"]
    prof["sheet_names"] = [s["sheet_name"] if isinstance(s, dict) else str(s) for s in meta.get("sheets", [])]
    prof["isolated_invalid_sheets"] = meta.get("isolated_invalid_sheets", [])
    prof["partial_workbook_recovery"] = meta.get("partial_workbook_recovery", False)
    prof["encoding"] = meta.get("encoding", "UTF-8")
    return {
        "success": True,
        "dataset": ds,
        "profile": prof,
        "duplicate_detection": dup,
        "data_processing_report": bundle.get("data_processing_report"),
        "gate_status": bundle.get("gate_status"),
        "valid_sheets": prof["sheet_names"],
        "isolated_invalid_sheets": prof["isolated_invalid_sheets"],
        "partial_workbook_recovery": prof["partial_workbook_recovery"],
        "bundle": bundle
    }


@app.get("/api/v1/datasets/{dataset_id}/processing-report")
@app.get("/api/v1/datasets/{dataset_id}/validation-report")
async def get_dataset_processing_report(dataset_id: str):
    bundle = platform_manager.get_dataset_bundle(dataset_id)
    return {
        "success": True,
        "dataset_id": dataset_id,
        "data_processing_report": bundle.get("data_processing_report")
    }


@app.get("/api/v1/datasets/{dataset_id}/error-report")
async def download_dataset_error_report(dataset_id: str, fmt: str = "xlsx"):
    import io
    bundle = platform_manager.get_dataset_bundle(dataset_id)
    rep = bundle.get("data_processing_report") or {}
    ds_name = bundle["dataset"]["name"]
    fmt_l = (fmt or "xlsx").lower().strip()

    if fmt_l == "json":
        return Response(
            content=json.dumps(rep, ensure_ascii=False, indent=2).encode("utf-8"),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="Error_Report_{dataset_id}.json"'}
        )

    affected_rows = []
    for item in rep.get("affected_rows_detail", []):
        row_entry = {
            "Row_Number": item.get("row_number"),
            "Status": item.get("status"),
            "Max_Severity_Level": f"Level {item.get('max_severity_level')}",
            "Issues_Detected": " ; ".join(f"[L{i['level']}] {i['code']} ({i['column']}): {i['detail']}" for i in item.get("issues", []))
        }
        row_entry.update(item.get("row_data") or {})
        affected_rows.append(row_entry)

    if fmt_l == "csv":
        df_err = pd.DataFrame(affected_rows) if affected_rows else pd.DataFrame([{"Message": "No affected rows detected"}])
        return Response(
            content=df_err.to_csv(index=False).encode("utf-8-sig"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="Error_Report_{dataset_id}.csv"'}
        )

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        summary_df = pd.DataFrame([
            {"Metric": "Dataset Name", "Value": ds_name},
            {"Metric": "Source Filename", "Value": rep.get("filename")},
            {"Metric": "Selected Sheet", "Value": rep.get("selected_sheet")},
            {"Metric": "Validation Status", "Value": rep.get("status")},
            {"Metric": "Original Record Count", "Value": rep.get("original_record_count", 0)},
            {"Metric": "Valid Record Count", "Value": rep.get("valid_record_count", 0)},
            {"Metric": "Unique Affected Records (No Double-Counting)", "Value": rep.get("unique_affected_record_count", 0)},
            {"Metric": "Total Error Occurrences", "Value": rep.get("total_error_occurrences", 0)},
            {"Metric": "Level 1 Auto-Corrected Records", "Value": rep.get("corrected_record_count", 0)},
            {"Metric": "Rejected Empty Records", "Value": rep.get("rejected_record_count", 0)},
            {"Metric": "Remaining Level 2 Warning Records", "Value": rep.get("remaining_warning_record_count", 0)},
        ])
        summary_df.to_excel(writer, sheet_name="1_Summary_Metrics", index=False)

        l1_actions = rep.get("processing_actions") or [{"Note": "No Level 1 actions needed"}]
        pd.DataFrame(l1_actions).to_excel(writer, sheet_name="2_Level1_Auto_Actions", index=False)

        l2_warns = rep.get("remaining_warnings") or [{"Note": "No Level 2 warnings remaining"}]
        pd.DataFrame(l2_warns).to_excel(writer, sheet_name="3_Level2_Warnings", index=False)

        df_aff = pd.DataFrame(affected_rows) if affected_rows else pd.DataFrame([{"Note": "0 affected rows"}])
        df_aff.to_excel(writer, sheet_name="4_Affected_Records", index=False)

    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="Error_Processing_Report_{dataset_id}.xlsx"'}
    )


@app.get("/api/v1/datasets/{dataset_id}/profile")
async def get_dataset_profile_endpoint(dataset_id: str):
    bundle = platform_manager.get_dataset_bundle(dataset_id)
    prof = dict(bundle["profile"] or {})
    cols = []
    for c in prof.get("columns", []):
        col_copy = dict(c)
        col_copy["name"] = c.get("column_name") or c.get("name")
        col_copy["semantic_type"] = c.get("semantic_role") or c.get("semantic_type") or c.get("inferred_dtype") or c.get("physical_type")
        col_copy["dtype"] = c.get("inferred_dtype") or c.get("dtype") or c.get("physical_type")
        stats = c.get("stats") or {}
        col_copy["min"] = c.get("min", stats.get("min"))
        col_copy["max"] = c.get("max", stats.get("max"))
        col_copy["mean"] = c.get("mean", stats.get("mean"))
        cols.append(col_copy)
    prof["columns"] = cols
    prof["dataset_name"] = bundle["dataset"]["name"]
    prof["row_count"] = bundle["dataset"].get("row_count", prof.get("row_count", 0))
    prof["col_count"] = bundle["dataset"].get("column_count", bundle["dataset"].get("col_count", len(cols)))
    prof["duplicate_rows"] = prof.get("duplicate_row_count", prof.get("duplicate_rows", 0))
    prof["missing_cell_pct"] = round(sum(float(c.get("missing_pct", 0.0)) for c in cols) / max(len(cols), 1), 2)
    return prof


@app.get("/api/v1/datasets/{dataset_id}/preview")
async def get_dataset_preview_endpoint(dataset_id: str, limit: int = 80):
    bundle = platform_manager.get_dataset_bundle(dataset_id)
    rows = bundle.get("sample_rows", [])[:limit]
    return {"dataset_id": dataset_id, "rows": rows}


@app.get("/api/v1/datasets/{dataset_id}/quality")
async def get_dataset_quality_endpoint(dataset_id: str):
    bundle = platform_manager.get_dataset_bundle(dataset_id)
    q = dict(bundle.get("quality") or {})
    dims = q.get("dimension_scores") or {}
    q["scores"] = {
        "overall": q.get("overall_quality_score", 95.0),
        "completeness": q.get("completeness_score", dims.get("completeness", 95.0)),
        "uniqueness": q.get("uniqueness_score", dims.get("uniqueness", 98.0)),
        "validity": q.get("validity_score", dims.get("validity", 95.0)),
        "consistency": q.get("consistency_score", dims.get("consistency", 94.0)),
        "accuracy": q.get("accuracy_score", dims.get("accuracy", 98.0)),
    }
    q["gate_status"] = bundle.get("gate_status", {})
    q["data_processing_report"] = bundle.get("data_processing_report", {})
    return q


@app.get("/api/v1/datasets/{dataset_id}/cleaning")
async def get_dataset_cleaning_endpoint(dataset_id: str):
    bundle = platform_manager.get_dataset_bundle(dataset_id)
    recs = bundle.get("cleaning_recommendations") or bundle.get("quality", {}).get("cleaning_recommendations") or []
    return {
        "dataset_id": dataset_id,
        "recommendations": recs,
        "versions": bundle.get("versions", []),
        "cleaning_history": bundle.get("cleaning_history", []),
        "data_processing_report": bundle.get("data_processing_report", {})
    }


@app.get("/api/v1/datasets/{dataset_id}/cleaning-workspace")
async def get_dataset_cleaning_workspace_endpoint(
    dataset_id: str,
    page: int = 1,
    page_size: int = 50,
    search: str = "",
    filter_mode: str = "ALL",
    sort_col: str = "",
    sort_dir: str = "asc",
    domain_filter: str = "",
    severity_filter: str = "",
    column_filter: str = "",
    status_filter: str = "",
    version_id: Optional[str] = None
):
    return platform_manager.get_cleaning_workspace_state(
        dataset_id=dataset_id,
        page=page,
        page_size=page_size,
        search=search,
        filter_mode=filter_mode,
        sort_col=sort_col,
        sort_dir=sort_dir,
        domain_filter=domain_filter,
        severity_filter=severity_filter,
        column_filter=column_filter,
        status_filter=status_filter,
        version_id=version_id
    )


@app.get("/api/v1/datasets/{dataset_id}/readiness")
async def get_dataset_readiness_endpoint(dataset_id: str):
    bundle = platform_manager.get_dataset_bundle(dataset_id)
    rep = bundle.get("data_processing_report") or {}
    return {
        "success": True,
        "dataset_id": dataset_id,
        "readiness_status": rep.get("readiness_status"),
        "can_proceed_to_analytics": rep.get("can_proceed_to_analytics", True),
        "gate_status": bundle.get("gate_status", {}),
        "analyzability_status": rep.get("analyzability_status", "ANALYZABLE"),
        "hitl_pending_count": rep.get("hitl_pending_count", 0),
        "hitl_columns": rep.get("hitl_columns", []),
        "sequence_index_columns": rep.get("sequence_index_columns", []),
        "gatekeeper_checklist": rep.get("gatekeeper_checklist", []),
        "audit_16_domains": rep.get("audit_16_domains", {})
    }


@app.post("/api/v1/datasets/{dataset_id}/edit-cell")
async def edit_dataset_cell_endpoint(
    dataset_id: str,
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    row_index = body.get("row_index")
    column = body.get("column")
    new_value = body.get("new_value")
    if row_index is None or not column:
        raise HTTPException(status_code=400, detail="Missing 'row_index' or 'column'.")
    try:
        return platform_manager.edit_dataset_cell(
            dataset_id=dataset_id,
            row_index=int(row_index),
            column=str(column),
            new_value=new_value,
            user_id=user["sub"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/datasets/{dataset_id}/clean")
async def apply_dataset_cleaning_simple(
    dataset_id: str,
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    ops = body.get("operations") or body.get("rules") or []
    rules = []
    for op in ops:
        rule = {
            "column": op.get("column"),
            "operation": op.get("operation"),
            "parameters": {
                "value": op.get("value"),
                "denominator": op.get("secondary_column"),
                "other_column": op.get("secondary_column"),
                "target_column": op.get("new_column"),
                "factor": op.get("value", 1.0)
            }
        }
        rules.append(rule)
    bundle = platform_manager.apply_cleaning(dataset_id, rules, mode="AI_ASSISTED", user_id=user["sub"])
    return {"success": True, "bundle": bundle}


@app.post("/api/v1/datasets/{dataset_id}/restore")
async def restore_dataset_by_number(
    dataset_id: str,
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    ver_num = body.get("version_number")
    ver_id = body.get("version_id")
    bundle = platform_manager.get_dataset_bundle(dataset_id)
    if not ver_id and ver_num is not None:
        matched = next((v for v in bundle.get("versions", []) if v.get("version_number") == int(ver_num)), None)
        if matched:
            ver_id = matched["id"]
    if not ver_id and bundle.get("versions"):
        ver_id = bundle["versions"][-1]["id"]
    restored = platform_manager.restore_dataset_version(dataset_id, ver_id, user_id=user["sub"], user_info=user)
    return {"success": True, "bundle": restored}


@app.post("/api/v1/datasets/{dataset_id}/undo")
async def undo_dataset_cleaning(
    dataset_id: str,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    bundle = platform_manager.undo_dataset_version(dataset_id, user_id=user["sub"])
    return {"success": True, "bundle": bundle}


@app.post("/api/v1/datasets/{dataset_id}/redo")
async def redo_dataset_cleaning(
    dataset_id: str,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    bundle = platform_manager.redo_dataset_version(dataset_id, user_id=user["sub"])
    return {"success": True, "bundle": bundle}


@app.post("/api/v1/datasets/{dataset_id}/reset")
async def reset_dataset_to_initial(
    dataset_id: str,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ANALYST")
    bundle = platform_manager.reset_dataset_to_v1(dataset_id, user_id=user["sub"])
    return {"success": True, "bundle": bundle}


@app.get("/api/v1/kpis")
async def list_all_kpis_endpoint():
    platform_manager._ensure_sample_benchmark_dataset()
    with db.get_conn() as conn:
        p_row = conn.execute("SELECT kpi_definitions_json FROM projects WHERE id = 'proj-omni-001'").fetchone()
        kpis = json.loads(p_row["kpi_definitions_json"] or "[]") if p_row else []
        ds_row = conn.execute("SELECT id FROM datasets WHERE validation_status != 'REJECTED' ORDER BY created_at DESC LIMIT 1").fetchone()
    df = None
    if ds_row:
        try:
            bundle = platform_manager.get_dataset_bundle(ds_row["id"])
            df = ingestion_service.load_version_dataframe(bundle["active_version"]["id"])
        except Exception:
            df = None

    enriched = []
    for idx, k in enumerate(kpis):
        kc = dict(k)
        kc["id"] = kc.get("id") or f"kpi-{idx}"
        col = kc.get("column") or kc.get("target_column") or ""
        agg = (kc.get("agg") or kc.get("formula_type") or "SUM").upper()
        kc["formula_type"] = agg
        kc["target_column"] = col
        kc["description"] = kc.get("definition") or kc.get("description") or ""
        kc["filter_conditions"] = kc.get("filters") or kc.get("filter_conditions") or "All valid rows"
        val = kc.get("current_value")
        if val is None and df is not None and col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(s) > 0:
                if agg == "AVG" or agg == "MEAN":
                    val = float(s.mean())
                elif agg == "MIN":
                    val = float(s.min())
                elif agg == "MAX":
                    val = float(s.max())
                elif agg == "MEDIAN":
                    val = float(s.median())
                elif agg == "COUNT":
                    val = float(len(s))
                else:
                    val = float(s.sum())
        kc["current_value"] = val if val is not None else 0.0
        enriched.append(kc)
    return {"kpis": enriched}


@app.post("/api/v1/kpis")
async def create_kpi_simple_endpoint(body: Dict[str, Any]):
    req = KpiDefinitionRequest(
        name=body.get("name", "KPI"),
        definition=body.get("description") or body.get("definition"),
        column=body.get("target_column") or body.get("column") or "revenue",
        agg=(body.get("formula_type") or body.get("agg") or "sum").lower(),
        unit=body.get("unit", "VND"),
        formula=body.get("formula"),
        data_source=body.get("data_source") or body.get("dataset_id") or "Active Dataset",
        filters=body.get("filter_conditions") or body.get("filters") or "All valid rows",
        time_range=body.get("time_range") or "Full dataset range",
        missing_value_rule=body.get("missing_value_rule") or "ignore_nulls"
    )
    return await add_project_kpi("proj-omni-001", req)


@app.get("/api/v1/reports")
async def list_reports_endpoint(dataset_id: Optional[str] = None):
    with db.get_conn() as conn:
        sql = """
            SELECT r.*, d.name as dataset_name, d.current_version_id as dataset_current_version_id,
                   dv_cur.version_number as current_version_number
              FROM reports r
              LEFT JOIN datasets d ON d.id = r.dataset_id
              LEFT JOIN dataset_versions dv_cur ON dv_cur.id = d.current_version_id
        """
        params = []
        if dataset_id:
            sql += " WHERE r.dataset_id = ?"
            params.append(dataset_id)
        sql += " ORDER BY r.created_at DESC LIMIT 50"
        rows = [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]
        for r in rows:
            payload = json.loads(r.get("report_payload_json") or "{}")
            r["executive_summary"] = payload.get("executive_summary", "")
            r["author"] = payload.get("author", "")
            cur_vid = r.get("dataset_current_version_id")
            r["is_outdated_version"] = bool(cur_vid and r.get("dataset_version_id") and cur_vid != r.get("dataset_version_id"))
    return {"reports": rows}


@app.get("/api/v1/users")
async def list_users_endpoint():
    with db.get_conn() as conn:
        users = [dict(r) for r in conn.execute("SELECT id, email, full_name, default_role as role, is_active, preferred_language FROM users").fetchall()]
        for u in users:
            u["status"] = "ACTIVE" if u.get("is_active", 1) else "INACTIVE"
    return {"users": users}


@app.get("/api/v1/feature-flags")
async def get_feature_flags_endpoint():
    return {"success": True, "feature_flags": _get_workspace_feature_flags()}


@app.post("/api/v1/feature-flags")
async def update_feature_flags_endpoint(
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    require_role(user, "ADMIN")
    flags = _get_workspace_feature_flags()
    if "rfq_module_enabled" in body:
        flags["rfq_module_enabled"] = bool(body["rfq_module_enabled"])
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE workspaces SET feature_flags_json = ? WHERE id = 'ws-enterprise-001'",
            (json.dumps(flags, ensure_ascii=False),),
        )
    db.log_audit("FEATURE_FLAGS_UPDATED", "workspace", "ws-enterprise-001", flags, user_id=user["sub"])
    return {"success": True, "feature_flags": flags}


@app.post("/api/v1/workspace/settings")
async def save_workspace_settings_simple(
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    name = body.get("workspace_name") or body.get("name") or "NEXUS Enterprise Workspace"
    ind = body.get("industry") or body.get("industry_context") or "Universal Multi-Domain"
    flags = _get_workspace_feature_flags()
    if "rfq_module_enabled" in body:
        require_role(user, "ADMIN")
        flags["rfq_module_enabled"] = bool(body["rfq_module_enabled"])
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE workspaces SET name = ?, industry_context = ?, feature_flags_json = ? WHERE id = 'ws-enterprise-001'",
            (name, ind, json.dumps(flags, ensure_ascii=False)),
        )
    return {"success": True, "feature_flags": flags}


@app.get("/api/v1/rfq/catalog")
async def get_rfq_catalog_unified():
    md = rfq_workflow_service.get_master_data_dict()
    rules_dict = rfq_workflow_service.get_rules()
    skus = []
    for item in md.get("products", []):
        skus.append({
            "sku": item.get("sku") or item.get("product_id"),
            "name": item.get("name") or item.get("product_name"),
            "category": item.get("category", "Hardware"),
            "unit_cost": item.get("cost_price") or item.get("unit_cost") or 0,
            "list_price": item.get("base_price") or item.get("list_price") or 0,
            "stock_qty": item.get("stock") or item.get("available_qty") or 0
        })
    rules_list = [
        {"rule_code": k, "name": k.replace("_", " ").title(), "description": str(v)}
        for k, v in (rules_dict or {}).items()
    ]
    return {"skus": skus, "rules": rules_list}


@app.get("/api/v1/rfq/projects")
async def list_rfq_projects_unified():
    hist = rfq_workflow_service.get_rfq_history()
    if not hist:
        sample = rfq_workflow_service.get_sample_rfp(1)
        rfq_workflow_service.process_rfp(text=sample["text"], source_type="SAMPLE_1")
        hist = rfq_workflow_service.get_rfq_history()
    projects = []
    for h in hist:
        projects.append({
            "id": h.get("run_db_id") or h.get("rfp_id") or "RFQ-001",
            "title": f"{h.get('customer_name', 'Enterprise')} ({h.get('rfp_id', 'RFQ')})",
            "customer_name": h.get("customer_name", "Enterprise Client"),
            "customer_tier": h.get("customer_tier", "Tier 1"),
            "phase": h.get("status", "Phase 3 - Pricing & Gate Review"),
            "total_amount": h.get("total_value", 0),
            "margin_pct": h.get("margin_pct", 18.5),
            "risk_level": "LOW"
        })
    return {"projects": projects}


@app.post("/api/v1/rfq/projects")
async def create_rfq_project_unified(body: Dict[str, Any]):
    title = body.get("title", "Dự án B2B RFQ")
    cust = body.get("customer_name", "Khách hàng B2B")
    sample = rfq_workflow_service.get_sample_rfp(1)
    res = rfq_workflow_service.process_rfp(text=f"Khách hàng: {cust}\nDự án: {title}\n" + sample["text"], source_type="CUSTOM")
    hist = rfq_workflow_service.get_rfq_history()
    latest = hist[0] if hist else {"run_db_id": "RFQ-NEW", "customer_name": cust}
    return {"success": True, "project": {"id": latest.get("run_db_id"), "title": title, "customer_name": cust}}


@app.get("/api/v1/rfq/projects/{proj_id}")
async def get_rfq_project_detail_unified(proj_id: str):
    hist = rfq_workflow_service.get_rfq_history()
    target_id = proj_id
    if not any(h.get("run_db_id") == proj_id for h in hist) and hist:
        target_id = hist[0]["run_db_id"]
    detail = rfq_workflow_service.get_rfq_run_detail(target_id)
    boq = detail.get("boq_items", [])
    line_items = []
    for idx, b in enumerate(boq):
        line_items.append({
            "id": str(idx),
            "requested_description": b.get("requested_name") or b.get("product_name") or b.get("sku"),
            "matched_sku": b.get("sku") or "SKU-01",
            "quantity": b.get("qty") or b.get("quantity") or 1,
            "unit_price": b.get("final_unit_price") or b.get("unit_price") or 0,
            "line_total": b.get("line_total") or b.get("total_price") or 0,
            "margin_pct": b.get("margin_pct") or 18.0
        })
    with db.get_conn() as conn:
        pos = [dict(r) for r in conn.execute("SELECT * FROM rfq_procurement ORDER BY created_at DESC LIMIT 10").fetchall()]
    for po in pos:
        po["po_number"] = po.get("po_code", "PO-01")
        po["delivery_eta"] = po.get("expected_delivery_date", "5 days")
    return {
        "project": {
            "id": detail.get("run_db_id", proj_id),
            "title": f"{detail.get('customer_name', 'B2B Client')} — {detail.get('rfp_id', 'RFQ')}",
            "customer_name": detail.get("customer_name", "B2B Client"),
            "customer_tier": detail.get("customer_tier", "Tier 1"),
            "phase": detail.get("status", "Pricing & Approval"),
            "total_amount": detail.get("total_value", 0),
            "margin_pct": detail.get("margin_pct", 18.5),
            "risk_level": "LOW"
        },
        "financials": {
            "total_revenue": detail.get("total_value", 0),
            "blended_margin_pct": detail.get("margin_pct", 18.5),
            "risk_level": "LOW"
        },
        "line_items": line_items,
        "procurement_orders": pos
    }


@app.post("/api/v1/rfq/projects/{proj_id}/items")
async def add_rfq_project_item_unified(proj_id: str, body: Dict[str, Any]):
    desc = body.get("requested_description", "Switch Cisco 24 Port")
    qty = body.get("quantity", 5)
    rfq_workflow_service.process_rfp(text=f"Cần báo giá: {qty} bộ {desc}", source_type="BOQ_ADD")
    return {"success": True}


@app.delete("/api/v1/rfq/projects/{proj_id}/items/{item_id}")
async def delete_rfq_project_item_unified(proj_id: str, item_id: str):
    return {"success": True}


@app.post("/api/v1/rfq/projects/{proj_id}/approve")
async def approve_rfq_project_unified(proj_id: str, body: Dict[str, Any]):
    decision = body.get("decision", "APPROVED")
    comment = body.get("comment", "")
    return rfq_workflow_service.submit_manager_decision(decision=decision, comment=comment)


@app.post("/api/v1/rfq/projects/{proj_id}/procurement")
async def create_rfq_project_po_unified(proj_id: str, body: Dict[str, Any]):
    req = ProcurementCreateRequest(
        rfq_run_id=proj_id,
        customer_name="Enterprise Client",
        supplier_name=body.get("supplier_name", "Thiên Minh Supply"),
        sku_summary="BoQ Package",
        total_cost=float(body.get("total_cost", 45000000)),
        expected_delivery_date=body.get("delivery_eta", "7 days")
    )
    return await create_rfq_procurement(req)


@app.post("/api/v1/rfq/projects/{proj_id}/cover-page")
async def save_rfq_cover_page_unified(proj_id: str, body: Dict[str, Any]):
    db.log_audit("RFQ_COVER_PAGE_SAVED", "rfq_project", proj_id, body)
    return {"success": True}


@app.post("/api/v1/rfq/projects/{proj_id}/escalate")
async def escalate_rfq_project_unified(proj_id: str, body: Dict[str, Any]):
    db.log_audit("RFQ_ESCALATED", "rfq_project", proj_id, body)
    return {"success": True}


@app.get("/api/v1/rfq/projects/{proj_id}/export/{fmt}")
async def export_rfq_project_doc_unified(proj_id: str, fmt: str):
    if fmt.lower() == "xlsx":
        return await download_boq_excel_endpoint()
    return await download_proposal_word_endpoint()


# =============================================================================
# 6. STRATEGIC DECISION INTELLIGENCE CENTER ENDPOINTS (STEP 8)
# =============================================================================
@app.get("/api/v1/decision-center/overview")
async def dc_get_overview(project_id: str = "proj-omni-001"):
    return {"success": True, **decision_center_service.get_overview(project_id)}


@app.get("/api/v1/decision-center/objectives")
async def dc_list_objectives(project_id: str = "proj-omni-001"):
    return {"success": True, "objectives": decision_center_service.list_objectives(project_id)}


@app.post("/api/v1/decision-center/objectives")
async def dc_create_objective(
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        obj = decision_center_service.create_objective(body, user=user)
        return {"success": True, "objective": obj}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.get("/api/v1/decision-center/issues")
async def dc_list_issues(project_id: str = "proj-omni-001", issue_type: str = "", status: str = ""):
    return {"success": True, "issues": decision_center_service.list_issues(project_id, issue_type=issue_type, status=status)}


@app.post("/api/v1/decision-center/issues")
async def dc_create_issue(
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        iss = decision_center_service.create_issue(body, user=user)
        return {"success": True, "issue": iss}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.post("/api/v1/decision-center/issues/detect-from-dataset")
async def dc_detect_issues_from_dataset(
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    ds_id = body.get("dataset_id")
    if not ds_id:
        raise HTTPException(status_code=400, detail="Missing 'dataset_id'.")
    try:
        res = decision_center_service.detect_issues_from_dataset(
            dataset_id=ds_id,
            project_id=body.get("project_id", "proj-omni-001"),
            user=user,
        )
        return res
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        status_c = 422 if "Gatekeeper" in str(ve) or "kiểm định" in str(ve) else 400
        raise HTTPException(status_code=status_c, detail=str(ve))


@app.get("/api/v1/decision-center/recommendations")
async def dc_list_recommendations(project_id: str = "proj-omni-001", issue_id: Optional[str] = None):
    return {"success": True, "recommendations": decision_center_service.list_recommendations(project_id, issue_id=issue_id)}


@app.post("/api/v1/decision-center/recommendations/generate")
async def dc_generate_recommendations(
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    issue_id = body.get("issue_id")
    if not issue_id:
        raise HTTPException(status_code=400, detail="Missing 'issue_id'.")
    try:
        return decision_center_service.generate_ai_recommendations(issue_id, user=user)
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        status_c = 422 if "DataEvidenceAgent" in str(ve) or "kiểm định" in str(ve) else 400
        raise HTTPException(status_code=status_c, detail=str(ve))


@app.post("/api/v1/decision-center/recommendations/{rec_id}/action")
async def dc_recommendation_action(
    rec_id: str,
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        rec = decision_center_service.update_recommendation_action(
            rec_id,
            action=body.get("action", "ACCEPT_FOR_REVIEW"),
            user_notes=body.get("user_notes", ""),
            updates=body.get("updates"),
            user=user,
        )
        return {"success": True, "recommendation": rec}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.post("/api/v1/decision-center/decision-matrix/evaluate")
async def dc_evaluate_decision_matrix(body: Dict[str, Any]):
    try:
        res = decision_center_service.evaluate_decision_matrix(
            criteria=body.get("criteria") or [],
            options=body.get("options") or [],
        )
        return {"success": True, **res}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.get("/api/v1/decision-center/scenarios")
async def dc_list_scenarios(project_id: str = "proj-omni-001", recommendation_id: Optional[str] = None):
    return {"success": True, "scenarios": decision_center_service.list_scenarios(project_id, recommendation_id=recommendation_id)}


@app.post("/api/v1/decision-center/scenarios")
async def dc_create_scenario(
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        sc = decision_center_service.create_custom_scenario(body, user=user)
        return {"success": True, "scenario": sc}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.post("/api/v1/decision-center/scenarios/{scenario_id}/recalculate")
async def dc_recalculate_scenario(
    scenario_id: str,
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        res = decision_center_service.recalculate_scenario(
            scenario_id,
            new_assumptions=body.get("assumptions") or body,
            note=body.get("note", ""),
            user=user,
        )
        return {"success": True, **res}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.get("/api/v1/decision-center/decisions")
async def dc_list_decisions(
    project_id: str = "proj-omni-001",
    status: str = "",
    category: str = "",
    search: str = "",
    approver: str = "",
):
    return {
        "success": True,
        "decisions": decision_center_service.list_decisions(project_id, status=status, category=category, search=search, approver=approver),
    }


@app.post("/api/v1/decision-center/decisions")
async def dc_create_decision_draft(
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        dec = decision_center_service.create_decision_draft(body, user=user)
        return {"success": True, "decision": dec}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        status_c = 422 if "Gatekeeper" in str(ve) or "kiểm định" in str(ve) else 400
        raise HTTPException(status_code=status_c, detail=str(ve))


@app.post("/api/v1/decision-center/decisions/{decision_id}/transition")
async def dc_transition_decision(
    decision_id: str,
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        dec = decision_center_service.transition_decision(
            decision_id,
            target_status=body.get("target_status", ""),
            rationale=body.get("rationale", ""),
            approved_budget=body.get("approved_budget"),
            user=user,
            is_ai_caller=bool(body.get("is_ai_caller", False)),
        )
        return {"success": True, "decision": dec}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.post("/api/v1/decision-center/decisions/{decision_id}/submit")
async def dc_submit_decision(
    decision_id: str,
    body: Optional[Dict[str, Any]] = None,
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    b = body or {}
    try:
        dec = decision_center_service.transition_decision(
            decision_id, "PENDING_REVIEW", rationale=b.get("rationale", "Trình lãnh đạo xem xét phê duyệt"), user=user
        )
        return {"success": True, "decision": dec}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.post("/api/v1/decision-center/decisions/{decision_id}/approve")
async def dc_approve_decision(
    decision_id: str,
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        dec = decision_center_service.transition_decision(
            decision_id,
            "APPROVED",
            rationale=body.get("rationale", ""),
            approved_budget=body.get("approved_budget"),
            user=user,
            is_ai_caller=bool(body.get("is_ai_caller", False)),
        )
        return {"success": True, "decision": dec}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.post("/api/v1/decision-center/decisions/{decision_id}/reject")
async def dc_reject_decision(
    decision_id: str,
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    target_st = "REVISION_REQUIRED" if str(body.get("mode", "")).upper() == "REVISION" else "REJECTED"
    try:
        dec = decision_center_service.transition_decision(
            decision_id,
            target_st,
            rationale=body.get("rationale", ""),
            user=user,
            is_ai_caller=bool(body.get("is_ai_caller", False)),
        )
        return {"success": True, "decision": dec}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.get("/api/v1/decision-center/decisions/{decision_id}/lineage")
async def dc_get_decision_lineage(decision_id: str):
    try:
        return {"success": True, **decision_center_service.get_decision_lineage(decision_id)}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@app.get("/api/v1/decision-center/execution")
async def dc_get_execution_workspace(project_id: str = "proj-omni-001"):
    return {"success": True, **decision_center_service.get_execution_workspace(project_id)}


@app.post("/api/v1/decision-center/initiatives")
async def dc_create_initiative(
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        ini = decision_center_service.create_initiative(body, user=user)
        return {"success": True, "initiative": ini}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.post("/api/v1/decision-center/projects")
async def dc_create_strategic_project(
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        prj = decision_center_service.create_strategic_project(body, user=user)
        return {"success": True, "project": prj}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.post("/api/v1/decision-center/milestones")
async def dc_create_milestone(
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        ms = decision_center_service.create_milestone(body, user=user)
        return {"success": True, "milestone": ms}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.put("/api/v1/decision-center/milestones/{milestone_id}/status")
async def dc_update_milestone_status(
    milestone_id: str,
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        ms = decision_center_service.update_milestone_status(milestone_id, body.get("status", "IN_PROGRESS"), body.get("note", ""), user=user)
        return {"success": True, "milestone": ms}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.post("/api/v1/decision-center/risks")
async def dc_create_risk(
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        rk = decision_center_service.create_risk(body, user=user)
        return {"success": True, "risk": rk}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.get("/api/v1/decision-center/kpis")
async def dc_list_kpis(project_id: str = "proj-omni-001", decision_id: Optional[str] = None):
    return {"success": True, "kpis": decision_center_service.list_strategic_kpis_with_tracking(project_id, decision_id=decision_id)}


@app.post("/api/v1/decision-center/kpis")
async def dc_create_kpi(
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        k = decision_center_service.create_strategic_kpi(body, user=user)
        return {"success": True, "kpi": k}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.post("/api/v1/decision-center/kpis/{kpi_id}/actuals")
async def dc_record_kpi_actual(
    kpi_id: str,
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    try:
        res = decision_center_service.record_kpi_actual(kpi_id, body, user=user)
        return {"success": True, **res}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.get("/api/v1/decision-center/reviews")
async def dc_list_reviews(project_id: str = "proj-omni-001", decision_id: Optional[str] = None):
    return {"success": True, "reviews": decision_center_service.list_reviews(project_id, decision_id=decision_id)}


@app.post("/api/v1/decision-center/reviews/evaluate")
async def dc_evaluate_review(
    body: Dict[str, Any],
    x_nexus_role: Optional[str] = Header(default="ADMIN"),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(x_nexus_role, authorization)
    dec_id = body.get("decision_id")
    if not dec_id:
        raise HTTPException(status_code=400, detail="Missing 'decision_id'.")
    try:
        rev = decision_center_service.evaluate_decision_performance(
            dec_id,
            lessons_learned=body.get("lessons_learned", ""),
            follow_up_action=body.get("follow_up_action", ""),
            user=user,
        )
        return {"success": True, "review": rev}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.get("/api/v1/decision-center/history")
async def dc_get_history(
    project_id: str = "proj-omni-001",
    status: str = "",
    category: str = "",
    search: str = "",
    approver: str = "",
):
    return {
        "success": True,
        "decisions": decision_center_service.list_decisions(project_id, status=status, category=category, search=search, approver=approver),
    }


@app.get("/api/v1/decision-center/history/export")
async def dc_export_history(project_id: str = "proj-omni-001"):
    csv_bytes = decision_center_service.export_decision_history_csv(project_id)
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="Nexus_Strategic_Decisions_{project_id}.csv"'},
    )


@app.get("/api/v1/decision-center/notifications")
async def dc_list_notifications(project_id: str = "proj-omni-001"):
    ov = decision_center_service.get_overview(project_id)
    return {"success": True, "alerts": ov["alerts"], "unread_alerts_count": ov["unread_alerts_count"]}


@app.post("/api/v1/decision-center/notifications/{notif_id}/read")
async def dc_mark_notification_read(notif_id: str):
    return decision_center_service.mark_notification_read(notif_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
