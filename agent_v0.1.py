# Project:      Agent
# Author:       yomu
# Time:         2024/10/24
# Version:      0.1
# Description:  agent main

"""
    启动AI agent的入口
"""

import os
import time
import argparse
import subprocess
import sys
from dotenv import load_dotenv

from Init.discard.AgentInit import InitAgent

# 加载环境变量
_ = load_dotenv()

# 初始化各个模块
def init_service(params:None):
    """
    使用 subprocess 执行 init.py 并传递命令行参数
    init.py采用config.yml文件来作为配置文件
    
    :param params: 要传递给 init.py 的参数列表（可以是任何类型的数据）
    """
    # 构建命令行列表：'python', 'init.py' 和传递的参数
    command = ['python', 'init.py'] + params  # 组合成完整的命令行
    print(f"Running command: {command}")
    
    # 执行命令并捕获输出
    result = subprocess.run(command, capture_output=True, text=True)
    
    # 打印 init.py 的输出
    print("init.py Output:")
    print(result.stdout)
    
    # 如果有错误输出，打印错误
    if result.stderr:
        print("Error:", result.stderr)

def main(config_path:str):
    # 初始化各个模块
    if os.path.isfile(config_path):
        init_service()
    else:
        raise FileNotFoundError(f"No such a config file named '{config_path}'!")
    
    # 执行
    # TODO 完善核心框架
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="agent start with modules")
    parser.add_argument("--config",
                        type=str,
                        default="./Init/config.yml",
                        help="agent配置文件config.yml的路径,默认为./Init/config.yml")
    # parser.add_argument("--pattern","-p",
    #                     type=str,
    #                     default='base',
    #                     help="运行模式：1.基础模式base(只有聊天机器人) 2.高级模式 advance(可自定义启动模块)")
    # parser.add_argument("--model","-m",
    #                     type=str,
    #                     default='llama3.2',
    #                     help="启用的核心LLM的名字(只能从ollama支持的模型中选择)")
    args = parser.parse_args()
    main(args.config)
    
    