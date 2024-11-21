# Project:      Agent
# Author:       yomu
# Time:         2024/11/08
# Version:      0.1
# Description:  agent Vision CoTracker3 server

# CoTracker3部署在服务器，采用C/S方式，大模型只作为客户端
# 以下代码仅供参考，最新的代码见 ~/Cotracker3/CoTracker3_server.py





import torch
import imageio.v3 as iio
from cotracker.utils.visualizer import Visualizer
from fastapi import FastAPI, UploadFile, File, Response
import uvicorn
import os

app = FastAPI()

device = 'cuda' if torch.cuda.is_available() else 'cpu'
cotracker = torch.hub.load("facebookresearch/co-tracker", "cotracker3_offline", source='github').to(device)

@app.post("/upload_video/")
async def upload_video(file: UploadFile = File(...)):
    # 临时保存上传的视频
    video_path = f"./temp/{file.filename}"
    os.makedirs("./temp", exist_ok=True)
    
    with open(video_path, "wb") as f:
        f.write(await file.read())

    # 读取视频帧
    frames = iio.imread(video_path, plugin="FFMPEG")
    grid_size = 10

    # 降低视频分辨率以减少显存占用
    frames = frames[::2, ::2, ::2, :]
    # 将视频帧转换为 Tensor 并移动到设备上
    video = torch.tensor(frames).permute(0, 3, 1, 2)[None].float().to(device)  # B T C H W

    # 使用 torch.no_grad() 以减少显存占用
    with torch.no_grad():
        # 运行跟踪
        pred_tracks, pred_visibility = cotracker(video, grid_size=grid_size)

    # 可视化跟踪结果并保存
    vis = Visualizer(save_dir="./saved_videos", pad_value=120, linewidth=3)
    vis.visualize(video, pred_tracks, pred_visibility)
    
    with open("./saved_videos/video.mp4", "rb") as f:
        video_data = f.read()

    os.remove(video_path)

    return Response(content=video_data, media_type="video/mp4")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8300)
