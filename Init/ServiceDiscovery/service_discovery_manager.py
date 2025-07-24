"""
服务发现管理器

负责通过Consul进行服务发现、健康检查和服务状态监控。
"""

import asyncio
import httpx
from typing import Dict, List, Optional, Tuple, Any
from logging import Logger

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config
from .exceptions import (
    ServiceDiscoveryError,
    ServiceNotFoundError,
    ServiceConnectionError,
    ServiceHealthCheckError,
    ConsulConnectionError
)


class ServiceInfo:
    """服务信息类"""
    def __init__(self, name: str, address: str, port: int, tags: List[str] | None = None):
        self.name = name
        self.address = address
        self.port = port
        self.tags = tags or []
        self.url = f"http://{address}:{port}"
        self.health_status = "unknown"
        self.last_check = None
    
    def __repr__(self):
        return f"ServiceInfo(name={self.name}, url={self.url}, status={self.health_status})"


class ServiceDiscoveryManager:
    """
    服务发现管理器
    
    主要功能：
    - 从Consul发现服务
    - 健康检查
    - 服务状态监控
    - 服务注册（可选）
    """
    
    def __init__(self, consul_url: str = "http://127.0.0.1:8500", config_path: Optional[str] = None):
        """
        初始化服务发现管理器
        
        Args:
            consul_url: Consul服务地址
            config_path: 配置文件路径
        """
        self.logger = setup_logger(name="ServiceDiscovery", log_path="Other")
        self.consul_url = consul_url.rstrip('/')
        
        # HTTP客户端
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
        
        # 服务缓存
        self.discovered_services: Dict[str, ServiceInfo] = {}
        
        # 配置
        self.config = self._load_config(config_path)
        
        # 必需服务列表
        self.required_services = self.config.get("required_services", [
            "ollama_server",
            "GPTSoVits_server", 
            "SenseVoice_server"
        ])
        
        # 服务映射（Consul服务名 -> 内部服务名）
        self.service_mapping = self.config.get("service_mapping", {
            "ollama_server": "llm_service",
            "GPTSoVits_server": "tts_service",
            "SenseVoice_server": "stt_service"
        })
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """加载配置"""
        if config_path:
            try:
                return load_config(config_path, "service_discovery", self.logger)
            except Exception as e:
                self.logger.warning(f"Failed to load config from {config_path}: {e}")
                self.logger.info("Using default configuration.")
        
        # 默认配置
        return {
            "required_services": [
                "ollama_server",
                "GPTSoVits_server", 
                "SenseVoice_server"
            ],
            "service_mapping": {
                "ollama_server": "llm_service",
                "GPTSoVits_server": "tts_service", 
                "SenseVoice_server": "stt_service"
            },
            "health_check": {
                "timeout": 5,
                "retry_count": 3,
                "retry_delay": 2
            }
        }
    
    async def discover_all_services(self) -> Dict[str, ServiceInfo]:
        """
        发现所有必需的服务
        
        Returns:
            Dict[str, ServiceInfo]: 服务名 -> 服务信息
        """
        self.logger.info("开始服务发现...")
        
        # 检查Consul连接
        await self._check_consul_connection()
        
        discovered = {}
        missing_services = []
        
        for service_name in self.required_services:
            try:
                service_info = await self._discover_single_service(service_name)
                if service_info:
                    # 使用映射后的服务名作为key
                    mapped_name = self.service_mapping.get(service_name, service_name)
                    discovered[mapped_name] = service_info
                    self.logger.info(f"✅ 发现服务: {service_name} -> {service_info.url}")
                else:
                    missing_services.append(service_name)
                    self.logger.error(f"❌ 服务未找到: {service_name}")
            except Exception as e:
                missing_services.append(service_name)
                self.logger.error(f"❌ 发现服务失败 {service_name}: {e}")
        
        if missing_services:
            raise ServiceNotFoundError(
                ", ".join(missing_services),
                f"Missing required services: {missing_services}"
            )
        
        # 缓存发现的服务
        self.discovered_services.update(discovered)
        
        self.logger.info(f"服务发现完成，共发现 {len(discovered)} 个服务")
        return discovered
    
    async def _check_consul_connection(self):
        """检查Consul连接"""
        try:
            response = await self.client.get(f"{self.consul_url}/v1/status/leader")
            response.raise_for_status()
            self.logger.info("✅ Consul连接正常")
        except Exception as e:
            raise ConsulConnectionError(
                self.consul_url,
                f"无法连接到Consul: {str(e)}"
            )
    
    async def _discover_single_service(self, service_name: str) -> Optional[ServiceInfo]:
        """
        发现单个服务
        
        Args:
            service_name: 服务名称
            
        Returns:
            ServiceInfo: 服务信息，如果未找到返回None
        """
        try:
            # 查询Consul服务目录
            url = f"{self.consul_url}/v1/catalog/service/{service_name}"
            response = await self.client.get(url)
            response.raise_for_status()
            
            services = response.json()
            if not services:
                return None
            
            # 选择第一个健康的服务实例
            for service in services:
                service_info = ServiceInfo(
                    name=service_name,
                    address=service.get("ServiceAddress") or service.get("Address"),
                    port=service.get("ServicePort"),
                    tags=service.get("ServiceTags", [])
                )
                
                # 检查服务健康状态
                if await self._check_service_health(service_info):
                    return service_info
            
            return None
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise ServiceDiscoveryError(f"Consul API error for {service_name}: {e}")
        except Exception as e:
            raise ServiceDiscoveryError(f"Failed to discover service {service_name}: {e}")
    
    async def _check_service_health(self, service_info: ServiceInfo) -> bool:
        """
        检查服务健康状态
        
        Args:
            service_info: 服务信息
            
        Returns:
            bool: 是否健康
        """
        health_config = self.config.get("health_check", {})
        timeout = health_config.get("timeout", 5)
        retry_count = health_config.get("retry_count", 3)
        retry_delay = health_config.get("retry_delay", 2)
        
        # 定义健康检查端点
        health_endpoints = {
            "ollama_server": "/api/tags",
            "GPTSoVits_server": "/health",
            "SenseVoice_server": "/health"
        }
        
        health_path = health_endpoints.get(service_info.name, "/health")
        health_url = f"{service_info.url}{health_path}"
        
        for attempt in range(retry_count):
            try:
                response = await self.client.get(health_url, timeout=timeout)
                if response.status_code == 200:
                    service_info.health_status = "healthy"
                    return True
                else:
                    self.logger.warning(
                        f"Health check failed for {service_info.name}: "
                        f"HTTP {response.status_code}"
                    )
            except Exception as e:
                self.logger.warning(
                    f"Health check attempt {attempt + 1} failed for {service_info.name}: {e}"
                )
                
                if attempt < retry_count - 1:
                    await asyncio.sleep(retry_delay)
        
        service_info.health_status = "unhealthy"
        return False
    
    async def get_service_info(self, service_name: str) -> ServiceInfo:
        """
        获取服务信息
        
        Args:
            service_name: 服务名称
            
        Returns:
            ServiceInfo: 服务信息
        """
        if service_name not in self.discovered_services:
            # 尝试重新发现服务
            original_name = None
            for k, v in self.service_mapping.items():
                if v == service_name:
                    original_name = k
                    break
            
            if original_name:
                service_info = await self._discover_single_service(original_name)
                if service_info:
                    self.discovered_services[service_name] = service_info
                else:
                    raise ServiceNotFoundError(service_name)
            else:
                raise ServiceNotFoundError(service_name)
        
        return self.discovered_services[service_name]
    
    async def refresh_service_health(self) -> Dict[str, bool]:
        """
        刷新所有服务的健康状态
        
        Returns:
            Dict[str, bool]: 服务名 -> 健康状态
        """
        health_status = {}
        
        for service_name, service_info in self.discovered_services.items():
            is_healthy = await self._check_service_health(service_info)
            health_status[service_name] = is_healthy
            
            if is_healthy:
                self.logger.debug(f"✅ {service_name} 健康")
            else:
                self.logger.warning(f"❌ {service_name} 不健康")
        
        return health_status
    
    async def wait_for_services(self, timeout: int = 60) -> bool:
        """
        等待所有必需服务就绪
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否所有服务都就绪
        """
        self.logger.info(f"等待服务就绪，超时时间: {timeout}秒")
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            try:
                await self.discover_all_services()
                health_status = await self.refresh_service_health()
                
                if all(health_status.values()):
                    self.logger.info("✅ 所有服务已就绪")
                    return True
                
                unhealthy_services = [name for name, healthy in health_status.items() if not healthy]
                self.logger.info(f"等待服务就绪: {unhealthy_services}")
                
            except Exception as e:
                self.logger.warning(f"服务检查失败: {e}")
            
            # 检查超时
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                self.logger.error(f"等待服务超时 ({timeout}秒)")
                return False
            
            # 等待重试
            await asyncio.sleep(5)
    
    async def cleanup(self):
        """清理资源"""
        self.logger.info("清理ServiceDiscoveryManager资源...")
        try:
            if hasattr(self, 'client') and self.client and not self.client.is_closed:
                await self.client.aclose()
                self.logger.debug("HTTP客户端已关闭")
            self.client = None
        except Exception as e:
            self.logger.warning(f"清理ServiceDiscoveryManager资源时出错: {e}")
    
    def __del__(self):
        """析构函数 - 不执行异步操作以避免警告"""
        # 不在析构函数中执行异步操作，只做标记
        if hasattr(self, 'client') and self.client and not getattr(self.client, 'is_closed', True):
            import warnings
            warnings.warn(
                "ServiceDiscoveryManager客户端未正确关闭，请确保调用cleanup()方法",
                ResourceWarning,
                stacklevel=2
            )
