"""
tools/policy_checker_tool.py
Công cụ kiểm tra chính sách chiết khấu và phân quyền phê duyệt động.
Đọc ngưỡng từ sheet ChinhSach_ChuyenDuyet (nếu có) kết hợp config/business_rules.json.
"""

import re
import time
import pandas as pd
from typing import Dict, Any, List, Optional
from tools.tool_base import ToolTracer

class PolicyCheckerTool:
    TOOL_NAME = "PolicyCheckerTool"

    def __init__(self, policies_df: Optional[pd.DataFrame], business_rules: Dict[str, Any], tracer: Optional[ToolTracer] = None):
        self.policies_df = policies_df
        self.rules = business_rules
        self.tracer = tracer or ToolTracer()

    def _extract_effective_thresholds(self) -> Dict[str, Any]:
        """Kết hợp cấu hình mặc định từ JSON và ghi đè nếu bảng ChinhSach_ChuyenDuyet có ngưỡng số học rõ ràng."""
        thresholds = dict(self.rules.get("approval_policy_thresholds", {}))
        
        if self.policies_df is not None and not self.policies_df.empty:
            for _, row in self.policies_df.iterrows():
                r_name = str(row.get("rule_name", "")).lower()
                rep_lim = str(row.get("sales_rep_limit", ""))
                mgr_lim = str(row.get("manager_limit", ""))
                
                if "chiết khấu" in r_name:
                    m_rep = re.search(r"([\d\.]+)\s*%", rep_lim)
                    if m_rep:
                        thresholds["sales_rep_max_discount_pct"] = float(m_rep.group(1))
                    m_mgr = re.findall(r"([\d\.]+)\s*%", mgr_lim)
                    if m_mgr:
                        thresholds["manager_max_discount_pct"] = float(m_mgr[-1])
                elif "biên lợi nhuận" in r_name or "margin" in r_name:
                    m_rep = re.search(r"([\d\.]+)\s*%", rep_lim)
                    if m_rep:
                        thresholds["sales_rep_min_gross_margin_pct"] = float(m_rep.group(1))
                    m_mgr = re.findall(r"([\d\.]+)\s*%", mgr_lim)
                    if m_mgr:
                        thresholds["manager_min_gross_margin_pct"] = float(m_mgr[0])

        return thresholds

    def evaluate_policies(
        self,
        discount_pct: float,
        gross_margin_pct: float,
        net_quoted_price: float,
        has_out_of_catalog: bool,
        has_schedule_conflict: bool,
        special_conditions: List[str],
        budget_exceeded: bool = False
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        th = self._extract_effective_thresholds()

        rep_max_disc = float(th.get("sales_rep_max_discount_pct", 5.0))
        mgr_max_disc = float(th.get("manager_max_discount_pct", 15.0))
        rep_min_margin = float(th.get("sales_rep_min_gross_margin_pct", 25.0))
        mgr_min_margin = float(th.get("manager_min_gross_margin_pct", 18.0))
        large_deal_vnd = float(th.get("large_deal_threshold_vnd", 300_000_000))

        triggers = []
        needs_manager = False
        needs_director = False

        # 1. Kiểm tra Chiết khấu (Boundary: <= rep_max_disc ok, > rep_max_disc triggers)
        if discount_pct > mgr_max_disc:
            needs_director = True
            needs_manager = True
            triggers.append(f"Chiết khấu {discount_pct:.2f}% > ngưỡng Trưởng phòng ({mgr_max_disc}%). Bắt buộc Giám đốc phê duyệt.")
        elif discount_pct > rep_max_disc:
            needs_manager = True
            triggers.append(f"Chiết khấu {discount_pct:.2f}% > ngưỡng NVKD ({rep_max_disc}%). Cần Trưởng phòng duyệt.")

        # 2. Kiểm tra Biên lợi nhuận (Boundary: >= rep_min_margin ok, < rep_min_margin triggers)
        if gross_margin_pct < mgr_min_margin:
            needs_director = True
            needs_manager = True
            triggers.append(f"Biên lợi nhuận {gross_margin_pct:.2f}% < ngưỡng an toàn tối thiểu ({mgr_min_margin}%). Bắt buộc Giám đốc phê duyệt ngoại lệ.")
        elif gross_margin_pct < rep_min_margin:
            needs_manager = True
            triggers.append(f"Biên lợi nhuận {gross_margin_pct:.2f}% < ngưỡng chuẩn NVKD ({rep_min_margin}%). Cần Trưởng phòng duyệt.")

        # 3. Ngoài danh mục
        if has_out_of_catalog and th.get("require_approval_for_out_of_catalog", True):
            needs_manager = True
            triggers.append("Có yêu cầu ngoài danh mục chuẩn (Custom/Out-of-catalog). Bắt buộc Trưởng phòng & Tech Lead duyệt.")

        # 4. Tiến độ gấp
        if has_schedule_conflict and th.get("require_approval_for_rush_schedule", True):
            needs_manager = True
            triggers.append("Tiến độ khách hàng yêu cầu gấp hơn năng lực/lead-time chuẩn. Cần Trưởng phòng & Vận hành duyệt.")

        # 5. Giá trị dự án lớn
        if net_quoted_price > large_deal_vnd:
            needs_manager = True
            triggers.append(f"Giá trị dự án ({net_quoted_price:,.0f} VNĐ) > hạn mức NVKD ({large_deal_vnd:,.0f} VNĐ). Cần Trưởng phòng ký duyệt.")

        # 6. Điều khoản thanh toán bất lợi
        if th.get("require_approval_for_deferred_payment", True):
            for cond in special_conditions:
                if any(k in cond.lower() for k in ["trả chậm", "tạm ứng 0%", "công nợ"]):
                    needs_manager = True
                    triggers.append(f"Điều khoản thanh toán ngoại lệ: {cond}. Cần Trưởng phòng & Kế toán trưởng duyệt.")

        # 7. Vượt ngân sách
        if budget_exceeded and th.get("require_approval_for_budget_exceeded", False):
            needs_manager = True
            triggers.append("Giá chào bán vượt trần ngân sách công bố của khách hàng.")

        if needs_director:
            level = "GIÁM ĐỐC ĐIỀU HÀNH PHÊ DUYỆT (Ngoại lệ cấp cao)"
        elif needs_manager:
            level = "TRƯỞNG PHÒNG KINH DOANH DUYỆT"
        else:
            level = "NVKD ĐƯỢC PHÉP BAN HÀNH (Trong hạn mức)"

        self.tracer.record(
            self.TOOL_NAME,
            "evaluate_policies",
            {"discount_pct": discount_pct, "gross_margin_pct": gross_margin_pct, "net_quoted_price": net_quoted_price},
            f"NeedsApproval: {needs_manager or needs_director}, Level: {level}, Triggers: {len(triggers)}",
            len(self.policies_df) if self.policies_df is not None else 0,
            t0,
            "OK"
        )

        return {
            "needs_special_approval": needs_manager or needs_director,
            "needs_director": needs_director,
            "approval_level": level,
            "triggers": triggers,
            "applied_thresholds": th
        }

