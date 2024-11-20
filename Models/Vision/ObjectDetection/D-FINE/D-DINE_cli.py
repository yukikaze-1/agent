import requests
import os
from tqdm import tqdm

# TODO 修改配置

# 定义服务器地址和端口
BASE_URL = "http://192.168.1.17:8000"

# 图像推理函数
def infer_image(image_path):
    url = f"{BASE_URL}/infer/image"
    if not os.path.exists(image_path):
        print("图像文件不存在。")
        return

    # 打开图像文件并发送请求
    with open(image_path, "rb") as image_file:
        files = {"file": (os.path.basename(image_path), image_file, "image/jpeg")}
        response = requests.post(url, files=files)

    # 处理响应
    if response.status_code == 200:
        # 将结果保存到本地
        result_path = f"./results/result_{os.path.basename(image_path)}"
        with open(result_path, 'wb') as result_file:
            result_file.write(response.content)
        print("结果已保存为:", result_path)
    else:
        print("请求失败，状态码:", response.status_code)

# 视频推理函数
def infer_video(video_path):
    url = f"{BASE_URL}/infer/video"
    if not os.path.exists(video_path):
        print("视频文件不存在。")
        return

    # 获取视频文件大小
    video_size = os.path.getsize(video_path)

    # 打开视频文件并发送请求
    with open(video_path, "rb") as video_file:
        files = {"file": (os.path.basename(video_path), video_file, "video/mp4")}
        response = requests.post(url, files=files, stream=True)

    # 处理响应
    if response.status_code == 200:
        # 将结果保存到本地
        total_size = int(response.headers.get('content-length', 0))
        result_path = f"./results/result_{os.path.basename(video_path)}"
        with open(result_path, 'wb') as result_file:
            for chunk in response.iter_content(chunk_size=65536):
                result_file.write(chunk)
        print("结果已保存为:", result_path)
    else:
        print("请求失败，状态码:", response.status_code)

# 主函数
def main():
    # 示例调用
    image_path = "./images/test.jpg"
    video_path = "./videos/test.mp4"

    # 创建结果保存目录
    if not os.path.exists("./results"):
        os.makedirs("./results")

    print("图像推理:")
    infer_image(image_path)

    print("\n视频推理:")
    infer_video(video_path)

if __name__ == "__main__":
    main()
