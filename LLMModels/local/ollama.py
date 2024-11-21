# Project:      Agent
# Author:       yomu
# Time:         2024/11/22
# Version:      0.1
# Description:  Ollama agent

"""
    与Ollama的接口，提供各种ollama支持的大模型
    目前支持的模型：
        llama3.2:latest              
        llava:13b                    
        llava-llama3:latest          
        nemotron-mini:latest         
        llava:latest                 
        llama3.2-vision:latest       
        solar:latest                 
        gemma2:latest                
        qwen2.5-coder:latest         
        qwen2.5:14b                  
        qwen2.5:latest            
"""

from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser



