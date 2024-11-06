# Project:      Agent
# Author:       yomu
# Time:         2024/10/24
# Version:      0.1
# Description:  agent functions

import os
import json
import time
from prompt import *
from Tools.tools import *
from memory import *
from TTS.tts import *


# TODO 实现
# 调用本地或者云端大模型
def call_llm(query,prompt):
    return "你好，调用本地或者云端大模型成功"

# 调用工具
def call_tool():
    pass

# 将回答生成语音
def generate_voice():
    pass

# 实时监听语音输入，并将输入转为文本格式
def capture_voice():
    pass

# 实时监听视频输入，并理解视频输入
def capture_video():
    pass

# agent记忆查询、更新、删除模块接口
def agent_memory(operator,memory={}):
    pass

# 解析大模型的回答
def reslove_response(response):
    pass

# agent接口，所有用户的输入全部通过该接口与大模型交互
# 用户每输入一次，就调用一次
# 针对任务的
def agent_execute(query,max_request_time,_long_memory):# TODO 完善整体流程
    # 短期记忆(针对该任务)
    short_memory = ShortMemory()    
    cur_request_time = 0
    long_memory = _long_memory
    
    
    while cur_request_time < max_request_time :
        cur_request_time += 1
        
        # 生成prompt
        prompt = generate_prompt(query,short_memory)
        
        start_time = time.time()
        print(f'********* {cur_request_time}. 开始调用大模型.....')
        
        # 调用大模型
        response = call_llm(query,prompt)
        
        end_time = time.time()
        print(f'结束调用{cur_request_time}次,花费时间:{end_time-start_time}')
        
        if not response or not isinstance(response,dict):
            print("call llm exception, response is :{}".format(response))
            continue
        
        # 解析大模型的响应response
        result = reslove_response(response)
        
        # 根据大模型的回复执行相应操作
        function_call_result = call_tool()
        
        # 更新短期记忆
        short_memory.update_memory()
        
        # 任务完成，短期记忆选择性写入长期记忆
        long_memory.update_memory()
    
    if cur_request_time == max_request_time:
        print("本次任务执行失败!")
    else:
        print("本次任务成功！")