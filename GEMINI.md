# 專案規範：影像資料夾 PDF 轉換工具

本文件定義了本專案的開發、維護與發布標準，確保專案具備高度的通用性、可讀性與專業度。

## 1. 程式碼慣例 (Coding Conventions)
- **詳盡註解**：所有程式碼必須提供教學等級的繁體中文註解，解釋「為什麼」這樣寫，而不僅是「在做什麼」。
- **通用化命名 (Generic Naming)**：
    - 嚴禁使用「漫畫」、「漫畫家」等具備特定媒體色彩的標籤或字眼，以降低版權爭議與法律風險。
    - 統一使用「項目 (Item)」、「影像 (Image)」、「目錄 (Directory)」等中性詞彙。
- **類型處理**：自動辨識並區分「卷 (Volume)」與「話 (Chapter)」的處理邏輯，確保兩者具備正確的 PDF 歸檔規格。

## 2. 版本管理與發布 (Releases)
- **版本號規範**：採用語義化版本 (Semantic Versioning)，例如 `v1.2.0`。
- **Git 標籤 (Tags)**：
    - 每次完成功能重構或重大修正後，必須打上對應的版本標籤。
    - 指令：`git tag -a vX.X.X -m "摘要"`。
- **GitHub 發布流程**：
    - 必須使用 GitHub CLI (`gh`) 工具同步建立正式 Release。
    - 發布內容必須包含詳細的更新說明 (Release Notes)，列出功能改進與修復項。
    - 指令：`gh release create vX.X.X --title "標題" --notes "更新細節"`。

## 3. 工作流 (Workflow)
1. **開發與測試**：在本地執行 `convert_to_pdf.py` 驗證功能。
2. **版本提交**：執行 `git commit`。
3. **版本發布**：執行 `git tag` 並透過 `gh` 建立遠端 Release。
4. **檔案同步**：確保 `README.md` 與 `.gitignore` 與程式碼同步更新。

## 4. 忽略設定 (.gitignore)
- 必須排除所有 `.pdf` 與影像原始檔案（如 `*.jpg`, `*.png` 等），確保 Git 儲存庫僅保留程式原始碼。
