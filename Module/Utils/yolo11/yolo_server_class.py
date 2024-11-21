from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from ultralytics import YOLO
import uvicorn
import shutil
import os
from io import BytesIO
from PIL import Image
import cv2
import numpy as np
import argparse

"""
    YOLO11的fastapi服务端，封装在一个类中
        默认监听0.0.0.0
        默认端口8300
        默认模型为yolo11n.pt
    注意：
        该文件应在agent启动时一并启动或者在需要时才启动！！！
"""



class YOLOServer:
    def __init__(self, 
                 model_path: str = "home/yomu/agent/Module/Utils/yolo11/models/yolo11n.pt",
                 host: str = "0.0.0.0",
                 port: int = 8300):
        """
        初始化 YOLO 服务器。

        :param model_path: YOLO 模型的路径
        :param port: 服务器运行的端口
        """
        self.app = FastAPI()  # 创建 FastAPI 应用实例
        self.model = YOLO(model_path)  # 加载 YOLO 模型
        self.host = host    
        self.port = port  # 设置服务器端口
        self.setup_routes()  # 设置路由

    def setup_routes(self):
        """设置 API 路由"""
        @self.app.post("/predict/image")
        async def predict_image(file: UploadFile = File(...)):
            """处理图像预测请求"""
            return await self._predict_image(file)

        @self.app.post("/predict/video")
        async def predict_video(file: UploadFile = File(...)):
            """处理视频预测请求"""
            return await self._predict_video(file)

        @self.app.websocket("/predict/stream")
        async def predict_stream(websocket: WebSocket):
            """处理视频流预测请求"""
            await self._predict_stream(websocket)

    async def _predict_image(self, file: UploadFile):
        """
        处理图像文件的预测。

        :param file: 上传的图像文件
        :return: 带有预测结果的图像
        """
        os.makedirs("temp", exist_ok=True)  # 创建临时目录
        file_location = f"temp/{file.filename}"  # 保存上传文件的位置
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)  # 将上传的文件保存到本地

        results = self.model(file_location)  # 使用 YOLO 模型进行预测
        output_image = BytesIO()  # 创建内存缓冲区
        annotated_image = results[0].plot()  # 绘制预测结果
        image = Image.fromarray(annotated_image[:, :, ::-1])  # 将 BGR 转换为 RGB
        image.save(output_image, format="JPEG")  # 保存图像到缓冲区
        output_image.seek(0)

        return StreamingResponse(output_image, media_type="image/jpeg", headers={"Content-Disposition": f"attachment; filename=predicted_{file.filename}"})

    async def _predict_video(self, file: UploadFile):
        """
        处理视频文件的预测。

        :param file: 上传的视频文件
        :return: 带有预测结果的视频
        """
        os.makedirs("temp", exist_ok=True)  # 创建临时目录
        file_location = f"temp/{file.filename}"  # 保存上传文件的位置
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)  # 将上传的视频文件保存到本地

        output_video_location = f"temp/predicted_{file.filename}"  # 输出视频文件的位置
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # 设置视频编码格式
        cap = cv2.VideoCapture(file_location)  # 打开视频文件
        out = cv2.VideoWriter(output_video_location, fourcc, cap.get(cv2.CAP_PROP_FPS), (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))  # 创建视频写入器

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            results = self.model(frame)  # 使用 YOLO 模型对帧进行预测
            annotated_frame = results[0].plot()  # 绘制预测结果到帧上
            out.write(annotated_frame)  # 将带有预测结果的帧写入输出视频

        cap.release()  # 释放视频读取器
        out.release()  # 释放视频写入器

        return StreamingResponse(open(output_video_location, "rb"), media_type="video/mp4", headers={"Content-Disposition": f"attachment; filename=predicted_{file.filename}"})

    async def _predict_stream(self, websocket: WebSocket):
        """
        处理视频流的预测。

        :param websocket: WebSocket 连接
        """
        await websocket.accept()  # 接受 WebSocket 连接
        try:
            while True:
                frame_bytes = await websocket.receive_bytes()  # 接收客户端发送的帧数据
                nparr = np.frombuffer(frame_bytes, np.uint8)  # 将字节数据转换为 NumPy 数组
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)  # 解码为图像

                results = self.model(frame)  # 使用 YOLO 模型进行预测
                annotated_frame = results[0].plot()  # 绘制预测结果
                _, buffer = cv2.imencode('.jpg', annotated_frame)  # 将帧编码为 JPEG 格式

                await websocket.send_bytes(buffer.tobytes())  # 通过 WebSocket 发送预测后的帧
        except WebSocketDisconnect:
            print("客户端断开了连接")
        except Exception as e:
            print(f"WebSocket连接出错: {e}")
        finally:
            if not websocket.client_state.name == "DISCONNECTED":
                await websocket.close()  # 关闭 WebSocket 连接

    def run(self):
        """运行 YOLO 服务器"""
        uvicorn.run(self.app, host=self.host, port=self.port, ws='auto')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO FastAPI Server")
    parser.add_argument("--port","-p", type=int, default=8300, help="运行服务器的端口")
    parser.add_argument("--host","-h",type=str,default="0.0.0.0",help="host")
    parser.add_argument("--model","-m", type=str, default="./models/yolo11n.pt", help="YOLO 模型路径")
    args = parser.parse_args()

    yoloserver = YOLOServer(model_path=args.model,host=args.host, port=args.port)  # 创建 YOLO 服务器实例
    yoloserver.run()  # 运行服务器
