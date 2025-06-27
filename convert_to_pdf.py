import os
import img2pdf
import re
from opencc import OpenCC

# 初始化簡體轉繁體
cc = OpenCC('s2t')

# 設定圖片根目錄為程式所在資料夾
root_dir = os.path.dirname(os.path.abspath(__file__))

# 取得根目錄資料夾名稱（最後一層）
root_folder_name = os.path.basename(root_dir)

# 正則表達式，抓取數字
number_pattern = re.compile(r'(\d+)')

# 預先掃描所有資料夾取得最大數字，決定補零長度
all_numbers = []

for folder in os.listdir(root_dir):
    match = number_pattern.search(folder)
    if match:
        all_numbers.append(int(match.group(1)))

# 決定補零位數，至少3位
if all_numbers:
    zero_padding = max(3, len(str(max(all_numbers))))
else:
    zero_padding = 3

print(f"數字補零至 {zero_padding} 位數。")
print(f"開始轉換，圖片資料夾：{root_dir}")

for folder in os.listdir(root_dir):
    folder_path = os.path.join(root_dir, folder)
    if os.path.isdir(folder_path):
        # 取得圖片檔案
        images = sorted(
            [
                f for f in os.listdir(folder_path)
                if f.lower().endswith((".jpg", ".jpeg", ".png"))
            ],
            key=lambda x: int(os.path.splitext(x)[0]) if os.path.splitext(x)[0].isdigit() else x
        )
        image_paths = [os.path.join(folder_path, img) for img in images]

        if image_paths:
            match = number_pattern.search(folder)
            if match:
                number = int(match.group(1))
                number_str = f"{number:0{zero_padding}}"

                if "卷" in folder or "捲" in folder:
                    base_name = f"第{number_str}卷"
                else:
                    base_name = f"第{number_str}話"

                # 取出標題部分
                title = re.sub(r'(第)?\d+(話|话|回|卷|捲)?', '', folder).strip()

                # 簡體轉繁體
                title = cc.convert(title)

                if title:
                    filename = f"{root_folder_name} {base_name}-{title}.pdf"
                else:
                    filename = f"{root_folder_name} {base_name}.pdf"

            else:
                filename = f"{root_folder_name} {cc.convert(folder)}.pdf"

            output_pdf = os.path.join(root_dir, filename)

            with open(output_pdf, "wb") as f:
                f.write(img2pdf.convert(image_paths))

            print(f"✅ 完成：{filename}")
        else:
            print(f"⚠️ 沒有找到圖片：{folder}")

print("🎉 全部轉換完成。按下 Enter 關閉視窗。")
input()
