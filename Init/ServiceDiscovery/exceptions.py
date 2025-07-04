"""
服务发现相关异常定义
"""

from typing import Optional


class ServiceDiscoveryError(Exception):
    """服务发现基础异常"""
    def __init__(self, message: str, service_name: Optional[str] = None):
        self.service_name = service_name
        super().__init__(message)


class ServiceNotFoundError(ServiceDiscoveryError):
    """服务未找到异常"""
    def __init__(self, service_name: str, message: Optional[str] = None):
        if message is None:
            message = f"Service '{service_name}' not found in service registry"
        super().__init__(message, service_name)


class ServiceConnectionError(ServiceDiscoveryError):
    """服务连接失败异常"""
    def __init__(self, service_name: str, endpoint: Optional[str] = None, message: Optional[str] = None):
        self.endpoint = endpoint
        if message is None:
            message = f"Failed to connect to service '{service_name}'"
            if endpoint:
                message += f" at {endpoint}"
        super().__init__(message, service_name)


class ServiceHealthCheckError(ServiceDiscoveryError):
    """服务健康检查失败异常"""
    def __init__(self, service_name: str, endpoint: Optional[str] = None, message: Optional[str] = None):
        self.endpoint = endpoint
        if message is None:
            message = f"Health check failed for service '{service_name}'"
            if endpoint:
                message += f" at {endpoint}"
        super().__init__(message, service_name)


class ServiceRegistrationError(ServiceDiscoveryError):
    """服务注册失败异常"""
    def __init__(self, service_name: str, message: Optional[str] = None):
        if message is None:
            message = f"Failed to register service '{service_name}'"
        super().__init__(message, service_name)


class ConsulConnectionError(ServiceDiscoveryError):
    """Consul连接失败异常"""
    def __init__(self, consul_url: str, message: Optional[str] = None):
        self.consul_url = consul_url
        if message is None:
            message = f"Failed to connect to Consul at {consul_url}"
        super().__init__(message)
