"""
服务发现模块

提供服务发现、连接管理和健康检查功能。
用于替代原有的ExternalServiceInit，实现服务发现模式。
"""

from .service_discovery_manager import ServiceDiscoveryManager
from .service_connector import ExternalServiceConnector
from .exceptions import (
    ServiceDiscoveryError,
    ServiceNotFoundError,
    ServiceConnectionError,
    ServiceHealthCheckError
)

__all__ = [
    'ServiceDiscoveryManager',
    'ExternalServiceConnector',
    'ServiceDiscoveryError',
    'ServiceNotFoundError',
    'ServiceConnectionError',
    'ServiceHealthCheckError'
]
