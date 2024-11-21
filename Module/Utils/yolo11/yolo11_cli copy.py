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

def load_environment_variables(env_path="./.env"):
    # 从指定的 .env 文件加载环境变量
    load_dotenv(env_path)
    
    # 构造服务器 URL，将基础 YOLO 服务器 URL 与 'predict' 端点连接起来
    yolo_server = os.getenv("YOLO_SERVER")
    if not yolo_server:
        raise ValueError("缺少必要的环境变量：YOLO_SERVER")
    image_server_url = f"{yolo_server}/predict/image" if not yolo_server.endswith('/') else f"{yolo_server}predict/image"
    video_server_url = f"{yolo_server}/predict/video" if not yolo_server.endswith('/') else f"{yolo_server}predict/video"
    stream_server_url = f"ws://{yolo_server[7:]}/predict/stream" if yolo_server.startswith("http://") else f"wss://{yolo_server[8:]}/predict/stream"
    
    # 获取保存预测结果的目录
    save_dir = os.getenv("YOLO_CLI_SAVE_DIR")
    if not save_dir:
        # 如果未指定保存目录，则在当前文件夹中创建一个 'predict' 文件夹并使用该文件夹
        save_dir = os.path.join(os.getcwd(), 'predict')
        os.makedirs(save_dir, exist_ok=True)
    else:
        # 确保保存目录存在
        os.makedirs(save_dir, exist_ok=True)
    
    return image_server_url, video_server_url, stream_server_url, save_dir

from datetime import datetime

def send_image_for_prediction(server_url, file_path, save_dir, output_filename=None):
    # 如果没有指定输出文件名，则使用原视频名称并加上 'predict_' 前缀
    if output_filename is None:
        output_filename = f"predict_{os.path.basename(file_path)}"
    # 检查指定的文件路径是否存在且是一个文件
    if os.path.isfile(file_path):
        try:
            # 以二进制模式打开图像文件并将其发送到服务器进行预测
            with open(file_path, "rb") as image_file:
                response = requests.post(server_url, files={"file": image_file}, timeout=100)

            # 如果响应成功，则将预测后的图像保存到指定的目录
            if response.status_code == 200:
                output_path = os.path.join(save_dir, output_filename)
                with open(output_path, "wb") as f:
                    f.write(response.content)
                print(f"预测后的图片已保存为 {output_path}")
            else:
                # 如果请求失败，则记录错误消息
                logging.error("请求失败，状态码: %s", response.status_code)
        except requests.exceptions.RequestException as e:
            # 捕获请求异常并记录错误
            logging.error("请求过程中出现异常: %s", e)
    else:
        # 如果文件不存在，则记录错误消息
        logging.error("文件不存在：%s", file_path)

def predict_image(file_path):
    # 加载环境变量并获取服务器 URL 和保存目录
    image_server_url, _, _, save_dir = load_environment_variables()
    # 调用 send_image_for_prediction 函数进行预测
    send_image_for_prediction(image_server_url, file_path, save_dir, output_filename=datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.jpg')

def send_video_for_prediction(server_url, file_path, save_dir, output_filename=None):
    # 如果没有指定输出文件名，则使用原视频名称并加上 'predict_' 前缀
    if output_filename is None:
        output_filename = f"predict_{os.path.basename(file_path)}"
    # 检查指定的文件路径是否存在且是一个文件
    if os.path.isfile(file_path):
        try:
            # 以二进制模式打开视频文件并将其发送到服务器进行预测
            with open(file_path, "rb") as video_file:
                response = requests.post(server_url, files={"file": video_file}, timeout=100)

            # 如果响应成功，则将预测后的视频保存到指定的目录
            if response.status_code == 200:
                output_path = os.path.join(save_dir, output_filename)
                with open(output_path, "wb") as f:
                    f.write(response.content)
                print(f"预测后的视频已保存为 {output_path}")
            else:
                # 如果请求失败，则记录错误消息
                logging.error("请求失败，状态码: %s", response.status_code)
        except requests.exceptions.RequestException as e:
            # 捕获请求异常并记录错误
            logging.error("请求过程中出现异常: %s", e)
    else:
        # 如果文件不存在，则记录错误消息
        logging.error("文件不存在：%s", file_path)

def predict_video(file_path):
    # 加载环境变量并获取服务器 URL 和保存目录
    _, video_server_url, _, save_dir = load_environment_variables()
    # 调用 send_video_for_prediction 函数进行预测
    send_video_for_prediction(video_server_url, file_path, save_dir)

def predict_from_webcam():
    # 加载环境变量并获取服务器 URL 和保存目录
    _, _, stream_server_url, save_dir = load_environment_variables()
    
    async def stream_webcam():
        # 使用 OpenCV 访问本地摄像头
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # 设置摄像头宽度
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # 设置摄像头高度
        if not cap.isOpened():
            logging.error("无法打开摄像头")
            return

        # 定义视频编解码器并创建 VideoWriter 对象以保存预测视频
        output_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '_predicted.avi'
        output_path = os.path.join(save_dir, output_filename)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(output_path, fourcc, 20.0, (640, 480))

        try:
            async with websockets.connect(stream_server_url) as websocket:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        logging.error("无法读取摄像头画面")
                        break

                    # 将帧编码为 JPEG 格式
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_bytes = buffer.tobytes()

                    # 将帧发送到服务器进行预测
                    await websocket.send(frame_bytes)

                    # 接收预测后的帧
                    predicted_frame_bytes = await websocket.recv()
                    predicted_frame = cv2.imdecode(np.frombuffer(predicted_frame_bytes, np.uint8), cv2.IMREAD_COLOR)

                    # 显示预测后的帧
                    cv2.imshow("Predicted Frame", predicted_frame)

                    # 将预测后的帧写入视频文件
                    out.write(predicted_frame)

                    # 按下 'q' 键退出
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
        except Exception as e:
            logging.error("WebSocket连接出错: %s", e)
        finally:
            # 释放摄像头资源、关闭所有 OpenCV 窗口，并释放 VideoWriter 对象
            cap.release()
            out.release()
            cv2.destroyAllWindows()

    asyncio.run(stream_webcam())

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
