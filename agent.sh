#!/bin/bash
# 快速启动 Agent 系统

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 直接调用完整的启动脚本
exec "$SCRIPT_DIR/start_agent.sh" "$@"
