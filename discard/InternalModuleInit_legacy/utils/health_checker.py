"""
模块健康检查工具

提供对内部模块运行状态的检查功能。
"""

from typing import Dict, Any, Optional, List, Tuple
from ..exceptions import ModuleError


class ModuleHealthChecker:
    """模块健康检查器"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def check_module_health(self, module_name: str, module_instance: Any) -> Tuple[bool, str]:
        """
        检查单个模块的健康状态
        
        Args:
            module_name: 模块名称
            module_instance: 模块实例
            
        Returns:
            Tuple[bool, str]: (是否健康, 状态描述)
        """
        try:
            # 检查基本实例状态
            if module_instance is None:
                return False, "Module instance is None"
            
            # 检查是否有健康检查方法
            if hasattr(module_instance, 'health_check'):
                try:
                    health_result = module_instance.health_check()
                    if isinstance(health_result, bool):
                        return health_result, "Health check passed" if health_result else "Health check failed"
                    elif isinstance(health_result, dict):
                        status = health_result.get('status', False)
                        message = health_result.get('message', 'No message')
                        return status, message
                    else:
                        return True, "Health check method exists but returned unexpected format"
                except Exception as e:
                    return False, f"Health check method failed: {str(e)}"
            
            # 如果没有专门的健康检查方法，检查基本属性
            if hasattr(module_instance, '__class__'):
                return True, f"Module instance of {module_instance.__class__.__name__} is active"
            
            return True, "Module instance exists"
            
        except Exception as e:
            self.logger.error(f"Error checking health for module {module_name}: {str(e)}")
            return False, f"Health check error: {str(e)}"
    
    def check_modules_health(self, modules: List[Tuple[str, Any]]) -> Dict[str, Tuple[bool, str]]:
        """
        批量检查多个模块的健康状态
        
        Args:
            modules: 模块列表，格式为 [(module_name, module_instance), ...]
            
        Returns:
            Dict[str, Tuple[bool, str]]: {module_name: (is_healthy, status_message)}
        """
        health_status = {}
        
        for module_name, module_instance in modules:
            try:
                is_healthy, message = self.check_module_health(module_name, module_instance)
                health_status[module_name] = (is_healthy, message)
                
                if is_healthy:
                    self.logger.debug(f"Module {module_name} is healthy: {message}")
                else:
                    self.logger.warning(f"Module {module_name} is unhealthy: {message}")
                    
            except Exception as e:
                error_msg = f"Failed to check health: {str(e)}"
                health_status[module_name] = (False, error_msg)
                self.logger.error(f"Health check failed for module {module_name}: {error_msg}")
        
        return health_status
    
    def get_health_summary(self, modules: List[Tuple[str, Any]]) -> Dict[str, Any]:
        """
        获取模块健康状态摘要
        
        Args:
            modules: 模块列表
            
        Returns:
            包含健康状态摘要的字典
        """
        health_status = self.check_modules_health(modules)
        
        healthy_modules = []
        unhealthy_modules = []
        
        for module_name, (is_healthy, message) in health_status.items():
            if is_healthy:
                healthy_modules.append(module_name)
            else:
                unhealthy_modules.append((module_name, message))
        
        total_modules = len(modules)
        healthy_count = len(healthy_modules)
        unhealthy_count = len(unhealthy_modules)
        
        summary = {
            "total_modules": total_modules,
            "healthy_count": healthy_count,
            "unhealthy_count": unhealthy_count,
            "health_percentage": (healthy_count / total_modules * 100) if total_modules > 0 else 0,
            "healthy_modules": healthy_modules,
            "unhealthy_modules": unhealthy_modules,
            "overall_healthy": unhealthy_count == 0
        }
        
        return summary
