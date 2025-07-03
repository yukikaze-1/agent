#!/bin/bash
# Project:      Agent
# Author:       yomu
# Time:         2025/01/06
# Version:      2.0
# Description:  Agent 系统启动脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本所在目录（Agent 项目根目录）
AGENT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_MAIN="$AGENT_ROOT/agent_v0.1.py"

# 检查 Python 是否安装
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 未安装，请先安装 Python3${NC}"
        exit 1
    fi
    
    # 检查 Python 版本
    python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    required_version="3.8"
    
    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        echo -e "${RED}❌ Python 版本过低: $python_version < $required_version${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Python 检查通过: $python_version${NC}"
}

# 设置环境变量
setup_environment() {
    export AGENT_HOME="$AGENT_ROOT"
    export PYTHONPATH="$AGENT_ROOT:$PYTHONPATH"
    export AGENT_ENV="${AGENT_ENV:-development}"
    
    echo -e "${GREEN}✅ 环境变量设置完成${NC}"
    echo -e "${BLUE}📁 AGENT_HOME: $AGENT_HOME${NC}"
    echo -e "${BLUE}🐍 PYTHONPATH: $PYTHONPATH${NC}"
    echo -e "${BLUE}🏷️  AGENT_ENV: $AGENT_ENV${NC}"
}

# 显示帮助信息
show_help() {
    echo -e "${BLUE}Agent 系统启动脚本${NC}"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  start                    启动 Agent 系统 (默认开发模式)"
    echo "  start --env production   启动 Agent 系统 (生产模式)"
    echo "  start --daemon           后台模式启动"
    echo "  check                    仅执行环境检查"
    echo "  stop                     停止 Agent 系统"
    echo "  restart                  重启 Agent 系统"
    echo "  status                   查看系统状态"
    echo "  help                     显示此帮助信息"
    echo ""
    echo "环境变量:"
    echo "  AGENT_ENV=production     设置运行环境"
    echo "  LOG_LEVEL=DEBUG          设置日志级别"
    echo ""
    echo "示例:"
    echo "  $0 start                 # 开发模式启动"
    echo "  $0 start --daemon        # 后台模式启动"
    echo "  AGENT_ENV=production $0 start  # 生产模式启动"
}

# 启动 Agent 系统
start_agent() {
    echo -e "${YELLOW}🚀 启动 Agent 系统...${NC}"
    
    # 检查是否已经在运行
    if [ -f "$AGENT_ROOT/.agent.pid" ]; then
        pid=$(cat "$AGENT_ROOT/.agent.pid")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  Agent 系统已在运行 (PID: $pid)${NC}"
            return 1
        else
            # 清理过期的 PID 文件
            rm -f "$AGENT_ROOT/.agent.pid"
        fi
    fi
    
    # 启动系统
    if [[ "$*" == *"--daemon"* ]]; then
        echo -e "${BLUE}🔧 以守护进程模式启动...${NC}"
        nohup python3 "$AGENT_MAIN" "$@" > "$AGENT_ROOT/Log/agent.log" 2>&1 &
        echo $! > "$AGENT_ROOT/.agent.pid"
        echo -e "${GREEN}✅ Agent 系统已在后台启动 (PID: $!)${NC}"
        echo -e "${BLUE}📄 日志文件: $AGENT_ROOT/Log/agent.log${NC}"
    else
        python3 "$AGENT_MAIN" "$@"
    fi
}

# 停止 Agent 系统
stop_agent() {
    echo -e "${YELLOW}🛑 停止 Agent 系统...${NC}"
    
    if [ -f "$AGENT_ROOT/.agent.pid" ]; then
        pid=$(cat "$AGENT_ROOT/.agent.pid")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${BLUE}📋 发送停止信号到进程 $pid${NC}"
            kill -TERM $pid
            
            # 等待进程优雅退出
            for i in {1..10}; do
                if ! ps -p $pid > /dev/null 2>&1; then
                    echo -e "${GREEN}✅ Agent 系统已停止${NC}"
                    rm -f "$AGENT_ROOT/.agent.pid"
                    return 0
                fi
                sleep 1
            done
            
            # 强制杀死进程
            echo -e "${YELLOW}⚠️  强制停止进程${NC}"
            kill -KILL $pid 2>/dev/null
            rm -f "$AGENT_ROOT/.agent.pid"
            echo -e "${GREEN}✅ Agent 系统已强制停止${NC}"
        else
            echo -e "${YELLOW}⚠️  Agent 系统未在运行${NC}"
            rm -f "$AGENT_ROOT/.agent.pid"
        fi
    else
        echo -e "${YELLOW}⚠️  未找到 PID 文件，Agent 系统可能未在运行${NC}"
    fi
}

# 检查系统状态
check_status() {
    echo -e "${BLUE}📊 检查 Agent 系统状态...${NC}"
    
    if [ -f "$AGENT_ROOT/.agent.pid" ]; then
        pid=$(cat "$AGENT_ROOT/.agent.pid")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Agent 系统正在运行 (PID: $pid)${NC}"
            
            # 显示进程信息
            echo -e "${BLUE}📋 进程信息:${NC}"
            ps -p $pid -o pid,ppid,cmd,etime,pcpu,pmem
            
            # 显示端口使用情况
            echo -e "${BLUE}🌐 端口使用情况:${NC}"
            netstat -tlnp 2>/dev/null | grep $pid || echo "   无监听端口"
            
        else
            echo -e "${RED}❌ Agent 系统未运行 (PID 文件存在但进程不存在)${NC}"
            rm -f "$AGENT_ROOT/.agent.pid"
        fi
    else
        echo -e "${YELLOW}⚠️  Agent 系统未运行${NC}"
    fi
}

# 环境检查
check_environment() {
    echo -e "${BLUE}🔍 执行环境检查...${NC}"
    python3 "$AGENT_MAIN" --check-only
}

# 重启系统
restart_agent() {
    echo -e "${YELLOW}🔄 重启 Agent 系统...${NC}"
    stop_agent
    sleep 2
    start_agent "$@"
}

# 主逻辑
main() {
    cd "$AGENT_ROOT"
    
    case "$1" in
        "start")
            check_python
            setup_environment
            shift
            start_agent "$@"
            ;;
        "stop")
            stop_agent
            ;;
        "restart")
            check_python
            setup_environment
            shift
            restart_agent "$@"
            ;;
        "status")
            check_status
            ;;
        "check")
            check_python
            setup_environment
            check_environment
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        "")
            # 默认启动
            check_python
            setup_environment
            start_agent
            ;;
        *)
            echo -e "${RED}❌ 未知命令: $1${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
