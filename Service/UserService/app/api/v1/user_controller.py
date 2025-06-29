# Project:      Agent
# Author:       yomu
# Time:         2025/06/29
# Version:      0.3
# Description:  User Controller - 用户服务控制器

"""
用户服务控制器
负责处理HTTP请求/响应，将业务逻辑委托给相应的服务层
"""

from typing import Optional
from logging import Logger
from fastapi import FastAPI, Form, Request, UploadFile, File, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer

from Module.Utils.FastapiServiceTools import get_client_ip
from Service.UserService.app.models.UserServiceRequestType import (
    RegisterRequest,
    LoginRequest,
    UnregisterRequest,
    ModifyPasswordRequest,
    ModifyProfileRequest,
    ModifySettingRequest,
    ModifyNotificationSettingsRequest
)
from Service.UserService.app.models.UserServiceResponseType import (
    ModifyNotificationSettingsResponse,
    UserServiceResponseErrorCode,
    UserServiceErrorDetail
)
from Service.UserService.app.services.user_auth_service import UserAuthService
from Service.UserService.app.services.user_account_service import UserAccountService
from Service.UserService.app.services.user_profile_service import UserProfileService
from Service.UserService.app.services.user_file_service import UserFileService


class UserController:
    """
    用户服务控制器
    负责定义API路由和处理HTTP请求，业务逻辑委托给服务层
    """
    
    def __init__(self,
                 app: FastAPI,
                 auth_service: UserAuthService,
                 account_service: UserAccountService,
                 profile_service: UserProfileService,
                 file_service: UserFileService,
                 logger: Optional[Logger] = None):
        self.app = app
        self.auth_service = auth_service
        self.account_service = account_service
        self.profile_service = profile_service
        self.file_service = file_service
        self.logger = logger
        
        # OAuth2 scheme for dependency injection
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/usr/login")
        
        # 设置路由
        self.setup_routes()
    
    def setup_routes(self):
        """设置所有API路由"""
        
        # 健康检查接口
        @self.app.get("/health")
        async def health_check():
            """系统健康状态检查"""
            return {"status": "healthy", "version": "refactored"}
        
        # 用户登录
        @self.app.post("/usr/login")
        async def usr_login(user: LoginRequest, request: Request):
            """用户登录接口"""
            # 获取客户端IP地址
            ip_address = get_client_ip(request)
            return await self.auth_service.login(
                identifier=user.identifier, 
                password=user.password, 
                agent=user.agent or "Unknown", 
                device=user.device or "Unknown",
                os=user.os or "Unknown", 
                ip_address=ip_address
            )

        # 用户注册
        @self.app.post("/usr/register")
        async def usr_register(user: RegisterRequest, request: Request):
            """用户注册接口"""
            return await self.account_service.register(
                user_name=user.user_name, 
                account=user.account, 
                password=user.password, 
                email=user.email
            )

        # 用户更改密码
        @self.app.post("/usr/change_pwd")
        async def usr_change_pwd(data: ModifyPasswordRequest, request: Request):
            """用户修改密码接口"""
            return await self.account_service.change_password(
                session_token=data.session_token,
                new_password=data.new_password
            )

        # 用户注销
        @self.app.post("/usr/unregister")
        async def usr_unregister(data: UnregisterRequest, request: Request):
            return await self.account_service.unregister(
                session_token=data.session_token
            )

        # 用户修改个人信息
        @self.app.post("/usr/modify_profile")
        async def usr_modify_profile(data: ModifyProfileRequest, request: Request):
            return await self.profile_service.modify_profile(
                session_token=data.session_token, 
                user_name=data.user_name, 
                profile_picture_path=data.profile_picture_url,
                signature=data.signature
            )

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
                    errors=[UserServiceErrorDetail(
                        code=UserServiceResponseErrorCode.INVALID_REQUEST_FORMAT, 
                        message="settings_json is required."
                    )],
                    data=None
                )
            return await self.profile_service.modify_notification_settings(
                session_token=data.session_token, 
                settings_json=data.settings_json
            )

        # 用户修改个人设置
        @self.app.post("/usr/modify_settings")
        async def usr_modify_settings(data: ModifySettingRequest, request: Request):
            return await self.profile_service.modify_settings(
                session_token=data.session_token,
                language=data.language,
                configure=data.configure
            )

        # 用户上传文件
        @self.app.post("/usr/upload_file")
        async def usr_upload_file(request: Request,
                                  session_token: str = Form(...), 
                                  file: UploadFile = File(...)):
            return await self.file_service.upload_file(
                session_token=session_token, 
                file=file
            )
    
    def get_current_user_id(self):
        """返回一个Depends(...) 封装依赖 通过token获得user_id"""
        async def _get_current_user_id(token: str = Depends(self.oauth2_scheme)) -> int:
            try:
                return self.auth_service.verify_token(token)
            except ValueError:
                raise HTTPException(status_code=401, detail="Token 验证失败")
        return Depends(_get_current_user_id)
