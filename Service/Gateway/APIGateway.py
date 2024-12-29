# Project:      Agent
# Author:       yomu
# Time:         2024/12/27
# Version:      0.1
# Description:  agent API Gateway

"""
    API网关, 目前只负责路由转发 
"""
import sys, os
import httpx
import uvicorn
from dotenv import dotenv_values
from urllib.parse import urljoin, quote
from fastapi import FastAPI, File, HTTPException, Form, Request, Response, status
from typing import Dict

from Module.Utils.Logger import setup_logger
from Module.Utils.LoadConfig import load_config



class APIGateway:
    """
    API网关

        1. 将/usr/* 路由到UserService
        2. 将/agent/chat/* 路由到ChatModule
        3. 将/agent/input/* 路由到UsreInputModule
        4. 将/agent/setting/* 路由到EnvironmentMannager
    """
    def __init__(self):
        self.logger = setup_logger(name="APIGateway", log_path='Other')
        
        self.env_vars = dotenv_values("/home/yomu/agent/Service/Gateway/.env") 
        self.config_path = self.env_vars.get("API_GATEWAY_CONFIG_PATH","") 
        self.config: Dict = load_config(config_path=self.config_path, config_name='APIGateway', logger=self.logger)
        
        self.routes: Dict = self.config.get("routes", {})
        self.host = self.config.get("host", "0.0.0.0")
        self.port = self.config.get("port", 20001)
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
        
        # 用户相关服务
        @self.app.api_route("/usr/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
        async def usr_service_proxy(request: Request, path: str):
            prefix = "/usr"
            return await self._usr_service_proxy(request, prefix ,path)


        # TODO 这个usr_ping_serve函数名字要改下，转发给微服务网关
        @self.app.api_route("/option/{path:path}", methods=["GET", "POST"])
        async def usr_ping_server(request: Request, path: str):
            prefix = "/option"
            return await self._usr_ping_server(request, prefix, path)
        
        
        # 用户输入
        @self.app.api_route("/agent/input/{path:path}", methods=["POST"])
        async def usr_chat_input(request: Request, path: str):
            prefix = "/agent/input"
            return await self._usr_chat_input(request, prefix, path)

        # DEBUG 用户输入
        @self.app.api_route("/agent/chat/{path:path}", methods=["POST"])
        async def test_usr_chat_input(request: Request, path: str):
            # try:
            #     # 直接读取请求体并返回
            #     body = await request.json()  # 以 JSON 格式读取请求体
            #     return {"received": body, "path": path}
            # except Exception as e:
            #     return {"error": str(e)}
            prefix = "/agent/chat"
            server = "OllamaAgent"
            return await self.forward(request, prefix, path, server)
    
    # 用户相关服务
    async def _usr_service_proxy(self, request: Request, prefix: str, path: str):
            server = "UserService"
            return await self.forward(request, prefix, path, server)
    
    
    # 用户ping服务器，转发给微服务网关
    async def _usr_ping_server(self, request: Request, prefix: str, path: str):
        server = "MicroServiceGateway"
        return await self.forward(request, prefix, path, server)
    
    
    # 用户输入
    async def _usr_chat_input(self, request: Request, prefix: str, path: str):
        """转发用户输入"""
        server = "MicroServiceGateway"
        return await self.forward(request, prefix, path, server)
    
    
    async def forward(self, request: Request, prefix: str, path: str, server: str):
        """实际转发函数"""
        # 路径编码，防止路径遍历攻击
        # sanitized_path = quote(path, safe='')
        sanitized_path = path
        
        # url拼接
        user_service_base_url = self.routes.get(server,'')
        if not user_service_base_url:
            self.logger.error(f"'{server}' environment variable in config.yml is not set.")
            raise HTTPException(status_code=500, detail="'{server}' URL is not configured.")
        
        user_service_url = urljoin(user_service_base_url, f"{prefix}/{sanitized_path}")
        # 打印调试信息
        self.logger.info(f"Forwarding {request.method} request for {prefix}/{path} to {user_service_url}")
        # self.logger.info(f"Request headers: {dict(request.headers)}")
        # self.logger.info(f"Request body: {await request.body()}")
        # self.logger.info(f"Forwarding {request.method} request for {prefix}/{path} to {user_service_url}")
        
        # 过滤请求头，移除不必要的头
        excluded_headers = ["host", "content-length", "transfer-encoding", "connection"]
        
        headers = {k: v for k, v in request.headers.items() if k.lower() not in excluded_headers}
        
        try:
            forwarded_response = await self.client.request(
                method=request.method,
                url=user_service_url,
                headers=headers,
                content=await request.body(),
                timeout=45.0
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
    server = APIGateway()
    server.run()


if __name__ == "__main__":
    main()