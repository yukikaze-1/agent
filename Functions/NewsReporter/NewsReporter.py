# Project:      Agent
# Author:       yomu
# Time:         2024/11/20
# Version:      0.1
# Description:  NewsReporter

# TODO 该文件实现newscollector+GPTSoVits的组合体NewsReporter
from Models.Utils.news_collector.newscollector import NewsCollector

"""
    运行前需要:
        1.本地运行Ollama服务端以及对应的大模型
        2.本地运行GPTSoVits服务端
    例子：
        Ollama:
            #bash: ollama serve
            #bash: ollama run llama3.2
        GPTSovits:
            #bash: conda activate GPTSoVits     (你的GPTSoVits环境)
            #bash: cd  GPTSovits                (你的GPTSoVits目录)
            #bash: python api_v2.py -a 0.0.0.0  (运行GPTSoVits服务端api)
"""


# collector = NewsCollector()  # 创建新闻收集器实例


if __name__ == "__main__":
    print("This is a part of agent,supposed not to run directly.Do nothing")
