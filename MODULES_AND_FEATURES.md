# MODULES & FEATURES MATRIX
# BẢNG ĐỐI CHIẾU & HỢP NHẤT TÍNH NĂNG (NEXUS ANALYTICS × THIEN MINH B2B RFQ)

## 1. Bảng Đối Chiếu 6 Nhóm Tính Năng Trước & Sau Hợp Nhất

| STT | Hạng mục / Tính năng | Nguồn gốc trước hợp nhất | Phân loại xử lý | Vị trí trong kiến trúc NEXUS ANALYTICS thống nhất |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **Master Workflow 6 Phases – 12 Steps – 5 Decision Gates** | Chỉ có trong Thiên Minh B2B RFQ | Tái sử dụng & Tích hợp DB | `engine/orchestrator.py`, `engine/decision_engine.py`, `nexus_analytics/services/rfq_workflow_service.py` |
| 2 | **4 Custom Skills (`Intake`, `SolutionMatcher`, `CommercialPricer`, `ProposalGovernance`)** | Chỉ có trong Thiên Minh B2B RFQ | Tái sử dụng trực tiếp | `skills/skill_01..04_*.py` |
| 3 | **4 Connected Tools (`DocumentReader`, `DataLookup`, `PricingCalculator`, `PolicyChecker`) + `ToolTracer`** | Chỉ có trong Thiên Minh B2B RFQ | Tái sử dụng trực tiếp | `tools/*.py` |
| 4 | **Human-in-the-loop (HITL) Manager Approval & Tờ trình vượt thẩm quyền** | Chỉ có trong Thiên Minh B2B RFQ | Hợp nhất vào DB & UI | Bảng `rfq_hitl_approvals` + Tab `B2B RFQ Workflow` |
| 5 | **Xuất Báo giá BoQ (`.xlsx`) & Hồ sơ Đề xuất (`.docx`) kèm Trang Bìa** | Chỉ có trong Thiên Minh B2B RFQ | Tái sử dụng trực tiếp | `agent_engine/export_generator.py` + Modal `#modalCoverPage` |
| 6 | **Configurable Business Rules (`config/business_rules.json`)** | Chỉ có trong Thiên Minh B2B RFQ | Hợp nhất vào UI & API | `/api/v1/rfq/rules` (`/api/rules`) + Tab `B2B Catalog & Rules` |
| 7 | **Universal Multi-Format Ingestion, Sheet Picker & Versioned Parquet Store** | Đã có trong NEXUS ANALYTICS | Giữ nguyên & Mở rộng | `nexus_analytics/services/ingestion_service.py` (tự động nạp thêm `DanhMuc_SanPham` của Thiên Minh làm Dataset) |
| 8 | **Data Profiling, Semantic Role Detection & Business Context KPI Layer** | Đã có trong NEXUS ANALYTICS | Giữ nguyên | `nexus_analytics/services/profiling_service.py` |
| 9 | **Configurable 4-Dimension Data Quality Engine & Controlled Cleaning (`v1..vN`, Rollback)** | Đã có trong NEXUS ANALYTICS | Giữ nguyên | `nexus_analytics/services/quality_engine.py`, `cleaning_engine.py` |
| 10 | **4-Level Universal Analytics Engine (18 phương pháp thống kê & ML) + Apache ECharts** | Đã có trong NEXUS ANALYTICS | Giữ nguyên | `nexus_analytics/services/analytics_engine.py` |
| 11 | **AI Analytics Agent (`Goal → Plan → Action → Observation → Reflection → Response`)** | Đã có trong NEXUS ANALYTICS | Giữ nguyên | `nexus_analytics/services/ai_agent_orchestrator.py` |
| 12 | **FastAPI Backend Server & Web UI Entrypoint** | Trùng lặp (`server.py` vs `nexus_server.py`, 2 file `index.html`) | **Hợp nhất (Group C)** | Hợp nhất vào một `server.py` duy nhất và một giao diện `nexus_analytics/static/index.html` duy nhất |
| 13 | **Prototype Streamlit cũ (`app.py`) & 6 file `agent_engine/*` đời đầu** | Dư thừa / Đã bị thay thế bởi `engine/` + `skills/` + `tools/` | **Loại bỏ an toàn (Group D)** | Đã xóa sau khi kiểm tra 0 file active tham chiếu |

---

## 2. Danh Sách 14 Phân Khu Giao Diện Thống Nhất (`nexus_analytics/static/index.html`)

1. **Overview:** Tổng quan chuỗi giá trị dữ liệu, 4 thẻ KPI, biểu đồ Pareto tự động và danh sách vai trò ngữ nghĩa.
2. **Projects & KPIs:** Quản lý dự án đa ngành và công thức KPI tùy chỉnh (Business Context Layer).
3. **Datasets & Versions:** Tải lên `.csv`/`.xlsx` đa sheet, xem trước (Preview) trước khi import, quản lý phiên bản Parquet và khôi phục (Rollback).
4. **Data Explorer:** Xem bảng dữ liệu chi tiết và xác nhận vai trò ngữ nghĩa (`Semantic Role`) của từng cột.
5. **Data Quality:** Bảng điểm chất lượng 4 chiều (`Completeness`, `Uniqueness`, `Validity`, `Consistency`), giải thích công thức và danh sách lỗi.
6. **Data Cleaning:** Làm sạch dữ liệu tự động (AI-Assisted) và thủ công (Manual), xem trước tác động và tạo phiên bản mới.
7. **B2B RFQ Workflow (6 Phases - 5 Gates):** Trung tâm điều hành quy trình xử lý hồ sơ mời thầu B2B Thiên Minh, 5 cổng quyết định, đối soát kỹ thuật, bảng BoQ, phê duyệt HITL, 6 nhóm đầu ra, nhật ký 12 bước và bằng chứng gọi công cụ.
8. **B2B Catalog & Rules:** Quản lý 4 sheet Master Data (`DanhMuc_SanPham`, `NangLuc_TrienKhai`, `ChinhSach_ChuyenDuyet`, `Lich_TrienKhai_KhaDung`), đồng bộ Google Sheets/Excel và chỉnh sửa `business_rules.json`.
9. **Analytics Studio:** Thực thi 18 phương pháp phân tích thuộc 4 cấp độ (`Descriptive`, `Diagnostic`, `Predictive`, `Prescriptive`) và ghim biểu đồ vào Dashboard.
10. **AI Analyst (`Chat with Data`):** Hỏi đáp ngôn ngữ tự nhiên có kiểm chứng công cụ, đính kèm `Evidence Reference` và chống bịa đặt số liệu.
11. **Dashboards:** Bảng điều khiển hiển thị các biểu đồ ECharts đã ghim.
12. **Reports:** Xuất 3 loại báo cáo chuẩn 9 phần (`Executive`, `Analytical`, `Operational`) ra `.xlsx` và `.docx`.
13. **Activity History:** Nhật ký kiểm toán (`audit_logs`) ghi nhận cả hoạt động phân tích dữ liệu lẫn các lần chạy B2B RFQ.
14. **Settings & RBAC:** Chuyển đổi vai trò `ADMIN` / `ANALYST` / `VIEWER` và kiểm tra trạng thái bảo mật.

