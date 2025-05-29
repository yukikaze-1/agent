"""
    封装与 EnvironmentManager 微服务的交互逻辑。UserService微服务会调用此模块
"""

import httpx
from logging import Logger
from typing import Any, Dict, List
from fastapi import HTTPException, status


class EnvironmentManagerClient:
    """
    封装与 EnvironmentManager 微服务的交互逻辑。
    """
    def __init__(self, consul_url: str, service_name: str, http_client: httpx.AsyncClient, logger: Logger):
        """
        初始化 EnvironmentManagerClient。

        参数:
            - consul_url (str): Consul 的 URL，用于服务发现。
            - service_name (str): EnvironmentManager 的服务名称。
            - http_client (httpx.AsyncClient): 共享的 HTTP 客户端。
            - logger (Any): 日志记录器实例。
        """
        self.consul_url = consul_url
        self.service_name = service_name
        self.client = http_client
        self.logger = logger
        self.load_balancer_index = 0

    async def get_service_instances(self) -> List[Dict[str, Any]]:
        """从 Consul 获取 EnvironmentManager 的服务实例列表。"""
        url = f"{self.consul_url}/v1/catalog/service/{self.service_name}"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            instances = [{"address": instance["Address"], "port": instance["ServicePort"]} for instance in response.json()]
            if not instances:
                self.logger.error(f"No instances found for service '{self.service_name}'.")
            return instances
        except httpx.RequestError as exc:
            self.logger.error(f"Error fetching service instances for '{self.service_name}': {exc}")
            return []
        except httpx.HTTPStatusError as exc:
            self.logger.error(f"HTTP error fetching service instances for '{self.service_name}': {exc}")
            return []

    async def call_endpoint(self, endpoint: str, data: Dict[str, Any]) -> Any:
        """调用 EnvironmentManager 的指定端点。"""
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
    