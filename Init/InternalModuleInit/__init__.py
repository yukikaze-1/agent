"""
InternalModuleInit - 重构版内部模块管理器

这是一个重构后的内部模块管理系统，提供以下改进：

1. 模块化设计：将功能拆分为独立的模块
2. 完善的错误处理：定义了专门的异常类
3. 配置验证：自动验证模块配置的正确性
4. 线程安全：支持多线程环境下的模块管理
5. 动态加载：支持动态加载和卸载模块
6. 类型检查：完善的类型注解和验证

支持的内部模块类型：
- LLM模块：ollama agent (使用Langchain的ChatOllama)
- TTS模块：GPTSoVits agent, CosyVoice agent
- STT模块：SenseVoice agent
- 其他功能模块

使用示例：
    from Init.InternalModuleInit import InternalModuleManager
    
    manager = InternalModuleManager()
    success, base_success, base_fail, opt_success, opt_fail = manager.init_modules()
    
    # 列出运行中的模块
    running_modules = manager.list_started_modules()
    
    # 停止可选模块
    manager.stop_optional_modules()
    
    # 重启指定模块
    manager.restart_single_module("GPTSoVitsAgent")

运行前请设置环境变量：
    export PYTHONPATH=/home/yomu/agent:$PYTHONPATH
"""

from .core import InternalModuleManager
from .exceptions import (
    ModuleError,
    ModuleStartupError,
    ModuleLoadError,
    ModuleConfigError,
    ModuleStopError,
    ModuleNotFoundError,
    ModuleDependencyError
)

__version__ = "2.0.0"
__author__ = "yomu"

__all__ = [
    'InternalModuleManager',
    'ModuleError',
    'ModuleStartupError',
    'ModuleLoadError',
    'ModuleConfigError',
    'ModuleStopError',
    'ModuleNotFoundError',
    'ModuleDependencyError'
]
