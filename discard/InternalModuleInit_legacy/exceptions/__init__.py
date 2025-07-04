"""
内部模块管理的异常类定义

定义了内部模块管理过程中可能出现的各种异常类型，
提供更精确的错误处理和调试信息。
"""

from typing import Optional, Any


class ModuleError(Exception):
    """内部模块管理的基础异常类"""
    
    def __init__(self, message: str, module_name: Optional[str] = None, 
                 error_code: Optional[str] = None, details: Optional[Any] = None):
        self.message = message
        self.module_name = module_name
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)
    
    def __str__(self):
        parts = [self.message]
        if self.module_name:
            parts.append(f"Module: {self.module_name}")
        if self.error_code:
            parts.append(f"Error Code: {self.error_code}")
        if self.details:
            parts.append(f"Details: {self.details}")
        return " | ".join(parts)


class ModuleStartupError(ModuleError):
    """模块启动失败异常"""
    
    def __init__(self, module_name: str, reason: str, details: Optional[Any] = None):
        super().__init__(
            f"Failed to start module '{module_name}': {reason}",
            module_name=module_name,
            error_code="MODULE_STARTUP_FAILED",
            details=details
        )


class ModuleLoadError(ModuleError):
    """模块加载失败异常"""
    
    def __init__(self, module_name: str, module_path: str, reason: str):
        super().__init__(
            f"Failed to load module '{module_name}' from '{module_path}': {reason}",
            module_name=module_name,
            error_code="MODULE_LOAD_FAILED",
            details={"module_path": module_path, "reason": reason}
        )


class ModuleConfigError(ModuleError):
    """模块配置错误异常"""
    
    def __init__(self, config_issue: str, module_name: Optional[str] = None, 
                 config_path: Optional[str] = None):
        super().__init__(
            f"Module configuration error: {config_issue}",
            module_name=module_name,
            error_code="MODULE_CONFIG_ERROR",
            details={"config_path": config_path}
        )


class ModuleStopError(ModuleError):
    """模块停止失败异常"""
    
    def __init__(self, module_name: str, reason: str):
        super().__init__(
            f"Failed to stop module '{module_name}': {reason}",
            module_name=module_name,
            error_code="MODULE_STOP_FAILED",
            details={"reason": reason}
        )


class ModuleNotFoundError(ModuleError):
    """模块未找到异常"""
    
    def __init__(self, module_name: str, context: str = ""):
        super().__init__(
            f"Module '{module_name}' not found" + (f" in {context}" if context else ""),
            module_name=module_name,
            error_code="MODULE_NOT_FOUND",
            details={"context": context}
        )


class ModuleDependencyError(ModuleError):
    """模块依赖错误异常"""
    
    def __init__(self, module_name: str, dependency: str, reason: str):
        super().__init__(
            f"Module '{module_name}' dependency error with '{dependency}': {reason}",
            module_name=module_name,
            error_code="MODULE_DEPENDENCY_ERROR",
            details={"dependency": dependency, "reason": reason}
        )
