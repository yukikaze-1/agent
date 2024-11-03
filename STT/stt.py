# Project:      Agent
# Author:       yomu
# Time:         2024/10/24
# Version:      0.1
# Description:  agent STT



# TODO 添加其他STT模型
# TODO 该文件负责对接各种STT模型

"""
    采用SenseVoice模型来将语音转为文字
"""

import SenseVoice
from dotenv import load_dotenv

load_dotenv("./.env")
