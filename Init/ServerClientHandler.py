# Project:      Agent
# Author:       yomu
# Time:         2024/12/12
# Version:      0.1
# Description:  agent network initialize

"""
    负责agent与用户客户端的通信
    运行前请 export PYTHONPATH=/home/yomu/agent:$PYTHONPATH
"""

import os
import uvicorn
import argparse
import yaml
from fastapi import FastAPI, File, HTTPException, Form
from datetime import datetime
from logging import Logger
from typing import Dict
from dotenv import dotenv_values

from Module.Utils.Logger import setup_logger
from UserAccountDataBaseInit import  UserAccountDataBase


class ServerClientHandler():
    """
        负责agent与用户客户端的通信的类
    """
    def __init__(self, logger: Logger=None):
        
        self.logger = logger or setup_logger(name="ServerClientHandler", log_path="InternalModule") 
        
        self.env_vars = dotenv_values("Init/.env")
        self.config_path = self.env_vars.get("INIT_CONFIG_PATH","")
        if not self.config_path :
            self.logger.error(f"ServerClientHandler: INIT_CONFIG_PATH environment variable not set.")
            raise ValueError(f"INIT_CONFIG_PATH environment variable not set.")
        
        self.config = self._load_config(config_path=self.config_path)
        
        self.host = self.config["server_host"]
        self.port = self.config["server_port"]
        self.app = FastAPI()
        self.usr_account_database = UserAccountDataBase()
        
        # 设置路由
        self.setup_routes()
        
        
    def _load_config(self, config_path: str) -> Dict:
        """从config_path中读取配置(*.yml)
            
            返回：
                yml文件中配置的字典表示
        """
        if config_path is None:
            self.logger.error(f"ServerClientHandler: Config file {config_path} is empty.Please check the file 'Init/.env'.It should set the 'INIT_CONFIG_PATH'")
            raise ValueError(f"Config file {config_path} is empty.Please check the file 'Init/.env'.It should set the 'INIT_CONFIG_PATH'")
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)  # 使用 safe_load 安全地加载 YAML 数据
                res = config["ServerClientHandler"]
            return res
        except FileNotFoundError:
            self.logger.error(f"ServerClientHandler: Config file {config_path} not found.")
            raise FileNotFoundError(f"Config file {config_path} not found.")
        except yaml.YAMLError as e:
            self.logger.error(f"ServerClientHandler: Error parsing the YAML config file: {e}")
            raise ValueError(f"Error parsing the YAML config file: {e}")
        
        
    def setup_routes(self):
        """设置 API 路由"""
        
        # 用户登录
        @self.app.post("/usr/login/")
        async def usr_login(username: str=Form(...), password: str=Form(...)):
            return await self._usr_login(username, password)
        
        # 用户注册
        @self.app.post("/usr/signup/")
        async def usr_signup(username: str=Form(...), password: str=Form(...)):
            return await self._usr_signup(username, password)
        
        # 用户更改密码
        @self.app.post("/usr/change_pwd/")
        async def usr_change_pwd(username: str=Form(...), password: str=Form(...)):
            return await self._usr_change_pwd(username, password)
        
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
    
    async def _usr_login(self, username:str, password: str):
        """验证用户登录"""
        res = self.usr_account_database.fetch_user_by_name(username)
        operator = 'usr_login'
        result = True
        message = 'Login successfully!'
        
        # 检查用户是否已注册
        if not res:
            result=False
            message=f'Login failed! Username "{username}" not exist!'
            self.logger.info(f"ServerClientHandler: Operator:{operator}, Result:{result}, Username:{username}, Message:{message}")
            return {"result": result, "message": message, "username": username}
        
        # 验证用户名和密码是否匹配
        if password != res["password"] :
            result=False
            message="Login failed! Invalid username or password!"
            self.logger.info(f"ServerClientHandler: Operator:{operator}, Result:{result}, Username:{username}, Message:{message}")
            return {"result": result ,"message": message, "username": username}  
            
        self.logger.info(f"ServerClientHandler: Operator:{operator}, Result:{result}, Username:{username}, Password:{password}, Message:{message}")
        return {"result": result ,"message": message, "username": username}    
            
    
    async def _usr_signup(self, username: str, password: str):
        """用户注册"""
        res = self.usr_account_database.fetch_user_by_name(username)
        
        operator = 'usr_signup'
        result=True
        message='Signup successfully!'
        
        # 如果已注册
        if res:
            result=False
            message=f"Signup failed! Username '{username}' is already exist!"
            self.logger.info(f"ServerClientHandler: Operator:{operator}, Result:{result}, Username:{username}, Message:{message}")
            return {"result": result, "message": message, "username": username}  
        
        # 注册
        res = self.usr_account_database.insert_user_info(username, password)
        
        # 注册成功
        if res:
            self.logger.info(f"ServerClientHandler: Operator:{operator}, Result:{result}, Username:{username}, Password:{password}, Message:{message}")
            return {"result": result, "message": message, "username": username}
        else:
            result=False
            message=f"Signup failed! Username '{username}' insert to database failed!"
            self.logger.info(f"ServerClientHandler: Operator:{operator}, Result:{result}, Username:{username}, Password:{password}, Message:{message}")
            return {"result": result, "message": message, "username": username}
    
    
    async def _usr_change_pwd(self, username: str, password: str):
        """用户更改密码"""
        operator = 'usr_change_pwd'
        result = True
        message = 'Change password successful!'
        
        #更新密码
        res = self.usr_account_database.update_user_password(username, new_password=password)
        
        # 成功更新密码
        if res:
            self.logger.info(f"ServerClientHandler: Operator:{operator}, Result:{result}, Username:{username}, Password:{password}, Message:{message}")
            return {"result": result, "message": message, "username": username}
        else:
            result=False
            message=f"Change password failed! Username '{username}' Update to database failed!"
            self.logger.info(f"ServerClientHandler: Operator:{operator}, Result:{result}, Username:{username}, Password:{password}, Message:{message}")
            return {"result": result, "message": message, "username": username}
     
     
    async def _usr_ping_server(self, time: str, client_ip: str):
        """接受用户端发来的ping，回送服务器信息"""         
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"Ping success."
        self.logger.info(f"ServerClientHandler: Operator: usr_ping_server. Result: True, Message: {message}")
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
    
    def run(self):
        uvicorn.run(self.app, host=self.host, port=self.port)

    def __del__(self):
        pass
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentFastAPI Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="服务器主机地址")
    parser.add_argument("--port", type=int, default=20000, help="服务器端口")
    args = parser.parse_args()

    server = ServerClientHandler(host=args.host, port=args.port)
    server.run()