# Agent 系统工具目录

这个目录包含了 Agent 系统开发和维护过程中使用的各种工具。

## 📁 目录结构

### `Environment/`
环境管理和验证工具
- **用途**: 确保系统在不同环境下的兼容性
- **工具**: 环境验证、路径修复、跨平台兼容性检查等
- **详情**: 查看 [`Environment/README.md`](Environment/README.md)

### `Development/`
开发辅助工具
- **用途**: 开发过程中使用的各种实用工具
- **工具**: 日志清理、包配置、早期函数定义等
- **详情**: 查看 [`Development/README.md`](Development/README.md)

## 🚀 快速使用

### 环境验证
```bash
# 快速验证当前环境
python Tools/Environment/quick_verify.py

# 完整环境测试
python Tools/Environment/test_full_environment.py

# 跨平台兼容性检查
python Tools/Environment/check_cross_platform_compatibility.py
```

### 开发工具
```bash
# 清理日志文件
python Tools/Development/rmlog.py
```

## 📋 使用建议

### 对于新开发者
1. 首先运行环境验证工具确保环境正确
2. 参考 Development 目录了解历史开发过程
3. 使用工具前请阅读相应的 README 文档

### 对于维护者
1. 定期运行环境验证工具检查系统状态
2. 新工具请添加到相应的子目录
3. 保持工具文档的更新

## 💡 工具开发指南

添加新工具时请遵循以下规范：
1. 选择合适的子目录（Environment/Development等）
2. 添加清晰的文档说明
3. 包含使用示例和注意事项
4. 更新相应目录的 README

## 🔧 维护说明

- 定期清理过时的工具
- 保持工具的功能性和兼容性
- 及时更新文档和使用说明
