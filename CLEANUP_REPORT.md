# CODEBASE CLEANUP & CONSOLIDATION REPORT
# NEXUS ANALYTICS – UNIFIED PLATFORM RESTRUCTURING

## 1. Phân Loại Toàn Bộ File Trong Repository (Nhóm A, B, C, D)

### Nhóm A – Giữ Nguyên (Đang hoạt động tốt & Đúng chuẩn kiến trúc)
- `engine/orchestrator.py`, `engine/decision_engine.py`, `engine/__init__.py`
- `skills/skill_01_intake_structurer.py`, `skills/skill_02_solution_matcher.py`, `skills/skill_03_commercial_pricer.py`, `skills/skill_04_proposal_governance.py`, `skills/__init__.py`
- `tools/tool_base.py`, `tools/doc_reader_tool.py`, `tools/data_lookup_tool.py`, `tools/pricing_calculator_tool.py`, `tools/policy_checker_tool.py`, `tools/__init__.py`
- `agent_engine/data_loader.py`, `agent_engine/export_generator.py`, `agent_engine/email_dispatcher.py`
- `config/business_rules.json`
- `data/thienminh_master_data.xlsx`, `data/catalog_products.csv`, `data/rfp_case_1_day_du.txt`, `data/rfp_case_2_thieu_thong_tin.txt`, `data/rfp_case_3_vuot_tham_quyen.txt`
- `nexus_analytics/core/config.py`, `nexus_analytics/core/security.py`
- `nexus_analytics/services/ingestion_service.py`, `profiling_service.py`, `quality_engine.py`, `cleaning_engine.py`, `analytics_engine.py`, `ai_agent_orchestrator.py`, `reporting_service.py`

### Nhóm B – Giữ Và Chỉnh Sửa (Mở rộng để tương thích hệ thống hợp nhất)
- `nexus_analytics/db/postgres_schema.sql` & `nexus_analytics/db/database.py`: Mở rộng từ 19 bảng lên **24 bảng quan hệ chuẩn hóa** (thêm 5 bảng B2B RFQ: `rfq_opportunities`, `rfq_runs`, `rfq_gate_decisions`, `rfq_boq_items`, `rfq_hitl_approvals`).
- `nexus_analytics/services/platform_manager.py`: Tự động đồng bộ bảng `DanhMuc_SanPham` từ `data/thienminh_master_data.xlsx` thành một Dataset phân tích trực tiếp trong NEXUS ANALYTICS.
- `nexus_analytics/services/rfq_workflow_service.py` *(Tạo mới)*: Kết nối `MasterOrchestrator` của Thiên Minh với CSDL 24 bảng và `audit_logs` của NEXUS ANALYTICS.
- `docker-compose.yml`, `tests/test_nexus_analytics.py`, `tests/test_http_api.py`.

### Nhóm C – Hợp Nhất (Consolidate Duplicate Entrypoints & UIs)
- Hợp nhất `server.py` (cổng 8000) và `nexus_server.py` (cổng 8001) thành **một `server.py` thống nhất duy nhất** hỗ trợ đầy đủ cả `/api/v1/*`, `/api/v1/rfq/*` và các route tương thích ngược `/api/*`.
- Hợp nhất `static/index.html` và `nexus_analytics/static/index.html` thành **một giao diện `nexus_analytics/static/index.html` thống nhất duy nhất** mang nhận diện thương hiệu **NEXUS ANALYTICS**.
- Hợp nhất `run_localhost.bat`, `start_web.bat` và `start_nexus.bat` thành **một script `run_localhost.bat` duy nhất**.

### Nhóm D – Đã Loại Bỏ An Toàn (Sau Khi Xác Minh 0 Tham Chiếu Active)

| File / Thư mục đã xóa | Lý do loại bỏ & Bằng chứng kiểm tra an toàn |
| :--- | :--- |
| `app.py` | Prototype Streamlit đời đầu, đã được thay thế hoàn toàn bằng kiến trúc FastAPI + Web SPA. |
| `run_app.bat` | Script chạy `streamlit run app.py` không còn sử dụng. |
| `agent_engine/rfp_parser.py` | Đã được thay thế hoàn toàn bởi `skills/skill_01_intake_structurer.py`. Không có module active nào import. |
| `agent_engine/completeness_checker.py` | Đã được thay thế hoàn toàn bởi `skills/skill_01_intake_structurer.py` và `engine/decision_engine.py`. |
| `agent_engine/inventory_pricing_validator.py` | Đã được thay thế hoàn toàn bởi `skills/skill_02_solution_matcher.py` và `tools/data_lookup_tool.py`. |
| `agent_engine/quotation_builder.py` | Đã được thay thế hoàn toàn bởi `skills/skill_03_commercial_pricer.py` và `tools/pricing_calculator_tool.py`. |
| `agent_engine/approval_evaluator.py` | Đã được thay thế hoàn toàn bởi `tools/policy_checker_tool.py` và `engine/decision_engine.py`. |
| `agent_engine/master_workflow.py` | Đã được thay thế hoàn toàn bởi `engine/orchestrator.py` (`MasterOrchestrator`). |
| `nexus_server.py` | Đã hợp nhất toàn bộ routes vào `server.py`. |
| `static/index.html` & thư mục `static/` | Đã hợp nhất toàn bộ giao diện B2B RFQ vào `nexus_analytics/static/index.html`. |
| `start_web.bat`, `start_nexus.bat` | Đã hợp nhất vào `run_localhost.bat`. |
| `New folder/` | Thư mục rỗng không chứa file. |

