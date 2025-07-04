# 服务发现架构实施指南

## 🎯 概述

本项目已成功实施**服务发现模式**，替代了原有的外部服务启动模式。新架构具有以下优势：

- ✅ **职责分离**: 外部服务独立部署，主程序专注业务逻辑
- ✅ **生产就绪**: 符合微服务部署最佳实践
- ✅ **故障隔离**: 外部服务故障不影响主程序启动
- ✅ **水平扩展**: 支持服务实例动态添加
- ✅ **运维友好**: 服务可独立管理和监控

## 🏗️ 架构对比

### 旧架构（已弃用）
```
主程序 → 启动外部服务 → 启动内部FastAPI代理 → 业务逻辑
```

### 新架构（推荐）
```
外部服务（独立部署） ← 服务发现 ← 内部代理模块 ← 主程序业务逻辑
```

## 📁 新增组件

### 1. 服务发现模块 (`Init/ServiceDiscovery/`)
- `service_discovery_manager.py`: 服务发现管理器
- `service_connector.py`: 外部服务连接器  
- `exceptions.py`: 服务发现相关异常
- `config.yml`: 服务发现配置

### 2. 内部代理模块
- `Module/LLM/LLMProxy.py`: LLM服务代理
- `Module/TTS/TTSProxy.py`: TTS服务代理
- `Module/STT/STTProxy.py`: STT服务代理

### 3. 更新的初始化流程
- `Init/Init.py`: 支持服务发现模式的系统初始化器

## 🚀 快速开始

### 步骤1: 部署外部服务

```bash
# 1. 启动Consul
consul agent -dev -client 0.0.0.0

# 2. 启动Ollama
ollama serve

# 3. 启动GPTSoVits服务
cd /path/to/GPTSoVits
python GPTSoVits_api.py -a 0.0.0.0 -p 9880

# 4. 启动SenseVoice服务
cd /path/to/SenseVoice  
python server.py --port 20060
```

### 步骤2: 服务注册

外部服务需要在Consul中注册，可以通过以下方式：

**手动注册**:
```bash
# 注册Ollama服务
curl -X PUT http://localhost:8500/v1/agent/service/register \
  -d '{
    "ID": "ollama_server",
    "Name": "ollama_server", 
    "Address": "127.0.0.1",
    "Port": 11434,
    "Check": {
      "HTTP": "http://127.0.0.1:11434/api/tags",
      "Interval": "10s"
    }
  }'
```

**自动注册**（推荐）:
使用服务自注册机制，在服务启动时自动注册到Consul。

### 步骤3: 启动主程序

```python
from Init.Init import SystemInitializer

# 使用服务发现模式
initializer = SystemInitializer(use_service_discovery=True)
result = initializer.initialize_all()

if result.success:
    print("✅ 系统启动成功")
else:
    print(f"❌ 系统启动失败: {result.message}")
```

### 步骤4: 使用代理模块

```python
import asyncio
from Module.LLM.LLMProxy import create_llm_proxy
from Module.TTS.TTSProxy import create_tts_proxy

async def main():
    # 创建LLM代理
    llm = await create_llm_proxy()
    response = await llm.chat("Hello!")
    
    # 创建TTS代理
    tts = await create_tts_proxy()
    audio_file = await tts.synthesize("你好世界")
    
    # 清理资源
    await llm.cleanup()
    await tts.cleanup()

asyncio.run(main())
```

## 🐳 Docker部署示例

### docker-compose.yml
```yaml
version: '3.8'

services:
  # 服务注册中心
  consul:
    image: consul:latest
    ports:
      - "8500:8500"
    command: "agent -dev -client 0.0.0.0"

  # LLM服务
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

  # TTS服务
  gpt-sovits:
    build: ./services/gpt-sovits
    ports:
      - "9880:9880"

  # 主程序
  agent-core:
    build: .
    depends_on:
      - consul
      - ollama
      - gpt-sovits
    environment:
      - CONSUL_URL=http://consul:8500
    volumes:
      - ./logs:/app/logs

volumes:
  ollama_data:
```

## ⚙️ 配置说明

### 服务发现配置 (`Init/ServiceDiscovery/config.yml`)

```yaml
service_discovery:
  # 必需服务列表
  required_services:
    - "ollama_server"
    - "GPTSoVits_server" 
    - "SenseVoice_server"

  # 服务映射
  service_mapping:
    "ollama_server": "llm_service"
    "GPTSoVits_server": "tts_service"
    "SenseVoice_server": "stt_service"

  # 健康检查
  health_check:
    timeout: 5
    retry_count: 3
    retry_delay: 2
```

### 代理模块配置示例

```yaml
# LLM代理配置
llm_proxy:
  consul_url: "http://127.0.0.1:8500"
  default_model: "qwen2.5"
  request_timeout: 120.0
  max_retries: 3

# TTS代理配置  
tts_proxy:
  consul_url: "http://127.0.0.1:8500"
  save_dir: "${AGENT_HOME}/Temp"
  default_character: "Elysia"
  characters:
    Elysia:
      gpt_path: "models/gpt.ckpt"
      sovits_path: "models/sovits.pth"
      ref_audio: "audio/ref.wav"
      ref_audio_text: "你好，我是爱莉希雅。"
```

## 🔧 故障排除

### 常见问题

1. **服务发现失败**
   ```
   错误: Service 'ollama_server' not found
   解决: 检查服务是否在Consul中正确注册
   ```

2. **连接超时**
   ```
   错误: Failed to connect to service
   解决: 检查网络连接和服务健康状态
   ```

3. **代理初始化失败**
   ```
   错误: LLM service not available
   解决: 确保外部LLM服务正在运行并已注册
   ```

### 调试命令

```bash
# 检查Consul服务状态
curl http://localhost:8500/v1/agent/services

# 检查服务健康状态
curl http://localhost:8500/v1/health/service/ollama_server

# 测试服务连接
curl http://localhost:11434/api/tags
```

## 📊 监控与日志

### 日志位置
- 服务发现: `Log/Other/ServiceDiscovery.log`
- 内部代理: `Log/InternalModule/LLMProxy.log`
- 系统初始化: `Log/Other/SystemInitializer.log`

### 健康检查
```python
# 检查代理模块健康状态
health_status = await llm_proxy.check_health()
print(f"LLM代理健康状态: {health_status}")
```

## 🎉 演示运行

运行完整演示：
```bash
cd Init/ServiceDiscovery
python demo_service_discovery.py
```

## 🔄 从旧架构迁移

如果需要回退到旧架构：
```python
# 使用传统模式
initializer = SystemInitializer(use_service_discovery=False)
```

---

## 总结

新的服务发现架构为您的Agent系统提供了：
- 🏭 **生产级别的可靠性**
- 🔧 **灵活的部署选项**  
- 📈 **良好的扩展性**
- 🛠️ **易于维护**

建议在生产环境中使用服务发现模式，在开发环境中可以根据需要选择合适的模式。
