# Project:      Agent
# Author:       yomu
# Time:         2024/12/27
# Version:      0.1
# Description:  agent user operation

"""
    负责用户服务，如登录、注册、修改密码、注销账号等
"""

import json
import httpx
import uvicorn
from fastapi import FastAPI, File, Form
from dotenv import dotenv_values


from Module.Utils.Database.UserAccountDataBaseAgent import  UserAccountDataBaseAgent
from Module.Utils.Logger import setup_logger
from Module.Utils.LoadConfig import load_config


class UserService:
    """
        负责用户服务：
        
            1. 登陆
            2. 注册
            3. 修改密码
            4. 登出
            5. 注销
    """
    def __init__(self):
        self.logger = setup_logger(name="UserService", log_path="InternalModule")
        
        self.env_vars = dotenv_values("/home/yomu/agent/Service/Other/.env")
        self.config_path = self.env_vars.get("USER_SERVICE_CONFIG_PATH","")
        self.config = load_config(config_path=self.config_path, config_name='UserService', logger=self.logger)
        
        self.usr_account_database = UserAccountDataBaseAgent(logger=self.logger)
        
        self.host = self.config.get("host", "0.0.0.0")
        self.port = self.config.get("port", 20010)
        self.app = FastAPI()
        
        # 设置路由
        self.setup_routes()
        
        
    def setup_routes(self):
        """设置路由"""
        
        # 用户登录
        @self.app.post("/usr/login/")
        async def usr_login(username: str=Form(...), password: str=Form(...)):
            return await self._usr_login(username, password)

                
        # 用户注册
        @self.app.post("/usr/register/")
        async def usr_register(username: str=Form(...), password: str=Form(...)):
            return await self._usr_register(username, password)
        
        
        # 用户更改密码
        @self.app.post("/usr/change_pwd/")
        async def usr_change_pwd(username: str=Form(...), password: str=Form(...)):
            return await self._usr_change_pwd(username, password)
        
        
        # 用户登出
        @self.app.post("/usr/logout/")
        async def usr_logout(username: str=Form(...)):
            return await self._usr_logout(username)
        
        
        # 用户注销
        @self.app.post("/usr/unregister/")
        async def usr_unregister(username: str=Form(...), password: str=Form(...)):
            return await self._usr_unregister(username, password)
        
        
    async def _usr_login(self, username:str, password: str):
        """验证用户登录"""
        res = self.usr_account_database.fetch_user_by_name(username)
        operator = 'usr_login'
        result = True
        message = 'Login successfully!'
        
        # 检查用户是否已注册
        if not res:
            result=False
            message=f"Login failed! Username '{username}' not exist!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}
        
        # 验证用户名和密码是否匹配
        if password != res["password"] :
            result=False
            message="Login failed! Invalid username or password!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
            return {"result": result ,"message": message, "username": username}  
            
        self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Password:'{password}', Message:'{message}'")
        return {"result": result ,"message": message, "username": username}    
            
    
    async def _usr_register(self, username: str, password: str):
        """用户注册"""
        res = self.usr_account_database.fetch_user_by_name(username)
        
        operator = 'usr_register'
        result=True
        message='register successfully!'
        
        # 如果已注册
        if res:
            result=False
            message=f"register failed! Username ''{username}'' is already exist!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}  
        
        # 注册
        res = self.usr_account_database.insert_user_info(username, password)
        
        # 注册成功
        if res:
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Password:'{password}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}
        else:
            result=False
            message=f"register failed! Username ''{username}'' insert to database failed!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Password:'{password}', Message:'{message}'")
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
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Password:'{password}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}
        else:
            result=False
            message=f"Change password failed! Username ''{username}'' Update to database failed!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Password:'{password}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}


    async def _usr_logout(self, username: str):
        """用户登出"""
        pass
    
    
    async def _usr_unregister(self, username: str, password: str):
        """用户注销账户"""
        pass
    
    def run(self):
        uvicorn.run(self.app, host=self.host, port=self.port)
        
        
def main():
    service = UserService()
    service.run()
    
    
if __name__ == "__main__":
    main()
    
    