# Project:      Agent
# Author:       yomu
# Time:         2024/11/08
# Version:      0.1
# Description:  agent STT SenseVoice server

# SenseVoice部署在本地，采用C/S方式
# 官方提供了fastapi的实现，在  ~/SenseVoice/api.py 
# 我自己实现了一个server，在~/SenseVoice/SenseVoice_server.py
# 虽然我实现了一个实时推流的SenseVoice，但效果非常差，实时推理建议上StreamingSenseVoice
# 下面的代码可能不是最新的，仅供参考
# 最新的代码见 ~/SenseVoice/SenseVoice_server.py



from fastapi import FastAPI, UploadFile, File, Form
import uvicorn
import numpy as np
from funasr import AutoModel
from typing_extensions import Annotated
from funasr.utils.postprocess_utils import rich_transcription_postprocess
import wave
import torchaudio
import os, io, re
from enum import Enum
from typing import List
from io import BytesIO
from model import SenseVoiceSmall

class Language(str, Enum):
    auto = "auto"
    zh = "zh"
    en = "en"
    yue = "yue"
    ja = "ja"
    ko = "ko"
    nospeech = "nospeech"

# 初始化SenseVoice模型(stream)
model_stream = AutoModel(model="paraformer-zh-streaming")

# 初始化SenseVoice模型(sentences)
model_dir = "iic/SenseVoiceSmall"
model_sentences, kwargs = SenseVoiceSmall.from_pretrained(model=model_dir, device=os.getenv("SENSEVOICE_DEVICE", "cuda:0"))
model_sentences.eval()

regex = r"<\|.*\|>"

# 初始化FastAPI应用
app = FastAPI()

# 定义实时推理接口(stream)
@app.post("/predict/stream/")
async def predict_stream(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    with wave.open(BytesIO(audio_bytes), 'rb') as audio_file:
        audio_np = np.frombuffer(audio_file.readframes(audio_file.getnframes()), dtype=np.int16)
    audio_np = audio_np.astype(np.float32) / 32768.0  # 转换为浮点数

    # 进行推理
    cache = {}  # 模型的缓存，用于实时推理
    res = model_stream.generate(input=audio_np, cache=cache, is_final=True)
    return {"result": res}

# 定义推理接口(sentences)
@app.post("/predict/sentences/")
async def predict_sentences(files: Annotated[List[bytes], File(description="wav or mp3 audios in 16KHz")], keys: Annotated[str, Form(description="name of each audio joined with comma")], lang: Annotated[Language, Form(description="language of audio content")] = "auto"):
    audios = []
    audio_fs = 0
    for file in files:
        file_io = BytesIO(file)
        data_or_path_or_list, audio_fs = torchaudio.load(file_io)
        data_or_path_or_list = data_or_path_or_list.mean(0)
        audios.append(data_or_path_or_list)
        file_io.close()
    if lang == "":
        lang = "auto"
    if keys == "":
        key = ["wav_file_tmp_name"]
    else:
        key = keys.split(",")
    res = model_sentences.inference(
        data_in=audios,
        language=lang, # "zh", "en", "yue", "ja", "ko", "nospeech"
        use_itn=False,
        ban_emo_unk=False,
        key=key,
        fs=audio_fs,
        **kwargs,
    )
    if len(res) == 0:
        return {"result": []}
    for it in res[0]:
        it["raw_text"] = it["text"]
        it["clean_text"] = re.sub(regex, "", it["text"], 0, re.MULTILINE)
        it["text"] = rich_transcription_postprocess(it["text"])
    return {"result": res[0]}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=50000)