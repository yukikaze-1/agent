# Project:      Agent
# Author:       yomu
# Time:         2024/12/27
# Version:      0.2 (Refactored to use split Agents)
# Description:  agent user operation - Refactored version with split database agents

"""
    负责用户服务，如登录、注册、修改密码、注销账号等
    此版本已重构为使用拆分后的多个数据库代理（UserCoreDBAgent, UserProfileDBAgent等）
"""

import uvicorn
import httpx
import asyncio
import concurrent.futures
import os
import ipaddress
import json
from typing import Dict, List, Any, AsyncGenerator, Optional
from fastapi import FastAPI, Form, HTTPException, status, Depends, Request, UploadFile, File
from fastapi.security import OAuth2PasswordBearer
from dotenv import dotenv_values
from contextlib import asynccontextmanager
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import IPvAnyAddress 

from Service.UserService.Agents.UserCoreDBAgent import UserCoreDBAgent
from Service.UserService.Agents.UserProfileDBAgent import UserProfileDBAgent
from Service.UserService.Agents.UserSettingsDBAgent import UserSettingsDBAgent
from Service.UserService.Agents.UserLoginLogsDBAgent import UserLoginLogsDBAgent
from Service.UserService.Agents.UserAccountActionsDBAgent import UserAccountActionsDBAgent
from Service.UserService.Agents.UserNotificationsDBAgent import UserNotificationsDBAgent
from Service.UserService.Agents.UserFilesDBAgent import UserFilesDBAgent
from Service.UserService.Agents.UserDatabaseManager import UserDatabaseManager
from Service.UserService.UserAccountDatabaseSQLParameterSchema import TableUserLoginLogsInsertSchema, TableUsersQueryWhereSchema, UserLanguage
from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config
from Module.Utils.ToolFunctions import retry
from Module.Utils.FastapiServiceTools import (
    get_service_instances,
    update_service_instances_periodically,
    register_service_to_consul,
    unregister_service_from_consul,
    get_client_ip
)
from Service.UserService.UserServiceRequestType import (
    RegisterRequest,
    LoginRequest,
    UnregisterRequest,
    ModifyPasswordRequest,
    ModifyProfileRequest,
    # UploadFileRequest,
    ModifySettingRequest,
    ModifyNotificationSettingsRequest
)
from Service.UserService.UserServiceResponseType import (
    UserServiceResponseErrorCode,
    UserServiceErrorDetail,
    RegisterData,
    RegisterResponse,
    LoginData,
    LoginResponse,
    UnregisterData,
    UnregisterResponse,
    ModifyPasswordData,
    ModifyPasswordResponse,
    ModifyProfileData,
    ModifyProfileResponse,
    UploadFileData, # 导入 UploadFileData
    UploadFileResponse,
    ModifySettingData,
    ModifySettingResponse,
    ModifyNotificationSettingsData,
    ModifyNotificationSettingsResponse
)
from Service.UserService.UserAccountDatabaseSQLParameterSchema import (
    UserStatus,
    TableUsersUpdateWhereSchema,
    TableUsersUpdateSetSchema,
    TableUserLoginLogsInsertSchema,
    UserAccountActionType,
    TableUserAccountActionsInsertSchema,
    TableUserProfileUpdateSetSchema,
    TableUserProfileUpdateWhereSchema,
    TableUserSettingsUpdateSetSchema,
    TableUserSettingsUpdateWhereSchema
)

# from Service.Other.EnvironmentManagerClient import EnvironmentManagerClient

    

class UserServiceRefactored:
    """
        负责用户服务（重构版本，使用拆分后的多个数据库代理）：
        
            1. 登陆
            2. 注册
            3. 上传文件
            4. 修改账户信息
            5. 注销
    """
    def __init__(self):
        self.logger = setup_logger(name="UserServiceRefactored", log_path="InternalModule")
        
        # 加载环境变量和配置
        self.env_vars = dotenv_values("${AGENT_HOME}/Service/UserService/.env")
        self.config_path = self.env_vars.get("USER_SERVICE_CONFIG_PATH","")
        self.config = load_config(config_path=self.config_path, config_name='UserService', logger=self.logger)
        
        # 验证配置文件
        required_keys = ["consul_url", "host", "port", "service_name", "service_id", "health_check_url", "jwt"]
        validate_config(required_keys, self.config, self.logger)
        
        # 初始化数据库管理器（包含所有代理）
        self.user_database_manager = UserDatabaseManager()
        
        # 使用数据库管理器中已初始化的代理实例
        self.user_core_db_agent = self.user_database_manager.user_core_agent
        self.user_profile_db_agent = self.user_database_manager.user_profile_agent
        self.user_settings_db_agent = self.user_database_manager.user_settings_agent
        self.user_login_logs_db_agent = self.user_database_manager.user_login_logs_agent
        self.user_account_actions_db_agent = self.user_database_manager.user_account_actions_agent
        self.user_notifications_db_agent = self.user_database_manager.user_notifications_agent
        self.user_files_db_agent = self.user_database_manager.user_files_agent
        
        # 限制用户上传的文件的大小1GB
        self.upload_file_max_size = 1 * 1024 * 1024 * 1024 
        
        # 存储服务实例
        self.service_instances: Dict[str, List[Dict]] = {}  # 存储从 Consul 获取的服务实例信息
        
        # Consul URL，确保包含协议前缀
        self.consul_url: str = self.config.get("consul_url", "http://127.0.0.1:8500")
        if not self.consul_url.startswith("http://") and not self.consul_url.startswith("https://"):
            self.consul_url = "http://" + self.consul_url
            self.logger.info(f"Consul URL adjusted to include http://: {self.consul_url}") 
        
        # 微服务本身地址
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 20011)  # 使用不同端口避免冲突

        # 服务注册信息
        self.service_name = self.config.get("service_name", "UserServiceRefactored")
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
            # self.logger.info("Registering service to Consul...")
            # tags = ["UserServiceRefactored"]
            # await register_service_to_consul(consul_url=self.consul_url,
            #                                  client=self.client,
            #                                  logger=self.logger,
            #                                  service_name=self.service_name,
            #                                  service_id=self.service_id,
            #                                  address=self.host,
            #                                  port=self.port,
            #                                  tags=tags,
            #                                  health_check_url=self.health_check_url)
            
            # 异步调用 init_connection，让所有 db_agent 拿到 connect_id
            await self.user_database_manager.init_all_connections()

            # 启动后台任务
            # task = asyncio.create_task(update_service_instances_periodically(
            #                                 consul_url=self.consul_url,
            #                                 client=self.client,
            #                                 service_instances=self.service_instances,
            #                                 config=self.config,
            #                                 logger=self.logger
            #                             ))
            yield  # 应用正常运行
            
        except Exception as e:
            self.logger.error(f"Exception during lifespan: {e}")
            raise
        
        finally:
            # 关闭后台任务
            # 如果 task 没有赋值过(None)，就不去 cancel
            # if task is not None:
            #     task.cancel()    
            #     try:
            #         await task
            #     except asyncio.CancelledError:
            #         self.logger.info("Background task cancelled successfully.")
                
            # 关闭所有DBAgent中的httpx
            await self.user_database_manager.cleanup()
            
            # 注销服务从 Consul
            # try:
            #     self.logger.info("Deregistering service from Consul...")
            #     await unregister_service_from_consul(consul_url=self.consul_url,
            #                                          client=self.client,
            #                                          logger=self.logger,
            #                                          service_id=self.service_id)
            #     self.logger.info("Service deregistered from Consul.")
            # except Exception as e:
            #     self.logger.error(f"Error while deregistering service: {e}")
                
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
            return {"status": "healthy", "version": "refactored"}
        
        # 用户登录
        @self.app.post("/usr/login")
        async def usr_login(user: LoginRequest, request: Request):
            ip_address = get_client_ip(request)
            return await self._usr_login(identifier=user.identifier, password=user.password, 
                                         agent=user.agent or "Unknown", 
                                         device=user.device or "Unknown",
                                         os=user.os or "Unknown", 
                                         ip_address=ip_address)

        # 用户注册
        @self.app.post("/usr/register")
        async def usr_register(user: RegisterRequest, request: Request):
            return await self._usr_register(user_name=user.user_name, account=user.account, 
                                            password=user.password, email=user.email)


        # 用户更改密码
        @self.app.post("/usr/change_pwd")
        async def usr_change_pwd(data: ModifyPasswordRequest, request: Request):
            return await self._usr_change_pwd(session_token=data.session_token,
                                              new_password=data.new_password)


        # 用户注销
        @self.app.post("/usr/unregister")
        async def usr_unregister(data: UnregisterRequest, request: Request):
            return await self._usr_unregister(session_token=data.session_token)


        # 用户修改个人信息
        @self.app.post("/usr/modify_profile")
        async def usr_modify_profile(data: ModifyProfileRequest, request: Request):
            return await self._usr_modify_profile(session_token=data.session_token, 
                                                  user_name=data.user_name, 
                                                  profile_picture_path=data.profile_picture_url,
                                                  signature=data.signature)


        # 用户修改通知设置
        @self.app.post("/usr/modify_notifications")
        async def usr_modify_notification_settings(data: ModifyNotificationSettingsRequest, request: Request):
            # 确保 settings_json 不为 None
            if data.settings_json is None:
                return ModifyNotificationSettingsResponse(
                    operator="usr_modify_notification_settings",
                    result=False,
                    message="settings_json cannot be null.",
                    err_code=UserServiceResponseErrorCode.INVALID_REQUEST_FORMAT,
                    errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.INVALID_REQUEST_FORMAT, message="settings_json is required.")],
                    data=None
                )
            return await self._usr_modify_notification_settings(session_token=data.session_token, 
                                                                settings_json=data.settings_json)


        # 用户修改个人设置
        @self.app.post("/usr/modify_settings")
        async def usr_modify_settings(data: ModifySettingRequest, request: Request):
            return await self._usr_modify_settings(session_token=data.session_token,
                                                   language=data.language,
                                                   configure=data.configure)


        # 用户上传文件
        @self.app.post("/usr/upload_file")
        async def usr_upload_file(request: Request,
                                  session_token: str = Form(...), 
                                  file: UploadFile = File(...)):
            return await self._usr_upload_file(session_token=session_token, file=file)

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
        """ 从Request 中获取注入的头部中包含的IP地址 """
        # 优先从 X-Forwarded-For 中取
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # 退而求其次取 request.client
        if request.client:
            return request.client.host

        # 无法获取时返回默认
        return "0.0.0.0"
    
        
    # --------------------------------
    # 功能函数（使用拆分后的多个Agent）
    # --------------------------------    
    async def _usr_login(self, identifier: str,
                         password: str,
                         ip_address: str,
                         agent: str,
                         device: str,
                         os: str) -> LoginResponse:
        """ 
        验证用户登录

        :param identifier: 用户名或邮箱
        :param password: 密码
        :param ip_address: 用户IP地址
        :param agent: 用户客户端版本
        :param device: 设备信息
        :param os: 操作系统信息

        :retruns:
            LoginResponse
        """
        operator = 'usr_login'
        
        # 1. 查询数据库
        try:
            res = await self.user_core_db_agent.fetch_user_id_and_password_hash_by_email_or_account(identifier=identifier)
        except Exception as e:
            self.logger.error(f"Function:'fetch_user_id_and_password_by_email_or_account' occurr exception.for user '{identifier}': {e}")
            erros = UserServiceErrorDetail(
                code=UserServiceResponseErrorCode.DATABASE_ERROR,
                message="Internal Database error."
            )
            return LoginResponse(
                operator=operator,
                result=False,
                message="Database error occurred.",
                err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                errors=[erros],
                data=None
            )

        self.logger.debug(res)

        # 2. 验证
        # 检查用户是否已注册
        if res is None:
            message = f"Login failed! User: '{identifier}' does not exist!"
            self.logger.info(message)
            return LoginResponse(
                operator=operator,
                result=False,
                message=message,
                err_code=UserServiceResponseErrorCode.ACCOUNT_NOT_FOUND,
                data=None
            )

        # 用户内部ID 和保存的密码hash
        user_id, stored_password_hash = res
        
        # 密码错误
        if not self.pwd_context.verify(password, stored_password_hash):
            # 登录失败log插入
            message = f"Login failed! Invalid account or password!"
            self.logger.info(message)
            try:
                await self.user_login_logs_db_agent.insert_login_log(
                    log_data=TableUserLoginLogsInsertSchema(
                        user_id=user_id,
                        ip_address=ip_address,
                        agent=agent,
                        device=device,
                        os=os,
                        login_success=False
                    )
                )
            except Exception as e:
                self.logger.error(f"Failed to insert login log for user {user_id}: {e}")

            return LoginResponse(
                operator=operator,
                result=False,
                message=message,
                err_code=UserServiceResponseErrorCode.PASSWORD_INCORRECT,
                data=None
            )

        # 3. 生成token
        access_token = self.create_access_token(user_id=user_id)

        # 4. 将token和 status 更新到 users 表
        try:
            res_update = await self.user_core_db_agent.update_users(
                update_data=TableUsersUpdateSetSchema(
                    session_token=access_token,
                    last_login_ip=ip_address,
                    last_login_time=datetime.now()
                ),
                update_where=TableUsersUpdateWhereSchema(user_id=user_id)
            )
            if not res_update:
                 self.logger.warning(f"Operator:'{operator}', Result:False, Message:'Token update failed!', User ID: {user_id}")

        except Exception as e:
            self.logger.error(f"Token update error for user {user_id}: {e}")
        
        # 5. 记录成功登录日志
        try:
            await self.user_login_logs_db_agent.insert_login_log(
                log_data=TableUserLoginLogsInsertSchema(
                    user_id=user_id,
                    ip_address=ip_address,
                    agent=agent,
                    device=device,
                    os=os,
                    login_success=True
                )
            )
        except Exception as e:
            self.logger.error(f"Failed to insert successful login log for user {user_id}: {e}")

        # 6. 获取用户详细信息用于返回
        user_profile_info = await self.user_profile_db_agent.fetch_user_profile(user_id)
        
        # 7. 构造返回数据
        login_data = LoginData(
            user_id=user_id,
            session_token=access_token,
            status=UserStatus.active.value,
            last_login_ip=ip_address,
            last_login_time=datetime.now(),
            profile_picture_url=user_profile_info.get("profile_picture_path") if user_profile_info else None,
            profile_picture_updated_at=user_profile_info.get("profile_picture_updated_at") if user_profile_info else None,
            signature=user_profile_info.get("signature") if user_profile_info else None
        )

        return LoginResponse(
            operator=operator,
            result=True,
            message="Login successful.",
            data=login_data
        )


    async def _usr_register(self, user_name: str, account: str, password: str, email: str) -> RegisterResponse:
        """
        用户注册

        :param user_name: 用户名
        :param account: 用户账号
        :param password: 用户密码
        :param email: 用户邮箱

        :return: RegisterResponse
        """
        operator = 'usr_register'
        
        # 1. 检查用户是否已存在
        try:
            # 检查账户是否存在
            if await self.user_core_db_agent.check_user_exists(identifier=account):
                message = f"Registration failed! Account: '{account}' already exists!"
                self.logger.info(message)
                return RegisterResponse(
                    operator=operator,
                    result=False,
                    message=message,
                    err_code=UserServiceResponseErrorCode.ACCOUNT_ALREADY_EXISTS,
                    errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.ACCOUNT_ALREADY_EXISTS, message=message, field='account')],
                    data=None
                )
            # 检查邮箱是否存在
            if await self.user_core_db_agent.check_user_exists(identifier=email):
                message = f"Registration failed! Email: '{email}' already exists!"
                self.logger.info(message)
                return RegisterResponse(
                    operator=operator,
                    result=False,
                    message=message,
                    err_code=UserServiceResponseErrorCode.EMAIL_ALREADY_EXISTS,
                    errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.EMAIL_ALREADY_EXISTS, message=message, field='email')],
                    data=None
                )
        except Exception as e:
            self.logger.error(f"Error checking if user exists: {e}")
            return RegisterResponse(
                operator=operator,
                result=False,
                message="Database error occurred while checking user existence.",
                err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.DATABASE_ERROR, message="Internal Database error.")],
                data=None
            )

        # 2. 密码哈希
        hashed_password = self.pwd_context.hash(password)

        # 3. 使用UserDatabaseManager插入新用户（自动处理user_uuid、user_suffix和file_folder_path）
        try:
            user_id = await self.user_database_manager.insert_new_user(
                account=account,
                email=email, 
                password_hash=hashed_password,
                user_name=user_name
            )
            if user_id:
                self.logger.info(f"Successfully registered new user with ID: {user_id}")
                
                # 记录账户创建动作
                try:
                    await self.user_account_actions_db_agent.insert_account_action(
                        action_data=TableUserAccountActionsInsertSchema(
                            user_id=user_id,
                            action_type=UserAccountActionType.login,
                            action_detail=f"User account '{account}' created successfully"
                        )
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to log account creation action for user {user_id}: {e}")
                
                return RegisterResponse(
                    operator=operator,
                    result=True,
                    message="Registration successful!",
                    data=RegisterData(user_id=user_id)
                )
            else:
                self.logger.error("Failed to register new user due to transaction failure.")
                return RegisterResponse(
                    operator=operator,
                    result=False,
                    message="Registration failed due to a server error.",
                    err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                    errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.DATABASE_ERROR, message="Failed to create user record.")],
                    data=None
                )
        except Exception as e:
            self.logger.error(f"Exception during new user registration: {e}")
            return RegisterResponse(
                operator=operator,
                result=False,
                message="An unexpected error occurred during registration.",
                err_code=UserServiceResponseErrorCode.UNKNOWN_ERROR,
                errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.UNKNOWN_ERROR, message=str(e))],
                data=None
            )


    async def _usr_change_pwd(self, session_token: str, new_password: str) -> ModifyPasswordResponse:
        """ 
        用户修改密码

        :param session_token: 会话token
        :param new_password: 新密码

        :return:
            ModifyPasswordResponse
        """
        operator = 'usr_change_pwd'
        
        # 1. 验证token
        try:
            user_id = self.verify_token(session_token)
        except ValueError as e:
            self.logger.warning(f"Invalid session token provided: {e}")
            return ModifyPasswordResponse(
                operator=operator,
                result=False,
                message="Invalid session token.",
                err_code=UserServiceResponseErrorCode.INVALID_TOKEN,
                errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.INVALID_TOKEN, message=str(e))],
                data=None
            )

        # 2. 密码哈希
        hashed_password = self.pwd_context.hash(new_password)

        # 3. 更新数据库
        try:
            success = await self.user_core_db_agent.update_user_password_by_user_id(
                user_id=user_id,
                new_password_hash=hashed_password
            )
            if success:
                self.logger.info(f"User {user_id} successfully changed their password.")
                
                # 注意：用户行为记录已经在 UserCoreDBAgent.update_user_password_by_user_id() 中插入
                # 这里不再重复插入，避免数据库中出现重复记录
                # # 记录密码修改动作
                # try:
                #     await self.user_account_actions_db_agent.insert_account_action(
                #         action_data=TableUserAccountActionsInsertSchema(
                #             user_id=user_id,
                #             action_type=UserAccountActionType.password_update,
                #             action_detail="User password changed successfully"
                #         )
                #     )
                # except Exception as e:
                #     self.logger.warning(f"Failed to log password change action for user {user_id}: {e}")
                
                # 获取用户信息用于响应
                user_info = await self.user_core_db_agent.fetch_user_info_by_user_id(user_id)
                if not user_info:
                    # 即使获取信息失败，密码也已成功修改，返回成功，但data可能不完整
                    self.logger.warning(f"Could not retrieve user info for user_id {user_id} after password change.")
                    return ModifyPasswordResponse(
                        operator=operator,
                        result=True,
                        message="Password changed successfully, but failed to retrieve updated user info.",
                        data=ModifyPasswordData(
                            user_id=user_id, 
                            password_update_time=datetime.now(),
                            account=None, # 显式传递None
                            email=None, # 显式传递None
                            user_name=None # 显式传递None
                        )
                    )

                return ModifyPasswordResponse(
                    operator=operator,
                    result=True,
                    message="Password changed successfully.",
                    data=ModifyPasswordData(
                        user_id=user_id,
                        account=user_info.get('account'),
                        email=user_info.get('email'),
                        user_name=user_info.get('user_name'),
                        password_update_time=datetime.now()
                    )
                )
            else:
                self.logger.error(f"Failed to change password for user {user_id}. Update operation failed.")
                return ModifyPasswordResponse(
                    operator=operator,
                    result=False,
                    message="Failed to change password.",
                    err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                    errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.DATABASE_ERROR, message="Failed to update password in database.")],
                    data=None
                )
        except Exception as e:
            self.logger.error(f"Database error while changing password for user {user_id}: {e}")
            return ModifyPasswordResponse(
                operator=operator,
                result=False,
                message="A database error occurred.",
                err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.DATABASE_ERROR, message=str(e))],
                data=None
            )


    async def _usr_unregister(self, session_token: str) -> UnregisterResponse:
        """ 
        用户注销

        :param session_token: 会话token

        :return:
            UnregisterResponse
        """
        operator = 'usr_unregister'
        
        # 1. 验证token
        try:
            user_id = self.verify_token(session_token)
        except ValueError as e:
            self.logger.warning(f"Invalid session token for unregister request: {e}")
            return UnregisterResponse(
                operator=operator,
                result=False,
                message="Invalid session token.",
                err_code=UserServiceResponseErrorCode.INVALID_TOKEN,
                errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.INVALID_TOKEN, message=str(e))],
                data=None
            )

        # 2. 软删除用户
        try:
            success = await self.user_core_db_agent.soft_delete_user_by_user_id(user_id=user_id)
            if success:
                self.logger.info(f"User {user_id} has been soft-deleted.")
                
                # 记录账户注销动作
                try:
                    await self.user_account_actions_db_agent.insert_account_action(
                        action_data=TableUserAccountActionsInsertSchema(
                            user_id=user_id,
                            action_type=UserAccountActionType.account_deletion,
                            action_detail="User account unregistered (soft-deleted)"
                        )
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to log account deletion action for user {user_id}: {e}")
                
                return UnregisterResponse(
                    operator=operator,
                    result=True,
                    message="Account unregistered successfully.",
                    data=UnregisterData(user_id=user_id)
                )
            else:
                self.logger.error(f"Failed to soft-delete user {user_id}. Operation failed.")
                return UnregisterResponse(
                    operator=operator,
                    result=False,
                    message="Failed to unregister account.",
                    err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                    errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.DATABASE_ERROR, message="Failed to update user status in database.")],
                    data=None
                )
        except Exception as e:
            self.logger.error(f"Database error during soft deletion for user {user_id}: {e}")
            return UnregisterResponse(
                operator=operator,
                result=False,
                message="A database error occurred.",
                err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.DATABASE_ERROR, message=str(e))],
                data=None
            )


    async def _usr_modify_profile(self, session_token: str, 
                                user_name: Optional[str], 
                                profile_picture_path: Optional[str], 
                                signature: Optional[str]) -> ModifyProfileResponse:
        """
        修改用户个人信息

        :param session_token: 会话token
        :param user_name: 新用户名
        :param profile_picture_path: 新头像路径
        :param signature: 新签名

        :return:
            ModifyProfileResponse
        """
        operator = 'usr_modify_profile'
        
        try:
            user_id = self.verify_token(session_token)
        except ValueError as e:
            self.logger.warning(f"Invalid session token provided: {e}")
            return ModifyProfileResponse(
                operator=operator,
                result=False,
                message=str(e),
                err_code=UserServiceResponseErrorCode.INVALID_TOKEN,
                data=None
            )

        update_data = {}
        if user_name is not None:
            update_data['user_name'] = user_name
        if profile_picture_path is not None:
            update_data['profile_picture_path'] = profile_picture_path
        if signature is not None:
            update_data['signature'] = signature
            
        if not update_data:
            return ModifyProfileResponse(
                operator=operator,
                result=False,
                message="No profile data provided to update.",
                err_code=UserServiceResponseErrorCode.INVALID_REQUEST_FORMAT,
                data=None
            )

        # 更新 users 表 (如果 user_name 存在)
        if 'user_name' in update_data:
            try:
                # 获取当前用户的 user_suffix
                user_info = await self.user_core_db_agent.fetch_user_info_by_user_id(user_id)
                if user_info and 'user_suffix' in user_info:
                    res_core = await self.user_core_db_agent.update_users(
                        update_data=TableUsersUpdateSetSchema(
                            user_name=update_data['user_name'], 
                            user_suffix=user_info['user_suffix']
                        ),
                        update_where=TableUsersUpdateWhereSchema(user_id=user_id)
                    )
                    if not res_core:
                        self.logger.warning(f"Failed to update user_name for user_id: {user_id}")
                else:
                    self.logger.error(f"Could not fetch user_suffix for user_id: {user_id}")
            except Exception as e:
                self.logger.error(f"Error updating user_name for user_id {user_id}: {e}")
                # 可以选择在这里返回错误，或者继续尝试更新 profile
        
        # 更新 user_profile 表
        profile_update_data = {k: v for k, v in update_data.items() if k != 'user_name'}
        if profile_update_data:
            try:
                res_profile = await self.user_profile_db_agent.update_user_profile(
                    update_data=TableUserProfileUpdateSetSchema(**profile_update_data),
                    update_where=TableUserProfileUpdateWhereSchema(user_id=user_id)
                )
                if not res_profile:
                    self.logger.warning(f"Failed to update user_profile for user_id: {user_id}")
                    # 如果核心信息更新了但这里失败了，可能需要考虑事务
            except Exception as e:
                self.logger.error(f"Error updating user_profile for user_id {user_id}: {e}")
                return ModifyProfileResponse(
                    operator=operator,
                    result=False,
                    message="Database error while updating profile.",
                    err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                    data=None
                )

        # 记录个人信息修改动作
        try:
            await self.user_account_actions_db_agent.insert_account_action(
                action_data=TableUserAccountActionsInsertSchema(
                    user_id=user_id,
                    action_type=UserAccountActionType.profile_update,
                    action_detail=f"User profile updated: {', '.join(update_data.keys())}"
                )
            )
        except Exception as e:
            self.logger.warning(f"Failed to log profile update action for user {user_id}: {e}")

        return ModifyProfileResponse(
            operator=operator,
            result=True,
            message="User profile updated successfully.",
            data=ModifyProfileData(
                user_id=user_id,
                user_name=user_name,
                profile_picture_url=profile_picture_path,
                signature=signature
            )
        )

    async def _usr_modify_notification_settings(self, session_token: str, settings_json: str) -> ModifyNotificationSettingsResponse:
        """
        修改用户通知设置

        :param session_token: 会话token
        :param settings_json: 新的通知设置 (JSON 字符串)

        :return:
            ModifyNotificationSettingsResponse
        """
        operator = 'usr_modify_notification_settings'
        
        try:
            user_id = self.verify_token(session_token)
        except ValueError as e:
            self.logger.warning(f"Invalid session token provided: {e}")
            return ModifyNotificationSettingsResponse(
                operator=operator,
                result=False,
                message=str(e),
                err_code=UserServiceResponseErrorCode.INVALID_TOKEN,
                data=None
            )
            
        try:
            # 验证 settings_json 是否是有效的 JSON
            settings_dict = json.loads(settings_json)
        except json.JSONDecodeError:
            return ModifyNotificationSettingsResponse(
                operator=operator,
                result=False,
                message="Invalid JSON format for notification settings.",
                err_code=UserServiceResponseErrorCode.INVALID_REQUEST_FORMAT,
                data=None
            )

        try:
            res = await self.user_settings_db_agent.update_user_settings(
                update_data=TableUserSettingsUpdateSetSchema(notification_setting=settings_json),
                update_where=TableUserSettingsUpdateWhereSchema(user_id=user_id)
            )
        except Exception as e:
            self.logger.error(f"Error updating notification settings for user {user_id}: {e}")
            return ModifyNotificationSettingsResponse(
                operator=operator,
                result=False,
                message="Database error while updating notification settings.",
                err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                data=None
            )

        if not res:
            return ModifyNotificationSettingsResponse(
                operator=operator,
                result=False,
                message="Failed to update notification settings, user may not exist.",
                err_code=UserServiceResponseErrorCode.ACCOUNT_NOT_FOUND,
                data=None
            )

        # 记录通知设置修改动作
        try:
            await self.user_account_actions_db_agent.insert_account_action(
                action_data=TableUserAccountActionsInsertSchema(
                    user_id=user_id,
                    action_type=UserAccountActionType.profile_update,
                    action_detail="User notification settings updated"
                )
            )
        except Exception as e:
            self.logger.warning(f"Failed to log notification settings update action for user {user_id}: {e}")

        return ModifyNotificationSettingsResponse(
            operator=operator,
            result=True,
            message="Notification settings updated successfully.",
            data=ModifyNotificationSettingsData(
                user_id=user_id,
                notification_settings=settings_dict
            )
        )

    async def _usr_modify_settings(self, session_token: str, 
                                 language: Optional[UserLanguage], 
                                 configure: Optional[str]) -> ModifySettingResponse:
        """
        修改用户个人设置

        :param session_token: 会话token
        :param language: 语言
        :param configure: 配置 (JSON 字符串)

        :return:
            ModifySettingResponse
        """
        operator = 'usr_modify_settings'
        
        try:
            user_id = self.verify_token(session_token)
        except ValueError as e:
            self.logger.warning(f"Invalid session token provided: {e}")
            return ModifySettingResponse(
                operator=operator,
                result=False,
                message=str(e),
                err_code=UserServiceResponseErrorCode.INVALID_TOKEN,
                data=None
            )

        update_data = {}
        configure_dict = None

        if language:
            update_data['language'] = language.value
        
        if configure:
            try:
                configure_dict = json.loads(configure)
                update_data['configure'] = configure_dict
            except json.JSONDecodeError:
                return ModifySettingResponse(
                    operator=operator,
                    result=False,
                    message="Invalid JSON format for configure.",
                    err_code=UserServiceResponseErrorCode.INVALID_REQUEST_FORMAT,
                    data=None
                )
        
        if not update_data:
            return ModifySettingResponse(
                operator=operator,
                result=False,
                message="No settings data provided to update.",
                err_code=UserServiceResponseErrorCode.INVALID_REQUEST_FORMAT,
                data=None
            )

        try:
            res = await self.user_settings_db_agent.update_user_settings(
                update_data=TableUserSettingsUpdateSetSchema(**update_data),
                update_where=TableUserSettingsUpdateWhereSchema(user_id=user_id)
            )
        except Exception as e:
            self.logger.error(f"Error updating settings for user {user_id}: {e}")
            return ModifySettingResponse(
                operator=operator,
                result=False,
                message="Database error while updating settings.",
                err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                data=None
            )

        if not res:
            return ModifySettingResponse(
                operator=operator,
                result=False,
                message="Failed to update settings, user may not exist.",
                err_code=UserServiceResponseErrorCode.ACCOUNT_NOT_FOUND,
                data=None
            )

        # 记录设置修改动作
        try:
            await self.user_account_actions_db_agent.insert_account_action(
                action_data=TableUserAccountActionsInsertSchema(
                    user_id=user_id,
                    action_type=UserAccountActionType.profile_update,
                    action_detail=f"User settings updated: {', '.join(update_data.keys())}"
                )
            )
        except Exception as e:
            self.logger.warning(f"Failed to log settings update action for user {user_id}: {e}")

        return ModifySettingResponse(
            operator=operator,
            result=True,
            message="User settings updated successfully.",
            data=ModifySettingData(
                user_id=user_id,
                language=language.value if language else None,
                configure=configure_dict
            )
        )

    async def _usr_upload_file(self, session_token: str, file: UploadFile) -> UploadFileResponse:
        """ 
        用户上传文件

        :param session_token: 会话token
        :param file: 上传的文件

        :return:
            UploadFileResponse
        """
        operator = 'usr_upload_file'

        if not file.filename:
            return UploadFileResponse(
                operator=operator,
                result=False,
                message="File name is missing.",
                err_code=UserServiceResponseErrorCode.INVALID_REQUEST_FORMAT,
                data=None
            )

        try:
            user_id = self.verify_token(session_token)
        except ValueError as e:
            self.logger.warning(f"Invalid session token for file upload: {e}")
            return UploadFileResponse(
                operator=operator,
                result=False,
                message="Invalid session token.",
                err_code=UserServiceResponseErrorCode.INVALID_TOKEN,
                errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.INVALID_TOKEN, message=str(e))],
                data=None
            )

        # 2. 检查文件大小
        # file.size is optional and can be None
        file_size = file.size or 0
        if file_size > self.upload_file_max_size:
            message = f"File size {file_size} exceeds the limit of {self.upload_file_max_size} bytes."
            self.logger.warning(message)
            return UploadFileResponse(
                operator=operator,
                result=False,
                message=message,
                err_code=UserServiceResponseErrorCode.FILE_TOO_LARGE,
                errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.FILE_TOO_LARGE, message=message)],
                data=None
            )

        # 3. 保存文件到服务器
        try:
            # 构建文件保存路径
            user_files_dir = Path(f"${AGENT_HOME}/Users/Files/{user_id}")
            user_files_dir.mkdir(parents=True, exist_ok=True)
            
            # 防止文件名冲突
            file_path = user_files_dir / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
            
            # 异步写入文件
            with open(file_path, "wb") as buffer:
                while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                    buffer.write(content)
            
            self.logger.info(f"User {user_id} uploaded file '{file.filename}' to '{file_path}'")

        except Exception as e:
            self.logger.error(f"Error saving uploaded file for user {user_id}: {e}")
            return UploadFileResponse(
                operator=operator,
                result=False,
                message="Failed to save uploaded file.",
                err_code=UserServiceResponseErrorCode.UNKNOWN_ERROR,
                errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.UNKNOWN_ERROR, message=str(e))],
                data=None
            )

        # 4. 将文件信息存入数据库
        try:
            file_data_dict = {
                "user_id": user_id,
                "file_name": file.filename,
                "file_type": file.content_type or "application/octet-stream",
                "file_path": str(file_path),
                "file_size": file_size,
                "upload_time": datetime.now()
            }
            
            res = await self.user_database_manager.insert_user_file(
                file_data_dict
            )

            if res:
                self.logger.info(f"Successfully handled file upload for user {user_id}, file '{file.filename}'")
                
                # 记录文件上传动作
                try:
                    await self.user_account_actions_db_agent.insert_account_action(
                        action_data=TableUserAccountActionsInsertSchema(
                            user_id=user_id,
                            action_type=UserAccountActionType.profile_update,
                            action_detail=f"File uploaded: {file.filename}"
                        )
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to log file upload action for user {user_id}: {e}")
                
                return UploadFileResponse(
                    operator=operator,
                    result=True,
                    message="File uploaded successfully.",
                    data=UploadFileData(
                        file_name=file.filename,
                        file_path=str(file_path),
                        file_size=file_size,
                        file_type=file.content_type
                    )
                )
            else:
                # 如果数据库插入失败，可以选择删除已保存的文件以保持一致性
                # os.remove(file_path)
                self.logger.error(f"Failed to insert file info for user {user_id}, file '{file.filename}'")
                return UploadFileResponse(
                    operator=operator,
                    result=False,
                    message="Failed to record file information.",
                    err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                    errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.DATABASE_ERROR, message="Failed to insert file info into database.")],
                    data=None
                )

        except Exception as e:
            self.logger.error(f"Database error during file info insertion for user {user_id}: {e}")
            # 如果数据库插入失败，可以选择删除已保存的文件以保持一致性
            # os.remove(file_path)
            return UploadFileResponse(
                operator=operator,
                result=False,
                message="A database error occurred while recording file information.",
                err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                errors=[UserServiceErrorDetail(code=UserServiceResponseErrorCode.DATABASE_ERROR, message=str(e))],
                data=None
            )


    def run(self):
        """ 启动服务 """
        # uvicorn.run(self.app, host=self.host, port=self.port, log_level="info", workers=4)
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")
