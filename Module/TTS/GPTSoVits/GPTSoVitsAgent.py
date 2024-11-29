# Project:      Agent
# Author:       yomu
# Time:         2024/11/21
# Version:      0.1
# Description:  GPTSoVits class

"""
    此文件只有GPTSoVits的客户端的代理
"""

import os
import datetime
import requests
import time
from urllib.parse import urljoin
from dotenv import load_dotenv

# TODO 之后考虑将GPTSoVits的server集成到AI agent内部。现阶段还是采用分离式C/S
# TODO 给该类添加注释
class GPTSoVitsAgent:
    """

    """
    def __init__(self, env_path:str=None):
        load_dotenv(env_path)
        self.default_gpt_path = os.path.join("./GPT_weights_v2", "alxy_all_modified_v1.0-e50.ckpt")
        self.default_sovits_path = os.path.join("./SoVITS_weights_v2", "alxy_all_modified_v1.0_e50_s4700.pth")
        self.default_ref_root = "/home/yomu/data/audio/reference"
        self.default_ref_audio = os.path.join(self.default_ref_root, "audio", "1_301.wav")
        self.default_ref_prompt = {
            "path": os.path.join(self.default_ref_root, "text", "1_301.txt"),
            "content": "我的话，呢哼，更多是靠少女的小心思吧。看看你现在的表情。好想去那里"
        }
        self.default_save_dir = os.getenv("GPTSOVITS_CLI_OUTPUT_DIR")
        if not self.default_save_dir:
            raise ValueError("GPTSOVITS_CLI_OUTPUT_DIR environment variable not set.")
        if not os.path.exists(self.default_save_dir):
            os.makedirs(self.default_save_dir)
        self.server = os.getenv("GPTSOVITS_SERVER")
        if not self.server:
            raise ValueError("GPTSOVITS_SERVER environment variable not set.")

    def generate_config(self, gpt=None, sovits=None, ref_audio=None, ref_audio_prompt=None, text_lang="zh", prompt_lang="zh", batch_size=20):
        config = {
            "gpt_model": gpt or self.default_gpt_path,
            "sovits_model": sovits or self.default_sovits_path,
            "ref_audio": ref_audio or self.default_ref_audio,
            "ref_audio_prompt": ref_audio_prompt or self.default_ref_prompt["content"],
            "text_lang": text_lang,
            "prompt_lang": prompt_lang,
            "batch_size": batch_size
        }
        return config

    def infer_tts_get(self, content, config=None):
        if config is None:
            config = self.generate_config()
        url = urljoin(self.server, "tts")
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
        self._send_request("GET", url, params=params)

    def infer_tts_post(self, content, config=None):
        if config is None:
            config = self.generate_config()
        url = urljoin(self.server, "tts")
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
        self._send_request("POST", url, json=payload, headers=headers)

    def set_gpt_weights(self, gpt_weights_path):
        url = urljoin(self.server, "set_gpt_weights")
        params = {"weights_path": gpt_weights_path}
        self._send_request("GET", url, params=params)

    def set_sovits_weights(self, sovits_weights_path):
        url = urljoin(self.server, "set_sovits_weights")
        params = {"weights_path": sovits_weights_path}
        self._send_request("GET", url, params=params)

    def restart_service(self):
        url = urljoin(self.server, "control")
        payload = {"command": "restart"}
        headers = {'Content-Type': 'application/json'}
        self._send_request("POST", url, json=payload, headers=headers)

    def _send_request(self, method, url, **kwargs):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = requests.request(method, url, **kwargs, stream=True, timeout=100)
                response.raise_for_status()
                if method in ["GET", "POST"] and kwargs.get("stream", True):
                    filename = os.path.join(self.default_save_dir, datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S%f") + '_output.wav')
                    with open(filename, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    print(f"Audio synthesis successful, saved as {filename}")
                else:
                    print("Request successful.")
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



if __name__ == "__main__":
    print("This is a part of agent, supposed not to run directly. Do nothing.")
    # agent = GPTSoVitsAgent()
    # agent.infer_tts_get("你好")
