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
from typing import Dict, List
from dotenv import dotenv_values
from collections import defaultdict

# from fastapi_limiter import FastAPILimiter
# from fastapi_limiter.depends import RateLimiter
# import redis.asyncio as redis  # 使用异步 Redis 客户端

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config


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
        
        # 初始化 AsyncClient 为 None
        self.client = None
        
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
                self.logger.error(f"Route URL for '{server}' must start with 'http://' or 'https://'. Current URL: {url}")
                raise ValueError(f"Route URL for '{server}' must start with 'http://' or 'https://'.")

            
        
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
            await self.register_service_to_consul(self.service_name, self.service_id, self.host, self.port, self.health_check_url)
            
            # 启动后台任务
            task = asyncio.create_task(self.update_service_instances_periodically())
            
            yield  # 应用正常运行
        except Exception as e:
            self.logger.error(f"Exception during lifespan: {e}")
            raise
        finally:
                
            # 关闭后台任务
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                self.logger.info("Background task cancelled successfully.")
                
            # 注销服务从 Consul
            try:
                self.logger.info("Deregistering service from Consul...")
                await self.unregister_service_from_consul(self.service_id)
                self.logger.info("Service deregistered from Consul.")
            except Exception as e:
                self.logger.error(f"Error while deregistering service: {e}")
                
            # 关闭 AsyncClient
            self.logger.info("Shutting down Async HTTP Client")
            if self.client:
                await self.client.aclose()

    
    
    # --------------------------------
    # 1. 服务发现与动态更新
    # --------------------------------
    async def get_service_instances(self, service_name: str) -> List[Dict]:
        """从 Consul 拉取服务实例列表"""
        url = f"{self.consul_url}/v1/catalog/service/{service_name}"
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                instances = [
                    {"address": instance["Address"], "port": instance["ServicePort"]}
                    for instance in response.json()
                ]
                if instances:
                    self.logger.info(f"Successfully fetched service instances for '{service_name}' from Consul.")
                    self.logger.debug(f"Service instances for '{service_name}': {instances}")
                else:
                    self.logger.error(f"No service instances found for '{service_name}' in Consul.")
                    # 可选择抛出异常或采取其他措施
                    # raise ValueError(f"No service instances found for '{service_name}' in Consul.")
                return instances
            else:
                self.logger.warning(f"Failed to fetch service instances for '{service_name}': {response.status_code}")
        except httpx.RequestError as exc:
            self.logger.error(f"Error fetching service instances from Consul for '{service_name}': {exc}")
        return []
    
    
   
    async def update_service_instances_periodically(self):
        """后台任务：定期更新服务实例"""
        while True:
            try:
                self.logger.info("Updating service instances...")
                # 从配置中动态获取需要监控的服务列表
                services = self.config.get("services", ["UserService"])
                for service_name in services:
                    instances = await self.get_service_instances(service_name)
                    self.service_instances[service_name] = instances
                    self.logger.debug(f"Service '{service_name}' instances updated: {instances}")
            except Exception as e:
                self.logger.error(f"Error updating service instances: {e}")
            await asyncio.sleep(10)  # 每 10 秒更新一次
        
    
    # --------------------------------
    # 2. 负载均衡
    # --------------------------------
    def get_next_instance(self, service_name: str) -> Dict:
        """获取服务的下一个实例（轮询负载均衡）"""
        instances = self.service_instances.get(service_name, [])
        if not instances:
            self.logger.warning(f"No instances found for service '{service_name}'.")
            return None

        index = self.load_balancer_index[service_name]
        instance = instances[index]
        self.load_balancer_index[service_name] = (index + 1) % len(instances)
        self.logger.debug(f"Selected instance {instance} for service '{service_name}'")
        return instance
    
    
    # --------------------------------
    # 3. 熔断机制
    # --------------------------------
    def is_instance_healthy(self, service_name: str, instance: Dict) -> bool:
        """检查服务实例是否健康"""
        failure_threshold = 3  # 设置失败阈值
        instance_key = f"{instance['address']}:{instance['port']}"
        is_healthy = self.failure_counts[service_name][instance_key] < failure_threshold
        self.logger.debug(f"Instance {instance_key} healthy: {is_healthy}")
        return is_healthy


    def record_failure(self, service_name: str, instance: Dict):
        """记录服务实例的失败次数"""
        instance_key = f"{instance['address']}:{instance['port']}"
        self.failure_counts[service_name][instance_key] += 1
        self.logger.warning(f"Recorded failure for {service_name} instance {instance_key}. Total failures: {self.failure_counts[service_name][instance_key]}")


    def reset_failure(self, service_name: str, instance: Dict):
        """重置服务实例的失败计数"""
        instance_key = f"{instance['address']}:{instance['port']}"
        self.failure_counts[service_name][instance_key] = 0
        self.logger.info(f"Reset failure count for {service_name} instance {instance_key}.")
        
    # --------------------------------
    # 4. 限流机制
    # --------------------------------
    # async def setup_redis_limiter(self):
    #     """初始化 Redis 用于限流"""
    #     redis_host = self.config.get("redis_host", "127.0.0.1")
    #     redis_port = self.config.get("redis_port", 6379)
    #     redis_db = self.config.get("redis_db", 0)
    #     try:
    #         redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
    #         await FastAPILimiter.init(redis_client)
    #         self.logger.info("FastAPILimiter initialized successfully.")
    #     except Exception as e:
    #         self.logger.error(f"Failed to initialize FastAPILimiter: {e}")
    #         raise   
        
        
    # --------------------------------
    # 5. Consul 服务注册与注销
    # --------------------------------
    async def register_service_to_consul(self, service_name, service_id, address, port, health_check_url, retries=3, delay=2.0):
        """向 Consul 注册该微服务网关"""
        payload = {
            "Name": service_name,
            "ID": service_id,
            "Address": address,
            "Port": port,
            "Tags": ["v1", "UserService"],
            "Check": {
                "HTTP": health_check_url,
                "Interval": "10s",
                "Timeout": "5s",
            }
        }

        for attempt in range(1, retries + 1):
            try:
                response = await self.client.put(f"{self.consul_url}/v1/agent/service/register", json=payload)
                if response.status_code == 200:
                    self.logger.info(f"Service '{service_name}' registered successfully to Consul.")
                    return
                else:
                    self.logger.warning(f"Attempt {attempt}: Failed to register service '{service_name}': {response.status_code}, {response.text}")
            except Exception as e:
                self.logger.error(f"Attempt {attempt}: Error while registering service '{service_name}': {e}")
            
            if attempt < retries:
                self.logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

        self.logger.error(f"All {retries} attempts to register service '{service_name}' failed.")
        raise HTTPException(status_code=500, detail="Service registration failed.")
    
    async def unregister_service_from_consul(self, service_id: str):
        """从 Consul 注销该微服务网关"""
        try:
            response = await self.client.put(f"{self.consul_url}/v1/agent/service/deregister/{service_id}")
            if response.status_code == 200:
                self.logger.info(f"Service with ID '{service_id}' deregistered successfully from Consul.")
            else:
                self.logger.warning(f"Failed to deregister service ID '{service_id}': {response.status_code}, {response.text}")
        except Exception as e:
            self.logger.error(f"Error while deregistering service ID '{service_id}': {e}")
    
    
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
        instance = self.get_next_instance(service_name)
        if not instance:
            self.logger.error(f"No available instances for service '{service_name}'.")
            raise HTTPException(status_code=503, detail=f"No available instances for service '{service_name}'")
        if not self.is_instance_healthy(service_name, instance):
            self.logger.warning(f"Service instance {instance['address']}:{instance['port']} is unhealthy.")
            raise HTTPException(status_code=503, detail=f"Service instance {instance['address']}:{instance['port']} is unhealthy")
        target_url = f"{instance['address']}:{instance['port']}/{path}"
        try:
            response = await self.client.request(
                method=request.method,
                url=target_url,
                headers=self.filter_headers(request.headers),
                content=await request.body(),
                timeout=httpx.Timeout(10.0, read=60.0)
            )
            self.reset_failure(service_name, instance)
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=self.filter_response_headers(response.headers)
            )
        except httpx.RequestError as e:
            self.record_failure(service_name, instance)
            self.logger.error(f"Error connecting to service '{service_name}': {e}")
            raise HTTPException(status_code=500, detail=f"Error connecting to service '{service_name}': {e}")
        except httpx.HTTPStatusError as exc:
            self.record_failure(service_name, instance)
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
        # 路径编码，防止路径遍历攻击
        sanitized_path = quote(path, safe='')

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
                timeout=httpx.Timeout(10.0, read=60.0)
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
    