# Project:      Agent
# Author:       yomu
# Time:         2024/12/27
# Version:      0.1
# Description:  agent user operation

"""
    负责用户服务，如登录、注册、修改密码、注销账号等
"""

import uvicorn
import httpx
import asyncio
import concurrent.futures
from typing import Dict, List, Any, AsyncGenerator, Optional
from fastapi import FastAPI, Form, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from dotenv import dotenv_values
from contextlib import asynccontextmanager
from pydantic import BaseModel, EmailStr, constr, Field, model_validator
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta

from Module.Utils.Database.UserAccountDataBaseAgent import  UserAccountDataBaseAgent
from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config
from Module.Utils.FastapiServiceTools import (
    get_service_instances,
    update_service_instances_periodically,
    register_service_to_consul,
    unregister_service_from_consul
)

# from Service.Other.EnvironmentManagerClient import EnvironmentManagerClient

# 各种请求的格式要求定义

class RegisterRequest(BaseModel):
    """ 用户注册 request """
    # TODO 待扩展功能，现只提供基础注册
    user_name: str = Field(..., description="用户名，不唯一，有数字后缀")
    account: str = Field(..., min_length=3, max_length=50, description="用户账号，唯一")
    password: str = Field(..., min_length=6, description="用户密码，最少六位")
    email: EmailStr = Field(..., description="用户邮箱")
    

class LoginRequest(BaseModel):
    """ 用户登陆 request """
    identifier: str = Field(min_length=3, max_length=50, description="用户账号或邮箱")
    password: str = Field(..., min_length=6)


class LogoutRequest(BaseModel):
    """ 用户注销账户 request """
    identifier: str = Field(min_length=3, max_length=50, description="用户账号或邮箱")
    password: str = Field(..., min_length=6)


class ModifyPasswordRequest(BaseModel):
    """ 用户修改密码 request"""
    identifier: str = Field(..., description="用户账号或邮箱")
    old_password: str = Field(..., min_length=6, description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码")
    

class ModifyProfileRequest(BaseModel):
    """ 用户修改个人信息 request"""
    account: str
    
class UploadFileRequest(BaseModel):
    """ 用户上传文件 request"""
    account: str
    
class ModifySettingRequest(BaseModel):
    """ 用户修改设置 request"""
    account: str
    

class UserService:
    """
        负责用户服务：
        
            1. 登陆
            2. 注册
            3. 上传文件
            4. 修改账户信息
            5. 注销
    """
    def __init__(self):
        self.logger = setup_logger(name="UserService", log_path="InternalModule")
        
        # 加载环境变量和配置
        self.env_vars = dotenv_values("/home/yomu/agent/Service/Other/.env")
        self.config_path = self.env_vars.get("USER_SERVICE_CONFIG_PATH","")
        self.config = load_config(config_path=self.config_path, config_name='UserService', logger=self.logger)
        
        # 验证配置文件
        required_keys = ["consul_url", "host", "port", "service_name", "service_id", "health_check_url", "jwt"]
        validate_config(required_keys, self.config, self.logger)
        
        # 用户信息数据库
        self.usr_account_database = UserAccountDataBaseAgent()
        
        # 存储服务实例
        self.service_instances: Dict[str, List[Dict]] = {}  # 存储从 Consul 获取的服务实例信息
        
        # Consul URL，确保包含协议前缀
        self.consul_url: str = self.config.get("consul_url", "http://127.0.0.1:8500")
        if not self.consul_url.startswith("http://") and not self.consul_url.startswith("https://"):
            self.consul_url = "http://" + self.consul_url
            self.logger.info(f"Consul URL adjusted to include http://: {self.consul_url}") 
        
        # 微服务本身地址
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 20010)

        # 服务注册信息
        self.service_name = self.config.get("service_name", "UserService")
        self.service_id = self.config.get("service_id", f"{self.service_name}-{self.host}:{self.port}")
        self.health_check_url = self.config.get("health_check_url", f"http://{self.host}:{self.port}/health")
        
        # 加密
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # jwt生成token设置
        self.jwt_secret_key = self.config.get("jwt", {}).get("secret_key", "your_secret_key")
        self.jwt_algorithm = self.config.get("jwt", {}).get("algorithm", "HS256")
        self.jwt_expiration = self.config.get("jwt", {}).get("expiration", 3600)
        
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/usr/login")
        
        # 初始化 httpx.AsyncClient
        self.client = None  # 在lifespan中初始化
        
        # 初始化 FastAPI 应用，使用生命周期管理
        self.app = FastAPI(lifespan=self.lifespan)
        
        # 线程池
        self.executor = concurrent.futures.ThreadPoolExecutor()
        
        # 初始化 EnvironmentManagerClient
        # self.environment_manager_client = EnvironmentManagerClient(
        #     consul_url=self.consul_url,
        #     service_name="EnvironmentManager",
        #     http_client=self.client
        # )
        
        # 设置路由
        self.setup_routes()
    
    
    @asynccontextmanager
    async def lifespan(self, app: FastAPI)-> AsyncGenerator[None, None]:
        """管理应用生命周期"""
        # 应用启动时执行
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(10.0, read=60.0)
        )
        self.logger.info("Async HTTP Client Initialized")
        
        # 先给 task 一个初始值
        task = None
        try:
            # 注册服务到 Consul
            self.logger.info("Registering service to Consul...")
            tags = ["UserService"]
            await register_service_to_consul(consul_url=self.consul_url,
                                             client=self.client,
                                             logger=self.logger,
                                             service_name=self.service_name,
                                             service_id=self.service_id,
                                             address=self.host,
                                             port=self.port,
                                             tags=tags,
                                             health_check_url=self.health_check_url)
            # 异步调用 init_connection，让 usr_account_database 拿到 connect_id
            await self.usr_account_database.init_connection()
            # 启动后台任务
            task = asyncio.create_task(update_service_instances_periodically(
                                            consul_url=self.consul_url,
                                            client=self.client,
                                            service_instances=self.service_instances,
                                            config=self.config,
                                            logger=self.logger
                                        ))
            yield  # 应用正常运行
            
        except Exception as e:
            self.logger.error(f"Exception during lifespan: {e}")
            raise
        
        finally:
            # 关闭后台任务
            # 如果 task 没有赋值过(None)，就不去 cancel
            if task is not None:
                task.cancel()    
                try:
                    await task
                except asyncio.CancelledError:
                    self.logger.info("Background task cancelled successfully.")
                
            # 关闭UserAccountDataBaseAgent中的httpx
            await self.usr_account_database.client.aclose()
            
            # 注销服务从 Consul
            try:
                self.logger.info("Deregistering service from Consul...")
                await unregister_service_from_consul(consul_url=self.consul_url,
                                                     client=self.client,
                                                     logger=self.logger,
                                                     service_id=self.service_id)
                self.logger.info("Service deregistered from Consul.")
            except Exception as e:
                self.logger.error(f"Error while deregistering service: {e}")
                
            # 关闭 AsyncClient
            self.logger.info("Shutting down Async HTTP Client")
            if self.client:
                await self.client.aclose()
                
            # 关闭线程池执行器
            self.logger.info("Shutting down ThreadPoolExecutor")
            self.executor.shutdown(wait=True)           
 
    
    # --------------------------------
    # 6. 请求转发逻辑
    # --------------------------------    
    def setup_routes(self):
        """设置路由"""
        
        @self.app.get("/health")
        async def health_check():
            """健康检查接口"""
            return {"status": "healthy"}
        
        # 用户登录
        @self.app.post("/usr/login")
        async def usr_login(user: LoginRequest):
            return await self._usr_login(user.identifier, user.password)

                
        # 用户注册
        @self.app.post("/usr/register")
        async def usr_register(username: str=Form(...), password: str=Form(...)):
            return await self._usr_register(username, password)
        
        
        # 用户更改密码
        @self.app.post("/usr/change_pwd")
        async def usr_change_pwd(user_id: int = self.get_current_user_id(), new_password: str = Form(...)):
            return await self._usr_change_pwd(user_id, new_password)

        
        # 用户注销
        @self.app.post("/usr/unregister")
        async def usr_unregister(user_id: int = self.get_current_user_id()):
            return await self._usr_unregister(user_id)
        
    
    # --------------------------------
    # 工具函数
    # -------------------------------- 
    def create_access_token(self, user_id: int) -> str:
        """ 生成 JWT token """
        expire = datetime.now() + timedelta(minutes=self.jwt_expiration)
        payload = {
            "user_id": user_id,  # 自定义载荷(用户ID)
            "exp": expire         # 过期时间（必须）
        }
        token = jwt.encode(payload, self.jwt_secret_key, algorithm=self.jwt_algorithm)
        return token    
    
    
    def verify_token(self, token: str) -> int:
        """ 验证 jwt token """
        try:
            payload = jwt.decode(token, self.jwt_secret_key, algorithms=[self.jwt_algorithm])
            user_id = payload.get("user_id")
            if user_id is None:
                raise ValueError("Missing user_id")
            return user_id
        except JWTError:
            raise ValueError("Invalid token")
    
    
    def get_current_user_id(self):
        """ 返回一个Depends(...) 封装依赖 通过token获得user_id"""
        async def _get_current_user_id(token: str = Depends(self.oauth2_scheme)) -> int:
            try:
                return self.verify_token(token)
            except JWTError:
                raise HTTPException(status_code=401, detail="Token 验证失败")
        return Depends(_get_current_user_id)    

        
        
    # --------------------------------
    # 功能函数
    # --------------------------------    
    async def _usr_login(self, identifier: str, password: str):
        """ 
        验证用户登录
        
        返回格式:
            成功:
                {"result": True, "message": message, "token": access_token}
            失败:
                {"result": False, "message": message, "user": identifier}
        """
        
        operator = 'usr_login'
        result = True
        message = f'Login successfully!'
        
        ### 查询数据库
        try:
            # loop = asyncio.get_event_loop()
            # res = await loop.run_in_executor(self.executor, self.usr_account_database.fetch_user_by_name, username)
            res = await self.usr_account_database.fetch_id_and_password_by_email_or_account(identifier=identifier)
        except Exception as e:
            self.logger.error(f"Database error during login for user '{identifier}': {e}")
            # return {"result": False, "message": "Internal server error.", "username": username}
            raise HTTPException(status_code=500, detail="Internal server error.")
        
        self.logger.info(res)
        
        ### 验证
        # 检查用户是否已注册
        if not res:
            result = False
            message = f"Login failed! User: '{identifier}' does not exist!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', User:'{identifier}', Message:'{message}'")
            return {"result": result, "message": message, "user": identifier}

        # 计算客户端传来的密码的hash值
        password_hash = self.pwd_context.hash(password)
        
        # 用户内部ID 和保存的密码hash
        user_id, stored_password_hash = res
        
        # 密码错误
        if stored_password_hash != password_hash:
            result = False
            message = "Login failed! Invalid account or password!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', User:'{identifier}', Message:'{message}'")
            return {"result": result, "message": message, "user": identifier}

        ### 生成token
        access_token = self.create_access_token(user_id=user_id)

        ### 返回token
        self.logger.info(f"Operator:'{operator}', Result:True, Message:'Login successful!', User ID: {user_id}, Token:'{access_token}'")
        return {"result": True, "message": "Login successful!", "token": access_token}
            
    
    async def _usr_register(self, username: str, password: str):
        """用户注册"""
        operator = 'usr_register'
        try:
            # loop = asyncio.get_event_loop()
            # res = await loop.run_in_executor(self.executor, self.usr_account_database.fetch_user_by_name, username)
            res = await self.usr_account_database.fetch_user_by_name(username)
        except Exception as e:
            self.logger.error(f"Database error during registration for user '{username}': {e}")
            return {"result": False, "message": "Internal server error.", "username": username}
        
        result = True
        message = 'Register successfully!'
        
        # 如果已注册
        if res:
            result = False
            message = f"Register failed! Username '{username}' already exists!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}  
        
        # 注册
        try:
            # res = await loop.run_in_executor(self.executor, self.usr_account_database.insert_user_info, username, password)
            res = await self.usr_account_database.insert_user_info(username, password)
        except Exception as e:
            self.logger.error(f"Database error during inserting user '{username}': {e}")
            return {"result": False, "message": "Internal server error.", "username": username}
        
        # 注册成功
        if res:
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}
            # TODO: 添加数据库插入逻辑
            
            # 将来调用 EnvironmentManager
            # env_data = {"username": username}
            # try:
            #     env_response = await environment_manager_client.call_endpoint("initialize_environment", env_data)
            #     print(env_response)
            # except Exception as e:
            #     raise HTTPException(status_code=500, detail="Failed to initialize user environment.")
        
        else:
            result = False
            message = f"Register failed! Inserting username '{username}' to database failed!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}
        
        
    async def _usr_change_pwd(self, user_id: int, new_password: str):
        """用户更改密码"""
        operator = 'usr_change_pwd'
        result = True
        message = 'Change password successful!'
        
        # 更新密码
        try:
            # loop = asyncio.get_event_loop()
            # res = await loop.run_in_executor(self.executor, self.usr_account_database.update_user_password, username, password)
            res = await self.usr_account_database.update_user_password(username, password)
        except Exception as e:
            self.logger.error(f"Database error during password update for user '{username}': {e}")
            return {"result": False, "message": "Internal server error.", "username": username}
        
        # 成功更新密码
        if res:
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}
        else:
            result = False
            message = f"Change password failed! Username '{username}' update in database failed!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}

    
    async def _usr_unregister(self, user_id: int):
        """用户注销账户"""
        operator = 'usr_unregister'
        # try:
        #     loop = asyncio.get_event_loop()
        #     res = await loop.run_in_executor(self.executor, self.usr_account_database.delete_user, username, password)
        # except Exception as e:
        #     self.logger.error(f"Database error during unregistration for user '{username}': {e}")
        #     raise HTTPException(status_code=500, detail="Internal server error.")
        
        # if res:
        #     message = 'Unregistration successful.'
        #     self.logger.info(f"Operator:'{operator}', Result:'True', Username:'{username}', Message:'{message}'")
        #     return {"result": True, "message": message, "username": username}
        # else:
        #     message = 'Unregistration failed. Invalid credentials or user does not exist.'
        #     self.logger.info(f"Operator:'{operator}', Result:'False', Username:'{username}', Message:'{message}'")
        #     raise HTTPException(status_code=400, detail=message)
        
        
        
    def run(self):
            uvicorn.run(self.app, host=self.host, port=self.port)
            
        
 
def main():
    service = UserService()
    service.run()
    
    
if __name__ == "__main__":
    main()
    
    