# Project:      Agent
# Author:       yomu
# Time:         2024/12/28
# Version:      0.1
# Description:  ollama agent

"""
    ollama 的 agent
"""

import fastapi
import uvicorn
import requests
from urllib.parse import urljoin, quote
from dotenv import dotenv_values
from typing import Dict, List
from fastapi import FastAPI, Form, Body

from Module.Utils.Logger import setup_logger
from Module.Utils.LoadConfig import load_config


class OllamaAgent:
    """
        Ollama 的代理
    """
    def __init__(self):
        self.logger = setup_logger(name="OllamaAgent", log_path="InternalModule")
        
        self.env_vars = dotenv_values("/home/yomu/agent/Module/LLM/.env") 
        self.config_path = self.env_vars.get("OLLAMA_AGENT_CONFIG_PATH","") 
        self.config: Dict = load_config(config_path=self.config_path, config_name='OllamaAgent', logger=self.logger)
        
        self.ollama_url = self.config.get("url","http://127.0.0.1:11434")
        self.host = self.config.get("host","0.0.0.0")
        self.port = self.config.get("port", 20030)
        
        self.app=FastAPI()
        
        self.setup_routes()
        
    def setup_routes(self):
        """设置路由"""
        
        # chat 
        @self.app.api_route("/agent/chat/to_ollama/chat/", methods=["POST"])
        async def  chat_with_ollama(data: Dict=Body(...)):
            return await self._chat(data)

        
        #generate
        @self.app.api_route("/agent/chat/to_ollama/generate/", methods=["POST"])
        async def generate_respone(data: Dict=Body(...)):
            return await self._generate_response(data)
        
        
    async def _generate_response(self, data: Dict):
        """chat"""
        headers = {"Content-Type": "application/json"}
        url = self.ollama_url
        url = urljoin(url,"/api/generate")

        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            return response_data['response']
        else:
            return f"Error: {response.status_code}, {response.text}"
        
        
    async def _chat(self,data: Dict):
        """chat"""
        headers = {"Content-Type": "application/json"}
        
        url = self.ollama_url
        url = urljoin(url,"/api/chat")

        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            return response_data
        else:
            return f"Error: {response.status_code}, {response.text}"
        
    
    def run(self):
        uvicorn.run(self.app, host=self.host, port=self.port)
    
    
def main():
    module = OllamaAgent()
    module.run()
    
    
def test():
    model = OllamaAgent()
    chat_data = {
            "model": "llama3.2",
            "messages": [
                {
                "role": "user",
                "content": "你好"
                }
            ],
            "stream": False
            }
    # reply = model._chat(data)
    generate_data={
                    "model": "llama3.2",
                    "prompt": "你好",
                    "stream": False
                    }
    reply = model._generate_response(generate_data)
    print(f"模型回复: {reply}")
    
    
if __name__ == "__main__":
    main()
    
    