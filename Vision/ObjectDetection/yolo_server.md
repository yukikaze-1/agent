# YOLO FastAPI 服务器使用说明

## 简介
本项目是一个基于 FastAPI 的服务器，用于处理图像和视频的目标检测。它使用 YOLO（You Only Look Once）深度学习模型来预测上传的图像或视频中的物体。用户可以通过 HTTP 请求上传文件或者通过 WebSocket 实现实时视频流的目标检测。模型文件可以通过命令行参数指定，默认使用 `yolo11n.pt`。

## 运行环境

### 必要依赖
1. Python 3.7 或以上版本
2. FastAPI
3. Uvicorn
4. OpenCV (`cv2`)
5. PIL (Pillow)
6. Ultralyctics YOLO 模型库
7. Websockets

使用以下命令安装依赖：
```bash
pip install fastapi uvicorn opencv-python pillow ultralytics websockets
```

## 启动服务器
使用命令行启动服务器，允许指定运行端口和模型路径。

```bash
python yolo_server.py --port 8000 --model ./models/yolo_custom.pt
```
- `--port` (`-p`)：可选参数，指定服务器运行的端口，默认为 `8000`。
- `--model` (`-m`)：可选参数，指定 YOLO 模型文件路径，默认为 `./models/yolo11n.pt`。

## 接口说明

### 1. `/predict/image` （POST）
- **功能**：对上传的图像文件进行目标检测，返回带有检测结果的图像。
- **请求参数**：
  - `file` (`UploadFile`)：要上传的图像文件。
- **返回**：
  - 带有预测结果的 JPEG 图像。

#### 示例请求
```bash
curl -X POST -F "file=@your_image.jpg" http://localhost:8000/predict/image -o output.jpg
```

### 2. `/predict/video` （POST）
- **功能**：对上传的视频文件进行目标检测，返回带有检测结果的视频。
- **请求参数**：
  - `file` (`UploadFile`)：要上传的视频文件。
- **返回**：
  - 带有预测结果的 MP4 视频。

#### 示例请求
```bash
curl -X POST -F "file=@your_video.mp4" http://localhost:8000/predict/video -o output.mp4
```

### 3. `/predict/stream` （WebSocket）
- **功能**：处理来自客户端的实时视频流，对每一帧进行目标检测，并将结果实时返回。
- **WebSocket 连接**：
  - 客户端通过 WebSocket 连接发送每一帧图像，服务器对图像进行检测，并将带有检测结果的帧返回。

#### 客户端示例代码
```python
import asyncio
import websockets
import cv2
import numpy as np

async def send_video():
    uri = "ws://localhost:8000/predict/stream"
    async with websockets.connect(uri) as websocket:
        cap = cv2.VideoCapture(0)  # 打开摄像头
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                _, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                
                await websocket.send(frame_bytes)
                predicted_frame_bytes = await websocket.recv()
                
                nparr = np.frombuffer(predicted_frame_bytes, np.uint8)
                predicted_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                cv2.imshow("YOLO Prediction", predicted_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

asyncio.run(send_video())
```

## 错误处理
- 当客户端断开 WebSocket 连接时，服务器将显示 `客户端断开了连接`，以更好地提示用户。
- 其他异常将记录在服务器日志中，以便于调试。

## 注意事项
- 确保在服务器中加载的模型文件路径正确有效。
- 默认的 `yolo11n.pt` 模型需要存在于指定目录中，或通过 `--model` 参数指定正确的模型路径。
- 确保视频流输入的帧率和分辨率符合系统性能要求，以避免延迟过高。

