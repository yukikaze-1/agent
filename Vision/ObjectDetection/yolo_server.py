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
import websockets

app = FastAPI()

# 使用命令行参数指定模型路径，默认为 yolo11n.pt
import argparse
parser = argparse.ArgumentParser(description="YOLO FastAPI Server")
parser.add_argument("--port", type=int, default=8000, help="运行服务器的端口")
parser.add_argument("--model", "-m", type=str, default="./models/yolo11n.pt", help="YOLO 模型路径")
args = parser.parse_args()

model = YOLO(args.model)  # 加载 YOLO 模型

@app.post("/predict/image")
async def predict_image(file: UploadFile = File(...)):
    os.makedirs("temp", exist_ok=True)  # 创建临时目录（如果不存在）
    
    file_location = f"temp/{file.filename}"  # 将上传的文件保存到临时目录
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    results = model(file_location)  # 使用 YOLO 模型进行预测
    
    output_image = BytesIO()  # 创建一个内存缓冲区来保存预测后的图像
    annotated_image = results[0].plot()  # 绘制预测结果
    image = Image.fromarray(annotated_image[:, :, ::-1])  # 将 BGR 转换为 RGB
    image.save(output_image, format="JPEG")  # 将图像保存到内存缓冲区
    output_image.seek(0)
    
    return StreamingResponse(output_image, media_type="image/jpeg", headers={"Content-Disposition": f"attachment; filename=predicted_{file.filename}"})  # 返回预测后的图像

@app.post("/predict/video")
async def predict_video(file: UploadFile = File(...)):
    os.makedirs("temp", exist_ok=True)  # 创建临时目录（如果不存在）
    
    file_location = f"temp/{file.filename}"  # 将上传的文件保存到临时目录
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    output_video_location = f"temp/predicted_{file.filename}"  # 输出视频文件的位置
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # 设置视频编码格式
    cap = cv2.VideoCapture(file_location)  # 打开视频文件
    out = cv2.VideoWriter(output_video_location, fourcc, cap.get(cv2.CAP_PROP_FPS), (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))  # 创建视频写入器
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        results = model(frame)  # 使用 YOLO 模型对帧进行预测
        annotated_frame = results[0].plot()  # 绘制预测结果到帧上
        out.write(annotated_frame)  # 将带有预测结果的帧写入输出视频
    
    cap.release()  # 释放视频读取器
    out.release()  # 释放视频写入器
    
    return StreamingResponse(open(output_video_location, "rb"), media_type="video/mp4", headers={"Content-Disposition": f"attachment; filename=predicted_{file.filename}"})  # 返回预测后的视频

@app.websocket("/predict/stream")
async def predict_stream(websocket: WebSocket):
    await websocket.accept()  # 接受 WebSocket 连接
    
    try:
        while True:
            # 接收客户端发送的帧数据
            frame_bytes = await websocket.receive_bytes()
            
            # 将字节数据转换为 NumPy 数组
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # 使用 YOLO 模型进行预测
            results = model(frame)
            annotated_frame = results[0].plot()  # 绘制预测结果
            
            # 将带有预测结果的帧编码为 JPEG 格式
            _, buffer = cv2.imencode('.jpg', annotated_frame)
            
            # 通过 WebSocket 发送预测后的帧
            await websocket.send_bytes(buffer.tobytes())
    except WebSocketDisconnect:
        print("客户端断开了连接")
    except Exception as e:
        print(f"WebSocket连接出错: {e}")
    finally:
        if not websocket.client_state.name == "DISCONNECTED":
            await websocket.close()  # 关闭 WebSocket 连接

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=args.port, ws='auto')
