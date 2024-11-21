# Agent


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
        - [ ] CosyVoice
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
