"""
skills/skill_03_commercial_pricer.py
Custom Skill 3: Commercial Pricing & Policy Validation (Phase 04 - Steps 08, 09)
- Input: StructuredRFQ, SolutionMatchOutput, Discount %, PricingCalculatorTool, PolicyCheckerTool.
- Output: Bảng BoQ, Chỉ số tài chính, So khớp ngân sách, Thẩm định chính sách chuyển duyệt & Tờ trình.
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from tools.pricing_calculator_tool import PricingCalculatorTool
from tools.policy_checker_tool import PolicyCheckerTool
from skills.skill_02_solution_matcher import SolutionMatchOutput

class CommercialInput(BaseModel):
    structured_rfq: Dict[str, Any]
    solution_match: SolutionMatchOutput
    custom_discount_pct: Optional[float] = None

class CommercialOutput(BaseModel):
    boq_items: List[Dict[str, Any]]
    financials: Dict[str, Any]
    budget_comparison: Dict[str, Any]
    policy_evaluation: Dict[str, Any]
    escalation_report: str

class CommercialPricerSkill:
    SKILL_NAME = "CommercialPricerSkill"

    def run(
        self,
        inp: CommercialInput,
        pricing_tool: PricingCalculatorTool,
        policy_tool: PolicyCheckerTool
    ) -> CommercialOutput:
        rfq = inp.structured_rfq
        match = inp.solution_match

        # Xác định mức chiết khấu từ yêu cầu khách hàng hoặc cấu hình UI
        requested_disc = 0.0
        for cond in rfq.get("special_conditions", []):
            if "chiết khấu" in cond.lower():
                m = re.search(r"([\d\.]+)%", cond)
                if m:
                    requested_disc = float(m.group(1))
                    break

        applied_disc = (
            float(inp.custom_discount_pct)
            if inp.custom_discount_pct is not None
            else (requested_disc if requested_disc > 0 else 5.0)
        )

        # 1. Gọi PricingCalculatorTool
        calc_res = pricing_tool.calculate_boq_and_financials(
            matched_products=match.matched_products,
            matched_services=match.matched_services,
            discount_pct=applied_disc,
            customer_budget=rfq.get("budget")
        )

        budget_comp = calc_res["budget_comparison"]
        budget_exceeded = (budget_comp.get("is_within_budget") is False)

        # 2. Gọi PolicyCheckerTool
        policy_res = policy_tool.evaluate_policies(
            discount_pct=applied_disc,
            gross_margin_pct=calc_res["gross_margin_pct"],
            net_quoted_price=calc_res["net_quoted_price"],
            has_out_of_catalog=match.has_out_of_catalog,
            has_schedule_conflict=(match.schedule_status in ["CONFLICT", "UNCLEAR"]),
            special_conditions=rfq.get("special_conditions", []),
            budget_exceeded=budget_exceeded
        )

        # 3. Nếu vượt thẩm quyền -> Lập phiếu chuyển duyệt
        escalation_report = ""
        if policy_res["needs_special_approval"]:
            triggers_txt = "\n".join([f"- {t}" for t in policy_res["triggers"]])
            escalation_report = (
                f"PHIẾU CHUYỂN DUYỆT NGOẠI LỆ THƯƠNG MẠI & KỸ THUẬT\n"
                f"Khách hàng: {rfq.get('customer_name')} | Địa điểm: {rfq.get('location')}\n"
                f"Giá niêm yết: {calc_res['total_list_price']:,.0f} VNĐ | Chiết khấu: {applied_disc:.1f}% | "
                f"Giá chào Net: {calc_res['net_quoted_price']:,.0f} VNĐ\n"
                f"Giá vốn (COGS): {calc_res['total_cost_price']:,.0f} VNĐ | "
                f"Lợi nhuận gộp: {calc_res['gross_profit']:,.0f} VNĐ ({calc_res['gross_margin_pct']:.1f}%)\n\n"
                f"CẤP THẨM QUYỀN YÊU CẦU: {policy_res['approval_level']}\n"
                f"CÁC ĐIỀU KIỆN KÍCH HOẠT CHUYỂN DUYỆT:\n{triggers_txt}\n\n"
                f"Ngày lập phiếu: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )

        financials = {
            "hw_total_list": calc_res["hw_total_list"],
            "hw_total_cost": calc_res["hw_total_cost"],
            "srv_total_list": calc_res["srv_total_list"],
            "srv_total_cost": calc_res["srv_total_cost"],
            "total_list_price": calc_res["total_list_price"],
            "total_cost_price": calc_res["total_cost_price"],
            "applied_discount_pct": calc_res["applied_discount_pct"],
            "discount_amount": calc_res["discount_amount"],
            "net_quoted_price": calc_res["net_quoted_price"],
            "gross_profit": calc_res["gross_profit"],
            "gross_margin_pct": calc_res["gross_margin_pct"]
        }

        return CommercialOutput(
            boq_items=calc_res["boq_items"],
            financials=financials,
            budget_comparison=budget_comp,
            policy_evaluation=policy_res,
            escalation_report=escalation_report
        )

