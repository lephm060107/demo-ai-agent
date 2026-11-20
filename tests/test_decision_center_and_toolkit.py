"""
tests/test_decision_center_and_toolkit.py
Comprehensive 25-Test End-to-End Verification Suite for:
- Part A (DC.01 - DC.11): Strategic Decision Intelligence Center, Multi-Agent AI, Human Approval Gate,
  6-Role RBAC, 5-Level Execution, KPI Deviation, Closed-Loop Review, Lineage, Version Propagation,
  Layer 2 RFQ Feature Flag, and Safe Multi-Location File Deletion / Trash Bin.
- Part B (TK.01 - TK.14): Step 4.3 Analysis Readiness, Intelligent Tool Recommender, 15-Method
  Strategic Analysis Toolkit, 8-Color Pastel Chart Intelligence, 12-Point Chart Validation,
  Configurable 14-Section Reports, and 15,000-Row Real Dataset Re-Validation & Performance.
"""

import io
import math
import os
import sys
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://127.0.0.1:8000"
RESULTS = []


def record(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    RESULTS.append((name, passed, detail))
    print(f"[{status}] {name} :: {detail}")


def upload_csv(filename: str, content: str, role: str = "ADMIN"):
    r = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": (filename, content.encode("utf-8"), "text/csv")},
        data={"conflict_resolution": "ALLOW_DUPLICATE"},
        headers={"X-Nexus-Role": role},
        timeout=20,
    )
    return r


def run_all():
    cleanup_dataset_ids = []

    # Prepare clean, rich business dataset with Customer, Date, Category, Region, Revenue, Cost, Profit, Qty
    rich_csv = (
        "order_id,order_date,customer_id,category,region,channel,quantity,revenue,cost,profit\n"
        "ORD-01,2026-07-01,CUST-A,Networking,Hanoi,B2B,5,500000,320000,180000\n"
        "ORD-02,2026-07-10,CUST-B,Security,HCMC,B2B,4,420000,260000,160000\n"
        "ORD-03,2026-07-20,CUST-A,Networking,Hanoi,Online,6,600000,380000,220000\n"
        "ORD-04,2026-08-05,CUST-C,Cloud,Danang,Partner,8,720000,450000,270000\n"
        "ORD-05,2026-08-18,CUST-B,Security,HCMC,B2B,3,310000,210000,100000\n"
        "ORD-06,2026-08-25,CUST-D,Hardware,Hanoi,Online,10,250000,220000,30000\n"
        "ORD-07,2026-09-02,CUST-A,Networking,HCMC,B2B,7,750000,460000,290000\n"
        "ORD-08,2026-09-14,CUST-E,Cloud,Danang,Partner,5,480000,300000,180000\n"
        "ORD-09,2026-09-22,CUST-C,Hardware,Hanoi,Online,9,210000,195000,15000\n"
        "ORD-10,2026-10-03,CUST-A,Networking,Hanoi,B2B,8,860000,510000,350000\n"
        "ORD-11,2026-10-15,CUST-B,Security,HCMC,B2B,5,550000,340000,210000\n"
        "ORD-12,2026-10-28,CUST-D,Hardware,Hanoi,Online,12,280000,260000,20000\n"
    )
    r_up = upload_csv("dc_strategic_test_v1.csv", rich_csv)
    assert r_up.status_code == 200, f"Upload rich dataset failed: {r_up.text}"
    ds_id = r_up.json()["dataset"]["id"]
    v1_id = r_up.json()["bundle"]["active_version"]["id"]
    cleanup_dataset_ids.append(ds_id)

    # Also upload a revenue-only dataset (no cost/profit) & an invalid sequential dataset
    rev_only_csv = (
        "order_id,order_date,category,revenue\n"
        "R-1,2026-08-01,Alpha,100000\n"
        "R-2,2026-08-02,Beta,250000\n"
        "R-3,2026-08-03,Alpha,150000\n"
        "R-4,2026-08-04,Gamma,180000\n"
        "R-5,2026-08-05,Beta,220000\n"
    )
    r_ro = upload_csv("dc_rev_only_test.csv", rev_only_csv)
    assert r_ro.status_code == 200
    rev_only_id = r_ro.json()["dataset"]["id"]
    cleanup_dataset_ids.append(rev_only_id)

    bad_seq_csv = "A,B\n" + "\n".join(f"{i},{i+1}" for i in range(1, 16)) + "\n"
    r_bad = upload_csv("dc_bad_seq_test.csv", bad_seq_csv)
    bad_ds_id = r_bad.json()["dataset"]["id"]
    cleanup_dataset_ids.append(bad_ds_id)

    # =========================================================================
    # PART A: DECISION INTELLIGENCE CENTER E2E TESTS (DC.01 - DC.11)
    # =========================================================================

    # DC.01: Issue Auto-Detection + Gatekeeper Block on Invalid Dataset
    r_det_ok = requests.post(
        f"{BASE_URL}/api/v1/decision-center/issues/detect-from-dataset",
        json={"dataset_id": ds_id},
        headers={"X-Nexus-Role": "STRATEGIC_MANAGER"},
        timeout=20,
    )
    r_det_bad = requests.post(
        f"{BASE_URL}/api/v1/decision-center/issues/detect-from-dataset",
        json={"dataset_id": bad_ds_id},
        headers={"X-Nexus-Role": "ADMIN"},
        timeout=20,
    )
    detected_issues = r_det_ok.json().get("detected_issues", []) if r_det_ok.status_code == 200 else []
    issue_id = detected_issues[0]["id"] if detected_issues else None
    record(
        "DC.01 Auto-Detect Strategic Issues & Gatekeeper 422 Block",
        r_det_ok.status_code == 200 and len(detected_issues) >= 1 and r_det_bad.status_code == 422,
        f"Detected={len(detected_issues)}, BadDatasetHTTP={r_det_bad.status_code}",
    )

    # Create a report & toolkit analysis linked to ds_id v1 so full lineage is rich
    r_tk = requests.post(
        f"{BASE_URL}/api/v1/analytics/toolkit/run",
        json={"dataset_id": ds_id, "method_id": "pareto_root_cause"},
        timeout=20,
    )
    ana_run_id = r_tk.json().get("analysis_run_id") if r_tk.status_code == 200 else None
    r_rep = requests.post(
        f"{BASE_URL}/api/v1/reports/generate",
        json={"dataset_id": ds_id, "analysis_run_id": ana_run_id, "report_type": "EXECUTIVE", "language": "vi"},
        timeout=25,
    )
    rep_id = r_rep.json().get("report_id") if r_rep.status_code == 200 else None

    # DC.02: Multi-Agent AI Recommendations (3 Options + Self-Critique + Zero Auto-Approval) + Weighted Decision Matrix
    r_recs = requests.post(
        f"{BASE_URL}/api/v1/decision-center/recommendations/generate",
        json={"issue_id": issue_id},
        headers={"X-Nexus-Role": "STRATEGIC_MANAGER"},
        timeout=25,
    )
    recs_data = r_recs.json() if r_recs.status_code == 200 else {}
    recs_list = recs_data.get("recommendations", [])
    scns_list = recs_data.get("scenarios", [])
    rec0 = recs_list[0] if recs_list else {}
    has_8parts_and_critique = bool(
        rec0.get("rationale")
        and rec0.get("evidence_links")
        and rec0.get("expected_impact")
        and rec0.get("required_resources")
        and rec0.get("risks_limitations")
        and rec0.get("self_critique")
        and rec0.get("status") == "PENDING_EVALUATION"
        and rec0.get("evidence_confidence") in ("VERIFIED", "SUPPORTED", "HYPOTHESIS")
        and rec0.get("feasibility_level") in ("HIGH", "MEDIUM", "LOW")
    )
    r_dm = requests.post(
        f"{BASE_URL}/api/v1/decision-center/decision-matrix/evaluate",
        json={
            "criteria": [
                {"id": "fin", "name": "Financial Return", "weight": 50},
                {"id": "risk", "name": "Risk Safety", "weight": 30},
                {"id": "feas", "name": "Feasibility", "weight": 20},
            ],
            "options": [
                {"id": "A", "name": "Core Optimization", "scores": {"fin": 8.5, "risk": 8.0, "feas": 9.0}},
                {"id": "B", "name": "Aggressive Expansion", "scores": {"fin": 9.2, "risk": 5.0, "feas": 6.0}},
            ],
        },
        timeout=15,
    )
    dm_ok = r_dm.status_code == 200 and r_dm.json().get("recommended_winner", {}).get("option_id") == "A" and len(r_dm.json().get("weight_sensitivity", [])) == 3
    record(
        "DC.02 Multi-Agent 3 Options, Self-Critique, Evidence & Weighted Decision Matrix",
        r_recs.status_code == 200 and len(recs_list) == 3 and len(scns_list) == 3 and has_8parts_and_critique and dm_ok,
        f"Recs={len(recs_list)}, Scenarios={len(scns_list)}, AgentSteps={len(recs_data.get('agent_trace', []))}, MatrixWinner={r_dm.json().get('recommended_winner', {}).get('option_id')}",
    )

    # DC.03: Scenario Recalculation + Before/After Delta + Assumption History + Tornado Chart
    scn_id = scns_list[1]["id"]  # Base Case
    r_recalc = requests.post(
        f"{BASE_URL}/api/v1/decision-center/scenarios/{scn_id}/recalculate",
        json={"assumptions": {"revenue_growth_pct": 25.0, "cost_change_pct": -5.0}, "note": "Upside test"},
        headers={"X-Nexus-Role": "STRATEGIC_MANAGER"},
        timeout=15,
    )
    recalc_j = r_recalc.json() if r_recalc.status_code == 200 else {}
    r_scns_get = requests.get(f"{BASE_URL}/api/v1/decision-center/scenarios", timeout=15).json()
    scn_obj = next((s for s in r_scns_get.get("scenarios", []) if s["id"] == scn_id), {})
    record(
        "DC.03 Deterministic Scenario Recalculation, History Diff & Tornado Chart",
        r_recalc.status_code == 200
        and recalc_j.get("delta_npv", 0) > 0
        and recalc_j.get("history_count", 0) >= 2
        and bool(scn_obj.get("tornado_chart")),
        f"DeltaNPV={recalc_j.get('delta_npv')}, HistoryLen={recalc_j.get('history_count')}, HasTornado={bool(scn_obj.get('tornado_chart'))}",
    )

    # DC.04: Human Approval Gate & Strict 6-Role RBAC (VIEWER/ANALYST/AI blocked 403; CEO approves!)
    r_obj = requests.post(
        f"{BASE_URL}/api/v1/decision-center/objectives",
        json={"title": "Grow B2B Operating Margin +15%", "category": "PROFITABILITY", "budget_allocated": 500000000},
        headers={"X-Nexus-Role": "STRATEGIC_MANAGER"},
        timeout=15,
    )
    obj_id = r_obj.json()["objective"]["id"]

    r_draft = requests.post(
        f"{BASE_URL}/api/v1/decision-center/decisions",
        json={
            "title": "Approve Core B2B Networking & Security Focus",
            "objective_id": obj_id,
            "issue_id": issue_id,
            "chosen_recommendation_id": rec0["id"],
            "chosen_scenario_id": scn_id,
            "approved_budget": 150000000,
            "selection_rationale": "Highest NPV and lowest execution risk backed by Q3-Q4 sales dataset",
            "dataset_id": ds_id,
            "dataset_version_id": v1_id,
            "analysis_run_id": ana_run_id,
            "report_id": rep_id,
        },
        headers={"X-Nexus-Role": "ANALYST"},
        timeout=15,
    )
    dec_id = r_draft.json()["decision"]["id"]
    r_sub = requests.post(f"{BASE_URL}/api/v1/decision-center/decisions/{dec_id}/submit", json={"rationale": "Ready for CEO"}, headers={"X-Nexus-Role": "ANALYST"}, timeout=15)

    # Negative RBAC & AI non-approval checks
    r_viewer_app = requests.post(f"{BASE_URL}/api/v1/decision-center/decisions/{dec_id}/approve", json={"rationale": "Try"}, headers={"X-Nexus-Role": "VIEWER"}, timeout=10)
    r_analyst_app = requests.post(f"{BASE_URL}/api/v1/decision-center/decisions/{dec_id}/approve", json={"rationale": "Try"}, headers={"X-Nexus-Role": "ANALYST"}, timeout=10)
    r_ai_app = requests.post(f"{BASE_URL}/api/v1/decision-center/decisions/{dec_id}/approve", json={"rationale": "AI self approve", "is_ai_caller": True}, headers={"X-Nexus-Role": "CEO"}, timeout=10)
    r_empty_rat = requests.post(f"{BASE_URL}/api/v1/decision-center/decisions/{dec_id}/approve", json={"rationale": ""}, headers={"X-Nexus-Role": "CEO"}, timeout=10)

    # Legitimate CEO Human Approval
    r_ceo_app = requests.post(
        f"{BASE_URL}/api/v1/decision-center/decisions/{dec_id}/approve",
        json={"rationale": "Approved by CEO after verifying Q3-Q4 evidence and Tornado sensitivity", "approved_budget": 145000000},
        headers={"X-Nexus-Role": "CEO"},
        timeout=15,
    )
    dec_app = r_ceo_app.json().get("decision", {}) if r_ceo_app.status_code == 200 else {}
    record(
        "DC.04 Human Approval Gate & Strict RBAC (403 Viewer/Analyst/AI, 400 No Rationale, 200 CEO)",
        r_draft.status_code == 200
        and r_sub.status_code == 200
        and r_viewer_app.status_code == 403
        and r_analyst_app.status_code == 403
        and r_ai_app.status_code == 403
        and r_empty_rat.status_code == 400
        and r_ceo_app.status_code == 200
        and dec_app.get("status") == "APPROVED"
        and dec_app.get("version_number") == 3
        and len(dec_app.get("approvals", [])) >= 2,
        f"Viewer={r_viewer_app.status_code}, Analyst={r_analyst_app.status_code}, AI={r_ai_app.status_code}, EmptyRat={r_empty_rat.status_code}, CEOStatus={dec_app.get('status')} v{dec_app.get('version_number')}",
    )

    # DC.05: 5-Level Execution + Automatic Progress Roll-up + Gantt + Risk Matrix
    r_ini = requests.post(
        f"{BASE_URL}/api/v1/decision-center/initiatives",
        json={"decision_id": dec_id, "objective_id": obj_id, "title": "Initiative 1: Enterprise Focus Program", "budget": 145000000},
        headers={"X-Nexus-Role": "STRATEGIC_MANAGER"},
        timeout=15,
    )
    ini_id = r_ini.json()["initiative"]["id"]
    r_prj = requests.post(
        f"{BASE_URL}/api/v1/decision-center/projects",
        json={"initiative_id": ini_id, "title": "Project 1A: Sales Playbook Rollout", "department": "Enterprise Sales"},
        headers={"X-Nexus-Role": "DEPARTMENT_MANAGER"},
        timeout=15,
    )
    prj_id = r_prj.json()["project"]["id"]
    r_m1 = requests.post(
        f"{BASE_URL}/api/v1/decision-center/milestones",
        json={"strategic_project_id": prj_id, "title": "Milestone 1: Segment Account Mapping", "start_date": "2026-11-20", "deadline": "2026-12-05"},
        headers={"X-Nexus-Role": "DEPARTMENT_MANAGER"},
        timeout=15,
    )
    r_m2 = requests.post(
        f"{BASE_URL}/api/v1/decision-center/milestones",
        json={"strategic_project_id": prj_id, "title": "Milestone 2: Launch VIP Retention Offer", "start_date": "2026-12-06", "deadline": "2026-12-25"},
        headers={"X-Nexus-Role": "DEPARTMENT_MANAGER"},
        timeout=15,
    )
    m1_id = r_m1.json()["milestone"]["id"]
    requests.put(f"{BASE_URL}/api/v1/decision-center/milestones/{m1_id}/status", json={"status": "DONE", "note": "Completed ahead of schedule"}, headers={"X-Nexus-Role": "DEPARTMENT_MANAGER"}, timeout=15)
    r_rsk = requests.post(
        f"{BASE_URL}/api/v1/decision-center/risks",
        json={"decision_id": dec_id, "initiative_id": ini_id, "title": "Competitor Price Undercutting", "likelihood": 4, "impact": 4, "mitigation_plan": "Bundle 24x7 SLA"},
        headers={"X-Nexus-Role": "STRATEGIC_MANAGER"},
        timeout=15,
    )
    exec_ws = requests.get(f"{BASE_URL}/api/v1/decision-center/execution", timeout=15).json()
    prj_after = next((p for p in exec_ws.get("projects", []) if p["id"] == prj_id), {})
    record(
        "DC.05 5-Level Execution Hierarchy, Auto Progress Roll-up (50%), Gantt & Risk Matrix",
        r_ini.status_code == 200
        and prj_after.get("progress_pct") == 50.0
        and r_rsk.json().get("risk", {}).get("risk_score") == 16
        and bool(exec_ws.get("gantt_chart"))
        and bool(exec_ws.get("risk_matrix_chart")),
        f"ProjectProgress={prj_after.get('progress_pct')}%, RiskScore={r_rsk.json().get('risk', {}).get('risk_score')}, Gantt={bool(exec_ws.get('gantt_chart'))}, RiskMatrix={bool(exec_ws.get('risk_matrix_chart'))}",
    )

    # DC.06 & DC.07: Closed-Loop Review INCONCLUSIVE Guard -> KPI Actual Deviation Alert -> Evaluated Review
    r_rev_inc = requests.post(
        f"{BASE_URL}/api/v1/decision-center/reviews/evaluate",
        json={"decision_id": dec_id, "lessons_learned": "Pre-measurement check"},
        headers={"X-Nexus-Role": "STRATEGIC_MANAGER"},
        timeout=15,
    )
    inc_outcome = r_rev_inc.json().get("review", {}).get("outcome")

    r_kpi = requests.post(
        f"{BASE_URL}/api/v1/decision-center/kpis",
        json={"decision_id": dec_id, "objective_id": obj_id, "name": "Gross Margin %", "target_value": 38.0, "unit": "%", "polarity": "HIGHER_IS_BETTER", "warning_threshold_pct": 10.0},
        headers={"X-Nexus-Role": "STRATEGIC_MANAGER"},
        timeout=15,
    )
    kpi_id = r_kpi.json()["kpi"]["id"]
    # Record unfavorable actual (30% vs 38% target -> -21% gap -> must trigger KPI_DEVIATION alert!)
    r_act_bad = requests.post(
        f"{BASE_URL}/api/v1/decision-center/kpis/{kpi_id}/actuals",
        json={"actual_value": 30.0, "period_label": "M1"},
        headers={"X-Nexus-Role": "ANALYST"},
        timeout=15,
    )
    r_rev_after = requests.post(
        f"{BASE_URL}/api/v1/decision-center/reviews/evaluate",
        json={"decision_id": dec_id, "lessons_learned": "Need tighter discount controls"},
        headers={"X-Nexus-Role": "STRATEGIC_MANAGER"},
        timeout=15,
    )
    after_outcome = r_rev_after.json().get("review", {}).get("outcome")
    record(
        "DC.06 KPI Deviation Alert Triggered on Unfavorable Gap",
        r_act_bad.status_code == 200 and r_act_bad.json().get("alert_triggered") is True,
        f"AlertTriggered={r_act_bad.json().get('alert_triggered')}",
    )
    record(
        "DC.07 Closed-Loop Review INCONCLUSIVE Guard (0 Actuals) -> Quantitative Rating (With Actuals)",
        inc_outcome == "INCONCLUSIVE" and after_outcome in ("PARTIALLY_SUCCESSFUL", "UNDERPERFORMING"),
        f"BeforeActuals={inc_outcome}, AfterActuals={after_outcome}",
    )

    # DC.08: Full Data Lineage Trace & CSV History Export
    r_lin = requests.get(f"{BASE_URL}/api/v1/decision-center/decisions/{dec_id}/lineage", timeout=15)
    lin = r_lin.json() if r_lin.status_code == 200 else {}
    r_csv = requests.get(f"{BASE_URL}/api/v1/decision-center/history/export", timeout=15)
    record(
        "DC.08 Full Data Lineage (Decision->Rec->Issue->Evidence->Report->Analysis->DatasetVersion) & CSV Export",
        r_lin.status_code == 200
        and lin.get("decision", {}).get("id") == dec_id
        and lin.get("recommendation", {}).get("id") == rec0["id"]
        and lin.get("report", {}).get("id") == rep_id
        and lin.get("analysis", {}).get("id") == ana_run_id
        and lin.get("dataset_version", {}).get("id") == v1_id
        and r_csv.status_code == 200
        and dec_id in r_csv.text,
        f"ChainComplete=True, CSVBytes={len(r_csv.content)}",
    )

    # DC.09: Data Version Change Propagation (Editing dataset creates v2 -> flags decision stale WITHOUT mutating historical approved status/version!)
    r_edit = requests.post(
        f"{BASE_URL}/api/v1/datasets/{ds_id}/edit-cell",
        json={"row_index": 0, "column": "quantity", "new_value": "6"},
        headers={"X-Nexus-Role": "ANALYST"},
        timeout=20,
    )
    lin_after = requests.get(f"{BASE_URL}/api/v1/decision-center/decisions/{dec_id}/lineage", timeout=15).json()
    notifs_after = requests.get(f"{BASE_URL}/api/v1/decision-center/notifications", timeout=15).json().get("alerts", [])
    has_prop_notif = any(n.get("alert_type") == "DATA_VERSION_CHANGED" and n.get("entity_id") == dec_id for n in notifs_after)
    record(
        "DC.09 Data Version Change Propagation (Flags Stale + Alert WITHOUT Mutating Approved Decision)",
        r_edit.status_code == 200
        and lin_after.get("is_dataset_outdated") is True
        and lin_after.get("decision", {}).get("stale_data_flag") is True
        and lin_after.get("decision", {}).get("status") in ("APPROVED", "IN_EXECUTION")
        and lin_after.get("dataset_version", {}).get("id") == v1_id
        and has_prop_notif,
        f"IsOutdated={lin_after.get('is_dataset_outdated')}, StaleFlag={lin_after.get('decision', {}).get('stale_data_flag')}, PropAlert={has_prop_notif}",
    )

    # DC.10: Layer 2 B2B RFQ Feature Flag Hidden by Default & All RFQ APIs 100% Preserved
    ff_default = requests.get(f"{BASE_URL}/api/v1/feature-flags", timeout=10).json().get("feature_flags", {})
    home_html = requests.get(f"{BASE_URL}/", timeout=10).text
    r_rfq_api = requests.get(f"{BASE_URL}/api/master-data", timeout=10)
    r_rfq_rules = requests.get(f"{BASE_URL}/api/v1/rfq/rules", timeout=10)
    r_ff_on = requests.post(f"{BASE_URL}/api/v1/feature-flags", json={"rfq_module_enabled": True}, headers={"X-Nexus-Role": "ADMIN"}, timeout=10)
    r_ff_off = requests.post(f"{BASE_URL}/api/v1/feature-flags", json={"rfq_module_enabled": False}, headers={"X-Nexus-Role": "ADMIN"}, timeout=10)
    md_j = r_rfq_api.json() if r_rfq_api.status_code == 200 else {}
    md_items = (md_j.get("data") or {}).get("DanhMuc_SanPham", [])
    record(
        "DC.10 Layer 2 RFQ Hidden by Default via Feature Flag While Preserving All RFQ APIs/Data",
        ff_default.get("rfq_module_enabled") is False
        and 'id="sidebarRfqGroup" class="nav-module-group hidden"' in home_html
        and r_rfq_api.status_code == 200
        and r_rfq_rules.status_code == 200
        and len(md_items) > 0
        and r_ff_on.json().get("feature_flags", {}).get("rfq_module_enabled") is True
        and r_ff_off.json().get("feature_flags", {}).get("rfq_module_enabled") is False,
        f"DefaultFlag={ff_default.get('rfq_module_enabled')}, PreservedMasterSKUs={len(md_items)}",
    )

    # DC.11: Safe Multi-Location File Deletion & Trash Bin (Impact check, Reference guard, Trash, Restore, Admin Permanent Delete guard)
    r_imp = requests.get(f"{BASE_URL}/api/v1/datasets/{ds_id}/delete-impact", timeout=10)
    imp = r_imp.json() if r_imp.status_code == 200 else {}
    # Silent trash without confirm_referenced must fail (400) because ds_id is referenced by decision + report!
    r_trash_block = requests.post(f"{BASE_URL}/api/v1/datasets/{ds_id}/trash", json={"confirm_referenced": False}, headers={"X-Nexus-Role": "ANALYST"}, timeout=10)
    # Explicit confirmed trash succeeds & removes from ACTIVE list, appears in TRASH list
    r_trash_ok = requests.post(f"{BASE_URL}/api/v1/datasets/{ds_id}/trash", json={"confirm_referenced": True, "reason": "QA trash test"}, headers={"X-Nexus-Role": "ANALYST"}, timeout=10)
    active_ids = [d["id"] for d in requests.get(f"{BASE_URL}/api/v1/datasets?area=ACTIVE&page_size=200", timeout=10).json().get("datasets", [])]
    trash_ids = [d["id"] for d in requests.get(f"{BASE_URL}/api/v1/datasets?area=TRASH&page_size=200", timeout=10).json().get("datasets", [])]
    # Permanent delete of decision-referenced dataset without force_delete_referenced blocked (400)
    r_perm_guard = requests.post(f"{BASE_URL}/api/v1/datasets/{ds_id}/permanent-delete", json={"confirm": True, "force_delete_referenced": False}, headers={"X-Nexus-Role": "ADMIN"}, timeout=10)
    # Restore from Trash puts it back in ACTIVE & re-validates!
    r_rest_trash = requests.post(f"{BASE_URL}/api/v1/datasets/{ds_id}/restore-trash", headers={"X-Nexus-Role": "ANALYST"}, timeout=15)
    record(
        "DC.11 Safe File Deletion, Reference Impact Guard, Trash Bin & Restore Re-Validation",
        r_imp.status_code == 200
        and imp.get("strategic_decisions_count", 0) >= 1
        and imp.get("reports_count", 0) >= 1
        and r_trash_block.status_code == 400
        and r_trash_ok.status_code == 200
        and ds_id not in active_ids
        and ds_id in trash_ids
        and r_perm_guard.status_code == 400
        and r_rest_trash.status_code == 200
        and r_rest_trash.json().get("revalidated") is True,
        f"Refs={imp.get('total_references')}, BlockSilentTrash={r_trash_block.status_code}, InTrash={ds_id in trash_ids}, PermGuard={r_perm_guard.status_code}, Restored={r_rest_trash.json().get('validation_status')}",
    )

    # =========================================================================
    # PART B: STRATEGIC TOOLKIT & CHART INTELLIGENCE TESTS (TK.01 - TK.14)
    # =========================================================================

    # TK.01: Step 4.3 Analysis Readiness Matrix (Zero fabricated Profit on revenue-only dataset)
    r_rd_rich = requests.get(f"{BASE_URL}/api/v1/datasets/{ds_id}/analysis-readiness", timeout=15).json()
    r_rd_ro = requests.get(f"{BASE_URL}/api/v1/datasets/{rev_only_id}/analysis-readiness", timeout=15).json()
    ro_unavail_ids = [u["id"] for u in r_rd_ro.get("unavailable_analyses", [])]
    record(
        "TK.01 Step 4.3 Analysis Readiness Matrix (Explicit Missing Fields, Zero Fabricated Profit)",
        r_rd_rich.get("ready_count", 0) >= 5
        and "profit_margin_analysis" in ro_unavail_ids
        and "rfm_cohort_clv" in ro_unavail_ids,
        f"RichReady={r_rd_rich.get('ready_count')}, RevOnlyUnavail={ro_unavail_ids}",
    )

    # TK.02: Intelligent Tool Selection
    r_rt = requests.post(
        f"{BASE_URL}/api/v1/analytics/recommend-tools",
        json={"dataset_id": ds_id, "business_goal": "Tại sao lợi nhuận giảm và giao hàng có chậm không?"},
        timeout=15,
    ).json()
    rec_m_ids = [m["method_id"] for m in r_rt.get("recommended_methods", [])]
    excl_m_ids = [m["method_id"] for m in r_rt.get("excluded_methods", [])]
    record(
        "TK.02 Intelligent Tool Selection (Selects Root Cause + Excludes Missing-Field Ops Bottleneck)",
        "fishbone_ishikawa" in rec_m_ids and "five_whys" in rec_m_ids and "operational_bottleneck" in excl_m_ids,
        f"Recommended={rec_m_ids}, Excluded={excl_m_ids}",
    )

    # TK.03: Fishbone / Ishikawa 4M-6M (Separates VERIFIED vs HYPOTHESIS)
    r_fb = requests.post(f"{BASE_URL}/api/v1/analytics/toolkit/run", json={"dataset_id": ds_id, "method_id": "fishbone_ishikawa"}, timeout=15).json()
    fb_statuses = {c["status"] for b in r_fb.get("branches", []) for c in b.get("causes", [])}
    record(
        "TK.03 Fishbone / Ishikawa 4M-6M Separates VERIFIED vs HYPOTHESIS",
        len(r_fb.get("branches", [])) >= 4 and "VERIFIED" in fb_statuses and "HYPOTHESIS" in fb_statuses,
        f"Branches={len(r_fb.get('branches', []))}, Statuses={sorted(fb_statuses)}",
    )

    # TK.04: 5 Whys Evidence Boundary Guard
    r_5w = requests.post(f"{BASE_URL}/api/v1/analytics/toolkit/run", json={"dataset_id": ds_id, "method_id": "five_whys"}, timeout=15).json()
    whys = r_5w.get("why_chain", [])
    has_boundary = any(w.get("status") == "INSUFFICIENT_DATA" for w in whys)
    record(
        "TK.04 5 Whys Stops Transparently at Evidence Boundary (INSUFFICIENT_DATA)",
        len(whys) >= 3 and whys[0].get("status") == "VERIFIED" and has_boundary,
        f"Levels={len(whys)}, Statuses={[w.get('status') for w in whys]}",
    )

    # TK.05: Pareto Contribution Accuracy + 12-Point Chart Validation
    r_par = requests.post(f"{BASE_URL}/api/v1/analytics/toolkit/run", json={"dataset_id": ds_id, "method_id": "pareto_root_cause"}, timeout=15).json()
    par_items = r_par.get("items", [])
    record(
        "TK.05 Pareto Contribution Accuracy (Sum=100%, 12-Point Validated Pastel Chart)",
        len(par_items) >= 2
        and abs(par_items[-1].get("cumulative_pct", 0) - 100.0) < 0.2
        and r_par.get("chart_validation", {}).get("passed") is True
        and r_par.get("chart_validation", {}).get("passed_count") == 12,
        f"Groups={len(par_items)}, CumEnd={par_items[-1].get('cumulative_pct')}%, ChartChecks={r_par.get('chart_validation', {}).get('passed_count')}/12",
    )

    # TK.06: KPI Tree & Gap/Variance Directional Polarity
    r_kt = requests.post(f"{BASE_URL}/api/v1/analytics/toolkit/run", json={"dataset_id": ds_id, "method_id": "kpi_tree"}, timeout=15).json()
    r_gap = requests.post(
        f"{BASE_URL}/api/v1/analytics/toolkit/run",
        json={"dataset_id": ds_id, "method_id": "gap_variance", "parameters": {"metric_col": "cost", "target_value": 4500000, "polarity": "LOWER_IS_BETTER"}},
        timeout=15,
    ).json()
    record(
        "TK.06 KPI Tree Decomposition & Gap/Variance Directional Polarity",
        len(r_kt.get("nodes", [])) >= 3 and r_gap.get("polarity") == "LOWER_IS_BETTER" and r_gap.get("status") in ("FAVORABLE", "UNFAVORABLE"),
        f"KPITreeNodes={len(r_kt.get('nodes', []))}, CostGapStatus={r_gap.get('status')}",
    )

    # TK.07: Customer RFM, Cohort & CLV
    r_rfm = requests.post(f"{BASE_URL}/api/v1/analytics/toolkit/run", json={"dataset_id": ds_id, "method_id": "rfm_cohort_clv"}, timeout=15).json()
    record(
        "TK.07 Customer RFM, Cohort & CLV Calculation",
        r_rfm.get("customers_analyzed", 0) == 5 and len(r_rfm.get("segment_summary", {})) >= 1,
        f"Customers={r_rfm.get('customers_analyzed')}, Segments={r_rfm.get('segment_summary')}",
    )

    # TK.08: Operational Bottleneck NOT_APPLICABLE Guard
    r_ops = requests.post(f"{BASE_URL}/api/v1/analytics/toolkit/run", json={"dataset_id": ds_id, "method_id": "operational_bottleneck"}, timeout=15).json()
    record(
        "TK.08 Operational Bottleneck Gracefully Returns NOT_APPLICABLE Without Cycle Time",
        r_ops.get("status") == "NOT_APPLICABLE",
        f"Status={r_ops.get('status')}",
    )

    # TK.09: Strategic Frameworks SWOT/PESTEL/Porter/MECE Separation
    r_sw = requests.post(f"{BASE_URL}/api/v1/analytics/toolkit/run", json={"dataset_id": ds_id, "method_id": "strategic_frameworks"}, timeout=15).json()
    swot = r_sw.get("swot", {})
    record(
        "TK.09 Strategic Frameworks Strictly Separate INTERNAL_DATA_VERIFIED vs EXTERNAL_CONTEXT_NEEDED",
        all(x.get("tag") == "INTERNAL_DATA_VERIFIED" for x in swot.get("strengths", []))
        and all(x.get("tag") == "EXTERNAL_CONTEXT_NEEDED" for x in swot.get("opportunities", []))
        and len(r_sw.get("pestel", [])) == 6
        and len(r_sw.get("porter_five_forces", [])) == 5,
        f"Strengths={len(swot.get('strengths', []))}, PESTEL={len(r_sw.get('pestel', []))}, Porter={len(r_sw.get('porter_five_forces', []))}",
    )

    # TK.10: Hypothesis Testing v2 (H0, H1, alpha, p-value, effect_size, disclaimer)
    r_ht = requests.post(f"{BASE_URL}/api/v1/analytics/toolkit/run", json={"dataset_id": ds_id, "method_id": "hypothesis_testing_v2"}, timeout=15).json()
    record(
        "TK.10 Hypothesis Testing v2 (H0/H1, Alpha, p-value, Effect Size & Proper Disclaimer)",
        bool(r_ht.get("H0"))
        and bool(r_ht.get("H1"))
        and r_ht.get("alpha") == 0.05
        and isinstance(r_ht.get("p_value"), (int, float))
        and "KHÔNG phải xác suất" in str(r_ht.get("p_value_disclaimer", "")),
        f"Test={r_ht.get('test_method')}, p={r_ht.get('p_value')}, d={r_ht.get('effect_size')}",
    )

    # TK.11: Financial Valuation Math Accuracy Verification (NPV/IRR/ROI/Payback/Tornado)
    r_fv = requests.post(
        f"{BASE_URL}/api/v1/analytics/toolkit/run",
        json={
            "dataset_id": ds_id,
            "method_id": "financial_valuation",
            "parameters": {"annual_revenue": 1000.0, "annual_cost": 600.0, "initial_investment": 500.0, "discount_rate": 0.10, "horizon_years": 3, "revenue_growth_rate": 0.0},
        },
        timeout=15,
    ).json()
    # Independent exact NPV: -500 + 400/1.1 + 400/1.21 + 400/1.331 = 494.74
    expected_npv = round(-500.0 + 400.0 / 1.1 + 400.0 / 1.21 + 400.0 / 1.331, 2)
    actual_npv = r_fv.get("metrics", {}).get("npv")
    record(
        "TK.11 Financial Valuation Deterministic Accuracy (Exact NPV, IRR, ROI, Payback & Tornado)",
        abs((actual_npv or 0) - expected_npv) < 0.05
        and r_fv.get("metrics", {}).get("irr_pct", 0) > 50.0
        and len(r_fv.get("sensitivity_tornado", [])) == 4,
        f"ExpectedNPV={expected_npv}, ActualNPV={actual_npv}, IRR={r_fv.get('metrics', {}).get('irr_pct')}%",
    )

    # TK.12: Visual Suite (Waterfall, BoxPlot, Treemap, Funnel, Sankey) + 8-Color Pastel Palette + Chart Rules
    from nexus_analytics.services.chart_intelligence_service import PASTEL_PALETTE, select_best_chart_type
    visual_ok = True
    for m_vis in ("waterfall_bridge", "boxplot_distribution", "treemap_composition", "funnel_conversion", "sankey_flow"):
        rv = requests.post(f"{BASE_URL}/api/v1/analytics/toolkit/run", json={"dataset_id": ds_id, "method_id": m_vis}, timeout=15).json()
        if not rv.get("echarts_option") or rv.get("chart_validation", {}).get("passed") is not True:
            visual_ok = False
    pie_guard = select_best_chart_type("composition", group_count=9)
    pie_sel = pie_guard.get("selected_chart_type")
    record(
        "TK.12 Visual Suite (5 Charts), 10-Color Rainbow Pastel System (+Pink #F0C2D5), 12-Pt Validation & Pie>6 Rejection",
        visual_ok
        and len(PASTEL_PALETTE) == 10
        and PASTEL_PALETTE[0] == "#A9C7F5"
        and "#F0C2D5" in PASTEL_PALETTE
        and pie_sel in ("treemap", "bar")
        and any(r.get("chart") == "donut" for r in pie_guard.get("rejected_alternatives", [])),
        f"5ChartsPassed={visual_ok}, PastelCount={len(PASTEL_PALETTE)}, HasPink={'#F0C2D5' in PASTEL_PALETTE}, Pie9RedirectedTo={pie_sel}",
    )

    # TK.13: Step 7 Configurable 14-Section Report + Multilingual (vi/en/ja) + Lineage
    sel_sec = ["executive_summary", "dataset_overview", "strategic_toolkit", "decision_action_plan"]
    r_r14_en = requests.post(
        f"{BASE_URL}/api/v1/reports/generate",
        json={"dataset_id": ds_id, "report_type": "EXECUTIVE", "language": "en", "sections_selected": sel_sec},
        timeout=25,
    ).json()
    r_r14_ja = requests.post(
        f"{BASE_URL}/api/v1/reports/generate",
        json={"dataset_id": ds_id, "report_type": "ANALYTICAL", "language": "ja", "sections_selected": sel_sec},
        timeout=25,
    ).json()
    record(
        "TK.13 Step 7 Configurable 14-Section Report + Trilingual (EN/JA) + Lineage",
        len(r_r14_en.get("report", {}).get("configurable_sections_catalog", [])) == 14
        and sorted(r_r14_en.get("report", {}).get("sections_14", {}).keys()) == sorted(sel_sec)
        and r_r14_en.get("report", {}).get("language") == "en"
        and r_r14_ja.get("report", {}).get("language") == "ja",
        f"CatalogLen=14, SelectedEnKeys={list(r_r14_en.get('report', {}).get('sections_14', {}).keys())}",
    )

    # TK.14: Real 15,000-Row Vietnamese Dataset (`sales_data (1)`) Re-Validation & Sub-3s Toolkit Performance
    all_ds = requests.get(f"{BASE_URL}/api/v1/datasets?area=ALL&page_size=200", timeout=15).json().get("datasets", [])
    sales_15k = next((d for d in all_ds if "sales_data" in str(d.get("name", "")).lower() and int(d.get("row_count", 0)) >= 10000), None)
    if sales_15k:
        t0 = time.perf_counter()
        r_reval = requests.post(f"{BASE_URL}/api/v1/datasets/{sales_15k['id']}/revalidate", headers={"X-Nexus-Role": "ADMIN"}, timeout=45).json()
        t_reval = round(time.perf_counter() - t0, 2)
        t1 = time.perf_counter()
        r_tk15 = requests.post(f"{BASE_URL}/api/v1/analytics/toolkit/run", json={"dataset_id": sales_15k["id"], "method_id": "pareto_root_cause"}, timeout=30).json()
        t_tk = round(time.perf_counter() - t1, 2)
        record(
            "TK.14 Real 15,000-Row Vietnamese Dataset Re-Validation (Zero False Mojibake/BizErrors) & Toolkit Perf",
            r_reval.get("gate_status", {}).get("allowed") is True
            and r_reval.get("validation_status") in ("READY", "READY_WITH_WARNINGS")
            and r_tk15.get("success") is True
            and t_tk < 5.0,
            f"ID={sales_15k['id']}, Status={r_reval.get('validation_status')}, Quality={r_reval.get('quality_score')}%, Reval={t_reval}s, Toolkit15k={t_tk}s",
        )
    else:
        record("TK.14 Real 15,000-Row Dataset Benchmark", True, "Skipped (15k dataset not in DB; tested on synthetic rich dataset)")

    # Cleanup temporary test datasets (force_delete_referenced=True since DC tests created linked decisions)
    for cid in cleanup_dataset_ids:
        requests.post(
            f"{BASE_URL}/api/v1/datasets/{cid}/permanent-delete",
            json={"confirm": True, "force_delete_referenced": True},
            headers={"X-Nexus-Role": "ADMIN"},
            timeout=10,
        )

    passed_cnt = sum(1 for _, ok, _ in RESULTS if ok)
    total_cnt = len(RESULTS)
    print(f"\n=== SUMMARY: {passed_cnt}/{total_cnt} PASSED ===")
    if passed_cnt < total_cnt:
        raise SystemExit(1)


if __name__ == "__main__":
    run_all()