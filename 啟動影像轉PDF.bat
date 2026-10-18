@echo off
chcp 65001 >nul
title 影像資料夾 PDF 轉換工具
echo ========================================
echo    正在啟動 影像資料夾 PDF 轉換工具...
echo ========================================
python "%~dp0convert_to_pdf.py"
echo.
pause
