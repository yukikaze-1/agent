# Project:      Agent
# Author:       yomu
# Time:         2024/12/1
# Version:      0.1
# Description:  agent frame initialize

"""
    负责AI agent 框架的初始化
    agent运行时框架
"""
import os
from concurrent.futures import ThreadPoolExecutor


class AgentFrameManager:
    """

    """
    threadpool_number: int # 线程池大小
    
    def __init__(self, threadpool_number=10):
        # 线程池
        self.threadpool = ThreadPoolExecutor(threadpool_number)
    
    def init_frame(self):
        pass
    
    def __del__(self):
        pass