"""
环境管理器客户端
封装与EnvironmentManager微服务的交互逻辑，提供服务发现和API调用功能
"""

import httpx
from logging import Logger
from typing import Any, Dict, List
from fastapi import HTTPException, status


class EnvironmentManagerClient:
    """
    环境管理器客户端
    封装与EnvironmentManager微服务的交互逻辑，提供服务发现和负载均衡功能
    """
    def __init__(self, consul_url: str, service_name: str, http_client: httpx.AsyncClient, logger: Logger):
        """
        初始化环境管理器客户端

        :param consul_url: Consul服务发现URL
        :param service_name: EnvironmentManager服务名称
        :param http_client: 共享的HTTP客户端
        :param logger: 日志记录器实例
        """
        self.consul_url = consul_url
        self.service_name = service_name
        self.client = http_client
        self.logger = logger
        self.load_balancer_index = 0

    async def get_service_instances(self) -> List[Dict[str, Any]]:
        """
        从Consul获取EnvironmentManager的服务实例列表
        
        :return: 服务实例列表，包含地址和端口信息
        """
        url = f"{self.consul_url}/v1/catalog/service/{self.service_name}"
        try:
            # 发送请求获取服务实例
            response = await self.client.get(url)
            response.raise_for_status()
            instances = [{"address": instance["Address"], "port": instance["ServicePort"]} for instance in response.json()]
            if not instances:
                self.logger.error(f"未找到服务 '{self.service_name}' 的实例")
            return instances
        except httpx.RequestError as exc:
            self.logger.error(f"获取服务 '{self.service_name}' 实例时发生请求错误：{exc}")
            return []
        except httpx.HTTPStatusError as exc:
            self.logger.error(f"获取服务 '{self.service_name}' 实例时发生HTTP错误：{exc}")
            return []

    async def call_endpoint(self, endpoint: str, data: Dict[str, Any]) -> Any:
        """
        调用EnvironmentManager的指定端点
        
        :param endpoint: API端点路径
        :param data: 请求数据
        :return: API响应结果
        """
        # 获取可用的服务实例
        instances = await self.get_service_instances()
        if not instances:
            self.logger.error(f"No instances available for service '{self.service_name}'.")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="EnvironmentManager service unavailable.")

        # 简单轮询负载均衡
        instance = instances[self.load_balancer_index]
        self.load_balancer_index = (self.load_balancer_index + 1) % len(instances)
        service_url = f"http://{instance['address']}:{instance['port']}/{endpoint}"

        try:
            response = await self.client.post(service_url, json=data, timeout=120.0)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            self.logger.error(f"Request error when calling '{service_url}': {exc}")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to communicate with EnvironmentManager.")
        except httpx.HTTPStatusError as exc:
            self.logger.error(f"HTTP error when calling '{service_url}': {exc.response.status_code} {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
    