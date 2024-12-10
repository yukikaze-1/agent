# Project:      Agent
# Author:       yomu
# Time:         2024/12/10
# Version:      0.1
# Description:  agent audio player

import os
import pygame
from concurrent.futures import ThreadPoolExecutor

"""
    负责播放音频，多线程管理
"""

# TODO 待完善
class AudioPlayer:
    """
        播放音频,管理音频播放的线程
    """
    thread_number: int   # 线程池的容量 

    def __init__(self, thread_number = 10):     
        self.thread_number = thread_number
        self.threadpool = ThreadPoolExecutor(self.thread_number)
    
    def _play(self,audio_path):
        pygame.init()
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(1)
        pygame.mixer.music.stop()
        pygame.quit()
        
    def play(self,audio_path: str):
        if os.path.isinstance(audio_path):
            print(f"Error!{audio_path} is not a audio!")
            return 
        result = self.threadpool.submit(self._play, audio_path)
        
    def __del__(self):
        print("AudioPlayer deleted")