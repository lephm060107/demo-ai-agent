"""
tools/pricing_calculator_tool.py
Công cụ tính toán giá bán, giá vốn, chiết khấu, biên lợi nhuận và so khớp ngân sách.
Ghi nhận bằng chứng gọi công cụ vào ToolTracer.
"""

import time
from typing import Dict, Any, List, Optional
from tools.tool_base import ToolTracer

class PricingCalculatorTool:
    TOOL_NAME = "PricingCalculatorTool"

    def __init__(self, tracer: Optional[ToolTracer] = None):
        self.tracer = tracer or ToolTracer()

    def calculate_boq_and_financials(
        self,
        matched_products: List[Dict[str, Any]],
        matched_services: List[Dict[str, Any]],
        discount_pct: float,
        customer_budget: Optional[float] = None
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        boq_items = []
        hw_list_total = 0.0
        hw_cost_total = 0.0
        srv_list_total = 0.0
        srv_cost_total = 0.0

        # 1. Tính dòng Phần cứng
        for idx, p in enumerate(matched_products, 1):
            qty = int(p["quantity"])
            u_list = float(p["list_price"])
            u_cost = float(p["cost_price"])
            l_total = qty * u_list
            c_total = qty * u_cost
            hw_list_total += l_total
            hw_cost_total += c_total
            boq_items.append({
                "stt": f"I.{idx}",
                "type": "Phần cứng",
                "name": p["name"],
                "sku": p["sku"],
                "specs": p["specs"],
                "unit": "Bộ/Cái",
                "quantity": qty,
                "unit_cost": u_cost,
                "unit_list_price": u_list,
                "total_cost": c_total,
                "total_list_price": l_total,
                "lead_time": f"{p['lead_time_days']} ngày"
            })

        # 2. Tính dòng Dịch vụ & Bảo trì
        for idx, s in enumerate(matched_services, 1):
            qty = int(s["quantity"])
            u_list = float(s["list_price"])
            u_cost = float(s["cost_price"])
            l_total = qty * u_list
            c_total = qty * u_cost
            srv_list_total += l_total
            srv_cost_total += c_total
            boq_items.append({
                "stt": f"II.{idx}",
                "type": "Dịch vụ & Bảo trì",
                "name": s["name"],
                "sku": s["service_id"],
                "specs": s.get("specs", f"Thời gian thi công: {s.get('min_days', 0)} ngày"),
                "unit": s.get("unit", "Gói"),
                "quantity": qty,
                "unit_cost": u_cost,
                "unit_list_price": u_list,
                "total_cost": c_total,
                "total_list_price": l_total,
                "lead_time": f"{s.get('min_days', 0)} ngày"
            })

        total_list_price = hw_list_total + srv_list_total
        total_cost_price = hw_cost_total + srv_cost_total
        discount_amount = round(total_list_price * (discount_pct / 100.0), 2)
        net_quoted_price = round(total_list_price - discount_amount, 2)
        gross_profit = round(net_quoted_price - total_cost_price, 2)
        gross_margin_pct = round((gross_profit / net_quoted_price * 100.0), 2) if net_quoted_price > 0 else 0.0

        # So khớp ngân sách
        budget_comparison = {"customer_budget": customer_budget, "is_within_budget": None}
        if customer_budget and customer_budget > 0:
            diff = customer_budget - net_quoted_price
            pct = (net_quoted_price / customer_budget) * 100.0
            is_within = net_quoted_price <= customer_budget
            budget_comparison = {
                "customer_budget": customer_budget,
                "net_quoted_price": net_quoted_price,
                "budget_diff": diff,
                "budget_pct": round(pct, 2),
                "is_within_budget": is_within,
                "comment": (
                    f"Giá chào ({net_quoted_price:,.0f} VNĐ) nằm TRONG ngân sách trần ({customer_budget:,.0f} VNĐ), tiết kiệm {diff:,.0f} VNĐ ({100-pct:.1f}%)."
                    if is_within else
                    f"CẢNH BÁO: Giá chào ({net_quoted_price:,.0f} VNĐ) VƯỢT ngân sách trần ({customer_budget:,.0f} VNĐ) thêm {abs(diff):,.0f} VNĐ ({pct-100:.1f}%)."
                )
            }
        else:
            budget_comparison["comment"] = "Khách hàng chưa công bố ngân sách trần."

        self.tracer.record(
            self.TOOL_NAME,
            "calculate_boq_and_financials",
            {"products_count": len(matched_products), "services_count": len(matched_services), "discount_pct": discount_pct},
            f"List: {total_list_price:,.0f}, Net: {net_quoted_price:,.0f}, Margin: {gross_margin_pct:.1f}%",
            len(boq_items),
            t0,
            "OK"
        )

        return {
            "boq_items": boq_items,
            "hw_total_list": hw_list_total,
            "hw_total_cost": hw_cost_total,
            "srv_total_list": srv_list_total,
            "srv_total_cost": srv_cost_total,
            "total_list_price": total_list_price,
            "total_cost_price": total_cost_price,
            "applied_discount_pct": discount_pct,
            "discount_amount": discount_amount,
            "net_quoted_price": net_quoted_price,
            "gross_profit": gross_profit,
            "gross_margin_pct": gross_margin_pct,
            "budget_comparison": budget_comparison
        }

