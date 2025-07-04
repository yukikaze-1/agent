# ExternalServiceInit - 外部服务管理器

## 概述

ExternalServiceInit 是一个重构后的外部服务管理系统，为Agent框架提供统一的外部服务启动、监控和管理功能。该模块采用模块化设计，提供完善的错误处理、健康检查、重试机制等功能。

## 版本信息

- **版本**: 2.0.0
- **作者**: yomu
- **Python版本**: 3.8+

## 主要功能

### 1. 模块化设计
- 核心功能分离为独立模块
- 清晰的代码组织结构
- 易于维护和扩展

### 2. 服务管理
- 外部服务进程启动和停止
- 基础服务和可选服务分类管理
- 自动服务依赖解析

### 3. 健康检查
- HTTP健康检查机制
- 实时服务状态监控
- 异常服务自动检测

### 4. 错误处理
- 专门的异常类定义
- 完善的错误恢复机制
- 详细的错误日志记录

### 5. 重试机制
- 指数退避算法
- 可配置重试次数和间隔
- 智能故障恢复

## 目录结构

```
ExternalServiceInit/
├── __init__.py              # 模块入口，导出主要类和异常
├── config.yml               # 服务配置文件
├── demo.py                  # 使用演示脚本
├── validate_config.py       # 配置验证工具
├── core/                    # 核心模块
│   ├── __init__.py
│   └── service_manager.py   # 服务管理器核心实现
├── exceptions/              # 异常定义
│   ├── __init__.py
│   └── service_exceptions.py
└── utils/                   # 工具模块
    ├── __init__.py
    ├── config_validator.py  # 配置验证器
    ├── health_checker.py    # 健康检查器
    ├── process_manager.py   # 进程管理器
    └── retry_manager.py     # 重试管理器
```

## 快速开始

### 1. 基本使用

```python
from Init.ExternalServiceInit import ExternalServiceManager

# 创建服务管理器实例
manager = ExternalServiceManager()

# 初始化并启动所有服务
base_services, optional_services = manager.init_services()

# 检查服务状态
status = manager.get_service_status()
print(f"运行中的基础服务: {len(status.get('base', []))}")
print(f"运行中的可选服务: {len(status.get('optional', []))}")

# 停止所有服务
manager.stop_all_services()
```

### 2. 单独管理服务

```python
# 启动基础服务
base_success, base_failed = manager.start_base_services()

# 启动可选服务
opt_success, opt_failed = manager.start_optional_services()

# 停止指定服务
manager.stop_service("service_name")

# 重启服务
manager.restart_service("service_name")
```

### 3. 健康检查

```python
# 检查所有服务健康状态
health_status = manager.check_all_services_health()

# 检查单个服务
is_healthy = manager.check_service_health("service_name")
```

## 配置文件

### config.yml 示例

```yaml
external_services:
  base_services:
    - name: "essential_service"
      command: "python service.py"
      port: 8000
      health_check_url: "http://localhost:8000/health"
      startup_timeout: 30
      retry_attempts: 3
      
  optional_services:
    - name: "optional_feature"
      command: "python feature.py"
      port: 8001
      health_check_url: "http://localhost:8001/health"
      startup_timeout: 20
      retry_attempts: 2

settings:
  default_timeout: 30
  max_retry_attempts: 3
  retry_backoff_factor: 2
  health_check_interval: 5
```

## 异常处理

模块定义了完整的异常层次结构：

```python
from Init.ExternalServiceInit import (
    ServiceError,           # 基础异常
    ServiceStartupError,    # 启动失败
    ServiceHealthCheckError,# 健康检查失败
    ServiceConfigError,     # 配置错误
    ServiceStopError,       # 停止失败
    ServiceNotFoundError    # 服务未找到
)

try:
    manager.start_service("my_service")
except ServiceStartupError as e:
    print(f"服务启动失败: {e}")
    # 处理启动失败逻辑
except ServiceConfigError as e:
    print(f"配置错误: {e}")
    # 处理配置错误逻辑
```

## 高级功能

### 1. 自定义健康检查

```python
# 自定义健康检查函数
def custom_health_check(service_config):
    # 实现自定义检查逻辑
    return True

manager.health_checker.register_custom_check("service_name", custom_health_check)
```

### 2. 服务依赖管理

```python
# 设置服务依赖关系
manager.set_service_dependencies({
    "dependent_service": ["required_service1", "required_service2"]
})
```

### 3. 监控和日志

- 所有操作都会记录详细日志
- 日志文件位于 `Log/ExternalService/` 目录
- 支持不同级别的日志输出

## 故障排除

### 常见问题

1. **服务启动失败**
   - 检查配置文件语法
   - 验证端口是否被占用
   - 确认服务可执行文件路径

2. **健康检查失败**
   - 验证健康检查URL是否正确
   - 检查服务是否正常响应
   - 确认网络连接状态

3. **配置错误**
   - 使用 `validate_config.py` 验证配置
   - 检查必需字段是否完整
   - 确认数据类型正确

### 调试工具

```bash
# 验证配置文件
python validate_config.py

# 运行演示
python demo.py

# 检查服务状态
python -c "from Init.ExternalServiceInit import ExternalServiceManager; print(ExternalServiceManager().get_service_status())"
```

## 开发和维护

### 扩展新功能

1. 在 `utils/` 目录添加新的工具模块
2. 在 `exceptions/` 目录定义相关异常
3. 更新 `__init__.py` 导出新的类和函数
4. 编写相应的测试用例

### 贡献指南

1. 遵循现有的代码风格
2. 添加完整的类型注解
3. 编写详细的文档字符串
4. 包含适当的错误处理
5. 添加相应的测试用例

## 相关文档

- [模块迁移指南](MIGRATION_GUIDE.md)
- [配置分离报告](CONFIG_SEPARATION_REPORT.md)
- [完成情况报告](COMPLETION_REPORT.md)
- [故障排除指南](../TROUBLESHOOTING.md)

## 联系方式

如有问题或建议，请联系：
- 作者: yomu
- 项目地址: Agent框架
