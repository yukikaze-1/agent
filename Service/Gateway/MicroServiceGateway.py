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
import asyncio
from urllib.parse import urljoin, quote
from fastapi import FastAPI, File, HTTPException, Form, Request, Response, status, Depends
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Dict, List, AsyncGenerator
from dotenv import dotenv_values
from collections import defaultdict
from contextlib import asynccontextmanager


from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config
from Module.Utils.FastapiServiceTools import (
    get_service_instances,
    update_service_instances_periodically,
    register_service_to_consul,
    unregister_service_from_consul,
    get_next_instance,
    is_instance_healthy,
    record_failure,
    reset_failure,
    setup_redis_limiter
)


class MicroServiceGateway():
    """
        微服务网关
    """
    def __init__(self):
        self.logger = setup_logger(name="MicroServiceGateway", log_path="Other") 
        
        # 加载环境变量和配置
        self.env_vars = dotenv_values("/home/yomu/agent/Service/Gateway/.env")
        self.config_path = self.env_vars.get("MICRO_SERVICE_GATEWAY_CONFIG_PATH","")
        self.config = load_config(config_path=self.config_path, config_name='MicroServiceGateway', logger=self.logger)
        
        # 超时配置
        self.request_timeout = self.config.get("request_timeout", 10.0)
        self.read_timeout = self.config.get("read_timeout", 60.0)
        
        # 存储服务实例和失败计数
        self.service_instances: Dict[str, List[Dict]] = {}  # 存储从 Consul 获取的服务实例信息
        self.failure_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))  # 服务实例失败计数
        
        # Consul URL，确保包含协议前缀
        self.consul_url: str = self.config.get("consul_url", "http://127.0.0.1:8500")
        if not self.consul_url.startswith("http://") and not self.consul_url.startswith("https://"):
            self.consul_url = "http://" + self.consul_url
            self.logger.info(f"Consul URL adjusted to include http://: {self.consul_url}")
        
        
        # 负载均衡索引
        self.load_balancer_index: Dict[str, int] = defaultdict(int)  
        
        # 微服务的路由表（内部服务间通信）
        self.routes: Dict[str, str] = self.config["routes"]
        
        # 验证配置文件
        self._validate_config()
        
        # 确保 routes 中的每个服务 URL 包含协议前缀
        for server, url in self.routes.items():
            if not url.startswith("http://") and not url.startswith("https://"):
                self.routes[server] = "http://" + url
                self.logger.info(f"Internal route '{server}' adjusted to include http://: {self.routes[server]}")
        
        # 微服务网关本身地址
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 20000)
        
        # 服务注册信息
        self.service_name = self.config.get("service_name", "MicroServiceGateway")
        self.service_id = self.config.get("service_id", f"{self.service_name}-{self.host}:{self.port}")
        self.health_check_url = self.config.get("health_check_url", f"http://{self.host}:{self.port}/health")
        
        # 初始化 httpx.AsyncClient
        self.client:  httpx.AsyncClient # 在lifespan中初始化
        
        # 初始化 FastAPI 应用，使用生命周期管理
        self.app = FastAPI(lifespan=self.lifespan)
        
        # 设置路由
        self.setup_routes()

    
    def _validate_config(self):
        """验证配置文件是否包含所有必需的配置项"""
        required_keys = ["consul_url", "routes", "services", "host", "port", "service_name", "service_id","health_check_url"]
        validate_config(required_keys, self.config, self.logger)
        
        # 检查 routes 是否为空
        if not self.routes:
            self.logger.error("No routes defined in configuration.")
            raise ValueError("No routes defined in configuration.")
        
        # 检查 routes 中的每个 URL 是否包含协议前缀
        for server, url in self.routes.items():
            if not url.startswith("http://") and not url.startswith("https://"):
                self.logger.warning(f"Route URL for '{server}' will be adjusted to include http://. Current URL: {url}")
        
        # 验证超时配置
        if self.request_timeout <= 0:
            self.logger.warning("Invalid request_timeout, using default 10.0")
            self.request_timeout = 10.0
        if self.read_timeout <= 0:
            self.logger.warning("Invalid read_timeout, using default 60.0") 
            self.read_timeout = 60.0

            
        
    @asynccontextmanager
    async def lifespan(self, app: FastAPI)-> AsyncGenerator[None, None]:
        """管理应用生命周期"""
        # 应用启动时执行
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(self.request_timeout, read=self.read_timeout)
        )
        self.logger.info("Async HTTP Client Initialized")
        
        task = None
        try:
            # 注册服务到 Consul
            self.logger.info("Registering service to Consul...")
            tags = ["MicroServiceGateway"]
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
            # 启动后台任务
            task = asyncio.create_task(update_service_instances_periodically(
                                            consul_url=self.consul_url,
                                            client=self.client,
                                            service_instances=self.service_instances,
                                            config=self.config,
                                            logger=self.logger
                                        ))
            
            yield  # 应用正常运行
        except Exception as e:
            self.logger.error(f"Exception during lifespan: {e}")
            raise
        finally:
                
            # 关闭后台任务
            # 如果 task 没有赋值过(None)，就不去 cancel
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    self.logger.info("Background task cancelled successfully.")
                
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
        """设置 API 路由"""
        
        @self.app.get("/health")
        async def health_check():
            """健康检查接口"""
            return {"status": "healthy"}

        # 聊天服务代理
        # @self.app.api_route("/agent/chat/to_ollama/chat", methods=["POST"], dependencies=[Depends(RateLimiter(times=10, seconds=1))])
        @self.app.api_route("/agent/chat/to_ollama/chat", methods=["POST"])
        async def ollma_chat_service_proxy(request: Request):
            prefix = "/agent/chat/to_ollama"
            path = "chat"
            server = "OllamaAgent"
            return await self.forward(request, prefix, path, server)

        
        # 用户测试服务器连通性
        @self.app.post("/option/ping/")
        async def usr_ping_server(time: str=Form(...), client_ip: str=Form(...)):
            return await self._usr_ping_server(time, client_ip)
        
        
        # 通用网关入口
        # @self.app.api_route("/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], dependencies=[Depends(RateLimiter(times=10, seconds=1))])
        @self.app.api_route("/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
        async def gateway(service_name: str, path: str, request: Request):
            return await self._gateway(service_name, path, request)
    
    
    async def _gateway(self, service_name: str, path: str, request: Request):
        """统一网关入口"""
        instance = get_next_instance(service_instances=self.service_instances,
                                     service_name=service_name,
                                     load_balancer_index=self.load_balancer_index,
                                     logger=self.logger)
        if not instance:
            self.logger.error(f"No available instances for service '{service_name}'.")
            raise HTTPException(status_code=503, detail=f"No available instances for service '{service_name}'")
        if not is_instance_healthy(service_name=service_name, instance=instance, failure_counts=self.failure_counts, logger=self.logger):
            self.logger.warning(f"Service instance {instance['address']}:{instance['port']} is unhealthy.")
            raise HTTPException(status_code=503, detail=f"Service instance {instance['address']}:{instance['port']} is unhealthy")
        target_url = f"http://{instance['address']}:{instance['port']}/{path}"
        self.logger.info(f"Forwarding {request.method} request to {target_url}")
        try:
            response = await self.client.request(
                method=request.method,
                url=target_url,
                headers=self.filter_headers(request.headers),
                content=await request.body(),
                timeout=httpx.Timeout(self.request_timeout, read=self.read_timeout)
            )
            # 检查响应状态
            response.raise_for_status()
            reset_failure(service_name=service_name, instance=instance, failure_counts=self.failure_counts, logger=self.logger)
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=self.filter_response_headers(response.headers)
            )
        except httpx.RequestError as e:
            record_failure(service_name=service_name, instance=instance, failure_counts=self.failure_counts, logger=self.logger)
            self.logger.error(f"Error connecting to service '{service_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error connecting to service '{service_name}': {e}")
        except httpx.HTTPStatusError as exc:
            record_failure(service_name=service_name, instance=instance, failure_counts=self.failure_counts, logger=self.logger)
            self.logger.error(f"HTTP error from service '{service_name}': {exc}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"{service_name} 返回错误")
             
     
    async def _usr_ping_server(self, time: str, client_ip: str):
        """接受用户端发来的ping，回送服务器信息"""         
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"Ping success."
        self.logger.info(f"Operator: usr_ping_server. Result: True, Message: {message}")
        return {"result": True, "message": message, "time": current_time}
    
    # --------------------------------
    # 请求转发过滤逻辑
    # --------------------------------     
    def filter_headers(self, headers):
        """过滤请求头，移除不必要的头"""
        excluded_headers = {"host", "content-length", "transfer-encoding", "connection"}
        return {k: v for k, v in headers.items() if k.lower() not in excluded_headers}
    

    def filter_response_headers(self, headers):
        """过滤响应头，移除不必要的头"""
        excluded_response_headers = {"content-encoding", "transfer-encoding", "connection"}
        return {k: v for k, v in headers.items() if k.lower() not in excluded_response_headers}

    
    async def forward(self, request: Request, prefix: str, path: str, server: str):
        """实际转发函数"""
        # 路径编码，防止路径遍历攻击，但保留正常的路径分隔符
        sanitized_path = quote(path, safe='/')

        # url拼接
        user_service_base_url = self.routes.get(server, '')
        if not user_service_base_url:
            self.logger.error(f"'{server}' environment variable in config.yml is not set.")
            raise HTTPException(status_code=500, detail=f"'{server}' URL is not configured.")

        user_service_url = urljoin(user_service_base_url, f"{prefix}/{sanitized_path}")

        self.logger.info(f"Forwarding {request.method} request for {prefix}/{path} to {user_service_url}")

        try:
            forwarded_response = await self.client.request(
                method=request.method,
                url=user_service_url,
                headers=self.filter_headers(request.headers),
                content=await request.body(),
                timeout=httpx.Timeout(self.request_timeout, read=self.read_timeout)
            )
            # 检查响应状态
            forwarded_response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            self.logger.error(f"HTTP error occurred while forwarding to '{server}': {exc}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"{server} 返回错误")
        except httpx.RequestError as exc:
            self.logger.error(f"Request error occurred while forwarding to '{server}': {exc}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"无法连接到 {server}")

        self.logger.info(f"Forwarded response with status {forwarded_response.status_code} for {prefix}/{path}")

        # 构建响应，保留状态码和头信息
        return Response(
            content=forwarded_response.content,
            status_code=forwarded_response.status_code,
            headers=self.filter_response_headers(forwarded_response.headers)
        )
    
    def run(self):
        uvicorn.run(self.app, host=self.host, port=self.port)
    

def main():
    server = MicroServiceGateway()
    server.run()
    
    
if __name__ == "__main__":
    main()
