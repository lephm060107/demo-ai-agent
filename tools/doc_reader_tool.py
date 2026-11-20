"""
tools/doc_reader_tool.py
Công cụ đọc tài liệu thực tế (PDF, DOCX, TXT, CSV, XLSX, Google Sheets).
Ghi nhận bằng chứng gọi công cụ qua ToolTracer.
"""

import io
import re
import time
import requests
import pandas as pd
from docx import Document
from pypdf import PdfReader
from typing import Dict, Any, Tuple, Optional

from tools.tool_base import ToolTracer

class DocumentReaderTool:
    TOOL_NAME = "DocumentReaderTool"

    def __init__(self, tracer: Optional[ToolTracer] = None):
        self.tracer = tracer or ToolTracer()

    def read_text_from_bytes(self, filename: str, content: bytes) -> Dict[str, Any]:
        t0 = time.perf_counter()
        fname = filename.lower()
        text = ""
        try:
            if fname.endswith(".pdf"):
                reader = PdfReader(io.BytesIO(content))
                text = "\n".join([p.extract_text() or "" for p in reader.pages])
                doc_type = f"PDF ({len(reader.pages)} pages)"
            elif fname.endswith(".docx"):
                doc = Document(io.BytesIO(content))
                text = "\n".join([p.text for p in doc.paragraphs if p.text])
                doc_type = f"DOCX ({len(doc.paragraphs)} paragraphs)"
            elif fname.endswith((".xlsx", ".xls")):
                xl = pd.ExcelFile(io.BytesIO(content))
                parts = []
                for s in xl.sheet_names:
                    df = xl.parse(s)
                    parts.append(f"--- Sheet: {s} ---\n{df.to_string(index=False)}")
                text = "\n".join(parts)
                doc_type = f"Excel ({len(xl.sheet_names)} sheets)"
            else:
                text = content.decode("utf-8", errors="ignore")
                doc_type = "Text/CSV"

            self.tracer.record(
                tool_name=self.TOOL_NAME,
                action="read_text_from_bytes",
                input_args={"filename": filename, "size_bytes": len(content)},
                output_summary=f"Extracted {len(text)} chars from {doc_type}",
                records_accessed=1,
                start_time=t0,
                status="OK"
            )
            return {"success": True, "filename": filename, "doc_type": doc_type, "text": text}
        except Exception as e:
            self.tracer.record(
                tool_name=self.TOOL_NAME,
                action="read_text_from_bytes",
                input_args={"filename": filename, "size_bytes": len(content)},
                output_summary=f"Error: {str(e)}",
                records_accessed=0,
                start_time=t0,
                status="ERROR"
            )
            return {"success": False, "filename": filename, "error": str(e), "text": ""}

    def read_text_from_path(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "rb") as f:
            data = f.read()
        return self.read_text_from_bytes(file_path, data)

    def load_master_excel_or_csv(self, filename: str, content: bytes) -> Tuple[bool, Dict[str, pd.DataFrame], str]:
        t0 = time.perf_counter()
        fname = filename.lower()
        dfs: Dict[str, pd.DataFrame] = {}
        try:
            if fname.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(content))
                dfs["DanhMuc_SanPham"] = df
                total_rows = len(df)
            elif fname.endswith((".xlsx", ".xls")):
                xl = pd.ExcelFile(io.BytesIO(content))
                total_rows = 0
                for s in xl.sheet_names:
                    df = xl.parse(s)
                    dfs[s] = df
                    total_rows += len(df)
            else:
                raise ValueError("Định dạng file không hỗ trợ. Chỉ chấp nhận .csv, .xlsx, .xls")

            self.tracer.record(
                tool_name=self.TOOL_NAME,
                action="load_master_excel_or_csv",
                input_args={"filename": filename, "size_bytes": len(content)},
                output_summary=f"Loaded {len(dfs)} sheet(s) ({total_rows} rows): {list(dfs.keys())}",
                records_accessed=total_rows,
                start_time=t0,
                status="OK"
            )
            return True, dfs, f"Nạp thành công {len(dfs)} bảng dữ liệu ({total_rows} dòng)."
        except Exception as e:
            self.tracer.record(
                tool_name=self.TOOL_NAME,
                action="load_master_excel_or_csv",
                input_args={"filename": filename},
                output_summary=f"Error: {str(e)}",
                records_accessed=0,
                start_time=t0,
                status="ERROR"
            )
            return False, {}, str(e)

    def load_google_sheets(self, url: str) -> Tuple[bool, Optional[pd.DataFrame], str]:
        t0 = time.perf_counter()
        try:
            csv_url = url.strip()
            if "docs.google.com/spreadsheets" in csv_url:
                match = re.search(r"/d/([a-zA-Z0-9-_]+)", csv_url)
                if match:
                    doc_id = match.group(1)
                    gid_match = re.search(r"gid=([0-9]+)", csv_url)
                    gid = gid_match.group(1) if gid_match else "0"
                    csv_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid={gid}"

            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(csv_url, headers=headers, timeout=15)
            if resp.status_code == 200:
                df = pd.read_csv(io.StringIO(resp.text))
                self.tracer.record(
                    tool_name=self.TOOL_NAME,
                    action="load_google_sheets",
                    input_args={"url": url},
                    output_summary=f"Fetched {len(df)} rows, columns: {list(df.columns)}",
                    records_accessed=len(df),
                    start_time=t0,
                    status="OK"
                )
                return True, df, f"Tải thành công {len(df)} dòng từ Google Sheets!"
            else:
                msg = f"HTTP {resp.status_code}: Vui lòng bật quyền xem công khai cho Google Sheet."
                self.tracer.record(
                    tool_name=self.TOOL_NAME,
                    action="load_google_sheets",
                    input_args={"url": url},
                    output_summary=msg,
                    records_accessed=0,
                    start_time=t0,
                    status="ERROR"
                )
                return False, None, msg
        except Exception as e:
            self.tracer.record(
                tool_name=self.TOOL_NAME,
                action="load_google_sheets",
                input_args={"url": url},
                output_summary=f"Exception: {str(e)}",
                records_accessed=0,
                start_time=t0,
                status="ERROR"
            )
            return False, None, f"Lỗi đọc Google Sheets: {str(e)}"

