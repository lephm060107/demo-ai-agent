"""
skills/skill_02_solution_matcher.py
Custom Skill 2: Solution Matching, Technical & Deployment Feasibility (Phase 03 - Steps 05, 06, 07)
- Input: StructuredRFQ, DataLookupTool, Matching & Deployment rules.
- Output: Matched products/services từ catalog thực tế, Compliance Matrix, Stock & Schedule Feasibility.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from tools.data_lookup_tool import DataLookupTool

class SolutionMatchInput(BaseModel):
    structured_rfq: Dict[str, Any]
    matching_rules: Dict[str, Any] = {}
    deployment_rules: Dict[str, Any] = {}

class SolutionMatchOutput(BaseModel):
    matched_products: List[Dict[str, Any]]
    unmatched_items: List[Dict[str, Any]]
    matched_services: List[Dict[str, Any]]
    compliance_checks: List[Dict[str, Any]]
    all_mandatory_met: bool
    inventory_warnings: List[str]
    schedule_status: str  # "OK" | "CONFLICT" | "UNCLEAR"
    schedule_warnings: List[str]
    has_out_of_catalog: bool
    max_hardware_lead_time: int
    total_min_service_days: int
    total_required_days: int
    team_info: Dict[str, Any]

class SolutionMatcherSkill:
    SKILL_NAME = "SolutionMatcherSkill"

    def run(self, inp: SolutionMatchInput, lookup_tool: DataLookupTool) -> SolutionMatchOutput:
        rfq = inp.structured_rfq
        m_rules = inp.matching_rules
        d_rules = inp.deployment_rules
        raw_lower = rfq.get("raw_text", "").lower()

        matched_products = []
        unmatched_items = []
        compliance_checks = []
        inventory_warnings = []

        # 1. Đối chiếu từng hạng mục thiết bị qua DataLookupTool (không hardcode SKU)
        for item in rfq.get("items_detected", []):
            cat = item["category"]
            qty = int(item["quantity"])
            req_feats = item.get("required_features", [])
            forb_feats = item.get("forbidden_features", [])

            res = lookup_tool.find_best_matching_product(
                category_query=cat,
                required_features=req_feats,
                forbidden_features=forb_feats,
                quantity_needed=qty
            )

            if res.get("found"):
                prod = res["product"]
                prod_entry = dict(prod)
                prod_entry["quantity"] = qty
                prod_entry["subtotal"] = prod["list_price"] * qty
                matched_products.append(prod_entry)

                compliance_checks.append({
                    "item": cat,
                    "required": ", ".join(req_feats) if req_feats else "Tiêu chuẩn",
                    "matched_solution": f"{prod['name']} ({prod['sku']})",
                    "status": "ĐÁP ỨNG",
                    "note": f"Khớp đặc tính kỹ thuật từ danh mục (Tồn kho: {prod['stock']}, Lead time: {prod['lead_time_days']} ngày)."
                })
            else:
                reason = res.get("reason", "Không tìm thấy sản phẩm phù hợp.")
                unmatched_items.append({
                    "category": cat,
                    "quantity": qty,
                    "required_features": req_feats,
                    "reason": reason
                })
                compliance_checks.append({
                    "item": cat,
                    "required": ", ".join(req_feats) if req_feats else "Tiêu chuẩn",
                    "matched_solution": "KHÔNG TÌM THẤY TRONG DANH MỤC",
                    "status": "KHÔNG ĐÁP ỨNG",
                    "note": reason
                })

        # 2. Kiểm tra yêu cầu ngoài danh mục (Out-of-catalog)
        has_out_of_catalog = False
        for cond in rfq.get("special_conditions", []):
            if any(k in cond.lower() for k in ["ngoài danh mục", "custom", "erp"]):
                has_out_of_catalog = True
                compliance_checks.append({
                    "item": "Yêu cầu tích hợp Custom",
                    "required": cond,
                    "matched_solution": "NGOÀI DANH MỤC CHUẨN",
                    "status": "CẦN THẨM ĐỊNH R&D",
                    "note": "Chưa có sẵn trong catalog. Cần Tech Lead & Quản lý phê duyệt ngoại lệ."
                })

        # 3. Kiểm tra Tồn kho & Lead time
        max_hw_lead_time = 0
        for p in matched_products:
            need = p["quantity"]
            stock = p["stock"]
            lead = p["lead_time_days"]
            if need > stock:
                shortage = need - stock
                max_hw_lead_time = max(max_hw_lead_time, lead)
                inventory_warnings.append(
                    f"{p['name']} ({p['sku']}): Thiếu {shortage} bộ (Cần: {need}, Tồn: {stock}). Cần {lead} ngày nhập hàng."
                )
            else:
                max_hw_lead_time = max(max_hw_lead_time, lead)

        # 4. Tra cứu Dịch vụ triển khai & Bảo trì từ dữ liệu thực
        matched_services = []
        # Khảo sát
        survey_srvs = lookup_tool.lookup_services(["khảo sát"])
        if survey_srvs:
            s = survey_srvs[0]
            matched_services.append({
                "service_id": s["service_id"], "name": s["name"], "unit": s["unit"],
                "quantity": 1, "cost_price": s["cost"], "list_price": s["price"],
                "min_days": s["min_days"], "specs": f"Năng lực: {s['capacity']}"
            })

        # Kéo cáp theo số node trích xuất từ văn bản hoặc config mặc định
        if any(k in raw_lower for k in ["kéo cáp", "thi công", "bấm đầu", "điểm mạng", "node"]):
            cable_srvs = lookup_tool.lookup_services(["kéo cáp"])
            if cable_srvs:
                s = cable_srvs[0]
                nodes = rfq.get("cable_nodes")
                if not nodes:
                    nodes = int(m_rules.get("default_nodes_when_unspecified", 50))
                matched_services.append({
                    "service_id": s["service_id"], "name": f"{s['name']} ({nodes} nodes)", "unit": s["unit"],
                    "quantity": nodes, "cost_price": s["cost"], "list_price": s["price"],
                    "min_days": s["min_days"], "specs": f"Năng lực: {s['capacity']}"
                })

        # Cấu hình Firewall / Switch / VLAN
        if any(k in raw_lower for k in ["cấu hình", "vlan", "qos", "vpn", "ha"]):
            cfg_srvs = lookup_tool.lookup_services(["firewall"]) or lookup_tool.lookup_services(["cấu hình"])
            if cfg_srvs:
                s = cfg_srvs[0]
                matched_services.append({
                    "service_id": s["service_id"], "name": s["name"], "unit": s["unit"],
                    "quantity": 1, "cost_price": s["cost"], "list_price": s["price"],
                    "min_days": s["min_days"], "specs": f"Năng lực: {s['capacity']}"
                })

        # Gói bảo trì SLA từ Danh mục sản phẩm (không hardcode SKU)
        sla_type = rfq.get("sla_type", "8x5")
        sla_res = lookup_tool.find_best_matching_product(
            category_query="Dịch vụ bảo trì",
            required_features=["24x7"] if "24x7" in sla_type else ["8x5"],
            forbidden_features=[],
            quantity_needed=1
        )
        if sla_res.get("found"):
            sp = sla_res["product"]
            matched_services.append({
                "service_id": sp["sku"], "name": sp["name"], "unit": "Năm (12 tháng)",
                "quantity": 1, "cost_price": sp["cost_price"], "list_price": sp["list_price"],
                "min_days": sp["lead_time_days"], "specs": sp["specs"]
            })

        # 5. Kiểm tra Năng lực Đội kỹ sư & Lịch triển khai
        total_min_service_days = sum(int(s["min_days"]) for s in matched_services)
        buffer_days = int(d_rules.get("rush_schedule_buffer_days", 0))
        total_required_days = max_hw_lead_time + total_min_service_days + buffer_days

        max_concurrent = int(d_rules.get("max_concurrent_projects_per_team", 2))
        team_info = lookup_tool.lookup_deployment_teams(rfq.get("location", ""), max_concurrent=max_concurrent)

        schedule_warnings = []
        schedule_status = "OK"
        cust_days = rfq.get("timeline_days")

        if team_info["status"] == "UNCLEAR":
            schedule_status = "UNCLEAR"
            schedule_warnings.append(team_info["reason"])
        elif team_info["status"] == "OVERLOADED":
            schedule_status = "CONFLICT"
            schedule_warnings.append(f"Các đội kỹ thuật khu vực {team_info.get('target_region')} đều đang quá tải (>= {max_concurrent} dự án).")

        if cust_days is not None and cust_days < total_required_days:
            schedule_status = "CONFLICT"
            schedule_warnings.append(
                f"XUNG ĐỘT TIẾN ĐỘ: Khách hàng yêu cầu {cust_days} ngày, nhưng tổng thời gian tối thiểu là {total_required_days} ngày "
                f"(Lead time thiết bị: {max_hw_lead_time} ngày + Thi công: {total_min_service_days} ngày)."
            )

        all_mandatory_met = (len(unmatched_items) == 0)

        return SolutionMatchOutput(
            matched_products=matched_products,
            unmatched_items=unmatched_items,
            matched_services=matched_services,
            compliance_checks=compliance_checks,
            all_mandatory_met=all_mandatory_met,
            inventory_warnings=inventory_warnings,
            schedule_status=schedule_status,
            schedule_warnings=schedule_warnings,
            has_out_of_catalog=has_out_of_catalog,
            max_hardware_lead_time=max_hw_lead_time,
            total_min_service_days=total_min_service_days,
            total_required_days=total_required_days,
            team_info=team_info
        )

