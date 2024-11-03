# Project:      Agent
# Author:       yomu
# Time:         2024/10/24
# Version:      0.1
# Description:  agent main

import json
from functions import call_llm

"""
    ***********************************************************************************************
    ***********************************************************************************************
    ***********************************************************************************************
"""

# 大模型响应格式(task向)
query_response_format = """
{
    "action": {
        "name": "action_name",
        "args": {
            "args_name": "args value"
        }
    },
    "thoughts":{
        "text": "thought",
        "plan": "plan",
        "criticism": "criticism",
        "step": "the summary of this step",  
        "reasoning": "reason"
    }
}
"""
"""
    ***********************************************************************************************
    ***********************************************************************************************
    ***********************************************************************************************
"""

# 大模型的响应格式(keywords 向)
keywords_response_format = """
    {
        "target": "the user's target",
        "keywords": []
    }
"""

# "keywords生成" 的prompt模版
keywords_query_format = """
    你需要从以下的内容中提取关键词。

    内容：
    {content}

    你应该以 json 的格式响应，响应格式如下：
    {keywords_response_format}
    确保响应结果可以由 python json.loads() 成功加载。
"""

# 生成“请求大模型总结关键词”的prompt
def generate_keywords_prompt(content):
    keywords_prompt = keywords_query_format.format(
        content=content,
        keywords_response_format=keywords_response_format
        )
    return keywords_prompt

# 总结关键词，会调用大模型
def summarize_keywords(content):
    keywords_prompt = generate_keywords_prompt(content)
    response = call_llm(keywords_prompt)
    keywords = response.get('keywords', [])
    return keywords

"""
    ***********************************************************************************************
    ***********************************************************************************************
    ***********************************************************************************************
"""

# 大模型的响应格式(prompt优化 向)
prompt_optimize_response_format = {
    'target': "user's target",
    'process': {
        'step1': 'step1',
        'step2': 'step2',
        'step3': 'step3',
        'more_steps': 'More steps if necessary'
    }
}

prompt_optimize_constraints = [
    '不要涉及政治'
    ]

# "prompt优化" 的prompt 模版
prompt_optimize_template = """
    麻烦将接下来的内容中所诉求的目标拆分成一个一个的小目标，并将其组织成流程。

    内容:
    {content}

    你应该以 json 的格式响应，响应格式如下：
    {prompt_optimize_output_format}
    确保响应结果可以由 python json.loads() 成功加载。

    限制说明：
    {prompt_optimize_constraints}
"""

# 生成 "prompt优化请求" 的prompt
def generate_optimize_prompt_of_prompt():
    pass


"""
    ***********************************************************************************************
    ***********************************************************************************************
    ***********************************************************************************************
"""


constraints = [
    
]
memory = {
    
}
resources = [
    
]

# "通常任务" 的prompt模板
query_prompt_template = """
    你是一个问答专家，你必须始终独立做出决策，无需寻求用户的帮助，发挥你作为 LLM 的优势，追求简答的策略，不要涉及法律的问题。

    目标:
    {query}

    限制条件说明:
    {constraints}

    上下文:
    {memory}

    资源说明:
    {resources}

    最佳实践的说明:

    响应格式说明:
    {query_response_format}
"""

# 生成"通常任务"的prompt
def generate_prompt(query, short_memory):
    pass


"""
    ***********************************************************************************************
    ***********************************************************************************************
    ***********************************************************************************************
"""