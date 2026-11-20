"""
tests/test_ux_chart_evidence_upgrade.py
Unit, Integration, and End-to-End Acceptance Test Suite for NEXUS ANALYTICS v4.1:
- Unit: Rainbow Pastel (+Pink #F0C2D5), Field Display Labels, 3-Origin Warning Classifier,
        Transparent 6-State Verification, Human-Readable Formulas, Raw Markdown Stripper.
- Acceptance (Phần XV.4): Product Name x Revenue Chart Builder (Horizontal Bar Auto, SUM,
        Descending, exact Share %, 12-Point Validation, Zero Reconciliation Diff, ID SUM block,
        Filter, Drill-Down rows, CSV/XLSX Export, Trilingual VI/EN/JA).
- Integration & E2E: 7-Tab Evidence & Formula Modal APIs (/api/v1/evidence/{id}, Analytics,
        Chart Builder, Toolkit, Step 6 AI Insights per-finding evidence links), 3-Origin
        Data Validation, Drag & Drop + Sidebar Active Dataset Card + Zero Fake 96% + Zero #2563eb.
"""

import io
import os
import re
import sys
import subprocess
import tempfile
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus_analytics.services.localization_helper import (
    RAINBOW_PASTEL_PALETTE,
    get_palette_by_mode,
    get_column_display_label,
    classify_warning_origin,
    determine_verification_state,
    strip_raw_markdown,
)

BASE_URL = "http://127.0.0.1:8000"
RESULTS = []


def record(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    RESULTS.append((name, passed, detail))
    print(f"[{status}] {name} :: {detail}")


def upload_csv(filename: str, content: str):
    r = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": (filename, content.encode("utf-8"), "text/csv")},
        data={"name": filename.replace(".csv", ""), "conflict_resolution": "CREATE_NEW"},
        headers={"X-Nexus-Role": "ADMIN"},
        timeout=30,
    )
    return r


def run_all():
    cleanup_ids = []

    # =========================================================================
    # U1: Unit — Rainbow Pastel Palette (Mandatory Pink #F0C2D5), Modes & Display Labels
    # =========================================================================
    lbl_vi = get_column_display_label("Product_Name", "vi")
    lbl_en = get_column_display_label("Product_Name", "en")
    lbl_ja = get_column_display_label("Product_Name", "ja")
    record(
        "U1 Rainbow Pastel 10-Color Spectrum (+Pink #F0C2D5) & Localized Field Display Labels",
        len(RAINBOW_PASTEL_PALETTE) == 10
        and "#F0C2D5" in RAINBOW_PASTEL_PALETTE
        and "#A9C7F5" in RAINBOW_PASTEL_PALETTE
        and "#A9D8C5" in RAINBOW_PASTEL_PALETTE
        and len(get_palette_by_mode("high_contrast")) == 10
        and len(get_palette_by_mode("monochrome")) == 10
        and lbl_vi == "Tên sản phẩm"
        and lbl_en == "Product Name"
        and lbl_ja == "商品名",
        f"Colors={len(RAINBOW_PASTEL_PALETTE)}, PinkPresent={'#F0C2D5' in RAINBOW_PASTEL_PALETTE}, Labels=({lbl_vi}/{lbl_en}/{lbl_ja})",
    )

    # =========================================================================
    # U2: Unit — 3-Origin Warning Classifier, Transparent Verification & Markdown Stripper
    # =========================================================================
    o_file = classify_warning_origin("INVALID_NUMERIC_TEXT")["warning_origin"]
    o_ai = classify_warning_origin("AMBIGUOUS_DATE_FORMAT")["warning_origin"]
    o_anom = classify_warning_origin("SUSPICIOUS_OUTLIER")["warning_origin"]
    v_ok = determine_verification_state(12, 0, 0)
    v_fail = determine_verification_state(10, 2, 0)
    v_miss = determine_verification_state(0, 0, 0, missing_data=True)
    cleaned = strip_raw_markdown("### **Heading** `Share_i` [FACT] Doanh thu tăng 12%.")
    record(
        "U2 3-Origin Warning Classifier, Transparent 6-State Verification & Clean Prose Stripper",
        o_file == "FILE_ERROR"
        and o_ai == "AI_INTERPRETATION_WARNING"
        and o_anom == "DATA_ANOMALY"
        and v_ok["status_code"] == "VERIFIED_SUCCESS"
        and v_fail["status_code"] == "DISCREPANCY_FOUND"
        and v_miss["status_code"] == "UNVERIFIABLE_MISSING_DATA"
        and "**" not in cleaned and "###" not in cleaned and "`" not in cleaned and "[FACT]" not in cleaned,
        f"Origins=({o_file},{o_ai},{o_anom}), Ver=({v_ok['status_code']},{v_fail['status_code']},{v_miss['status_code']})",
    )

    # =========================================================================
    # E1: Acceptance Test (Phần XV.4) — Product Name x Revenue -> Auto Horizontal Bar Chart
    # =========================================================================
    csv_prod_rev = (
        "Order_ID,Order_Date,Product_Name,Category,Region,Revenue_VND,Cost_VND,Profit_VND\n"
        "ORD-001,2026-01-05,Laptop Pro 16,Electronics,North,35000000,24000000,11000000\n"
        "ORD-002,2026-01-08,Laptop Pro 16,Electronics,South,40000000,27000000,13000000\n"
        "ORD-003,2026-01-12,Cloud Suite Enterprise,Software,North,25000000,10000000,15000000\n"
        "ORD-004,2026-01-15,Smart Monitor 4K,Electronics,Central,15000000,11000000,4000000\n"
        "ORD-005,2026-01-20,Cloud Suite Enterprise,Software,South,30000000,12000000,18000000\n"
        "ORD-006,2026-02-03,Ergonomic Dock Hub,Accessories,North,5000000,3000000,2000000\n"
    )
    r_up = upload_csv("ux_prod_rev_acceptance.csv", csv_prod_rev)
    ds_id = r_up.json()["dataset"]["id"]
    cleanup_ids.append(ds_id)

    # Check chart defaults endpoint auto-detects Product_Name x Revenue_VND
    r_def = requests.get(f"{BASE_URL}/api/v1/datasets/{ds_id}/chart-defaults?language=vi", timeout=15).json()
    def_cfg = r_def.get("default_config", {})

    # Build default chart (Product_Name x Revenue_VND, Auto, SUM, Descending)
    r_cb = requests.post(
        f"{BASE_URL}/api/v1/charts/build",
        json={"dataset_id": ds_id, "x_col": "Product_Name", "y_col": "Revenue_VND", "aggregation": "SUM", "chart_type": "auto", "sort_dir": "desc", "language": "vi"},
        timeout=15,
    ).json()
    # Expected totals: Laptop Pro 16 = 75M (50%), Cloud Suite = 55M (36.67%), Monitor = 15M (10%), Dock = 5M (3.33%); Total = 150M
    tbl = r_cb.get("table_rows", [])
    expected_total = 150_000_000.0
    actual_total = r_cb.get("totals", {}).get("rendered_total", 0)
    recon_diff = r_cb.get("totals", {}).get("reconciliation_diff", 999)
    share_sum = round(sum(float(x.get("share_pct") or 0) for x in tbl), 2)
    record(
        "E1 Acceptance (XV.4): Product_Name x Revenue_VND -> Auto Horizontal Bar, Exact SUM=150M, Share=100%, 12/12 Valid",
        def_cfg.get("x_col") == "Product_Name"
        and def_cfg.get("y_col") == "Revenue_VND"
        and r_cb.get("success") is True
        and r_cb.get("selected_chart_type") == "horizontal_bar"
        and abs(actual_total - expected_total) < 0.01
        and recon_diff < 0.01
        and tbl[0]["group"] == "Laptop Pro 16"
        and abs(tbl[0]["value"] - 75_000_000.0) < 0.01
        and abs(tbl[0]["share_pct"] - 50.0) < 0.01
        and abs(share_sum - 100.0) < 0.1
        and r_cb.get("chart_validation", {}).get("passed") is True
        and r_cb.get("chart_validation", {}).get("passed_count") == 12
        and "#F0C2D5" in r_cb.get("palette", []),
        f"Type={r_cb.get('selected_chart_type')}, Top={tbl[0]['group']}({tbl[0]['share_pct']}%), Total={actual_total:,.0f}, Diff={recon_diff}, Checks={r_cb.get('chart_validation', {}).get('passed_count')}/12",
    )

    # =========================================================================
    # E2: Chart Builder Guardrails — Block SUM on ID, Filter, Drill-Down, CSV/XLSX Export & EN/JA Localization
    # =========================================================================
    r_bad_id = requests.post(
        f"{BASE_URL}/api/v1/charts/build",
        json={"dataset_id": ds_id, "x_col": "Product_Name", "y_col": "Order_ID", "aggregation": "SUM", "language": "vi"},
        timeout=15,
    )
    r_flt = requests.post(
        f"{BASE_URL}/api/v1/charts/build",
        json={"dataset_id": ds_id, "x_col": "Product_Name", "y_col": "Revenue_VND", "aggregation": "SUM", "filter_col": "Region", "filter_val": "North", "language": "en"},
        timeout=15,
    ).json()
    r_ja = requests.post(
        f"{BASE_URL}/api/v1/charts/build",
        json={"dataset_id": ds_id, "x_col": "Product_Name", "y_col": "Revenue_VND", "aggregation": "SUM", "language": "ja"},
        timeout=15,
    ).json()
    r_dd = requests.post(
        f"{BASE_URL}/api/v1/charts/drilldown",
        json={"dataset_id": ds_id, "filter_col": "Product_Name", "filter_val": "Laptop Pro 16", "limit": 50},
        timeout=15,
    ).json()
    r_exp_csv = requests.post(
        f"{BASE_URL}/api/v1/charts/export?fmt=csv",
        json={"dataset_id": ds_id, "x_col": "Product_Name", "y_col": "Revenue_VND", "aggregation": "SUM"},
        timeout=15,
    )
    r_exp_xlsx = requests.post(
        f"{BASE_URL}/api/v1/charts/export?fmt=xlsx",
        json={"dataset_id": ds_id, "x_col": "Product_Name", "y_col": "Revenue_VND", "aggregation": "SUM"},
        timeout=15,
    )
    record(
        "E2 Chart Builder Guards (Block SUM on ID=400), Filter (North=65M), Drill-Down (2 rows), CSV/XLSX Export & EN/JA Titles",
        r_bad_id.status_code == 400
        and r_flt.get("totals", {}).get("rendered_total") == 65_000_000.0
        and "商品名" in (r_ja.get("chart_title_i18n", {}).get("ja", ""))
        and r_dd.get("matched_total") == 2
        and r_exp_csv.status_code == 200 and "Laptop Pro 16" in r_exp_csv.text
        and r_exp_xlsx.status_code == 200 and len(r_exp_xlsx.content) > 1000,
        f"IDGuard={r_bad_id.status_code}, NorthTotal={r_flt.get('totals', {}).get('rendered_total')}, DrillRows={r_dd.get('matched_total')}, XLSXBytes={len(r_exp_xlsx.content)}",
    )

    # =========================================================================
    # E3: 7-Tab Evidence Bundle across Analytics, Toolkit, Chart Builder & /api/v1/evidence/{run_id}
    # =========================================================================
    r_an = requests.post(
        f"{BASE_URL}/api/v1/analytics/run",
        json={"dataset_id": ds_id, "method_name": "pareto_analysis", "metric_col": "Revenue_VND", "dimension_col": "Product_Name"},
        timeout=15,
    ).json()
    r_tk = requests.post(
        f"{BASE_URL}/api/v1/analytics/toolkit/run",
        json={"dataset_id": ds_id, "method_id": "pareto_root_cause"},
        timeout=15,
    ).json()
    run_id = r_an.get("analysis_run_id")
    r_ev = requests.get(f"{BASE_URL}/api/v1/evidence/{run_id}", timeout=15).json()
    required_7_tabs = {"overview", "data_source", "formulas", "execution_steps", "data_evidence", "verification", "limitations"}
    cb_tabs = set((r_cb.get("evidence_bundle") or {}).keys())
    an_tabs = set((r_an.get("evidence_bundle") or {}).keys())
    tk_tabs = set((r_tk.get("evidence_bundle") or {}).keys())
    no_raw_share_var = "Share_i" not in str(r_tk.get("formula_used", "")) and "Cumulative_k" not in str(r_tk.get("formula_used", ""))
    record(
        "E3 Unified 7-Tab Evidence & Formula Bundle (Chart Builder, Analytics, Toolkit, /api/v1/evidence) & Zero Raw Share_i",
        required_7_tabs.issubset(cb_tabs)
        and required_7_tabs.issubset(an_tabs)
        and required_7_tabs.issubset(tk_tabs)
        and r_ev.get("success") is True
        and r_ev.get("dataset_id") == ds_id
        and no_raw_share_var
        and bool(r_an.get("verification_state", {}).get("status_code"))
        and len(r_cb.get("evidence_bundle", {}).get("formulas", [])) >= 2,
        f"7TabsPresent=(CB:{required_7_tabs.issubset(cb_tabs)}, AN:{required_7_tabs.issubset(an_tabs)}, TK:{required_7_tabs.issubset(tk_tabs)}), NoRawShareVar={no_raw_share_var}",
    )

    # =========================================================================
    # E4: Step 6 Executive AI Insights Redesign (Zero Raw Markdown, Per-Finding Evidence Links, VI/EN/JA)
    # =========================================================================
    r_ai_vi = requests.post(
        f"{BASE_URL}/api/v1/ai/query",
        json={"dataset_id": ds_id, "prompt": "Nhóm sản phẩm nào đang đóng góp doanh thu lớn nhất?", "language": "vi"},
        timeout=20,
    ).json()
    r_ai_en = requests.post(
        f"{BASE_URL}/api/v1/ai/query",
        json={"dataset_id": ds_id, "prompt": "Which products drive the largest revenue?", "language": "en"},
        timeout=20,
    ).json()
    r_ai_ja = requests.post(
        f"{BASE_URL}/api/v1/ai/query",
        json={"dataset_id": ds_id, "prompt": "どの商品が最も売上に貢献していますか？", "language": "ja"},
        timeout=20,
    ).json()
    s6_vi = r_ai_vi.get("step6_executive_insights", {})
    kfs_vi = s6_vi.get("key_findings", [])
    has_finding_bundles = len(kfs_vi) >= 1 and required_7_tabs.issubset(set((kfs_vi[0].get("evidence_bundle") or {}).keys()))
    clean_exec = "**" not in s6_vi.get("executive_summary", "") and "###" not in s6_vi.get("executive_summary", "")
    record(
        "E4 Step 6 Executive AI Insights (6 Sections, Per-Finding 7-Tab Evidence, Clean Prose, VI/EN/JA)",
        clean_exec
        and has_finding_bundles
        and len(s6_vi.get("business_impact", [])) >= 2
        and len(s6_vi.get("action_recommendations", [])) >= 1
        and bool(s6_vi.get("causes_and_hypotheses", {}).get("verified_causes"))
        and bool(r_ai_vi.get("verification_state", {}).get("status_code"))
        and r_ai_en.get("step6_executive_insights", {}).get("language") == "en"
        and r_ai_ja.get("step6_executive_insights", {}).get("language") == "ja",
        f"Findings={len(kfs_vi)}, PerFindingEvidence={has_finding_bundles}, CleanExec={clean_exec}, BizImpacts={len(s6_vi.get('business_impact', []))}",
    )

    # =========================================================================
    # E5: 3-Origin Warning Distinction in Data Validation API
    # =========================================================================
    csv_origins = (
        "Order_Date,Product_Name,Revenue_VND\n"
        "2026-01-01,Item A,100000\n"
        "2026-01-02,Item B,110000\n"
        "2026-01-03,Item C,105000\n"
        "2026-01-04,Item D,98000\n"
        "2026-01-05,Item E,102000\n"
        "2026-01-06,Item F,abc_error\n"
        "2026-01-07,Item G,99000000\n"
    )
    r_up_o = upload_csv("ux_3origins_test.csv", csv_origins)
    ds_o = r_up_o.json()["dataset"]["id"]
    cleanup_ids.append(ds_o)
    q_o = requests.get(f"{BASE_URL}/api/v1/datasets/{ds_o}/quality", timeout=15).json()
    audit16 = (q_o.get("data_processing_report") or {}).get("audit_16_domains") or {}
    orig_sum = audit16.get("warning_origin_summary") or {}
    record(
        "E5 Data Validation 3-Origin Separation (FILE_ERROR vs AI_INTERPRETATION_WARNING vs DATA_ANOMALY)",
        orig_sum.get("FILE_ERROR", 0) >= 1 and orig_sum.get("DATA_ANOMALY", 0) >= 1 and "AI_INTERPRETATION_WARNING" in orig_sum,
        f"OriginSummary={orig_sum}",
    )

    # =========================================================================
    # E6: Frontend Static Audit (Drag&Drop, No Fake System Ready, No 0.96, No #2563eb, 7-Tab Modal, JS/I18N=0)
    # =========================================================================
    html = open("nexus_analytics/static/index.html", encoding="utf-8").read()
    m = re.search(r"<script>(.*)</script>", html, re.S)
    js = m.group(1) if m else ""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".js", mode="w", encoding="utf-8")
    tmp.write(js)
    tmp.close()
    rc = subprocess.run(["node", "--check", tmp.name], capture_output=True, text=True)
    os.unlink(tmp.name)

    vi = set(re.findall(r"^                ([a-zA-Z0-9_]+):", html.split("vi: {")[1].split("\n            },")[0], re.M))
    en = set(re.findall(r"^                ([a-zA-Z0-9_]+):", html.split("en: {")[1].split("\n            },")[0], re.M))
    ja = set(re.findall(r"^                ([a-zA-Z0-9_]+):", html.split("ja: {")[1].split("\n            }")[0], re.M))
    dom_keys = set(re.findall(r'data-i18n(?:-[a-z]+)?="([^"]+)"', html))
    fns = set(re.findall(r"(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\(", js))
    called = set(re.findall(r'on(?:click|change|input)="([a-zA-Z0-9_]+)\(', html))
    ana_py = open("nexus_analytics/services/analytics_engine.py", encoding="utf-8").read()

    has_dnd = all(k in js for k in ("initDropZone", "dragenter", "dragover", "dragleave", "drop", "dataTransfer"))
    no_fake_ready = 'data-i18n="system_ready"' not in html and 'id="sidebarDatasetCard"' in html
    no_fake_96 = "|| 0.96" not in js
    no_electric_blue = "#2563eb" not in ana_py
    has_7tab_modal = 'id="modalSourceEvidenceFormula"' in html and all(f'data-evtab="{k}"' in html for k in ("overview", "data_source", "formulas", "execution_steps", "data_evidence", "verification", "limitations"))
    record(
        "E6 Frontend Audit (node=0, I18N parity, MissingDOM=0, MissingFn=0, DnD, Real Sidebar Card, Zero Fake 96%, Zero #2563eb, 7-Tab Modal)",
        rc.returncode == 0
        and vi == en == ja
        and len(dom_keys - vi) == 0
        and len(called - fns) == 0
        and html.count('href="#"') == 0
        and has_dnd
        and no_fake_ready
        and no_fake_96
        and no_electric_blue
        and has_7tab_modal,
        f"node={rc.returncode}, I18N={len(vi)}/{len(en)}/{len(ja)}, MissDOM={len(dom_keys-vi)}, MissFn={len(called-fns)}, DnD={has_dnd}, RealSidebar={no_fake_ready}, No96={no_fake_96}, NoBlue={no_electric_blue}, Modal7={has_7tab_modal}",
    )

    # Cleanup test datasets
    for cid in cleanup_ids:
        requests.post(
            f"{BASE_URL}/api/v1/datasets/{cid}/permanent-delete",
            json={"confirm": True, "force_delete_referenced": True},
            headers={"X-Nexus-Role": "ADMIN"},
            timeout=10,
        )

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n=== UX / CHART BUILDER / EVIDENCE UPGRADE SUMMARY: {passed}/{total} PASSED ===")
    if passed < total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_all()

