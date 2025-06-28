# Project:      Agent
# Author:       yomu
# Time:         2025/6/18
# Version:      0.1
# Description:  UserService Request Type Definitions


"""
    各种请求的格式定义
"""
from typing import Dict, Optional
from pydantic import BaseModel, EmailStr, constr, Field, model_validator

from Service.UserService.UserAccountDatabaseSQLParameterSchema import UserLanguage


# 各种请求的格式要求定义

class StrictBaseModel(BaseModel):
    """ 基础模型，所有请求都继承自此模型 """
    class Config:
        # 允许额外的字段
        extra = "forbid"


class RegisterRequest(StrictBaseModel):
    """ 用户注册 request """
    user_name: str = Field(..., description="用户名，不唯一，有数字后缀")
    account: str = Field(..., min_length=3, max_length=50, description="用户账号，唯一")
    password: str = Field(..., min_length=6, description="用户密码，最少六位")
    email: EmailStr = Field(..., description="用户邮箱")
    

class LoginRequest(StrictBaseModel):
    """ 用户登陆 request """
    identifier: str = Field(min_length=3, max_length=50, description="用户账号或邮箱")
    password: str = Field(..., min_length=6, description="用户密码")
    agent: str = Field(..., description="用户客户端版本")
    device: str = Field(..., description="设备信息")
    os: str = Field(..., description="操作系统信息")


class UnregisterRequest(StrictBaseModel):
    """ 用户注销账户 request """
    session_token: str = Field(..., description="session token")


class ModifyPasswordRequest(StrictBaseModel):
    """ 用户修改密码 request"""
    session_token: str = Field(..., description="session token")
    new_password: str = Field(..., min_length=6, description="新密码")
    

class ModifyProfileRequest(StrictBaseModel):
    """ 用户修改个人信息 request"""
    session_token: str = Field(..., description="session token")
    user_name: Optional[str] = Field(default=None, description="用户名")
    profile_picture_url: Optional[str] = Field(default=None, description="头像URL")
    signature: Optional[str] = Field(default=None, description="个性签名")
    
    
class ModifySettingRequest(StrictBaseModel):
    """ 用户修改设置 request"""
    session_token: str = Field(..., description="session token")
    language: Optional[UserLanguage] = Field(default=None, description="语言")
    configure: Optional[str] = Field(default=None, description="用户配置 (JSON string)")


class ModifyNotificationSettingsRequest(StrictBaseModel):
    """ 用户修改通知设置 request"""
    session_token: str = Field(..., description="session token")
    notifications_enabled: Optional[bool] = Field(default=None, description="是否启用通知")
    settings_json: Optional[str] = Field(default=None, description="通知设定JSON (string)")