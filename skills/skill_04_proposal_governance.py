"""
skills/skill_04_proposal_governance.py
Custom Skill 4: Proposal Generation, Task Routing & Final Quality Gate (Phase 05 & Phase 06 - Steps 10, 11, 12)
- Tạo 6 nhóm kết quả đầu ra đầy đủ.
- Xuất file Excel (.xlsx), Word (.docx), JSON ra thư mục outputs/.
- Đánh giá Cổng chất lượng cuối (Gate 5 - Quality Gate).
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from agent_engine.export_generator import export_quotation_to_excel, export_proposal_to_docx
from skills.skill_01_intake_structurer import IntakeOutput
from skills.skill_02_solution_matcher import SolutionMatchOutput
from skills.skill_03_commercial_pricer import CommercialOutput

class GovernanceInput(BaseModel):
    opp_id: str
    intake_out: IntakeOutput
    match_out: Optional[SolutionMatchOutput] = None
    commercial_out: Optional[CommercialOutput] = None
    hitl_decision: Optional[Dict[str, Any]] = None
    quality_rules: Dict[str, Any] = {}
    tool_calls: List[Dict[str, Any]] = []
    execution_logs: List[Dict[str, Any]] = []

class GovernanceOutput(BaseModel):
    quality_gate_passed: bool
    quality_checks: List[Dict[str, Any]]
    failed_step_redirect: Optional[str] = None
    task_assignments: Dict[str, Any]
    output_files: Dict[str, str]
    six_output_groups: Dict[str, Any]

class ProposalGovernanceSkill:
    SKILL_NAME = "ProposalGovernanceSkill"

    def _assign_owners(self, structured_rfq: Dict[str, Any], match_out: Optional[SolutionMatchOutput]) -> Dict[str, Any]:
        loc = structured_rfq.get("location", "").lower()
        region = "Miền Bắc"
        sales_lead = "Nguyễn Văn Hải (Senior Sales B2B)"
        tech_lead = "Nguyễn Văn Hùng (Lead Solution Architect)"
        ops_coord = "Lê Thị Lan (Điều phối Kho & Vận hành)"

        if any(k in loc for k in ["hồ chí minh", "tp.hcm", "miền nam", "bình dương"]):
            region = "Miền Nam"
            sales_lead = "Lê Thị Mai (Key Account Manager)"
            tech_lead = "Lê Hoàng Nam (Lead Network Engineer)"
            ops_coord = "Võ Văn Kiên (Điều phối Kho & Vận hành)"
        elif any(k in loc for k in ["đà nẵng", "miền trung", "huế"]):
            region = "Miền Trung"
            sales_lead = "Trần Thanh Tùng (Account Director)"
            tech_lead = "Trần Đình Trọng (Pre-sales Architect)"
            ops_coord = "Nguyễn Thị Ngọc (Phòng Vận hành)"

        # Nếu match_out đã tìm được kỹ sư trực tiếp từ bảng Lich_TrienKhai_KhaDung
        if match_out and match_out.team_info.get("available_teams"):
            first_team = match_out.team_info["available_teams"][0]
            tech_lead = f"{first_team.get('lead_engineer')} ({first_team.get('team_id')})"

        return {
            "region": region,
            "sales_lead": sales_lead,
            "tech_lead": tech_lead,
            "ops_coordinator": ops_coord,
            "assigned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def run(self, inp: GovernanceInput) -> GovernanceOutput:
        rfq = inp.intake_out.structured_rfq
        tasks = self._assign_owners(rfq, inp.match_out)
        q_rules = inp.quality_rules

        quality_checks = []
        failed_step_redirect = None

        # 1. Đánh giá Quality Gate (Gate 5)
        if not inp.intake_out.is_complete_and_consistent:
            quality_checks.append({"check": "Đầy đủ & nhất quán thông tin", "passed": False, "detail": "Thất bại tại Gate 1"})
            failed_step_redirect = "Step 04: Requirement Validation"
        elif inp.match_out and not inp.match_out.all_mandatory_met and q_rules.get("require_zero_unmatched_mandatory", True):
            quality_checks.append({"check": "Đáp ứng điều kiện kỹ thuật bắt buộc", "passed": False, "detail": "Có hạng mục không khớp trong danh mục"})
            failed_step_redirect = "Step 05: Product & Solution Matching"
        elif inp.commercial_out:
            boq_ok = (len(inp.commercial_out.boq_items) > 0) if q_rules.get("require_non_empty_boq", True) else True
            price_ok = (inp.commercial_out.financials["net_quoted_price"] > 0) if q_rules.get("require_positive_net_price", True) else True
            needs_appr = inp.commercial_out.policy_evaluation["needs_special_approval"]
            hitl = inp.hitl_decision

            quality_checks.append({"check": "BoQ có hạng mục", "passed": boq_ok, "detail": f"{len(inp.commercial_out.boq_items)} dòng BoQ"})
            quality_checks.append({"check": "Giá chào hợp lệ (> 0)", "passed": price_ok, "detail": f"{inp.commercial_out.financials['net_quoted_price']:,.0f} VNĐ"})

            if not boq_ok or not price_ok:
                failed_step_redirect = "Step 08: Pricing Calculation"
            elif needs_appr and q_rules.get("require_manager_signoff_if_escalated", True):
                if hitl and hitl.get("decision") == "APPROVED":
                    quality_checks.append({"check": "Phê duyệt ngoại lệ của Quản lý (HITL)", "passed": True, "detail": f"Đã duyệt bởi {hitl.get('decided_by')}"})
                else:
                    status_str = hitl.get("status_label") if hitl else "CHƯA CÓ PHÊ DUYỆT TỪ QUẢN LÝ"
                    quality_checks.append({"check": "Phê duyệt ngoại lệ của Quản lý (HITL)", "passed": False, "detail": status_str})
                    failed_step_redirect = "Step 09: Quản lý phê duyệt (HITL)"
            else:
                quality_checks.append({"check": "Thẩm quyền phê duyệt", "passed": True, "detail": "Trong hạn mức NVKD tự quyết"})
        else:
            quality_checks.append({"check": "Dữ liệu thương mại", "passed": False, "detail": "Chưa tính toán báo giá"})
            failed_step_redirect = "Step 08: Pricing Calculation"

        quality_gate_passed = all(c["passed"] for c in quality_checks) and (failed_step_redirect is None)

        # 2. Tạo file đầu ra thực tế vào thư mục outputs/
        os.makedirs("outputs", exist_ok=True)
        output_files = {}

        if inp.commercial_out and inp.match_out:
            # Chuẩn bị dict tương thích với export_generator
            q_dict = dict(inp.commercial_out.financials)
            q_dict["boq_items"] = inp.commercial_out.boq_items
            q_dict["budget_comparison"] = inp.commercial_out.budget_comparison

            v_dict = inp.match_out.model_dump()
            a_dict = dict(inp.commercial_out.policy_evaluation)
            if inp.hitl_decision:
                a_dict["approval_level"] = inp.hitl_decision.get("status_label", a_dict["approval_level"])

            excel_bytes = export_quotation_to_excel(q_dict, v_dict, rfq)
            docx_bytes = export_proposal_to_docx(q_dict, v_dict, rfq, a_dict)

            excel_path = os.path.join("outputs", f"Bao_Gia_{inp.opp_id}.xlsx")
            docx_path = os.path.join("outputs", f"De_Xuat_{inp.opp_id}.docx")

            with open(excel_path, "wb") as f:
                f.write(excel_bytes)
            with open(docx_path, "wb") as f:
                f.write(docx_bytes)

            output_files["excel_boq"] = excel_path
            output_files["word_proposal"] = docx_path

        # 3. Tổng hợp 6 nhóm kết quả đầu ra theo yêu cầu
        six_output_groups = {
            "group_1_requirement_analysis": {
                "title": "Nhóm 1: Phân tích Hồ sơ & Kiểm tra Đầy đủ/Nhất quán",
                "structured_rfq": rfq,
                "checklist": inp.intake_out.checklist,
                "missing_items": inp.intake_out.missing_items,
                "inconsistencies": inp.intake_out.inconsistencies,
                "clarification_letter": inp.intake_out.clarification_letter
            },
            "group_2_technical_and_deployment": {
                "title": "Nhóm 2: Đối soát Giải pháp Kỹ thuật, Tồn kho & Lịch triển khai",
                "compliance_checks": inp.match_out.compliance_checks if inp.match_out else [],
                "unmatched_items": inp.match_out.unmatched_items if inp.match_out else [],
                "inventory_warnings": inp.match_out.inventory_warnings if inp.match_out else [],
                "schedule_status": inp.match_out.schedule_status if inp.match_out else "N/A",
                "schedule_warnings": inp.match_out.schedule_warnings if inp.match_out else [],
                "total_required_days": inp.match_out.total_required_days if inp.match_out else 0
            },
            "group_3_commercial_quotation": {
                "title": "Nhóm 3: Dự toán Bóc tách BoQ & Phân tích Tài chính",
                "boq_items": inp.commercial_out.boq_items if inp.commercial_out else [],
                "financials": inp.commercial_out.financials if inp.commercial_out else {},
                "budget_comparison": inp.commercial_out.budget_comparison if inp.commercial_out else {}
            },
            "group_4_task_and_approval_routing": {
                "title": "Nhóm 4: Phân công Nhiệm vụ & Phiếu Chuyển duyệt (HITL)",
                "task_assignments": tasks,
                "policy_evaluation": inp.commercial_out.policy_evaluation if inp.commercial_out else {},
                "escalation_report": inp.commercial_out.escalation_report if inp.commercial_out else "",
                "hitl_decision": inp.hitl_decision
            },
            "group_5_exportable_deliverables": {
                "title": "Nhóm 5: Hồ sơ Đề xuất Hoàn chỉnh & File Xuất",
                "output_files": output_files
            },
            "group_6_governance_and_audit": {
                "title": "Nhóm 6: Nhật ký Thực thi, Bằng chứng Gọi Công cụ & Quality Gate",
                "quality_gate_passed": quality_gate_passed,
                "quality_checks": quality_checks,
                "failed_step_redirect": failed_step_redirect,
                "tool_calls_count": len(inp.tool_calls),
                "tool_calls": inp.tool_calls,
                "execution_logs": inp.execution_logs
            }
        }

        json_path = os.path.join("outputs", f"Full_Report_{inp.opp_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(six_output_groups, f, ensure_ascii=False, indent=2)
        output_files["json_report"] = json_path

        return GovernanceOutput(
            quality_gate_passed=quality_gate_passed,
            quality_checks=quality_checks,
            failed_step_redirect=failed_step_redirect,
            task_assignments=tasks,
            output_files=output_files,
            six_output_groups=six_output_groups
        )
