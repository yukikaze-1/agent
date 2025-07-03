# Project:      Agent
# Author:       yomu
# Time:         2025/01/08
# Version:      0.1
# Description:  agent prompt optimizer

"""
    提示词优化器
"""

import httpx
import asyncio
import uvicorn
from typing import Dict, List, Any, AsyncGenerator, Optional
from dotenv import dotenv_values
from fastapi import HTTPException, FastAPI, status, Form, Body
from pydantic import BaseModel
from contextlib import asynccontextmanager

from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.schema.runnable import RunnableSerializable

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config
from Module.Utils.FastapiServiceTools import(
    register_service_to_consul,
    unregister_service_from_consul,
)
from Module.Utils.PromptTemplate.PromptOptimizerTemplate import (
    check_typographical_errors_prompt,
    optimize_prompt
)


class PromptOptimizer:
    """
        提示词Prompt 优化器
        
        接受ChatModule发来的用户输入(文本、语音、)
    """
    class PromptPayload(BaseModel):
        user: str
        content: str
    
    def __init__(self):
        self.logger = setup_logger(name="APIGateway", log_path='Other')
        
        # 加载环境变量和配置
        self.env_vars = dotenv_values("${AGENT_HOME}/Module/Input/.env") 
        self.config_path = self.env_vars.get("PROMPT_OPTIMIZER_CONFIG_PATH","") 
        self.config: Dict = load_config(config_path=self.config_path, config_name='PromptOptimizer', logger=self.logger)
        
        # 初始化 AsyncClient 为 None
        self.client: httpx.AsyncClient
        
        # Consul URL，确保包含协议前缀
        self.consul_url: str = self.config.get("consul_url", "http://127.0.0.1:8500")
        if not self.consul_url.startswith("http://") and not self.consul_url.startswith("https://"):
            self.consul_url = "http://" + self.consul_url
            self.logger.info(f"Consul URL adjusted to include http://: {self.consul_url}")
        
        # 验证配置文件
        required_keys = ["consul_url", "host", "port" ,"service_name", "service_id", "health_check_url"]
        validate_config(required_keys, self.config, self.logger)
        
        # 微服务本身地址
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 20022)
        
        # 服务注册信息
        self.service_name = self.config.get("service_name", "PromptOptimizer")
        self.service_id = self.config.get("service_id", f"{self.service_name}-{self.host}:{self.port}")
        self.health_check_url = self.config.get("health_check_url", f"http://{self.host}:{self.port}/health")
        
         # 初始化 FastAPI 应用，使用生命周期管理
        self.app = FastAPI(lifespan=self.lifespan)
        
        # 大模型相关参数
        self.temperature = self.config.get("temperature", 0.1)
        self.model_name = self.config.get("model_name", "llama3.2")
        self.llm = ChatOllama(model=self.model_name, temperature=self.temperature)
        
        # 纠正逻辑的chain(在setup_chains中初始化)
        self.correct_prompt_chain: RunnableSerializable[dict, str] | None = None
        
        # 设置路由
        self.setup_routes()
        
        # 设置LLM链
        self.setup_chains()
        
        
    @asynccontextmanager
    async def lifespan(self, app: FastAPI)-> AsyncGenerator[None, None]:
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
            tags = ["PromptOptimizer"]
            await register_service_to_consul(consul_url=self.consul_url,
                                             client=self.client,
                                             logger=self.logger,
                                             service_name=self.service_name,
                                             service_id=self.service_id,
                                             address=self.host,
                                             port=self.port,
                                             tags=tags,
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
    
    # --------------------------------
    # 设置LLMChain
    # --------------------------------
    def setup_chains(self):
        """设置LLM链"""       
        # 纠正逻辑的chain
        self.correct_prompt_chain = check_typographical_errors_prompt | self.llm | StrOutputParser() 
        
        
    # --------------------------------
    # 设置路由
    # --------------------------------
    def setup_routes(self):
        """设置 API 路由"""
        
        @self.app.get("/health", summary="健康检查接口")
        async def health_check():
            """返回服务的健康状态"""
            return {"status": "healthy"}
        
        
        @self.app.api_route("/prompt/optimize", methods=["POST", "GET"], summary="提示词优化")
        async def prompt_optimize(payload: 'PromptOptimizer.PromptPayload'):
            """提示词优化"""
            content = payload.content
            self.logger.info(f"payload: {payload}")
            self.logger.info(f"content: {content}")
            return await self._prompt_optimize(content)
    
    
    async def _prompt_optimize(self, content: str):
        """提示词优化"""
        # 检查并修正可能的错误
        prompt = {"text": content}
        check_result = self.correct_prompt_chain.invoke(prompt)
        
        # 进行优化
        
        return check_result
        
    
    
    def run(self):
        uvicorn.run(self.app, host=self.host, port=self.port)
    
def main():
    service = PromptOptimizer()
    service.run()
    
    
if __name__ == "__main__":
    main()
    
    
    
