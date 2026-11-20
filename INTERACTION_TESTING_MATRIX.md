# INTERACTION TESTING MATRIX & TRANSLATION QA REPORT – NEXUS ANALYTICS v2.3

## 1. Báo cáo Kiểm định Dịch thuật & Đa ngôn ngữ (Translation QA Report – Part 4.5)

| Tiêu chí Kiểm định (Part 4 Requirements) | Kết quả | Chi tiết Kiểm chứng Thực tế |
|---|---|---|
| **1. Vị trí Language Switcher** | **PASS (100%)** | Đặt cố định tại góc trên bên trái của Sidebar (`#globalLangSwitcher`), ngay bên dưới logo thương hiệu **NEXUS ANALYTICS**, hiển thị tên đầy đủ: `🇻🇳 Tiếng Việt`, `🇬🇧 English`, `🇯🇵 日本語`. Khi thu gọn Sidebar vẫn giữ nút chuyển ngôn ngữ nhanh (`#collapsedLangCode`). |
| **2. Độ phủ từ điển 3 ngôn ngữ (`I18N.vi`, `I18N.en`, `I18N.ja`)** | **PASS (423 / 423 keys)** | 100% đồng bộ khóa dịch thuật: `VI = 423 keys`, `EN = 423 keys`, `JA = 423 keys`. Độ phủ `data-i18n`, `data-i18n-placeholder`, `data-i18n-title`, `data-i18n-label` trên DOM đạt **100% (`MissingDOM = 0`)**. |
| **3. Không trộn lẫn ngôn ngữ (Zero Mixed-Language Rule)** | **PASS (100%)** | Khi chọn Tiếng Việt, Tiếng Anh hoặc Tiếng Nhật, toàn bộ Menu, Header, 8 bước hướng dẫn, 10 mục kiểm tra chất lượng (`validation_checklist`), gợi ý làm sạch (`rationale_i18n`), diễn giải phân tích 5 phần (`structured_explanation_i18n`), thẻ nhận định AI và thông báo đều chuyển sang duy nhất ngôn ngữ đang chọn. |
| **4. Định dạng Số, Ngày tháng & Tiền tệ theo Locale** | **PASS (100%)** | Tự động định dạng qua `Intl.NumberFormat` / `toLocaleString` và `toLocaleDateString` theo `vi-VN`, `en-US`, `ja-JP` kèm đơn vị tiền tệ (`VND`, `USD`, `JPY`). |
| **5. Lưu trữ bền vững (Persistence)** | **PASS (100%)** | Lưu đồng thời vào `localStorage` (`nexus_lang`) và bảng `users.preferred_language` qua `POST /api/v1/user/preferences` (và alias `/api/v1/users/preferences`). |

---

## 2. Ma trận Kiểm thử Tương tác Giao diện & Nghiệp vụ (Interaction Testing Matrix – Part 6)

| Khu vực (6 Navigation Areas) | Thành phần / Nút bấm / Biểu mẫu | Handler / API Endpoint | Trạng thái |
|---|---|---|---|
| **Header & Sidebar** | Chuyển đổi ngôn ngữ (`🇻🇳 Tiếng Việt` / `🇬🇧 English` / `🇯🇵 日本語`) | `setLanguage(lang)` → `POST /api/v1/user/preferences` | **PASS** |
| **Header & Sidebar** | Thu gọn / Mở rộng Sidebar (`#sidebarToggleBtn`) | `toggleSidebarCollapse()` + `applySidebarState()` | **PASS** |
| **Header & Sidebar** | Tìm kiếm nhanh toàn cục (`#globalSearchInput`) & lọc menu (`#sidebarFeatureFilter`) | `runGlobalSearch(val)` / `filterSidebarFeatures(val)` | **PASS** |
| **Header & Sidebar** | Hồ sơ cá nhân trung lập (Không tự gán chức danh Analyst/CEO hay ép chọn RBAC) | `renderUserIdentityUI()` (Không có `#headerRoleSelect`) | **PASS** |
| **Thanh 8 Bước Phân Tích** | `1. Tải dữ liệu → 2. Hiểu dữ liệu → 3. Kiểm tra → 4. Làm sạch → 5. Phân tích → 6. Nhận định AI → 7. Báo cáo → 8. Ra quyết định` | `navigateToById(viewId)` + `updatePageContextBanner(viewId)` | **PASS** |
| **1. Tổng quan (`#view-overview`)** | Tiêu đề trung lập `"Biến dữ liệu thành quyết định."`, Tải file Excel/CSV hoặc Thử bộ dữ liệu minh họa | `handleFileUpload(file)` / `trySampleDatasetOnHome()` | **PASS** |
| **1. Tổng quan (`#view-overview`)** | 4 Thao tác nhanh (`Kiểm tra dữ liệu`, `Phân tích dữ liệu`, `Hỏi trợ lý AI`, `Tạo báo cáo`) + 4 Thẻ nhận định AI | `navigateToById(...)` + `loadOverviewChart(...)` | **PASS** |
| **2. Dữ liệu (`#view-data_hub`)** | Tải lên file CSV/Excel nhiều Sheet, chọn Sheet, phân biệt rõ `[Dữ liệu của tôi]` và `[Dữ liệu minh họa]` | `POST /api/v1/datasets/upload` + `reingestSelectedSheet()` | **PASS** |
| **2. Dữ liệu (`#view-data_explorer`)** | Giải thích ý nghĩa cột bằng ngôn ngữ đời thường (`Con số / Số tiền`, `Ngày tháng`, `Phân nhóm`) & Tìm kiếm dòng | `GET /api/v1/datasets/{id}/profile` + `filterPreviewRows()` | **PASS** |
| **2. Dữ liệu (`#view-data_quality`)** | 4 điểm chất lượng + **10 hạng mục kiểm tra toàn diện (`#dqValidationChecklistGrid`)** + Danh sách lỗi đa ngữ | `GET /api/v1/datasets/{id}/quality` | **PASS** |
| **2. Dữ liệu (`#view-data_cleaning`)** | Áp dụng gợi ý tự động, làm sạch thủ công, tạo cột tính toán mới (`derive_ratio_pct`, `derive_diff`) & Khôi phục phiên bản | `POST /api/v1/datasets/{id}/clean` + `POST /api/v1/datasets/{id}/restore` | **PASS** |
| **3. Phân tích (`#view-bi_analytics`)** | 5 câu hỏi gợi ý cho người mới + 18 phương pháp phân tích + Tùy chọn nâng cao ẩn/hiện (`Progressive Disclosure`) | `selectGuidedAnalysisPreset()` + `POST /api/v1/analytics/run` | **PASS** |
| **3. Phân tích (`#view-bi_analytics`)** | **Diễn giải kết quả 5 phần bắt buộc (`1. Kết quả`, `2. Bằng chứng`, `3. Ý nghĩa`, `4. Hành động`, `5. Giới hạn`)** + **Truy vết 8 thông số & Đối soát 8 bước** | `renderAnalyticsResult(res)` | **PASS** |
| **3. Phân tích (`#view-bi_kpis`)** | Biểu mẫu định nghĩa KPI **9 thuộc tính bắt buộc** + Cảnh báo tự động khi tên chỉ số mơ hồ (`#kpiAmbiguityBanner`) | `checkKpiAmbiguity()` + `POST /api/v1/kpis` | **PASS** |
| **3. Phân tích (`#view-bi_dashboards` & `bi_reports`)** | Bảng biểu 4 góc nhìn có bộ lọc cột/giá trị + Tạo & xuất báo cáo tổng hợp (`.xlsx`, `.docx`, In/PDF) | `renderInteractiveDashboard()` + `POST /api/v1/reports/generate` | **PASS** |
| **4. Vận hành (`#view-rfq_operations` & `rfq_catalog`)** | Toàn bộ nghiệp vụ **Thiên Minh B2B RFQ**: 6 Phases / 5 Gates, Bóc tách BoQ, Phê duyệt HITL, Đơn đặt hàng PO, Danh bạ Khách hàng/NCC & Sản phẩm SKU | `/api/v1/rfq/projects`, `/api/v1/rfq/partners`, `/api/v1/rfq/procurement`, `/api/v1/rfq/catalog` | **PASS** |
| **5. Trợ lý AI (`#view-ai_assistant`)** | Hỏi đáp ngôn ngữ tự nhiên + **Tách biệt 5 nhóm chống suy diễn (`FACT`, `CALCULATION`, `INSIGHT`, `HYPOTHESIS`, `RECOMMENDATION`)** | `POST /api/v1/ai/query` (`/api/v1/ai/chat`) | **PASS** |
| **6. Cài đặt (`#view-admin_governance`)** | Cập nhật tên hiển thị cá nhân (tùy chọn), ngôn ngữ, không gian làm việc & Phân quyền / Nhật ký hệ thống dành riêng cho Quản trị viên | `saveUserProfileSettings()` + `saveWorkspaceSettings()` + `createNewUserAccount()` | **PASS** |
