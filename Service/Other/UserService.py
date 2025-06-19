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
from fastapi import FastAPI, Form, HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from dotenv import dotenv_values
from contextlib import asynccontextmanager
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
from Module.Utils.Database.RequestType import (
    RegisterRequest,
    LoginRequest,
    UnregisterRequest,
    ModifyPasswordRequest,
    ModifyProfileRequest,
    UploadFileRequest,
    ModifySettingRequest,
    ModifyNotificationSettingsRequest
)
from Module.Utils.Database.ResponseType import (
    RegisterResponse,
    LoginResponse,
    LogoutResponse,
    ModifyPasswordResponse,
    ModifyProfileResponse,
    UploadFileResponse,
    ModifySettingResponse,
    ModifyNotificationSettingsResponse
)

# from Service.Other.EnvironmentManagerClient import EnvironmentManagerClient

    

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
        
        # 健康检查接口
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy"}
        
        # 用户登录
        @self.app.post("/usr/login")
        async def usr_login(user: LoginRequest, request: Request):
            ip_address = request.
            return await self._usr_login(user.identifier, user.password, user.agent, user.device, user.os)
                
        # 用户注册
        @self.app.post("/usr/register")
        async def usr_register(user: RegisterRequest, request: Request):
            return await self._usr_register(user.user_name, user.account, user.password, user.email)

        # 用户更改密码
        @self.app.post("/usr/change_pwd")
        async def usr_change_pwd(data: ModifyPasswordRequest, request: Request):
            return await self._usr_change_pwd(data.session_token, data.new_password)

        # 用户注销
        @self.app.post("/usr/unregister")
        async def usr_unregister(data: UnregisterRequest, request: Request):
            return await self._usr_unregister(data.session_token)

        # 用户修改个人信息
        @self.app.post("/usr/modify_profile")
        async def usr_modify_profile(data: ModifyProfileRequest, request: Request):
            return await self._usr_modify_profile(data.session_token, data.user_name, data.profile_picture_url, data.signature)

        # 用户修改通知设置
        @self.app.post("/usr/modify_notifications")
        async def usr_modify_notification_settings(data: ModifyNotificationSettingsRequest, request: Request):
            return await self._usr_modify_notification_settings(data.session_token, data.notifications_enabled)

        # 用户修改个人设置
        @self.app.post("/usr/modify_settings")
        async def usr_modify_settings(data: ModifySettingRequest, request: Request):
            return await self._usr_modify_settings(data.session_token, data.account)

        # 用户上传文件
        @self.app.post("/usr/upload_file")
        async def usr_upload_file(data: UploadFileRequest, request: Request):
            return await self._usr_upload_file(data.session_token, data.file)

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
        """
        验证 jwt token 
        从token 中获取user_id

        :param token: JWT token

        :return: 用户ID
        """
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


    def get_client_ip(self, request: Request) -> str:
        return request.headers.get("x-forwarded-for", "unknown").split(",")[0].strip()
    
        
    # --------------------------------
    # 功能函数
    # --------------------------------    
    async def _usr_login(self, identifier: str,
                         password: str,
                         ip_address: str,
                         agent: str,
                         device: str,
                         os: str) -> Dict:
        """ 
        验证用户登录

        :param identifier: 用户名或邮箱
        :param password: 密码
        :param ip_address: 用户IP地址
        :param agent: 用户客户端版本
        :param device: 设备信息
        :param os: 操作系统信息

        返回格式:
            成功:
                {"operator": "usr_login", "result": True, "message": message, "token": access_token}
            失败:
                {"operator": "usr_login", "result": False, "message": message, "user": identifier}
        """
        
        operator = 'usr_login'
        result = True
        message = f'Login successfully!'
        
        # 1. 查询数据库
        try:
            # loop = asyncio.get_event_loop()
            # res = await loop.run_in_executor(self.executor, self.usr_account_database.fetch_user_by_name, username)
            res = await self.usr_account_database.fetch_user_id_and_password_by_email_or_account(identifier=identifier)
               
        except Exception as e:
            self.logger.error(f"Database error during login for user '{identifier}': {e}")
            raise HTTPException(status_code=500, detail="Internal server error.")

        self.logger.info(res)

        # 2. 验证
        # 检查用户是否已注册
        if res is None:
            result = False
            message = f"Login failed! User: '{identifier}' does not exist!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', User:'{identifier}', Message:'{message}'")
            return {"result": result, "message": message, "user": identifier}
        
        # 用户内部ID 和保存的密码hash
        user_id, stored_password_hash = res
        
        # 密码错误
        if not self.pwd_context.verify(password, stored_password_hash):
            # 登录失败log插入
            result = False
            message = f"Login failed! Invalid account or password!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', User:'{identifier}', Message:'{message}'")
            try:
                res_insert_user_login_logs = await self.usr_account_database.insert_user_login_logs(
                    user_id=user_id,
                    ip_address=ip_address,
                    agent=agent,
                    device=device,
                    os=os,
                    login_success=False
                )
            except Exception as e:
                self.logger.error(f"Failed to insert login log for user {user_id}: {e}")
                return {"result": False, "message": message, "user": identifier}
            
            self.logger.info(f"Operator:'{operator}', Result:'{result}', User:'{identifier}', Message:'{message}'")
            return {"result": False, "message": message, "user": identifier}

        # 3. 生成token
        access_token = self.create_access_token(user_id=user_id)

        # 4. 将token更新到 users 表
        update_data = {"access_token": access_token}
        where_conditions =["user_id = %s"]
        where_values = [user_id]
        try:
            res_update = await self.usr_account_database.mysql_helper.update_one(table="users", data=update_data,
                                                         where_conditions=where_conditions,
                                                         where_values=where_values)
        except Exception as e:
            self.logger.error(f"Token update error for user {user_id}: {e}")
        
        if res_update:
            self.logger.info(f"Operator:'{operator}', Result:True, Message:'Token updated successfully!', User ID: {user_id}")
        else:
            self.logger.warning(f"Operator:'{operator}', Result:False, Message:'Token update failed!', User ID: {user_id}")

        # 5. 生成登入log，插入user_login_logs 表中
        try:
            res_insert = await self.usr_account_database.insert_user_login_logs(
                user_id=user_id,
                ip_address=ip_address,
                agent=agent,
                device=device,
                os=os,
                login_success=True
            )
        except Exception as e:
            self.logger.error(f"Failed to insert login log for user {user_id}: {e}")
            
        if res_insert:
            self.logger.info(f"Operator:'{operator}', Result:True, Message:'Login log inserted successfully!', User ID: {user_id}")
        else:
            self.logger.warning(f"Operator:'{operator}', Result:False, Message:'Login log insertion failed!', User ID: {user_id}")

        # 6. 返回token
        self.logger.info(f"Operator:'{operator}', Result:True, Message:'Login successful!', User ID: {user_id}")
        return {"result": True, "message": "Login successful!", "token": access_token}


    async def _usr_register(self, user_name: str, account: str, password: str, email: str):
        """
        用户注册

        :param user_name: 用户名
        :param account: 用户账号
        :param password: 用户密码
        :param email: 用户邮箱

        :返回格式: {
            "operator": "usr_register",
            "result": bool,
            "message": str,
            "data": Any
        }
        """
        
        operator = 'usr_register'
        
        # 1. 检查是否已被注册        
        # 先通过email查询
        try:
            # loop = asyncio.get_event_loop()
            # res = await loop.run_in_executor(self.executor, self.usr_account_database.fetch_user_by_name, username)
            res_email = await self.usr_account_database.fetch_user_id_and_password_by_email_or_account(
                identifier=email
            )
        except Exception as e:
            self.logger.error(f"Database error during registration for user '{email}': {e}")
            return {"result": False, "message": "Internal server error.", "username": user_name}
        
        # 如果已注册
        if res_email:
            result = False
            message = f"Register failed! Email '{email}' already exists!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Email:'{email}', Message:'{message}'")
            return {"result": result, "message": message, "email": email}

        # 再通过account查询
        try:
            # loop = asyncio.get_event_loop()
            # res = await loop.run_in_executor(self.executor, self.usr_account_database.fetch_user_by_name, username)
            res_account = await self.usr_account_database.fetch_user_id_and_password_by_email_or_account(
                identifier=account
            )
        except Exception as e:
            self.logger.error(f"Database error during registration for user '{account}': {e}")
            return {"result": False, "message": "Internal server error.", "username": user_name}
        
        # 如果已注册
        if res_account:
            result = False
            message = f"Register failed! Account '{account}' already exists!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Account:'{account}', Message:'{message}'")
            return {"result": result, "message": message, "account": account}

        # 2. 注册
        try:
            # res = await loop.run_in_executor(self.executor, self.usr_account_database.insert_user_info, username, password)
            res_insert_new_user = await self.usr_account_database.insert_new_user(
                user_name=user_name,
                account=account,
                password_hash=self.pwd_context.hash(password),
                email=email
            )
        except Exception as e:
            self.logger.error(f"Database error during inserting user '{user_name}': {e}")
            return {"result": False, "message": "Internal server error.", "username": user_name}

        # 注册成功
        if res_insert_new_user:
            self.logger.info(f"Operator:'{operator}', Result: True, Username:'{user_name}', Message:")
            return {"result": True, "message": "User registered successfully.", "username": user_name} 
            # TODO 将来调用 EnvironmentManager
            # env_data = {"username": username}
            # try:
            #     env_response = await environment_manager_client.call_endpoint("initialize_environment", env_data)
            #     print(env_response)
            # except Exception as e:
            #     raise HTTPException(status_code=500, detail="Failed to initialize user environment.")
        
        else:
            result = False
            message = f"Register failed! Inserting user '<{user_name}> <{account}> <{email}>' to database failed!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{user_name}', Message:'{message}'")
            return {"result": result, "message": message, "username": user_name}

        
    async def _usr_change_pwd(self, session_token: str, new_password: str) -> Dict:
        """
        用户更改密码

        :param session_token: 用户的session token
        :param new_password: 新密码
        
        返回格式:
            成功:
                {"operator": "usr_change_pwd", "result": True, "message": message}
            失败:
                {"operator": "usr_change_pwd", "result": False, "message": message}
        """
        operator = 'usr_change_pwd'
        result = False
        
        # 1. 获取user_id
        user_id = self.verify_token(token=session_token)
        
        # 2. 计算password hash
        new_password_hash = self.pwd_context.hash(new_password)

        # 3. 更新密码hash到 users表中
        try:
            # loop = asyncio.get_event_loop()
            # res = await loop.run_in_executor(self.executor, self.usr_account_database.update_user_password, username, password)
            result = await self.usr_account_database.update_user_password_by_user_id(
                user_id=user_id, new_password_hash=new_password_hash
            )
        except Exception as e:
            message = f"Database error during password update for user id'{user_id}': {e}"
            self.logger.error(message)
            return {"result": False, "message": "Internal server error.", "user_id": user_id}

        if result:
            self.logger.info(f"Password updated successfully for user id'{user_id}'")
        else:
            message = f"Password update failed for user id'{user_id}'"
            self.logger.error(message)
            return {"result": False, "message": "Internal server error.", "user_id": None}

        # 4. 插入 log 到 user_account_actions 中
        action_data = {
            "user_id": user_id,
            "action_type": "change_password",
            "action_detail": "Changed password.",
        }
        try:
            await self.usr_account_database.mysql_helper.insert_one(table="user_account_actions", data=action_data)
        except Exception as e:
            self.logger.error(f"Database error during action log insert for user id'{user_id}': {e}")

        if result:
            message = f"Change password successful! User ID '{user_id}'"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', User ID:'{user_id}', Message:'{message}'")
            return {"result": result, "message": message, "user_id": user_id}
        else:
            message = f"Change password failed! User ID '{user_id}' update in database failed!"
            self.logger.warning(f"Operator:'{operator}', Result:'{result}', User ID:'{user_id}', Message:'{message}'")
            return {"result": result, "message": message, "user_id": user_id}

    
    async def _usr_unregister(self, session_token: str) -> Dict:
        """
        用户注销账户

        :param session_token: 用户的session token

        """
        operator = 'usr_unregister'
        
        # 1. 解析出user_id
        user_id = self.verify_token(token=session_token)

        # 2. 删除数据库对应条目(软删除)
        try:
            await self.usr_account_database.soft_delete_user_by_user_id(user_id=user_id)
        except Exception as e:
            self.logger.error(f"Database error during unregistration for user id'{user_id}': {e}")
            return {"result": False, "message": "Internal server error.", "user_id": user_id}

        # 3. 返回结果
        message = f"Unregistration successful! User ID '{user_id}'"
        self.logger.info(f"Operator:'{operator}', Result:'True', User ID:'{user_id}', Message:'{message}'")
        
        return {"result": True, "message": message, "user_id": user_id}
    
        
        # if res:
        #     message = 'Unregistration successful.'
        #     self.logger.info(f"Operator:'{operator}', Result:'True', Username:'{username}', Message:'{message}'")
        #     return {"result": True, "message": message, "username": username}
        # else:
        #     message = 'Unregistration failed. Invalid credentials or user does not exist.'
        #     self.logger.info(f"Operator:'{operator}', Result:'False', Username:'{username}', Message:'{message}'")
        #     raise HTTPException(status_code=400, detail=message)
        
        
    async def _usr_modify_profile(self, session_token: str, user_name: str,
                                  profile_picture_url: str, signature: str) -> Dict:
        """
        用户修改个人信息
        """
        operator = 'usr_modify_profile'

        # 1. 解析出user_id
        user_id = self.verify_token(token=session_token)

        # 2. 更新数据库对应条目
        try:
            await self.usr_account_database.update_user_profile(
                user_id=user_id,
                user_name=user_name,
                profile_picture_url=profile_picture_url,
                signature=signature
            )
        except Exception as e:
            self.logger.error(f"Database error during profile update for user id'{user_id}': {e}")
            return {"result": False, "message": "Internal server error.", "user_id": user_id}

        # 3. 返回结果
        message = f"Profile update successful! User ID '{user_id}'"
        self.logger.info(f"Operator:'{operator}', Result:'True', User ID:'{user_id}', Message:'{message}'")

        return {"result": True, "message": message, "user_id": user_id}


    async def _usr_modify_notification_settings(self, session_token: str, notifications_enabled: bool) -> Dict:
        """
        用户修改通知设置
        """
        operator = 'usr_modify_notification_settings'

        # 1. 解析出user_id
        user_id = self.verify_token(token=session_token)

        # 2. 更新数据库对应条目
        try:
            await self.usr_account_database.update_user_notification_settings(
                user_id=user_id,
                notifications_enabled=notifications_enabled
            )
        except Exception as e:
            self.logger.error(f"Database error during notification settings update for user id'{user_id}': {e}")
            return {"result": False, "message": "Internal server error.", "user_id": user_id}

        # 3. 返回结果
        message = f"Notification settings update successful! User ID '{user_id}'"
        self.logger.info(f"Operator:'{operator}', Result:'True', User ID:'{user_id}', Message:'{message}'")

        return {"result": True, "message": message, "user_id": user_id}


    async def _usr_modify_settings(self, session_token: str, account: str) -> Dict:
        """
        用户修改设置
        """
        operator = 'usr_modify_settings'

        # 1. 解析出user_id
        user_id = self.verify_token(token=session_token)

        # 2. 更新数据库对应条目
        try:
            await self.usr_account_database.update_user_settings(
                user_id=user_id,
                account=account
            )
        except Exception as e:
            self.logger.error(f"Database error during settings update for user id'{user_id}': {e}")
            return {"result": False, "message": "Internal server error.", "user_id": user_id}

        # 3. 返回结果
        message = f"Settings update successful! User ID '{user_id}'"
        self.logger.info(f"Operator:'{operator}', Result:'True', User ID:'{user_id}', Message:'{message}'")

        return {"result": True, "message": message, "user_id": user_id}


    async def _usr_upload_file(self, session_token: str, file: bytes) -> Dict:
        """
        用户上传文件
        """
        operator = 'usr_upload_file'

        # 1. 解析出user_id
        user_id = self.verify_token(token=session_token)

        # 2. 上传文件到云存储
        try:
            file_id = await self.file_storage.upload_file(file)
            await self.usr_account_database.save_user_file(user_id=user_id, file_id=file_id)
        except Exception as e:
            self.logger.error(f"File upload error for user id'{user_id}': {e}")
            return {"result": False, "message": "Internal server error.", "user_id": user_id}

        # 3. 返回结果
        message = f"File upload successful! User ID '{user_id}', File ID '{file_id}'"
        self.logger.info(f"Operator:'{operator}', Result:'True', User ID:'{user_id}', File ID:'{file_id}', Message:'{message}'")

        return {"result": True, "message": message, "user_id": user_id, "file_id": file_id}
    
    
    def run(self):
        uvicorn.run(self.app, host=self.host, port=self.port)
            
        
 
def main():
    service = UserService()
    service.run()
    
    
if __name__ == "__main__":
    main()
    
    