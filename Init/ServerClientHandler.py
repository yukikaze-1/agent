# Project:      Agent
# Author:       yomu
# Time:         2024/12/12
# Version:      0.1
# Description:  agent network initialize

"""
    负责agent与用户客户端的通信
"""

import os
import uvicorn
import argparse
from fastapi import FastAPI, File, HTTPException, Form
from datetime import datetime
from dotenv import dotenv_values

from UserAccountDataBaseInit import UserAccountDataBase

class ServerClientHandler():
    """
        负责agent与用户客户端的通信的类
    """
    # TODO 修改host和port，让其在config.yml中配置
    def __init__(self, host: str = "0.0.0.0", port: int = 20000):
        self.host = host
        self.port = port
        self.app = FastAPI()
        self.usr_account_database = UserAccountDataBase()
        
        # 设置路由
        self.setup_routes()
        
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
        @self.app.post("/usr/changepwd/")
        async def usr_change_pwd(username: str=Form(...), new_password: str=Form(...)):
            return await self._usr_change_pwd(username, new_password)
        
        # 用户更改设置
        @self.app.post("/agent/setting/")
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
        # 检查用户是否已注册
        if not self.usr_account_database.query(username):
            raise HTTPException(status_code=401, detail="Account does not exist!")  # 返回 401 未授权错误
        
        # 验证用户名和密码是否匹配
        stored_password = self.usr_account_database.query(username)
        if stored_password != password:
            raise HTTPException(status_code=401, detail="Invalid username or password!")  # 返回错误提示 
        
        # 登录成功
        return {"message": "Login successful!", "username": username}    
    
    async def _usr_signup(self, username: str, password: str):
        """用户注册"""
        # 检查用户是否已注册
        if not self.usr_account_database.query(username):
            raise HTTPException(status_code=401, detail="Account is already exist!")  # 返回 401 未授权错误
        
        # 注册账户
        self.usr_account_database.insert(username, password)
        return {"message": "Signup successfully!", "username": username}
    
    async def _usr_change_pwd(self, username: str, new_password: str):
        """用户更改密码"""
        try:
            self.usr_account_database.modify(key=username, new_value=new_password)
            return {"message": "Change password successful!", "username": username} 
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error changing password: {str(e)}")
             
    
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
    parser = argparse.ArgumentParser(description="SenseVoice FastAPI Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="服务器主机地址")
    parser.add_argument("--port", type=int, default=20000, help="服务器端口")
    args = parser.parse_args()

    server = ServerClientHandler(host=args.host, port=args.port)
    server.run()