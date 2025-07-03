# Agent 系统启动指南

## 📚 概述

本文档介绍了 Agent 系统的新启动方式。从 v0.2 版本开始，`agent_v0.1.py` 成为了系统的唯一主入口，自动管理环境变量，无需手动设置 `PYTHONPATH`。

## 🚀 快速开始

### 方式一：直接运行 Python 脚本

```bash
# 开发模式启动（默认）
python agent_v0.1.py

# 生产模式启动
python agent_v0.1.py --env production

# 后台模式启动
python agent_v0.1.py --daemon

# 仅环境检查
python agent_v0.1.py --check-only
```

### 方式二：使用启动脚本（推荐）

#### Linux/macOS
```bash
# 使用完整脚本
./start_agent.sh start              # 开发模式启动
./start_agent.sh start --daemon     # 后台模式启动
./start_agent.sh check              # 环境检查
./start_agent.sh status             # 查看状态
./start_agent.sh stop               # 停止系统

# 使用快速脚本
./agent.sh start                    # 开发模式启动
./agent.sh start --env production   # 生产模式启动
```

#### Windows
```cmd
REM 使用 Windows 脚本
start_agent.bat start              REM 开发模式启动
start_agent.bat check              REM 环境检查
start_agent.bat help               REM 显示帮助
```

## 🔧 重要修复说明

### 环境变量传递修复 (v0.2.1)

我们已经修复了一个重要问题：确保通过 `subprocess.Popen` 启动的 Service（如 FastAPI 服务）能够正确访问环境变量和导入项目模块。

**修复内容：**
- ✅ 修复了 `ProcessManager` 中 `subprocess.Popen` 不传递环境变量的问题
- ✅ 确保所有子进程都能访问 `PYTHONPATH`、`AGENT_HOME` 等关键环境变量  
- ✅ 现在 Service 下的 FastAPI 服务可以正常使用 `from Module.Utils.xxx import xxx`
- ✅ 添加了完整的环境变量验证和测试机制

**影响的组件：**
- Service/UserService
- Service/MySQLService
- 其他通过 ExternalServiceInit 启动的服务

## 🔧 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--env` | 运行环境模式 | `--env production` |
| `--daemon` | 后台守护进程模式 | `--daemon` |
| `--check-only` | 仅执行环境检查 | `--check-only` |
| `--config` | 指定配置文件 | `--config custom.yml` |
| `--log-level` | 日志级别 | `--log-level DEBUG` |
| `--port` | 指定主服务端口 | `--port 8080` |
| `--no-health-check` | 跳过健康检查 | `--no-health-check` |

## 🌍 环境配置

### 环境级别

- **development**: 开发环境（默认）
- **testing**: 测试环境  
- **production**: 生产环境

### 配置文件优先级

1. `.env.{environment}` - 环境特定配置（最高优先级）
2. `.env` - 主配置文件
3. `.env.global` - 全局默认配置（最低优先级）

### 环境变量

系统会自动设置以下环境变量：

```bash
AGENT_HOME=/home/yomu/agent           # 项目根目录
PYTHONPATH=/home/yomu/agent          # Python 路径
AGENT_ENV=development                # 当前环境
```

## 🔍 交互式命令

启动后，系统提供交互式命令界面：

```
Agent> status      # 查看系统状态
Agent> health      # 执行健康检查  
Agent> help        # 显示帮助
Agent> quit        # 退出系统
```

## 📊 后台模式

### 启动后台服务

```bash
# Linux/macOS
./start_agent.sh start --daemon
python agent_v0.1.py --daemon

# 查看状态
./start_agent.sh status

# 停止服务
./start_agent.sh stop
```

### 日志查看

```bash
# 查看实时日志
tail -f Log/agent.log

# 查看错误日志
tail -f Log/ExternalService/*.log
tail -f Log/InternalModule/*.log
```

## 🛠️ 故障排除

### 常见问题

1. **权限错误**
   ```bash
   chmod +x start_agent.sh agent.sh
   ```

2. **Python 版本不兼容**
   - 确保 Python >= 3.8
   ```bash
   python --version
   ```

3. **环境变量未生效**
   ```bash
   # 检查环境
   python agent_v0.1.py --check-only
   ```

4. **端口占用**
   ```bash
   # 查看端口使用
   netstat -tlnp | grep 8080
   ```

### 环境检查

```bash
# 执行完整环境检查
python agent_v0.1.py --check-only

# 或使用脚本
./start_agent.sh check

# 快速验证（新增）
python quick_verify.py
```

### 验证 Service 模块导入

```bash
# 验证环境变量传递是否正常
python test_full_environment.py

# 测试特定模块导入
python test_environment.py
```

## 📁 目录结构

```
/home/yomu/agent/
├── agent_v0.1.py          # 主入口文件
├── start_agent.sh         # Linux/macOS 启动脚本
├── start_agent.bat        # Windows 启动脚本  
├── agent.sh              # 快速启动脚本
├── .env                  # 主配置文件
├── .env.global           # 全局配置
├── .env.development      # 开发环境配置
├── .env.production       # 生产环境配置
├── .agent.pid            # 后台进程 PID 文件
└── Log/
    ├── agent.log         # 主日志文件
    ├── ExternalService/  # 外部服务日志
    └── InternalModule/   # 内部模块日志
```

## 🚀 迁移指南

### 从旧版本迁移

如果您之前使用手动设置环境变量的方式：

```bash
# 旧方式（不再需要）
export PYTHONPATH=/home/yomu/agent:$PYTHONPATH
python your_script.py

# 新方式
./agent.sh start
# 或
python agent_v0.1.py
```

### 自动化部署

```bash
# 部署脚本示例
#!/bin/bash
cd /home/yomu/agent
git pull
./start_agent.sh stop
./start_agent.sh start --env production --daemon
```

## 📞 支持

如果遇到问题：

1. 查看日志文件：`Log/agent.log`
2. 执行环境检查：`python agent_v0.1.py --check-only`
3. 查看系统状态：`./start_agent.sh status`

---

**注意**: 从 v0.2 版本开始，无需手动设置 `PYTHONPATH` 环境变量，系统会自动处理所有环境配置。
