# Project:      Agent
# Author:       yomu
# Time:         2025/6/18
# Version:      0.1
# Description:  UserService Response Type Definitions


"""
    Uservice 各种回复的格式定义
"""

from datetime import datetime
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, EmailStr, constr, Field, model_validator


# ******************************************************************************
# ******************************** 错误相关 ************************************
# ******************************************************************************

class UserServiceResponseErrorCode(IntEnum):
    """  UserService Response 的错误代码类 """
    ACCOUNT_NOT_FOUND = 1001    # 账户未注册
    PASSWORD_INCORRECT = 1002    # 密码不正确
    INVALID_EMAIL = 1003         # 邮箱格式不正确
    ACCOUNT_ALREADY_EXISTS = 1004 # 账户已被注册
    EMAIL_ALREADY_EXISTS = 1005   # 邮箱已被注册
    USER_NOT_REGISTERED = 1006    # 用户未注册
    TOKEN_EXPIRED = 2001         # 令牌已过期
    INVALID_TOKEN = 2002         # 无效的令牌
    INVALID_REQUEST_FORMAT = 2003 # 请求格式错误（如JSON解析失败）
    DATABASE_ERROR = 3001       # 数据库错误
    LLM_ERROR = 4001            # LLM错误
    STT_ERROR = 5001            # STT错误
    TTS_ERROR = 6001            # TTS错误
    FILE_TOO_LARGE = 7001         # 文件过大
    UNKNOWN_ERROR = 9999        # 未知错误
    # TODO 待完善
    

class UserServiceErrorDetail(BaseModel):
    """ UserService详细错误类 """
    code: UserServiceResponseErrorCode = Field(..., description="错误代码")
    message: str = Field(..., description="错误信息")
    field: Optional[str] = Field(default=None, description="出错字段，比如 'email'")
    hint: Optional[str] = Field(default=None, description="帮助提示")


# ******************************************************************************
# ******************************** Response相关 ********************************
# ******************************************************************************

class UserServiceBaseResponse(BaseModel):
    """ 基础回复格式 """
    operator: str = Field(..., description="操作")
    result: bool = Field(..., description="操作结果")
    message: str = Field(..., description="提示信息")
    err_code: Optional[UserServiceResponseErrorCode] = Field(default=None, description="错误代码")
    errors: Optional[List[UserServiceErrorDetail]] = Field(default=None, description="详细错误列表")
    trace_id: Optional[str] = Field(default=None, description="链路追踪ID")
    elapsed_ms: Optional[int] = Field(default=None, description="服务端处理耗时（毫秒）")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应生成时间")
    lang: Optional[str] = Field(default="zh", description="返回语言（国际化支持）")
    level: Optional[str] = Field(default=None, description="提示等级: info / warning / error")

# -------------------------------- 用户注册相关 ----------------------------

class RegisterData(BaseModel):
    """ 用户注册返回给客户端的信息 """
    user_id: int = Field(..., description="用户ID")
    account: Optional[str] = Field(default=None, description="用户账号")
    email: Optional[str] = Field(default=None, description="用户邮箱")
    user_name: Optional[str] = Field(default=None, description="用户昵称")

class RegisterResponse(UserServiceBaseResponse):
    """ 用户注册 response """
    data: Optional[RegisterData] = Field(default=None, description="用户注册附加数据")


# -------------------------------- 用户登陆相关 --------------------------------
class LoginData(BaseModel):
    """ 用户登陆成功返回给客户端的信息 """
    user_id: int = Field(..., description="用户ID")
    session_token: str = Field(..., description="会话令牌")
    status: Optional[str] = Field(default=None, description="用户状态")
    last_login_time: Optional[datetime] = Field(default=None, description="最后登录时间")
    last_login_ip: Optional[str] = Field(default=None, description="最后登录IP")
    profile_picture_url: Optional[str] = Field(default=None, description="头像URL")
    profile_picture_updated_at: Optional[datetime] = Field(default=None, description="头像更新时间")
    signature: Optional[str] = Field(default=None, description="用户签名")


class LoginResponse(UserServiceBaseResponse):
    """ 用户登陆 response """
    data: Optional[LoginData] = Field(default=None, description="用户信息")


# -------------------------------- 用户注销相关 --------------------------------

class UnregisterData(BaseModel):
    """ 用户注销返回给客户端的信息 """
    user_id: int = Field(..., description="用户ID")
    unregister_time: datetime = Field(default_factory=datetime.now, description="用户注销时间")


class UnregisterResponse(UserServiceBaseResponse):
    """ 用户注销账户 response """
    data: Optional[UnregisterData] = Field(default=None, description="用户注销附加数据")


# -------------------------------- 用户修改相关 --------------------------------

class ModifyPasswordData(BaseModel):
    """ 用户修改密码返回给客户端的信息 """
    user_id: int = Field(..., description="用户ID")
    account: Optional[str] = Field(default=None, description="用户账号")
    email: Optional[str] = Field(default=None, description="用户邮箱")
    user_name: Optional[str] = Field(default=None, description="用户昵称")
    password_update_time: datetime = Field(..., description="用户密码更新时间")


class ModifyPasswordResponse(UserServiceBaseResponse):
    """ 用户修改密码 response """
    data: Optional[ModifyPasswordData] = Field(default=None, description="用户修改密码附加数据")




class ModifyProfileData(BaseModel):
    """ 用户修改个人信息返回给客户端的信息 """
    user_id: int = Field(..., description="用户ID")
    user_name: Optional[str] = Field(default=None, description="用户昵称")
    profile_picture_url: Optional[str] = Field(default=None, description="用户头像URL")
    signature: Optional[str] = Field(default=None, description="用户签名")


class ModifyProfileResponse(UserServiceBaseResponse):
    """ 用户修改个人信息 response """
    data: Optional[ModifyProfileData] = Field(default=None, description="用户修改个人信息附加数据")




class ModifySettingData(BaseModel):
    """ 用户修改设置返回给客户端的信息 """
    user_id: int = Field(..., description="用户ID")
    language: Optional[str] = Field(default=None, description="用户语言")
    configure: Optional[Dict[str, Any]] = Field(default=None, description="用户配置")
    notification_settings: Optional[Dict[str, Any]] = Field(default=None, description="用户通知设置")

class ModifySettingResponse(UserServiceBaseResponse):
    """ 用户修改设置 response """
    data: Optional[ModifySettingData] = Field(default=None, description="用户修改设置附加数据")




class ModifyNotificationSettingsData(BaseModel):
    """ 用户修改通知设置返回给客户端的信息 """
    user_id: int = Field(..., description="用户ID")
    notification_settings: Optional[Dict[str, Any]] = Field(default=None, description="用户通知设置")


class ModifyNotificationSettingsResponse(UserServiceBaseResponse):
    """ 用户修改通知设置 response """
    data: Optional[ModifyNotificationSettingsData] = Field(default=None, description="用户修改通知设置附加数据")


# -------------------------------- 用户上传文件相关 --------------------------------

class UploadFileData(BaseModel):
    """ 文件信息 """
    file_name: str = Field(..., description="文件名")
    file_type: Optional[str] = Field(..., description="文件类型")
    file_path: str = Field(..., description="文件路径")
    file_size: Optional[int] = Field(..., description="文件大小")
    upload_time: datetime = Field(default_factory=datetime.now, description="上传时间")

class UploadFileResponse(UserServiceBaseResponse):
    """ 用户上传文件 response """
    data: Optional[UploadFileData] = Field(default=None, description="用户上传文件附加数据")


