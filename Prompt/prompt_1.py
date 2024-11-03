# Project:      Agent
# Author:       yomu
# Time:         2024/10/24
# Version:      0.1
# Description:  agent main

import json
import logging
from functions import call_llm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

user_prompt = "根据给定的目标和迄今为止取得的进展，确定下一个要执行action，并使用前面指定的JSON模式进行响应："

class TaskHandler:
    def __init__(self, response_format, query_template):
        self.response_format = response_format
        self.query_template = query_template

    def generate_prompt(self, content, **kwargs):
        return self.query_template.format_map({"content": json.dumps(content), **kwargs})

    def call_model(self, prompt):
        try:
            response = call_llm(prompt)
            if isinstance(response, str) and response:
                return response
            elif response is None:
                logging.warning("No response received from LLM.")
            else:
                logging.warning("Unexpected response type from LLM.")
        except (ConnectionError, TimeoutError) as e:
            logging.error(f"Error calling LLM: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
        return ""

class KeywordTaskHandler(TaskHandler):
    def __init__(self):
        response_format = {
            "target": "the user's target",
            "keywords": []
        }
        query_template = """
        你需要从以下的内容中提取关键词。

        内容：
        {content}

        你应该以 json 的格式响应，响应格式如下：
        {response_format}
        确保响应结果可以由 python json.loads() 成功加载。
        """
        super().__init__(response_format, query_template)

    def summarize_keywords(self, content):
        prompt = self.generate_prompt(content=content)
        response = self.call_model(prompt)
        if not response:
            return []
        try:
            response_data = json.loads(response)
            return response_data.get('keywords', [])
        except (json.JSONDecodeError, TypeError) as e:
            logging.error(f"Error parsing response: {e}")
        return []

class PromptOptimizationHandler(TaskHandler):
    def __init__(self):
        response_format = {
            "target": "user's target",
            "process": {
                "step1": "step1",
                "step2": "step2",
                "step3": "step3",
                "more_steps": "More steps if necessary"
            }
        }
        query_template = """
        麻烦将接下来的内容中所诉求的目标拆分成一个一个的小目标，并将其组织成流程。

        内容:
        {content}

        限制:
        {constraints}

        你应该以 json 的格式响应，响应格式如下：
        {response_format}
        确保响应结果可以由 python json.loads() 成功加载。

        限制说明：
        {constraints}
        """
        super().__init__(response_format, query_template)

class GeneralTaskHandler(TaskHandler):
    def __init__(self):
        response_format = {
            "action": {
                "name": "action_name",
                "args": {
                    "args_name": "args value"
                }
            },
            "thoughts": {
                "text": "thought",
                "plan": "plan",
                "criticism": "criticism",
                "step": "the summary of this step",
                "reasoning": "reason"
            }
        }
        query_template = """
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
        {response_format}
        """
        super().__init__(response_format, query_template)
