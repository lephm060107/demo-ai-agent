"""
skills/skill_01_intake_structurer.py
Custom Skill 1: Intake & Intelligence Structurer (Phase 01 & Phase 02 - Steps 01, 02, 03, 04)
- Input: Văn bản thô RFP, loại nguồn, cấu hình tiêu chuẩn bắt buộc.
- Output: StructuredRFQ, Checklist đầy đủ, Danh sách thiếu/mâu thuẫn, Thư làm rõ.
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class IntakeInput(BaseModel):
    raw_text: str
    source_type: str = "TEXT"
    completeness_rules: Dict[str, bool] = {}

class IntakeOutput(BaseModel):
    structured_rfq: Dict[str, Any]
    checklist: List[Dict[str, Any]]
    missing_items: List[str]
    inconsistencies: List[str]
    is_complete_and_consistent: bool
    status_label: str
    clarification_letter: str

class IntakeStructurerSkill:
    SKILL_NAME = "IntakeStructurerSkill"

    def run(self, inp: IntakeInput) -> IntakeOutput:
        text = inp.raw_text.strip()
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        raw_lower = text.lower()
        rules = inp.completeness_rules

        # 1. Trích xuất Khách hàng
        customer_name = "Chưa định danh"
        for line in lines:
            if re.search(r"(bên yêu cầu|khách hàng|đơn vị yêu cầu|công ty)\s*[:\-]\s*", line, re.I):
                val = re.sub(r"^.*(bên yêu cầu|khách hàng|đơn vị yêu cầu|công ty)\s*[:\-]\s*", "", line, flags=re.I).strip()
                if val and not any(k in val.lower() for k in ["thiên minh", "phòng kinh doanh", "bộ phận"]):
                    customer_name = val
                    break
            elif any(k in line.lower() for k in ["tập đoàn", "công ty cổ phần", "công ty tnhh"]) and "thiên minh" not in line.lower():
                customer_name = line.strip("- :")
                break

        # 2. Địa điểm triển khai
        location = "Chưa xác định"
        for line in lines:
            if re.search(r"(địa chỉ triển khai|địa điểm triển khai|địa chỉ|địa điểm|khu vực triển khai|nơi triển khai)\s*[:\-]\s*", line, re.I):
                val = re.sub(r"^.*(địa chỉ triển khai|địa điểm triển khai|địa chỉ|địa điểm|khu vực triển khai|nơi triển khai)\s*[:\-]\s*", "", line, flags=re.I).strip()
                if len(val) > 3:
                    location = val
                    break

        # 3. Thời hạn nộp hồ sơ
        submission_deadline = "Không ghi rõ"
        sub_m = re.search(r"(thời hạn nộp|hạn nộp|nộp hồ sơ trước|chào giá trước)\s*[:\-]?\s*([^\.\n]+)", text, re.I)
        if sub_m:
            submission_deadline = sub_m.group(2).strip()

        # 4. Ngân sách trần (ưu tiên dòng chứa từ khóa ngân sách/dự toán và bắt buộc đi kèm đơn vị tiền tệ)
        budget = None
        budget_raw = "Chưa công bố"
        for line in lines:
            if re.search(r"(ngân sách|dự toán|giá trần|kinh phí|chi phí dự kiến)", line, re.I):
                b_m = re.search(r"([\d\.,]+)\s*(triệu|tỷ|tr|vnđ|vnd|đồng|đ)\b", line, re.I)
                if b_m:
                    num_str = b_m.group(1).replace(".", "").replace(",", "")
                    unit = b_m.group(2).lower()
                    try:
                        val = float(num_str)
                        if "tỷ" in unit:
                            val *= 1_000_000_000
                        elif "triệu" in unit or unit == "tr" or val < 10000:
                            val *= 1_000_000
                        budget = int(val)
                        budget_raw = f"{budget:,.0f} VNĐ"
                        break
                    except Exception:
                        pass

        # 5. Tiến độ (Timeline) & Số ngày
        timeline_start = None
        timeline_end = None
        timeline_days = None
        start_m = re.search(r"(bắt đầu|khởi công|triển khai từ)[^\d\n]*(\d{1,2}[/-]\d{1,2}[/-]\d{4})", text, re.I)
        if start_m:
            timeline_start = start_m.group(2)
        end_m = re.search(r"(hoàn thành|nghiệm thu|bàn giao trước|xong trước)[^\d\n]*(\d{1,2}[/-]\d{1,2}[/-]\d{4})", text, re.I)
        if end_m:
            timeline_end = end_m.group(2)
        days_m = re.search(r"(\d+)\s*ngày\s*(làm việc|triển khai|kể từ)", text, re.I)
        if days_m:
            timeline_days = int(days_m.group(1))
        elif timeline_start and timeline_end:
            try:
                d1 = datetime.strptime(timeline_start.replace("-", "/"), "%d/%m/%Y")
                d2 = datetime.strptime(timeline_end.replace("-", "/"), "%d/%m/%Y")
                timeline_days = (d2 - d1).days
            except Exception:
                pass

        # 6. SLA & Bảo trì
        sla_type = "Chưa nêu rõ"
        if "24x7" in text or "24/7" in text:
            sla_type = "24x7"
        elif "8x5" in text or "8/5" in text or "hành chính" in raw_lower:
            sla_type = "8x5"

        # 7. Trích xuất số lượng nhân sự / điểm mạng (nodes) động từ văn bản
        cable_nodes = None
        node_m = re.search(r"(\d+)\s*(điểm mạng|node|nút mạng)", text, re.I)
        if node_m:
            cable_nodes = int(node_m.group(1))
        else:
            user_m = re.search(r"(\d+)\s*(nhân sự|người dùng|user|nhân viên)", text, re.I)
            if user_m:
                cable_nodes = int(user_m.group(1))

        # 8. Trích xuất hạng mục & điều kiện bắt buộc (required_features / forbidden_features)
        items_detected = []

        if "switch" in raw_lower or "chuyển mạch" in raw_lower:
            sw_m = re.search(r"(\d+)\s*(?:bộ|cái|chiếc)?\s*(?:switch|thiết bị chuyển mạch)", text, re.I)
            sw_qty = int(sw_m.group(1)) if sw_m else 0
            req_feats = []
            forb_feats = []
            if "poe" in raw_lower:
                req_feats.append("PoE")
                forb_feats.append("Non-PoE")
            if "layer 3" in raw_lower or "l3" in raw_lower or "định tuyến" in raw_lower:
                req_feats.append("Layer 3")
            if re.search(r"24\s*cổng\s*hoặc\s*48\s*cổng|24\s*port\s*or\s*48\s*port", raw_lower):
                req_feats.append("24")
            elif re.search(r"\b48\s*(?:cổng|port)\b", raw_lower):
                req_feats.append("48")
            elif re.search(r"\b24\s*(?:cổng|port)\b", raw_lower):
                req_feats.append("24")
            items_detected.append({
                "category": "Switch",
                "quantity": sw_qty,
                "required_features": req_feats,
                "forbidden_features": forb_feats
            })

        if "firewall" in raw_lower or "tường lửa" in raw_lower:
            fw_m = re.search(r"(\d+)\s*(?:bộ|cái|chiếc)?\s*(?:firewall|tường lửa)", text, re.I)
            if fw_m:
                fw_qty = int(fw_m.group(1))
            elif "tường lửa thế hệ mới" in raw_lower or "ngfw" in raw_lower:
                fw_qty = 1
            else:
                fw_qty = 0
            req_feats = []
            if "ha" in raw_lower or "high availability" in raw_lower or "dự phòng" in raw_lower:
                req_feats.append("HA")
            if "vpn" in raw_lower:
                req_feats.append("VPN")
            if "1gbps" in raw_lower or "1.6gbps" in raw_lower or "100f" in raw_lower:
                req_feats.append("1.6Gbps")
            items_detected.append({
                "category": "Firewall",
                "quantity": fw_qty,
                "required_features": req_feats,
                "forbidden_features": []
            })

        if "access point" in raw_lower or re.search(r"\bap\b", raw_lower) or "wifi" in raw_lower or "wi-fi" in raw_lower:
            ap_m = re.search(r"(\d+)\s*(?:bộ|cái|chiếc)?\s*(?:access point|ap|bộ phát wifi|wifi)", text, re.I)
            ap_qty = int(ap_m.group(1)) if ap_m else 0
            req_feats = []
            if "wifi 6" in raw_lower or "wi-fi 6" in raw_lower or "802.11ax" in raw_lower:
                req_feats.append("Wi-Fi 6")
            if "ngoài trời" in raw_lower or "outdoor" in raw_lower or "ip67" in raw_lower:
                req_feats.append("IP67")
            items_detected.append({
                "category": "Access Point",
                "quantity": ap_qty,
                "required_features": req_feats,
                "forbidden_features": []
            })

        if "rack" in raw_lower or "tủ mạng" in raw_lower:
            rk_m = re.search(r"(\d+)\s*(?:bộ|cái|tủ)?\s*(?:tủ mạng|tủ rack|rack)", text, re.I)
            rk_qty = int(rk_m.group(1)) if rk_m else 1
            items_detected.append({
                "category": "Tủ mạng",
                "quantity": rk_qty,
                "required_features": ["27U"] if "27u" in raw_lower else [],
                "forbidden_features": []
            })

        if "cáp" in raw_lower or "cat6" in raw_lower:
            cb_m = re.search(r"(\d+)\s*(?:thùng|cuộn)?\s*cáp", text, re.I)
            cb_qty = int(cb_m.group(1)) if cb_m else 0
            items_detected.append({
                "category": "Phụ kiện cáp",
                "quantity": cb_qty,
                "required_features": ["Cat6"] if "cat6" in raw_lower else [],
                "forbidden_features": []
            })

        if "ups" in raw_lower or "lưu điện" in raw_lower:
            up_m = re.search(r"(\d+)\s*(?:bộ|cái)?\s*(?:ups|bộ lưu điện|lưu điện)", text, re.I)
            up_qty = int(up_m.group(1)) if up_m else 1
            items_detected.append({
                "category": "Nguồn dự phòng",
                "quantity": up_qty,
                "required_features": ["3000VA"] if ("3000va" in raw_lower or "3kva" in raw_lower) else [],
                "forbidden_features": []
            })

        # 9. Điều kiện đặc biệt
        special_conditions = []
        disc_m = re.search(r"chiết khấu[^\d\n]*([\d\.]+)%", text, re.I)
        if disc_m:
            special_conditions.append(f"Yêu cầu chiết khấu thương mại: {disc_m.group(1)}%")
        if any(k in raw_lower for k in ["ngoài danh mục", "tích hợp erp", "custom api", "phần mềm ngoài"]):
            special_conditions.append("Yêu cầu tích hợp ngoài danh mục tiêu chuẩn (Custom requirement)")
        if any(k in raw_lower for k in ["trả chậm", "tạm ứng 0%", "sau 45 ngày", "sau 30 ngày"]):
            special_conditions.append("Điều khoản thanh toán bất lợi (Trả chậm / Tạm ứng 0%)")

        # 10. Kiểm tra tính đầy đủ & nhất quán (Step 04 Validation)
        checklist = []
        missing_items = []
        inconsistencies = []

        # Check A: Khách hàng
        has_cust = customer_name != "Chưa định danh"
        if has_cust:
            checklist.append({"criterion": "Thông tin định danh khách hàng", "status": "ĐẠT", "detail": f"{customer_name} | {location}"})
        else:
            checklist.append({"criterion": "Thông tin định danh khách hàng", "status": "THIẾU", "detail": "Chưa xác định tên công ty khách hàng."})
            if rules.get("require_customer_name", True):
                missing_items.append("Tên đơn vị yêu cầu & Thông tin liên hệ.")

        # Check B: Danh mục & Số lượng
        is_vague = any(v in raw_lower for v in ["vài cái", "cần một con", "linh tinh"])
        items_missing_qty = [it["category"] for it in items_detected if it["quantity"] <= 0]
        if items_detected and not items_missing_qty and not is_vague:
            summary = ", ".join([f"{it['quantity']}x {it['category']}" for it in items_detected])
            checklist.append({"criterion": "Danh mục hạng mục & Số lượng cụ thể", "status": "ĐẠT", "detail": summary})
        else:
            detail_msg = f"Thiếu số lượng cụ thể cho: {', '.join(items_missing_qty)}" if items_missing_qty else "Yêu cầu chung chung, chưa có bảng kê số lượng thiết bị."
            checklist.append({"criterion": "Danh mục hạng mục & Số lượng cụ thể", "status": "THIẾU", "detail": detail_msg})
            if rules.get("require_items_with_quantity", True):
                missing_items.append(f"Số lượng chi tiết từng thiết bị ({', '.join(items_missing_qty) if items_missing_qty else 'Switch, Firewall, Access Point'}).")

        # Check C: Đặc tính kỹ thuật bắt buộc
        has_specs = any(len(it["required_features"]) > 0 for it in items_detected)
        if has_specs and not is_vague:
            all_feats = [f"{it['category']}: {it['required_features']}" for it in items_detected if it["required_features"]]
            checklist.append({"criterion": "Đặc tính kỹ thuật bắt buộc", "status": "ĐẠT", "detail": "; ".join(all_feats)})
        else:
            checklist.append({"criterion": "Đặc tính kỹ thuật bắt buộc", "status": "THIẾU", "detail": "Chưa rõ tiêu chuẩn PoE, Layer 3, chuẩn Wi-Fi, hoặc tính năng bảo mật NGFW."})
            if rules.get("require_mandatory_tech_specs", True):
                missing_items.append("Thông số kỹ thuật bắt buộc (PoE, số cổng, throughput Firewall, chuẩn Wi-Fi 6).")

        # Check D: Tiến độ (Timeline) & Tính nhất quán ngày tháng
        if timeline_days is not None and timeline_days < 0:
            inconsistencies.append(f"MÂU THUẪN LỊCH TRÌNH: Ngày bắt đầu ({timeline_start}) đang nằm SAU ngày hoàn thành ({timeline_end}).")
            checklist.append({"criterion": "Lịch trình & Thời hạn hoàn thành", "status": "MÂU THUẪN", "detail": inconsistencies[-1]})
        elif timeline_start or timeline_end or timeline_days:
            checklist.append({"criterion": "Lịch trình & Thời hạn hoàn thành", "status": "ĐẠT", "detail": f"Từ {timeline_start or 'N/A'} đến {timeline_end or 'N/A'} ({timeline_days or 'N/A'} ngày)"})
        else:
            checklist.append({"criterion": "Lịch trình & Thời hạn hoàn thành", "status": "THIẾU", "detail": "Không có ngày bắt đầu hoặc hạn chót bàn giao."})
            if rules.get("require_timeline", True):
                missing_items.append("Kế hoạch tiến độ & Hạn chót nghiệm thu.")

        # Check E: SLA Bảo trì
        if sla_type != "Chưa nêu rõ":
            checklist.append({"criterion": "Yêu cầu bảo trì & SLA", "status": "ĐẠT", "detail": f"Gói hỗ trợ {sla_type}"})
        else:
            checklist.append({"criterion": "Yêu cầu bảo trì & SLA", "status": "THIẾU", "detail": "Chưa xác định gói bảo trì (8x5 hay 24x7)."})
            if rules.get("require_sla", True):
                missing_items.append("Cam kết dịch vụ bảo trì SLA (8x5 hay 24x7).")

        # Check F: Mâu thuẫn quy mô (Inconsistency check: e.g. Firewall chạy cụm HA nhưng chỉ đặt 1 con Firewall)
        if "chạy cụm ha" in raw_lower or "active - standby" in raw_lower or "active-passive" in raw_lower:
            for it in items_detected:
                if it["category"] == "Firewall" and it["quantity"] == 1:
                    inconsistencies.append("MÂU THUẪN KỸ THUẬT: Khách yêu cầu chạy cụm Firewall High Availability (Active-Standby) nhưng chỉ đặt số lượng 01 thiết bị (Cần tối thiểu 02 thiết bị).")

        is_ok = (len(missing_items) == 0) and (len(inconsistencies) == 0)
        clarification_letter = ""
        if not is_ok:
            issues = missing_items + inconsistencies
            q_lines = "\n".join([f"{i}. {iss}" for i, iss in enumerate(issues, 1)])
            clarification_letter = (
                f"KÍNH GỬI: {customer_name.upper()}\n"
                f"THƯ YÊU CẦU LÀM RÕ VÀ XÁC MINH THÔNG TIN HỒ SƠ CHÀO GIÁ\n\n"
                f"Để đảm bảo phương án kỹ thuật đáp ứng đầy đủ điều kiện bắt buộc và đúng tiến độ, "
                f"Công ty Thiên Minh kính đề nghị Quý đơn vị làm rõ các nội dung chưa đầy đủ/mâu thuẫn sau:\n\n"
                f"{q_lines}\n\n"
                f"Trân trọng cảm ơn!\nPhòng Kinh Doanh B2B - Công ty Thiết bị Mạng Thiên Minh."
            )

        structured_rfq = {
            "customer_name": customer_name,
            "location": location,
            "submission_deadline": submission_deadline,
            "budget": budget,
            "budget_raw": budget_raw,
            "timeline_start": timeline_start,
            "timeline_end": timeline_end,
            "timeline_days": timeline_days,
            "sla_type": sla_type,
            "cable_nodes": cable_nodes,
            "items_detected": items_detected,
            "special_conditions": special_conditions,
            "source_type": inp.source_type,
            "raw_text": text
        }

        return IntakeOutput(
            structured_rfq=structured_rfq,
            checklist=checklist,
            missing_items=missing_items,
            inconsistencies=inconsistencies,
            is_complete_and_consistent=is_ok,
            status_label="ĐỦ THÔNG TIN & NHẤT QUÁN" if is_ok else "THIẾU THÔNG TIN / MÂU THUẪN",
            clarification_letter=clarification_letter
        )
