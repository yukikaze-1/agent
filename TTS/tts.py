# Project:      Agent
# Author:       yomu
# Time:         2024/10/30
# Version:      0.1
# Description:  TTS

"""
    使用GPTSoVits模型进行TTS 
    生成的语音存放在 ../.env 中的 GPTSOVITS_LOCAL_OUTPUT_DIR 中
    目前是存放在/home/yomu/agent/TTS/output
"""
# TODO 目前采用了GPTSoVits模型，后续考虑添加CosyVoice
# TODO 该文件负责对接各种TTS模型

import GPTSoVits
