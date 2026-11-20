"""
tests/test_history_version_management.py
Automated Acceptance Suite covering all 20 mandatory requirements of:
NEXUS ANALYTICS - UPGRADE DATA HISTORY & VERSION MANAGEMENT
"""

import io
import os
import re
import sys
import time
import pandas as pd
import requests

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

BASE_URL = "http://127.0.0.1:8000"


def _wait_for_server():
    for _ in range(25):
        try:
            r = requests.get(f"{BASE_URL}/", timeout=2)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.4)
    raise RuntimeError("Server on port 8000 did not become ready in time.")


def run_acceptance_suite():
    _wait_for_server()
    results = []
    created_ids = []

    def record(name: str, passed: bool, detail: str):
        status = "PASS" if passed else "FAIL"
        results.append({"test": name, "status": status, "detail": detail})
        print(f"[{status}] {name} -> {detail}")

    # Wait briefly to fetch baseline HTML
    html = requests.get(f"{BASE_URL}/", timeout=10).text

    # ------------------------------------------------------------------
    # T1: Valid upload appears in Active Datasets with READY status
    # ------------------------------------------------------------------
    v1_csv = (
        "order_id,order_date,category,revenue,cost,profit\n"
        "ORD-1,2026-10-01,Hardware,1000,600,400\n"
        "ORD-2,2026-10-02,Software,2000,1000,1000\n"
    ).encode("utf-8")
    r1 = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": ("lifecycle_sales_q4.csv", v1_csv, "text/csv")},
        data={"name": "Lifecycle Sales Q4", "domain": "Sales & Revenue"},
        timeout=15,
    )
    d1 = r1.json()
    ds_id = d1["dataset"]["id"]
    v1_id = d1["bundle"]["active_version"]["id"]
    created_ids.append(ds_id)

    active_list = requests.get(f"{BASE_URL}/api/v1/datasets?area=ACTIVE&page_size=200", timeout=10).json()["datasets"]
    in_active = any(x["id"] == ds_id and x["validation_status"] == "READY" for x in active_list)
    record("HVM.1 Valid File Uploaded Appears in Active Datasets (READY)", r1.status_code == 200 and in_active, f"DatasetID={ds_id}")

    # ------------------------------------------------------------------
    # T2 & T3: Rejected Level-3 file stored in Archive (REJECTED) & blocked from Analytics/Reports
    # ------------------------------------------------------------------
    r_rej = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": ("broken_empty_hvm.csv", b"", "text/csv")},
        timeout=10,
    )
    rej_id = r_rej.json().get("rejected_dataset", {}).get("id")
    if rej_id:
        created_ids.append(rej_id)

    arc_rej = requests.get(f"{BASE_URL}/api/v1/datasets?area=DATA_ARCHIVE&status=REJECTED&page_size=50", timeout=10).json()["datasets"]
    act_after_rej = requests.get(f"{BASE_URL}/api/v1/datasets?area=ACTIVE&page_size=200", timeout=10).json()["datasets"]
    rej_in_archive = any(x["id"] == rej_id and x["validation_status"] == "REJECTED" for x in arc_rej)
    rej_not_active = not any(x["id"] == rej_id for x in act_after_rej)

    ana_rej = requests.post(f"{BASE_URL}/api/v1/analytics/run", json={"dataset_id": rej_id, "method_name": "summary_stats"}, timeout=10)
    rep_rej = requests.post(f"{BASE_URL}/api/v1/reports/generate", json={"dataset_id": rej_id, "report_type": "EXECUTIVE"}, timeout=10)
    det_rej = requests.get(f"{BASE_URL}/api/v1/datasets/{rej_id}/detail", timeout=10).json()
    record(
        "HVM.2 & HVM.3 Rejected File Persisted in Archive Only & Blocked from Analytics/Reports",
        r_rej.status_code == 422 and rej_in_archive and rej_not_active and ana_rej.status_code == 422 and rep_rej.status_code == 422 and det_rej.get("is_rejected") is True,
        f"InArchive={rej_in_archive}, NotActive={rej_not_active}, AnaBlock={ana_rej.status_code}, RepBlock={rep_rej.status_code}"
    )

    # Also upload a REQUIRES_CORRECTION file + PARTIALLY_VALID workbook to test all statuses
    dirty_csv = (
        "order_id,order_date,revenue,cost,profit\n"
        "ORD-1,2026-02-30,INVALID_NUM,500,400\n"
        "ORD-2,2026-10-05,2000,1000,1000\n"
    ).encode("utf-8")
    r_dirty = requests.post(f"{BASE_URL}/api/v1/datasets/upload", files={"file": ("dirty_cells_hvm.csv", dirty_csv, "text/csv")}, timeout=15).json()
    dirty_id = r_dirty["dataset"]["id"]
    created_ids.append(dirty_id)

    bio_wb = io.BytesIO()
    with pd.ExcelWriter(bio_wb, engine="openpyxl") as w:
        pd.DataFrame([{"id": "A1", "revenue": 500}, {"id": "A2", "revenue": 700}]).to_excel(w, sheet_name="GoodSheet", index=False)
        pd.DataFrame().to_excel(w, sheet_name="EmptyBadSheet", index=False)
    bio_wb.seek(0)
    r_part = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": ("partial_wb_hvm.xlsx", bio_wb.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        timeout=15,
    ).json()
    part_id = r_part["dataset"]["id"]
    created_ids.append(part_id)

    # ------------------------------------------------------------------
    # T4, T5, T6, T18, T19: Multi-filtering (status, fuzzy search, format, date), combined filters & pagination
    # ------------------------------------------------------------------
    st_req = requests.get(f"{BASE_URL}/api/v1/datasets?status=REQUIRES_CORRECTION&page_size=50", timeout=10).json()["datasets"]
    st_part = requests.get(f"{BASE_URL}/api/v1/datasets?status=PARTIALLY_VALID&page_size=50", timeout=10).json()["datasets"]
    fuzzy_res = requests.get(f"{BASE_URL}/api/v1/datasets?search=lifecycle%20sales&file_format=CSV&date_range=TODAY&status=READY", timeout=10).json()["datasets"]
    p1 = requests.get(f"{BASE_URL}/api/v1/datasets?area=ALL&page=1&page_size=2", timeout=10).json()
    p2 = requests.get(f"{BASE_URL}/api/v1/datasets?area=ALL&page=2&page_size=2", timeout=10).json()
    disjoint_pages = set(x["id"] for x in p1["datasets"]).isdisjoint(set(x["id"] for x in p2["datasets"]))

    record(
        "HVM.4-6 & HVM.18-19 Status/Search/Format/Date Filters, Combined Filtering & Pagination",
        any(x["id"] == dirty_id for x in st_req)
        and any(x["id"] == part_id for x in st_part)
        and any(x["id"] == ds_id for x in fuzzy_res)
        and p1["pagination"]["total_pages"] >= 2
        and disjoint_pages,
        f"ReqCorr={any(x['id']==dirty_id for x in st_req)}, PartVal={any(x['id']==part_id for x in st_part)}, Combined={any(x['id']==ds_id for x in fuzzy_res)}, Pages={p1['pagination']['total_pages']}"
    )

    # ------------------------------------------------------------------
    # T8: Identical file detection (Case A)
    # ------------------------------------------------------------------
    r_dup_same = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": ("lifecycle_sales_q4.csv", v1_csv, "text/csv")},
        data={"conflict_resolution": "PROMPT"},
        timeout=15,
    ).json()
    dup_a = r_dup_same.get("duplicate_detection", {})
    # Clean staging if left behind
    if r_dup_same.get("staging_id"):
        requests.post(f"{BASE_URL}/api/v1/datasets/confirm-import", json={"staging_id": r_dup_same["staging_id"], "action": "CANCEL"}, timeout=10)
    record(
        "HVM.8 Identical File Recognized as Duplicate (Case A)",
        r_dup_same.get("requires_decision") is True and dup_a.get("match_type") == "IDENTICAL_FILE" and dup_a.get("matched_dataset_id") == ds_id,
        f"Match={dup_a.get('match_type')}, Msg='{dup_a.get('message_i18n', {}).get('vi')}'"
    )

    # ------------------------------------------------------------------
    # T16: Generate Report on v1 BEFORE updating file (pinned strictly to v1)
    # ------------------------------------------------------------------
    rep_v1 = requests.post(
        f"{BASE_URL}/api/v1/reports/generate",
        json={"dataset_id": ds_id, "report_type": "EXECUTIVE", "title": "Q4 Baseline Report v1", "language": "vi"},
        timeout=15,
    ).json()
    ana_v1 = requests.post(
        f"{BASE_URL}/api/v1/analytics/run",
        json={"dataset_id": ds_id, "method_name": "summary_stats", "metric_col": "revenue"},
        timeout=15,
    ).json()
    rep_v1_id = rep_v1["report_id"]
    rep_v1_sum = rep_v1["report"]["key_statistics"]["total_revenue"] if "total_revenue" in rep_v1.get("report", {}).get("key_statistics", {}) else 3000

    # ------------------------------------------------------------------
    # T9 & T10: AI Cleaning creates v2 (v1 immutable), User Cell Edit creates v3
    # ------------------------------------------------------------------
    cln_dirty = requests.post(
        f"{BASE_URL}/api/v1/datasets/{dirty_id}/clean/apply",
        json={"mode": "AI_ASSISTED", "rules": [{"column": "order_id", "operation": "trim_whitespace"}]},
        timeout=15,
    ).json()
    dirty_v2_num = cln_dirty["bundle"]["active_version"]["version_number"]

    edit_dirty = requests.post(
        f"{BASE_URL}/api/v1/datasets/{dirty_id}/edit-cell",
        json={"row_index": 0, "column": "revenue", "new_value": "1500"},
        timeout=15,
    ).json()
    dirty_v3_num = edit_dirty["version_number"]
    det_dirty = requests.get(f"{BASE_URL}/api/v1/datasets/{dirty_id}/detail", timeout=10).json()
    src_types = {v["version_number"]: v["source_type"] for v in det_dirty["versions"]}
    record(
        "HVM.9 & HVM.10 AI Cleaning & Direct Cell Edit Create Distinct Versions Preserving Original v1",
        dirty_v2_num == 2 and dirty_v3_num == 3 and src_types.get(1) == "ORIGINAL_UPLOAD" and src_types.get(2) == "AI_CLEANED" and src_types.get(3) == "USER_EDITED",
        f"SourceTypes={src_types}"
    )

    # ------------------------------------------------------------------
    # T7, T11, T12, T17: Same filename content change -> Case B NEW_VERSION (no overwrite), Compare v1 vs v2, Restore v1, Report Isolation & Cross-Version Analytics Compare
    # ------------------------------------------------------------------
    v2_csv = (
        "order_id,order_date,category,revenue,cost,profit\n"
        "ORD-1,2026-10-01,Hardware,5000,2500,2500\n"
        "ORD-2,2026-10-02,Software,2000,1000,1000\n"
        "ORD-3,2026-10-03,Cloud,3000,1200,1800\n"
    ).encode("utf-8")
    r_upd = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": ("lifecycle_sales_q4.csv", v2_csv, "text/csv")},
        data={"conflict_resolution": "PROMPT"},
        timeout=15,
    ).json()
    dup_b = r_upd.get("duplicate_detection", {})

    # Schema mismatch Case C guard check
    mismatch_csv = "unrelated_a,unrelated_b\n1,2\n3,4\n".encode("utf-8")
    r_mis = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": ("lifecycle_sales_q4.csv", mismatch_csv, "text/csv")},
        data={"conflict_resolution": "PROMPT"},
        timeout=15,
    ).json()
    dup_c = r_mis.get("duplicate_detection", {})
    r_mis_guard = requests.post(
        f"{BASE_URL}/api/v1/datasets/confirm-import",
        json={"staging_id": r_mis["staging_id"], "action": "NEW_VERSION", "target_dataset_id": ds_id, "confirm_schema_change": False},
        timeout=15,
    )
    requests.post(f"{BASE_URL}/api/v1/datasets/confirm-import", json={"staging_id": r_mis["staging_id"], "action": "CANCEL"}, timeout=10)

    # Confirm Case B as NEW_VERSION (v2)
    r_conf_v2 = requests.post(
        f"{BASE_URL}/api/v1/datasets/confirm-import",
        json={"staging_id": r_upd["staging_id"], "action": "NEW_VERSION", "target_dataset_id": ds_id},
        timeout=15,
    ).json()
    v2_id = r_conf_v2["bundle"]["active_version"]["id"]

    # Check Compare Versions (v1 vs v2)
    cmp_res = requests.get(f"{BASE_URL}/api/v1/datasets/{ds_id}/versions/compare?version_a_id={v1_id}&version_b_id={v2_id}", timeout=15).json()
    # Check Report Isolation (Section 12)
    reports_after = requests.get(f"{BASE_URL}/api/v1/reports?dataset_id={ds_id}", timeout=10).json()["reports"]
    old_rep_row = next(r for r in reports_after if r["id"] == rep_v1_id)
    # Cross-version analytics comparison (Revenue Sum 3000 vs 10000 -> Delta +7000)
    ana_cmp = requests.post(
        f"{BASE_URL}/api/v1/datasets/{ds_id}/compare-analytics",
        json={"version_a_id": v1_id, "version_b_id": v2_id, "method_name": "summary_stats", "metric_col": "revenue"},
        timeout=15,
    ).json()
    rev_delta = next((k for k in ana_cmp.get("kpi_deltas", []) if k["column"] == "revenue"), {})

    # Restore back to v1
    r_rest = requests.post(f"{BASE_URL}/api/v1/datasets/{ds_id}/versions/{v1_id}/restore", timeout=15).json()
    rest_v_num = r_rest["bundle"]["active_version"]["version_number"]

    record(
        "HVM.7,11,12,16,17 Update Conflict (B/C), Version Compare, Restore v1 & Old Report Isolation",
        dup_b.get("match_type") == "SAME_NAME_CONTENT_CHANGED"
        and dup_c.get("match_type") == "SCHEMA_MISMATCH_WARNING"
        and r_mis_guard.status_code == 400
        and r_conf_v2["bundle"]["active_version"]["version_number"] == 2
        and cmp_res["row_diff"]["rows_added"] == 1
        and cmp_res["row_diff"]["changed_cells_count"] >= 1
        and old_rep_row["dataset_version_id"] == v1_id
        and old_rep_row["is_outdated_version"] is True
        and rev_delta.get("sum_delta") == 7000.0
        and rest_v_num == 1,
        f"CaseB={dup_b.get('match_type')}, CaseC_Guard={r_mis_guard.status_code}, DeltaRev={rev_delta.get('sum_delta')}, OutdatedFlag={old_rep_row.get('is_outdated_version')}, RestoredV={rest_v_num}"
    )

    # ------------------------------------------------------------------
    # T13 & T14: Archive preserves history/reports & Restore from Archive runs re-validation
    # ------------------------------------------------------------------
    arc_res = requests.post(f"{BASE_URL}/api/v1/datasets/{ds_id}/archive", json={"reason": "QA Archive"}, timeout=15).json()
    det_arc = requests.get(f"{BASE_URL}/api/v1/datasets/{ds_id}/detail", timeout=10).json()
    arc_preserves = len(det_arc["versions"]) == 2 and len(det_arc["linked_reports"]) >= 1 and len(det_arc["processing_history"]) >= 4

    rest_arc = requests.post(f"{BASE_URL}/api/v1/datasets/{ds_id}/restore-archive", timeout=15).json()
    record(
        "HVM.13 & HVM.14 Archive Preserves History/Versions/Reports & Restore Re-validates",
        arc_res["validation_status"] == "ARCHIVED"
        and arc_preserves
        and rest_arc["lifecycle_area"] == "ACTIVE"
        and rest_arc["revalidated"] is True
        and rest_arc["validation_status"] == "READY",
        f"ArchiveStatus={arc_res['validation_status']}, VersionsPreserved={len(det_arc['versions'])}, Revalidated={rest_arc['validation_status']}"
    )

    # ------------------------------------------------------------------
    # T15: Permanent Delete Confirmation & RBAC Control (VIEWER vs ANALYST vs ADMIN)
    # ------------------------------------------------------------------
    r_v_edit = requests.post(
        f"{BASE_URL}/api/v1/datasets/{dirty_id}/edit-cell",
        json={"row_index": 0, "column": "revenue", "new_value": "999"},
        headers={"X-Nexus-Role": "VIEWER"},
        timeout=10,
    )
    r_v_arc = requests.post(f"{BASE_URL}/api/v1/datasets/{ds_id}/archive", json={}, headers={"X-Nexus-Role": "VIEWER"}, timeout=10)
    r_a_del = requests.post(f"{BASE_URL}/api/v1/datasets/{ds_id}/permanent-delete", json={"confirm": True}, headers={"X-Nexus-Role": "ANALYST"}, timeout=10)
    r_adm_noconf = requests.post(f"{BASE_URL}/api/v1/datasets/{ds_id}/permanent-delete", json={"confirm": False}, headers={"X-Nexus-Role": "ADMIN"}, timeout=10)
    r_adm_del = requests.post(f"{BASE_URL}/api/v1/datasets/{ds_id}/permanent-delete", json={"confirm": True}, headers={"X-Nexus-Role": "ADMIN"}, timeout=10)
    if r_adm_del.status_code == 200:
        created_ids = [i for i in created_ids if i != ds_id]

    record(
        "HVM.15 RBAC Permissions (VIEWER/ANALYST/ADMIN) & Explicit Confirmation for Permanent Delete",
        r_v_edit.status_code == 403
        and r_v_arc.status_code == 403
        and r_a_del.status_code == 403
        and r_adm_noconf.status_code == 400
        and r_adm_del.status_code == 200,
        f"ViewerEdit={r_v_edit.status_code}, ViewerArc={r_v_arc.status_code}, AnalystDel={r_a_del.status_code}, AdminNoConf={r_adm_noconf.status_code}, AdminDel={r_adm_del.status_code}"
    )

    # ------------------------------------------------------------------
    # T20: UI Sections, Controls, Zero Dead Handlers & I18N Parity
    # ------------------------------------------------------------------
    req_dom = [
        "dhFilterToolbarCard", "dhActiveDatasetsSection", "dhArchiveDatasetsSection",
        "modalUploadConflict", "modalDatasetDetail", "modalPermanentDelete",
        "dsTabPanel_overview", "dsTabPanel_preview", "dsTabPanel_quality", "dsTabPanel_history", "dsTabPanel_versions",
    ]
    dom_ok = all(dom_id in html for dom_id in req_dom)
    onclicks = set(re.findall(r'onclick="([a-zA-Z_][a-zA-Z0-9_]*)\(', html))
    defined_fns = set(re.findall(r'(?:async\s+)?function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', html))
    missing_h = onclicks - defined_fns - {"navigator", "document", "window"}
    record(
        "HVM.20 UI Controls, Sections, Modals & Zero Missing Handlers",
        dom_ok and len(missing_h) == 0,
        f"AllSections={dom_ok}, MissingHandlers={missing_h}"
    )

    # Clean up remaining temporary test datasets
    for tid in created_ids:
        try:
            requests.post(f"{BASE_URL}/api/v1/datasets/{tid}/permanent-delete", json={"confirm": True}, headers={"X-Nexus-Role": "ADMIN"}, timeout=10)
        except Exception:
            pass

    passed = sum(1 for r in results if r["status"] == "PASS")
    print(f"\nNEXUS DATA HISTORY & VERSION MANAGEMENT SUMMARY: {passed}/{len(results)} PASSED.")
    assert passed == len(results), f"Some HVM tests failed: {results}"


if __name__ == "__main__":
    run_acceptance_suite()

