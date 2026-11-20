# PRODUCT REQUIREMENTS DOCUMENT (PRD)
# NEXUS ANALYTICS – UNIVERSAL AI-POWERED BUSINESS DATA ANALYTICS PLATFORM

## 1. Tầm Nhìn & Triết Lý Sản Phẩm
**NEXUS ANALYTICS** là nền tảng phân tích dữ liệu doanh nghiệp đa lĩnh vực (Universal Business Data Analytics Platform) kết hợp giữa **Data Engineering**, **Statistical & ML Analytics**, **Interactive BI Visualization** và **Autonomous AI Analytics Agent**.

- **Chuỗi giá trị cốt lõi (Core Value Pipeline):**
  `Raw Data → Data Understanding → Data Quality → Data Processing → Data Analytics → Business Insights → Intelligent Recommendations → Business Decisions`
- **Định vị kép (Dual-Experience):**
  1. **No-Code Analytics (Business Users):** CEO, Giám đốc Khối, Trưởng bộ phận (Sales, Marketing, Finance, HR, Ops, Supply Chain) tải dữ liệu, xem điểm chất lượng, nhận gợi ý làm sạch, hỏi đáp bằng ngôn ngữ tự nhiên (Chat with Data) và xuất báo cáo điều hành.
  2. **Advanced Analytics (Data/Business Analysts):** Kiểm soát biến số, tham số kiểm định thống kê, công thức KPI tùy chỉnh, ma trận tương quan, phân tích Pareto/ABC/RFM/Cohort, hồi quy, dự báo chuỗi thời gian và tùy biến Dashboard.

---

## 2. Đối Tượng Sử Dụng & Phân Quyền (RBAC)
| Vai trò (Role) | Quyền hạn trong Workspace & Project |
| :--- | :--- |
| **Owner / Admin** | Quản trị Workspace, thành viên, cấu hình AI Provider, toàn quyền tạo/xóa Project, Dataset, Dashboard, Report và xem Audit Logs. |
| **Analyst / Editor** | Tạo Project, tải lên Dataset, chạy Profiling, phê duyệt Data Cleaning (tạo Dataset Version mới), chạy Analytics, cấu hình KPI, tạo Dashboard & Report. |
| **Viewer (Executive/Stakeholder)** | Xem Project, Dataset Preview, kết quả Profiling/Quality, tương tác Dashboard, đặt câu hỏi cho AI Analyst (chỉ đọc) và tải báo cáo. |

---

## 3. Yêu Cầu Chức Năng Cốt Lõi (Functional Requirements)

### FR-01: Quản lý Người dùng, Workspace & Project
- Đăng ký, đăng nhập (JWT/Session token), phân tách dữ liệu theo `workspace_id` và `project_id`.
- Mỗi Project quản lý tập hợp các Dataset, Dataset Versions, Profiling Runs, Cleaning History, Analysis Runs, Dashboards, AI Conversations và Reports.

### FR-02: Data Ingestion & Multi-Format Validation
- Hỗ trợ tải lên `.csv`, `.xlsx`, `.xls` (kéo thả hoặc chọn file).
- Kiểm tra kích thước file, phần mở rộng, MIME type, cấu trúc bảng, tự động phát hiện bảng mã (`utf-8`, `utf-8-sig`, `cp1258`, `latin1`) và dấu phân cách CSV (`,`, `;`, `\t`, `|`).
- Hỗ trợ file Excel nhiều sheet: liệt kê danh sách sheet kèm số dòng/cột và cho phép chọn sheet cần phân tích.
- Cung cấp chế độ **Preview trước khi Import** và cam kết **bất biến dữ liệu gốc (Raw File Immutability - Version 1)**.

### FR-03: Data Understanding, Profiling & Semantic Role Detection
- Tự động phân tích từng cột: kiểu dữ liệu vật lý (`numeric`, `categorical`, `datetime`, `boolean`, `text`), số bản ghi, số giá trị duy nhất (`unique_count`), tỷ lệ thiếu (`missing_pct`), số bản ghi trùng lặp.
- Thống kê chi tiết cho biến định lượng: `min`, `max`, `mean`, `median`, `mode`, `std`, `variance`, `q25`, `q50`, `q75`, `iqr`, `skewness`.
- **Semantic Business Role Detection:** Tự động nhận diện vai trò nghiệp vụ của cột (`timestamp/date`, `revenue/amount`, `cost/expense`, `profit/margin`, `quantity/volume`, `customer_id`, `product/category`, `channel/region`, `identifier`) dựa trên tên cột, kiểu dữ liệu, độ phân tán (cardinality) và mẫu giá trị. Cho phép người dùng xác nhận hoặc ghi đè vai trò.

### FR-04: Configurable Data Quality Engine
- Đánh giá 4 chiều chất lượng với trọng số có thể cấu hình (mặc định: Completeness `35%`, Uniqueness `20%`, Validity `25%`, Consistency `20%`):
  $$\text{Quality Score} = w_C \cdot C + w_U \cdot U + w_V \cdot V + w_S \cdot S$$
- Chỉ rõ từng vấn đề (cột bị ảnh hưởng, số dòng lỗi, vị trí mẫu, mức độ `HIGH`/`MEDIUM`/`LOW`, đề xuất khắc phục).
- **Nguyên tắc trung thực:** Không tuyên bố độ chính xác thực tế (ground-truth accuracy) nếu không có nguồn đối chiếu độc lập.

### FR-05: Data Cleaning Engine & Version Control
- Hỗ trợ cả **Manual Cleaning** và **AI-Assisted Cleaning Recommendations**.
- Các thao tác làm sạch được kiểm soát:
  - Xử lý giá trị thiếu (`fill_median`, `fill_mean`, `fill_mode`, `fill_constant`, `drop_rows`).
  - Xử lý bản ghi trùng lặp (`drop_duplicates`).
  - Chuẩn hóa chuỗi & khoảng trắng (`trim_whitespace`, `normalize_case`).
  - Chuẩn hóa kiểu số & ngày tháng (`parse_numeric`, `parse_datetime`).
  - Xử lý ngoại lệ (`cap_iqr_outliers`, `flag_outliers` — mặc định đánh dấu hoặc giới hạn biên thay vì tự ý xóa quan sát hợp lệ).
- **Preview & Phê duyệt trước khi áp dụng:** Tạo `DatasetVersion` mới (`v2`, `v3`, ...), lưu trữ dưới dạng Parquet/Snapshot, ghi `CleaningHistory` và hỗ trợ **Undo / Rollback** về bất kỳ phiên bản nào.

### FR-06: Universal Analytics Engine (4 Cấp Độ) & Business Context Layer
- **Business Context Layer:** Cho phép định nghĩa và lưu KPI tùy chỉnh (tên KPI, công thức tính hoặc cột nguồn, hàm tổng hợp, đơn vị, chiều phân tích). Tự động gợi ý KPI theo ngữ cảnh ngành (Sales, Marketing, Finance, HR, Operations).
- **4 Cấp độ phân tích (có kiểm tra điều kiện áp dụng trước khi chạy):**
  1. **Descriptive Analytics:** Thống kê mô tả, tổng hợp KPI, phân phối tần suất, xu hướng theo thời gian (Trend Analysis).
  2. **Diagnostic Analytics:** Ma trận tương quan Pearson/Spearman, Group-by & Segmentation, Cross-tabulation, Phân tích phương sai/biến động kỳ này so với kỳ trước (Period-over-Period Variance), Pareto Analysis (80/20), Kiểm định giả thuyết (Two-sample t-test / ANOVA).
  3. **Predictive Analytics:** Hồi quy tuyến tính đa biến (Linear Regression), Phân cụm khách hàng/sản phẩm (K-Means Clustering), Phát hiện bất thường (Z-Score & IQR Anomaly Detection), Dự báo chuỗi thời gian (Time-Series Trend + Seasonal Forecasting kèm khoảng tin cậy).
  4. **Prescriptive Analytics:** Phân tích ABC (Inventory/Revenue Prioritization), Phân tích RFM (Recency - Frequency - Monetary), Kịch bản What-If / Scenario Simulation (thay đổi giá, sản lượng, chi phí, tỷ lệ chuyển đổi) và Khuyến nghị hành động có định lượng tác động.

### FR-07: Visualization Engine & Dashboard Builder
- Tự động chọn loại biểu đồ Apache ECharts phù hợp (`Bar`, `Line`, `Pie/Donut`, `Scatter`, `Histogram`, `Boxplot`, `Heatmap`, `Pareto Dual-Axis`).
- Mọi biểu đồ đều có tiêu đề, đơn vị đo, nhãn trục, nguồn `dataset_version`, khoảng thời gian và chú giải.
- **Dashboard Builder:** Lưu các KPI Card và Chart vào Dashboard của Project, hỗ trợ lọc và chia sẻ.

### FR-08: AI Analytics Agent (`Goal → Planning → Action → Observation → Reflection → Response`)
- Điều phối qua các công cụ backend có kiểm soát: `get_dataset_schema`, `profile_dataset`, `query_dataset`, `calculate_statistics`, `compare_periods`, `detect_outliers`, `calculate_correlation`, `generate_chart`, `run_forecast`, `generate_report`.
- Mọi câu trả lời trong **Chat with Data** đều tách biệt rõ:
  1. **Verified Facts & Quantitative Results** (kèm `Evidence Reference`: `dataset_version`, công cụ đã gọi, cột sử dụng, số bản ghi).
  2. **Analytical Interpretation / Hypotheses** (không đánh đồng tương quan với nhân quả).
  3. **Actionable Business Recommendations** (vấn đề, bằng chứng, mức độ ảnh hưởng, hành động, KPI theo dõi, giới hạn).

### FR-09: Executive, Analytical & Operational Reporting
- Tạo 3 loại báo cáo chuẩn doanh nghiệp: **Executive Report**, **Analytical Report**, **Operational Report**.
- Đầy đủ 9 mục: Executive Summary, Dataset Information, Data Quality Assessment, Key Metrics, Analytical Findings, Visualizations, Recommendations, Methodology và Limitations.
- Hỗ trợ xuất file **Excel (`.xlsx`)**, **Word/Printable PDF Report (`.docx` / `.html`)** và **JSON**.

