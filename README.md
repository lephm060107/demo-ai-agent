# NEXUS ANALYTICS v2.0
# Universal AI-Powered Business Data Analytics & B2B RFQ Intelligence Platform

**NEXUS ANALYTICS** là nền tảng phân tích dữ liệu doanh nghiệp đa lĩnh vực kết hợp hệ thống tự động hóa xử lý hồ sơ mời thầu B2B (**Thiên Minh B2B RFQ Master Workflow**).

---

## 1. Khởi Chạy Nhanh (Quick Start)

```powershell
# Khởi chạy Unified Platform trên cổng 8000
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload

# Hoặc nhấp đúp vào file:
.\run_localhost.bat
```

- **Giao diện Web thống nhất:** **http://localhost:8000** *(hoặc **http://127.0.0.1:8000**)*
- **Tài liệu OpenAPI / Swagger:** **http://localhost:8000/docs**

---

## 2. Kiến Trúc Hợp Nhất (Unified Architecture)

```text
c:\Users\X1-Gen8\Downloads\AI301_S4\
├── server.py                               # Unified FastAPI Server (Analytics + B2B RFQ trên cổng 8000)
├── run_localhost.bat                       # Script khởi động nhanh nền tảng thống nhất
├── docker-compose.yml                      # Cấu hình triển khai PostgreSQL 16 + Redis + Nexus App
├── config/
│   └── business_rules.json                 # Cấu hình động quy tắc nghiệp vụ B2B RFQ
├── data/
│   ├── thienminh_master_data.xlsx          # 4 sheets: Sản phẩm, Năng lực, Chính sách, Lịch kỹ sư
│   ├── catalog_products.csv                # Danh mục sản phẩm chuẩn
│   └── rfp_case_1..3_*.txt                 # 3 hồ sơ RFQ mẫu (Đạt chuẩn, Thiếu tin, Vượt thẩm quyền)
├── engine/
│   ├── orchestrator.py                     # MasterOrchestrator (6 Phases - 12 Steps - 5 Decision Gates)
│   └── decision_engine.py                  # DecisionEngine (5 cổng IF/ELSE tường minh)
├── skills/
│   ├── skill_01_intake_structurer.py       # IntakeStructurerSkill (Phase 01-02)
│   ├── skill_02_solution_matcher.py        # SolutionMatcherSkill (Phase 03)
│   ├── skill_03_commercial_pricer.py       # CommercialPricerSkill (Phase 04)
│   └── skill_04_proposal_governance.py     # ProposalGovernanceSkill (Phase 05-06)
├── tools/
│   ├── tool_base.py                        # ToolTracer & ToolCallRecord
│   ├── doc_reader_tool.py                  # DocumentReaderTool (.pdf, .docx, .txt, .csv, .xlsx, Google Sheets)
│   ├── data_lookup_tool.py                 # DataLookupTool (Tra cứu động, không hardcode SKU)
│   ├── pricing_calculator_tool.py          # PricingCalculatorTool (Tính toán BoQ & lợi nhuận gộp)
│   └── policy_checker_tool.py              # PolicyCheckerTool (Kiểm tra chiết khấu & thẩm quyền)
├── agent_engine/
│   ├── data_loader.py                      # Nạp dữ liệu Master Data & Google Sheets helper
│   ├── export_generator.py                 # Xuất báo giá .xlsx và hồ sơ đề xuất .docx (có Trang Bìa)
│   └── email_dispatcher.py                 # Sinh công văn làm rõ & tờ trình phê duyệt
├── nexus_analytics/
│   ├── core/                               # Config & Security (RBAC, Anti-CSV/Prompt Injection)
│   ├── db/                                 # 24 Normalized Relational Tables (SQLite WAL / PostgreSQL 16 DDL)
│   ├── services/                           # Ingestion, Profiling, Quality, Cleaning, 4-Level Analytics, AI Agent, Reporting, RFQ Service
│   ├── static/index.html                   # Unified Enterprise SaaS Frontend (14 phân khu chức năng)
│   └── storage/                            # Lưu trữ Versioned Parquet, Raw Files & Reports
└── tests/
    ├── test_nexus_analytics.py             # Kiểm thử toàn diện 24 bảng, 18 thuật toán, AI Agent & E2E
    ├── test_suite.py                       # Kiểm thử 11 kịch bản Normal/Missing/Boundary/Custom Data cho B2B RFQ
    └── test_http_api.py                    # Kiểm thử 8 kịch bản HTTP E2E cho luồng B2B RFQ
```

---

## 3. Chạy Kiểm Thử Tự Động

```powershell
python tests/test_suite.py
python tests/test_http_api.py
python tests/test_nexus_analytics.py
```

