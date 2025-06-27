# 圖片資料夾批次轉 PDF 工具

一個簡單的 Python 腳本，可以快速將指定資料夾下的每個子資料夾中的圖片（jpg/png）合併成 PDF，並自動命名檔案。

---

## 功能特色

- 自動識別資料夾名稱中的數字（話數、卷數等），並補零（例如第0005話）。
- 支援多種命名格式：「話」、「卷」、「捲」等。
- 自動從資料夾名稱擷取標題文字，並將簡體字轉成繁體中文。
- 輸出的 PDF 檔名前綴會加上根目錄名稱，方便分類管理。
- 支援 jpg、jpeg、png 格式圖片，並依檔名排序。
- Windows 雙擊即可執行（需要安裝 Python 及相關套件）。

---

## 使用說明

1. 將本腳本 `convert_to_pdf.py` 放在你要轉換圖片的根目錄資料夾。

2. 安裝 Python（如果尚未安裝）：
   - 官方下載頁面：https://www.python.org/downloads/
   - 安裝時請勾選「Add Python to PATH」

3. 安裝所需 Python 套件：
   ```bash
   pip install img2pdf opencc-python-reimplemented
