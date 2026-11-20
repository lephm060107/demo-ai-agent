"""
Module data_loader.py:
Quản lý nạp dữ liệu danh mục sản phẩm, năng lực triển khai, bảng giá, tồn kho và chính sách duyệt
Hỗ trợ file Excel (.xlsx, .xls), file CSV, và Google Sheets Link.
"""

import io
import re
import requests
import pandas as pd
from typing import Dict, Any, Tuple, Optional

def convert_google_sheets_url_to_csv(url: str) -> str:
    """
    Chuyển đổi URL Google Sheets thông thường thành URL xuất trực tiếp CSV
    Ví dụ:
    https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit#gid=0
    -> https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/export?format=csv&gid=0
    """
    url = url.strip()
    if "docs.google.com/spreadsheets" in url:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            doc_id = match.group(1)
            gid = "0"
            gid_match = re.search(r"gid=([0-9]+)", url)
            if gid_match:
                gid = gid_match.group(1)
            return f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid={gid}"
    return url

def load_from_google_sheets(url: str) -> Tuple[bool, Optional[pd.DataFrame], str]:
    """Tải dữ liệu từ URL Google Sheets công khai hoặc dạng chia sẻ."""
    try:
        csv_url = convert_google_sheets_url_to_csv(url)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(csv_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            df = pd.read_csv(io.StringIO(resp.text))
            return True, df, "Tải thành công từ Google Sheets!"
        else:
            return False, None, f"Không thể tải Google Sheets (HTTP {resp.status_code}). Vui lòng đảm bảo Sheet đã bật quyền xem công khai (Anyone with link can view)."
    except Exception as e:
        return False, None, f"Lỗi khi đọc Google Sheets: {str(e)}"

def load_from_uploaded_file(uploaded_file) -> Dict[str, pd.DataFrame]:
    """
    Đọc dữ liệu từ file upload (Excel hoặc CSV).
    Trả về dictionary các DataFrame theo tên sheet.
    """
    dfs = {}
    fname = uploaded_file.name.lower()
    if fname.endswith(".csv"):
        dfs["DanhMuc_SanPham"] = pd.read_csv(uploaded_file)
    elif fname.endswith((".xlsx", ".xls")):
        excel_file = pd.ExcelFile(uploaded_file)
        for sheet_name in excel_file.sheet_names:
            dfs[sheet_name] = excel_file.parse(sheet_name)
    return dfs

def load_default_master_data(excel_path: str = "data/thienminh_master_data.xlsx") -> Dict[str, pd.DataFrame]:
    """Tải bộ dữ liệu chuẩn của Công ty Thiên Minh."""
    dfs = {}
    try:
        excel_file = pd.ExcelFile(excel_path)
        for s in excel_file.sheet_names:
            dfs[s] = excel_file.parse(s)
    except Exception:
        # Fallback reading CSV
        dfs["DanhMuc_SanPham"] = pd.read_csv("data/catalog_products.csv")
    return dfs

