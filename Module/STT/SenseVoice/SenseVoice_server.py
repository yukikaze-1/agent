# Project:      Agent
# Author:       yomu
# Time:         2024/11/08
# Version:      0.1
# Description:  agent STT SenseVoice server

# SenseVoice部署在本地，采用C/S方式
# 官方提供了fastapi的实现，在  ~/SenseVoice/api.py 
# 我自己实现了一个server，在~/SenseVoice/SenseVoice_server_class.py
# 虽然我实现了一个实时推流的SenseVoice，但效果非常差，实时推理建议上StreamingSenseVoice
# 下面的代码可能不是最新的，仅供参考
# 最新的代码见 ~/SenseVoice/SenseVoice_server.py

"""
    最后修改于2024/12/2/4:33
"""

'''
from fastapi import FastAPI, UploadFile, File, Form
import uvicorn
import numpy as np
from funasr import AutoModel
from typing_extensions import Annotated
from funasr.utils.postprocess_utils import rich_transcription_postprocess
import wave
import torchaudio
import os
import re
import argparse
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

class SenseVoiceServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 50000):
        """
        初始化 SenseVoice 服务器。

        :param host: 服务器主机地址
        :param port: 服务器端口
        """
        self.host = host
        self.port = port
        self.app = FastAPI()  # 创建 FastAPI 应用实例
        self.model_stream = AutoModel(model="paraformer-zh-streaming")  # 初始化流模型
        model_dir = "iic/SenseVoiceSmall"
        self.model_sentences, self.kwargs = SenseVoiceSmall.from_pretrained(model=model_dir, device=os.getenv("SENSEVOICE_DEVICE", "cuda:0"))
        self.model_sentences.eval()  # 设置模型为评估模式
        self.regex = r"<\|.*\|>"
        self.setup_routes()  # 设置路由

    def setup_routes(self):
        """设置 API 路由"""
        @self.app.post("/predict/stream/")
        async def predict_stream(file: UploadFile = File(...)):
            return await self._predict_stream(file)

        @self.app.post("/predict/sentences/")
        async def predict_sentences(files: Annotated[List[bytes],File(description="wav or mp3 audios in 16KHz")],
                                    keys: Annotated[str, Form(description="name of each audio joined with comma")],
                                    lang: Annotated[Language, Form(description="language of audio content")] = "auto"):
            return await self._predict_sentences(files, keys, lang)

    async def _predict_stream(self, file: UploadFile):
        """
        处理实时推理请求。

        :param file: 上传的音频文件
        :return: 推理结果
        """
        audio_bytes = await file.read()
        with wave.open(BytesIO(audio_bytes), 'rb') as audio_file:
            audio_np = np.frombuffer(audio_file.readframes(audio_file.getnframes()), dtype=np.int16)
        audio_np = audio_np.astype(np.float32) / 32768.0  # 转换为浮点数

        # 进行推理
        cache = {}  # 模型的缓存，用于实时推理
        res = self.model_stream.generate(input=audio_np, cache=cache, is_final=True)
        return {"result": res}

    async def _predict_sentences(self, files: List[bytes], keys: str, lang: Language):
        """
        处理句子推理请求。

        :param files: 上传的音频文件列表
        :param keys: 音频文件的名称
        :param lang: 音频内容的语言
        :return: 推理结果
        """
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
        res = self.model_sentences.inference(
            data_in=audios,
            language=lang,
            use_itn=False,
            ban_emo_unk=False,
            key=key,
            fs=audio_fs,
            **self.kwargs,
        )
        if len(res) == 0:
            return {"result": []}
        for it in res[0]:
            it["raw_text"] = it["text"]
            it["clean_text"] = re.sub(self.regex, "", it["text"], 0, re.MULTILINE)
            it["text"] = rich_transcription_postprocess(it["text"])
        return {"result": res[0]}

    def run(self):
        """运行 SenseVoice 服务器"""
        uvicorn.run(self.app, host=self.host, port=self.port)

def main():
    parser = argparse.ArgumentParser(description="SenseVoice FastAPI Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="服务器主机地址")
    parser.add_argument("--port", type=int, default=50000, help="服务器端口")
    args = parser.parse_args()

    server = SenseVoiceServer(host=args.host, port=args.port)
    server.run()

if __name__ == "__main__":
    main()

'''