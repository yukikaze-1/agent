import requests
import sys
import os
from datetime import datetime

# TODO 将服务器地址抽离出来，再优化下这份代码

def upload_image(file_path, language='zh'):
    url = "http://192.168.1.17:8200/ocr/"
    files = {'file': open(file_path, 'rb')}
    params = {'language': language}
    
    response = requests.post(url, files=files, params=params)
    
    if response.status_code == 200:
        response.raise_for_status()
        result = response.json()

        # 获取当前时间并格式化为文件名
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = "./output"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{current_time}.json")

        # 保存结果到文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(response.text)

        # 额外保存所有的 text 到一个 txt 文件中
        text_output_path = os.path.join(output_dir, f"{current_time}.txt")
        with open(text_output_path, 'w', encoding='utf-8') as f:
            for item in result:
                for text_line in item.get("text_lines", []):
                    f.write(text_line.get("text", "") + "\n")

        print("OCR Result saved to:", output_path)
        print("Text extracted and saved to:", text_output_path)
    else:
        print(f"请求失败，状态码: {response.status_code}, 信息: {response.text}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ocr_client.py <image_path> [language]")
        sys.exit(1)

    image_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else 'en'
    upload_image(image_path, language)
