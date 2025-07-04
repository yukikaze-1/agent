"""
外部服务连接器

负责连接到已发现的外部服务，管理HTTP客户端连接。
"""

import httpx
import asyncio
from typing import Dict, Optional, Any, List
from logging import Logger

from Module.Utils.Logger import setup_logger
from .service_discovery_manager import ServiceDiscoveryManager, ServiceInfo
from .exceptions import (
    ServiceConnectionError,
    ServiceHealthCheckError,
    ServiceNotFoundError
)


class ServiceClient:
    """服务客户端包装器"""
    
    def __init__(self, service_info: ServiceInfo, client: httpx.AsyncClient):
        self.service_info = service_info
        self.client = client
        self.base_url = service_info.url
    
    async def get(self, path: str, **kwargs) -> httpx.Response:
        """GET请求"""
        url = f"{self.base_url}{path}"
        return await self.client.get(url, **kwargs)
    
    async def post(self, path: str, **kwargs) -> httpx.Response:
        """POST请求"""
        url = f"{self.base_url}{path}"
        return await self.client.post(url, **kwargs)
    
    async def put(self, path: str, **kwargs) -> httpx.Response:
        """PUT请求"""
        url = f"{self.base_url}{path}"
        return await self.client.put(url, **kwargs)
    
    async def delete(self, path: str, **kwargs) -> httpx.Response:
        """DELETE请求"""
        url = f"{self.base_url}{path}"
        return await self.client.delete(url, **kwargs)
    
    def __repr__(self):
        return f"ServiceClient(service={self.service_info.name}, url={self.base_url})"


class ExternalServiceConnector:
    """
    外部服务连接器
    
    负责：
    - 连接到已发现的外部服务
    - 管理HTTP客户端连接
    - 提供服务客户端接口
    - 连接健康监控
    """
    
    def __init__(self, discovery_manager: ServiceDiscoveryManager):
        """
        初始化服务连接器
        
        Args:
            discovery_manager: 服务发现管理器
        """
        self.logger = setup_logger(name="ServiceConnector", log_path="Other")
        self.discovery_manager = discovery_manager
        
        # 服务客户端缓存
        self.service_clients: Dict[str, ServiceClient] = {}
        
        # HTTP客户端配置
        self.client_config = {
            "timeout": httpx.Timeout(10.0, read=60.0),
            "limits": httpx.Limits(max_connections=100, max_keepalive_connections=20),
            "follow_redirects": True
        }
    
    async def initialize_connections(self) -> Dict[str, ServiceClient]:
        """
        初始化所有服务连接
        
        Returns:
            Dict[str, ServiceClient]: 服务名 -> 服务客户端
        """
        self.logger.info("初始化服务连接...")
        
        # 首先发现所有服务
        discovered_services = await self.discovery_manager.discover_all_services()
        
        # 为每个服务创建客户端
        connected_services = {}
        failed_services = []
        
        for service_name, service_info in discovered_services.items():
            try:
                client = await self._create_service_client(service_info)
                connected_services[service_name] = client
                self.logger.info(f"✅ 连接服务成功: {service_name} -> {service_info.url}")
            except Exception as e:
                failed_services.append(service_name)
                self.logger.error(f"❌ 连接服务失败: {service_name} -> {e}")
        
        if failed_services:
            raise ServiceConnectionError(
                ", ".join(failed_services),
                message=f"Failed to connect to services: {failed_services}"
            )
        
        # 缓存连接
        self.service_clients.update(connected_services)
        
        self.logger.info(f"服务连接初始化完成，共连接 {len(connected_services)} 个服务")
        return connected_services
    
    async def _create_service_client(self, service_info: ServiceInfo) -> ServiceClient:
        """
        创建服务客户端
        
        Args:
            service_info: 服务信息
            
        Returns:
            ServiceClient: 服务客户端
        """
        # 创建专用的HTTP客户端
        client = httpx.AsyncClient(
            base_url=service_info.url,
            **self.client_config
        )
        
        # 测试连接
        await self._test_connection(service_info, client)
        
        return ServiceClient(service_info, client)
    
    async def _test_connection(self, service_info: ServiceInfo, client: httpx.AsyncClient):
        """
        测试服务连接
        
        Args:
            service_info: 服务信息
            client: HTTP客户端
        """
        # 定义测试端点
        test_endpoints = {
            "ollama_server": "/api/tags",
            "GPTSoVits_server": "/health",
            "SenseVoice_server": "/health"
        }
        
        test_path = test_endpoints.get(service_info.name, "/health")
        
        try:
            response = await client.get(test_path, timeout=5.0)
            response.raise_for_status()
            self.logger.debug(f"连接测试成功: {service_info.name}{test_path}")
        except Exception as e:
            raise ServiceConnectionError(
                service_info.name,
                service_info.url,
                f"Connection test failed: {str(e)}"
            )
    
    async def get_service_client(self, service_name: str) -> ServiceClient:
        """
        获取服务客户端
        
        Args:
            service_name: 服务名称
            
        Returns:
            ServiceClient: 服务客户端
        """
        if service_name not in self.service_clients:
            # 尝试重新连接
            service_info = await self.discovery_manager.get_service_info(service_name)
            client = await self._create_service_client(service_info)
            self.service_clients[service_name] = client
        
        return self.service_clients[service_name]
    
    async def reconnect_service(self, service_name: str) -> ServiceClient:
        """
        重新连接服务
        
        Args:
            service_name: 服务名称
            
        Returns:
            ServiceClient: 新的服务客户端
        """
        self.logger.info(f"重新连接服务: {service_name}")
        
        # 关闭旧连接
        if service_name in self.service_clients:
            old_client = self.service_clients[service_name]
            await old_client.client.aclose()
            del self.service_clients[service_name]
        
        # 重新发现服务
        service_info = await self.discovery_manager.get_service_info(service_name)
        
        # 创建新连接
        new_client = await self._create_service_client(service_info)
        self.service_clients[service_name] = new_client
        
        self.logger.info(f"✅ 服务重连成功: {service_name}")
        return new_client
    
    async def check_connections_health(self) -> Dict[str, bool]:
        """
        检查所有连接的健康状态
        
        Returns:
            Dict[str, bool]: 服务名 -> 健康状态
        """
        health_status = {}
        
        for service_name, service_client in self.service_clients.items():
            try:
                # 简单的健康检查
                test_endpoints = {
                    "llm_service": "/api/tags",
                    "tts_service": "/health",
                    "stt_service": "/health"
                }
                
                test_path = test_endpoints.get(service_name, "/health")
                response = await service_client.get(test_path, timeout=5.0)
                
                health_status[service_name] = response.status_code == 200
                
                if response.status_code == 200:
                    self.logger.debug(f"✅ {service_name} 连接健康")
                else:
                    self.logger.warning(f"❌ {service_name} 连接异常: HTTP {response.status_code}")
                    
            except Exception as e:
                health_status[service_name] = False
                self.logger.warning(f"❌ {service_name} 连接检查失败: {e}")
        
        return health_status
    
    async def wait_for_all_services(self, timeout: int = 60) -> bool:
        """
        等待所有服务连接就绪
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否所有服务都连接成功
        """
        self.logger.info(f"等待所有服务连接就绪，超时: {timeout}秒")
        
        # 等待服务发现完成
        if not await self.discovery_manager.wait_for_services(timeout):
            return False
        
        # 初始化连接
        try:
            await self.initialize_connections()
            return True
        except Exception as e:
            self.logger.error(f"服务连接初始化失败: {e}")
            return False
    
    def get_service_url(self, service_name: str) -> Optional[str]:
        """
        获取服务URL
        
        Args:
            service_name: 服务名称
            
        Returns:
            str: 服务URL，如果不存在返回None
        """
        if service_name in self.service_clients:
            return self.service_clients[service_name].base_url
        return None
    
    def list_connected_services(self) -> List[str]:
        """
        列出所有已连接的服务
        
        Returns:
            List[str]: 服务名称列表
        """
        return list(self.service_clients.keys())
    
    async def cleanup(self):
        """清理所有连接"""
        self.logger.info("清理服务连接...")
        
        for service_name, service_client in self.service_clients.items():
            try:
                await service_client.client.aclose()
                self.logger.debug(f"清理连接: {service_name}")
            except Exception as e:
                self.logger.warning(f"清理连接失败 {service_name}: {e}")
        
        self.service_clients.clear()
        
        # 清理发现管理器
        await self.discovery_manager.cleanup()
        
        self.logger.info("服务连接清理完成")
    
    def __del__(self):
        """析构函数"""
        try:
            if hasattr(self, 'service_clients') and self.service_clients:
                asyncio.create_task(self.cleanup())
        except Exception:
            pass
