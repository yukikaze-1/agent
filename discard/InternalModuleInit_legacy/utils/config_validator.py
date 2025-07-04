"""
配置验证工具

提供内部模块配置的验证功能。
"""

import os
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from ..exceptions import ModuleConfigError


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def validate_module_structure(self, config: Dict[str, Any]) -> bool:
        """验证模块配置结构"""
        required_keys = ["base_modules", "optional_modules", "support_modules"]
        
        for key in required_keys:
            if key not in config:
                raise ModuleConfigError(f"Missing required key '{key}' in config")
        
        return True
    
    def validate_module_list(self, modules: List[Dict[str, str]], module_type: str) -> bool:
        """验证模块列表格式"""
        if not isinstance(modules, list):
            raise ModuleConfigError(f"{module_type} must be a list")
        
        for i, module in enumerate(modules):
            if not isinstance(module, dict):
                raise ModuleConfigError(f"{module_type}[{i}] must be a dictionary")
            
            if len(module) != 1:
                raise ModuleConfigError(
                    f"{module_type}[{i}] must contain exactly one key-value pair, "
                    f"got {len(module)}"
                )
            
            module_name = list(module.keys())[0]
            module_path = list(module.values())[0]
            
            if not isinstance(module_name, str) or not module_name.strip():
                raise ModuleConfigError(f"{module_type}[{i}] has invalid module name")
            
            if not isinstance(module_path, str) or not module_path.strip():
                raise ModuleConfigError(f"{module_type}[{i}] has invalid module path")
        
        return True
    
    def validate_module_path(self, module_name: str, module_path: str) -> bool:
        """验证模块路径是否有效"""
        try:
            # 尝试验证模块路径格式
            path_parts = module_path.split('.')
            if len(path_parts) < 2:
                raise ModuleConfigError(
                    f"Invalid module path '{module_path}' for module '{module_name}'. "
                    "Expected format: 'Package.Subpackage.Module'"
                )
            
            # 可以添加更多路径验证逻辑
            return True
            
        except Exception as e:
            raise ModuleConfigError(
                f"Error validating module path '{module_path}' for module '{module_name}': {str(e)}"
            )
    
    def validate_support_modules(self, support_modules: List[str]) -> bool:
        """验证支持的模块列表"""
        if not isinstance(support_modules, list):
            raise ModuleConfigError("support_modules must be a list")
        
        for module in support_modules:
            if not isinstance(module, str) or not module.strip():
                raise ModuleConfigError(f"Invalid support module name: {module}")
        
        return True


def validate_module_config(config: Dict[str, Any], logger) -> bool:
    """
    验证内部模块配置的完整性和正确性
    
    Args:
        config: 配置字典
        logger: 日志记录器
        
    Returns:
        bool: 验证是否通过
        
    Raises:
        ModuleConfigError: 当配置无效时
    """
    validator = ConfigValidator(logger)
    
    # 验证基本结构
    validator.validate_module_structure(config)
    
    # 验证base模块
    base_modules = config.get("base_modules", [])
    validator.validate_module_list(base_modules, "base_modules")
    
    # 验证optional模块
    optional_modules = config.get("optional_modules", [])
    validator.validate_module_list(optional_modules, "optional_modules")
    
    # 验证支持的模块列表
    support_modules = config.get("support_modules", [])
    validator.validate_support_modules(support_modules)
    
    # 验证所有模块路径
    all_modules = base_modules + optional_modules
    for module_dict in all_modules:
        module_name = list(module_dict.keys())[0]
        module_path = list(module_dict.values())[0]
        validator.validate_module_path(module_name, module_path)
        
        # 检查模块是否在支持列表中
        if module_name not in support_modules:
            logger.warning(f"Module '{module_name}' is not in support_modules list")
    
    logger.info("Module configuration validation passed")
    return True
