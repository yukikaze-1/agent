# Project:      Agent
# Author:       yomu
# Time:         2024/10/30
# Version:      0.1
# Description:  TTS

"""
    使用GPTSoVits模型进行TTS 
    生成的语音存放在 ./.env 中的 GPTSOVITS_CLI_OUTPUT_DIR 中
    目前是存放在/home/yomu/agent/TTS/output
"""
# TODO 目前采用了GPTSoVits模型，后续考虑添加CosyVoice

"""
config_format:{
    "gpt_model":        "GPT model path",
    "sovits_model":     "SoVits model path",
    "ref_audio":        "reference audio path",
    "ref_audio_prompt": "reference audio text",
    "text_lang":        "language to generate",
    "prompt_lang":      "the  language of reference audio's prompt"
    "batch_size":       "batch size"
    }
"""

import os
import datetime
import requests
import json
import time

from urllib.parse import urljoin
from gradio_client import Client, file #TODO file要被启用，改为handle_file，记得测试下tts防止暴毙
from dotenv import load_dotenv

load_dotenv("./.env")

# 默认配置
default_gpt_path = os.path.join("./GPT_weights_v2", "alxy_all_modified_v1.0-e50.ckpt")
default_sovits_path = os.path.join("./SoVITS_weights_v2", "alxy_all_modified_v1.0_e50_s4700.pth")
default_ref_root = "/home/yomu/data/audio/reference"
default_ref_audio = os.path.join(default_ref_root, "audio", "1_301.wav")
default_ref_prompt = {
    "path": os.path.join(default_ref_root, "text", "1_301.txt"),
    "content": "我的话，嗯哼，更多是靠少女的小心思吧。看看你现在的表情。好想去那里"
}
default_aux_ref_audio_paths = [
    file(os.path.join(default_ref_root, "audio", f"1_30{i}.wav")) for i in range(2, 10)
]
default_save_dir = os.getenv("GPTSOVITS_CLI_OUTPUT_DIR")

if not default_save_dir:
    raise ValueError("GPTSOVITS_CLI_OUTPUT_DIR environment variable not set.")

if not os.path.exists(default_save_dir):
    os.makedirs(default_save_dir)

# 服务器地址
server = os.getenv("GPTSOVITS_SERVER")
if not server:
    raise ValueError("GPTSOVITS_SERVER environment variable not set.")

# 请求的封装
def generate_config(gpt=default_gpt_path,
                    sovits=default_sovits_path,
                    ref_audio=default_ref_audio,
                    ref_audio_prompt=default_ref_prompt["content"],
                    text_lang="zh",
                    prompt_lang="zh",
                    batch_size=20):
    config = {
        "gpt_model": gpt,
        "sovits_model": sovits,
        "ref_audio": ref_audio,
        "ref_audio_prompt": ref_audio_prompt,
        "text_lang": text_lang,
        "prompt_lang": prompt_lang,
        "batch_size": batch_size
    }
    return config

# 默认的请求，除了要生成的文本
default_config = generate_config()

# 推理示例（GET 请求）
def infer_tts_get(content, config=default_config):
    url = urljoin(server, "tts")
    params = {
        "text": content,
        "text_lang": config["text_lang"],
        "ref_audio_path": config["ref_audio"],
        "prompt_lang": config["prompt_lang"],
        "prompt_text": config["ref_audio_prompt"],
        "text_split_method": "cut5",
        "batch_size": config["batch_size"],
        "media_type": "wav",
        "streaming_mode": True
    }
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, stream=True, timeout=100)
            response.raise_for_status()
            filename = os.path.join(default_save_dir, datetime.datetime.now().strftime("%Y-%m-%d-%H:%M-%S%f") + '_output.wav')
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"Audio synthesis successful, saved as {filename}")
            break
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response content: {e.response.content}")
            if attempt < max_retries - 1:
                print("Retrying...")
                time.sleep(2 ** (attempt + 1))
            else:
                print("Failed after multiple attempts.")

# 推理示例（POST 请求）
def infer_tts_post(content, config=default_config):
    url = urljoin(server, "tts")
    payload = {
        "text": content,
        "text_lang": config["text_lang"],
        "ref_audio_path": config["ref_audio"],
        "prompt_text": config["ref_audio_prompt"],
        "prompt_lang": config["prompt_lang"],
        "top_k": 5,
        "top_p": 1,
        "temperature": 1,
        "text_split_method": "cut0",
        "batch_size": config["batch_size"],
        "streaming_mode": True
    }
    headers = {'Content-Type': 'application/json'}
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers, stream=True, timeout=100)
            response.raise_for_status()
            filename = os.path.join(default_save_dir, datetime.datetime.now().strftime("%Y-%m-%d-%H:%M-%S%f") + '_output.wav')
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"Audio synthesis successful, saved as {filename}")
            break
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response content: {e.response.content}")
            if attempt < max_retries - 1:
                print("Retrying...")
                time.sleep(2 ** (attempt + 1))
            else:
                print("Failed after multiple attempts.")

# 切换 GPT 模型
def set_gpt_weights(gpt_weights_path):
    url = urljoin(server, "set_gpt_weights")
    params = {
        "weights_path": gpt_weights_path
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        print(f"GPT model switched successfully. Now is {gpt_weights_path}")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

# 切换 Sovits 模型
def set_sovits_weights(sovits_weights_path):
    url = urljoin(server, "set_sovits_weights")
    params = {
        "weights_path": sovits_weights_path
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        print(f"Sovits model switched successfully. Now is {sovits_weights_path}")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

# 控制命令（重新运行）# TODO 这个功能有问题，会报错Error: 405 Client Error: Method Not Allowed for url: http://192.168.1.17:9880/control
def restart_service():
    url = urljoin(server, "control")
    payload = {
        "command": "restart"
    }
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        print("Service restarted successfully")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("This is a part of agent,supposed not to run directly.Do nothing")