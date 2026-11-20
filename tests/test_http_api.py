"""
tests/test_http_api.py
Kiểm thử End-to-End qua HTTP trực tiếp vào localhost:8000 (FastAPI Server)
"""

import os
import sys
import requests

BASE_URL = "http://127.0.0.1:8000"
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    passed = 0
    total = 0

    def check(name: str, cond: bool, detail: str):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1
            print(f"[PASS] {name} -> {detail}")
        else:
            print(f"[FAIL] {name} -> {detail}")

    # 1. GET /
    r_home = requests.get(f"{BASE_URL}/", timeout=10)
    check("HTTP GET / (Unified NEXUS ANALYTICS UI)", r_home.status_code == 200 and "NEXUS ANALYTICS" in r_home.text, f"Status={r_home.status_code}")

    # 2. GET /api/rules & /api/master-data
    r_rules = requests.get(f"{BASE_URL}/api/rules", timeout=10)
    r_master = requests.get(f"{BASE_URL}/api/master-data", timeout=10)
    check(
        "HTTP GET /api/rules & /api/master-data",
        r_rules.status_code == 200 and "approval_policy_thresholds" in r_rules.json() and len(r_master.json().get("sheets", [])) == 4,
        f"Sheets={r_master.json().get('sheets')}"
    )

    # 3. Upload RFP file + Process Case 1
    rfp_path = os.path.join(ROOT_DIR, "data/rfp_case_1_day_du.txt")
    with open(rfp_path, "rb") as f:
        r_up = requests.post(f"{BASE_URL}/api/upload-rfp-file", files={"file": ("rfp_case_1_day_du.txt", f, "text/plain")}, timeout=10)
    up_json = r_up.json()
    check("HTTP POST /api/upload-rfp-file", r_up.status_code == 200 and up_json.get("success") is True, f"ToolCalls={len(up_json.get('tool_calls', []))}")

    r_p1 = requests.post(f"{BASE_URL}/api/process-rfp", json={"text": up_json["text"], "custom_discount": 5.0, "source_type": "TXT"}, timeout=15)
    p1 = r_p1.json()
    check(
        "HTTP POST /api/process-rfp (Case 1)",
        r_p1.status_code == 200 and p1.get("phase_status") == "COMPLETED" and p1.get("gate_5_passed") is True,
        f"Status={p1.get('phase_status')}, Net={p1.get('quotation', {}).get('net_quoted_price')}"
    )

    # 4. Download Excel & Word deliverables
    r_xls = requests.get(f"{BASE_URL}/api/download/boq-excel", timeout=10)
    r_doc = requests.get(f"{BASE_URL}/api/download/proposal-word", timeout=10)
    check(
        "HTTP GET /api/download/boq-excel & proposal-word",
        r_xls.status_code == 200 and len(r_xls.content) > 2000 and r_doc.status_code == 200 and len(r_doc.content) > 5000,
        f"Excel={len(r_xls.content)} bytes, Word={len(r_doc.content)} bytes"
    )

    # 5. Case 3 HITL flow over HTTP
    r_s3 = requests.get(f"{BASE_URL}/api/samples/3", timeout=10).json()
    r_p3 = requests.post(f"{BASE_URL}/api/process-rfp", json={"text": r_s3["text"], "custom_discount": 12.0}, timeout=15).json()
    r_hitl = requests.post(f"{BASE_URL}/api/manager-decision", json={"decision": "APPROVED", "comment": "Duyệt qua HTTP E2E"}, timeout=15).json()
    wf3_after = r_hitl.get("workflow_result", {})
    check(
        "HTTP HITL Flow (Case 3 -> WAITING -> APPROVED -> COMPLETED)",
        r_p3.get("phase_status") == "WAITING_HITL_APPROVAL" and wf3_after.get("phase_status") == "COMPLETED",
        f"Before={r_p3.get('phase_status')} -> After={wf3_after.get('phase_status')}"
    )

    # 6. Upload custom CSV dataset via HTTP & verify non-hardcoded matching, then restore default Excel
    custom_csv = os.path.join(ROOT_DIR, "tests/custom_dataset_test.csv")
    with open(custom_csv, "rb") as f:
        r_mc = requests.post(f"{BASE_URL}/api/upload-master-file", files={"file": ("custom_dataset_test.csv", f, "text/csv")}, timeout=10).json()
    r_p_cust = requests.post(f"{BASE_URL}/api/process-rfp", json={"text": up_json["text"], "custom_discount": 5.0}, timeout=15).json()
    sols = " ".join(c["matched_solution"] for c in r_p_cust["validation"]["compliance_checks"])
    check(
        "HTTP Upload Custom Dataset CSV -> Non-hardcoded SKUs",
        r_mc.get("success") is True and "HPE-ARUBA-6200F-24P" in sols,
        f"CustomMatched={sols}"
    )

    # Restore default master xlsx so localhost UI has clean default Thiên Minh dataset
    default_xlsx = os.path.join(ROOT_DIR, "data/thienminh_master_data.xlsx")
    with open(default_xlsx, "rb") as f:
        requests.post(f"{BASE_URL}/api/upload-master-file", files={"file": ("thienminh_master_data.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, timeout=10)

    # 7. GET /api/execution-logs
    r_logs = requests.get(f"{BASE_URL}/api/execution-logs", timeout=10).json()
    check(
        "HTTP GET /api/execution-logs",
        len(r_logs.get("logs", [])) >= 10 and len(r_logs.get("tool_calls", [])) >= 6,
        f"Logs={len(r_logs.get('logs', []))}, ToolCalls={len(r_logs.get('tool_calls', []))}"
    )

    print(f"\nHTTP E2E SUMMARY: {passed}/{total} PASSED")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

