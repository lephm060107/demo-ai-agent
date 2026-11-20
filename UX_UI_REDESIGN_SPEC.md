# UX/UI AUDIT & INFORMATION ARCHITECTURE REDESIGN SPECIFICATION
# NEXUS ANALYTICS v2.1 – ENTERPRISE UX/UI & IA RESTRUCTURING

## 1. Phase 1: UX Audit & Các Vấn Đề Cốt Lõi Của Giao Diện Cũ

Qua rà soát toàn bộ giao diện và luồng người dùng hiện tại (`nexus_analytics/static/index.html`):

1. **Vấn đề về Kiến trúc Thông tin (Information Architecture):**
   - Thanh điều hướng cũ liệt kê 14 mục phẳng theo tên module kỹ thuật (`Overview`, `Projects & KPIs`, `Datasets & Versions`, `Data Explorer`, `Data Quality`, `Data Cleaning`, `B2B RFQ Workflow`, `B2B Catalog & Rules`, `Analytics Studio`...), khiến người dùng doanh nghiệp (CEO, Quản lý, Nhân viên kinh doanh) khó phân biệt đâu là luồng **Phân tích dữ liệu** và đâu là luồng **Vận hành báo giá B2B RFQ**.
2. **Vấn đề về Hành trình Người dùng (User Journey):**
   - Các trang thiếu thanh định hướng hành trình (Journey Stepper / Next-Step Guide) trả lời 4 câu hỏi: *Đang ở đâu? Trang này dùng để làm gì? Hành động chính là gì? Bước tiếp theo là gì?*
3. **Vấn đề về Hiển thị theo Ngữ cảnh (Progressive Disclosure):**
   - Các tham số kỹ thuật (mã băm SHA-256, JSON payload, quy tắc làm sạch thủ công, cấu hình JSON) hiển thị ngang hàng với các thao tác cơ bản.
   - Các hành động quan trọng (Phê duyệt/Từ chối vượt thẩm quyền HITL, Áp dụng làm sạch dữ liệu, Khôi phục phiên bản, Cập nhật quy tắc duyệt) chưa có hộp thoại xác nhận an toàn (Confirmation Modal).
4. **Vấn đề về Ngôn ngữ & Việt hóa (Localization):**
   - Còn trộn lẫn nhãn tiếng Anh và tiếng Việt trên thanh điều hướng (`Overview`, `Data Explorer`, `Analytics Studio`, `Settings & RBAC`, `Active Dataset & Version`, `Ask AI Agent`).

---

## 2. Phase 2: Bản Đồ Chuyển Đổi Kiến Trúc Thông Tin (6 Khu Vực Điều Hướng Cấp Cao)

Toàn bộ chức năng hiện có được bảo toàn 100% và tổ chức lại vào **6 Khu Vực Nghiệp Vụ Cấp Cao** hoàn toàn bằng tiếng Việt:

| Khu vực cấp cao (6 Nhóm) | Màn hình / Phân khu con (Sub-views) | Ánh xạ từ module cũ (Bảo toàn 100% tính năng & API) | Quyền truy cập tối thiểu |
| :--- | :--- | :--- | :--- |
| **1. TỔNG QUAN** | • Trung tâm điều hành ( KPI thật, Công việc cần xử lý, Hoạt động gần đây, Gợi ý AI) | `Overview` + tóm tắt từ `Activity` & `B2B RFQ` | `VIEWER` |
| **2. TRUNG TÂM DỮ LIỆU** | • **2.1. Kho dữ liệu & Tải lên** (Chọn file `.csv`/`.xlsx`, chọn Sheet, xem trước)<br>• **2.2. Khám phá & Cấu trúc** (Xem bảng, lọc, xác nhận vai trò cột)<br>• **2.3. Kiểm tra chất lượng** (Điểm 4 chiều + tùy chỉnh trọng số)<br>• **2.4. Làm sạch & Phiên bản** (Đề xuất AI, làm sạch thủ công, khôi phục `v1..vN`) | `Datasets & Versions` + `Data Explorer` + `Data Quality` + `Data Cleaning` | Xem: `VIEWER`<br>Sửa/Nhập: `ANALYST` |
| **3. PHÂN TÍCH & THÔNG MINH KINH DOANH** | • **3.1. Phân tích & Dự báo** (18 phương pháp 4 cấp độ + Tùy chọn tham số nâng cao)<br>• **3.2. Dự án & Chỉ số KPI** (Quản lý dự án & công thức KPI)<br>• **3.3. Bảng điều khiển (Dashboard)** (Biểu đồ đã ghim)<br>• **3.4. Báo cáo doanh nghiệp** (Báo cáo Điều hành, Phân tích, Vận hành `.xlsx`/`.docx`) | `Analytics Studio` + `Projects & KPIs` + `Dashboards` + `Reports` | Xem/Phân tích: `VIEWER`<br>Tạo KPI/Báo cáo: `ANALYST` |
| **4. VẬN HÀNH KINH DOANH (B2B RFQ)** | • **4.1. Thẩm định & Báo giá B2B RFQ** (Quy trình 6 Giai đoạn – 12 Bước – 5 Cổng, BoQ, Phê duyệt HITL, Trang bìa A4, 6 nhóm đầu ra)<br>• **4.2. Danh mục, Năng lực & Quy tắc duyệt** (4 bảng Master Data: Sản phẩm, Năng lực, Chính sách, Lịch kỹ sư + Cấu hình quy tắc) | `B2B RFQ Workflow` + `B2B Catalog & Rules` | Xem/Chạy thử: `VIEWER`<br>Cập nhật danh mục/Duyệt: `ANALYST` / `ADMIN` |
| **5. TRỢ LÝ AI** | • **5.1. Trợ lý Phân tích & Nghiệp vụ** (Hỏi đáp ngôn ngữ tự nhiên, Chu trình 6 bước, Bằng chứng truy vết, Lịch sử hội thoại)<br>• **5.2. Trợ lý AI theo ngữ cảnh** (Thanh gợi ý AI nhúng trực tiếp ở từng khu vực) | `AI Analyst` + Contextual AI Banners | `VIEWER` |
| **6. QUẢN TRỊ HỆ THỐNG** | • **6.1. Không gian làm việc & Phân quyền** (Người dùng, Vai trò RBAC, Workspace)<br>• **6.2. Nhật ký hoạt động & Cài đặt** (Nhật ký kiểm toán `audit_logs`, Cài đặt hệ thống) | `Activity History` + `Settings & RBAC` | Xem: `VIEWER`<br>Quản trị: `ADMIN` |

---

## 3. Phase 3: Hệ Thống Thiết Kế (Design System Tokens)

- **Phong cách chủ đạo:** Minimalist Enterprise SaaS + Modern BI (Linear / Stripe / Notion inspired).
- **Bảng màu có mục đích (Purposeful Color Tokens):**
  - Nền chính (`Surface Canvas`): `#F8FAFC` (Slate 50), Thẻ nội dung (`Card Surface`): `#FFFFFF`, Đường viền mảnh (`Border`): `#E2E8F0` (1px solid, hạn chế card lồng card).
  - Màu chữ (`Typography`): Tiêu đề `#0F172A`, Nội dung chính `#334155`, Chữ phụ/nhãn `#64748B`.
  - Màu hành động chính (`Primary Action`): `#0F172A` (Slate 900) và `#2563EB` (Enterprise Blue).
  - Màu nhấn Trợ lý AI (`AI Accent`): `#6D28D9` (Violet 700), nền nhạt `#F5F3FF`.
  - Màu trạng thái ngữ nghĩa (`Semantic Status`): Đạt/Tích cực `#059669` (Emerald), Cảnh báo/Chờ duyệt `#D97706` (Amber), Lỗi/Chặn cổng `#DC2626` (Rose).
- **Bố cục chuẩn của mọi màn hình (4-Question Page Template):**
  1. **Thanh định vị & Ngữ cảnh (Breadcrumb & Context Header):** Cho biết người dùng đang ở khu vực nào và mục đích của trang.
  2. **Thanh dẫn dắt hành trình (User Journey Stepper & Next Step CTA):** Chỉ rõ vị trí hiện tại trong chuỗi quy trình và nút chuyển sang bước kế tiếp.
  3. **Khu vực thao tác chính (Primary Workspace):** Hiển thị gọn gàng thông tin cốt lõi.
  4. **Khu vực tùy chọn chuyên sâu (Progressive Disclosure Drawer/Accordion):** Ẩn mặc định các tham số kỹ thuật nâng cao, chỉ mở khi chuyên viên phân tích nhấp vào.

