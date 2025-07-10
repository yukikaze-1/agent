#!/bin/bash
# 启动Ollama并注册到Consul

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONSUL_URL="http://127.0.0.1:8500"
OLLAMA_PORT=11434

echo "🚀 启动Ollama并注册到Consul..."

# 检查Ollama是否已经在运行
if curl -s http://127.0.0.1:$OLLAMA_PORT/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama已经在运行"
else
    echo "🔄 启动Ollama服务..."
    # 在后台启动Ollama
    nohup ollama serve > /dev/null 2>&1 &
    OLLAMA_PID=$!
    
    # 等待Ollama启动
    echo "⏳ 等待Ollama启动..."
    for i in {1..30}; do
        if curl -s http://127.0.0.1:$OLLAMA_PORT/api/tags > /dev/null 2>&1; then
            echo "✅ Ollama启动成功"
            break
        fi
        sleep 1
        if [ $i -eq 30 ]; then
            echo "❌ Ollama启动超时"
            exit 1
        fi
    done
fi

# 注册到Consul
echo "📝 注册Ollama到Consul..."
python3 "$SCRIPT_DIR/register_service.py" --service ollama --consul-url "$CONSUL_URL"

if [ $? -eq 0 ]; then
    echo "🎉 Ollama启动并注册成功！"
    echo ""
    echo "📋 服务信息:"
    echo "  - Ollama API: http://127.0.0.1:$OLLAMA_PORT"
    echo "  - Consul UI: $CONSUL_URL/ui"
    echo ""
    echo "🛑 要停止并注销服务，请运行:"
    echo "  python3 $SCRIPT_DIR/register_service.py --deregister ollama_server"
    echo "  pkill ollama"
else
    echo "❌ 注册失败"
    exit 1
fi
