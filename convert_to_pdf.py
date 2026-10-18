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

OUTPUT_SUBDIRS = {"卷", "話", "特殊"}

def convert_item(item_path, combine_chapters=True, combine_volumes=True, process_chapters=True, clear_old=False, skip_existing=False):
    """處理單一影像項目資料夾，並依類型分流轉為 PDF"""
    if not os.path.isdir(item_path):
        return

    item_name = os.path.basename(item_path)
    print(f"\n📂 正在處理項目：{item_name}")
    stats["total_projects"] += 1

    if clear_old:
        # 清理本目錄及分類子目錄下的既有 PDF
        for root, _, files in os.walk(item_path):
            for pdf in files:
                if pdf.lower().endswith(".pdf"):
                    try: os.remove(os.path.join(root, pdf))
                    except: pass

    # 取得子資料夾並按數值排序（排除 PDF 歸檔專用之子目錄）
    sub_folders = [
        f for f in os.listdir(item_path) 
        if os.path.isdir(os.path.join(item_path, f)) and f not in OUTPUT_SUBDIRS
    ]
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

    # 1. 處理 [卷]：視設定進行 5 卷分塊合併或獨立處理
    if volumes:
        if combine_volumes:
            chunk_size = 5
            print(f"  > 偵測到 {len(volumes)} 個卷項目，將以 {chunk_size} 卷為單位合併...")
            for i in range(0, len(volumes), chunk_size):
                chunk = volumes[i:i + chunk_size]
                process_folders_to_pdf(item_path, chunk, item_name, is_combined=True, skip_existing=skip_existing)
        else:
            for folder in volumes:
                process_folders_to_pdf(item_path, [folder], item_name, skip_existing=skip_existing)

    # 2. 處理 [其他無編號項目]：獨立處理
    if others:
        print(f"  > 偵測到 {len(others)} 個特殊/無編號項目，將獨立處理...")
        for folder in others:
            process_folders_to_pdf(item_path, [folder], item_name, skip_existing=skip_existing)

    # 3. 處理 [正規話數]：視設定轉換或略過（無卷時啟動保底轉換）
    if chapters:
        if not process_chapters and volumes:
            # 既有卷又有話，且設定不轉話數 -> 依設定略過話數
            print(f"  ⏭️  已略過 {len(chapters)} 個話數項目（依設定不轉話數）")
        elif (not process_chapters and not volumes) or combine_chapters:
            # 觸發無卷保底，或原本即設定合併話數 (10 話一包)
            chunk_size = 10
            if not process_chapters and not volumes:
                print(f"  💡 偵測到本項目無任何卷數，啟動保底機制（以 {chunk_size} 話為單位合併）...")
            else:
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
    """將一或多個資料夾內的圖片合併為一個 PDF，並依類型分流至對應子目錄 (卷/話/特殊) 歸檔"""
    
    # 1. 判定歸檔類別並建立專屬子目錄 (卷 / 話 / 特殊)
    _, is_vol, has_num = get_folder_info(folders[0])
    if is_vol:
        sub_dir_name = "卷"
        type_str = "卷"
    elif has_num:
        sub_dir_name = "話"
        type_str = "話"
    else:
        sub_dir_name = "特殊"
        type_str = ""

    output_dir = os.path.join(item_path, sub_dir_name)
    os.makedirs(output_dir, exist_ok=True)

    # 2. 決定檔名規格
    if not is_combined:
        folder = folders[0]
        num, _, has_num = get_folder_info(folder)
        
        if has_num:
            num_str = f"{int(num):0{ZERO_PADDING}}" if num.is_integer() else f"{num:0{ZERO_PADDING}}"
            title = re.sub(r'(第)?\d+(?:\.\d+)?(話|话|回|卷|捲)?', '', folder).strip()
            title = cc.convert(title)
            filename = f"{item_name} 第{num_str}{type_str}{'-' + title if title else ''}.pdf"
        else:
            # 無編號項目，直接用資料夾名稱轉繁體
            filename = f"{item_name} {cc.convert(folder)}.pdf"
    else:
        # 合併檔名：提取首尾編號，並依類型 (卷/話) 命名
        nums = []
        for f in folders:
            n, _, _ = get_folder_info(f)
            nums.append(f"{int(n):0{ZERO_PADDING}}" if n.is_integer() else f"{n:0{ZERO_PADDING}}")
        
        if len(folders) == 1:
            filename = f"{item_name} 第{nums[0]}{type_str}.pdf"
        else:
            filename = f"{item_name} 第{nums[0]}-{nums[-1]}{type_str}.pdf"

    output_pdf = os.path.join(output_dir, filename)

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
    print("   影像資料夾 PDF 轉換工具 (v1.7.1)")
    print("========================================")
    
    print("[1] 完整模式  [2] 智慧增量  [3] 手動選取")
    choice = input("請輸入: ").strip()
    
    do_combine = True
    do_combine_vol = True
    do_process_chaps = True
    do_clear = False
    do_skip = False
    target_folders = []

    if choice == '1':
        target_folders = [os.path.join(root_dir, f) for f in item_folders]
        do_combine_vol = input("合併卷模式 (5 卷一包)？(Y/n): ").lower() != 'n'
        do_process_chaps = input("是否轉換話數 (連載)？(Y/n): ").lower() != 'n'
        if do_process_chaps:
            do_combine = input("合併話模式 (10 話一包)？(Y/n): ").lower() != 'n'
        else:
            do_combine = False
        do_clear = input("清理舊檔？(y/N): ").lower() == 'y'
    elif choice == '2':
        target_folders = [os.path.join(root_dir, f) for f in item_folders]
        do_combine_vol = input("合併卷模式 (5 卷一包)？(Y/n): ").lower() != 'n'
        do_process_chaps = input("是否轉換話數 (連載)？(Y/n): ").lower() != 'n'
        if do_process_chaps:
            do_combine = input("合併話模式 (10 話一包)？(Y/n): ").lower() != 'n'
        else:
            do_combine = False
        do_skip = True
    elif choice in ['3', '']:
        print("\n清單：")
        for i, f in enumerate(item_folders, 1): print(f"[{i}] {f}")
        indices_str = input("編號 (例: 1,3-5): ").strip()
        do_combine_vol = input("合併卷模式 (5 卷一包)？(Y/n): ").lower() != 'n'
        do_process_chaps = input("是否轉換話數 (連載)？(Y/n): ").lower() != 'n'
        if do_process_chaps:
            do_combine = input("合併話模式 (10 話一包)？(Y/n): ").lower() != 'n'
        else:
            do_combine = False
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

    print(f"\n🚀 啟動處理 (合卷:{do_combine_vol}, 轉話:{do_process_chaps}, 合話:{do_combine}, 清理:{do_clear}, 增量:{do_skip})...")
    for path in target_folders:
        convert_item(path, combine_chapters=do_combine, combine_volumes=do_combine_vol, process_chapters=do_process_chaps, clear_old=do_clear, skip_existing=do_skip)

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
