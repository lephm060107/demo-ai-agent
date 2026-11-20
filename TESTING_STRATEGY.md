# TESTING & QUALITY ASSURANCE STRATEGY
# NEXUS ANALYTICS – UNIVERSAL AI-POWERED BUSINESS DATA ANALYTICS PLATFORM

## 1. Nguyên Tắc Kiểm Thử (Zero-Unverified-Claim Policy)
- Mọi công thức thống kê, điểm chất lượng dữ liệu, phép biến đổi làm sạch và kết quả phân tích của AI Agent đều phải được kiểm thử đối chiếu với **Expected Mathematical Results** xác định trước.
- Không đánh dấu bất kỳ module nào là hoàn thành nếu bài kiểm thử tự động chưa chạy thành công với mã thoát `0`.

## 2. Ba Cấp Độ Kiểm Thử Tự Động (`tests/test_nexus_analytics.py`)

### 2.1. Unit Testing
- **Statistical & Mathematical Verification:** Kiểm tra độ chính xác của `mean`, `median`, `std`, `quantiles`, hệ số tương quan Pearson `r`, hồi quy tuyến tính `R²` & hệ số góc, kiểm định `t-test`, phân tích `Pareto 80/20`, phân nhóm `ABC` và `RFM` trên tập dữ liệu mẫu có đáp án toán học biết trước.
- **Data Quality Formula Verification:** Kiểm tra công thức tính điểm `Completeness`, `Uniqueness`, `Validity`, `Consistency` và khả năng thay đổi trọng số cấu hình.
- **Data Cleaning & Immutability Verification:** Kiểm tra xử lý thiếu dữ liệu, xóa bản ghi trùng lặp, chuẩn hóa chuỗi/ngày tháng, bảo toàn ngoại lệ nghiệp vụ hợp lệ và tạo `DatasetVersion` mới mà không làm thay đổi `Version 1`.
- **RBAC & Security Sanitization:** Kiểm tra phân quyền `ADMIN` vs `ANALYST` vs `VIEWER`, chặn CSV Formula Injection (`=CMD|...`) và chặn Prompt Injection nhúng trong ô dữ liệu.

### 2.2. Integration Testing
- Kiểm tra luồng đọc file thực tế (`.csv` tiếng Việt có dấu, `.xlsx` nhiều worksheet), lưu trữ Parquet và ghi nhận đầy đủ vào 18 bảng CSDL.
- Kiểm tra `AIAnalyticsAgentOrchestrator` thực sự gọi các backend tools (`get_dataset_schema`, `calculate_statistics`, `compare_periods`, `calculate_correlation`, `detect_outliers`, `run_forecast`) và trả về `Evidence Reference` khớp với số liệu tính toán.

### 2.3. End-to-End (E2E) HTTP Workflow Testing
- Kiểm tra trọn vẹn hành trình người dùng qua HTTP API:
  `Login → Tạo Workspace/Project → Upload File (Preview & Chọn Sheet) → Import & Profiling → Kiểm tra Data Quality → Preview & Apply Data Cleaning (tạo v2) → Rollback/Undo test → Chạy 4 cấp độ Analytics → Lưu Widget vào Dashboard → Chat with Data (AI Agent) → Xuất Báo Cáo Executive/Analytical/Operational (.xlsx & .docx)`.

## 3. Bộ Dữ Liệu Kiểm Thử Đa Kịch Bản
1. **Multi-Domain Clean & Dirty Retail/E-Commerce Dataset (Tiếng Việt có dấu):** Chứa doanh thu, chi phí, lợi nhuận, số lượng, ngày giao dịch, mã khách hàng, danh mục sản phẩm, kênh bán hàng; cố tình cài đặt sẵn bản ghi trùng lặp, giá trị thiếu (`NULL`), khoảng trắng thừa, ngày tháng không đồng nhất và 1 đơn hàng B2B giá trị lớn hợp lệ (để kiểm tra phân biệt Outlier hợp lệ vs lỗi dữ liệu).
2. **Multi-Sheet Enterprise Excel Workbook (`.xlsx`):** Gồm nhiều sheet (`Sales_2026`, `Marketing_Campaigns`, `Finance_Ledger`) để kiểm thử tính năng chọn sheet và phân tích đa lĩnh vực.

