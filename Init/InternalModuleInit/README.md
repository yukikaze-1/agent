# InternalModuleInit - 内部模块管理器

## 概述

InternalModuleInit 是Agent框架的内部模块管理系统，负责管理和协调各种AI功能模块的启动、运行和停止。该模块采用重构后的架构，提供更好的模块化设计、线程安全、动态加载等特性。

## 版本信息

- **版本**: 2.0.0
- **作者**: yomu
- **Python版本**: 3.8+

## 主要功能

### 1. 模块化管理
- LLM模块：Ollama Agent (基于Langchain的ChatOllama)
- TTS模块：GPTSoVits Agent, CosyVoice Agent
- STT模块：SenseVoice Agent
- 自定义功能模块支持

### 2. 动态加载
- 运行时模块加载和卸载
- 热重载支持
- 依赖关系自动解析

### 3. 线程安全
- 多线程环境下的安全操作
- 锁机制保护关键资源
- 并发模块管理

### 4. 健康监控
- 模块状态实时监控
- 异常检测和自动恢复
- 性能指标收集

### 5. 配置管理
- 模块配置验证
- 动态配置更新
- 环境变量支持

## 目录结构

```
InternalModuleInit/
├── __init__.py              # 模块入口，导出主要类和异常
├── config.yml               # 模块配置文件
├── demo.py                  # 使用演示脚本
├── debug_config.py          # 配置调试工具
├── validate_config.py       # 配置验证工具
├── core/                    # 核心模块
│   ├── __init__.py
│   └── module_manager.py    # 模块管理器核心实现
├── exceptions/              # 异常定义
│   ├── __init__.py
│   └── module_exceptions.py
└── utils/                   # 工具模块
    ├── __init__.py
    ├── config_validator.py  # 配置验证器
    ├── module_loader.py     # 模块加载器
    ├── health_checker.py    # 健康检查器
    └── dependency_resolver.py # 依赖解析器
```

## 环境要求

在使用前，请确保设置正确的环境变量：

```bash
export PYTHONPATH=/home/yomu/agent:$PYTHONPATH
```

## 快速开始

### 1. 基本使用

```python
from Init.InternalModuleInit import InternalModuleManager

# 创建模块管理器实例
manager = InternalModuleManager()

# 初始化所有模块
success, base_success, base_fail, opt_success, opt_fail = manager.init_modules()

print(f"总体成功: {success}")
print(f"基础模块 - 成功: {base_success}, 失败: {base_fail}")
print(f"可选模块 - 成功: {opt_success}, 失败: {opt_fail}")

# 列出运行中的模块
running_modules = manager.list_started_modules()
print(f"运行中的模块: {running_modules}")
```

### 2. 单独管理模块

```python
# 启动指定模块
success = manager.start_single_module("GPTSoVitsAgent")

# 停止指定模块
manager.stop_single_module("GPTSoVitsAgent")

# 重启指定模块
success = manager.restart_single_module("GPTSoVitsAgent")

# 检查模块状态
is_running = manager.is_module_running("GPTSoVitsAgent")
```

### 3. 批量操作

```python
# 启动所有基础模块
base_success, base_failed = manager.start_base_modules()

# 启动所有可选模块
opt_success, opt_failed = manager.start_optional_modules()

# 停止所有可选模块
manager.stop_optional_modules()

# 停止所有模块
manager.stop_all_modules()
```

## 配置文件

### config.yml 示例

```yaml
internal_modules:
  support_modules:
    - "OllamaAgent"
    - "GPTSoVitsAgent"
    - "CosyVoiceAgent"
    - "SenseVoiceAgent"
  
  base_modules:
    - name: "OllamaAgent"
      module_path: "Module.LLM.OllamaAgent"
      class_name: "OllamaAgent"
      config:
        model: "llama2"
        temperature: 0.7
      dependencies: []
      startup_timeout: 30
      
  optional_modules:
    - name: "GPTSoVitsAgent"
      module_path: "Module.TTS.GPTSoVitsAgent"
      class_name: "GPTSoVitsAgent"
      config:
        voice_model: "default"
      dependencies: ["OllamaAgent"]
      startup_timeout: 45

settings:
  default_timeout: 30
  max_startup_attempts: 3
  health_check_interval: 10
  enable_hot_reload: true
```

## 支持的模块类型

### 1. LLM模块
- **OllamaAgent**: 基于Langchain ChatOllama的语言模型代理
- 支持多种大语言模型
- 自动模型管理和优化

### 2. TTS模块
- **GPTSoVitsAgent**: GPT-SoVITS语音合成代理
- **CosyVoiceAgent**: CosyVoice语音合成代理
- 支持多音色和语言

### 3. STT模块
- **SenseVoiceAgent**: SenseVoice语音识别代理
- 高精度语音转文字
- 支持多语言识别

## 异常处理

完整的异常层次结构：

```python
from Init.InternalModuleInit import (
    ModuleError,            # 基础模块异常
    ModuleStartupError,     # 模块启动失败
    ModuleLoadError,        # 模块加载失败
    ModuleConfigError,      # 配置错误
    ModuleStopError,        # 模块停止失败
    ModuleNotFoundError,    # 模块未找到
    ModuleDependencyError   # 依赖错误
)

try:
    manager.start_single_module("GPTSoVitsAgent")
except ModuleStartupError as e:
    print(f"模块启动失败: {e}")
except ModuleDependencyError as e:
    print(f"依赖错误: {e}")
except ModuleConfigError as e:
    print(f"配置错误: {e}")
```

## 高级功能

### 1. 依赖管理

```python
# 检查模块依赖
dependencies = manager.get_module_dependencies("GPTSoVitsAgent")

# 解析启动顺序
startup_order = manager.resolve_startup_order()

# 检查依赖冲突
conflicts = manager.check_dependency_conflicts()
```

### 2. 健康监控

```python
# 检查所有模块健康状态
health_status = manager.check_all_modules_health()

# 检查单个模块
is_healthy = manager.check_module_health("OllamaAgent")

# 获取模块性能指标
metrics = manager.get_module_metrics("GPTSoVitsAgent")
```

### 3. 动态配置

```python
# 更新模块配置
new_config = {"temperature": 0.8}
manager.update_module_config("OllamaAgent", new_config)

# 重载配置
manager.reload_config()

# 热重载模块
manager.hot_reload_module("GPTSoVitsAgent")
```

### 4. 事件监听

```python
# 注册模块事件监听器
def on_module_started(module_name):
    print(f"模块 {module_name} 已启动")

manager.register_event_listener("module_started", on_module_started)
```

## 开发指南

### 1. 创建新模块

```python
from Module.Base import BaseAgent

class CustomAgent(BaseAgent):
    def __init__(self, config):
        super().__init__(config)
        # 初始化逻辑
    
    def start(self):
        # 启动逻辑
        pass
    
    def stop(self):
        # 停止逻辑
        pass
    
    def health_check(self):
        # 健康检查逻辑
        return True
```

### 2. 配置新模块

在 `config.yml` 中添加模块配置：

```yaml
internal_modules:
  support_modules:
    - "CustomAgent"
  
  optional_modules:
    - name: "CustomAgent"
      module_path: "Module.Custom.CustomAgent"
      class_name: "CustomAgent"
      config:
        custom_param: "value"
      dependencies: []
      startup_timeout: 30
```

## 故障排除

### 常见问题

1. **模块导入失败**
   - 检查 PYTHONPATH 环境变量
   - 验证模块路径是否正确
   - 确认依赖包已安装

2. **模块启动超时**
   - 增加 startup_timeout 设置
   - 检查模块初始化逻辑
   - 查看详细错误日志

3. **依赖冲突**
   - 使用依赖解析器检查冲突
   - 调整模块启动顺序
   - 解决循环依赖问题

### 调试工具

```bash
# 验证配置文件
python validate_config.py

# 调试配置
python debug_config.py

# 运行演示
python demo.py

# 检查模块状态
python -c "
from Init.InternalModuleInit import InternalModuleManager
manager = InternalModuleManager()
print(manager.list_started_modules())
"
```

## 性能优化

### 1. 内存管理
- 定期清理未使用的模块
- 优化模块加载策略
- 监控内存使用情况

### 2. 启动优化
- 并行启动独立模块
- 延迟加载可选模块
- 缓存模块实例

### 3. 监控和日志
- 使用异步日志记录
- 实时性能指标收集
- 异常趋势分析

## 相关文档

- [模块迁移指南](MIGRATION_GUIDE.md)
- [环境设置指南](../ENVIRONMENT_GUIDE.md)
- [故障排除指南](../TROUBLESHOOTING.md)
- [快速开始指南](../QUICKSTART.md)

## 联系方式

如有问题或建议，请联系：
- 作者: yomu
- 项目地址: Agent框架
