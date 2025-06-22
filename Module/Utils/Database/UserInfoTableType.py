# Project:      Agent
# Author:       yomu
# Time:         2025/6/22
# Version:      0.1
# Description:  User information tables pydantic definition

"""
    用户数据库的各表的pydantic
"""

from enum import StrEnum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, EmailStr, Field, model_validator, field_validator, IPvAnyAddress, IPv4Address, IPv6Address
from datetime import datetime
from pathlib import Path
from pydantic_core import PydanticCustomError

"""
    pydantic层面的设计：
    
        所有的 InsertRequest 和 UpdateRequest 的字段集合都是数据库中的 表 的字段 的真子集。
        
        insert 有insert的白名单
        update 有update的白名单
        
        InsertRequest：
            1. 在InsertRequest中的所有字段均必须手动赋值，没有默认值。
            2. 在InsertRequest中没有，但是在表中有的字段表示：
                a. 该字段只能由数据库自动插入（这些字段都在数据库层面由默认值）。eg. 每张表的created_at字段，有默认值DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP。
                b. 插入时无需赋值且默认为NULL 且 更新时可以更新的字段。eg. users表中的last_login_time和last_login_ip
            
        UpdateRequest:
            1. 在UpdateRequest中的所有字段值均可以为None，但不能同时全部为None。
            2. 在UpdateRequest中值为None的字段表示不更新该字段。具体转换在构建update sql语句时进行(跳过值为None的字段)。
            3. 在UpdateRequest中某些字段需要进行格式校验。eg. users表中的file_folder_path字段。
            4. 在表中有但在UpdateRequest中没有的字段表示：
                a. 该字段只能由数据库进行更新。eg.每张表的updated_at字段。
            5. 
            
        Response:
            1. 所有表的所有字段均会被返回
            2. 某些表的某些字段可能会返回None，代表该字段值为NULL。eg. users表的last_login_time和last_login_ip之类的字段。
            3. 
"""

# 字段过滤
SQL_REQUEST_ALLOWED_FIELDS = {
    "users": {
        "insert": {"user_uuid", "status", "account", "password_hash", "email", "file_folder_path"},
        "update": {"status", "password_hash", "last_login_ip", "last_login_ip", "session_token", "deleted_at"}
    },
    
    "user_profile": {
        "insert": {"user_name", "profile_picture_path", "signature"},
        "update": {"user_name", "profile_picture_path", "signature"}
    },
    
    "user_login_logs": {
        "insert": {"user_id", "login_time", "ip_address", "agent", "device", "os", "login_success"},
        "update": {}
    },
    
    "user_settings": {
        "insert": {"user_id", "language", "configure", "notification_setting"},
        "update": {"language", "configure", "notification_setting"}
    },
    
    "user_account_actions": {
        "insert": {"user_id", "action_type", "action_detail"},
        "update": {}
    },
    
    "user_notifications": {
        "insert": {"user_id", "notification_type", "notification_title", "notification_content", "is_read"},
        "update": {"notification_type", "notification_title", "notification_content", "is_read"}
    },
    
    "user_files": {
        "insert": {"user_id", "file_name", "file_path", "file_type", "file_size", "upload_time", "is_deleted"},
        "update": {"file_name", "file_path", "file_size", "file_type", "upload_time", "is_deleted"}
    },
    
    "conversations": {
        "insert": {"user_id", "title", "message_count"},
        "update": {"title", "message_count"}
    },
    
    "conversation_messages": {
        "insert": {"conversation_id", "user_id", "sender_role", "message_type", "parent_message_id", "content", "token_count"},
        "update": {}
    }
}


"""

## 用户信息数据库设计

### 1. 用户主表 (`users`)
| 字段名             | 类型                                                                      | 描述         |
| ----------------- | ------------------------------------------------------------------------- | ---------- |
| `user_id`         | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                                 | 用户内部ID（主键） |
| `user_uuid`       | `CHAR(36) NOT NULL UNIQUE`                                                | 用户UUID     |
| `status`          | `VARCHAR(64) NOT NULL`                                                    | 用户状态       |
| `account`         | `VARCHAR(256) NOT NULL UNIQUE`                                            | 用户账号       |
| `password_hash`   | `VARCHAR(256) NOT NULL`                                                   | 密码哈希值      |
| `email`           | `VARCHAR(256) NOT NULL UNIQUE`                                            | 用户邮箱       |
| `last_login_time` | `DATETIME`                                                                | 最后登录时间     |
| `last_login_ip`   | `VARCHAR(64)`                                                             | 最后登录IP     |
| `session_token`   | `VARCHAR(2048)`                                                           | Session令牌  |
| `file_folder_path`| `VARCHAR(512) NOT NULL UNIQUE`                                            | 用户个人文件夹(默认为UUID为命名)  |
| `created_at`      | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`                             | 创建时间       |
| `updated_at`      | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 修改时间
| `deleted_at`      | `DATETIME DEFAULT NULL`                                                   | 删除时间 |

CREATE TABLE users (
  user_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_uuid CHAR(36) NOT NULL UNIQUE,
  status VARCHAR(64) NOT NULL,
  account VARCHAR(256) NOT NULL UNIQUE,
  password_hash VARCHAR(256) NOT NULL,
  email VARCHAR(256) NOT NULL UNIQUE,
  last_login_time DATETIME,
  last_login_ip VARCHAR(64),
  session_token VARCHAR(2048),
  file_folder_path VARCHAR(512) NOT NULL UNIQUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at DATETIME DEFAULT NULL
);
"""



class StrictBaseModel(BaseModel):
    """ pydantic 禁止额外字段 """
    class Config:
        extra = "forbid"
        

class UserStatus(StrEnum):
    inactive = "inactive"
    active = "active"
    deleted = "deleted"
    

class TableUsersResponse(StrictBaseModel):
    """ 用户主表 Response"""
    user_id: int = Field(..., description="用户内部ID（主键）")
    user_uuid: str = Field(..., description="用户UUID")
    status: UserStatus = Field(..., description="用户状态")
    account: str = Field(..., description="用户账号")
    password_hash: str= Field(..., description="密码哈希值")
    email: EmailStr = Field(..., description="用户邮箱")
    last_login_time: datetime | None = Field(..., description="最后登录时间")
    last_login_ip: IPvAnyAddress | None = Field(..., description="最后登录IP")
    session_token: str | None = Field(..., description="Session令牌")
    file_folder_path: str = Field(..., description="用户个人文件夹路径")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="修改时间")
    deleted_at: datetime | None = Field(..., description="删除时间")
    # Response的file_folder_path不需要校验。但是在request中的需要校验
    
    

class TableUsersInsertRequest(StrictBaseModel):
    """ 用户主表 Insert Request """
    user_uuid: str = Field(..., min_length=36, max_length=36, description="用户UUID")
    status: UserStatus = Field(default=UserStatus.inactive, description="用户状态")
    account: str = Field(..., min_length=4, max_length=256, description="用户账号")
    password_hash: str = Field(..., min_length=6, max_length=256, description="密码哈希值")
    email: EmailStr = Field(..., description="用户邮箱")
    file_folder_path: str = Field(..., description="用户个人文件夹路径")
    
    
    @field_validator("file_folder_path")
    def validate_file_folder_path(cls, value: str) -> str:
        """ 验证用户个人文件夹路径 """
        path = Path(value)
        
        # 1. 禁止绝对路径
        if path.is_absolute():
            raise ValueError("路径必须是相对路径（不能以/开头）")
        
        # 2. 标准化路径格式
        normalized = path.as_posix()
        
        # 3. 防止路径穿越
        if any(part == ".." for part in normalized.split('/')):
            raise ValueError("路径包含非法跳转（../）")
            
        return normalized  # 返回标准化字符串
    
    
class TableUsersUpdateRequest(StrictBaseModel):
    """ 用户主表 Update Request """
    status: UserStatus | None = Field(default=None, description="用户状态")
    password_hash: str | None = Field(default=None, min_length=6, max_length=256, description="密码哈希值")
    last_login_time: datetime | None = Field(default=None, description="最后登录时间")
    last_login_ip: IPvAnyAddress | None = Field(default=None, description="最后登录IP")
    session_token: str | None = Field(default=None, description="Session令牌")
    deleted_at: datetime | None = Field(default=None, description="删除时间")

    @model_validator(mode="after")
    def at_least_one_field_must_be_present(self) -> 'TableUsersUpdateRequest':
        if not ( self.status or self.password_hash or  self.last_login_time or self.last_login_ip or self.session_token or self.deleted_at):
            raise ValueError("至少需要提供一个要更新的字段（status、password_hash、last_login_time、last_login_ip、session_token、deleted_at）")
        return self


"""

### 2. 用户扩展资料 (`user_profile`)
| 字段名                        | 类型                                                                      | 描述          |
| ---------------------        | ----------------------------------------------------------------          | ----------- |
| `user_id`                    | `INT UNSIGNED PRIMARY KEY FK`                                             | 用户ID（主键+外键） |
| `user_name`                  | `VARCHAR(256) NOT NULL`                                                   | 用户名         |
| `profile_picture_path`        | `VARCHAR(512) NOT NULL DEFAULT 'Resources/img/nahida.jpg'`                | 头像URL地址     |
| `signature`                  | `VARCHAR(256) DEFAULT NULL`                                               | 用户个性签名      |
| `created_at`                 | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`                             | 创建时间        |
| `updated_at`                 | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 修改时间        |
| `profile_picture_updated_at` | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP `                            | 头像URL地址修改时间   |

CREATE TABLE user_profile (
  user_id INT UNSIGNED PRIMARY KEY,
  user_name VARCHAR(256) NOT NULL,
  profile_picture_path VARCHAR(512) NOT NULL DEFAULT 'Resources/img/nahida.jpg',
  signature VARCHAR(256) DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  profile_picture_updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_user_profile_user_id FOREIGN KEY (user_id) 
    REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
    
  DELIMITER $$

  CREATE TRIGGER trg_update_profile_picture_time
  BEFORE UPDATE ON user_profile
  FOR EACH ROW
  BEGIN
    -- 如果头像字段发生了变化
    IF NOT (NEW.profile_picture_path <=> OLD.profile_picture_path) THEN
        SET NEW.profile_picture_updated_at = CURRENT_TIMESTAMP;
    END IF;
  END$$  
  DELIMITER ;
);

"""
class TableUserProfileResponse(StrictBaseModel):
    """ 用户扩展资料 Response"""
    user_id: int = Field(..., description="用户ID（主键+外键）")
    user_name: str = Field(..., description="用户名")
    profile_picture_path: str = Field(..., description="头像URL地址")
    signature: str | None = Field(..., description="用户个性签名")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="修改时间")
    profile_picture_updated_at: datetime = Field(..., description="头像URL地址修改时间")
    # Response的profile_picture_path不需要校验。但是在request中的需要校验


class TableUserProfileInsertRequest(StrictBaseModel):
    """  用户扩展资料 Insert Request """
    user_name: str = Field(..., min_length=1, max_length=256, description="用户名")
    profile_picture_path: str | None = Field(default=None, description="头像URL地址")
    signature: str | None = Field(default=None,max_length=256, description="用户个性签名")

    @field_validator("profile_picture_path")
    def validate_profile_picture_path(cls, value: str | None) -> str | None:
        """ 验证头像文件路径 """
        if value is None:
            return value
        
        path = Path(value)
        
        # 1. 禁止绝对路径
        if not value.startswith("Resources/img/"):
            raise ValueError("头像文件路径必须以 'Resources/img/' 开头")
        
        # 2. 标准化路径格式
        normalized = path.as_posix()
        
        # 3. 防止路径穿越
        if any(part == ".." for part in normalized.split('/')):
            raise ValueError("路径包含非法跳转（../）")
        return normalized
    

class TableUserProfileUpdateRequest(StrictBaseModel):
    """  用户扩展资料 Update Request """
    user_name: str | None = Field(default=None, min_length=1, max_length=256, description="用户名")
    profile_picture_path: str | None = Field(default=None, description="头像URL地址")
    signature: str | None = Field(default=None, max_length=256, description="用户个性签名")
    
    @field_validator("profile_picture_path")
    def validate_profile_picture_path(cls, value: str) -> str:
        """ 验证头像文件路径 """
        path = Path(value)
        
        # 1. 禁止绝对路径
        if not value.startswith("Resources/img/"):
            raise ValueError("头像文件路径必须以 'Resources/img/' 开头")
        
        # 2. 标准化路径格式
        normalized = path.as_posix()
        
        # 3. 防止路径穿越
        if any(part == ".." for part in normalized.split('/')):
            raise ValueError("路径包含非法跳转（../）")
        return normalized
    
    @model_validator(mode="after")
    def at_least_one_field_must_be_present(self) -> 'TableUserProfileUpdateRequest':
        if not (self.user_name or self.profile_picture_path or self.signature):
            raise ValueError("至少需要提供一个要更新的字段（用户名(user_name)、头像URL(profile_picture_path)或签名(signature)）")
        return self

"""

### 3. 用户登录认证 (`user_login_logs`)
| 字段名           | 类型                                                                      | 描述       |
| --------------- | ----------------------------------------------------------------          | -------- |
| `login_id`      | `BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                              | 日志主键     |
| `user_id`       | `INT UNSIGNED NOT NULL`                                                   | 用户ID（外键） |
| `login_time`    | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP NOT NULL`                    | 登陆时间     |
| `ip_address`    | `VARCHAR(64) NOT NULL`                                                    | 登陆IP      |
| `agent`         | `VARCHAR(512) NOT NULL`                                                   | 浏览器代理    |
| `device`        | `VARCHAR(512) NOT NULL`                                                   | 登录设备     |
| `os`            | `VARCHAR(512) NOT NULL`                                                   | 操作系统     |
| `login_success` | `BOOL DEFAULT FALSE NOT NULL`                                             | 是否成功登录   |
| `created_at`    | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`                             | 创建时间     |
| `updated_at`    | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间     |

CREATE TABLE user_login_logs (
  login_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL,
  login_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP NOT NULL,
  ip_address VARCHAR(64) NOT NULL,
  agent VARCHAR(512) NOT NULL,
  device VARCHAR(512) NOT NULL,
  os VARCHAR(512) NOT NULL,
  login_success BOOL DEFAULT FALSE NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_login_logs_user_id FOREIGN KEY (user_id) 
    REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

"""

class TableUserLoginLogsResponse(StrictBaseModel):
    """ 用户登录日志 """
    login_id: int = Field(..., description="日志ID（主键）")
    user_id: int = Field(..., description="用户ID（外键）")
    login_time: datetime = Field(..., description="登录时间")
    ip_address: IPvAnyAddress = Field(..., description="登录IP地址")
    agent: str = Field(..., description="浏览器代理")
    device: str = Field(..., description="登录设备")
    os: str = Field(..., description="操作系统")
    login_success: bool = Field(..., description="登录是否成功")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="修改时间")


class TableUserLoginLogsInsertRequest(StrictBaseModel):
    """ 用户登录日志 Insert Request """
    user_id: int = Field(..., description="用户ID（外键）")
    ip_address: IPvAnyAddress = Field(..., description="登录IP地址")
    agent: str = Field(..., description="浏览器代理")
    device: str = Field(..., description="登录设备")
    os: str = Field(..., description="操作系统")
    login_success: bool = Field(..., description="登录是否成功")
    

"""

### 4. 用户自定义设置 (`user_settings`)
| 字段名                  | 类型                                                                      | 描述          |
| ---------------------- | ----------------------------------------------------------------          | ----------- |
| `user_id`              | `INT UNSIGNED PRIMARY KEY FK`                                             | 用户ID（主键+外键） |
| `language`             | `VARCHAR(8) NOT NULL DEFAULT 'zh'`                                        | 用户语言偏好      |
| `configure`            | `JSON NOT NULL`                                                           | 用户配置    |
| `notification_setting` | `JSON NOT NULL`                                                           | 用户通知设置      |
| `created_at`           | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`                             | 创建时间        |
| `updated_at`           | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间        |

CREATE TABLE user_settings (
  user_id INT UNSIGNED PRIMARY KEY,
  language VARCHAR(8) NOT NULL DEFAULT 'zh',
  configure JSON NOT NULL,
  notification_setting JSON NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_user_settings_user_id FOREIGN KEY (user_id) 
    REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

"""

class UserLanguage(StrEnum):
    """ 用户语言偏好 """
    zh = "zh"
    en = "en"
    jp = "jp"
    

class TableUserSettingsResponse(StrictBaseModel):
    """ 用户自定义设置 """
    user_id: int = Field(..., description="用户ID（主键+外键）")
    language: UserLanguage = Field(..., description="用户语言偏好")
    configure: dict = Field(..., description="用户配置")
    notification_setting: dict = Field(..., description="用户通知设置")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="修改时间")


class TableUserSettingsInsertRequest(StrictBaseModel):
    """ 用户自定义设置 Insert Request """
    user_id: int = Field(..., description="用户ID（主键+外键）")
    language: UserLanguage = Field(..., description="用户语言偏好")
    configure: dict = Field(..., description="用户配置")
    notification_setting: dict = Field(..., description="用户通知设置")
    
    
class TableUserSettingsUpdateRequest(StrictBaseModel):
    """ 用户自定义设置 Update Request """
    language: UserLanguage | None = Field(default=None, description="用户语言偏好")
    configure: dict | None = Field(default=None, description="用户配置")
    notification_setting: dict | None = Field(default=None, description="用户通知设置")
    
    @model_validator(mode="after")
    def at_least_one_field_must_be_present(self) -> 'TableUserSettingsUpdateRequest':
        if not (self.language or self.configure or self.notification_setting):
            raise ValueError("至少需要提供一个要更新的字段（language、configure或notification_setting）")
        return self

"""

# TODO 将该表修改为只读
### 5. 用户账户行为 (`user_account_actions`)
| 字段名                       | 类型                                                                      | 描述       |
| --------------------------- | ----------------------------------------------------------------          | -------- |
| `action_id`                 | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                                 | 主键       |
| `user_id`                   | `INT UNSIGNED NOT NULL FK`                                                | 用户ID（外键） |
| `action_type`               | `VARCHAR(256) NOT NULL`                                                   | 用户账户操作类型   |
| `action_detail`             | `VARCHAR(512) NOT NULL`                                                   | 用户账户操作细节   |
| `created_at`                | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`                             | 创建时间     |
| `updated_at`                | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间     |

CREATE TABLE user_account_actions (
  action_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL,
  action_type VARCHAR(256) NOT NULL,
  action_detail VARCHAR(512) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_user_actions_user_id FOREIGN KEY (user_id) 
    REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

"""
class UserAccountActionType(StrEnum):
    """ 用户账户操作类型 """
    login = "login"
    password_change = "password_change"
    profile_update = "profile_update"
    account_deletion = "account_deletion"
    

class TableUserAccountActionsResponse(StrictBaseModel):
    """ 用户账户行为 """
    action_id: int = Field(..., description="主键")
    user_id: int = Field(..., description="用户ID（外键）")
    action_type: UserAccountActionType = Field(..., description="用户账户操作类型")
    action_detail: str = Field(..., description="用户账户操作细节")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class TableUserAccountActionsInsertRequest(StrictBaseModel):
    """ 用户账户行为 Insert Request """
    user_id: int = Field(..., description="用户ID（外键）")
    action_type: UserAccountActionType = Field(..., description="用户账户操作类型")
    action_detail: str = Field(..., description="用户账户操作细节")
    

"""

### 6. 用户通知与消息 (`user_notifications`)
| 字段名                | 类型                                                                       | 描述       |
| --------------------  | ----------------------------------------------------------------          | -------- |
| `notification_id`     | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                                 | 通知ID（主键） |
| `user_id`             | `INT UNSIGNED NOT NULL FK`                                                | 用户ID（外键） |
| `notification_type`   | `VARCHAR(64) NOT NULL`                                                    | 通知类型     |
| `notification_title`  | `VARCHAR(256) NOT NULL`                                                   | 通知标题     |
| `notification_content`| `TEXT`                                                                    | 通知内容     |
| `is_read`             | `BOOL NOT NULL DEFAULT FALSE`                                            | 是否已读     |
| `created_at`          | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`                             | 创建时间     |
| `updated_at`          | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间     |

CREATE TABLE user_notifications (
  notification_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL,
  notification_type VARCHAR(64) NOT NULL,
  notification_title VARCHAR(256) NOT NULL,
  notification_content TEXT,
  is_read BOOL NOT NULL DEFAULT FALSE ,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_user_notifications_user_id FOREIGN KEY (user_id) 
    REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

"""

class UserNotificationType(StrEnum):
    """ 通知类型 """
    system = "system"
    security = "security"
    promotion = "promotion"


class TableUserNotificationsResponse(StrictBaseModel):
    """ 用户通知与消息 Response"""
    notification_id: int = Field(..., description="通知ID（主键）")
    user_id: int = Field(..., description="用户ID（外键）")
    notification_type: UserNotificationType = Field(..., description="通知类型")
    notification_title: str = Field(..., description="通知标题")
    notification_content: str = Field(..., description="通知内容")
    is_read: bool = Field(..., description="是否已读")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class TableUserNotificationsInsertRequest(StrictBaseModel):
    """ 用户通知与消息 Insert Request """
    user_id: int = Field(..., description="用户ID（外键）")
    notification_type: UserNotificationType = Field(..., description="通知类型")
    notification_title: str = Field(..., description="通知标题")
    notification_content: str = Field(..., description="通知内容")
    is_read: bool = Field(..., description="是否已读")


class TableUserNotificationsUpdateRequest(StrictBaseModel):
    """ 用户通知与消息 Update Request """
    notification_type: UserNotificationType | None = Field(default=None, description="通知类型")
    notification_title: str | None = Field(default=None, description="通知标题")
    notification_content: str | None = Field(default=None, description="通知内容")
    is_read: bool | None = Field(default=None, description="是否已读")
    
    @model_validator(mode="after")
    def at_least_one_field_must_be_present(self) -> 'TableUserNotificationsUpdateRequest':
        if not (self.notification_type or self.notification_title or self.notification_content or self.is_read):
            raise ValueError("至少需要提供一个要更新的字段（notification_type、notification_title、notification_content或is_read）")
        return self

"""

### 7. 用户文件 (`user_files`)
| 字段名            | 类型                                                                      | 描述           |
| ---------------- | ----------------------------------------------------------------          | ------------ |
| `file_id`        | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                                 | 文件ID         |
| `user_id`        | `INT UNSIGNED NOT NULL FK`                                                | 用户ID（外键）     |
| `file_path`      | `VARCHAR(512) NOT NULL`                                                   | 文件相对路径       |
| `file_name`      | `VARCHAR(256) NOT NULL`                                                   | 原始文件名        |
| `file_type`      | `VARCHAR(256) NOT NULL`                                                   | 文件类型（如 .png） |
| `file_size`      | `BIGINT UNSIGNED NOT NULL`                                                | 文件大小         |
| `upload_time`    | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP `                            | 上传时间         |
| `is_deleted`     | `BOOL DEFAULT FALSE NOT NULL`                                             | 是否删除         |
| `created_at`     | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`                             | 创建时间         |
| `updated_at`     | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间         |

CREATE TABLE user_files (
  file_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL,
  file_path VARCHAR(512) NOT NULL,
  file_name VARCHAR(256) NOT NULL,
  file_type VARCHAR(256) NOT NULL,
  file_size BIGINT UNSIGNED NOT NULL,
  upload_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_deleted BOOL DEFAULT FALSE NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_user_files_user_id FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

"""
# TODO file type是否需要一个单独的enum class?

class TableUserFilesResponse(StrictBaseModel):
    """ 用户文件 """
    file_id: int = Field(..., description="文件ID")
    user_id: int = Field(..., description="用户ID（外键）")
    file_name: str = Field(..., description="原始文件名")
    file_path: str = Field(..., description="文件相对路径")
    file_type: str = Field(..., description="文件类型（如 .png）")
    file_size: int = Field(..., description="文件大小")
    upload_time: datetime = Field(..., description="上传时间")
    is_deleted: bool = Field(..., description="是否删除")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class TableUserFilesInsertRequest(StrictBaseModel):
    """ 用户文件 Insert Request """
    user_id: int = Field(..., description="用户ID（外键）")
    file_path: str = Field(..., min_length=1, max_length=512, description="文件相对路径")
    file_name: str = Field(..., min_length=1, max_length=256, description="原始文件名")
    file_type: str = Field(..., min_length=1, max_length=256, description="文件类型（如 .png）")
    file_size: int = Field(..., description="文件大小")
    upload_time: datetime = Field(..., description="上传时间") 
    is_deleted: bool = Field(..., description="是否删除")
    
    
class TableUserFilesUpdateRequest(StrictBaseModel):
    """ 用户文件 Update Request """
    file_path: str | None = Field(default=None, min_length=1, max_length=512, description="文件相对路径")
    file_name: str | None = Field(default=None, min_length=1, max_length=256, description="原始文件名")
    file_type: str | None = Field(default=None, min_length=1, max_length=256, description="文件类型（如 .png）")
    file_size: int | None = Field(default=None, description="文件大小")
    upload_time: datetime | None = Field(default=None, description="上传时间")
    is_deleted: bool | None = Field(default=None, description="是否删除")

    @model_validator(mode="after")
    def at_least_one_field_must_be_present(self) -> 'TableUserFilesUpdateRequest':
        if not (self.file_path or self.file_name or self.file_type or self.file_size or self.is_deleted or self.upload_time):
            raise ValueError("至少需要提供一个要更新的字段（file_path、file_name、file_type、file_size、is_deleted或upload_time）")
        return self

"""

# TODO 将conversations 和conversations_messages 抽离出来放在一个单独的数据库，并且单独写一个封装类来操作
### 8. 会话表(`conversations`)
| 字段名             | 类型                                                                      | 说明          |
| ----------------- | ----------------------------------------------------------------          | ----------- |
| `conversation_id` | `BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                              | 会话 ID       |
| `user_id`         | `INT UNSIGNED NOT NULL FK`                                                | 用户内部 ID（外键） |
| `title`           | `VARCHAR(256) NOT NULL`                                                   | 会话标题        |
| `message_count`   | `INT UNSIGNED NOT NULL DEFAULT 0`                                         | 消息数量        |
| `created_at`      | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`                             | 创建时间        |
| `updated_at`      | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 修改时间        |

CREATE TABLE conversations (
    conversation_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    title VARCHAR(256) NOT NULL,
    message_count INT UNSIGNED NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_conversations_user_id FOREIGN KEY (user_id) 
      REFERENCES users(user_id)
      ON DELETE CASCADE ON UPDATE CASCADE
);


"""
class TableConversationsResponse(StrictBaseModel):
    """ 会话表 """
    conversation_id: int = Field(..., description="会话 ID")
    user_id: int = Field(..., description="用户内部 ID（外键）")
    title: str = Field(..., description="会话标题")
    message_count: int = Field(..., description="消息数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="修改时间")


class TableConversationsInsertRequest(StrictBaseModel):
    """ 会话表 Insert Request """
    user_id: int = Field(..., description="用户内部 ID（外键）")
    title: str = Field(..., description="会话标题")
    message_count: int = Field(default=0, description="消息数量")


class TableConversationsUpdateRequest(StrictBaseModel):
    """ 会话表 Update Request """
    title: str | None = Field(default=None, min_length=1, max_length=256, description="会话标题")
    message_count: int | None = Field(default=None, description="消息数量")

    @model_validator(mode="after")
    def at_least_one_field_must_be_present(self) -> 'TableConversationsUpdateRequest':
        if not (self.title or self.message_count):
            raise ValueError("至少需要提供一个要更新的字段（title、message_count）")
        return self
    
    
"""

### 9. 会话消息表(`conversation_messages`)
| 字段名             | 类型                                                              | 说明        |
| -----------------  | ---------------------------------------------------------------- | --------- |
| `message_id`       | `BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                     | 消息 ID     |
| `conversation_id`  | `INT UNSIGNED NOT NULL FK`                                       | 会话 ID（外键） |
| `user_id`          | `INT UNSIGNED NOT NULL FK`                                       | 用户 ID（外键） |
| `sender_role`      | `VARCHAR(64) NOT NULL`                                           | 角色        |
| `message_type`     | `VARCHAR(256) NOT NULL`                                          | 信息类型      |
| `parent_message_id`| `BIGINT UNSIGNED DEFAULT NULL`                                   | 父消息 ID（外键） |
| `content`          | `TEXT DEFAULT NULL`                                              | 内容        |
| `token_count`      | `INT UNSIGNED NOT NULL`                                          | 消息 Token 数（用于统计消耗） |
| `created_at`       | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`                    | 创建时间      |

CREATE TABLE conversation_messages (
    message_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    conversation_id BIGINT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    sender_role VARCHAR(64) NOT NULL,
    message_type VARCHAR(256) NOT NULL,
    parent_message_id BIGINT UNSIGNED DEFAULT NULL,
    content TEXT DEFAULT NULL,
    token_count INT UNSIGNED NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_conversation_messages_conversation_id FOREIGN KEY (conversation_id)
      REFERENCES conversations(conversation_id)
      ON DELETE CASCADE ON UPDATE CASCADE,
      
    CONSTRAINT fk_conversation_messages_user_id FOREIGN KEY (user_id)
      REFERENCES users(user_id)
      ON DELETE CASCADE ON UPDATE CASCADE,  

    CONSTRAINT fk_conversation_messages_parent_message_id FOREIGN KEY (parent_message_id)
      REFERENCES conversation_messages(message_id)
      ON DELETE CASCADE ON UPDATE CASCADE
);

"""

class ConversationMessageType(StrEnum):
    """ 消息类型 """
    text = "text"
    image = "image"
    file = "file"
    audio = "audio"
    video = "video"


class SenderRole(StrEnum):
    """ 角色 """
    user = "user"
    assistant = "assistant"
    system = "system"
    observer = "observer"
    

class TableConversationMessagesResponse(StrictBaseModel):
    """ 会话消息表 """
    message_id: int = Field(..., description="消息 ID")
    conversation_id: int = Field(..., description="会话 ID（外键）")
    user_id: int = Field(..., description="用户 ID（外键）")
    sender_role: SenderRole = Field(..., description="角色")
    message_type: ConversationMessageType = Field(..., description="信息类型")
    parent_message_id: int | None = Field(..., description="父消息 ID（外键）")
    content: str | None = Field(..., description="内容")
    token_count: int = Field(..., description="消息 Token 数（用于统计消耗）")
    created_at: datetime = Field(..., description="创建时间")



class TableConversationMessagesInsertRequest(StrictBaseModel):
    """ 会话消息表 Insert Request """
    conversation_id: int = Field(..., description="会话 ID（外键）")
    user_id: int = Field(..., description="用户 ID（外键）")
    sender_role: SenderRole = Field(..., description="角色")
    message_type: ConversationMessageType = Field(..., description="信息类型")
    parent_message_id: int | None = Field(..., description="父消息 ID（外键）")
    content: str | None = Field(..., description="内容")
    token_count: int = Field(..., description="消息 Token 数（用于统计消耗）")
    
    
    