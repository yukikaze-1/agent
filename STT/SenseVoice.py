# Project:      Agent
# Author:       yomu
# Time:         2024/10/24
# Version:      0.1
# Description:  agent STT

import os
import os.path
import time
import datetime

from gradio_client import Client, handle_file
from dotenv import load_dotenv

load_dotenv("./.env")

"""
    采用SenseVoice模型来将语音转为文字
    @ 输入为一段语音，以文件形式保存
    @ 输出为一个字符串，可保存至文件
"""

# trans_file = "/home/yomu/data/audio/test/1_301.wav"

# 接口函数
def speech_recognition(filename: str) -> str:
    save_dir = os.getenv("SENSEVOICE_HISTORY_DIR", "./default_history_dir")
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    result = speech_recognition_aux(filename)
    
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    save_file = os.path.join(save_dir, f"history_{current_date}.txt")

    try:
        with open(save_file, "a") as f:
            f.write(result)
    except Exception as e:
        raise IOError(f"Error saving result to file '{save_file}': {e}")

    return result

# 实现函数
def speech_recognition_aux(filename: str) -> str:
    server = os.getenv("SENSEVOICE_SERVER")
    if not server:
        raise ValueError("Environment variable 'SENSEVOICE_SERVER' is not set.")

    try:
        client = Client(server)
    except Exception as e:
        raise RuntimeError(f"Error initializing client: {e}")

    if not os.path.isfile(filename):
        raise FileNotFoundError(f"The file '{filename}' does not exist or is not a valid file.")

    try:
        input_wav = handle_file(filename)
    except Exception as e:
        raise ValueError(f"Error handling file '{filename}': {e}")

    retries = 3
    for attempt in range(retries):
        try:
            result = client.predict(
                input_wav=input_wav,
                language="auto",
                api_name="/model_inference"
            )
            return result
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                raise RuntimeError(f"Error during model inference after {retries} attempts: {e}")

# print(speech_recognition(trans_file))
