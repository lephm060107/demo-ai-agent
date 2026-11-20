"""
tests/test_suite.py
Bộ kiểm thử tự động cho Hệ thống Master Workflow AI Agent (Công ty Thiên Minh):
1. Normal Testing (Case 1 đầy đủ thông tin, đạt Gate 1-5)
2. Missing Data & Contradiction Testing (Case 2 thiếu tin -> Gate 1; Mâu thuẫn ngày; Không khớp kỹ thuật -> Gate 2)
3. Boundary Testing (Ngưỡng chiết khấu 5.0 vs 5.01 vs 15.0 vs 15.01; Biên tồn kho stock == qty vs stock == qty-1; Biên tiến độ days == req vs days == req-1; Chuyển trạng thái HITL)
4. Custom Dataset Testing (Nạp bộ dữ liệu SKU & giá hoàn toàn mới, chứng minh không hardcode)
"""

import os
import sys
import json
import pandas as pd

# Đảm bảo import từ thư mục gốc project
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from agent_engine.data_loader import load_default_master_data
from tools.doc_reader_tool import DocumentReaderTool
from tools.tool_base import ToolTracer
from tools.policy_checker_tool import PolicyCheckerTool
from engine.orchestrator import MasterOrchestrator, load_business_rules


def read_text(rel_path: str) -> str:
    with open(os.path.join(ROOT_DIR, rel_path), "r", encoding="utf-8") as f:
        return f.read()


def run_all_tests():
    results = []
    master_data = load_default_master_data(os.path.join(ROOT_DIR, "data/thienminh_master_data.xlsx"))
    rules = load_business_rules(os.path.join(ROOT_DIR, "config/business_rules.json"))

    def record(name: str, passed: bool, detail: str):
        status = "PASS" if passed else "FAIL"
        results.append({"test": name, "status": status, "detail": detail})
        print(f"[{status}] {name} -> {detail}")

    # =========================================================================
    # NHÓM 1: NORMAL TESTING
    # =========================================================================
    case1_text = read_text("data/rfp_case_1_day_du.txt")
    orch = MasterOrchestrator(business_rules=rules)
    res1 = orch.run(case1_text, master_data, custom_discount=5.0, source_type="TXT")

    ok1 = (
        res1["phase_status"] == "COMPLETED"
        and res1["gate_1_passed"] is True
        and res1["gate_2_passed"] is True
        and res1["gate_3_passed"] is True
        and res1["gate_4_passed"] is True
        and res1["gate_5_passed"] is True
        and len(res1["tool_calls"]) >= 6
        and os.path.exists(res1["output_files"].get("excel_boq", ""))
        and os.path.exists(res1["output_files"].get("word_proposal", ""))
        and os.path.exists(res1["output_files"].get("json_report", ""))
    )
    record(
        "1.1 Normal Workflow (Case 1 đầy đủ)",
        ok1,
        f"Status={res1['phase_status']}, Net={res1['quotation']['net_quoted_price']:,.0f} đ, Margin={res1['quotation']['gross_margin_pct']:.2f}%, Tools={len(res1['tool_calls'])}"
    )

    # Kiểm tra đọc file thực tế qua DocumentReaderTool
    tracer = ToolTracer()
    doc_tool = DocumentReaderTool(tracer=tracer)
    doc_res = doc_tool.read_text_from_path(os.path.join(ROOT_DIR, "data/rfp_case_1_day_du.txt"))
    record(
        "1.2 DocumentReaderTool đọc file thực tế",
        doc_res["success"] and len(doc_res["text"]) > 100 and len(tracer.records) == 1,
        f"DocType={doc_res['doc_type']}, Chars={len(doc_res['text'])}, ToolCallID={tracer.records[0].call_id}"
    )

    # =========================================================================
    # NHÓM 2: MISSING DATA, CONTRADICTION & UNMATCHED TESTING
    # =========================================================================
    case2_text = read_text("data/rfp_case_2_thieu_thong_tin.txt")
    res2 = orch.run(case2_text, master_data, custom_discount=5.0)
    ok2 = (
        res2["phase_status"] == "PAUSED_AT_GATE_1"
        and res2["gate_1_passed"] is False
        and len(res2["completeness"]["missing_items"]) >= 3
        and bool(res2["completeness"]["clarification_letter"])
    )
    record(
        "2.1 Missing Data (Case 2 thiếu thông tin -> Gate 1 Block)",
        ok2,
        f"Status={res2['phase_status']}, Missing={len(res2['completeness']['missing_items'])} nhóm"
    )

    # 2.2 Mâu thuẫn ngày tháng (Ngày bắt đầu sau ngày hoàn thành)
    contradiction_rfq = """
    Kính gửi Thiên Minh,
    Khách hàng: Công ty Kiểm Thử Mâu Thuẫn
    Địa điểm: Quận 1, TP.HCM
    Danh mục thiết bị:
    - 02 Switch 24-port PoE+ Layer 3
    Yêu cầu SLA: 8x5
    Thời gian bắt đầu triển khai: 25/12/2026
    Thời hạn hoàn thành nghiệm thu: 10/12/2026
    """
    res_contra = orch.run(contradiction_rfq, master_data, custom_discount=5.0)
    ok_contra = (
        res_contra["phase_status"] == "PAUSED_AT_GATE_1"
        and res_contra["gate_1_passed"] is False
        and len(res_contra["completeness"]["inconsistencies"]) >= 1
    )
    record(
        "2.2 Contradiction Test (Mâu thuẫn Timeline -> Gate 1 Block)",
        ok_contra,
        f"Inconsistencies={res_contra['completeness']['inconsistencies']}"
    )

    # 2.3 Gate 2 Block: Yêu cầu PoE nhưng danh mục chỉ có Non-PoE
    non_poe_only_df = master_data["DanhMuc_SanPham"][
        ~master_data["DanhMuc_SanPham"]["sku"].isin(["SW-C9200L-24P", "SW-C9200L-48P"])
    ].copy()
    restricted_master = dict(master_data)
    restricted_master["DanhMuc_SanPham"] = non_poe_only_df

    res_g2 = orch.run(case1_text, restricted_master, custom_discount=5.0)
    ok_g2 = (
        res_g2["phase_status"] == "STOPPED_AT_GATE_2_UNMATCHED"
        and res_g2["gate_1_passed"] is True
        and res_g2["gate_2_passed"] is False
        and len(res_g2["validation"]["unmatched_items"]) >= 1
    )
    record(
        "2.3 Unmatched Technical Spec (Yêu cầu PoE nhưng chỉ có Non-PoE -> Gate 2 Block)",
        ok_g2,
        f"Status={res_g2['phase_status']}, Unmatched={res_g2['validation']['unmatched_items'][0]['category']}"
    )

    # =========================================================================
    # NHÓM 3: BOUNDARY TESTING (ĐÚNG NGƯỠNG BIÊN)
    # =========================================================================
    pol_tool = PolicyCheckerTool(policies_df=master_data.get("ChinhSach_ChuyenDuyet"), business_rules=rules)

    # 3.1 Discount boundaries (5.0% vs 5.01% vs 15.0% vs 15.01%) với Margin an toàn 30% & Deal nhỏ 200M
    p_500 = pol_tool.evaluate_policies(5.0, 30.0, 200_000_000, False, False, [])
    p_501 = pol_tool.evaluate_policies(5.01, 30.0, 200_000_000, False, False, [])
    p_1500 = pol_tool.evaluate_policies(15.0, 25.0, 200_000_000, False, False, [])
    p_1501 = pol_tool.evaluate_policies(15.01, 25.0, 200_000_000, False, False, [])

    ok_disc_bounds = (
        p_500["needs_special_approval"] is False
        and p_501["needs_special_approval"] is True and p_501["needs_director"] is False
        and p_1500["needs_special_approval"] is True and p_1500["needs_director"] is False
        and p_1501["needs_director"] is True
    )
    record(
        "3.1 Discount Threshold Boundaries (5.0% / 5.01% / 15.0% / 15.01%)",
        ok_disc_bounds,
        f"5.0%->{not p_500['needs_special_approval']} | 5.01%->Mgr({p_501['needs_special_approval']}) | 15.0%->Mgr({not p_1500['needs_director']}) | 15.01%->Dir({p_1501['needs_director']})"
    )

    # 3.2 Margin boundaries (25.0% vs 24.99% vs 18.0% vs 17.99%)
    m_2500 = pol_tool.evaluate_policies(0.0, 25.0, 200_000_000, False, False, [])
    m_2499 = pol_tool.evaluate_policies(0.0, 24.99, 200_000_000, False, False, [])
    m_1800 = pol_tool.evaluate_policies(0.0, 18.0, 200_000_000, False, False, [])
    m_1799 = pol_tool.evaluate_policies(0.0, 17.99, 200_000_000, False, False, [])

    ok_margin_bounds = (
        m_2500["needs_special_approval"] is False
        and m_2499["needs_special_approval"] is True and m_2499["needs_director"] is False
        and m_1800["needs_special_approval"] is True and m_1800["needs_director"] is False
        and m_1799["needs_director"] is True
    )
    record(
        "3.2 Gross Margin Boundaries (25.0% / 24.99% / 18.0% / 17.99%)",
        ok_margin_bounds,
        f"25.0%->Self | 24.99%->Mgr | 18.0%->Mgr | 17.99%->Dir({m_1799['needs_director']})"
    )

    # 3.3 Stock boundary: stock == quantity (2) vs stock == quantity - 1 (1) cho SW-C9200L-24P
    stock_eq_df = master_data["DanhMuc_SanPham"].copy()
    stock_eq_df.loc[stock_eq_df["sku"] == "SW-C9200L-24P", "stock"] = 2
    m_stock_eq = dict(master_data)
    m_stock_eq["DanhMuc_SanPham"] = stock_eq_df
    res_stock_eq = orch.run(case1_text, m_stock_eq, custom_discount=5.0)
    sw_warns_eq = [w for w in res_stock_eq["validation"]["inventory_warnings"] if "SW-C9200L-24P" in w]

    stock_lt_df = master_data["DanhMuc_SanPham"].copy()
    stock_lt_df.loc[stock_lt_df["sku"] == "SW-C9200L-24P", "stock"] = 1
    m_stock_lt = dict(master_data)
    m_stock_lt["DanhMuc_SanPham"] = stock_lt_df
    res_stock_lt = orch.run(case1_text, m_stock_lt, custom_discount=5.0)
    sw_warns_lt = [w for w in res_stock_lt["validation"]["inventory_warnings"] if "SW-C9200L-24P" in w]

    record(
        "3.3 Stock Boundary (stock==qty=2 vs stock==qty-1=1)",
        len(sw_warns_eq) == 0 and len(sw_warns_lt) >= 1,
        f"stock=2 warns={len(sw_warns_eq)} | stock=1 warns={len(sw_warns_lt)}"
    )

    # 3.4 Timeline boundary: Kiểm tra đúng ngưỡng req_days vs req_days - 1
    req_days = res1["validation"]["total_required_days"]
    tl_exact_rfq = case1_text.replace("15 ngày làm việc", f"{req_days} ngày làm việc")
    res_tl_ok = orch.run(tl_exact_rfq, master_data, custom_discount=5.0)
    tl_short_rfq = case1_text.replace("15 ngày làm việc", f"{req_days - 1} ngày làm việc")
    res_tl_conflict = orch.run(tl_short_rfq, master_data, custom_discount=5.0)

    record(
        f"3.4 Timeline Boundary ({req_days}d == req OK vs {req_days - 1}d < req CONFLICT)",
        res_tl_ok["validation"]["schedule_status"] == "OK" and res_tl_conflict["validation"]["schedule_status"] == "CONFLICT",
        f"{req_days}d->{res_tl_ok['validation']['schedule_status']} | {req_days - 1}d->{res_tl_conflict['validation']['schedule_status']}"
    )

    # 3.5 HITL Gate 4 & Gate 5 State Transitions (Case 3)
    case3_text = read_text("data/rfp_case_3_vuot_tham_quyen.txt")
    res3_wait = orch.run(case3_text, master_data, custom_discount=12.0, hitl_decision=None)
    res3_rej = orch.run(case3_text, master_data, custom_discount=12.0, hitl_decision={
        "decision": "REJECTED", "status_label": "TỪ CHỐI DUYỆT", "comment": "Biên lợi nhuận quá thấp", "decided_by": "Trưởng phòng"
    })
    res3_app = orch.run(case3_text, master_data, custom_discount=12.0, hitl_decision={
        "decision": "APPROVED", "status_label": "ĐÃ PHÊ DUYỆT", "comment": "Chấp thuận giữ khách VIP", "decided_by": "Trưởng phòng"
    })

    ok_hitl = (
        res3_wait["phase_status"] == "WAITING_HITL_APPROVAL" and res3_wait["gate_5_passed"] is False
        and res3_rej["phase_status"] == "FAILED_QUALITY_GATE" and res3_rej["gate_5_passed"] is False
        and res3_app["phase_status"] == "COMPLETED" and res3_app["gate_5_passed"] is True
    )
    record(
        "3.5 HITL Transition Boundaries (None -> WAITING | REJECTED -> FAIL | APPROVED -> COMPLETED)",
        ok_hitl,
        f"None->{res3_wait['phase_status']} | Rej->{res3_rej['phase_status']} | App->{res3_app['phase_status']}"
    )

    # =========================================================================
    # NHÓM 4: CUSTOM NEW DATASET TESTING (CHỨNG MINH KHÔNG HARDCODE)
    # =========================================================================
    custom_csv_path = os.path.join(ROOT_DIR, "tests/custom_dataset_test.csv")
    custom_df = pd.read_csv(custom_csv_path)
    custom_master = {
        "DanhMuc_SanPham": custom_df,
        "NangLuc_TrienKhai": master_data["NangLuc_TrienKhai"],
        "ChinhSach_ChuyenDuyet": master_data["ChinhSach_ChuyenDuyet"],
        "Lich_TrienKhai_KhaDung": master_data["Lich_TrienKhai_KhaDung"],
    }
    res_custom = orch.run(case1_text, custom_master, custom_discount=5.0)
    matched_sols = " ".join([c["matched_solution"] for c in res_custom["validation"]["compliance_checks"]])
    ok_custom = (
        res_custom["phase_status"] == "COMPLETED"
        and "HPE-ARUBA-6200F-24P" in matched_sols
        and "PA-440-NGFW" in matched_sols
        and "U6-PRO-WIFI6" in matched_sols
    )
    record(
        "4.1 New Dataset Compatibility (Zero Hardcoding SKU/Price)",
        ok_custom,
        f"Matched Solutions={matched_sols}, NetPrice={res_custom['quotation']['net_quoted_price']:,.0f} đ"
    )

    # Xuất báo cáo JSON
    passed_cnt = sum(1 for r in results if r["status"] == "PASS")
    total_cnt = len(results)
    report = {
        "total": total_cnt,
        "passed": passed_cnt,
        "failed": total_cnt - passed_cnt,
        "results": results
    }
    os.makedirs(os.path.join(ROOT_DIR, "logs"), exist_ok=True)
    with open(os.path.join(ROOT_DIR, "logs/test_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nSUMMARY: {passed_cnt}/{total_cnt} tests PASSED.")
    return 0 if passed_cnt == total_cnt else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
