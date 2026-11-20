# API SPECIFICATION
# NEXUS ANALYTICS – UNIVERSAL AI-POWERED BUSINESS DATA ANALYTICS PLATFORM

Base URL: `http://127.0.0.1:8001` (OpenAPI Interactive Docs: `http://127.0.0.1:8001/docs`)

## 1. Authentication, Workspace & Project Management
- **`POST /api/v1/auth/login`**: Đăng nhập và nhận phiên làm việc + thông tin Workspace/Role.
- **`GET /api/v1/workspaces`**: Liệt kê danh sách Workspace mà người dùng hiện tại có quyền truy cập.
- **`POST /api/v1/projects`**: Tạo Project phân tích mới gắn với `workspace_id` và `business_domain`.
- **`GET /api/v1/projects/{project_id}`**: Lấy chi tiết Project, danh sách Dataset, KPI definitions, Dashboards và Reports.
- **`POST /api/v1/projects/{project_id}/kpis`**: Định nghĩa hoặc xác nhận KPI trong Business Context Layer (`name`, `formula_type`, `column`, `secondary_column`, `unit`).

## 2. Data Ingestion, Multi-Sheet Inspection & Versioning
- **`POST /api/v1/datasets/inspect-upload`**: Tải file `.csv`, `.xlsx`, `.xls` vào vùng staging để kiểm tra dung lượng, MIME, encoding, delimiter, danh sách worksheet và trả về `Preview` (20 dòng đầu + cấu trúc cột) trước khi import chính thức.
- **`POST /api/v1/datasets/confirm-import`**: Xác nhận import sheet đã chọn vào Project, lưu bản gốc bất biến (`Version 1`) sang Parquet, kích hoạt tự động **Data Understanding & Profiling Engine** và **Data Quality Engine**.
- **`GET /api/v1/datasets/{dataset_id}`**: Lấy thông tin Dataset, danh sách các `DatasetVersion`, lịch sử làm sạch và Profiling Run hiện hành.
- **`GET /api/v1/datasets/{dataset_id}/rows`**: Truy vấn phân trang và lọc dữ liệu của `version_id` hiện hành cho màn hình **Data Explorer**.
- **`POST /api/v1/datasets/{dataset_id}/columns/roles`**: Người dùng xác nhận hoặc điều chỉnh `semantic_role` của từng cột.

## 3. Data Quality & Controlled Data Cleaning
- **`POST /api/v1/datasets/{dataset_id}/quality-config`**: Cập nhật trọng số công thức tính điểm Data Quality (`completeness`, `uniqueness`, `validity`, `consistency`) và tính lại điểm.
- **`GET /api/v1/datasets/{dataset_id}/cleaning-recommendations`**: AI phân tích danh sách lỗi chất lượng và đề xuất chuỗi quy tắc làm sạch (`CleaningRule`) kèm giải thích nghiệp vụ (phân biệt lỗi dữ liệu vs ngoại lệ hợp lệ).
- **`POST /api/v1/datasets/{dataset_id}/clean/preview`**: Xem trước kết quả làm sạch (`rows_before`, `rows_after`, mẫu dữ liệu thay đổi) mà chưa ghi đè.
- **`POST /api/v1/datasets/{dataset_id}/clean/apply`**: Phê duyệt và áp dụng quy tắc làm sạch -> tạo `DatasetVersion` mới (`v2`, `v3`...), tự động chạy lại Profiling & Quality Score trên phiên bản mới.
- **`POST /api/v1/datasets/{dataset_id}/versions/{version_id}/restore`**: Undo / Rollback Dataset về một phiên bản trước đó.

## 4. Universal Analytics Engine (4 Levels) & Visualization
- **`POST /api/v1/analytics/run`**: Thực thi phương pháp phân tích trên `dataset_version_id`:
  - `DESCRIPTIVE`: `summary_stats`, `frequency_distribution`, `kpi_summary`, `trend_analysis`
  - `DIAGNOSTIC`: `correlation_matrix`, `group_aggregation`, `cross_tabulation`, `period_variance`, `pareto_analysis`, `hypothesis_test`
  - `PREDICTIVE`: `linear_regression`, `kmeans_clustering`, `anomaly_detection`, `time_series_forecast`
  - `PRESCRIPTIVE`: `abc_analysis`, `rfm_analysis`, `cohort_analysis`, `what_if_scenario`
  Mỗi response đều trả về: `validation_checks`, `formula_used`, `quantitative_results`, `interpretation`, `echarts_option` và `evidence_reference`.

## 5. AI Analytics Agent (`Chat with Data`)
- **`POST /api/v1/ai/chat`**: Gửi câu hỏi ngôn ngữ tự nhiên tới AI Analytics Agent.
  - Response trả về chu trình 6 bước:
    1. `goal`: Mục tiêu câu hỏi đã nhận diện.
    2. `plan`: Kế hoạch phân tích và các cột/biến được chọn.
    3. `tool_calls`: Danh sách công cụ backend đã thực sự gọi (`get_dataset_schema`, `calculate_statistics`, `compare_periods`, `calculate_correlation`, `detect_outliers`, `run_forecast`, `generate_chart`...).
    4. `observations`: Kết quả định lượng thu được từ các tool.
    5. `reflection`: Kiểm chứng độ tin cậy, cỡ mẫu, lưu ý không suy diễn nhân quả từ tương quan.
    6. `response`: Gồm `verified_facts`, `hypotheses`, `recommendations`, `echarts_option` và `evidence_references`.

## 6. Dashboards, Reports & Audit Logs
- **`POST /api/v1/dashboards`** & **`POST /api/v1/dashboards/{dashboard_id}/widgets`**: Tạo Dashboard và ghim KPI/Chart vào Dashboard.
- **`POST /api/v1/reports/generate`**: Sinh báo cáo **Executive**, **Analytical**, hoặc **Operational** (9 phần chuẩn) và xuất file `.xlsx` / `.docx`.
- **`GET /api/v1/reports/{report_id}/download/{format}`**: Tải báo cáo dưới dạng `xlsx` hoặc `docx`.
- **`GET /api/v1/audit-logs`**: Truy xuất nhật ký hoạt động và kiểm toán toàn hệ thống.

