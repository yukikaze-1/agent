"""
模块动态加载工具

提供动态加载和实例化内部模块的功能。
"""

import importlib
from logging import Logger
from typing import Any, Dict, Optional, Type
from logging import Logger
from ..exceptions import ModuleLoadError, ModuleDependencyError


class ModuleLoader:
    """模块加载器"""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self._loaded_modules: Dict[str, Any] = {}
    
    def load_module(self, module_name: str, module_path: str) -> Any:
        """
        动态加载模块
        
        Args:
            module_name: 模块类名
            module_path: 模块导入路径
            
        Returns:
            模块类对象
            
        Raises:
            ModuleLoadError: 当模块加载失败时
        """
        cache_key = f"{module_path}.{module_name}"
        
        # 检查缓存
        if cache_key in self._loaded_modules:
            self.logger.debug(f"Using cached module: {cache_key}")
            return self._loaded_modules[cache_key]
        
        try:
            # 动态导入模块
            module = importlib.import_module(module_path)
            
            # 获取类对象
            cls = getattr(module, module_name, None)
            if cls is None:
                raise ModuleLoadError(
                    module_name, 
                    module_path, 
                    f"Class '{module_name}' not found in module '{module_path}'"
                )
            
            # 缓存已加载的模块
            self._loaded_modules[cache_key] = cls
            self.logger.debug(f"Successfully loaded module: {cache_key}")
            
            return cls
            
        except ModuleNotFoundError as e:
            raise ModuleLoadError(
                module_name, 
                module_path, 
                f"Module '{module_path}' could not be found: {str(e)}"
            ) from e
        except AttributeError as e:
            raise ModuleLoadError(
                module_name, 
                module_path, 
                f"Module '{module_path}' does not contain class '{module_name}': {str(e)}"
            ) from e
        except Exception as e:
            raise ModuleLoadError(
                module_name, 
                module_path, 
                f"Unexpected error loading module: {str(e)}"
            ) from e
    
    def create_instance(self, module_class: Type, *args, **kwargs) -> Any:
        """
        创建模块实例
        
        Args:
            module_class: 模块类
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            模块实例
            
        Raises:
            ModuleLoadError: 当实例创建失败时
        """
        try:
            instance = module_class(*args, **kwargs)
            self.logger.debug(f"Successfully created instance of {module_class.__name__}")
            return instance
            
        except Exception as e:
            raise ModuleLoadError(
                module_class.__name__,
                module_class.__module__,
                f"Failed to create instance: {str(e)}"
            ) from e
    
    def clear_cache(self):
        """清空模块缓存"""
        self._loaded_modules.clear()
        self.logger.debug("Module cache cleared")


def dynamic_import_module(module_name: str, module_path: str, logger: Logger, *args, **kwargs) -> Any:
    """
    动态导入并实例化模块的便捷函数
    
    Args:
        module_name: 模块类名
        module_path: 模块导入路径
        logger: 日志记录器
        *args: 传递给模块构造函数的位置参数
        **kwargs: 传递给模块构造函数的关键字参数
        
    Returns:
        模块实例
        
    Raises:
        ModuleLoadError: 当模块加载或实例化失败时
    """
    loader = ModuleLoader(logger)
    module_class = loader.load_module(module_name, module_path)
    return loader.create_instance(module_class, *args, **kwargs)
