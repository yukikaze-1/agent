# Project:      Agent
# Author:       yomu
# Time:         2025/6/18
# Version:      0.1
# Description:  Response Type Definitions


"""
    各种回复的格式定义
"""

from pydantic import BaseModel, EmailStr, constr, Field, model_validator


# 各种回复的格式要求定义

class RegisterResponse(BaseModel):
    """ 用户注册 response """
    user_id: str = Field(..., description="用户唯一标识符")
    message: str = Field(..., description="提示信息")
    result: bool = Field(..., description="操作结果")

class LoginResponse(BaseModel):
    """ 用户登陆 response """
    user_id: str = Field(..., description="用户唯一标识符")
    token: str = Field(..., description="JWT token")
    message: str = Field(..., description="提示信息")
    result: bool = Field(..., description="操作结果")

class LogoutResponse(BaseModel):
    """ 用户注销账户 response """
    message: str = Field(..., description="提示信息")
    result: bool = Field(..., description="操作结果")

class ModifyPasswordResponse(BaseModel):
    """ 用户修改密码 response """
    message: str = Field(..., description="提示信息")
    result: bool = Field(..., description="操作结果")

class ModifyProfileResponse(BaseModel):
    """ 用户修改个人信息 response """
    message: str = Field(..., description="提示信息")
    result: bool = Field(..., description="操作结果")

class UploadFileResponse(BaseModel):
    """ 用户上传文件 response """
    file_id: str = Field(..., description="文件唯一标识符")
    message: str = Field(..., description="提示信息")
    result: bool = Field(..., description="操作结果")

class ModifySettingResponse(BaseModel):
    """ 用户修改设置 response """
    message: str = Field(..., description="提示信息")
    result: bool = Field(..., description="操作结果")

class ModifyNotificationSettingsResponse(BaseModel):
    """ 用户修改通知设置 response """
    message: str = Field(..., description="提示信息")
    result: bool = Field(..., description="操作结果")