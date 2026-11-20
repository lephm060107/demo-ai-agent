@echo off
chcp 65001 >nul
echo ======================================================================
echo   NEXUS ANALYTICS v2.0 - UNIFIED AI DATA ANALYTICS ^& B2B RFQ PLATFORM
echo   Starting Unified Platform at http://127.0.0.1:8000
echo ======================================================================
start "" "http://127.0.0.1:8000"
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
pause
