# Project:      Agent
# Author:       yomu
# Time:         2024/12/10
# Version:      0.1
# Description:  agent video player

import os
import pygame
import json
from concurrent.futures import ThreadPoolExecutor

"""
    负责播放视频，多线程管理
"""

# TODO 实现
class VideoPlayer:
    """
        播放视频,管理视频播放的线程
    """
    thread_number: int   # 线程池的容量 

    def __init__(self, thread_number = 10):     
        self.thread_number = thread_number
        self.threadpool = ThreadPoolExecutor(self.thread_number)
    
    def _play(self,video_path):
        pass
        
    def play(self,video_path: str):
        if os.path.isinstance(video_path):
            print(f"Error!{video_path} is not a video!")
            return 
        result = self.threadpool.submit(self._play, video_path)
        
    def __del__(self):
        print("VideoPlayer deleted")