# Project:      Agent
# Author:       yomu
# Time:         2025/01/07
# Version:      0.1
# Description:  agent STT SenseVoice Agent

"""
    负责识别语音
"""

import os
import httpx
import asyncio
import uvicorn
from fastapi import FastAPI, status, Form, HTTPException, Body
from dotenv import dotenv_values
from typing import Dict, List, Any, Tuple, AsyncGenerator
from pydantic import BaseModel
from contextlib import asynccontextmanager

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config
from Module.Utils.FastapiServiceTools import (
    register_service_to_consul,
    unregister_service_from_consul
)


class SenseVoiceAgent:
    """
    
    """
    
    class AudioRecognizeRequest(BaseModel):
        audio_path: str
        
    
    def __init__(self):
        self.logger = setup_logger(name="SenseVoiceAgent", log_path="InternalModule")
        
        # 加载环境变量和配置
        self.env_vars = dotenv_values(os.path.join(
            os.environ.get('AGENT_HOME', os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "Module/STT/SenseVoice/.env"
        ))
        self.config_path = self.env_vars.get("SENSEVOICE_AGENT_CONFIG_PATH","")
        self.config = load_config(config_path=self.config_path, config_name='SenseVoiceAgent', logger=self.logger)
        
        # 验证配置文件
        required_keys = ["consul_url", "server_url", "host", "port", "service_name", "service_id", "health_check_url"]
        validate_config(required_keys, self.config, self.logger)
        
        # Consul URL，确保包含协议前缀
        self.consul_url: str = self.config.get("consul_url", "http://127.0.0.1:8500")
        if not self.consul_url.startswith("http://") and not self.consul_url.startswith("https://"):
            self.consul_url = "http://" + self.consul_url
            self.logger.info(f"Consul URL adjusted to include http://: {self.consul_url}") 
        
        # 微服务本身地址
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 20041)
        
        # SenseVoice_server地址
        self.server_url = self.config.get("server_url", "")
        
        # 服务注册信息
        self.service_name = self.config.get("service_name", "SenseVoiceAgent")
        self.service_id = self.config.get("service_id", f"{self.service_name}-{self.host}:{self.port}")
        self.health_check_url = self.config.get("health_check_url", f"http://{self.host}:{self.port}/health")
        
        # 初始化 httpx.AsyncClient
        self.client:  httpx.AsyncClient  # 在lifespan中初始化
        
        # 初始化 FastAPI 应用，使用生命周期管理
        self.app = FastAPI(lifespan=self.lifespan)
        
        # 设置路由
        self.setup_routes()
        
    
    @asynccontextmanager
    async def lifespan(self, app: FastAPI)-> AsyncGenerator[None, None]:
        """管理应用生命周期"""
        # 应用启动时执行
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(10.0, read=60.0)
        )
        self.logger.info("Async HTTP Client Initialized")
        

        try:
            # 注册服务到 Consul
            self.logger.info("Registering service to Consul...")
            tags = ["SenseVoiceAgent"]
            await register_service_to_consul(consul_url=self.consul_url,
                                             client=self.client,
                                             logger=self.logger,
                                             service_name=self.service_name,
                                             service_id=self.service_id,
                                             address=self.host,
                                             port=self.port,
                                             tags=tags,
                                             health_check_url=self.health_check_url)
            
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
                
      
    
    # --------------------------------
    # 6. 请求转发逻辑
    # --------------------------------    
    def setup_routes(self):
        """设置路由"""
        
        @self.app.get("/health")
        async def health_check():
            """健康检查接口"""
            return {"status": "healthy"}
        
        @self.app.post("/audio/recognize")
        async def audio_recognize(recognize_request: 'SenseVoiceAgent.AudioRecognizeRequest'):
            """语音识别接口"""
            file_path = recognize_request.audio_path
            return await self._audio_recognize(file_path)
    
    
    async def _audio_recognize(self, audio_path: str, lang: str="auto")->List[Tuple[str,str]]:
        """语音识别"""
        # 提取音频文件名作为 key
        keys = os.path.basename(audio_path)
        ret: List[Tuple[str,str]] = [] 

        try:
            # 使用单文件版本的发送函数
            result = await self._send_audio_files(audio_path, keys, lang)
            
            # 解析API返回的结果
            for res in result.get("result", []):
                ret.append((res['key'], res.get('clean_text', '')))
            return ret
        except Exception as e:
            self.logger.error(f"Error during ASR inference: {e}")
            return ret
        
    
    async def _send_audio_files(self, audio_file: str, keys: str, lang: str="auto")->Dict:
        """发送音频文件到 ASR API"""
        try:
            with open(audio_file, "rb") as f:
                files = {"files": (os.path.basename(audio_file), f, "audio/wav")}
                form_data = {
                    "keys": keys,
                    "lang": lang,
                }
                # 发送POST请求到ASR API
                url = self.server_url + "/predict/sentences"
                response = await self.client.post(url, files=files, data=form_data, timeout=120.0)
                response.raise_for_status()  # 如果响应错误，则抛出异常
                return response.json()
        except httpx.RequestError as e:
            self.logger.error(f"Failed to connect to server with error: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            return {}
    
    def run(self):
            uvicorn.run(self.app, host=self.host, port=self.port)
    
def main():
    service = SenseVoiceAgent()
    service.run()
    

if __name__ == "__main__":
    main()
    
    