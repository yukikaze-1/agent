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
import aiofiles
import httpx
import asyncio
import uvicorn
from fastapi import Form, Request, File, FastAPI
from typing import Dict, List, Any
from urllib.parse import urljoin
from dotenv import dotenv_values

from Module.Utils.ConfigTools import load_config, validate_config
from Module.Utils.Logger import setup_logger
from Module.Utils.FastapiServiceTools import (
    get_service_instances,
    update_service_instances_periodically,
    register_service_to_consul,
    unregister_service_from_consul
)

# TODO 之后考虑将GPTSoVits的server集成到AI agent内部。现阶段还是采用分离式C/S
class GPTSoVitsAgent:
    """
    GPTSoVitsAgent 类作为 GPTSoVits 客户端的代理，负责与 GPTSoVits 服务交互、
    处理请求、并通过 Consul 进行服务注册与发现。

    功能包括：
    - 加载配置文件和环境变量
    - 服务注册与注销
    - 设置 API 路由
    - 处理语音生成请求
    """
    def __init__(self):
        self.logger = setup_logger(name="GPTSoVitsAgent", log_path='ExternalService')
        
        # 加载环境变量和配置
        self.env_vars = dotenv_values("/home/yomu/agent/Module/TTS/GPTSoVits/.env")
        self.config_path = self.env_vars.get("GPTSOVITS_CONFIG_PATH","") 
        self.config: Dict = load_config(config_path=self.config_path, config_name='GPTSovits', logger=self.logger)
        
        # 声线
        self.characters: Dict = self.config.get("characters", {})
        self.setting: Dict = self.config.get("setting", {})

        # GPTSoVits 生成配置
        self.character: Dict = self.characters.get("Elysia", {})
        self.gpt_path = self.character.get("gpt_path", "")
        self.sovits_path = self.character.get("sovits_path", "")
        self.ref_audio = self.character.get("ref_audio", "")
        self.ref_audio_text = self.character.get("ref_audio_text", "")

        self.save_dir = self.setting.get("save_dir", "")
        self.server_url = self.setting.get("server_url", "")
        
        # 微服务本身地址
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 20040)
        
        # Consul URL，确保包含协议前缀
        self.consul_url: str = self.config.get("consul_url", "http://127.0.0.1:8500")
        if not self.consul_url.startswith("http://") and not self.consul_url.startswith("https://"):
            self.consul_url = "http://" + self.consul_url
            self.logger.info(f"Consul URL adjusted to include http://: {self.consul_url}")
        
                
        self.infer_count = 0
        
        # 验证配置文件
        self._validate_config()
        
        # 服务注册信息
        self.service_name = self.config.get("service_name", "GPTSoVits")
        self.service_id = self.config.get("service_id", f"{self.service_name}-{self.host}:{self.port}")
        self.health_check_url = self.config.get("health_check_url", f"http://{self.host}:{self.port}/health")
        
        # 初始化 FastAPI 应用，使用生命周期管理
        self.app = FastAPI(lifespan=self.lifespan)
        
        # 设置路由
        self.setup_routes()
        
        
    def _validate_config(self):
        """
        验证配置文件是否包含所有必需的配置项。
        """
        required_keys = ["consul_url", "host", "port", "service_name", "health_check_url", "characters", "setting"]
        validate_config(required_keys, self.config, self.logger)
        
        # 验证特定配置
        if not self.characters:
            self.logger.error("No characters defined in configuration.")
            raise ValueError("No characters defined in configuration.")
        
        if not self.setting:
            self.logger.error("No setting defined in configuration.")
            raise ValueError("No setting defined in configuration.")
        
        # 验证 Elysia 配置
        if not self.character:
            self.logger.error("Character 'Elysia' is not defined in configuration.")
            raise ValueError("Character 'Elysia' is not defined in configuration.")
        
        # 验证必需的子键
        required_character_keys = ["gpt_path", "sovits_path", "ref_audio", "ref_audio_text"]
        for key in required_character_keys:
            if key not in self.character:
                self.logger.error(f"Missing required character configuration key: {key}")
                raise KeyError(f"Missing required character configuration key: {key}")
        
        # 验证必需的设置键
        required_setting_keys = ["save_dir", "server_url"]
        for key in required_setting_keys:
            if key not in self.setting:
                self.logger.error(f"Missing required setting configuration key: {key}")
                raise KeyError(f"Missing required setting configuration key: {key}")
    
    
    async def lifespan(self, app: FastAPI):
        """管理应用生命周期"""
        self.logger.info("Starting lifespan...")

        try:
            # 初始化 AsyncClient
            self.client = httpx.AsyncClient(
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                timeout=httpx.Timeout(10.0, read=60.0)
            )
            self.logger.info("Async HTTP Client Initialized")

            # 注册服务到 Consul
            self.logger.info("Registering service to Consul...")
            await register_service_to_consul(consul_url=self.consul_url,
                                             client=self.client,
                                             logger=self.logger,
                                             service_name=self.service_name,
                                             service_id=self.service_id,
                                             address=self.host,
                                             port=self.port,
                                             health_check_url=self.health_check_url)
            self.logger.info("Service registered to Consul.")

            yield  # 应用正常运行

        except Exception as e:
            self.logger.error(f"Exception during lifespan: {e}")
            raise

        finally:
            # 注销服务从 Consul
            try:
                self.logger.info("Deregistering service from Consul...")
                await unregister_service_from_consul(consul_url=self.consul_url,
                                                     client=self.client,
                                                     logger=self.logger,
                                                     service_id=self.service_id)
                self.logger.info("Service deregistered from Consul.")
            except Exception as e:
                self.logger.error(f"Error while deregistering service: {e}")
                
            # 关闭 AsyncClient
            self.logger.info("Shutting down Async HTTP Client")
            if self.client:
                await self.client.aclose()               
    
    
    def setup_routes(self):
        """设置 API 路由"""
        
        @self.app.get("/health", summary="健康检查接口")
        async def health_check():
            """返回服务的健康状态"""
            return {"status": "healthy"}
        
        @self.app.post("/agent/chat/TTS/infer", summary="生成语音")
        async def generate_voice(content: str = Form(...)):
            """
            接收文本内容并生成语音。

            - **content**: 需要生成语音的文本内容。
            """
            return await self._generate_voice(content)
        
    
    async def _generate_voice(self, content: str):
        """语音生成"""
        return await self.infer_tts_get(content)
        
        
    def generate_config(self, gpt=None, sovits=None, ref_audio=None, ref_audio_prompt=None, text_lang="zh", prompt_lang="zh", batch_size=20):
        config = {
            "gpt_model": gpt or self.gpt_path,
            "sovits_model": sovits or self.sovits_path,
            "ref_audio": ref_audio or self.ref_audio,
            "ref_audio_text": ref_audio_prompt or self.ref_audio_text["content"],
            "text_lang": text_lang,
            "prompt_lang": prompt_lang,
            "batch_size": batch_size
        }
        return config
    

    async def infer_tts_get(self, content: str, config: Dict[str, Any] = None) -> str:
        """
        使用 GET 请求进行语音生成。

        - **content**: 需要生成语音的文本内容。
        - **config**: 可选的配置字典。
        - **返回**: 保存的音频文件路径或响应内容。
        """
        if config is None:
            config = self.generate_config()
        url = urljoin(self.server_url, "tts")
        params = {
            "text": content,
            "text_lang": config["text_lang"],
            "ref_audio_path": config["ref_audio"],
            "prompt_lang": config["prompt_lang"],
            "prompt_text": config["ref_audio_text"],
            "text_split_method": "cut5",
            "batch_size": config["batch_size"],
            "media_type": "wav",
            "streaming_mode": True
        }
        self.infer_count += 1
        return await self._send_request("GET", url, save_response=True, params=params)


    async def infer_tts_post(self, content: str, config: Dict[str, Any] = None) -> str:
        """
        使用 POST 请求进行语音生成。

        - **content**: 需要生成语音的文本内容。
        - **config**: 可选的配置字典。
        - **返回**: 保存的音频文件路径或响应内容。
        """
        if config is None:
            config = self.generate_config()
        url = urljoin(self.server_url, "tts")
        payload = {
            "text": content,
            "text_lang": config["text_lang"],
            "ref_audio_path": config["ref_audio"],
            "prompt_text": config["ref_audio_text"],
            "prompt_lang": config["prompt_lang"],
            "top_k": 5,
            "top_p": 1,
            "temperature": 1,
            "text_split_method": "cut0",
            "batch_size": config["batch_size"],
            "streaming_mode": True
        }
        headers = {'Content-Type': 'application/json'}
        return await self._send_request("POST", url, save_response=True, json=payload, headers=headers)

        

    async def set_gpt_weights(self, gpt_weights_path: str) -> str:
        """
        设置 GPT 权重。

        - **gpt_weights_path**: GPT 权重文件的路径。
        - **返回**: 响应内容或保存的文件路径。
        """
        url = urljoin(self.server_url, "set_gpt_weights")
        params = {"weights_path": gpt_weights_path}
        return await self._send_request("GET", url, save_response=False, params=params)


    async def set_sovits_weights(self, sovits_weights_path: str) -> str:
        """
        设置 Sovits 权重。

        - **sovits_weights_path**: Sovits 权重文件的路径。
        - **返回**: 响应内容或保存的文件路径。
        """
        url = urljoin(self.server_url, "set_sovits_weights")
        params = {"weights_path": sovits_weights_path}
        return await self._send_request("GET", url, save_response=False, params=params)


    async def restart_service(self) -> str:
        """
        重启服务。

        - **返回**: 响应内容或保存的文件路径。
        """
        url = urljoin(self.server_url, "control")
        payload = {"command": "restart"}
        headers = {'Content-Type': 'application/json'}
        return await self._send_request("POST", url, save_response=False, json=payload, headers=headers)

        

    async def _send_request(self, method: str, url: str, save_response: bool = True, **kwargs: Any) -> str:
        """
        发送 HTTP 请求并处理响应。

        - **method**: HTTP 方法（GET, POST, etc.）
        - **url**: 请求的 URL
        - **save_response**: 是否保存响应内容到文件
        - **kwargs**: 其他请求参数
        - **返回**: 保存的文件路径或响应文本
        """
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # 发起异步请求
                response = await self.client.request(method, url, **kwargs, stream=True)
                
                # 检查 HTTP 响应状态码
                response.raise_for_status()
                
                if save_response and method.upper() in ["GET", "POST"] and kwargs.get("stream", True):
                    # 生成唯一的文件名
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S%f")
                    filename = os.path.join(self.save_dir, f"{timestamp}_output.wav")
                    
                    # 异步写入文件
                    async with aiofiles.open(filename, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            if chunk:
                                await f.write(chunk)
                    
                    self.logger.info(f"Audio synthesis successful, saved as '{filename}'")
                    return filename  # 返回文件路径
                else:
                    content = response.text
                    self.logger.info("Request successful.")
                    return content  # 返回响应文本
                
            except httpx.RequestError as e:
                self.logger.error(f"Request error: {e}")
                if e.response:
                    self.logger.warning(f"Response content: {e.response.text}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error("Failed after multiple attempts.")
                    raise  # 抛出异常以便上层处理

            except httpx.HTTPStatusError as e:
                self.logger.error(f"HTTP error: {e}")
                if e.response:
                    self.logger.warning(f"Response content: {e.response.text}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error("Failed after multiple attempts.")
                    raise  # 抛出异常以便上层处理

        
                    
    def run(self):
        uvicorn.run(self.app, host=self.host, port=self.port)
    


def main():
    agent = GPTSoVitsAgent()
    agent.run()


if __name__ == "__main__":
    main()
