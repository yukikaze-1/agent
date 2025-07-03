# Project:      Agent
# Author:       yomu
# Time:         2024/12/27
# Version:      0.1
# Description:  pocess the text input of user

"""
    接受并处理用户发来的文本消息
"""

import os
import uvicorn
import fastapi
from fastapi import Form, FastAPI
from typing import Dict
from dotenv import dotenv_values

from Module.Utils.ConfigTools import load_config
from Module.Utils.Logger import setup_logger

class UserTextInputProcessModule:
    """
        处理用户发来的文本消息
            1. 文本优化
            2. 转发给PromptOptimizer
    """
    def __init__(self):
        self.logger = setup_logger(name="UserTextInputProcessModule", log_path="InternalModule")

        self.env_vars = dotenv_values(os.path.join(
            os.environ.get('AGENT_HOME', os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "Module/Input/.env"
        ))
        self.config_path = self.env_vars.get("USER_TEXT_INPUT_PROCESS_MODULE_CONFIG_PATH","") 
        self.config: Dict = load_config(config_path=self.config_path, config_name='UserTextInputProcessModule', logger=self.logger)
        
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 20020)
        self.app = FastAPI()
        
        # 设置路由
        self.setup_routes()
    
    def setup_routes(self):
        """设置路由"""
        
        # 用户文本输入
        @self.app.api_route("/agent/chat/input/text/", methods=["POST"])
        async def process_text_input(input_type: str=Form(...), content: str=Form(...)):
            return await self._process_text_input(input_type, content)
        
        
    def _process_text_input(input_type: str, content: str):
        """"""
        pass
    
    def run(self):
        uvicorn.run(self.app, host=self.host, port=self.port)
        
        
def main():
    module = UserTextInputProcessModule()
    module.run()
    

if __name__ == "__main__":
    main()
    
    