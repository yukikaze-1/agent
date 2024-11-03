# 


import os
import json
import dashscope

from prompt_1 import user_prompt
from zhipuai import ZhipuAI
from dotenv import load_dotenv
from dashscope.api_entities.dashscope_response import Message

load_dotenv()

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

class ModelProvider(object):
    def __init__(self):
        self.api_key = os.environ.get('DASHSCOPE_API_KEY')
        self.model_name = os.environ.get('MODEL_NAME')
        self._client = dashscope.Generation()
        self.max_retry_time = 3

    def chat(self, prompt, chat_history):
        cur_retry_time = 0
        while cur_retry_time < self.max_retry_time:
            cur_retry_time += 1
            try:
                messages = [
                    Message(role="system", content=prompt)
                ]
                for his in chat_history:
                    messages.append(Message(role="user", content=his[0]))
                    messages.append(Message(role="system", content=his[1]))
                # 最后1条信息是用户的输入
                messages.append(Message(role="user", content=user_prompt))
                response = self._client.call(
                    model=self.model_name,
                    api_key=self.api_key,
                    messages=messages
                )
                # print("response:{}".format(response))
                content = json.loads(response["output"]["text"])
                return content
            except Exception as e:
                print("call llm exception:{}".format(e))
        return {}


def call_zhipuAI(content): # TODO 完善
    client = ZhipuAI(api_key=ZHIPU_API_KEY)  # 请填写您自己的APIKey
    response = client.chat.completions.create(
        model="glm-4",  # 请填写您要调用的模型名称
        messages=[
            {"role":"user",
            "content":content
            }
        ])
    answer = response.choices[0].message
    