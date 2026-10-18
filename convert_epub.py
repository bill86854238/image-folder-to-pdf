import os
import sys
import shutil
import zipfile
import re
from opencc import OpenCC

# 確保 Windows 控制台輸出支援 UTF-8，防止 cp950 編碼錯誤
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# =================================================================
# 1. 初始化設定與繁體轉換器
# =================================================================
# 採用台灣正體中文及慣用語轉換 (例如: 網絡 -> 網路、內存 -> 記憶體)
cc = OpenCC('s2twp')

# 需進行文字繁體轉換與標籤替換的副檔名清單
TEXT_EXTENSIONS = ('.html', '.xhtml', '.opf', '.ncx', '.xml', '.txt')

def backup_file(file_path, backup_dir="backup_original_epubs"):
    """
    執行安全備份：在處理前將原始檔案複製至獨立備份目錄中，
    確保原始下載檔案 100% 不受任何修改或損壞。
    """
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, os.path.basename(file_path))
    if not os.path.exists(backup_path):
        shutil.copy2(file_path, backup_path)
        print(f"  🛡️ 已建立安全備份：{backup_path}")
    else:
        print(f"  🛡️ 備份檔案已存在，安全無虞：{backup_path}")

def clean_css_font_family(css_content):
    """
    解除 CSS 字體死鎖：
    簡體 EPUB 常在 CSS 中寫死 '宋体' 或特定中文字型，
    導致電子書閱讀器無法自訂字型或出現方塊缺字。
    此函式將寫死的 font-family 宣告移除，使閱讀器自帶字型能正常生效。
    """
    # 移除 font-family 宣告 (例如 font-family: "宋体", sans-serif;)
    cleaned = re.sub(r'font-family\s*:[^;}]+;?', '/* font-family cleared */', css_content, flags=re.IGNORECASE)
    return cleaned

def clean_language_tags(text):
    """
    修正語言標籤：
    將 zh-CN / zh-Hans 改為 zh-TW / zh-Hant，
    防止電子書閱讀器將繁體字以簡體字形引擎渲染導致缺筆或字形變形。
    """
    text = re.sub(r'<dc:language>\s*(zh-CN|zh-Hans|zh)\s*</dc:language>', '<dc:language>zh-TW</dc:language>', text, flags=re.IGNORECASE)
    text = re.sub(r'xml:lang=["\'](zh-CN|zh-Hans|zh)["\']', 'xml:lang="zh-TW"', text, flags=re.IGNORECASE)
    text = re.sub(r'lang=["\'](zh-CN|zh-Hans|zh)["\']', 'lang="zh-TW"', text, flags=re.IGNORECASE)
    return text

def convert_epub_file(epub_path):
    """
    將單一 EPUB 轉換為符合電子書規範的繁體版 EPUB
    """
    filename = os.path.basename(epub_path)
    output_filename = filename.replace(".epub", "_繁體.epub")
    output_path = os.path.join(os.path.dirname(epub_path), output_filename)

    print(f"\n========================================")
    print(f"📖 開始處理：{filename}")
    print(f"========================================")

    # 1. 執行事前安全備份
    backup_file(epub_path)

    # 2. 開啟來源 EPUB 與目標 EPUB
    temp_output = output_path + ".tmp"
    try:
        with zipfile.ZipFile(epub_path, 'r') as zin, zipfile.ZipFile(temp_output, 'w') as zout:
            all_files = zin.namelist()

            # 規範關鍵：mimetype 必須是第一個 entry，且絕對不能壓縮 (ZIP_STORED)
            if "mimetype" in all_files:
                mimetype_data = zin.read("mimetype")
                zout.writestr("mimetype", mimetype_data, compress_type=zipfile.ZIP_STORED)

            # 依序處理其餘檔案
            for item in zin.infolist():
                if item.filename == "mimetype":
                    continue

                content = zin.read(item.filename)
                fname_lower = item.filename.lower()

                # 處理文字檔案：繁體轉換 + 語言標籤修正
                if fname_lower.endswith(TEXT_EXTENSIONS):
                    try:
                        text = content.decode('utf-8')
                        # 繁體轉換
                        text_tw = cc.convert(text)
                        # 語言標籤修正為 zh-TW
                        text_tw = clean_language_tags(text_tw)
                        content = text_tw.encode('utf-8')
                    except UnicodeDecodeError:
                        pass  # 若非 UTF-8 編碼則維持原樣以確保資料完整

                # 處理樣式表：解除字體死鎖
                elif fname_lower.endswith('.css'):
                    try:
                        css_text = content.decode('utf-8')
                        css_text = clean_css_font_family(css_text)
                        content = css_text.encode('utf-8')
                    except UnicodeDecodeError:
                        pass

                # 寫入目標檔案 (使用 DEFLATED 壓縮)
                zout.writestr(item, content, compress_type=zipfile.ZIP_DEFLATED)

        # 轉檔完成，將暫存檔替換為正式輸出檔
        if os.path.exists(output_path):
            os.remove(output_path)
        os.rename(temp_output, output_path)
        print(f"✅ 成功產出繁體版：{output_filename}")
        return True
    except Exception as e:
        if os.path.exists(temp_output):
            os.remove(temp_output)
        print(f"❌ 轉換失敗 {filename}: {e}")
        return False

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    # 搜尋當前目錄下非 _繁體 結尾的 epub 檔案
    target_epubs = [
        os.path.join(root_dir, f) for f in os.listdir(root_dir)
        if f.lower().endswith(".epub") and not f.endswith("_繁體.epub")
    ]

    if not target_epubs:
        print("❌ 找不到待轉換的 EPUB 小說檔案。")
        return

    print("========================================")
    print("      EPUB 小說繁體化轉換工具 (v1.0.0)")
    print("========================================")
    print(f"找到 {len(target_epubs)} 個 EPUB 項目：")
    for f in target_epubs:
        print(f"  - {os.path.basename(f)}")

    success_count = 0
    for epub in target_epubs:
        if convert_epub_file(epub):
            success_count += 1

    print("\n" + "="*40)
    print(f"🎉 全部處理完成！成功轉換：{success_count} / {len(target_epubs)}")
    print("原始檔案皆已完整備份於 backup_original_epubs/ 目錄下。")
    print("="*40)

if __name__ == "__main__":
    main()
