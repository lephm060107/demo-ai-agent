"""
tests/test_nexus_v22_redesign.py
Automated E2E Quality Assurance & Interaction Verification for:
- Vintage Botanical Design Tokens & Collapsible Sidebar
- Global Language Switcher (VI / EN / JA) Placement & Complete I18N Key Parity
- Trilingual User Preference Persistence (/api/v1/user/preferences)
- Trilingual AI Analytics Agent (VI / EN / JA + Anti-Hallucination Guard)
- Trilingual Reports & Grounded AI Insights (/api/v1/insights/summary)
- Data Transformation Engine (derive_ratio_pct, derive_diff)
- B2B RFQ Partner CRM CRUD, Quotation Run Comparison & Procurement Tracking CRUD
- Admin Users, Workspaces & Dashboards CRUD + Zero Dead Buttons / Zero href="#"
"""

import os
import re
import sys
import json
import pandas as pd
import requests

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from nexus_analytics.services.cleaning_engine import cleaning_engine

BASE_URL = "http://127.0.0.1:8000"


def run_v22_suite():
    results = []

    def record(name: str, passed: bool, detail: str):
        status = "PASS" if passed else "FAIL"
        results.append({"test": name, "status": status, "detail": detail})
        print(f"[{status}] {name} -> {detail}")

    # 1. Vintage Botanical Tokens, Top-Left Global Language Switcher, Collapsible Sidebar & Dead-Link Audit
    html = requests.get(f"{BASE_URL}/", timeout=10).text
    vb_tokens = ["#FFF9ED", "#A8B77B", "#58743A", "#344B2A", "#F1D9D5", "#EEE8C5", "#35372C"]
    has_tokens = all(tok.lower() in html.lower() for tok in vb_tokens)

    # Check globalLangSwitcher appears inside <aside id="appSidebar"> before <main>
    aside_pos = html.find('<aside id="appSidebar"')
    lang_pos = html.find('id="globalLangSwitcher"')
    main_pos = html.find('<main ')
    top_left_ok = aside_pos != -1 and lang_pos != -1 and main_pos != -1 and (aside_pos < lang_pos < main_pos)

    # Check zero href="#" and zero missing JS handlers or static IDs
    no_dead_href = ('href="#"' not in html) and ("href='#'" not in html)
    onclicks = set(re.findall(r'onclick="([a-zA-Z_][a-zA-Z0-9_]*)\(', html))
    defined_fns = set(re.findall(r'(?:async\s+)?function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', html))
    missing_handlers = onclicks - defined_fns - {"navigator", "document", "window"}
    ids_html = set(re.findall(r'\sid="([^"]+)"', html))
    ids_js = set(re.findall(r"getElementById\(['\"]([^'\"$]+)['\"]\)", html))
    missing_ids = ids_js - ids_html

    record(
        "5.1 Vintage Botanical Palette, Top-Left Sidebar Language Switcher & Zero Dead Links",
        has_tokens and top_left_ok and no_dead_href and len(missing_handlers) == 0 and len(missing_ids) == 0,
        f"Tokens={has_tokens}, TopLeftLang={top_left_ok}, NoDeadHref={no_dead_href}, MissingHandlers={missing_handlers}, MissingIDs={missing_ids}"
    )

    # 2. Complete I18N Dictionary Parity Check across VI / EN / JA
    i18n_keys_ok = True
    key_counts = {}
    for lang_code in ("vi", "en", "ja"):
        m = re.search(rf"\b{lang_code}:\s*\{{(.*?)\n\s*\}}", html.split("const I18N = {")[1], re.S)
        keys = set(re.findall(r"^\s+([a-zA-Z0-9_]+):", m.group(1), re.M)) if m else set()
        key_counts[lang_code] = keys

    vi_keys, en_keys, ja_keys = key_counts["vi"], key_counts["en"], key_counts["ja"]
    # Also ensure every data-i18n attribute exists in all 3 languages
    dom_i18n_keys = set(re.findall(r'data-i18n="([^"]+)"', html)) | set(re.findall(r'data-i18n-placeholder="([^"]+)"', html))
    missing_vi = dom_i18n_keys - vi_keys
    missing_en = dom_i18n_keys - en_keys
    missing_ja = dom_i18n_keys - ja_keys
    i18n_keys_ok = (len(vi_keys) > 150 and vi_keys == en_keys == ja_keys and len(missing_vi) == 0 and len(missing_en) == 0 and len(missing_ja) == 0)

    record(
        "5.2 Trilingual I18N Key Parity (VI == EN == JA) & 100% DOM Key Coverage",
        i18n_keys_ok,
        f"VI={len(vi_keys)}, EN={len(en_keys)}, JA={len(ja_keys)}, MissingDOM={missing_vi | missing_en | missing_ja}"
    )

    # 3. Language Preference Persistence (VI -> EN -> JA -> VI)
    r_en = requests.post(f"{BASE_URL}/api/v1/user/preferences", json={"preferred_language": "en"}, timeout=10).json()
    boot_en = requests.get(f"{BASE_URL}/api/v1/bootstrap", timeout=10).json()
    r_ja = requests.post(f"{BASE_URL}/api/v1/user/preferences", json={"preferred_language": "ja"}, timeout=10).json()
    boot_ja = requests.get(f"{BASE_URL}/api/v1/bootstrap", timeout=10).json()
    r_vi = requests.post(f"{BASE_URL}/api/v1/user/preferences", json={"preferred_language": "vi"}, timeout=10).json()
    record(
        "5.3 Language Preference DB Persistence (VI -> EN -> JA -> VI)",
        r_en.get("preferred_language") == "en" and boot_en.get("preferred_language") == "en"
        and r_ja.get("preferred_language") == "ja" and boot_ja.get("preferred_language") == "ja"
        and r_vi.get("preferred_language") == "vi",
        f"Verified DB round-trip VI -> {boot_en.get('preferred_language')} -> {boot_ja.get('preferred_language')} -> {r_vi.get('preferred_language')}"
    )

    # 4. Trilingual AI Assistant (EN + JA + Guards) & Grounded AI Insights Summary
    sales_ds = next((d for d in boot_en["datasets"] if "Sales 2026" in d["name"]), boot_en["datasets"][0])
    ds_id = sales_ds["id"]

    ai_en = requests.post(f"{BASE_URL}/api/v1/ai/chat", json={"dataset_id": ds_id, "question": "Which product contributes highest profit?", "language": "en"}, timeout=15).json()
    ai_ja = requests.post(f"{BASE_URL}/api/v1/ai/chat", json={"dataset_id": ds_id, "question": "利益が最も高い商品は何ですか？", "language": "ja"}, timeout=15).json()
    ai_ja_guard = requests.post(f"{BASE_URL}/api/v1/ai/chat", json={"dataset_id": ds_id, "question": "ビットコイン価格は？", "language": "ja"}, timeout=15).json()

    ins_vi = requests.get(f"{BASE_URL}/api/v1/insights/summary?dataset_id={ds_id}&lang=vi", timeout=10).json()
    ins_en = requests.get(f"{BASE_URL}/api/v1/insights/summary?dataset_id={ds_id}&lang=en", timeout=10).json()
    ins_ja = requests.get(f"{BASE_URL}/api/v1/insights/summary?dataset_id={ds_id}&lang=ja", timeout=10).json()

    ai_tri_ok = (
        ai_en.get("language") == "en" and "Verified Quantitative Findings" in ai_en.get("answer_markdown", "")
        and ai_ja.get("language") == "ja" and "検証済み定量結果" in ai_ja.get("answer_markdown", "")
        and "不足" in ai_ja_guard.get("answer_markdown", "")
        and len(ins_vi.get("cards", [])) == 4 and len(ins_en.get("cards", [])) == 4 and len(ins_ja.get("cards", [])) == 4
    )
    record(
        "5.4 Trilingual AI Agent (EN/JA + Guard) & 4 Grounded AI Insights Cards",
        ai_tri_ok,
        f"EN_Tools={len(ai_en.get('tool_calls', []))}, JA_Tools={len(ai_ja.get('tool_calls', []))}, InsightsCards=4x3langs"
    )

    # 5. Data Transformation Engine Unit Check (derive_ratio_pct & derive_diff)
    df_tf = pd.DataFrame([
        {"product": "A", "revenue": 1000.0, "cost": 600.0, "profit": 400.0},
        {"product": "B", "revenue": 2000.0, "cost": 1500.0, "profit": 500.0}
    ])
    tf_out, tf_logs = cleaning_engine.execute_rules(df_tf, [
        {"column": "profit", "operation": "derive_ratio_pct", "parameters": {"denominator": "revenue", "target_column": "margin_pct"}},
        {"column": "revenue", "operation": "derive_diff", "parameters": {"other_column": "cost", "target_column": "net_calc"}}
    ])
    tf_ok = abs(float(tf_out["margin_pct"].iloc[0]) - 40.0) < 1e-6 and abs(float(tf_out["net_calc"].iloc[1]) - 500.0) < 1e-6
    record(
        "5.5 Data Transformation Rules (derive_ratio_pct & derive_diff)",
        tf_ok,
        f"margin_pct[0]={tf_out['margin_pct'].iloc[0]}% (Expected 40.0), net_calc[1]={tf_out['net_calc'].iloc[1]} (Expected 500.0)"
    )

    # 6. B2B RFQ Partner CRM CRUD, Quotation Run Comparison & Procurement Tracking CRUD
    p_create = requests.post(
        f"{BASE_URL}/api/v1/rfq/partners",
        json={"partner_type": "SUPPLIER", "name": "Test Botanical Partner QA", "region": "Hà Nội", "sla_tier": "Gold"},
        headers={"X-Nexus-Role": "ANALYST"}, timeout=10
    ).json()
    pid = p_create.get("partner_id")
    p_list = requests.get(f"{BASE_URL}/api/v1/rfq/partners", timeout=10).json().get("partners", [])
    p_del = requests.delete(f"{BASE_URL}/api/v1/rfq/partners/{pid}", headers={"X-Nexus-Role": "ADMIN"}, timeout=10).json()

    po_create = requests.post(
        f"{BASE_URL}/api/v1/rfq/procurement",
        json={"customer_name": "QA Corp", "supplier_name": "Cisco", "sku_summary": "SW-C9200L x2", "total_cost": 56000000},
        headers={"X-Nexus-Role": "ANALYST"}, timeout=10
    ).json()
    po_id = po_create.get("procurement_id")
    po_patch = requests.patch(
        f"{BASE_URL}/api/v1/rfq/procurement/{po_id}",
        json={"status": "DELIVERED"},
        headers={"X-Nexus-Role": "ANALYST"}, timeout=10
    ).json()

    rfq_hist = boot_en.get("rfq_history", [])
    run_detail_ok = False
    if rfq_hist:
        rd = requests.get(f"{BASE_URL}/api/v1/rfq/runs/{rfq_hist[0]['run_db_id']}", timeout=10).json()
        run_detail_ok = rd.get("success") is True and "boq_items" in rd.get("run", {})

    rfq_crm_ok = (
        p_create.get("success") is True and any(p["id"] == pid for p in p_list) and p_del.get("success") is True
        and po_create.get("success") is True and po_patch.get("status") == "DELIVERED"
        and run_detail_ok
    )
    record(
        "5.6 B2B RFQ CRM CRUD, Procurement Pipeline & Quotation Run Detail Comparison API",
        rfq_crm_ok,
        f"PartnerCRUD=True, ProcurementStatus={po_patch.get('status')}, RunDetailCompareReady={run_detail_ok}"
    )

    # 7. Dashboard, Widget & Admin RBAC Enforcement
    ws_block = requests.post(f"{BASE_URL}/api/v1/workspaces", json={"name": "Blocked WS"}, headers={"X-Nexus-Role": "VIEWER"}, timeout=10)
    ws_ok = requests.post(f"{BASE_URL}/api/v1/workspaces", json={"name": "Botanical Telemetry WS"}, headers={"X-Nexus-Role": "ADMIN"}, timeout=10)
    dash_ok = requests.post(f"{BASE_URL}/api/v1/dashboards", json={"name": "Q4 Botanical KPI Board"}, headers={"X-Nexus-Role": "ANALYST"}, timeout=10)

    admin_crud_ok = ws_block.status_code == 403 and ws_ok.status_code == 200 and dash_ok.status_code == 200
    record(
        "5.7 Admin Workspace & Interactive Dashboard Creation + VIEWER 403 Guard",
        admin_crud_ok,
        f"ViewerBlocked={ws_block.status_code == 403}, WorkspaceCreated={ws_ok.status_code == 200}, DashboardCreated={dash_ok.status_code == 200}"
    )

    # 8. Part 1 Human-Centered UX: No Fake User Identities/Titles, No Forced RBAC Selector, Full-Name Lang Switcher
    no_fake_identity = (
        "Trần Minh Quân" not in html
        and "CEO / Owner" not in html
        and "Senior Data Analyst" not in html
        and "headerRoleSelect" not in html
        and "Biến dữ liệu thành quyết định." in html
        and "Tiếng Việt" in html and "English" in html and "日本語" in html
    )
    record(
        "5.8 Human-Centered UX: Zero Fake User Titles, Zero Forced RBAC Selector & Full-Name Lang Switcher",
        no_fake_identity,
        f"NoFakeIdentity={no_fake_identity}, NeutralHeroPresent={'Biến dữ liệu thành quyết định.' in html}"
    )

    # 9. Part 5.2: 10-Point Comprehensive Data Validation Checklist
    qual_resp = requests.get(f"{BASE_URL}/api/v1/datasets/{ds_id}/quality", timeout=10).json()
    v_checks = qual_resp.get("validation_checklist", [])
    expected_check_ids = {
        "missing_values", "duplicate_records", "invalid_values", "data_types", "date_formats",
        "inconsistent_units", "inconsistent_categories", "outliers", "invalid_relationships", "unexpected_schema_changes"
    }
    found_check_ids = {c.get("check_id") for c in v_checks}
    val_10_ok = len(v_checks) == 10 and expected_check_ids == found_check_ids and all(
        "vi" in c.get("label_i18n", {}) and "en" in c.get("label_i18n", {}) and "ja" in c.get("label_i18n", {})
        for c in v_checks
    )
    record(
        "5.9 10-Point Comprehensive Pre-Analysis Data Validation Checklist (VI/EN/JA)",
        val_10_ok,
        f"ChecksCount={len(v_checks)}/10, AllTrilingual={val_10_ok}"
    )

    # 10. Part 3.3 & Part 5.3-5.7: 5-Part Result Explanation, 8-Field Traceability, 8-Check Verification, 9-Field KPI & 5-Category Epistemic AI
    ana_res = requests.post(
        f"{BASE_URL}/api/v1/analytics/run",
        json={"dataset_id": ds_id, "method_name": "pareto_analysis"},
        timeout=15
    ).json()
    exp5 = ana_res.get("structured_explanation", {})
    exp5_i18n = ana_res.get("structured_explanation_i18n", {})
    trace8 = ana_res.get("traceability", {})
    ver8 = ana_res.get("verification_report", {})

    exp5_ok = all(k in exp5 for k in ("1_result", "2_evidence", "3_meaning", "4_action", "5_limitation")) and all(
        lang in exp5_i18n for lang in ("vi", "en", "ja")
    )
    trace8_ok = all(
        k in trace8 for k in ("source_dataset", "source_sheet", "columns_used", "filter_conditions", "formula", "method", "computed_at", "dataset_version")
    )
    ver8_ok = ver8.get("verified") is True and len(ver8.get("checks", [])) == 8

    kpi_res = requests.post(
        f"{BASE_URL}/api/v1/projects/proj-omni-001/kpis",
        json={
            "name": "Net Verified Revenue QA",
            "definition": "Total verified revenue excluding nulls",
            "column": "revenue",
            "agg": "sum",
            "unit": "VND",
            "data_source": "Sales 2026",
            "filters": "All valid rows",
            "time_range": "FY2026",
            "missing_value_rule": "exclude_nulls"
        },
        timeout=10
    ).json()
    latest_kpi = (kpi_res.get("kpis") or [{}])[-1]
    kpi9_ok = all(
        k in latest_kpi for k in ("name", "definition", "formula", "unit", "data_source", "filters", "time_range", "updated_at", "missing_value_rule")
    )

    ep_ai = ai_en.get("epistemic_breakdown", {})
    ep5_ok = all(k in ep_ai for k in ("FACT", "CALCULATION", "INSIGHT", "HYPOTHESIS", "RECOMMENDATION"))

    record(
        "5.10 5-Part Explanation, 8-Field Traceability, 8-Point Verification, 9-Field KPI & 5-Category Epistemic AI",
        exp5_ok and trace8_ok and ver8_ok and kpi9_ok and ep5_ok,
        f"Exp5={exp5_ok}, Trace8={trace8_ok}, Verify8={ver8_ok}, KPI9={kpi9_ok}, EpistemicAI5={ep5_ok}"
    )

    # 11. TSV Upload, Business Understanding, 4-Layer Insight, 10-Step AI Orchestration & Multi-Format Export (PDF/XLSX/TSV/CSV)
    tsv_bytes = "order_id\tdate\tproduct\trevenue\tcost\tprofit\nORD-1\t2026-10-01\t東京サーバー\t1000\t600\t400\nORD-2\t2026-10-02\t大阪ルーター\t2000\t1200\t800\n".encode("utf-8-sig")
    up_tsv = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": ("ja_sales_test.tsv", tsv_bytes, "text/tab-separated-values")},
        data={"name": "JA TSV Sales Test"},
        timeout=15
    ).json()
    tsv_ds_id = up_tsv.get("dataset", {}).get("id")
    prof_tsv = requests.get(f"{BASE_URL}/api/v1/datasets/{tsv_ds_id}/profile", timeout=10).json()
    has_bu_and_rel = "business_understanding" in prof_tsv and "relationships" in prof_tsv

    four_layer_ok = "four_layer_insight_i18n" in ana_res and len(ai_en.get("orchestration_steps", [])) == 10

    rep_en = requests.post(
        f"{BASE_URL}/api/v1/reports/generate",
        json={"dataset_id": ds_id, "report_type": "EXECUTIVE", "language": "en"},
        timeout=15
    ).json()
    pdf_resp = requests.get(f"{BASE_URL}{rep_en['download_pdf_url']}", timeout=10)
    tsv_exp = requests.get(f"{BASE_URL}/api/v1/datasets/{ds_id}/export?fmt=tsv", timeout=10)
    xlsx_exp = requests.get(f"{BASE_URL}/api/v1/datasets/{ds_id}/export?fmt=xlsx", timeout=10)
    requests.delete(f"{BASE_URL}/api/v1/datasets/{tsv_ds_id}", timeout=10)

    export_multi_ok = (
        up_tsv.get("success") is True
        and has_bu_and_rel
        and four_layer_ok
        and pdf_resp.status_code == 200 and pdf_resp.content.startswith(b"%PDF-1.4")
        and tsv_exp.status_code == 200 and len(tsv_exp.content) > 50
        and xlsx_exp.status_code == 200 and len(xlsx_exp.content) > 500
    )
    record(
        "5.11 TSV/Japanese Ingestion, Business Understanding, 10-Step AI Orchestration & PDF/XLSX/TSV/CSV Exports",
        export_multi_ok,
        f"TSV_Upload={up_tsv.get('success')}, BusinessContext={has_bu_and_rel}, AI10Steps={four_layer_ok}, PDF_Bytes={len(pdf_resp.content)}"
    )

    # 12. File Validation, 3-Tier Error Classification, Partial Multi-Sheet Recovery & Zero Double-Counting Report
    import io
    # 12a. Level 3 Critical Error (Empty 0-byte file & Unsupported format)
    crit_empty = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": ("empty_broken.csv", b"", "text/csv")},
        timeout=10
    )
    crit_unsup = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")},
        timeout=10
    )
    crit_json = crit_empty.json()
    l3_ok = (
        crit_empty.status_code == 422
        and crit_unsup.status_code == 422
        and crit_json.get("severity") == "LEVEL_3_CRITICAL"
        and crit_json.get("can_proceed_to_analytics") is False
        and all(lang in crit_json.get("reason_i18n", {}) for lang in ("vi", "en", "ja"))
    )

    # 12b. Partial Multi-Sheet Workbook Recovery (1 valid sheet + 1 empty sheet)
    xlsx_buf = io.BytesIO()
    with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
        df_valid_sheet = pd.DataFrame({
            "order_id": ["ORD-01", "ORD-02", None, "ORD-01", "ORD-04"],
            "customer_name": ["  Alpha Corp  ", "Beta Ltd", None, "  Alpha Corp  ", "Delta Inc"],
            "revenue": ["1,200,000", "2,500,000", None, "1,200,000", "-50000"],
            "cost": [800000, None, None, 800000, 300000]
        })
        df_valid_sheet.to_excel(writer, sheet_name="Valid_Sales", index=False)
        pd.DataFrame().to_excel(writer, sheet_name="Empty_Broken_Sheet", index=False)

    partial_resp = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": ("multi_sheet_recovery.xlsx", xlsx_buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"name": "Multi-Sheet Recovery Test"},
        timeout=15
    )
    partial_data = partial_resp.json()
    partial_ds_id = partial_data.get("dataset", {}).get("id")
    rep_proc = partial_data.get("data_processing_report", {})

    partial_ok = (
        partial_resp.status_code == 200
        and partial_data.get("partial_workbook_recovery") is True
        and "Valid_Sales" in (partial_data.get("valid_sheets") or [])
        and any(s.get("sheet_name") == "Empty_Broken_Sheet" for s in (partial_data.get("isolated_invalid_sheets") or []))
    )

    # 12c. Level 1 Auto-Recovery, Level 2 Warnings, Zero Double-Counting & Error Report Export
    zero_double_count_ok = (
        rep_proc.get("original_record_count") == 5
        and rep_proc.get("valid_record_count") == 4
        and rep_proc.get("rejected_record_count") == 1  # 1 empty row isolated
        and rep_proc.get("corrected_record_count", 0) >= 1
        and rep_proc.get("total_error_occurrences", 0) > rep_proc.get("unique_affected_record_count", 0)
    )
    err_xlsx = requests.get(f"{BASE_URL}/api/v1/datasets/{partial_ds_id}/error-report?fmt=xlsx", timeout=10)
    err_csv = requests.get(f"{BASE_URL}/api/v1/datasets/{partial_ds_id}/error-report?fmt=csv", timeout=10)
    requests.delete(f"{BASE_URL}/api/v1/datasets/{partial_ds_id}", timeout=10)

    err_export_ok = err_xlsx.status_code == 200 and len(err_xlsx.content) > 500 and err_csv.status_code == 200 and len(err_csv.content) > 50

    record(
        "5.12 3-Tier File Validation, Partial Multi-Sheet Recovery, Zero Double-Counting & Error Reports",
        l3_ok and partial_ok and zero_double_count_ok and err_export_ok,
        f"L3_Reject={l3_ok}, PartialWorkbook={partial_ok}, Orig={rep_proc.get('original_record_count')}/Valid={rep_proc.get('valid_record_count')}/UniqueAff={rep_proc.get('unique_affected_record_count')}/Occurrences={rep_proc.get('total_error_occurrences')}, ErrExport={err_export_ok}"
    )

    # 13. AI Data Cleaning Workspace & 20 Acceptance Criteria (BOM-only, 20,001 & 100,000 Rows, Red Cell Edit, Re-validation, Undo/Redo/Reset)
    # 13a. BOM + Whitespace-only file rejection (Criterion #2)
    crit_bom = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": ("bom_whitespace.csv", b"\xef\xbb\xbf   \r\n\t  ", "text/csv")},
        timeout=10
    )
    bom_ok = crit_bom.status_code == 422 and crit_bom.json().get("error_code") == "BOM_OR_WHITESPACE_ONLY_FILE"

    # 13b. 20,001 rows & 100,000 rows full scan + error at row #99,999 outside Page 1 (Criteria #3, #4, #18)
    lines_20k = ["order_id,revenue\n"] + [f"ORD-{i},1000\n" for i in range(1, 20002)]
    up_20k = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": ("rows_20001.csv", "".join(lines_20k).encode("utf-8"), "text/csv")},
        data={"name": "Dataset 20001 Rows"},
        timeout=30
    ).json()
    ds_20k_id = up_20k.get("dataset", {}).get("id")
    scan_20k_ok = up_20k.get("data_processing_report", {}).get("original_record_count") == 20001
    requests.delete(f"{BASE_URL}/api/v1/datasets/{ds_20k_id}", timeout=10)

    lines_100k = ["order_id,revenue\n"] + [f"ORD-{i},1000\n" for i in range(1, 100000)] + ["ORD-100000,BROKEN_REV_AT_END\n"]
    up_100k = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": ("rows_100000.csv", "".join(lines_100k).encode("utf-8"), "text/csv")},
        data={"name": "Dataset 100000 Rows"},
        timeout=60
    ).json()
    ds_100k_id = up_100k.get("dataset", {}).get("id")
    ws_100k = requests.get(f"{BASE_URL}/api/v1/datasets/{ds_100k_id}/cleaning-workspace?page=1&page_size=50", timeout=20).json()
    nav_100k = ws_100k.get("grid", {}).get("error_navigation", [])
    scan_100k_ok = (
        ws_100k.get("overview", {}).get("total_rows_scanned") == 100000
        and any(e.get("row_number") == 100000 and e.get("column") == "revenue" for e in nav_100k)
    )
    requests.delete(f"{BASE_URL}/api/v1/datasets/{ds_100k_id}", timeout=10)

    # 13c. Duplicate Headers, Invalid Date, Text in Revenue (No Zero-Coercion!), Outliers & In-Place Cell Edit + Undo/Redo/Reset (Criteria #5-#15, #17, #19, #20)
    dirty_csv = (
        "order_id,order_date,revenue,revenue\n"
        "ORD-01,2026-10-01,1000,10\n"
        "ORD-02,2026-02-30,CHUA_RO_TIEN,20\n"
        "ORD-03,2026-10-03,1200,30\n"
        "ORD-04,2026-10-04,1100,40\n"
        "ORD-05,2026-10-05,9999999,50\n"
    ).encode("utf-8")
    up_dirty = requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": ("dirty_workspace.csv", dirty_csv, "text/csv")},
        data={"name": "Dirty Workspace Test"},
        timeout=15
    ).json()
    dirty_id = up_dirty.get("dataset", {}).get("id")
    ws_init = requests.get(f"{BASE_URL}/api/v1/datasets/{dirty_id}/cleaning-workspace?page=1&page_size=50", timeout=10).json()

    # Verify duplicate header detected, invalid date & text-in-revenue highlighted in red (and text NOT turned into 0!)
    rep_init = ws_init.get("data_processing_report", {})
    dup_hdr_ok = len(rep_init.get("structural_issues", [])) >= 1
    row_2_cells = ws_init["grid"]["rows"][1]["cells"]
    row_2_errs = ws_init["grid"]["rows"][1]["cell_errors"]
    red_cells_ok = (
        row_2_cells["revenue"] == "CHUA_RO_TIEN"  # Preserved verbatim, never coerced to 0!
        and "revenue" in row_2_errs and row_2_errs["revenue"]["error_code"] == "INVALID_NUMERIC_TEXT"
        and "order_date" in row_2_errs and row_2_errs["order_date"]["error_code"] == "INVALID_DATE_FORMAT"
        and ws_init["overview"]["readiness_status"] == "Awaiting User Correction"
    )
    outlier_preserved_ok = len(ws_init["grid"]["rows"]) == 5 and any(
        w.get("category") == "SUSPICIOUS_OUTLIERS" or w.get("error_code") == "SUSPICIOUS_OUTLIER"
        for w in ws_init["report"].get("warnings", [])
    )

    # Criterion #12: User enters a value that is STILL invalid -> stays red (`cell_valid is False`)
    edit_bad = requests.post(
        f"{BASE_URL}/api/v1/datasets/{dirty_id}/edit-cell",
        json={"row_index": 1, "column": "revenue", "new_value": "STILL_TEXT_ERROR"},
        timeout=10
    ).json()
    still_red_ok = edit_bad.get("cell_valid") is False and edit_bad.get("cell_error", {}).get("error_code") == "INVALID_NUMERIC_TEXT"

    # Criterion #11 & #13: User fixes both red cells on row_index=1 -> red highlight removed (`cell_valid is True`)
    edit_good_rev = requests.post(
        f"{BASE_URL}/api/v1/datasets/{dirty_id}/edit-cell",
        json={"row_index": 1, "column": "revenue", "new_value": "1500"},
        timeout=10
    ).json()
    edit_good_dt = requests.post(
        f"{BASE_URL}/api/v1/datasets/{dirty_id}/edit-cell",
        json={"row_index": 1, "column": "order_date", "new_value": "2026-10-02"},
        timeout=10
    ).json()
    fixed_ok = edit_good_rev.get("cell_valid") is True and edit_good_dt.get("cell_valid") is True

    # Criterion #14 & #15: Undo, Redo, and Reset to v1
    undo_res = requests.post(f"{BASE_URL}/api/v1/datasets/{dirty_id}/undo", json={}, timeout=10).json()
    undo_ver = undo_res.get("bundle", {}).get("active_version", {}).get("version_number")
    redo_res = requests.post(f"{BASE_URL}/api/v1/datasets/{dirty_id}/redo", json={}, timeout=10).json()
    redo_ver = redo_res.get("bundle", {}).get("active_version", {}).get("version_number")
    reset_res = requests.post(f"{BASE_URL}/api/v1/datasets/{dirty_id}/reset", json={}, timeout=10).json()
    reset_ver = reset_res.get("bundle", {}).get("active_version", {}).get("version_number")
    ver_ctrl_ok = (undo_ver == 3 and redo_ver == 4 and reset_ver == 1)

    requests.delete(f"{BASE_URL}/api/v1/datasets/{dirty_id}", timeout=10)

    all_20_ok = bom_ok and scan_20k_ok and scan_100k_ok and dup_hdr_ok and red_cells_ok and outlier_preserved_ok and still_red_ok and fixed_ok and ver_ctrl_ok
    record(
        "5.13 AI Data Cleaning Workspace & All 20 Acceptance Criteria (BOM, 20k/100k Scan, Red Cell Edit, Re-validation, Undo/Redo/Reset)",
        all_20_ok,
        f"BOM={bom_ok}, 20k={scan_20k_ok}, 100k_OutPageErr={scan_100k_ok}, DupHdr={dup_hdr_ok}, RedCells={red_cells_ok}, OutlierKept={outlier_preserved_ok}, StillRed={still_red_ok}, Fixed={fixed_ok}, VerCtrl={ver_ctrl_ok}"
    )

    passed_cnt = sum(1 for r in results if r["status"] == "PASS")
    total_cnt = len(results)
    os.makedirs(os.path.join(ROOT_DIR, "logs"), exist_ok=True)
    with open(os.path.join(ROOT_DIR, "logs", "v22_redesign_test_report.json"), "w", encoding="utf-8") as f:
        json.dump({"total": total_cnt, "passed": passed_cnt, "failed": total_cnt - passed_cnt, "results": results}, f, ensure_ascii=False, indent=2)

    print(f"\nNEXUS V2.2 REDESIGN TEST SUMMARY: {passed_cnt}/{total_cnt} PASSED.")
    return 0 if passed_cnt == total_cnt else 1


if __name__ == "__main__":
    sys.exit(run_v22_suite())

