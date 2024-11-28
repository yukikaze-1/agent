# Project:      Agent
# Author:       yomu
# Time:         2024/11/27
# Version:      0.1
# Description:  agent internal module initialize


"""
    用于启动agent内部模块
    在当前进程环境(即agent的进程环境)中运行
    
    1. LLM
        1) ollama agent *
    2. TTS
        1) GPTSoVits agent *
        2) CosyVoice agent
    3. STT
        1) SenseVoice agent 
    4. 
"""

import os
from typing import List,Dict
from dotenv import load_dotenv

load_dotenv()

class InternalModuleManager:
    """
        负责管理启动和关闭 AI agent的各内部模块
        (如各种功能的外部服务器的客户端agent)
        
        如需要添加自定义的内部模块，则需要按照下面的格式： 
        {
            
        }
    """
    def __init__(self,
                 module,
                 ):
        pass
    
    def _init_base_module(slef):
        """
        添加最小启动的最基础的内部功能模块
        
        (注：ollama llm不在此处，因为langchain提供了ChatOllama这一模块)
        
            1. 语音合成(GPTSoVits)
            2. 语音识别(SenseVoice)
            3. 
        """
        pass
    
    def _init_optional_module(self):
        """
        添加可选的内部功能模块

            1. 
            
        """
        pass

    def init_module():
        pass
    
    

