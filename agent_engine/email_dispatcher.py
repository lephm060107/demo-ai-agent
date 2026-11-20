"""
Module email_dispatcher.py:
Quản lý tạo và gửi email thông báo tự động theo quy trình bán hàng B2B:
1. Gửi Khách hàng: Thư yêu cầu làm rõ / bổ sung thông tin.
2. Gửi Trưởng phòng Kinh doanh: Thông báo cơ hội bán hàng cần phê duyệt khẩn.
3. Gửi Khách hàng: Thư báo giá chính thức kèm hồ sơ đề xuất.
"""

from typing import Dict, Any, Optional
from datetime import datetime

def build_clarification_email_html(parsed: Dict[str, Any], missing_items: list) -> str:
    """Tạo mẫu email HTML gửi khách hàng yêu cầu làm rõ thông tin."""
    cust = parsed.get("customer_name", "Quý Khách hàng")
    now_str = datetime.now().strftime("%d/%m/%Y")
    
    items_html = "".join([f"<li style='margin-bottom: 8px;'><strong>{it}</strong></li>" for it in missing_items])
    
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 650px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #1e3a8a; color: white; padding: 20px; text-align: center;">
            <h2 style="margin: 0; font-size: 20px;">CÔNG TY TNHH THIẾT BỊ MẠNG THIÊN MINH</h2>
            <p style="margin: 5px 0 0; font-size: 13px; opacity: 0.9;">Phòng Giải Pháp & Kinh Doanh Doanh Nghiệp (B2B)</p>
        </div>
        <div style="padding: 24px; color: #334155; line-height: 1.6;">
            <p>Kính gửi: <strong>{cust}</strong>,</p>
            <p>Thiên Minh xin chân thành cảm ơn Quý đơn vị đã gửi yêu cầu chào giá dự án hạ tầng mạng.</p>
            <p>Để đảm bảo đề xuất giải pháp kỹ thuật đáp ứng chính xác nhất tiêu chuẩn hoạt động, tính năng tương thích và tối ưu hóa ngân sách, chúng tôi kính đề nghị Quý khách hỗ trợ làm rõ một số điểm sau:</p>
            
            <div style="background-color: #f8fafc; border-left: 4px solid #0284c7; padding: 12px 16px; margin: 15px 0;">
                <h4 style="margin: 0 0 10px; color: #0369a1;">DANH MỤC THÔNG TIN CẦN BỔ SUNG:</h4>
                <ul style="margin: 0; padding-left: 20px;">
                    {items_html}
                </ul>
            </div>
            
            <p>Đội ngũ kỹ sư của Thiên Minh sẵn sàng đến khảo sát trực tiếp tại địa điểm trong vòng 24 giờ hoàn toàn miễn phí.</p>
            <p>Kính mong nhận được phản hồi của Quý đơn vị trước ngày <strong>{now_str}</strong> để chúng tôi kịp thời hoàn thiện hồ sơ chào giá.</p>
            
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
            <p style="font-size: 13px; color: #64748b; margin: 0;">
                <strong>Người phụ trách:</strong> Bộ phận Pre-Sales Thiên Minh<br>
                Hotline Kỹ thuật: 1900-6868 | Email: presales@thienminh-network.vn
            </p>
        </div>
    </div>
    """
    return html

def build_approval_request_email_html(
    opp: Dict[str, Any],
    quotation: Dict[str, Any],
    approval: Dict[str, Any]
) -> str:
    """Tạo mẫu email HTML gửi Trưởng phòng Kinh doanh đề nghị duyệt ngoại lệ."""
    triggers_html = "".join([f"<li style='color: #b91c1c; margin-bottom: 6px;'>{t}</li>" for t in approval.get("triggers", [])])
    
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 650px; margin: 0 auto; border: 1px solid #fecaca; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #dc2626; color: white; padding: 18px 20px;">
            <span style="background-color: #991b1b; padding: 3px 8px; border-radius: 4px; font-size: 11px; text-transform: uppercase; font-weight: bold;">Cần duyệt khẩn</span>
            <h3 style="margin: 8px 0 0; font-size: 18px;">[TRÌNH DUYỆT] Cơ hội bán hàng: {opp.get('opportunity_name')}</h3>
        </div>
        <div style="padding: 24px; color: #334155; line-height: 1.6;">
            <p>Kính gửi: <strong>Trưởng phòng Kinh doanh B2B</strong>,</p>
            <p>Hệ thống AI Agent phát hiện hồ sơ cơ hội <strong>{opp.get('opp_id')}</strong> có các tiêu chí vượt hạn mức tự quyết của NVKD:</p>
            
            <div style="background-color: #fef2f2; border: 1px solid #fee2e2; border-radius: 6px; padding: 12px 16px; margin: 15px 0;">
                <h4 style="margin: 0 0 8px; color: #991b1b;">LÝ DO CẦN TRƯỞNG PHÒNG DUYỆT:</h4>
                <ul style="margin: 0; padding-left: 20px;">
                    {triggers_html}
                </ul>
            </div>
            
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 13px;">
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 8px 0; color: #64748b;">Tổng giá niêm yết:</td>
                    <td style="padding: 8px 0; text-align: right; font-weight: bold;">{quotation.get('total_list_price', 0):,.0f} VNĐ</td>
                </tr>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 8px 0; color: #64748b;">Mức chiết khấu đề xuất:</td>
                    <td style="padding: 8px 0; text-align: right; font-weight: bold; color: #dc2626;">{quotation.get('applied_discount_pct', 0):.1f}% (-{quotation.get('discount_amount', 0):,.0f} VNĐ)</td>
                </tr>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 8px 0; color: #64748b;">Giá chào bán (Net):</td>
                    <td style="padding: 8px 0; text-align: right; font-weight: bold; color: #16a34a; font-size: 15px;">{quotation.get('net_quoted_price', 0):,.0f} VNĐ</td>
                </tr>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 8px 0; color: #64748b;">Biên lợi nhuận gộp:</td>
                    <td style="padding: 8px 0; text-align: right; font-weight: bold;">{quotation.get('gross_margin_pct', 0):.1f}% (Lãi gộp: {quotation.get('gross_profit', 0):,.0f} VNĐ)</td>
                </tr>
            </table>
            
            <p style="margin-top: 15px;">Trưởng phòng có thể xem xét phê duyệt hoặc chỉ đạo điều chỉnh trực tiếp trên Portal AI Agent.</p>
            <p style="font-size: 13px; color: #64748b;">NVKD phụ trách: <strong>{opp.get('sales_lead')}</strong></p>
        </div>
    </div>
    """
    return html

