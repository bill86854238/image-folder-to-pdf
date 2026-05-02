import os
import img2pdf
import re
from opencc import OpenCC
import pikepdf

# =================================================================
# 1. 全域初始化設定
# =================================================================

cc = OpenCC('s2t')

# 正則表達式：支援整數與小數
num_with_tag_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*(?:話|话|回|卷|捲|集)')
any_number_pattern = re.compile(r'(\d+(?:\.\d+)?)')

ZERO_PADDING = 4

stats = {
    "total_projects": 0,
    "success_count": 0,
    "skip_count": 0,
    "fail_list": []
}

# =================================================================
# 2. 輔助函式
# =================================================================

def get_folder_info(folder_name):
    """
    從資料夾名稱提取資訊。
    傳回: (number, is_volume, has_real_number)
    """
    is_volume = any(k in folder_name for k in ["卷", "捲"])
    has_real_number = True
    
    # 優先找標籤前的數字
    tag_match = num_with_tag_pattern.search(folder_name)
    if tag_match:
        number = float(tag_match.group(1))
    else:
        # 沒標籤才找隨機數字
        any_match = any_number_pattern.search(folder_name)
        if any_match:
            number = float(any_match.group(1))
        else:
            number = 999999.0 # 無數字排最後
            has_real_number = False

    return number, is_volume, has_real_number

# =================================================================
# 3. 核心轉換與書籤函式
# =================================================================

def convert_item(item_path, combine_chapters=True, clear_old=False, skip_existing=False):
    """處理單一影像項目資料夾"""
    if not os.path.isdir(item_path):
        return

    item_name = os.path.basename(item_path)
    print(f"\n📂 正在處理項目：{item_name}")
    stats["total_projects"] += 1

    if clear_old:
        old_pdfs = [f for f in os.listdir(item_path) if f.lower().endswith(".pdf")]
        for pdf in old_pdfs:
            try: os.remove(os.path.join(item_path, pdf))
            except: pass

    # 取得子資料夾並按數值排序
    sub_folders = [f for f in os.listdir(item_path) if os.path.isdir(os.path.join(item_path, f))]
    sub_folders.sort(key=lambda f: get_folder_info(f)[0])
    
    if not sub_folders:
        return

    # --- 三路分類邏輯 ---
    volumes = []   # 卷/捲
    chapters = []  # 有編號的話數
    others = []    # 完全無編號的項目 (如: 小劇場、番外篇)

    for f in sub_folders:
        num, is_vol, has_num = get_folder_info(f)
        if is_vol:
            volumes.append(f)
        elif has_num:
            chapters.append(f)
        else:
            others.append(f)

    # 1. 處理 [卷]：獨立處理
    for folder in volumes:
        process_folders_to_pdf(item_path, [folder], item_name, skip_existing=skip_existing)

    # 2. 處理 [其他無編號項目]：獨立處理
    if others:
        print(f"  > 偵測到 {len(others)} 個特殊/無編號項目，將獨立處理...")
        for folder in others:
            process_folders_to_pdf(item_path, [folder], item_name, skip_existing=skip_existing)

    # 3. 處理 [正規話數]：視情況合併
    if chapters:
        if combine_chapters:
            chunk_size = 10
            print(f"  > 偵測到 {len(chapters)} 個話數項目，將以 {chunk_size} 話為單位合併...")
            for i in range(0, len(chapters), chunk_size):
                chunk = chapters[i:i + chunk_size]
                process_folders_to_pdf(item_path, chunk, item_name, is_combined=True, skip_existing=skip_existing)
        else:
            for folder in chapters:
                process_folders_to_pdf(item_path, [folder], item_name, skip_existing=skip_existing)

def add_bookmarks_to_pdf(pdf_path, bookmarks):
    """為 PDF 加入書籤"""
    try:
        with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
            with pdf.open_outline() as outline:
                for page_num, title in bookmarks:
                    new_bookmark = pikepdf.OutlineItem(title, page_num)
                    outline.root.append(new_bookmark)
            pdf.save(pdf_path)
    except: pass

def process_folders_to_pdf(item_path, folders, item_name, is_combined=False, skip_existing=False):
    """將一或多個資料夾內的圖片合併為一個 PDF"""
    
    # 1. 決定檔名
    if not is_combined:
        folder = folders[0]
        num, is_vol, has_num = get_folder_info(folder)
        
        if has_num:
            num_str = f"{int(num):0{ZERO_PADDING}}" if num.is_integer() else f"{num:0{ZERO_PADDING}}"
            type_str = "卷" if is_vol else "話"
            title = re.sub(r'(第)?\d+(?:\.\d+)?(話|话|回|卷|捲)?', '', folder).strip()
            title = cc.convert(title)
            filename = f"{item_name} 第{num_str}{type_str}{'-' + title if title else ''}.pdf"
        else:
            # 無編號項目，直接用資料夾名稱轉繁體
            filename = f"{item_name} {cc.convert(folder)}.pdf"
    else:
        # 合併檔名：提取首尾話數
        nums = []
        for f in folders:
            n, _, _ = get_folder_info(f)
            nums.append(f"{int(n):0{ZERO_PADDING}}" if n.is_integer() else f"{n:0{ZERO_PADDING}}")
        filename = f"{item_name} 第{nums[0]}-{nums[-1]}話.pdf"

    output_pdf = os.path.join(item_path, filename)

    if skip_existing and os.path.exists(output_pdf):
        print(f"  ⏭️  跳過已存在：{filename}")
        stats["skip_count"] += 1
        return

    # 2. 蒐集圖片與書籤
    all_image_paths = []
    bookmark_info = []
    current_page_offset = 0

    for folder in folders:
        folder_path = os.path.join(item_path, folder)
        try:
            images = sorted(
                [f for f in os.listdir(folder_path) if f.lower().endswith((".jpg", ".jpeg", ".png"))],
                key=lambda x: int(os.path.splitext(x)[0]) if os.path.splitext(x)[0].isdigit() else x
            )
            if images:
                bookmark_info.append((current_page_offset, cc.convert(folder)))
                all_image_paths.extend([os.path.join(folder_path, img) for img in images])
                current_page_offset += len(images)
        except: pass

    if not all_image_paths: return

    # 3. 轉換與後處理
    try:
        with open(output_pdf, "wb") as f:
            f.write(img2pdf.convert(all_image_paths))
        if is_combined and len(folders) > 1:
            add_bookmarks_to_pdf(output_pdf, bookmark_info)
        print(f"  ✅ 完成：{filename}")
        stats["success_count"] += 1
    except Exception as e:
        print(f"  ❌ 轉換失敗 {filename}: {e}")
        stats["fail_list"].append(filename)

# =================================================================
# 4. 主程式流程
# =================================================================

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    item_folders = sorted([f for f in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, f)) and not f.startswith('.')])

    if not item_folders:
        print("❌ 找不到項目。")
        return

    print("========================================")
    print("   影像資料夾 PDF 轉換工具 (v1.6.1)")
    print("========================================")
    
    print("[1] 完整模式  [2] 智慧增量  [3] 手動選取")
    choice = input("請輸入: ").strip()
    
    do_combine = True
    do_clear = False
    do_skip = False
    target_folders = []

    if choice == '1':
        target_folders = [os.path.join(root_dir, f) for f in item_folders]
        do_combine = input("合併模式 (10 話一包)？(Y/n): ").lower() != 'n'
        do_clear = input("清理舊檔？(y/N): ").lower() == 'y'
    elif choice == '2':
        target_folders = [os.path.join(root_dir, f) for f in item_folders]
        do_combine = input("合併模式 (10 話一包)？(Y/n): ").lower() != 'n'
        do_skip = True
    elif choice in ['3', '']:
        print("\n清單：")
        for i, f in enumerate(item_folders, 1): print(f"[{i}] {f}")
        indices_str = input("編號 (例: 1,3-5): ").strip()
        do_combine = input("合併模式？(Y/n): ").lower() != 'n'
        do_skip = input("跳過已存在？(Y/n): ").lower() != 'n'
        try:
            for part in indices_str.replace('，', ',').split(','):
                if '-' in part:
                    s, e = map(int, part.split('-'))
                    for i in range(s, e + 1):
                        if 1 <= i <= len(item_folders): target_folders.append(os.path.join(root_dir, item_folders[i-1]))
                elif part.strip().isdigit():
                    idx = int(part.strip())
                    if 1 <= idx <= len(item_folders): target_folders.append(os.path.join(root_dir, item_folders[idx-1]))
        except: return
    else: return

    print(f"\n🚀 啟動處理 (合併:{do_combine}, 清理:{do_clear}, 增量:{do_skip})...")
    for path in target_folders:
        convert_item(path, combine_chapters=do_combine, clear_old=do_clear, skip_existing=do_skip)

    print("\n" + "="*40)
    print("       任務執行總結報告")
    print("="*40)
    print(f"總處理項目數：{stats['total_projects']}")
    print(f"成功產出檔案：{stats['success_count']}")
    print(f"跳過已存在檔：{stats['skip_count']}")
    if stats["fail_list"]:
        print(f"失敗清單 (共 {len(stats['fail_list'])} 個)：")
        for f in stats["fail_list"]: print(f"  - {f}")
    print("="*40)
    input("\n按下 Enter 鍵結束...")

if __name__ == "__main__":
    main()
