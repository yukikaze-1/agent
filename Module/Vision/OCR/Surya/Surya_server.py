# 服务端实现见  ~/Surya/surya_server.py
# 下面的代码可能不是最新的，仅供参考
# 最新的代码见 ~/Surya/surya_server.py
 
 
from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
import io
import json
from surya.ocr import run_ocr
from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor
import uvicorn

import argparse
parser = argparse.ArgumentParser(description="Surya Server")
parser.add_argument("--port","-p", type=int, default=8200, help="运行服务器的端口")
args = parser.parse_args()

app = FastAPI()

det_processor, det_model = load_det_processor(), load_det_model()
rec_model, rec_processor = load_rec_model(), load_rec_processor()


@app.post("/ocr/")
async def perform_ocr(file: UploadFile = File(...), language: str = Query("en", description="Language code for OCR")):
    # 限制文件大小为10MB
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File size exceeds the 10MB limit.")

    # 读取上传的文件
    try:
        image = Image.open(io.BytesIO(contents))
    except UnidentifiedImageError:
        return JSONResponse(content={"error": "Invalid image format."}, status_code=400)

    # 执行 OCR
    predictions = run_ocr(
        [image],
        [[language]],  # 动态语言参数
        det_model,
        det_processor,
        rec_model,
        rec_processor
    )

    # 将预测结果转换为可序列化的格式
    serialized_predictions = json.loads(json.dumps(predictions, default=lambda o: o.__dict__))
    return JSONResponse(content=serialized_predictions)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=args.port)