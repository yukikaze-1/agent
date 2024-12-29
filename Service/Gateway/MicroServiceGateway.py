# Project:      Agent
# Author:       yomu
# Time:         2024/12/12
# Version:      0.1
# Description:  agent Microservice Gateway

"""
    负责agent与用户客户端的通信
    运行前请 export PYTHONPATH=/home/yomu/agent:$PYTHONPATH
"""

import os
import uvicorn
import httpx  # 用于服务间通信
from urllib.parse import urljoin, quote
from fastapi import FastAPI, File, HTTPException, Form, Request, Response, status
from datetime import datetime
from typing import Dict
from dotenv import dotenv_values

from Module.Utils.Logger import setup_logger
from Module.Utils.LoadConfig import load_config


class MicroServiceGateway():
    """
        微服务网关
    """
    def __init__(self):
        self.logger = setup_logger(name="MicroServiceGateway", log_path="Other") 
        
        self.env_vars = dotenv_values("/home/yomu/agent/Service/Gateway/.env")
        self.config_path = self.env_vars.get("MICRO_SERVICE_GATEWAY_CONFIG_PATH","")
        self.config = load_config(config_path=self.config_path, config_name='MicroServiceGateway', logger=self.logger)
        
        # 微服务的路由表（内部服务间通信）
        self.internal_routes = self.config["internal_routes"]
        self.host = self.config.get("host", "0.0.0.0")
        self.port = self.config.get("port", 20000)
        self.app = FastAPI()
        
        # 设置路由
        self.setup_routes()
        
         # 添加事件处理
        self.app.add_event_handler("startup", self.on_startup)
        self.app.add_event_handler("shutdown", self.on_shutdown)
        
        # 初始化 AsyncClient 为 None
        self.client = None

    async def on_startup(self):
        """应用启动时创建 AsyncClient 实例"""
        self.logger.info("Initializing httpx.AsyncClient...")
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(10.0, read=5.0)
        )
        self.logger.info("httpx.AsyncClient initialized.")
        

    async def on_shutdown(self):
        """应用关闭时关闭 AsyncClient 实例"""
        self.logger.info("Closing httpx.AsyncClient...")
        if self.client:
            await self.client.aclose()
            self.logger.info("httpx.AsyncClient closed.")
        self.logger.info("No httpx.AsyncClient need to close.")
    
        
    def setup_routes(self):
        """设置 API 路由"""

        # 聊天
        @self.app.api_route("/agent/chat/to_ollama/chat", methods=["Post"])
        async def ollma_chat_service_proxy(request: Request):
            prefix = "/agent/chat/to_ollama"
            path = "chat"
            server = "OllamaAgent"
            return await self.forward(request, prefix, path, server)
            
        
        # 用户测试服务器连通性
        @self.app.post("/option/ping/")
        async def usr_ping_server(time: str=Form(...), client_ip: str=Form(...)):
            return await self._usr_ping_server(time, client_ip)
        
        # 用户更改设置
        @self.app.post("/agent/setting/change/")
        async def usr_change_setting():
            return await self._usr_change_setting()
        
        # 用户的文本输入
        @self.app.post("/agent/input/text/")
        async def usr_text_input():
            return await self._usr_text_input()
        
        # 用户的语音输入
        @self.app.post("/agent/input/audio/")
        async def usr_audio_input():
            return await self._usr_audio_input()
        
        # 用户的语音输入
        @self.app.post("/agent/input/audio_streaming/")
        async def usr_audio_streaming_input():
            return await self._usr_audio_streaming_input()
        
        # 用户的图片输入
        @self.app.post("/agent/input/picture/")
        async def usr_picture_input():
            return await self._usr_picture_input()
        
        # 用户的视频文件输入
        @self.app.post("/agent/input/video/")
        async def usr_video_input():
            return await self._usr_video_input()
        
        # 用户的实时视频流输入
        @self.app.post("/agent/input/video_streaming/")
        async def usr_video_streaming_input():
            return await self._usr_video_streaming_input()
        
        
     
    async def _usr_ping_server(self, time: str, client_ip: str):
        """接受用户端发来的ping，回送服务器信息"""         
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"Ping success."
        self.logger.info(f"Operator: usr_ping_server. Result: True, Message: {message}")
        return {"result": True, "message": message, "time": current_time}
    
    async def _usr_change_setting(self):
        """接受用户发来的选项配置信息"""
        pass
    
    async def _usr_text_input(self):
        """接受用户在聊天框中发送的文本信息"""
        pass
    
    async def _usr_audio_input(self):
        """接受用户的语音输入"""
        pass
    
    async def _usr_audio_streaming_input(self):
        """接受用户的实时语音流输入"""
        pass
    
    async def _usr_picture_input(self):
        """接受用户的图片输入"""
        pass
    
    async def _usr_video_input(self):
        """接受用户的视频文件输入"""
        pass
    
    async def _usr_video_streaming_input(self):
        """接受用户的实时视频流输入"""
        pass
    
    async def _usr_file_input(self):
        """接受用户的文件输入"""
        pass
        
    def __del__(self):
        pass
    
    async def forward(self, request: Request, prefix: str, path: str, server: str):
        """实际转发函数"""
        # 路径编码，防止路径遍历攻击
        sanitized_path = quote(path, safe='')
        
        # url拼接
        user_service_base_url = self.internal_routes.get(server,'')
        if not user_service_base_url:
            self.logger.error(f"'{server}' environment variable in config.yml is not set.")
            raise HTTPException(status_code=500, detail="'{server}' URL is not configured.")
        
        user_service_url = urljoin(user_service_base_url, f"{prefix}/{sanitized_path}")
        
        self.logger.info(f"Forwarding {request.method} request for {prefix}/{path} to {user_service_url}")
        
        # 过滤请求头，移除不必要的头
        excluded_headers = ["host", "content-length", "transfer-encoding", "connection"]
        headers = {k: v for k, v in request.headers.items() if k.lower() not in excluded_headers}
        
        try:
            forwarded_response = await self.client.request(
                method=request.method,
                url=user_service_url,
                headers=headers,
                content=await request.body(),
                timeout=5.0
            )
            # 检查响应状态
            forwarded_response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            self.logger.error(f"HTTP error occurred: {exc}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"{server} 返回错误")
        except httpx.RequestError as exc:
            self.logger.error(f"Request error occurred: {exc}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"无法连接到 {server}")
        
        # 过滤响应头，移除不必要的头
        excluded_response_headers = ["content-encoding", "transfer-encoding", "connection"]
        response_headers = {
            k: v for k, v in forwarded_response.headers.items() if k.lower() not in excluded_response_headers
        }
        
        self.logger.info(f"Forwarded response with status {forwarded_response.status_code} for {prefix}/{path}")    
        
        # 构建响应，保留状态码和头信息
        return Response(
                    content=forwarded_response.content,
                    status_code=forwarded_response.status_code,
                    headers=response_headers
                )
    
    def run(self):
        uvicorn.run(self.app, host=self.host, port=self.port)
    

def main():
    server = MicroServiceGateway()
    server.run()
    
    
if __name__ == "__main__":
    main()
    