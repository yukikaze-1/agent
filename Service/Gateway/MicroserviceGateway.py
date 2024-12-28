# Project:      Agent
# Author:       yomu
# Time:         2024/12/12
# Version:      0.1
# Description:  agent Microservice Gateway

"""
    负责agent与用户客户端的通信
    运行前请 export PYTHONPATH=/home/yomu/agent:$PYTHONPATH
"""

import os
import uvicorn
import httpx  # 用于服务间通信
from fastapi import FastAPI, File, HTTPException, Form, Request, Response
from datetime import datetime
from typing import Dict
from dotenv import dotenv_values

from Module.Utils.Logger import setup_logger
from Module.Utils.LoadConfig import load_config


class MicroserviceGateway():
    """
        微服务网关
    """
    def __init__(self):
        self.logger = setup_logger(name="MicroserviceGateway", log_path="Other") 
        
        self.env_vars = dotenv_values("/home/yomu/agent/Service/Gateway/.env")
        self.config_path = self.env_vars.get("MICRO_SERVICE_GATEWAY_CONFIG_PATH","")
        self.config = load_config(config_path=self.config_path, config_name='MicroserviceGateway', logger=self.logger)
        
        # 微服务的路由表（内部服务间通信）
        self.internal_routes = self.config["internal_routes"]
        self.host = self.config.get("host", "0.0.0.0")
        self.port = self.config.get("port", 20000)
        self.app = FastAPI()
        
        # 设置路由
        self.setup_routes()

        
    def setup_routes(self):
        """设置 API 路由"""

            
        # 聊天
        @self.app.api_route("/agent/chat/{path:path}", methods=["Post"])
        async def chat_service_proxy(request: Request, path: str):
            pass
            
        
        # 用户测试服务器连通性
        @self.app.post("/option/ping/")
        async def usr_ping_server(time: str=Form(...), client_ip: str=Form(...)):
            return await self._usr_ping_server(time, client_ip)
        
        # 用户更改设置
        @self.app.post("/agent/setting/change/")
        async def usr_change_setting():
            return await self._usr_change_setting()
        
        # 用户的文本输入
        @self.app.post("/agent/input/text/")
        async def usr_text_input():
            return await self._usr_text_input()
        
        # 用户的语音输入
        @self.app.post("/agent/input/audio/")
        async def usr_audio_input():
            return await self._usr_audio_input()
        
        # 用户的语音输入
        @self.app.post("/agent/input/audio_streaming/")
        async def usr_audio_streaming_input():
            return await self._usr_audio_streaming_input()
        
        # 用户的图片输入
        @self.app.post("/agent/input/picture/")
        async def usr_picture_input():
            return await self._usr_picture_input()
        
        # 用户的视频文件输入
        @self.app.post("/agent/input/video/")
        async def usr_video_input():
            return await self._usr_video_input()
        
        # 用户的实时视频流输入
        @self.app.post("/agent/input/video_streaming/")
        async def usr_video_streaming_input():
            return await self._usr_video_streaming_input()
    
        
     
    async def _usr_ping_server(self, time: str, client_ip: str):
        """接受用户端发来的ping，回送服务器信息"""         
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"Ping success."
        self.logger.info(f"Operator: usr_ping_server. Result: True, Message: {message}")
        return {"result": True, "message": message, "time": current_time}
    
    async def _usr_change_setting(self):
        """接受用户发来的选项配置信息"""
        pass
    
    async def _usr_text_input(self):
        """接受用户在聊天框中发送的文本信息"""
        pass
    
    async def _usr_audio_input(self):
        """接受用户的语音输入"""
        pass
    
    async def _usr_audio_streaming_input(self):
        """接受用户的实时语音流输入"""
        pass
    
    async def _usr_picture_input(self):
        """接受用户的图片输入"""
        pass
    
    async def _usr_video_input(self):
        """接受用户的视频文件输入"""
        pass
    
    async def _usr_video_streaming_input(self):
        """接受用户的实时视频流输入"""
        pass
    
    async def _usr_file_input(self):
        """接受用户的文件输入"""
        pass
        
    def __del__(self):
        pass
    
    def run(self):
        uvicorn.run(self.app, host=self.host, port=self.port)
    

def main():
    server = MicroserviceGateway()
    server.run()
    
    
if __name__ == "__main__":
    main()
    