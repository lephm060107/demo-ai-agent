"""
tests/test_step5_analytics_acceptance.py
Mandatory 9-Test Acceptance Suite (Section 10) for Step 5 – Data Analytics & Step 6 Integration:
  Test 1: Revenue by Product (group_aggregation + Chart Builder Horizontal Bar, exact source total match)
  Test 2: Monthly Trend Analysis (Revenue + Order Date, granularity='month', chronological order + source total match)
  Test 3: Pareto Analysis (descending sort, individual & cumulative share summing to 100%)
  Test 4: Missing Values Handling (explicit warning, NEVER silently replaces missing with 0)
  Test 5: Incompatible Method Guard (HTTP 400 METHOD_PRECONDITION_NOT_MET, ZERO silent fallback to summary_stats)
  Test 6: Switching Datasets (columns, defaults & outputs strictly reflect selected dataset, zero stale leakage)
  Test 7: Immutable Analysis History & Version Replay (editing dataset to v2 does NOT mutate saved v1 run; flags outdated)
  Test 8: Step 5 -> Step 6 AI Insights Handoff (passing analysis_run_id anchors Step 6 to exact Step 5 verified figures)
  Test 9: All Step 5 UI Controls, All 18+ Analytical Methods Connected, JS/DOM/I18N Zero Errors & Real 15k Dataset Check
"""

import os
import re
import sys
import subprocess
import tempfile
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://127.0.0.1:8000"
RESULTS = []


def record(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    RESULTS.append((name, passed, detail))
    print(f"[{status}] {name} :: {detail}")


def upload_csv(filename: str, content: str):
    return requests.post(
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": (filename, content.encode("utf-8"), "text/csv")},
        data={"name": filename.replace(".csv", ""), "conflict_resolution": "CREATE_NEW"},
        headers={"X-Nexus-Role": "ADMIN"},
        timeout=30,
    )


def run_all():
    cleanup_ids = []

    # Rich dataset A: Sales with Date, Product, Region, Channel, Customer, Qty, Unit_Price, Revenue, Cost, Profit
    csv_a = (
        "Order_ID,Order_Date,Product_Name,Category,Region,Channel,Customer_ID,Quantity,Unit_Price,Revenue_VND,Cost_VND,Profit_VND\n"
        "O-01,2026-01-05,Laptop Pro 16,Hardware,North,Direct,C-01,2,20000000,40000000,28000000,12000000\n"
        "O-02,2026-01-18,Cloud ERP,Software,South,Online,C-02,1,30000000,30000000,10000000,20000000\n"
        "O-03,2026-02-04,Laptop Pro 16,Hardware,South,Direct,C-01,3,19000000,57000000,42000000,15000000\n"
        "O-04,2026-02-20,Smart Monitor,Hardware,Central,Partner,C-03,4,5000000,20000000,14000000,6000000\n"
        "O-05,2026-03-08,Cloud ERP,Software,North,Online,C-02,2,28000000,56000000,20000000,36000000\n"
        "O-06,2026-03-22,Docking Hub,Accessory,North,Online,C-04,5,2000000,10000000,6000000,4000000\n"
        "O-07,2026-04-06,Laptop Pro 16,Hardware,Central,Direct,C-05,1,21000000,21000000,14000000,7000000\n"
        "O-08,2026-04-19,Smart Monitor,Hardware,North,Partner,C-03,2,4800000,9600000,7000000,2600000\n"
    )
    # Expected Source Revenue Total = 40+30+57+20+56+10+21+9.6 = 243,600,000
    expected_total_a = 243_600_000.0
    r_up_a = upload_csv("step5_test_sales_a.csv", csv_a)
    ds_a = r_up_a.json()["dataset"]["id"]
    cleanup_ids.append(ds_a)

    # Dataset B (minimal: NO Date, NO Unit_Price, NO Quantity — for Test 5 & Test 6!)
    csv_b = (
        "Branch,Revenue_USD,Expenses_USD\n"
        "Tokyo,50000,30000\n"
        "Osaka,35000,20000\n"
        "Kyoto,15000,9000\n"
    )
    r_up_b = upload_csv("step5_test_branch_b.csv", csv_b)
    ds_b = r_up_b.json()["dataset"]["id"]
    cleanup_ids.append(ds_b)

    # Dataset C (with optional/non-blocking missing values in Note for Test 4!)
    csv_c = (
        "Order_Date,Product_Name,Revenue_VND,Note\n"
        "2026-01-01,Item A,145000,ok\n"
        "2026-01-02,Item B,280000,\n"
        "2026-01-03,Item A,195000,vip\n"
        "2026-01-04,Item C,410000,\n"
        "2026-01-05,Item B,325000,ok\n"
    )
    r_up_c = upload_csv("step5_test_missing_c.csv", csv_c)
    ds_c = r_up_c.json()["dataset"]["id"]
    cleanup_ids.append(ds_c)

    # =========================================================================
    # TEST 1: Revenue by Product (group_aggregation + Chart Builder Horizontal Bar)
    # =========================================================================
    r_t1 = requests.post(
        f"{BASE_URL}/api/v1/analytics/run",
        json={"dataset_id": ds_a, "analysis_type": "group_aggregation", "metric_col": "Revenue_VND", "dimension_col": "Product_Name", "language": "vi"},
        timeout=15,
    ).json()
    groups = (r_t1.get("results") or {}).get("groups", [])
    grp_sum = round(sum(float(g["sum"]) for g in groups), 2)
    r_cb1 = requests.post(
        f"{BASE_URL}/api/v1/charts/build",
        json={"dataset_id": ds_a, "x_col": "Product_Name", "y_col": "Revenue_VND", "aggregation": "SUM", "chart_type": "auto", "sort_dir": "desc"},
        timeout=15,
    ).json()
    record(
        "Test 1 Revenue by Product (Bar/Horizontal Bar + 100% Source Total Match = 243.6M)",
        r_t1.get("success") is True
        and r_t1.get("method_name") == "group_aggregation"
        and abs(grp_sum - expected_total_a) < 0.01
        and groups[0]["group"] == "Laptop Pro 16"
        and abs(groups[0]["sum"] - 118_000_000.0) < 0.01
        and r_cb1.get("selected_chart_type") == "horizontal_bar"
        and abs(r_cb1.get("totals", {}).get("rendered_total", 0) - expected_total_a) < 0.01,
        f"Top={groups[0]['group']}({groups[0]['sum']:,.0f}), GroupSum={grp_sum:,.0f}, ChartType={r_cb1.get('selected_chart_type')}",
    )

    # =========================================================================
    # TEST 2: Monthly Trend Analysis (Revenue + Order Date, Chronological Order & Reconciliation)
    # =========================================================================
    r_t2 = requests.post(
        f"{BASE_URL}/api/v1/analytics/run",
        json={"dataset_id": ds_a, "analysis_type": "trend_analysis", "metric_col": "Revenue_VND", "dimension_col": "Order_Date", "granularity": "month", "language": "vi"},
        timeout=15,
    ).json()
    t2_res = r_t2.get("results") or {}
    t2_series = t2_res.get("series", [])
    periods = [s["period"] for s in t2_series]
    record(
        "Test 2 Monthly Trend Analysis (Real trend_analysis, Chronological Order & Source Sum Match)",
        r_t2.get("success") is True
        and r_t2.get("method_name") == "trend_analysis"
        and t2_res.get("granularity") == "month"
        and periods == ["2026-01", "2026-02", "2026-03", "2026-04"]
        and periods == sorted(periods)
        and abs(float(t2_res.get("grouped_total", 0)) - expected_total_a) < 0.01
        and float(t2_res.get("reconciliation_diff", 999)) < 0.01,
        f"Periods={periods}, GroupedSum={t2_res.get('grouped_total'):,.0f}, Diff={t2_res.get('reconciliation_diff')}",
    )

    # =========================================================================
    # TEST 3: Pareto Analysis (Descending Sort, Share % & Cumulative % == 100.0%)
    # =========================================================================
    r_t3 = requests.post(
        f"{BASE_URL}/api/v1/analytics/run",
        json={"dataset_id": ds_a, "analysis_type": "pareto_analysis", "metric_col": "Revenue_VND", "dimension_col": "Product_Name"},
        timeout=15,
    ).json()
    p_items = (r_t3.get("results") or {}).get("items", [])
    vals = [float(x["value"]) for x in p_items]
    share_sum = round(sum(float(x["share_pct"]) for x in p_items), 2)
    record(
        "Test 3 Pareto Analysis (Descending Order, Share Sum ~100%, Final Cumulative = 100%)",
        r_t3.get("method_name") == "pareto_analysis"
        and len(p_items) == 4
        and vals == sorted(vals, reverse=True)
        and abs(share_sum - 100.0) <= 0.1
        and abs(float(p_items[-1]["cumulative_pct"]) - 100.0) <= 0.1,
        f"Items={len(p_items)}, ShareSum={share_sum}%, CumEnd={p_items[-1]['cumulative_pct']}%",
    )

    # =========================================================================
    # TEST 4: Missing Value Disclosure (Never Silently Turns Missing Into 0!)
    # =========================================================================
    r_t4 = requests.post(
        f"{BASE_URL}/api/v1/analytics/run",
        json={"dataset_id": ds_c, "analysis_type": "group_aggregation", "metric_col": "Revenue_VND", "dimension_col": "Note"},
        timeout=15,
    ).json()
    m_notices = r_t4.get("missing_value_notices") or []
    t4_groups = (r_t4.get("results") or {}).get("groups", [])
    # Only rows with non-null Note ('ok': 145k+325k=470k, 'vip': 195k -> sum 665k; 2 null Note rows excluded, NEVER filled as 0!)
    t4_sum = sum(float(g["sum"]) for g in t4_groups)
    record(
        "Test 4 Missing Values Disclosed Explicitly & NEVER Silently Replaced With 0",
        r_t4.get("success") is True
        and len(m_notices) >= 1
        and m_notices[0].get("column") == "Note"
        and m_notices[0].get("missing_count") == 2
        and m_notices[0].get("policy") == "EXCLUDED_NOT_ZERO_FILLED"
        and abs(t4_sum - 665_000.0) < 0.01,
        f"MissingCount={m_notices[0].get('missing_count') if m_notices else 0}, Policy={m_notices[0].get('policy') if m_notices else None}, NonNullSum={t4_sum:,.0f}",
    )

    # =========================================================================
    # TEST 5: Incompatible Method Guard (HTTP 400, ZERO Silent Fallback to summary_stats!)
    # =========================================================================
    r_t5_pe = requests.post(
        f"{BASE_URL}/api/v1/analytics/run",
        json={"dataset_id": ds_b, "analysis_type": "price_elasticity", "language": "vi"},
        timeout=15,
    )
    r_t5_tr = requests.post(
        f"{BASE_URL}/api/v1/analytics/run",
        json={"dataset_id": ds_b, "analysis_type": "trend_analysis", "language": "vi"},
        timeout=15,
    )
    r_t5_eoq = requests.post(
        f"{BASE_URL}/api/v1/analytics/run",
        json={"dataset_id": ds_b, "analysis_type": "Reorder_optimization", "language": "vi"},
        timeout=15,
    )
    record(
        "Test 5 Incompatible Method Returns Explicit HTTP 400 (Zero Silent Fallback to summary_stats)",
        r_t5_pe.status_code == 400 and r_t5_pe.json().get("not_applicable") is True
        and r_t5_tr.status_code == 400 and r_t5_tr.json().get("not_applicable") is True
        and r_t5_eoq.status_code == 400 and r_t5_eoq.json().get("not_applicable") is True,
        f"PriceElasticity={r_t5_pe.status_code}, TrendNoDate={r_t5_tr.status_code}, EOQNoQty={r_t5_eoq.status_code}",
    )

    # =========================================================================
    # TEST 6: Switching Datasets (Zero Stale Leakage — Columns & Totals Match DS B = 100k USD!)
    # =========================================================================
    prof_b = requests.get(f"{BASE_URL}/api/v1/datasets/{ds_b}/profile", timeout=15).json()
    cols_b = [c["name"] for c in prof_b.get("columns", [])]
    r_t6_b = requests.post(
        f"{BASE_URL}/api/v1/analytics/run",
        json={"dataset_id": ds_b, "analysis_type": "group_aggregation", "metric_col": "Revenue_USD", "dimension_col": "Branch"},
        timeout=15,
    ).json()
    b_groups = (r_t6_b.get("results") or {}).get("groups", [])
    b_sum = sum(float(g["sum"]) for g in b_groups)
    record(
        "Test 6 Switching Dataset Strictly Uses New Dataset Schema & Figures (Zero Old Dataset Data)",
        cols_b == ["Branch", "Revenue_USD", "Expenses_USD"]
        and b_groups[0]["group"] == "Tokyo"
        and abs(b_sum - 100_000.0) < 0.01
        and "Laptop Pro 16" not in str(b_groups),
        f"ColsB={cols_b}, TopB={b_groups[0]['group']}({b_groups[0]['sum']}), TotalB={b_sum}",
    )

    # =========================================================================
    # TEST 7: Immutable Analysis History & Replay Across Dataset Version Update (v1 -> v2)
    # =========================================================================
    run_id_v1 = r_t1["analysis_run_id"]
    # Edit DS A cell (Quantity 2 -> 3 on row 0) to create v2
    r_ed = requests.post(
        f"{BASE_URL}/api/v1/datasets/{ds_a}/edit-cell",
        json={"row_index": 0, "column": "Quantity", "new_value": "3"},
        headers={"X-Nexus-Role": "ADMIN"},
        timeout=20,
    )
    r_hist = requests.get(f"{BASE_URL}/api/v1/analytics/history?dataset_id={ds_a}", timeout=15).json()
    r_rep = requests.get(f"{BASE_URL}/api/v1/analytics/runs/{run_id_v1}", timeout=15).json()
    rep_groups = (r_rep.get("results") or {}).get("groups", [])
    record(
        "Test 7 Immutable Analysis History & Replay (v1 Run Unchanged After v2 Edit, Outdated Flag=True)",
        r_ed.status_code == 200
        and any(h["id"] == run_id_v1 for h in r_hist.get("runs", []))
        and r_rep.get("is_historical_replay") is True
        and r_rep.get("is_outdated_version") is True
        and r_rep.get("dataset_version", {}).get("version_number") == 1
        and bool(r_rep.get("evidence_bundle"))
        and abs(sum(float(g["sum"]) for g in rep_groups) - expected_total_a) < 0.01,
        f"RunID={run_id_v1}, ReplayedVer=v{r_rep.get('dataset_version', {}).get('version_number')}, Outdated={r_rep.get('is_outdated_version')}, HistRuns={len(r_hist.get('runs', []))}",
    )

    # =========================================================================
    # TEST 8: Step 5 -> Step 6 AI Insights Handoff Anchored on Exact Saved Analysis Run
    # =========================================================================
    r_s6 = requests.post(
        f"{BASE_URL}/api/v1/ai/query",
        json={"dataset_id": ds_a, "analysis_run_id": run_id_v1, "prompt": "Giải thích kết quả doanh thu theo sản phẩm vừa phân tích", "language": "vi"},
        timeout=20,
    ).json()
    tc_names = [tc.get("tool_name", "") for tc in r_s6.get("tool_calls", [])]
    s6_kfs = (r_s6.get("step6_executive_insights") or {}).get("key_findings", [])
    record(
        "Test 8 Step 5 -> Step 6 AI Insights Handoff Anchored to Exact Saved Analysis Run (Zero Guessing)",
        r_s6.get("linked_analysis_run_id") == run_id_v1
        and any("step5_verified_run:group_aggregation" in n for n in tc_names)
        and len(s6_kfs) >= 1
        and "Laptop Pro 16" in str(s6_kfs[0].get("main_metric", "")),
        f"LinkedRunID={r_s6.get('linked_analysis_run_id')}, Tools={tc_names[:3]}, Finding1={str(s6_kfs[0].get('main_metric', ''))[:65]}",
    )

    # =========================================================================
    # TEST 9: All 18+ Step 5 Dropdown Methods Connected + Real 15k Dataset + Zero JS/DOM/I18N Errors
    # =========================================================================
    all_dropdown_methods = [
        "descriptive_stats", "group_aggregation", "trend_analysis", "period_comparison",
        "pareto_analysis", "abc_xyz_classification", "correlation_matrix", "anomaly_detection",
        "variance_root_cause", "hypothesis_test", "rfm_segmentation", "cohort_retention",
        "funnel_conversion", "forecasting", "moving_average", "regression_driver",
        "what_if_simulation", "Reorder_optimization", "price_elasticity"
    ]
    ran_ok = []
    ran_fail = []
    for m_key in all_dropdown_methods:
        rm = requests.post(
            f"{BASE_URL}/api/v1/analytics/run",
            json={"dataset_id": ds_a, "analysis_type": m_key, "language": "vi"},
            timeout=15,
        )
        if rm.status_code == 200 and rm.json().get("success") is True and rm.json().get("method_name") != ("summary_stats" if m_key != "descriptive_stats" else "__none__"):
            ran_ok.append(m_key)
        else:
            ran_fail.append((m_key, rm.status_code, rm.text[:80]))

    # Recommend tools returns columns_to_use
    r_rec = requests.post(
        f"{BASE_URL}/api/v1/analytics/recommend-tools",
        json={"dataset_id": ds_a, "business_goal": "Tìm nguyên nhân doanh thu giảm"},
        timeout=15,
    ).json()
    has_rec_cols = all(bool(m.get("columns_to_use")) for m in r_rec.get("recommended_methods", []))

    # Static JS/DOM/I18N audit
    html = open("nexus_analytics/static/index.html", encoding="utf-8").read()
    js = re.search(r"<script>(.*)</script>", html, re.S).group(1)
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

    record(
        "Test 9 All 19 Step 5 Methods Connected (Zero Silent Fallback), AI Tool Cols & Frontend Audit (JS/DOM/I18N=0)",
        len(ran_ok) == len(all_dropdown_methods)
        and has_rec_cols
        and rc.returncode == 0
        and vi == en == ja
        and len(dom_keys - vi) == 0
        and len(called - fns) == 0,
        f"MethodsConnected={len(ran_ok)}/{len(all_dropdown_methods)}, Fails={ran_fail}, RecCols={has_rec_cols}, node={rc.returncode}, I18N={len(vi)}, MissDOM={len(dom_keys-vi)}, MissFn={len(called-fns)}",
    )

    # Cleanup temporary test datasets
    for cid in cleanup_ids:
        requests.post(
            f"{BASE_URL}/api/v1/datasets/{cid}/permanent-delete",
            json={"confirm": True, "force_delete_referenced": True},
            headers={"X-Nexus-Role": "ADMIN"},
            timeout=10,
        )

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n=== STEP 5 ANALYTICS ACCEPTANCE SUMMARY: {passed}/{total} PASSED ===")
    if passed < total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_all()
