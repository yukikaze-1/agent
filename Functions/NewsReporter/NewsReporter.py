# Project:      Agent
# Author:       yomu
# Time:         2024/11/20
# Version:      0.1
# Description:  NewsReporter

'''
    测试：运行前要export PYTHONPATH=/home/yomu/agent:$PYTHONPATH

'''

# TODO 该文件实现newscollector+GPTSoVits的组合体NewsReporter

from Module.Utils.news_collector.newscollector import NewsCollector
from Module.TTS.GPTSoVits.GPTSoVits_class import GPTSoVitsAgent

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


def main():
    collector = NewsCollector()     # 创建新闻收集器实例
    reporter = GPTSoVitsAgent()     # 创建GPTSoVits客户代理实例
    
    news_list = collector.run()
    for category, pubtime, content, link in news_list:
        print(f"[{category}] {pubtime} {content} {link}")
        reporter.infer_tts_get(content=content)

if __name__ == "__main__":
    print("This is a part of agent,supposed not to run directly.Do nothing")
    main()
    

