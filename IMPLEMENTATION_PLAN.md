# IMPLEMENTATION PLAN & ROADMAP
# NEXUS ANALYTICS – UNIVERSAL AI-POWERED BUSINESS DATA ANALYTICS PLATFORM

## Phase 0: Project Discovery & Technical Blueprint (COMPLETED)
- Kiểm tra toàn bộ repository hiện tại (`c:\Users\X1-Gen8\Downloads\AI301_S4`) và bảo toàn nguyên trạng hệ thống **Thiên Minh B2B RFQ AI Agent** trên cổng `8000`.
- Khảo sát runtime thực tế (`Python 3.12.10`, `FastAPI`, `Pandas`, `NumPy`, `PyArrow`, `OpenPyXL`, `python-docx`, `SQLite3`).
- Thiết lập bộ 7 tài liệu chuẩn: `PRD.md`, `ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `API_SPECIFICATION.md`, `IMPLEMENTATION_PLAN.md`, `TESTING_STRATEGY.md`, `CHANGELOG.md`.

## Phase 1: Core Foundation, Database Schema & Security (IN PROGRESS -> COMPLETED)
- Xây dựng CSDL quan hệ chuẩn hóa 18 bảng (`nexus_analytics/db/database.py` + `postgres_schema.sql` + `docker-compose.yml`).
- Xây dựng dịch vụ xác thực, phân quyền RBAC (`ADMIN`, `ANALYST`, `VIEWER`), quản lý Workspace, Project và Audit Trail.
- Thiết lập cơ chế bảo mật chống CSV Injection, Path Traversal và Prompt Injection từ dữ liệu bảng.

## Phase 2: Vertical Slice 1 – Ingestion, Multi-Sheet Preview, Profiling & Quality Engine
- Xây dựng `IngestionService` hỗ trợ `.csv` (tự động nhận diện UTF-8/UTF-8-SIG/CP1258/Latin1 và delimiter), `.xlsx`/`.xls` đa sheet, màn hình Preview trước khi import và lưu trữ Parquet theo phiên bản (`v1`).
- Xây dựng `ProfilingService` trích xuất thống kê mô tả đầy đủ (`min`, `max`, `mean`, `median`, `mode`, `std`, `quantiles`, `skewness`) và nhận diện vai trò ngữ nghĩa của cột (`Semantic Role Detection`).
- Xây dựng `DataQualityEngine` chấm điểm 4 chiều (`Completeness`, `Uniqueness`, `Validity`, `Consistency`) theo trọng số cấu hình được.

## Phase 3: Controlled Data Cleaning & Dataset Versioning
- Xây dựng `CleaningEngine` hỗ trợ 2 chế độ: **Manual Cleaning** và **AI-Assisted Cleaning**.
- Cho phép Preview tác động trước khi áp dụng, tạo `DatasetVersion` mới (`v2`, `v3`...), lưu `CleaningHistory` và hỗ trợ **Undo/Restore** về phiên bản trước.

## Phase 4: Universal Analytics Engine (4 Levels) & Visualization Engine
- Xây dựng `BusinessContextLayer` quản lý KPI động theo ngành hoặc do người dùng tự định nghĩa công thức.
- Xây dựng `AnalyticsEngine` bao phủ 4 cấp độ:
  1. **Descriptive:** Summary Stats, Frequency Distribution, KPI Aggregation, Time Trend.
  2. **Diagnostic:** Pearson/Spearman Correlation Matrix, Group-by/Segmentation, Cross-tab, Period-over-Period Variance, Pareto 80/20, Welch's t-test & One-way ANOVA.
  3. **Predictive:** Multiple Linear Regression (OLS), K-Means++ Clustering, Anomaly Detection (IQR & Z-Score), Time-Series Forecasting (Trend + Seasonality + Confidence Interval).
  4. **Prescriptive:** ABC Analysis, RFM Customer Segmentation, Cohort Retention/Behavior Analysis, What-If Scenario Simulator.
- Xây dựng `VisualizationEngine` tự động sinh cấu hình **Apache ECharts** chuẩn BI và **Dashboard Builder**.

## Phase 5: AI Analytics Agent (`Goal → Planning → Action → Observation → Reflection → Response`)
- Xây dựng `AIAnalyticsAgentOrchestrator` với 10 công cụ kiểm soát chặt chẽ (`get_dataset_schema`, `profile_dataset`, `query_dataset`, `calculate_statistics`, `compare_periods`, `detect_outliers`, `calculate_correlation`, `generate_chart`, `run_forecast`, `generate_report`).
- Đảm bảo mọi câu trả lời đều kèm `Evidence Reference`, biểu đồ tương ứng, tách biệt rõ dữ kiện/tương quan/giả thuyết và khuyến nghị hành động.

## Phase 6: Executive/Analytical/Operational Reporting, UI/UX & Full QA Verification
- Xây dựng `ReportingService` xuất 3 loại báo cáo chuẩn 9 phần ra `.xlsx` và `.docx` (có Trang Bìa).
- Xây dựng giao diện **Premium Enterprise SaaS BI** (`nexus_analytics/static/index.html`) với 12 phân khu chức năng.
- Thực thi bộ kiểm thử tự động `tests/test_nexus_analytics.py` (Unit + Integration + E2E) trên nhiều bộ dữ liệu đa ngành.

