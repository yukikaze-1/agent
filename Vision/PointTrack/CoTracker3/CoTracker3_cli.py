import requests
import os
from pathlib import Path

class VideoClient:
    def __init__(self, server_url, input_video_path, output_dir):
        self.server_url = server_url
        self.input_video_path = Path(input_video_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_video_path = self.output_dir / f"processed_{self.input_video_path.name}"

    def upload_and_download_video(self):
        try:
            with self.input_video_path.open("rb") as file:
                files = {"file": (self.input_video_path.name, file, "video/mp4")}
                response = requests.post(self.server_url, files=files)
                response.raise_for_status()
                self.save_processed_video(response.content)
                print(f"处理后的视频已保存到 {self.output_video_path}")
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
        except Exception as e:
            print(f"发生错误: {e}")

    def save_processed_video(self, video_data):
        with self.output_video_path.open("wb") as f:
            f.write(video_data)

if __name__ == "__main__":
    # 定义要上传的视频文件路径和 FastAPI 服务端地址
    video_file_path = "./videos/test.mp4"
    server_url = "http://192.168.1.17:8300/upload_video/"
    output_directory = "./output"

    # 初始化客户端并上传视频
    client = VideoClient(server_url, video_file_path, output_directory)
    client.upload_and_download_video()

# TODO 环境与环境变量，优化代码