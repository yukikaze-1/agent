# Project:      Agent
# Author:       yomu
# Time:         2025/6/18
# Version:      0.1
# Description:  Request Type Definitions


"""
    各种请求的格式定义
"""
from typing import Dict
from pydantic import BaseModel, EmailStr, constr, Field, model_validator


# 各种请求的格式要求定义

class RegisterRequest(BaseModel):
    """ 用户注册 request """
    user_name: str = Field(..., description="用户名，不唯一，有数字后缀")
    account: str = Field(..., min_length=3, max_length=50, description="用户账号，唯一")
    password: str = Field(..., min_length=6, description="用户密码，最少六位")
    email: EmailStr = Field(..., description="用户邮箱")
    

class LoginRequest(BaseModel):
    """ 用户登陆 request """
    identifier: str = Field(min_length=3, max_length=50, description="用户账号或邮箱")
    password: str = Field(..., min_length=6, description="用户密码")
    agent: str = Field(..., description="用户客户端版本")
    device: str = Field(..., description="设备信息")
    os: str = Field(..., description="操作系统信息")


class UnregisterRequest(BaseModel):
    """ 用户注销账户 request """
    session_token: str = Field(..., description="session token")


class ModifyPasswordRequest(BaseModel):
    """ 用户修改密码 request"""
    session_token: str = Field(..., description="session token")
    new_password: str = Field(..., min_length=6, description="新密码")
    

class ModifyProfileRequest(BaseModel):
    """ 用户修改个人信息 request"""
    session_token: str = Field(..., description="session token")
    user_name: str = Field(..., description="用户名")
    profile_picture_url: str = Field(..., description="头像URL")
    signature: str = Field(..., description="个性签名")


class UploadFileRequest(BaseModel):
    """ 用户上传文件 request"""
    session_token: str = Field(..., description="session token")
    file: bytes = Field(..., description="上传的文件")
    
    
class ModifySettingRequest(BaseModel):
    """ 用户修改设置 request"""
    session_token: str = Field(..., description="session token")
    language: str | None = Field(..., description="语言")
    configure_json_path: str | None = Field(..., description="配置文件路径")
    notification_setting: Dict | None = Field(..., description="通知设置")


class ModifyNotificationSettingsRequest(BaseModel):
    """ 用户修改通知设置 request"""
    session_token: str = Field(..., description="session token")
    notifications_enabled: bool = Field(..., description="是否启用通知")
    settings_json: Dict = Field(..., description="通知设定JSON")
    # TODO 这个setting_json支不支持自定义呢？即pydantic支不支持嵌套？