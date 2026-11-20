"""
tools/data_lookup_tool.py
Công cụ tra cứu động dữ liệu doanh nghiệp (Sản phẩm, Tồn kho, Dịch vụ triển khai, Lịch kỹ sư).
HOÀN TOÀN KHÔNG HARDCODE SKU hay giá. Tự động chấm điểm đặc tính kỹ thuật từ DataFrame đang nạp.
"""

import time
import pandas as pd
from typing import Dict, Any, List, Optional
from tools.tool_base import ToolTracer

class DataLookupTool:
    TOOL_NAME = "DataLookupTool"

    def __init__(self, master_data: Dict[str, pd.DataFrame], tracer: Optional[ToolTracer] = None):
        self.master_data = master_data
        self.tracer = tracer or ToolTracer()

    def _get_df(self, preferred_name: str, fallback_index: int = 0) -> pd.DataFrame:
        if preferred_name in self.master_data and isinstance(self.master_data[preferred_name], pd.DataFrame):
            return self.master_data[preferred_name]
        keys = list(self.master_data.keys())
        if keys and fallback_index < len(keys):
            return self.master_data[keys[fallback_index]]
        return pd.DataFrame()

    def find_best_matching_product(
        self,
        category_query: str,
        required_features: List[str],
        forbidden_features: List[str],
        quantity_needed: int
    ) -> Dict[str, Any]:
        """
        Tra cứu và chấm điểm sản phẩm trong bảng DanhMuc_SanPham dựa trên thuộc tính kỹ thuật bắt buộc.
        """
        t0 = time.perf_counter()
        df = self._get_df("DanhMuc_SanPham", 0)
        if df.empty:
            self.tracer.record(self.TOOL_NAME, "find_best_matching_product",
                               {"category": category_query}, "Catalog is empty", 0, t0, "ERROR")
            return {"found": False, "reason": "Danh mục sản phẩm rỗng."}

        # Chuẩn hóa tên cột để hỗ trợ bộ dữ liệu mới có thể viết hoa/thường khác nhau
        col_map = {c.lower().strip(): c for c in df.columns}
        cat_col = col_map.get("category", "category")
        specs_col = col_map.get("specs", "specs")
        name_col = col_map.get("name", "name")
        sku_col = col_map.get("sku", "sku")
        stock_col = col_map.get("stock", "stock")
        lead_col = col_map.get("lead_time_days", "lead_time_days")
        cost_col = col_map.get("cost_price", "cost_price")
        price_col = col_map.get("list_price", "list_price")

        # Lọc theo nhóm (category) hoặc tên sản phẩm
        cat_lower = category_query.lower()
        candidates = df[
            df[cat_col].astype(str).str.lower().str.contains(cat_lower, na=False) |
            df[name_col].astype(str).str.lower().str.contains(cat_lower, na=False)
        ]

        if candidates.empty:
            self.tracer.record(
                self.TOOL_NAME, "find_best_matching_product",
                {"category": category_query, "required": required_features},
                f"No product found in category '{category_query}'",
                len(df), t0, "OK"
            )
            return {"found": False, "reason": f"Không có sản phẩm thuộc nhóm '{category_query}' trong danh mục."}

        best_candidate = None
        best_score = -1
        disqualified_reasons = []

        for _, row in candidates.iterrows():
            specs_text = f"{row.get(name_col, '')} {row.get(specs_col, '')}".lower()
            
            # 1. Kiểm tra điều kiện loại trừ (ví dụ: khách cần PoE nhưng thiết bị ghi 'non-poe')
            violated_forbidden = False
            for fb in forbidden_features:
                if fb.lower() in specs_text:
                    disqualified_reasons.append(f"{row.get(sku_col)}: Loại vì chứa '{fb}'")
                    violated_forbidden = True
                    break
            if violated_forbidden:
                continue

            # 2. Kiểm tra tất cả yêu cầu bắt buộc (mandatory constraints)
            matched_reqs = 0
            missing_reqs = []
            for req in required_features:
                req_l = req.lower()
                # Hỗ trợ tìm kiếm linh hoạt các từ đồng nghĩa cơ bản trong ngành mạng
                if req_l == "poe":
                    ok = ("poe" in specs_text) and ("non-poe" not in specs_text)
                elif req_l in ["layer 3", "l3"]:
                    ok = ("layer 3" in specs_text) or ("l3" in specs_text)
                elif req_l in ["wifi 6", "wi-fi 6", "802.11ax"]:
                    ok = ("wi-fi 6" in specs_text) or ("wifi 6" in specs_text) or ("802.11ax" in specs_text)
                elif req_l == "ha":
                    ok = ("ha" in specs_text) or ("high availability" in specs_text)
                elif req_l == "vpn":
                    ok = ("non-vpn" not in specs_text) and (
                        "vpn" in specs_text or "ngfw" in specs_text or "sd-wan" in specs_text or "ipsec" in specs_text
                    )
                elif req_l == "24x7":
                    ok = ("24x7" in specs_text) or ("24/7" in specs_text)
                elif req_l == "8x5":
                    ok = ("8x5" in specs_text) or ("8/5" in specs_text)
                else:
                    ok = req_l in specs_text

                if ok:
                    matched_reqs += 1
                else:
                    missing_reqs.append(req)

            # Nếu thiếu yêu cầu kỹ thuật bắt buộc -> không đạt chuẩn
            if len(required_features) > 0 and missing_reqs:
                disqualified_reasons.append(f"{row.get(sku_col)}: Thiếu {missing_reqs}")
                continue

            # Chấm điểm ưu tiên: khớp nhiều đặc tính + ưu tiên còn tồn kho + giá hợp lý
            stock_val = int(row.get(stock_col, 0))
            stock_bonus = 2 if stock_val >= quantity_needed else 0
            score = matched_reqs * 10 + stock_bonus

            # Tie-breaker: ưu tiên giá thấp hơn nhưng VẪN ĐẠT ĐỦ 100% tính năng bắt buộc
            if best_candidate is None or score > best_score or (
                score == best_score and float(row.get(price_col, 0)) < float(best_candidate.get("list_price", 0))
            ):
                best_score = score
                best_candidate = {
                    "sku": str(row.get(sku_col, "")),
                    "name": str(row.get(name_col, "")),
                    "category": str(row.get(cat_col, "")),
                    "specs": str(row.get(specs_col, "")),
                    "stock": stock_val,
                    "lead_time_days": int(row.get(lead_col, 0)),
                    "cost_price": float(row.get(cost_col, 0)),
                    "list_price": float(row.get(price_col, 0)),
                    "match_score": score
                }

        if best_candidate is None:
            summary = f"0/{len(candidates)} candidates passed mandatory specs. Disqualified: {disqualified_reasons}"
            self.tracer.record(self.TOOL_NAME, "find_best_matching_product",
                               {"category": category_query, "required": required_features},
                               summary, len(candidates), t0, "OK")
            return {
                "found": False,
                "reason": f"Không có thiết bị nào thuộc nhóm '{category_query}' đáp ứng đầy đủ điều kiện bắt buộc: {required_features}. ({'; '.join(disqualified_reasons)})"
            }

        summary = f"Matched {best_candidate['sku']} (Stock: {best_candidate['stock']}, ListPrice: {best_candidate['list_price']:,.0f}) from {len(candidates)} candidates"
        self.tracer.record(self.TOOL_NAME, "find_best_matching_product",
                           {"category": category_query, "required": required_features, "qty": quantity_needed},
                           summary, len(candidates), t0, "OK")
        return {"found": True, "product": best_candidate, "candidates_evaluated": len(candidates)}

    def lookup_services(self, service_keywords: List[str]) -> List[Dict[str, Any]]:
        """Tra cứu động dịch vụ từ bảng NangLuc_TrienKhai."""
        t0 = time.perf_counter()
        df = self._get_df("NangLuc_TrienKhai", 1)
        matched = []
        if not df.empty:
            for _, row in df.iterrows():
                name_str = str(row.get("name", "")).lower()
                if any(kw.lower() in name_str for kw in service_keywords):
                    matched.append({
                        "service_id": str(row.get("service_id", "")),
                        "name": str(row.get("name", "")),
                        "unit": str(row.get("unit", "Gói")),
                        "price": float(row.get("price", 0)),
                        "cost": float(row.get("cost", 0)),
                        "min_days": int(row.get("min_days", 0)),
                        "capacity": str(row.get("capacity", ""))
                    })
        self.tracer.record(self.TOOL_NAME, "lookup_services",
                           {"keywords": service_keywords},
                           f"Found {len(matched)} matching service(s)", len(df), t0, "OK")
        return matched

    def lookup_deployment_teams(self, location_text: str, max_concurrent: int = 2) -> Dict[str, Any]:
        """Tra cứu năng lực đội ngũ triển khai từ bảng Lich_TrienKhai_KhaDung."""
        t0 = time.perf_counter()
        df = self._get_df("Lich_TrienKhai_KhaDung", 3)
        if df.empty or "team_id" not in df.columns:
            self.tracer.record(self.TOOL_NAME, "lookup_deployment_teams",
                               {"location": location_text}, "Schedule table missing or empty", 0, t0, "OK")
            return {"status": "UNCLEAR", "reason": "Không có dữ liệu lịch đội kỹ thuật để xác minh.", "teams": []}

        loc_l = location_text.lower()
        target_region = "Miền Bắc"
        if any(k in loc_l for k in ["hồ chí minh", "tp.hcm", "miền nam", "bình dương", "đồng nai"]):
            target_region = "Miền Nam"
        elif any(k in loc_l for k in ["đà nẵng", "miền trung", "huế", "quảng nam"]):
            target_region = "Miền Trung"

        teams = df.to_dict(orient="records")
        region_teams = [t for t in teams if str(t.get("region", "")).lower() == target_region.lower()]
        if not region_teams:
            region_teams = teams

        available_teams = [t for t in region_teams if int(t.get("active_projects", 0)) < max_concurrent]
        status = "AVAILABLE" if available_teams else "OVERLOADED"

        self.tracer.record(self.TOOL_NAME, "lookup_deployment_teams",
                           {"location": location_text, "target_region": target_region},
                           f"Status: {status}, Available teams: {len(available_teams)}/{len(region_teams)}",
                           len(df), t0, "OK")
        return {
            "status": status,
            "target_region": target_region,
            "available_teams": available_teams,
            "all_region_teams": region_teams
        }
