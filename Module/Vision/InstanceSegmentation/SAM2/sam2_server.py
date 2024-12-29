from fastapi import FastAPI, UploadFile, File, HTTPException, Response, Form
from pydantic import BaseModel
import uvicorn
import numpy as np
import torch
from PIL import Image
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
import io
import os
import argparse
import random
import json
import matplotlib.pyplot as plt
import zipfile
import cv2

# 解析命令行参数
parser = argparse.ArgumentParser(description="Start SAM2 FastAPI server with specified model checkpoint and config.")
parser.add_argument('--checkpoint', '-m', type=str, default='./checkpoints/sam2.1_hiera_large.pt', help="Path to the SAM2 checkpoint file.")
parser.add_argument('--config', '-c', type=str, default='./configs/sam2.1/sam2.1_hiera_l.yaml', help="Path to the model config file.")
args = parser.parse_args()

# 创建FastAPI应用
app = FastAPI()

# 选择用于计算的设备
if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")
print(f"using device: {device}")

# 设置模型和配置文件的路径
sam2_checkpoint = args.checkpoint
model_cfg = args.config

# 加载模型和配置文件
sam2_model = build_sam2(model_cfg, sam2_checkpoint, device=device)
predictor = SAM2ImagePredictor(sam2_model)

# 定义请求体的数据格式
class PointRequest(BaseModel):
    x: int
    y: int
    label: int

# 定义渲染函数

def show_mask(mask, ax, random_color=False, borders=True):
    if random_color:
        color = np.concatenate([np.random.random(3), np.array([0.6])], axis=0)
    else:
        color = np.array([30/255, 144/255, 255/255, 0.6])
    h, w = mask.shape[-2:]
    mask = mask.astype(np.uint8)
    mask_image = mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
    if borders:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        contours = [cv2.approxPolyDP(contour, epsilon=0.01, closed=True) for contour in contours]
        mask_image = cv2.drawContours(mask_image, contours, -1, (1, 1, 1, 0.5), thickness=2)
    ax.imshow(mask_image)

def show_points(coords, labels, ax, marker_size=375):
    pos_points = coords[labels == 1]
    neg_points = coords[labels == 0]
    ax.scatter(pos_points[:, 0], pos_points[:, 1], color='green', marker='*', s=marker_size, edgecolor='white', linewidth=1.25)
    ax.scatter(neg_points[:, 0], neg_points[:, 1], color='red', marker='*', s=marker_size, edgecolor='white', linewidth=1.25)

@app.post("/predict/image")
async def predict_mask(file: UploadFile = File(...), points: str = Form(...)):
    # 读取上传的图片文件
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = np.array(image)

    # 设置标记点和标签
    points_data = json.loads(points)
    input_points = [[point['x'], point['y']] for point in points_data]
    input_labels = [point['label'] for point in points_data]
    input_point = np.array(input_points)
    input_label = np.array(input_labels)

    # 绑定图片到模型
    predictor.set_image(image)

    # 进行预测
    with torch.amp.autocast('cuda', enabled=False):
        masks, scores, logits = predictor.predict(
            point_coords=input_point,
            point_labels=input_label,
            multimask_output=True,
        )

    # 使用matplotlib分别渲染每个掩码
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for i, (mask, score) in enumerate(zip(masks, scores)):
            fig, ax = plt.subplots(figsize=(image.shape[1] / 100, image.shape[0] / 100))
            ax.imshow(image, aspect='auto')

            # 显示掩码
            show_mask(mask, ax, random_color=True, borders=True)

            # 显示标记点和置信度
            show_points(input_point, input_label, ax)
            ax.set_title(f"Mask {i+1}, Score: {score:.3f}", fontsize=18)

            plt.axis('off')
            buf = io.BytesIO()
            plt.savefig(buf, format="PNG", dpi=300, bbox_inches='tight', pad_inches=0)
            plt.close(fig)
            buf.seek(0)

            # 将每个渲染结果保存到zip文件中
            zip_file.writestr(f'mask_{i+1}.png', buf.getvalue())

    zip_buffer.seek(0)

    # 返回包含所有掩码渲染的zip文件
    return Response(content=zip_buffer.getvalue(), media_type="application/zip", headers={"Content-Disposition": "attachment; filename=masks.zip"})

if __name__ == "__main__":
    # 启动FastAPI服务器
    uvicorn.run(app, host="127.0.0.1", port=8100)


# TODO 刚一直过来，还没进行测试与环境配置