# Project:      Agent
# Author:       yomu
# Time:         2024/10/24
# Version:      0.1
# Description:  yolo11 

"""
    目标检测模型
    提供功能：
        1. 识别图像or视频or摄像头中的物体
        
"""

import os
import requests
import logging
import cv2
import io
import numpy as np
import websockets
import asyncio
from dotenv import load_dotenv
from urllib.parse import urljoin
from datetime import datetime

"""
    yolo11的客户端代理类
"""
class YOLO11Agent:
    def __init__(self,
                 env_path: str = None,
                 yolo_server: str = "http://192.168.1.17:8300",
                 output_save_dir: str = "${AGENT_HOME}/Module/Utils/yolo11/output",
                 ):
        """
        初始化 YOLO 客户端，加载环境变量并设置服务器 URL 和保存目录。
        Args:
            Attention!!!:    
                env_path和yolo_server + output_save_dir两者取其一，如果同时有，优先使用env_path中的配置
            env_path: None or str 客户端代理的配置信息 
            yolo_server(str): yolo11服务器ip地址及端口
            output_save_dir(str): yolo客户端代理保存服务端输出的文件夹路径
        """
        if env_path is None :   
            self.output_save_dir = output_save_dir
            self.image_server_url =f"{yolo_server}/predict/image" if not yolo_server.endswith('/') else f"{yolo_server}predict/image"
            self.video_server_url =f"{yolo_server}/predict/video" if not yolo_server.endswith('/') else f"{yolo_server}predict/video"
            self.stream_server_url =f"ws://{yolo_server[7:]}/predict/stream" if yolo_server.startswith("http://") else f"wss://{yolo_server[8:]}/predict/stream"
        else:
            # 从.env文件中加载配置
            self.image_server_url, self.video_server_url, self.stream_server_url, self.output_save_dir = self.load_environment_variables(env_path)    

        

    def load_environment_variables(self, env_path):
        """加载环境变量并设置服务器 URL 和保存目录"""
        load_dotenv(env_path)
        
        yolo_server = os.getenv("YOLO_SERVER")
        if not yolo_server:
            raise ValueError("缺少必要的环境变量：YOLO_SERVER")
        
        image_server_url = f"{yolo_server}/predict/image" if not yolo_server.endswith('/') else f"{yolo_server}predict/image"
        video_server_url = f"{yolo_server}/predict/video" if not yolo_server.endswith('/') else f"{yolo_server}predict/video"
        stream_server_url = f"ws://{yolo_server[7:]}/predict/stream" if yolo_server.startswith("http://") else f"wss://{yolo_server[8:]}/predict/stream"
        
        save_dir = os.getenv("YOLO_CLI_SAVE_DIR")
        if not save_dir:
            save_dir = os.path.join(os.getcwd(), 'output')
            os.makedirs(save_dir, exist_ok=True)
        else:
            os.makedirs(save_dir, exist_ok=True)
        
        return image_server_url, video_server_url, stream_server_url, save_dir

    def _send_image_for_prediction(self, file_path:str, output_filename=None):
        """发送图像文件进行预测"""
        if output_filename is None:
            output_filename = f"predict_{os.path.basename(file_path)}"
        
        if os.path.isfile(file_path):
            try:
                with open(file_path, "rb") as image_file:
                    response = requests.post(self.image_server_url, files={"file": image_file}, timeout=100)

                if response.status_code == 200:
                    output_path = os.path.join(self.output_save_dir, output_filename)
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    print(f"预测后的图片已保存为 {output_path}")
                else:
                    logging.error("请求失败，状态码: %s", response.status_code)
            except requests.exceptions.RequestException as e:
                logging.error("请求过程中出现异常: %s", e)
        else:
            logging.error("文件不存在：%s", file_path)

    def predict_image(self, file_path:str):
        """预测图像"""
        self._send_image_for_prediction(file_path,
                                        output_filename=datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.jpg')

    def _send_video_for_prediction(self, file_path:str, output_filename=None):
        """发送视频文件进行预测"""
        if output_filename is None:
            output_filename = f"predict_{os.path.basename(file_path)}"
        
        if os.path.isfile(file_path):
            try:
                with open(file_path, "rb") as video_file:
                    response = requests.post(self.video_server_url, files={"file": video_file}, timeout=1000)

                if response.status_code == 200:
                    output_path = os.path.join(self.output_save_dir, output_filename)
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    print(f"预测后的视频已保存为 {output_path}")
                else:
                    logging.error("请求失败，状态码: %s", response.status_code)
            except requests.exceptions.RequestException as e:
                logging.error("请求过程中出现异常: %s", e)
        else:
            logging.error("文件不存在：%s", file_path)

    def predict_video(self, file_path:str):
        """预测视频"""
        self._send_video_for_prediction(file_path)

    def predict_from_webcam(self):
        """从摄像头进行预测"""
        asyncio.run(self._stream_webcam())

    async def _stream_webcam(self):
        """异步处理摄像头视频流预测"""
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not cap.isOpened():
            logging.error("无法打开摄像头")
            return

        output_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '_predicted.avi'
        output_path = os.path.join(self.output_save_dir, output_filename)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(output_path, fourcc, 20.0, (640, 480))

        try:
            async with websockets.connect(self.stream_server_url) as websocket:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        logging.error("无法读取摄像头画面")
                        break

                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_bytes = buffer.tobytes()

                    await websocket.send(frame_bytes)

                    predicted_frame_bytes = await websocket.recv()
                    predicted_frame = cv2.imdecode(np.frombuffer(predicted_frame_bytes, np.uint8), cv2.IMREAD_COLOR)

                    cv2.imshow("Predicted Frame", predicted_frame)
                    out.write(predicted_frame)

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
        except Exception as e:
            logging.error("WebSocket连接出错: %s", e)
        finally:
            cap.release()
            out.release()
            cv2.destroyAllWindows()

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# def main():
#     agent = YOLO11Agent()
#     print("init end")
#     print("runiing for image")
#     agent.predict_image("/home/yomu/data/picture/photo/test.jpg")
#     agent.predict_video("/home/yomu/data/video/test.mp4")
#     agent.predict_from_webcam()

if __name__ == "__main__":
    print("This is a module,should not run directly.Do nothing")
    # main()
    
    