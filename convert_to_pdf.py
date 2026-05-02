import os
import img2pdf
import re
from opencc import OpenCC

# =================================================================
# 1. 全域初始化設定
# =================================================================

# 初始化 OpenCC 轉換器：'s2t' 代表「簡體轉繁體 (Simplified to Traditional)」
cc = OpenCC('s2t')

# 正則表達式 (Regex)：用來抓取字串中出現的「數字」
number_pattern = re.compile(r'(\d+)')

# 補零設定：統一補齊為 4 位數 (例如 5 變成 0005)
ZERO_PADDING = 4

# =================================================================
# 2. 輔助函式
# =================================================================

def get_folder_info(folder_name):
    """從資料夾名稱提取編號與類型（卷或話）"""
    match = number_pattern.search(folder_name)
    number = int(match.group(1)) if match else 0
    is_volume = any(k in folder_name for k in ["卷", "捲"])
    return number, is_volume

# =================================================================
# 3. 核心轉換函式
# =================================================================

def convert_item(item_path, combine_chapters=True, clear_old=False):
    """
    處理單一影像項目資料夾。
    combine_chapters: 是否啟動每 10 話合併模式。
    clear_old: 轉換前是否刪除舊的 PDF。
    """
    if not os.path.isdir(item_path):
        return

    item_name = os.path.basename(item_path)
    print(f"\n📂 正在處理項目：{item_name}")

    # --- 環境清理：刪除舊的 PDF ---
    if clear_old:
        old_pdfs = [f for f in os.listdir(item_path) if f.lower().endswith(".pdf")]
        if old_pdfs:
            print(f"  🧹 正在清理舊的 PDF 檔案 (共 {len(old_pdfs)} 個)...")
            for pdf in old_pdfs:
                try:
                    os.remove(os.path.join(item_path, pdf))
                except Exception as e:
                    print(f"  ⚠️ 無法刪除 {pdf}: {e}")

    # 取得所有子資料夾並排序
    sub_folders = sorted([f for f in os.listdir(item_path) if os.path.isdir(os.path.join(item_path, f))])
    
    if not sub_folders:
        print(f"ℹ️  在「{item_name}」中找不到任何子資料夾。")
        return

    # 將資料夾分類為「卷」與「話」
    volumes = []
    chapters = []
    for f in sub_folders:
        _, is_vol = get_folder_info(f)
        if is_vol:
            volumes.append(f)
        else:
            chapters.append(f)

    # --- 處理 [卷]：維持一卷一個 PDF ---
    if volumes:
        print(f"  > 偵測到 {len(volumes)} 個「卷」項目，將獨立處理...")
        for folder in volumes:
            process_folders_to_pdf(item_path, [folder], item_name)

    # --- 處理 [話]：根據設定決定是否合併 ---
    if chapters:
        if combine_chapters:
            # 每 10 話一組進行合併
            chunk_size = 10
            print(f"  > 偵測到 {len(chapters)} 個「話」項目，將以 {chunk_size} 話為單位合併...")
            for i in range(0, len(chapters), chunk_size):
                chunk = chapters[i:i + chunk_size]
                process_folders_to_pdf(item_path, chunk, item_name, is_combined=True)
        else:
            # 獨立處理每一話
            print(f"  > 偵測到 {len(chapters)} 個「話」項目，將獨立處理...")
            for folder in chapters:
                process_folders_to_pdf(item_path, [folder], item_name)

def process_folders_to_pdf(item_path, folders, item_name, is_combined=False):
    """將一或多個資料夾內的圖片合併為一個 PDF"""
    all_image_paths = []
    display_numbers = []

    for folder in folders:
        folder_path = os.path.join(item_path, folder)
        num, is_vol = get_folder_info(folder)
        display_numbers.append(f"{num:0{ZERO_PADDING}}")

        try:
            images = sorted(
                [f for f in os.listdir(folder_path) if f.lower().endswith((".jpg", ".jpeg", ".png"))],
                key=lambda x: int(os.path.splitext(x)[0]) if os.path.splitext(x)[0].isdigit() else x
            )
            all_image_paths.extend([os.path.join(folder_path, img) for img in images])
        except Exception as e:
            print(f"  ❌ 讀取 {folder} 出錯: {e}")

    if not all_image_paths:
        return

    if not is_combined:
        folder = folders[0]
        num, is_vol = get_folder_info(folder)
        num_str = f"{num:0{ZERO_PADDING}}"
        type_str = "卷" if is_vol else "話"
        title = re.sub(r'(第)?\d+(話|话|回|卷|捲)?', '', folder).strip()
        title = cc.convert(title)
        filename = f"{item_name} 第{num_str}{type_str}{'-' + title if title else ''}.pdf"
    else:
        start_num = display_numbers[0]
        end_num = display_numbers[-1]
        filename = f"{item_name} 第{start_num}-{end_num}話.pdf"

    output_pdf = os.path.join(item_path, filename)
    try:
        with open(output_pdf, "wb") as f:
            f.write(img2pdf.convert(all_image_paths))
        print(f"  ✅ 完成：{filename}")
    except Exception as e:
        print(f"  ❌ 轉換失敗 {filename}: {e}")

# =================================================================
# 4. 主程式流程
# =================================================================

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    item_folders = sorted([f for f in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, f)) and not f.startswith('.')])

    if not item_folders:
        print("❌ 找不到可處理的項目資料夾。")
        return

    print("========================================")
    print("   影像資料夾 PDF 轉換工具 (v1.3.0)")
    print("========================================")
    print(f"找到 {len(item_folders)} 個項目。")
    print("----------------------------------------")
    print("[1] 自動處理所有項目")
    print("[2] 手動選取特定項目")
    print("----------------------------------------")
    
    choice = input("請輸入 1 或 2: ").strip()
    
    # 功能詢問
    do_combine = input("\n是否啟動「每 10 話自動合併」模式？(Y/n): ").strip().lower() != 'n'
    do_clear = input("是否在轉換前「刪除舊的 PDF 檔案」？(y/N): ").strip().lower() == 'y'

    target_folders = []
    if choice == '1':
        target_folders = [os.path.join(root_dir, f) for f in item_folders]
    elif choice == '2':
        print("\n可選清單：")
        for i, f in enumerate(item_folders, 1): print(f"[{i}] {f}")
        indices_str = input("\n請輸入編號 (例: 1,3-5): ").strip()
        try:
            for part in indices_str.replace('，', ',').split(','):
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    for i in range(start, end + 1):
                        if 1 <= i <= len(item_folders): target_folders.append(os.path.join(root_dir, item_folders[i-1]))
                elif part.strip().isdigit():
                    idx = int(part.strip())
                    if 1 <= idx <= len(item_folders): target_folders.append(os.path.join(root_dir, item_folders[idx-1]))
        except:
            print("❌ 輸入格式錯誤。")
            return
    else:
        return

    if not target_folders:
        print("⚠️ 未選取任何對象。")
        return

    print(f"\n🚀 準備處理 {len(target_folders)} 個項目...")
    print(f"設定：合併模式={'開啟' if do_combine else '關閉'}, 清理舊檔={'開啟' if do_clear else '關閉'}")
    
    for path in target_folders:
        convert_item(path, combine_chapters=do_combine, clear_old=do_clear)

    print("\n" + "="*40)
    print("🎉 任務全部完成！")
    print("="*40)
    input("\n按下 Enter 鍵結束...")

if __name__ == "__main__":
    main()
