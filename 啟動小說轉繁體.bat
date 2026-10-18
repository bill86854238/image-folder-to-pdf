@echo off
chcp 65001 >nul
title EPUB 小說繁體化轉換工具
echo ========================================
echo    正在啟動 EPUB 小說繁體化轉換工具...
echo ========================================
python "%~dp0convert_epub.py"
echo.
pause
