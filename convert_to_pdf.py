import os
import img2pdf
import re
from opencc import OpenCC

# =================================================================
# 1. 全域初始化設定
# =================================================================

cc = OpenCC('s2t')

# 正則表達式優化：優先匹配「話/卷/回」前方的數字，若無則匹配任意數字
# 例如：從 "第1005話" 中精準提取 "1005"
num_with_tag_pattern = re.compile(r'(\d+)\s*(?:話|话|回|卷|捲|回|集)')
any_number_pattern = re.compile(r'(\d+)')

ZERO_PADDING = 4

# =================================================================
# 2. 輔助函式
# =================================================================

def get_folder_info(folder_name):
    """從資料夾名稱提取編號與類型（卷或話）"""
    # 優先找標籤前的數字
    tag_match = num_with_tag_pattern.search(folder_name)
    if tag_match:
        number = int(tag_match.group(1))
    else:
        # 沒標籤才找隨機數字
        any_match = any_number_pattern.search(folder_name)
        number = int(any_match.group(1)) if any_match else 999999 # 無數字排最後

    is_volume = any(k in folder_name for k in ["卷", "捲"])
    return number, is_volume

# =================================================================
# 3. 核心轉換函式
# =================================================================

def convert_item(item_path, combine_chapters=True, clear_old=False, skip_existing=False):
    """處理單一影像項目資料夾"""
    if not os.path.isdir(item_path):
        return

    item_name = os.path.basename(item_path)
    print(f"\n📂 正在處理項目：{item_name}")

    if clear_old:
        old_pdfs = [f for f in os.listdir(item_path) if f.lower().endswith(".pdf")]
        for pdf in old_pdfs:
            try: os.remove(os.path.join(item_path, pdf))
            except: pass

    # 取得子資料夾，並根據「提取出的數字」進行精確排序
    sub_folders = [f for f in os.listdir(item_path) if os.path.isdir(os.path.join(item_path, f))]
    sub_folders.sort(key=lambda f: get_folder_info(f)[0]) # 使用數值排序
    
    if not sub_folders:
        return

    volumes = []
    chapters = []
    for f in sub_folders:
        _, is_vol = get_folder_info(f)
        if is_vol: volumes.append(f)
        else: chapters.append(f)

    # 處理卷
    for folder in volumes:
        process_folders_to_pdf(item_path, [folder], item_name, skip_existing=skip_existing)

    # 處理話 (每 10 話合併)
    if chapters:
        if combine_chapters:
            chunk_size = 10
            for i in range(0, len(chapters), chunk_size):
                chunk = chapters[i:i + chunk_size]
                process_folders_to_pdf(item_path, chunk, item_name, is_combined=True, skip_existing=skip_existing)
        else:
            for folder in chapters:
                process_folders_to_pdf(item_path, [folder], item_name, skip_existing=skip_existing)

def process_folders_to_pdf(item_path, folders, item_name, is_combined=False, skip_existing=False):
    """將一或多個資料夾內的圖片合併為一個 PDF"""
    
    # 提取這組資料夾中「真實有效」的編號（用於檔名顯示）
    valid_numbers = []
    for f in folders:
        num, _ = get_folder_info(f)
        if num != 999999:
            valid_numbers.append(f"{num:0{ZERO_PADDING}}")
        else:
            valid_numbers.append("未知")

    # 1. 決定檔名
    if not is_combined:
        folder = folders[0]
        num, is_vol = get_folder_info(folder)
        num_str = f"{num:0{ZERO_PADDING}}" if num != 999999 else "Extra"
        type_str = "卷" if is_vol else "話"
        title = re.sub(r'(第)?\d+(話|话|回|卷|捲)?', '', folder).strip()
        title = cc.convert(title)
        filename = f"{item_name} 第{num_str}{type_str}{'-' + title if title else ''}.pdf"
    else:
        start_num = valid_numbers[0]
        end_num = valid_numbers[-1]
        filename = f"{item_name} 第{start_num}-{end_num}話.pdf"

    output_pdf = os.path.join(item_path, filename)

    if skip_existing and os.path.exists(output_pdf):
        print(f"  ⏭️  跳過已存在：{filename}")
        return

    # 2. 蒐集圖片
    all_image_paths = []
    for folder in folders:
        folder_path = os.path.join(item_path, folder)
        try:
            images = sorted(
                [f for f in os.listdir(folder_path) if f.lower().endswith((".jpg", ".jpeg", ".png"))],
                key=lambda x: int(os.path.splitext(x)[0]) if os.path.splitext(x)[0].isdigit() else x
            )
            all_image_paths.extend([os.path.join(folder_path, img) for img in images])
        except: pass

    if not all_image_paths: return

    # 3. 轉換
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
        print("❌ 找不到項目。")
        return

    print("========================================")
    print("   影像資料夾 PDF 轉換工具 (v1.5.0)")
    print("========================================")
    
    print("[1] 完整模式  [2] 增量更新  [3] 手動選取")
    choice = input("請輸入: ").strip()
    
    do_combine = True
    do_clear = False
    do_skip = False
    target_folders = []

    if choice == '1':
        target_folders = [os.path.join(root_dir, f) for f in item_folders]
        do_combine = input("合併模式？(Y/n): ").lower() != 'n'
        do_clear = input("清理舊檔？(y/N): ").lower() == 'y'
    elif choice == '2':
        target_folders = [os.path.join(root_dir, f) for f in item_folders]
        do_combine = input("合併模式？(Y/n): ").lower() != 'n'
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

    print(f"\n🚀 處理中 (合併:{do_combine}, 清理:{do_clear}, 增量:{do_skip})...")
    for path in target_folders:
        convert_item(path, combine_chapters=do_combine, clear_old=do_clear, skip_existing=do_skip)

    print("\n🎉 完成！")
    input("按 Enter 關閉...")

if __name__ == "__main__":
    main()
