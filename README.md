# Agent

一个模块化的 AI Agent 系统，支持多模态交互和智能服务。

## 🚀 快速开始

```bash
# 克隆项目
git clone <repository_url>
cd agent

# 直接运行（无需手动配置环境变量）
python agent_v0.1.py

# 或使用启动脚本
./start_agent.sh start
```

## 📚 文档

- **[启动指南](Docs/STARTUP_GUIDE.md)** - 详细的启动方法和配置说明
- **[跨平台部署](Docs/CROSS_PLATFORM_DEPLOY_GUIDE.md)** - 确保在不同系统上的兼容性
- **[环境工具](Tools/Environment/README.md)** - 环境验证和故障排除工具
- **[归档文件](Archive/README.md)** - 已归档的测试脚本和临时文件

## 🔧 环境验证

```bash
# 快速验证环境
python Tools/Environment/quick_verify.py

# 完整环境测试
python Tools/Environment/test_full_environment.py
```

## 📁 项目结构

```
agent/
├── Archive/          # 归档的测试脚本和临时文件
├── Client/          # 客户端实现
├── Config/          # 配置文件
├── Core/            # 核心模块
├── Data/            # 数据存储
├── Docs/            # 文档
├── Functions/       # 功能模块
├── Init/            # 初始化模块
├── Log/             # 日志文件
├── Memory/          # 记忆模块
├── Module/          # 各种AI模块
├── Other/           # 其他服务
├── Service/         # 微服务
├── Tools/           # 工具脚本
└── Users/           # 用户数据
```

# 1. 简介
# 2. 框架

## 功能模块
- 视觉模块
    1. 目标检测
        - [x] YOLO11
            > https://github.com/ultralytics/ultralytics
        
        - [ ] D-FINE
            > https://github.com/Peterande/D-FINE
    2. 实例分割
        - [ ] SAM2
            > https://github.com/facebookresearch/sam2
    3. OCR
        - [ ] GOT-OCR2.0
            > https://github.com/Ucas-HaoranWei/GOT-OCR2.0
        - [ ] Surya-OCR
            > https://github.com/VikParuchuri/surya
    4. 目标跟踪
    5. 关键点检测
        - CoTracker3
            > https://github.com/facebookresearch/co-tracker
    6. 3D场景重建
    7. 表情识别

- 听觉模块
    1. 语音识别(STT)
        - [ ] SenseVoice
            > https://github.com/FunAudioLLM/SenseVoice
        - [ ] StreamingSenseVoice
            > https://github.com/pengzhendong/streaming-sensevoice
        - [ ] ~~whisper~~
            > https://github.com/openai/whisper
    2. 实时打断
    3. 语气识别

- 语音模块
    1. 语音生成(TTS)
        - [x] GPTSoVits
            > https://github.com/RVC-Boss/GPT-SoVITS
        - [ ] CosyVoice2
            > https://github.com/FunAudioLLM/CosyVoice
    2. 其他声音生成
        - [ ] Stable-audio-tools
            > https://github.com/Stability-AI/stable-audio-tools
- 记忆模块
    - [ ] Langchain自带记忆模块
    - [ ] 自己实现一个记忆模块

- 联网模块

- 语言模型
    - [x] LLam3.2
        > https://github.com/meta-llama/llama3
    - [x] Qwen2.5
        > https://github.com/QwenLM/Qwen2.5
    - [ ] Gemma 2
        > 

- RAG模块
- VSA模块
    - [ ] VSA
        > https://github.com/cnzzx/VSA

- 其他模块
    1. 文本图像匹配
        - [ ] CLIP
            > https://github.com/openai/CLIP
    2. AI画图模块
        - [ ] Stable-Diffusion
            - [ ] Stable-Diffusion3.5
            > https://github.com/Stability-AI/sd3.5
            <details>
            <summary>配置要求</summary>

             - Stable-Diffusion3.5 large/large_turbo (FP8)==> 24GB(18GB)

             - Stable-Diffusion3.5 medium (FP8) == > 18GB(14GB)
            </details>

        - [ ] flux
        - [ ] LoRa
    3. AI视频生成模块
        - [ ] Sora
    4. 语音克隆模块
        - [ ] ~~So-Vits-SVC~~(已停更)
        > https://github.com/svc-develop-team/so-vits-svc
        - [ ] So-Vits-SVC-fork
        > https://github.com/voicepaw/so-vits-svc-fork
        - [ ] VoiceChanger(实时语音转换)
        > https://github.com/w-okada/voice-changer
    5. Prompt模块
        - [ ] LangGPT
        > https://github.com/langgptai/LangGPT
    6. Memory模块
        - [ ] MemGPT
            > https://github.com/letta-ai/letta
        - [ ] OMNE框架
            >  https://arxiv.org/abs/2410.15665
    7. 端到端语音模型   
        - [ ] GLM-4-voice
            > https://github.com/THUDM/GLM-4-Voice
    8. 端侧控制模块
        - [ ] LiMAC框架
            > https://arxiv.org/abs/2410.17883
    9. 对接ollama的接口模块
        - [ ] LangChain-Chatchat[参考]
            > https://github.com/chatchat-space/Langchain-Chatchat
        

- 多agent合作模块
    - [ ] Swarm
        > https://github.com/openai/swarm
    - [ ] Co-STORM
        > https://github.com/stanford-oval/storm
# 3. 安装
