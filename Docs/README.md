# Agent 系统文档

这个目录包含了 Agent 系统的所有文档和指南。

## 📚 文档列表

### 用户指南
- `STARTUP_GUIDE.md` - 系统启动指南，包含详细的启动方法和参数说明
- `CROSS_PLATFORM_DEPLOY_GUIDE.md` - 跨平台部署指南，确保在不同操作系统上的兼容性

### 技术报告
- `COMPATIBILITY_REPORT.md` - 兼容性验证报告，由自动化工具生成

### 参考资料
- `Reference/` - 硬件规格、模型性能等参考文档
- `study/` - 开发过程中的学习文档和技术研究

### 备份文件
- `Backup/` - 包含各种配置文件和文档的备份版本

## 🔗 快速导航

### 对于新用户
1. 首先阅读 [`STARTUP_GUIDE.md`](STARTUP_GUIDE.md) 了解如何启动系统
2. 如果遇到跨平台问题，参考 [`CROSS_PLATFORM_DEPLOY_GUIDE.md`](CROSS_PLATFORM_DEPLOY_GUIDE.md)

### 对于开发者
1. 查看 [`COMPATIBILITY_REPORT.md`](COMPATIBILITY_REPORT.md) 了解系统兼容性状态
2. 使用 `../Tools/Environment/` 中的工具进行环境验证

## 📋 文档维护

- 文档会随着系统更新而更新
- 自动生成的报告会定期刷新
- 备份文件保留历史版本以供参考

## 💡 帮助

如果在使用过程中遇到问题：
1. 首先查看相应的文档
2. 运行环境验证工具：`python Tools/Environment/quick_verify.py`
3. 查看兼容性报告中的故障排除部分
