# Project:      Agent
# Author:       yomu
# Time:         2024/12/28
# Version:      0.1
# Description:  ollama agent

"""
    ollama 的 agent
"""

import uvicorn
import httpx
import asyncio
from urllib.parse import urljoin
from dotenv import dotenv_values
from typing import Dict, List
from fastapi import FastAPI, Form, Body, HTTPException

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config
from Module.Utils.ServiceTools import (
    register_service_to_consul,
    unregister_service_from_consul
)

class OllamaAgent:
    """
        Ollama 的代理
    """
    def __init__(self):
        self.logger = setup_logger(name="OllamaAgent", log_path="InternalModule")
        
        # 加载环境变量和配置
        self.env_vars = dotenv_values("/home/yomu/agent/Module/LLM/.env") 
        self.config_path = self.env_vars.get("OLLAMA_AGENT_CONFIG_PATH","") 
        self.config: Dict = load_config(config_path=self.config_path, config_name='OllamaAgent', logger=self.logger)
        
        # 验证配置文件
        required_keys = ["consul_url", "host", "port", "ollama_url" ,"service_name", "service_id", "health_check_url"]
        validate_config(required_keys, self.config, self.logger)
        
        # Consul URL，确保包含协议前缀
        self.consul_url: str = self.config.get("consul_url", "http://127.0.0.1:8500")
        if not self.consul_url.startswith("http://") and not self.consul_url.startswith("https://"):
            self.consul_url = "http://" + self.consul_url
            self.logger.info(f"Consul URL adjusted to include http://: {self.consul_url}") 
        
        # Ollama的地址
        self.ollama_url = self.config.get("ollama_url","http://127.0.0.1:11434")
        
        # 微服务本身地址
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 20030)
        
        # 服务注册信息
        self.service_name = self.config.get("service_name", "OllamaAgent")
        self.service_id = self.config.get("service_id", f"{self.service_name}-{self.host}:{self.port}")
        self.health_check_url = self.config.get("health_check_url", f"http://{self.host}:{self.port}/health")
        
        # 初始化 httpx.AsyncClient
        self.client = None  # 在lifespan中初始化
        
        # 初始化 FastAPI 应用，使用生命周期管理
        self.app = FastAPI(lifespan=self.lifespan)
        
        # 设置路由
        self.setup_routes()
        
    
    async def lifespan(self, app: FastAPI):
        """管理应用生命周期"""
        # 应用启动时执行
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(10.0, read=60.0)
        )
        self.logger.info("Async HTTP Client Initialized")
        
        try:
            # 注册服务到 Consul
            await register_service_to_consul(consul_url=self.consul_url,
                                             client=self.client,
                                             logger=self.logger,
                                             service_name=self.service_name,
                                             service_id=self.service_id,
                                             address=self.host,
                                             port=self.port,
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
                
        
    def setup_routes(self):
        """设置路由"""
        
        @self.app.get("/health")
        async def health_check():
            """健康检查接口"""
            return {"status": "healthy"}
        
        # chat 
        @self.app.api_route("/agent/chat/to_ollama/chat/", methods=["POST"], summary="Chat with Ollama", description="Send a chat message to Ollama and receive a response.")
        async def  chat_with_ollama(data: Dict=Body(...)):
            return await self._chat(data)

        
        #generate
        @self.app.api_route("/agent/chat/to_ollama/generate/", methods=["POST"], summary="Generate response from Ollama", description="Send a prompt to Ollama and receive a generated response.")
        async def generate_respone(data: Dict=Body(...)):
            return await self._generate_response(data)
        
        
    # --------------------------------
    # 功能函数
    # --------------------------------     
    async def _generate_response(self, data: Dict):
        """generate_response"""
        headers = {"Content-Type": "application/json"}
        url = urljoin(self.ollama_url, "/api/generate")

        response = await self.client.post(url, json=data, headers=headers)

        try:
            response = await self.client.post(url, json=data, headers=headers)
            response.raise_for_status()
            response_data = response.json()
            
            if response.status_code == 200:
                # return {"result": True, "response": response_data['response']}
                return response_data
            else:
                self.logger.error(f"Unexpected response structure: {response_data}")
                raise HTTPException(status_code=500, detail="Invalid response from Ollama.")
            
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Ollama generate_response HTTP error: {e.response.status_code}, {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        
        except httpx.RequestError as e:
            self.logger.error(f"Ollama generate_response Request error: {e}")
            raise HTTPException(status_code=503, detail="Failed to communicate with Ollama.")
        
        except Exception as e:
            self.logger.error(f"Ollama generate_response Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error.")
        
        
    async def _chat(self,data: Dict):
        """与 Ollama 进行聊天"""
        headers = {"Content-Type": "application/json"}
        url = urljoin(self.ollama_url,"/api/chat")

        response = await self.client.post(url, json=data, headers=headers)

        try:
            response = await self.client.post(url, json=data, headers=headers)
            response.raise_for_status()
            response_data = response.json()
            
            if response.status_code == 200:
                # return {"result": True, "response": response_data['response']}
                return response_data
            else:
                self.logger.error(f"Unexpected response structure: {response_data}")
                raise HTTPException(status_code=500, detail="Invalid response from Ollama.")
            
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Ollama generate_response HTTP error: {e.response.status_code}, {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        
        except httpx.RequestError as e:
            self.logger.error(f"Ollama generate_response Request error: {e}")
            raise HTTPException(status_code=503, detail="Failed to communicate with Ollama.")
        
        except Exception as e:
            self.logger.error(f"Ollama generate_response Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error.")
        
        
    
    def run(self):
        uvicorn.run(self.app, host=self.host, port=self.port)
    
    
def main():
    module = OllamaAgent()
    module.run()
    
    
if __name__ == "__main__":
    main()
    
    