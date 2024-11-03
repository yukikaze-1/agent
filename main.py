# Project:      Agent
# Author:       yomu
# Time:         2024/10/24
# Version:      0.1
# Description:  agent main

import os
import time
from functions import *
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 全局记忆(长期记忆)# TODO 长期记忆怎么解决？放哪个文件？谁来管理？


# TODO 这玩意走单线程还是多线程？能让模块在不同的线程运行吗？比如记忆模块和行动模块？
def main():
    long_mem = LongMemory()
    # print(f"Using model:{os.getenv('MODEL_NAME')}")
    while True:
        print(f"Using model:{os.getenv('MODEL_NAME')}")
        query = input("Enter your query:")
        if "exit" == query:
            return
        agent_execute(query,long_mem)


if __name__ == "__main__":
    main()
    
    