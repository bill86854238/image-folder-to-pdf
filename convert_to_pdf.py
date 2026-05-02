import os
import img2pdf
import re
from opencc import OpenCC

# 初始化簡體轉繁體
cc = OpenCC('s2t')

# 正則表達式，抓取數字
number_pattern = re.compile(r'(\d+)')

# 補零位數固定為 4 位
ZERO_PADDING = 4

def convert_comic(comic_path):
    """處理單一影像項目資料夾，將其子目錄轉換為 PDF"""
    if not os.path.isdir(comic_path):
        return

    comic_folder_name = os.path.basename(comic_path)
    print(f"\n📂 正在處理項目：{comic_folder_name}")
    print(f"路徑：{comic_path}")

    # 取得項目資料夾下的所有子目錄
    sub_folders = [f for f in os.listdir(comic_path) if os.path.isdir(os.path.join(comic_path, f))]
    
    if not sub_folders:
        print(f"ℹ️  在 {comic_folder_name} 中找不到任何子目錄。")
        return

    for folder in sub_folders:
        folder_path = os.path.join(comic_path, folder)
        
        # 取得圖片檔案
        try:
            images = sorted(
                [
                    f for f in os.listdir(folder_path)
                    if f.lower().endswith((".jpg", ".jpeg", ".png"))
                ],
                key=lambda x: int(os.path.splitext(x)[0]) if os.path.splitext(x)[0].isdigit() else x
            )
        except Exception as e:
            print(f"❌ 讀取資料夾出錯 {folder}: {e}")
            continue

        image_paths = [os.path.join(folder_path, img) for img in images]

        if image_paths:
            match = number_pattern.search(folder)
            if match:
                number = int(match.group(1))
                number_str = f"{number:0{ZERO_PADDING}}"

                if "卷" in folder or "捲" in folder:
                    base_name = f"第{number_str}卷"
                else:
                    base_name = f"第{number_str}話"

                # 取出標題部分並清除關鍵字
                title = re.sub(r'(第)?\d+(話|话|回|卷|捲)?', '', folder).strip()
                # 簡體轉繁體
                title = cc.convert(title)

                if title:
                    filename = f"{comic_folder_name} {base_name}-{title}.pdf"
                else:
                    filename = f"{comic_folder_name} {base_name}.pdf"
            else:
                filename = f"{comic_folder_name} {cc.convert(folder)}.pdf"

            output_pdf = os.path.join(comic_path, filename)

            try:
                with open(output_pdf, "wb") as f:
                    f.write(img2pdf.convert(image_paths))
                print(f"  ✅ 完成：{filename}")
            except Exception as e:
                print(f"  ❌ 轉換失敗 {filename}: {e}")
        else:
            # 略過不含圖片的資料夾，不印出警告以保持畫面整潔
            pass

def main():
    # 設定根目錄為程式所在資料夾
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 取得所有項目資料夾（排除隱藏資料夾）
    comic_folders = sorted([
        f for f in os.listdir(root_dir) 
        if os.path.isdir(os.path.join(root_dir, f)) and not f.startswith('.')
    ])

    if not comic_folders:
        print("❌ 在當前目錄下找不到任何項目資料夾。")
        input("\n按下 Enter 鍵結束...")
        return

    print("========================================")
    print("   影像資料夾 PDF 轉換工具 (多模式支援)")
    print("========================================")
    print(f"當前目錄：{root_dir}")
    print(f"找到 {len(comic_folders)} 個項目資料夾。")
    print("----------------------------------------")
    print("請選擇執行模式：")
    print("[1] 處理所有項目 (自動掃描兩層)")
    print("[2] 手動選取項目 (可多選)")
    print("----------------------------------------")
    
    choice = input("請輸入選項 (1 或 2): ").strip()

    target_folders = []

    if choice == '1':
        target_folders = [os.path.join(root_dir, f) for f in comic_folders]
    elif choice == '2':
        print("\n可用項目清單：")
        for i, folder in enumerate(comic_folders, 1):
            print(f"[{i}] {folder}")
        
        print("\n請輸入編號（多選請用逗號隔開，例如: 1,3,5）：")
        indices_str = input("編號：").strip()
        
        try:
            # 解析輸入，支援逗號與空白
            indices = [int(x.strip()) for x in indices_str.replace('，', ',').split(',') if x.strip().isdigit()]
            for idx in indices:
                if 1 <= idx <= len(comic_folders):
                    target_folders.append(os.path.join(root_dir, comic_folders[idx-1]))
                else:
                    print(f"⚠️ 忽略無效編號：{idx}")
        except ValueError:
            print("❌ 輸入格式錯誤。")
            return
    else:
        print("❌ 無效選項，程式結束。")
        return

    if not target_folders:
        print("⚠️ 未選取任何項目，程式結束。")
        return

    # 開始執行轉換
    print(f"\n🚀 開始處理 {len(target_folders)} 個項目...")
    for folder_path in target_folders:
        convert_comic(folder_path)

    print("\n" + "="*40)
    print("🎉 所有選定任務已完成！")
    print("="*40)
    input("\n按下 Enter 鍵關閉視窗...")

if __name__ == "__main__":
    main()
