"""
Module export_generator.py:
Xuất bản chào giá và hồ sơ đề xuất kinh doanh ra file:
- Excel (.xlsx) chứa Trang Bìa Hồ Sơ, BoQ chi tiết, phân tích tài chính và đối soát kỹ thuật.
- Word (.docx) có Trang Bìa (Cover Page) chuẩn hồ sơ thầu B2B riêng biệt ở Trang 1, theo sau bởi nội dung chi tiết.
"""

import io
from datetime import datetime
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from typing import Dict, Any


def _set_cell_background(cell, fill_hex: str):
    """Tô màu nền ô bảng trong Word (ví dụ 'FF7A00' hoặc 'F8FAFC')."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tcPr.append(shd)


def export_quotation_to_excel(
    quotation_data: Dict[str, Any],
    validation_data: Dict[str, Any],
    parsed_rfp: Dict[str, Any]
) -> bytes:
    """Xuất file Excel báo giá chi tiết (BoQ) kèm sheet Trang Bìa."""
    output = io.BytesIO()
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 0: Trang Bìa Hồ Sơ (Cover Sheet)
        cover_rows = [
            {"Mục": "TÊN TÀI LIỆU", "Nội dung": "HỒ SƠ ĐỀ XUẤT KỸ THUẬT & BÁO GIÁ THƯƠNG MẠI B2B"},
            {"Mục": "Đơn vị phát hành (Nhà thầu)", "Nội dung": "CÔNG TY TNHH THIẾT BỊ MẠNG THIÊN MINH"},
            {"Mục": "Đơn vị yêu cầu (Chủ đầu tư)", "Nội dung": parsed_rfp.get("customer_name", "Quý Khách Hàng")},
            {"Mục": "Địa điểm triển khai", "Nội dung": parsed_rfp.get("location", "Theo hồ sơ mời thầu")},
            {"Mục": "Thời hạn nộp hồ sơ", "Nội dung": parsed_rfp.get("submission_deadline", "Theo yêu cầu")},
            {"Mục": "Ngày xuất hồ sơ", "Nội dung": now_str},
            {"Mục": "Tổng giá niêm yết (VNĐ)", "Nội dung": f"{quotation_data.get('total_list_price', 0):,.0f} VNĐ"},
            {"Mục": "Chiết khấu thương mại", "Nội dung": f"{quotation_data.get('applied_discount_pct', 0):.1f}% (-{quotation_data.get('discount_amount', 0):,.0f} VNĐ)"},
            {"Mục": "TỔNG GIÁ CHÀO BÁN NET (Chưa VAT)", "Nội dung": f"{quotation_data.get('net_quoted_price', 0):,.0f} VNĐ"},
            {"Mục": "Thời gian triển khai dự kiến", "Nội dung": f"{validation_data.get('total_required_days', 10)} ngày làm việc"},
            {"Mục": "Cam kết dịch vụ SLA", "Nội dung": f"Gói bảo trì tiêu chuẩn {parsed_rfp.get('sla_type', '8x5')}"},
        ]
        pd.DataFrame(cover_rows).to_excel(writer, sheet_name="Trang_Bia_Ho_So", index=False)

        # Sheet 1: Bảng chào giá BoQ
        items = quotation_data.get("boq_items", [])
        df_boq = pd.DataFrame(items)
        col_rename = {
            "stt": "STT",
            "type": "Phân loại",
            "name": "Tên Thiết bị / Dịch vụ",
            "sku": "Mã SKU/Dịch vụ",
            "specs": "Thông số kỹ thuật / Đặc tính",
            "unit": "ĐVT",
            "quantity": "Số lượng",
            "unit_list_price": "Đơn giá Niêm yết (VNĐ)",
            "total_list_price": "Thành tiền Niêm yết (VNĐ)",
            "lead_time": "Thời gian giao/Lắp"
        }
        cols_to_keep = [k for k in col_rename.keys() if k in df_boq.columns]
        df_boq_export = df_boq[cols_to_keep].rename(columns=col_rename)
        df_boq_export.to_excel(writer, sheet_name="Bang_Chao_Gia_BoQ", index=False)

        # Sheet 2: Phân tích Tài chính
        summary_data = [
            {"Chỉ số tài chính": "Tổng giá niêm yết (List Price)", "Giá trị (VNĐ)": f"{quotation_data.get('total_list_price', 0):,.0f}", "Ghi chú": "Giá niêm yết chuẩn"},
            {"Chỉ số tài chính": "Tỷ lệ chiết khấu áp dụng", "Giá trị (VNĐ)": f"{quotation_data.get('applied_discount_pct', 0):.1f}%", "Ghi chú": "Mức ưu đãi thương mại"},
            {"Chỉ số tài chính": "Số tiền chiết khấu", "Giá trị (VNĐ)": f"{quotation_data.get('discount_amount', 0):,.0f}", "Ghi chú": "Khoản giảm giá cho khách"},
            {"Chỉ số tài chính": "Giá chào thực tế (Net Quoted Price)", "Giá trị (VNĐ)": f"{quotation_data.get('net_quoted_price', 0):,.0f}", "Ghi chú": "Chưa bao gồm VAT"},
            {"Chỉ số tài chính": "Giá vốn dự toán (COGS)", "Giá trị (VNĐ)": f"{quotation_data.get('total_cost_price', 0):,.0f}", "Ghi chú": "Giá nhập + Chi phí thi công"},
            {"Chỉ số tài chính": "Lợi nhuận gộp (Gross Profit)", "Giá trị (VNĐ)": f"{quotation_data.get('gross_profit', 0):,.0f}", "Ghi chú": "Lãi gộp dự án"},
            {"Chỉ số tài chính": "Biên lợi nhuận gộp (Gross Margin)", "Giá trị (VNĐ)": f"{quotation_data.get('gross_margin_pct', 0):.1f}%", "Ghi chú": "Tỷ suất sinh lời"}
        ]
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name="Phan_Tich_Tai_Chinh", index=False)

        # Sheet 3: Đối soát kỹ thuật (Compliance Matrix)
        checks = validation_data.get("compliance_checks", [])
        if checks:
            df_checks = pd.DataFrame(checks).rename(columns={
                "item": "Hạng mục",
                "required": "Yêu cầu kỹ thuật bắt buộc",
                "matched_solution": "Giải pháp Thiên Minh đề xuất",
                "status": "Đánh giá tuân thủ",
                "note": "Ghi chú bảo đảm tính năng"
            })
            df_checks.to_excel(writer, sheet_name="Doi_Soat_Ky_Thuat", index=False)

    output.seek(0)
    return output.getvalue()


def export_proposal_to_docx(
    quotation_data: Dict[str, Any],
    validation_data: Dict[str, Any],
    parsed_rfp: Dict[str, Any],
    approval_data: Dict[str, Any]
) -> bytes:
    """
    Xuất file Word Hồ sơ Đề xuất Kỹ thuật & Thương mại chuyên nghiệp.
    Trang 1 là TRANG BÌA (Cover Page) độc lập chuẩn hồ sơ thầu B2B.
    """
    doc = Document()
    now_str = datetime.now().strftime("%d/%m/%Y")
    doc_code = f"TM-PROP-{datetime.now().strftime('%Y%m%d-%H%M')}"
    customer_name = parsed_rfp.get("customer_name") or "QUÝ KHÁCH HÀNG DOANH NGHIỆP"
    location = parsed_rfp.get("location") or "Việt Nam"
    deadline = parsed_rfp.get("submission_deadline") or "Theo thông báo mời thầu"
    sla_type = parsed_rfp.get("sla_type") or "8x5"
    net_price = quotation_data.get("net_quoted_price", 0)
    list_price = quotation_data.get("total_list_price", 0)
    disc_pct = quotation_data.get("applied_discount_pct", 0)
    disc_amt = quotation_data.get("discount_amount", 0)
    req_days = validation_data.get("total_required_days", 10)
    appr_level = approval_data.get("approval_level", "NVKD ĐƯỢC PHÉP BAN HÀNH")

    # =========================================================================
    # TRANG 1: TRANG BÌA HỒ SƠ ĐỀ XUẤT (EXECUTIVE B2B COVER PAGE)
    # =========================================================================
    # 1. Quốc hiệu & Tiêu ngữ / Tên đơn vị (Bảng 2 cột)
    hdr_table = doc.add_table(rows=1, cols=2)
    hdr_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_left, c_right = hdr_table.rows[0].cells[0], hdr_table.rows[0].cells[1]

    p_l1 = c_left.paragraphs[0]
    p_l1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_l1 = p_l1.add_run("CÔNG TY TNHH THIẾT BỊ MẠNG THIÊN MINH\n")
    r_l1.bold = True
    r_l1.font.size = Pt(10)
    r_l1.font.color.rgb = RGBColor(15, 23, 42)
    r_l2 = p_l1.add_run("KHỐI GIẢI PHÁP & KINH DOANH B2B\n")
    r_l2.font.size = Pt(9)
    r_l2.font.color.rgb = RGBColor(255, 122, 0)
    r_l3 = p_l1.add_run(f"Số: {doc_code}")
    r_l3.italic = True
    r_l3.font.size = Pt(9)

    p_r1 = c_right.paragraphs[0]
    p_r1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_r1 = p_r1.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n")
    r_r1.bold = True
    r_r1.font.size = Pt(10)
    r_r2 = p_r1.add_run("Độc lập - Tự do - Hạnh phúc\n")
    r_r2.bold = True
    r_r2.font.size = Pt(9.5)
    r_r3 = p_r1.add_run(f"Hà Nội, ngày {now_str}")
    r_r3.italic = True
    r_r3.font.size = Pt(9)

    doc.add_paragraph("")

    # 2. Nhãn Bảo mật & Phân loại Hồ sơ
    p_badge = doc.add_paragraph()
    p_badge.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_badge = p_badge.add_run("★ HỒ SƠ DỰ THẦU & ĐỀ XUẤT GIẢI PHÁP B2B — BẢO MẬT THƯƠNG MẠI ★")
    r_badge.bold = True
    r_badge.font.size = Pt(9.5)
    r_badge.font.color.rgb = RGBColor(255, 122, 0)

    # 3. Tiêu đề chính của Trang Bìa
    p_main_title = doc.add_paragraph()
    p_main_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_mt1 = p_main_title.add_run("HỒ SƠ ĐỀ XUẤT KỸ THUẬT\n& BÁO GIÁ THƯƠNG MẠI")
    r_mt1.bold = True
    r_mt1.font.size = Pt(22)
    r_mt1.font.color.rgb = RGBColor(15, 23, 42)

    p_sub_title = doc.add_paragraph()
    p_sub_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_st = p_sub_title.add_run("TECHNICAL & COMMERCIAL PROPOSAL — ENTERPRISE NETWORK INFRASTRUCTURE")
    r_st.bold = True
    r_st.font.size = Pt(10)
    r_st.font.color.rgb = RGBColor(100, 116, 139)

    # 4. Khung Tên Dự Án & Chủ Đầu Tư nổi bật
    proj_table = doc.add_table(rows=1, cols=1)
    proj_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    proj_cell = proj_table.rows[0].cells[0]
    _set_cell_background(proj_cell, "FFF4EC")
    p_proj = proj_cell.paragraphs[0]
    p_proj.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_pj1 = p_proj.add_run("DỰ ÁN: CUNG CẤP & TRIỂN KHAI HẠ TẦNG MẠNG DOANH NGHIỆP\n")
    r_pj1.bold = True
    r_pj1.font.size = Pt(12)
    r_pj1.font.color.rgb = RGBColor(234, 108, 0)
    r_pj2 = p_proj.add_run(f"KÍNH GỬI: {customer_name.upper()}\n")
    r_pj2.bold = True
    r_pj2.font.size = Pt(13)
    r_pj2.font.color.rgb = RGBColor(15, 23, 42)
    r_pj3 = p_proj.add_run(f"Địa điểm triển khai: {location}")
    r_pj3.font.size = Pt(10.5)

    doc.add_paragraph("")

    # 5. Bảng Tóm Tắt Định Danh Hồ Sơ Trên Trang Bìa
    meta_rows = [
        ("Mã hồ sơ đề xuất", doc_code),
        ("Chủ đầu tư / Bên mời thầu", customer_name),
        ("Đơn vị tư vấn & Nhà thầu", "CÔNG TY TNHH THIẾT BỊ MẠNG THIÊN MINH"),
        ("Địa điểm lắp đặt & bàn giao", location),
        ("Thời hạn nộp hồ sơ (Deadline)", deadline),
        ("Tổng giá trị đề xuất (Net, chưa VAT)", f"{net_price:,.0f} VNĐ (Đã chiết khấu {disc_pct:.1f}%)"),
        ("Thời gian thi công & bàn giao", f"{req_days} ngày làm việc kể từ ngày ký hợp đồng"),
        ("Cam kết bảo hành & bảo trì (SLA)", f"Bảo hành chính hãng 12 tháng | Hỗ trợ kỹ thuật {sla_type}"),
        ("Cấp phê duyệt thẩm quyền (Gate 4)", appr_level),
        ("Trạng thái kiểm định cuối (Gate 5)", "ĐẠT CHUẨN QUALITY GATE — SẴN SÀNG BÀN GIAO"),
    ]
    meta_table = doc.add_table(rows=len(meta_rows) + 1, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header row
    h0, h1 = meta_table.rows[0].cells[0], meta_table.rows[0].cells[1]
    _set_cell_background(h0, "0F172A")
    _set_cell_background(h1, "0F172A")
    rh0 = h0.paragraphs[0].add_run("THÔNG TIN HỒ SƠ DỰ THẦU")
    rh0.bold = True
    rh0.font.size = Pt(10)
    rh0.font.color.rgb = RGBColor(255, 255, 255)
    rh1 = h1.paragraphs[0].add_run("CHI TIẾT XÁC NHẬN")
    rh1.bold = True
    rh1.font.size = Pt(10)
    rh1.font.color.rgb = RGBColor(255, 255, 255)

    for idx, (k, v) in enumerate(meta_rows, start=1):
        c0, c1 = meta_table.rows[idx].cells[0], meta_table.rows[idx].cells[1]
        bg = "F8FAFC" if idx % 2 == 1 else "FFFFFF"
        _set_cell_background(c0, bg)
        _set_cell_background(c1, bg)
        rk = c0.paragraphs[0].add_run(k)
        rk.bold = True
        rk.font.size = Pt(9.5)
        rv = c1.paragraphs[0].add_run(str(v))
        rv.font.size = Pt(9.5)
        if "Tổng giá trị" in k or "Gate 5" in k:
            rv.bold = True
            rv.font.color.rgb = RGBColor(234, 108, 0)

    doc.add_paragraph("")

    # 6. Khối Xác Nhận & Chữ Ký Trang Bìa (3 Cột)
    sign_table = doc.add_table(rows=1, cols=3)
    sign_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    s_titles = [
        ("KIẾN TRÚC SƯ GIẢI PHÁP\n(Solution Architect)", "Đã thẩm định kỹ thuật\n(Gate 2 & Gate 3)"),
        ("PHỤ TRÁCH KINH DOANH\n(B2B Account Lead)", "Đã kiểm tra báo giá\n(Phase 04 Commercial)"),
        ("PHÊ DUYỆT THẨM QUYỀN\n(B2B Sales Director)", f"{appr_level}\n(Gate 4 & Gate 5)")
    ]
    for idx, (stitle, ssub) in enumerate(s_titles):
        sc = sign_table.rows[0].cells[idx]
        ps = sc.paragraphs[0]
        ps.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rs1 = ps.add_run(stitle + "\n\n")
        rs1.bold = True
        rs1.font.size = Pt(9)
        rs2 = ps.add_run(ssub)
        rs2.italic = True
        rs2.font.size = Pt(8.5)
        rs2.font.color.rgb = RGBColor(100, 116, 139)

    # Ngắt trang sau Trang Bìa để vào nội dung chính ở Trang 2
    doc.add_page_break()

    # =========================================================================
    # TRANG 2+: NỘI DUNG CHI TIẾT HỒ SƠ ĐỀ XUẤT KỸ THUẬT & THƯƠNG MẠI
    # =========================================================================
    doc.add_heading("1. PHÂN TÍCH TỔNG QUAN YÊU CẦU & MỤC TIÊU DỰ ÁN", level=1)
    doc.add_paragraph(
        f"Hồ sơ yêu cầu chào giá (RFQ) của {customer_name} triển khai tại {location} đã được "
        "Hệ thống AI Agent Master Workflow và Hội đồng Giải pháp Công ty Thiên Minh thẩm định qua "
        "6 giai đoạn (6 Phases - 12 Steps - 5 Decision Gates). Phương án đề xuất dưới đây đảm bảo "
        "đáp ứng 100% tiêu chuẩn kỹ thuật bắt buộc, tối ưu chi phí đầu tư và cam kết đúng tiến độ bàn giao."
    )

    doc.add_heading("2. BẢNG ĐỐI SOÁT & TUÂN THỦ KỸ THUẬT BẮT BUỘC (COMPLIANCE MATRIX)", level=1)
    checks = validation_data.get("compliance_checks", [])
    if checks:
        table = doc.add_table(rows=1, cols=4)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_cells = table.rows[0].cells
        headers = ["Hạng mục", "Yêu cầu bắt buộc", "Giải pháp Thiên Minh đề xuất", "Đánh giá"]
        for i, h_text in enumerate(headers):
            _set_cell_background(hdr_cells[i], "0F172A")
            run = hdr_cells[i].paragraphs[0].add_run(h_text)
            run.bold = True
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(255, 255, 255)
        for c in checks:
            row_cells = table.add_row().cells
            row_cells[0].text = str(c.get("item", ""))
            row_cells[1].text = str(c.get("required", ""))
            row_cells[2].text = str(c.get("matched_solution", ""))
            row_cells[3].text = str(c.get("status", ""))

    doc.add_heading("3. BẢNG DỰ TOÁN KHỐI LƯỢNG & BÁO GIÁ CHI TIẾT (BoQ)", level=1)
    boq_items = quotation_data.get("boq_items", [])
    if boq_items:
        boq_table = doc.add_table(rows=1, cols=6)
        boq_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        b_headers = ["STT", "Tên Thiết Bị / Dịch Vụ", "Mã SKU", "ĐVT", "SL", "Thành Tiền (VNĐ)"]
        for i, bh in enumerate(b_headers):
            _set_cell_background(boq_table.rows[0].cells[i], "FF7A00")
            r = boq_table.rows[0].cells[i].paragraphs[0].add_run(bh)
            r.bold = True
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(255, 255, 255)
        for it in boq_items:
            rc = boq_table.add_row().cells
            rc[0].text = str(it.get("stt", ""))
            rc[1].text = f"{it.get('name', '')} ({it.get('specs', '')})"
            rc[2].text = str(it.get("sku", ""))
            rc[3].text = str(it.get("unit", ""))
            rc[4].text = str(it.get("quantity", ""))
            rc[5].text = f"{it.get('total_list_price', 0):,.0f}"

    doc.add_paragraph("")
    doc.add_paragraph(f"• Tổng giá trị niêm yết (List Price): {list_price:,.0f} VNĐ")
    doc.add_paragraph(f"• Chiết khấu thương mại áp dụng ({disc_pct:.1f}%): -{disc_amt:,.0f} VNĐ")
    p_net = doc.add_paragraph()
    r_net = p_net.add_run(f"• TỔNG GIÁ CHÀO BÁN THỰC TẾ (NET, CHƯA VAT): {net_price:,.0f} VNĐ")
    r_net.bold = True
    r_net.font.color.rgb = RGBColor(234, 108, 0)

    doc.add_heading("4. KẾ HOẠCH TRIỂN KHAI & CAM KẾT BẢO TRÌ SLA", level=1)
    doc.add_paragraph(f"• Tổng thời gian giao hàng và thi công trọn gói: {req_days} ngày làm việc.")
    doc.add_paragraph(f"• Cam kết dịch vụ hỗ trợ kỹ thuật (SLA): Gói {sla_type}, phản hồi sự cố trong vòng 4 giờ.")
    doc.add_paragraph("• Bảo hành tiêu chuẩn: 12 tháng chính hãng theo quy định của nhà sản xuất.")

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output.getvalue()
