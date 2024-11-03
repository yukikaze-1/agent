# YOLO 预测脚本说明文档

## 概述
该脚本提供了将图像、视频或摄像头流发送到 YOLO（You Only Look Once）服务器进行目标检测的功能。用户可以对图像、视频以及实时摄像头画面进行目标预测，并将结果保存在本地以便进一步使用或分析。脚本提供以下功能：

1. 对图像文件中的目标进行预测。
2. 对视频文件中的目标进行预测。
3. 对实时摄像头画面中的目标进行预测，并保存预测视频。

## 依赖项
该脚本需要以下依赖项：

- Python 3
- `os`（标准库，用于文件操作）
- `requests`（用于向 YOLO 服务器发出 HTTP 请求）
- `logging`（用于记录错误和信息）
- `cv2`（OpenCV，用于视频捕获和图像操作）
- `numpy`（用于处理图像数据）
- `websockets`（用于管理实时流的 WebSocket 连接）
- `asyncio`（用于管理异步操作）
- `dotenv`（用于从 `.env` 文件加载环境变量）

可以使用以下命令安装所需的依赖项：
```sh
pip install requests opencv-python numpy websockets python-dotenv
```

## 环境变量
该脚本使用定义在 `.env` 文件中的环境变量来配置 YOLO 服务器的 URL 和保存结果的目录。需要以下变量：

- **YOLO_SERVER**：YOLO 服务器的基础 URL。
- **YOLO_CLI_SAVE_DIR**：保存预测结果的目录。如果未指定，将在当前工作目录下创建一个名为 `predict` 的默认目录。

## 函数说明

### 1. `load_environment_variables(env_path="./.env")`
该函数从指定的 `.env` 文件加载环境变量，并构造 YOLO 服务器端点的 URL。同时确保结果保存目录的存在。

- **参数**：`env_path` - `.env` 文件的路径（默认为 `./.env`）。
- **返回**：用于图像、视频和流预测的 URL 以及保存目录。

### 2. `send_image_for_prediction(server_url, file_path, save_dir, output_filename=None)`
该函数将图像发送到 YOLO 服务器进行预测，并保存预测结果。

- **参数**：
  - `server_url`：YOLO 服务器的图像预测端点的 URL。
  - `file_path`：要预测的图像文件的路径。
  - `save_dir`：保存预测结果的目录。
  - `output_filename`：输出文件的名称（可选）。

### 3. `predict_image(file_path)`
这是一个面向用户的函数，使用 `send_image_for_prediction` 将图像发送到 YOLO 服务器进行预测。

- **参数**：`file_path` - 图像文件的路径。

### 4. `send_video_for_prediction(server_url, file_path, save_dir, output_filename=None)`
该函数将视频发送到 YOLO 服务器进行预测，并保存预测结果。

- **参数**：
  - `server_url`：YOLO 服务器的视频预测端点的 URL。
  - `file_path`：要预测的视频文件的路径。
  - `save_dir`：保存预测结果的目录。
  - `output_filename`：输出文件的名称（可选）。

### 5. `predict_video(file_path)`
这是一个面向用户的函数，使用 `send_video_for_prediction` 将视频发送到 YOLO 服务器进行预测。

- **参数**：`file_path` - 视频文件的路径。

### 6. `predict_from_webcam()`
该函数从摄像头捕获画面，将其发送到 YOLO 服务器进行预测，并实时显示预测后的画面。预测视频也会被保存在本地。

- **参数**：无。
- **注意**：输出视频以 `.avi` 格式保存，使用 `XVID` 编解码器。

### 异步摄像头流处理
`predict_from_webcam` 中的 `stream_webcam()` 函数使用 WebSocket 与 YOLO 服务器建立异步连接。它从摄像头捕获画面，将其发送到服务器进行预测，接收预测后的画面，然后进行显示并保存。

## 如何使用脚本
1. **环境设置**：在脚本所在目录创建一个 `.env` 文件，内容如下：
   ```
   YOLO_SERVER=http://<your_yolo_server_url>
   YOLO_CLI_SAVE_DIR=./predictions
   ```
   将 `<your_yolo_server_url>` 替换为 YOLO 服务器的 URL。

2. **运行脚本**：使用以下命令之一运行不同的功能：
   - 预测图像：
     ```python
     predict_image("path/to/your/image.jpg")
     ```
   - 预测视频：
     ```python
     predict_video("path/to/your/video.mp4")
     ```
   - 实时预测摄像头画面：
     ```python
     predict_from_webcam()
     ```

3. **输出**：预测结果将保存在 `YOLO_CLI_SAVE_DIR` 指定的目录中，如果未指定，则保存在默认的 `predict` 文件夹中。

## 错误处理
该脚本包括以下场景的错误处理：
- 缺少环境变量：如果未定义 `YOLO_SERVER`，则抛出 `ValueError`。
- 文件不存在：如果指定的文件不存在，则记录错误。
- 请求错误：记录失败的 HTTP 请求或 WebSocket 问题的错误。
- 摄像头问题：如果无法访问摄像头或读取画面，则记录错误。

## 日志记录
该脚本使用 `logging` 模块记录重要事件，包括错误和状态更新。日志以时间戳、日志级别和消息的形式显示在控制台中。

## 注意事项
- 请确保 YOLO 服务器正在运行且可以从运行该脚本的机器访问。
- 摄像头预测功能使用 WebSockets，这要求 YOLO 服务器支持实时流的 WebSocket 连接。
- 脚本目前设置为使用 `XVID` 编解码器将预测后的画面保存为 `.avi` 视频文件。如果需要，可以根据需要调整不同的编解码器或格式。

请根据您的具体需求自定义该脚本！

