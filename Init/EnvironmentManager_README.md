# EnvironmentManager - 环境管理器

## 概述

EnvironmentManager 是Agent框架的环境管理系统，负责系统环境的检查、配置和管理，确保Agent在正确的环境中运行。该模块提供全面的环境验证、资源检查、目录管理和用户环境配置功能。

## 版本信息

- **版本**: 2.0
- **作者**: yomu
- **Python版本**: 3.8+

## 主要功能

### 1. 环境变量管理
- 必需环境变量检查和设置
- 动态环境变量配置
- 环境变量验证和修复

### 2. 系统依赖验证
- Python版本和包依赖检查
- 系统工具可用性验证
- 第三方服务连接测试

### 3. 目录结构管理
- 必需目录自动创建
- 目录权限检查
- 存储空间验证

### 4. 资源可用性检查
- 内存和CPU使用率监控
- 磁盘空间检查
- 网络连接验证

### 5. 用户环境管理
- 用户权限验证
- 个人配置管理
- 多用户环境支持

## 环境级别

系统支持三种环境级别：

```python
from Init.EnvironmentManager import EnvironmentLevel

# 开发环境
EnvironmentLevel.DEVELOPMENT

# 测试环境  
EnvironmentLevel.TESTING

# 生产环境
EnvironmentLevel.PRODUCTION
```

## 快速开始

### 1. 基本使用

```python
from Init.EnvironmentManager import EnvironmentManager, EnvironmentLevel

# 创建环境管理器实例
env_manager = EnvironmentManager(
    base_path="/home/yomu/agent",
    env_level=EnvironmentLevel.DEVELOPMENT
)

# 检查所有环境要求
results = env_manager.check_all_requirements()

# 打印检查结果
for result in results:
    if result.success:
        print(f"✓ {result.category}: {result.message}")
    else:
        print(f"✗ {result.category}: {result.message}")
        if result.suggestions:
            for suggestion in result.suggestions:
                print(f"  建议: {suggestion}")
```

### 2. 环境初始化

```python
# 完整环境初始化
success = env_manager.initialize_environment()

if success:
    print("环境初始化成功")
else:
    print("环境初始化失败，请检查错误日志")

# 获取初始化报告
report = env_manager.get_initialization_report()
print(f"成功项目: {len(report['successful'])}")
print(f"失败项目: {len(report['failed'])}")
```

### 3. 分类检查

```python
# 检查环境变量
env_results = env_manager.check_environment_variables()

# 检查系统依赖
dep_results = env_manager.check_system_dependencies()

# 检查目录结构
dir_results = env_manager.check_directory_structure()

# 检查资源可用性
resource_results = env_manager.check_resource_availability()

# 检查配置文件
config_results = env_manager.check_configuration_files()
```

## 环境要求

### 1. 必需环境变量

```bash
# 设置Python路径
export PYTHONPATH=/home/yomu/agent:$PYTHONPATH

# 设置Agent主目录
export AGENT_HOME=/home/yomu/agent

# 设置环境级别
export AGENT_ENV=development
```

### 2. 必需目录结构

```
agent/
├── Log/                     # 日志目录
│   ├── ExternalService/     # 外部服务日志
│   ├── InternalModule/      # 内部模块日志
│   ├── Other/               # 其他日志
│   └── Test/                # 测试日志
├── Config/                  # 配置目录
├── Data/                    # 数据目录
├── Resources/               # 资源目录
├── Users/                   # 用户目录
│   ├── Config/              # 用户配置
│   └── Files/               # 用户文件
└── Temp/                    # 临时目录
```

### 3. 系统依赖

```python
# Python包依赖
required_packages = [
    "yaml",
    "requests", 
    "pathlib",
    "logging",
    "psutil"  # 可选，用于资源监控
]

# 系统工具依赖
system_tools = [
    "python3",
    "pip",
    "git"
]
```

## 用户环境管理

### 1. 用户环境信息

```python
from Init.EnvironmentManager import UserEnvironment

# 创建用户环境
user_env = UserEnvironment(
    username="agent_user",
    user_id="1001",
    home_directory="/home/agent_user",
    preferences={
        "language": "zh-cn",
        "theme": "dark",
        "log_level": "INFO"
    },
    permissions=["read", "write", "execute"]
)

# 设置用户环境
env_manager.set_user_environment(user_env)
```

### 2. 用户配置管理

```python
# 加载用户配置
user_config = env_manager.load_user_config("agent_user")

# 更新用户配置
env_manager.update_user_config("agent_user", {
    "new_setting": "value"
})

# 保存用户配置
env_manager.save_user_config("agent_user", user_config)
```

## 高级功能

### 1. 环境诊断

```python
# 生成详细诊断报告
diagnosis = env_manager.diagnose_environment()

print(f"诊断结果: {diagnosis['status']}")
print(f"问题数量: {len(diagnosis['issues'])}")
print(f"警告数量: {len(diagnosis['warnings'])}")

# 自动修复问题
fixed_issues = env_manager.auto_fix_issues(diagnosis['issues'])
print(f"已修复问题: {len(fixed_issues)}")
```

### 2. 资源监控

```python
# 获取系统资源使用情况
resources = env_manager.get_resource_usage()

print(f"内存使用率: {resources['memory_percent']}%")
print(f"CPU使用率: {resources['cpu_percent']}%")
print(f"磁盘使用率: {resources['disk_percent']}%")

# 设置资源阈值监控
env_manager.set_resource_thresholds({
    "memory_threshold": 80,  # 内存使用率阈值
    "cpu_threshold": 75,     # CPU使用率阈值
    "disk_threshold": 90     # 磁盘使用率阈值
})
```

### 3. 环境备份和恢复

```python
# 备份当前环境配置
backup_path = env_manager.backup_environment("/path/to/backup")

# 恢复环境配置
success = env_manager.restore_environment("/path/to/backup")

# 导出环境配置
config_export = env_manager.export_environment_config()

# 导入环境配置
env_manager.import_environment_config(config_export)
```

### 4. 环境变化监控

```python
# 启动环境监控
env_manager.start_monitoring()

# 注册变化回调
def on_environment_change(change_type, details):
    print(f"环境变化: {change_type}, 详情: {details}")

env_manager.register_change_callback(on_environment_change)

# 停止监控
env_manager.stop_monitoring()
```

## 配置选项

### 1. 基础配置

```python
# 自定义配置
custom_config = {
    "required_env_vars": {
        "CUSTOM_VAR": "custom_value"
    },
    "required_directories": [
        "custom_dir1",
        "custom_dir2"
    ],
    "required_packages": [
        "custom_package"
    ],
    "system_tools": [
        "custom_tool"
    ]
}

env_manager.update_configuration(custom_config)
```

### 2. 环境级别配置

```python
# 不同环境级别的配置
level_configs = {
    EnvironmentLevel.DEVELOPMENT: {
        "debug": True,
        "log_level": "DEBUG",
        "strict_checks": False
    },
    EnvironmentLevel.TESTING: {
        "debug": True,
        "log_level": "INFO", 
        "strict_checks": True
    },
    EnvironmentLevel.PRODUCTION: {
        "debug": False,
        "log_level": "WARNING",
        "strict_checks": True
    }
}
```

## 故障排除

### 常见问题

1. **环境变量未设置**
   ```bash
   # 解决方案：设置必需的环境变量
   export PYTHONPATH=/home/yomu/agent:$PYTHONPATH
   export AGENT_HOME=/home/yomu/agent
   ```

2. **目录权限不足**
   ```bash
   # 解决方案：修改目录权限
   chmod -R 755 /home/yomu/agent
   chown -R $USER:$USER /home/yomu/agent
   ```

3. **包依赖缺失**
   ```bash
   # 解决方案：安装缺失的包
   pip install -r requirements.txt
   ```

4. **资源不足**
   - 释放内存空间
   - 清理临时文件
   - 关闭不必要的进程

### 调试工具

```python
# 启用详细日志
env_manager.set_log_level("DEBUG")

# 生成诊断报告
diagnosis = env_manager.diagnose_environment()

# 检查特定组件
component_status = env_manager.check_component_status("directories")

# 验证修复结果
verification = env_manager.verify_environment_integrity()
```

## 性能优化

### 1. 检查优化
- 并行执行独立检查
- 缓存检查结果
- 跳过重复验证

### 2. 资源监控优化
- 异步资源监控
- 采样间隔优化
- 历史数据压缩

### 3. 日志优化
- 分级日志记录
- 日志轮转配置
- 异步日志写入

## API参考

### 主要方法

```python
class EnvironmentManager:
    def __init__(self, base_path: str, env_level: EnvironmentLevel)
    def check_all_requirements(self) -> List[EnvironmentCheckResult]
    def initialize_environment(self) -> bool
    def check_environment_variables(self) -> List[EnvironmentCheckResult]
    def check_system_dependencies(self) -> List[EnvironmentCheckResult]
    def check_directory_structure(self) -> List[EnvironmentCheckResult]
    def check_resource_availability(self) -> List[EnvironmentCheckResult]
    def set_user_environment(self, user_env: UserEnvironment) -> bool
    def diagnose_environment(self) -> Dict[str, Any]
    def get_resource_usage(self) -> Dict[str, float]
    def backup_environment(self, backup_path: str) -> str
```

## 相关文档

- [环境设置指南](ENVIRONMENT_GUIDE.md)
- [快速开始指南](QUICKSTART.md)
- [故障排除指南](TROUBLESHOOTING.md)
- [API参考文档](API_REFERENCE.md)

## 联系方式

如有问题或建议，请联系：
- 作者: yomu
- 项目地址: Agent框架
