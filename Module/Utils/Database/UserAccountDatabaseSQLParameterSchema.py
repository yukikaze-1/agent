# Project:      Agent
# Author:       yomu
# Time:         2025/6/22
# Version:      0.1
# Description:  User information tables pydantic definition

"""
    用户数据库的各表的pydantic
"""

from enum import StrEnum
from typing import Dict, List, Any, Optional, Set, Literal
from pydantic import BaseModel, EmailStr, Field, model_validator, field_validator, IPvAnyAddress, IPv4Address, IPv6Address
from datetime import datetime
from pathlib import Path
from pydantic_core import PydanticCustomError

# ------------------------------------------------------------------------------------------------
# 各表的schema的汇总
# ------------------------------------------------------------------------------------------------ 

"""
    注：StrictBaseModel为pydantic，作用为禁止额外字段。以下所有Schema均直接或间接继承StrictBaseModel。

    A. 'users'
        1. 基础Schema:
            a. TableUsersSchema                          ← 完整表结构
            b. TableUsersInsertSchema                    ← 用于插入（insert）
            c. TableUsersUpdateSetSchema                 ← update 的 set 部分
            d. TableUsersUpdateWhereSchema               ← update 的 where 部分
            e. TableUsersDeleteWhereSchema               ← delete 的 where 条件
            f. TableUsersQueryWhereSchema                ← query 的 where 条件
            g. TableUsersQueryFieldsSchema               ← query 的 select 字段控制（如 FieldSelectionSchema） 

        2. 业务Schema
            a. SoftDeleteUserSchema                             users表 软删除一个用户(通过主键user_id)(将status置为'deleted',deleted_at字段会由触发器自动更新)
            b. HardDeleteUserSchema                             users表 应删除一个用户(通过主键user_id)(将用户数据从users表中删除，其余表格会自动删除相关数据，因为user_id是其他表的外键)
            c. ChangePasswordHashSchema                         users表 更新用户密码Hash(通过主键User_id)
            d. FetchUserUUIDByUserIDSchema                      users表 查找 user_uuid 字段(通过user_uuid主键)
            e. UpdateSessionTokenSchema                         users表 更新 session_token 字段(通过user_id主键)
            f. DeleteExpiredUsersSchema                         users表 硬删除所有状态为'deleted'且deleted_at字段离现在超过x天的用户
            g. UpdateLastLoginTimeAndLastLoginIPSchema          users表 更新 last_login_time 和 last_login_ip 字段(通过user_id 主键)

"""


# ------------------------------------------------------------------------------------------------
# 各种Schema的解释
# ------------------------------------------------------------------------------------------------ 
"""
    pydantic层面的设计：
            
        insert 有insert的白名单
        update 有update的白名单
        delete 有delete的白名单
        query  有query 的白名单
        各业务需求有额外的白名单
        
        InsertSchema：
            描述 “允许插入的新数据” —— 即表中可写字段，通常不包括主键（如自增 ID）
            1. 在InsertSchema中的所有字段均必须手动赋值，没有默认值。
            2. 在InsertSchema中没有，但是在表中有的字段表示：
                a. 系统维护字段。该字段只能由数据库自动插入（这些字段都在数据库层面由默认值）。eg. 每张表的created_at字段，有默认值DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP。
                b. 只能更新的字段（插入时无需赋值 且默认为NULL 且 更新时可以更新的字段）。eg. users表中的last_login_time和last_login_ip
                c. 自增主键（如 users 表的 user_id）
                
                
        UpdateSchema:
            功能：描述 “允许更新的字段 + 用于定位记录的主键或索引字段”
            用途：
                a. 校验前端更新请求
                b. 生成 UPDATE table SET col1=%s WHERE where_conditions = where_values
            1. 在UpdateSchema中的所有字段值均可以为None，但不能同时全部为None。
            2. 在UpdateSchema中值为None的字段表示不更新该字段。具体转换在构建update sql语句时进行(跳过值为None的字段)。
            3. 在UpdateSchema中某些字段需要进行格式校验。eg. users表中的file_folder_path字段。
            4. 在表中有但在UpdateSchema中没有的字段表示：
                a. 该字段只能由数据库进行更新。eg.每张表的updated_at字段。
            
            
        DeleteSchema:
            DeleteWhereSchema：
                1. 内含的所有字段均为where条件（即: WHERE key = value）
                2. 字段值可为None但不可全部同时为None
                3. 部分字段存在互斥or组合
                4. 最终 WHERE 语句仅使用不为 None 的字段构造
       
        QuerySchema:
            QueryWhereSchema:
                1. 内含的所有字段均为where条件（即: WHERE key = value）
                2. 字段值可为None但不可全部同时为None
                3. 最终 WHERE 语句仅使用不为 None 的字段构造
                
            QueryFieldSchema:
                所有表的查询字段的schema均由SQL_REQUEST_ALLOWED_FIELDS白名单+FieldSelectionSchema来实现

         
"""

# ------------------------------------------------------------------------------------------------
# 各种需要的工具函数
# ------------------------------------------------------------------------------------------------     
# 字段过滤
def get_allowed_fields(table: str, action: Literal['insert', 'update', 'delete', 'query']) -> set[str]:
    """ 
    获取指定表和操作的允许字段集合
    
    :param table: 表名
    :param action: 操作类型
    :type action: Literal['insert', 'update', 'delete', 'query']
    :return: 允许的字段集合
    """
    if action not in {'insert', 'update', 'delete', 'query'}:
        raise ValueError(f"Unsupported action: '{action}'. Must be one of <'insert', 'update', 'delete', 'query'>")
    return SQL_REQUEST_ALLOWED_FIELDS.get(table, {}).get(action, set())


def filter_writable_fields(schema: BaseModel, allowed_fields: Set[str]) -> dict:
    """
    过滤出可用于 SQL 写入的字段。
    
    - 跳过为 None 的字段（用于 insert 或 update）
    - 跳过未在白名单中的字段
    
    :pram schema: pydantic BaseModel 实例
    :param allowed_fields: 允许的字段集合
    
    :return: 过滤后的字典，包含允许的字段及其值
    """
    return {
        key: value
        for key, value in schema.model_dump(exclude_unset=True).items()
        if key in allowed_fields and value is not None
    }

# ------------------------------------------------------------------------------------------------
# 各操作的数据库字段的白名单
# ------------------------------------------------------------------------------------------------ 

SQL_REQUEST_ALLOWED_FIELDS = {
    "users": {
        "insert": {"user_uuid", "account", "password_hash", "email", "file_folder_path"},
        "update_set":   {"status", "user_name", "user_suffix", "password_hash", "last_login_time", "last_login_ip", "session_token"},
        "update_where": {"user_id", "user_uuid", "status", "account", "email", "user_name", "user_suffix", "last_login_time", "created_at", "deleted_at"},
        "delete_where": {"user_id", "user_name", "user_suffix","status", "deleted_at"},
        "query_where":  {"user_id", "user_uuid", "user_name", "user_suffix", "user_display_name", "status", "account", "email", "created_at", "deleted_at"},
        "query_fields": {"user_id", "user_uuid", "user_name", "user_suffix", "user_display_name", "status", "account", "email", "last_login_time", "last_login_ip", "file_folder_path", "created_at", "updated_at", "deleted_at"}
    }, 
    
    "user_profile": {
        "insert":     {"user_id", "profile_picture_path", "signature"},
        "update_set": {"user_name", "profile_picture_path", "signature"},
        "update_where": {"user_id"},
        "delete_where": {"user_id"},
        "query_where":  {"user_id"},
        "query_fields": {"user_id", "profile_picture_path", "signature", "created_at", "updated_at", "profile_picture_updated_at"}
    }, 
    
    "user_login_logs": {
        "insert": {"user_id", "login_time", "ip_address", "agent", "device", "os", "login_success"},
        "update_set": {},
        "update_where":{},
        "delete_where": {"login_id", "user_id", "login_time", "login_success", "created_at"},
        "query_where":{"login_id", "user_id", "login_time", "login_success", "created_at"},
        "query_fields":{"login_id", "user_id", "login_time", "ip_address", "agent", "device", "os", "login_success", "created_at", "updated_at"}
    },
    
    "user_settings": {
        "insert": {"user_id", "language", "configure", "notification_setting"},
        "update_set": {"language", "configure", "notification_setting"},
        "update_where":{"user_id"},
        "delete_where": {"user_id"},
        "query_where":{"user_id", "language", "created_at", "updated_at"},
        "query_fields":{"user_id", "language", "configure", "notification_setting", "created_at", "updated_at"}
    }, 
    
    "user_account_actions": {
        "insert": {"user_id", "action_type", "action_detail"},
        "update_set": {},
        "update_where":{},
        "delete_where": {"user_id", "action_id", "created_at"},
        "query_where":{"action_id", "user_id", "action_type", "action_detail", "created_at"},
        "query_fields":{"action_id", "user_id", "action_type", "action_detail", "created_at", "updated_at"}
    },
    
    "user_notifications": {
        "insert": {"user_id", "notification_type", "notification_title", "notification_content", "is_read"},
        "update_set":   {"notification_type", "notification_title", "notification_content", "is_read"},
        "update_where": {"notification_id", "user_id",  "is_read", "created_at"},
        "delete_where": {"notification_id", "user_id", "notification_type", "notification_title", "is_read", "created_at"},
        "query_where":  {"notification_id", "user_id", "notification_type", "notification_title", "is_read", "created_at", "updated_at"},
        "query_fields": {"notification_id", "user_id", "notification_type", "notification_title", "notification_content", "is_read", "created_at", "updated_at"}
    },

    "user_files": {
        "insert": {"user_id", "file_name", "file_path", "file_type", "file_size", "upload_time", "is_deleted"},
        "update_set": {"file_name", "file_path", "file_size", "file_type", "upload_time", "is_deleted"},
        "update_where":{"file_id", "user_id", "file_type", "is_deleted", "created_at", "upload_time"},
        "delete_where": {"file_id", "user_id", "is_deleted", "created_at", "upload_time"},
        "query_where":{"file_id", "user_id", "file_name", "file_type", "file_size", "is_deleted", "created_at", "upload_time"},
        "query_fields":{ "file_id", "user_id", "file_name", "file_path", "file_type", "file_size", "upload_time", "is_deleted", "created_at", "updated_at"}
    },

    "conversations": {
        "insert": {"user_id", "title", "message_count"},
        "update": {"title", "message_count"},
        "delete": {"conversation_id", "user_id"}
    }, # TODO 还没实现这两张表不该放这里
    
    "conversation_messages": {
        "insert": {"conversation_id", "user_id", "sender_role", "message_type", "parent_message_id", "content", "token_count"},
        "update": {},
        "delete": {"message_id", "conversation_id", "user_id"}
    }
}

# ------------------------------------------------------------------------------------------------
# 数据库通用schema
# ------------------------------------------------------------------------------------------------ 

class StrictBaseModel(BaseModel):
    """ pydantic 禁止额外字段 """
    class Config:
        extra = "forbid"
        
        
class FieldSelectionSchema(StrictBaseModel):
    fields: Optional[List[str]] = Field(
        default=None,
        description="指定返回字段的列表，若为 None 则返回全部字段"
    )

# ------------------------------------------------------------------------------------------------
# 数据库各表的表设计和操作schema
# ------------------------------------------------------------------------------------------------ 
"""

## 用户信息数据库设计

### 1. 用户主表 (`users`)
| 字段名                   | 类型                                                                                            | 描述        
| -----------------       | -------------------------------------------------------------------------                       | ----------
| `user_id`               | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                                                       | 用户内部ID（主键）
| `user_uuid`             | `CHAR(36) NOT NULL UNIQUE`                                                                      | 用户UUID    
| `user_name`             | `VARCHAR(255) NOT NULL`                                                                         | 用户名        
| `user_suffix`           | `INT UNSIGNED NOT NULL`                                                                         | 用户名唯一数字后缀        
| `user_display_name`     | `VARCHAR(261) GENERATED ALWAYS AS (CONCAT(user_name, '#', LPAD(user_suffix, 4, '0'))) STORED`   | 实际显示用户名(用户名#数字后缀)
| `status`                | `VARCHAR(64) NOT NULL`                                                                          | 用户状态      
| `account`               | `VARCHAR(255) NOT NULL UNIQUE`                                                                  | 用户账号      
| `password_hash`         | `VARCHAR(255) NOT NULL`                                                                         | 密码哈希值     
| `email`                 | `VARCHAR(255) NOT NULL UNIQUE`                                                                  | 用户邮箱      
| `last_login_time`       | `DATETIME`                                                                                      | 最后登录时间    
| `last_login_ip`         | `VARCHAR(64)`                                                                                   | 最后登录IP    
| `session_token`         | `VARCHAR(2048)`                                                                                 | Session令牌 
| `file_folder_path`      | `VARCHAR(512) NOT NULL UNIQUE`                                                                  | 用户个人文件夹(默认为UUID为命名) 
| `created_at`            | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`                                                   | 创建时间      
| `updated_at`            | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`                       | 修改时间
| `deleted_at`            | `DATETIME DEFAULT NULL`                                                                         | 删除时间 

CREATE TABLE users (
  user_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_uuid CHAR(36) NOT NULL UNIQUE,
  user_name VARCHAR(255) NOT NULL,
  user_suffix INT UNSIGNED NOT NULL,    -- 自动分配的后缀编号
  user_display_name VARCHAR(261) GENERATED ALWAYS AS (CONCAT(user_name, '#', LPAD(user_suffix, 4, '0'))) STORED,
  status VARCHAR(64) NOT NULL,
  account VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  last_login_time DATETIME,
  last_login_ip VARCHAR(64),
  session_token VARCHAR(2048),
  file_folder_path VARCHAR(512) NOT NULL UNIQUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at DATETIME DEFAULT NULL,

  UNIQUE(user_name, user_suffix),         -- 保证同名用户后缀唯一
  UNIQUE(user_display_name)               -- 全局唯一的展示名
);  

-- 创建索引, 加速搜索
CREATE INDEX idx_user_name_suffix ON users(user_name, user_suffix);

-- 触发器
DELIMITER $$

CREATE TRIGGER before_users_update
BEFORE UPDATE ON users
FOR EACH ROW
BEGIN
  -- 如果 status 被设置为 'deleted'，并且之前不是 'deleted'，则更新 deleted_at
  IF NEW.status = 'deleted' AND OLD.status <> 'deleted' THEN
    SET NEW.deleted_at = NOW();
  END IF;

  -- 如果 status 被改回非 deleted，并且原来是 deleted，可以选择是否清空 deleted_at（可选）
  IF NEW.status <> 'deleted' AND OLD.status = 'deleted' THEN
    SET NEW.deleted_at = NULL;
  END IF;
END$$

DELIMITER ;
"""     

class UserStatus(StrEnum):
    inactive = "inactive"
    active = "active"
    deleted = "deleted"
    

class TableUsersSchema(StrictBaseModel):
    """ 用户主表 Schema """
    user_id: int 
    user_uuid: str 
    user_name: str
    user_suffix: int
    user_display_name: str 
    status: UserStatus
    account: str
    password_hash: str
    email: EmailStr
    last_login_time: datetime | None 
    last_login_ip: IPvAnyAddress | None 
    session_token: str | None 
    file_folder_path: str 
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    
    

class TableUsersInsertSchema(StrictBaseModel):
    """ 用户主表 Insert Schema 没有的字段要么是系统维护，要么是插入时不能赋值，只能更新"""
    user_uuid: str = Field(..., min_length=36, max_length=36, description="用户UUID")
    user_name: str = Field(..., min_length=4, max_length=64,  description="用户名")
    user_suffix: int = Field(..., description="用户名唯一数字后缀")
    account: str = Field(..., min_length=4, max_length=255, description="用户账号")
    password_hash: str = Field(..., min_length=6, max_length=255, description="密码哈希值")
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
    
    
class TableUsersUpdateSetSchema(StrictBaseModel):
    """ 用户主表 Update SET Schema """
    status: UserStatus | None = Field(default=None, description="用户状态")
    user_name: str | None = Field(default=None, min_length=4, max_length=64,  description="用户名")
    user_suffix: int | None = Field(default=None, description="用户名唯一数字后缀")
    password_hash: str | None = Field(default=None, min_length=6, max_length=255, description="密码哈希值")
    last_login_time: datetime | None = Field(default=None, description="最后登录时间")
    last_login_ip: IPvAnyAddress | None = Field(default=None, description="最后登录IP")
    session_token: str | None = Field(default=None, description="Session令牌")

    @model_validator(mode="after")
    def at_least_one_field_must_be_present(self) -> 'TableUsersUpdateSetSchema':
        if not any([self.status, self.user_name, self.user_suffix, self.password_hash, self.last_login_time, self.last_login_ip, self.session_token]):
            raise ValueError("至少需要提供一个要更新的字段（status、user_name、password_hash、last_login_time、last_login_ip、session_token）")
        return self
    
    @model_validator(mode="after")
    def name_and_suffix_must_both_be_present_or_not(self) -> 'TableUsersUpdateSetSchema':
        if (self.user_name is not None) != (self.user_suffix is not None):
            raise ValueError("如果提供了user_name，则必须同时提供user_suffix，反之亦然")
        return self
    
    
class TableUsersUpdateWhereSchema(StrictBaseModel):
    """ 用户主表 Update WHERE Schema """
    user_id: int | None = Field(..., description="用户内部ID（主键）")
    user_uuid: str | None = Field(..., description="用户UUID")
    account: str | None = Field(default=None, min_length=4, max_length=255, description="用户账号")
    email: EmailStr | None = Field(default=None, description="用户邮箱")
    status: UserStatus | None = Field(default=None, description="用户状态")
    user_name: str | None = Field(default=None, min_length=4, max_length=64,  description="用户名")
    user_suffix: int | None = Field(default=None, description="用户名唯一数字后缀")
    last_login_time: datetime | None = Field(default=None, description="最后登录时间")
    created_at: datetime | None = Field(default=None, description="创建时间")
    deleted_at: datetime | None = Field(default=None, description="删除时间")


class TableUsersDeleteWhereSchema(StrictBaseModel):
    """ 用户主表 Delete WHERE Schema """
    user_id: int | None = Field(default=None, description="用户内部ID（主键）")
    user_name: str | None = Field(default=None, min_length=4, max_length=64,  description="用户名")
    user_suffix: int | None = Field(default=None, description="用户名唯一数字后缀")
    status: UserStatus | None = Field(default=None, description="用户状态")
    deleted_at: datetime | None = Field(default=None, description="删除时间")
    
    @model_validator(mode="after")
    def validate_all(self) -> 'TableUsersDeleteWhereSchema':
        # 1. 至少提供一个字段
        if not any([self.user_id, self.user_name, self.user_suffix, self.status, self.deleted_at]):
            raise ValueError("至少需要提供一个定位删除的字段（user_id、user_name、user_suffix、status或deleted_at）")

        # 2. user_id 和 (user_name + user_suffix) 不能同时出现
        if self.user_id is not None and self.user_name is not None and self.user_suffix is not None:
            raise ValueError("不能同时提供 user_id 和 (user_name + user_suffix)")
        
        # 3. user_name 与 user_suffix 要么都提供，要么都不提供
        if (self.user_name is not None) != (self.user_suffix is not None):
            raise ValueError("如果提供了 user_name，则必须同时提供 user_suffix，反之亦然")

        return self
    

class TableUsersQueryWhereSchema(StrictBaseModel):
    """ 用于查询 users 表的筛选条件（WHERE 部分）"""
    user_id: Optional[int] = Field(None, description="用户ID")
    user_uuid: Optional[str] = Field(None, description="UUID")
    status: Optional[UserStatus] = Field(None, description="用户状态")
    account: Optional[str] = Field(None, description="账号")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    
"""

### 2. 用户扩展资料 (`user_profile`)
| 字段名                        | 类型                                                                      | 描述          |
| ---------------------        | ----------------------------------------------------------------          | ----------- |
| `user_id`                    | `INT UNSIGNED PRIMARY KEY FK`                                             | 用户ID（主键+外键） |
| `profile_picture_path`        | `VARCHAR(512) NOT NULL DEFAULT 'Resources/img/nahida.jpg'`                | 头像URL地址     |
| `signature`                  | `VARCHAR(255) DEFAULT NULL`                                               | 用户个性签名      |
| `created_at`                 | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`                             | 创建时间        |
| `updated_at`                 | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 修改时间        |
| `profile_picture_updated_at` | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP `                            | 头像URL地址修改时间   |

CREATE TABLE user_profile (
  user_id INT UNSIGNED PRIMARY KEY,
  profile_picture_path VARCHAR(512) NOT NULL DEFAULT 'Resources/img/nahida.jpg',
  signature VARCHAR(255) DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  profile_picture_updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_user_profile_user_id FOREIGN KEY (user_id) 
    REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);  

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


"""
class TableUserProfileSchema(StrictBaseModel):
    """ 用户扩展资料 Schema"""
    user_id: int
    profile_picture_path: str
    signature: str | None
    created_at: datetime
    updated_at: datetime
    profile_picture_updated_at: datetime



class TableUserProfileInsertSchema(StrictBaseModel):
    """  
    用户扩展资料 Insert Schema 
    注意：user_id 为主键+外键，由调用方从 users 表插入后获取 user_id 后再插入本表。
    """
    user_id: int = Field(..., description="用户ID（主键+外键）")
    profile_picture_path: str | None = Field(default=None, description="头像URL地址")
    signature: str | None = Field(default=None,max_length=255, description="用户个性签名")

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
    

class TableUserProfileUpdateSetSchema(StrictBaseModel):
    """  用户扩展资料 Update SET Schema """
    profile_picture_path: str | None = Field(default=None, description="头像URL地址")
    signature: str | None = Field(default=None, max_length=255, description="用户个性签名")
    
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
    def at_least_one_field_must_be_present(self) -> 'TableUserProfileUpdateSetSchema':
        if not (self.profile_picture_path or self.signature):
            raise ValueError("至少需要提供一个要更新的字段（头像URL(profile_picture_path)或签名(signature)）")
        return self
    
    
class TableUserProfileUpdateWhereSchema(StrictBaseModel):
    """  用户扩展资料 Update WHERE Schema """
    user_id: int = Field(..., description="用户ID（主键+外键）")
    

class TableUserProfileDeleteSchema(StrictBaseModel):
    """ 用户扩展资料 Delete Schema """
    user_id: int = Field(..., description="用户ID（主键+外键）")# 因为是删除，需要user_id来定位删除的位置


class TableUserProfileQueryWhereSchema(StrictBaseModel):
    """ 用户扩展资料 Query WHERE Schema """
    user_id: int | None = Field(default=None, description="用户ID（主键+外键）")

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

class TableUserLoginLogsSchema(StrictBaseModel):
    """ 用户登录日志 """
    login_id: int 
    user_id: int 
    login_time: datetime 
    ip_address: IPvAnyAddress
    agent: str 
    device: str 
    os: str 
    login_success: bool 
    created_at: datetime
    updated_at: datetime 


class TableUserLoginLogsInsertSchema(StrictBaseModel):
    """ 用户登录日志 Insert Schema """
    user_id: int = Field(..., description="用户ID（外键）")
    ip_address: IPvAnyAddress = Field(..., description="登录IP地址")
    agent: str = Field(..., description="浏览器代理")
    device: str = Field(..., description="登录设备")
    os: str = Field(..., description="操作系统")
    login_success: bool = Field(..., description="登录是否成功")
   
   
class TableUserLoginLogsDeleteWhereSchema(StrictBaseModel):
    """ 用户登录日志 Delete WHERE Schema """
    login_id: int | None = Field(default=None, description="日志ID（主键）")
    user_id: int | None = Field(default=None, description="用户ID（外键）") 
    login_time: datetime | None = Field(default=None, description="登录时间")
    login_success: bool | None = Field(default=None, description="登录是否成功")
    created_at: datetime | None = Field(default=None, description="创建时间")
    
    @model_validator(mode="after")
    def validate_all(self) -> 'TableUserLoginLogsDeleteWhereSchema':
        if not (self.user_id or self.login_id or self.login_time or self.login_success or self.created_at):
            raise ValueError("至少需要提供一个要删除的 WHERE 字段（user_id、login_id、login_time、login_success或created_at）")
        return self


class TableUserLoginLogsQueryWhereSchema(StrictBaseModel):
    """ 用户登录日志 Query WHERE Schema """
    login_id: int | None = Field(default=None, description="日志ID（主键）")
    user_id: int | None = Field(default=None, description="用户ID（外键）")
    login_time: datetime | None = Field(default=None, description="登录时间")
    login_success: bool | None = Field(default=None, description="登录是否成功")
    created_at: datetime | None = Field(default=None, description="创建时间")

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
    

class TableUserSettingsSchema(StrictBaseModel):
    """ 用户自定义设置 """
    user_id: int
    language: UserLanguage 
    configure: dict 
    notification_setting: dict
    created_at: datetime 
    updated_at: datetime 


class TableUserSettingsInsertSchema(StrictBaseModel):
    """ 用户自定义设置 Insert Schema """
    user_id: int = Field(..., description="用户ID（主键+外键）")
    language: UserLanguage = Field(..., description="用户语言偏好")
    configure: dict = Field(..., description="用户配置")
    notification_setting: dict = Field(..., description="用户通知设置")
    
    
class TableUserSettingsUpdateSetSchema(StrictBaseModel):
    """ 用户自定义设置 Update SET Schema """
    language: UserLanguage | None = Field(default=None, description="用户语言偏好")
    configure: dict | None = Field(default=None, description="用户配置")
    notification_setting: dict | None = Field(default=None, description="用户通知设置")
    
    @model_validator(mode="after")
    def at_least_one_field_must_be_present(self) -> 'TableUserSettingsUpdateSetSchema':
        if not (self.language or self.configure or self.notification_setting):
            raise ValueError("至少需要提供一个要更新的字段（language、configure或notification_setting）")
        return self


class TableUserSettingsUpdateWhereSchema(StrictBaseModel):
    """ 用户自定义设置 Update WHERE Schema """
    user_id: int = Field(..., description="用户ID（主键+外键）")
    

class TableUserSettingsDeleteWhereSchema(StrictBaseModel):
    """ 用户自定义设置 Delete WHERE Schema """
    user_id: int = Field(..., description="用户ID（主键+外键）")


class TableUserSettingsQueryWhereSchema(StrictBaseModel):
    """ 用户自定义设置 Query WHERE Schema """
    user_id: int | None = Field(default=None, description="用户ID（主键+外键）")
    language: UserLanguage | None = Field(default=None, description="用户语言偏好")
    configure: dict | None = Field(default=None, description="用户配置")
    notification_setting: dict | None = Field(default=None, description="用户通知设置")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="修改时间")

"""

### 5. 用户账户行为 (`user_account_actions`)
| 字段名                       | 类型                                                                      | 描述       |
| --------------------------- | ----------------------------------------------------------------          | -------- |
| `action_id`                 | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                                 | 主键       |
| `user_id`                   | `INT UNSIGNED NOT NULL FK`                                                | 用户ID（外键） |
| `action_type`               | `VARCHAR(255) NOT NULL`                                                   | 用户账户操作类型   |
| `action_detail`             | `VARCHAR(512) NOT NULL`                                                   | 用户账户操作细节   |
| `created_at`                | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`                             | 创建时间     |
| `updated_at`                | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间     |

CREATE TABLE user_account_actions (
  action_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL,
  action_type VARCHAR(255) NOT NULL,
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
    

class TableUserAccountActionsSchema(StrictBaseModel):
    """ 用户账户行为 """
    action_id: int 
    user_id: int 
    action_type: UserAccountActionType 
    action_detail: str 
    created_at: datetime 
    updated_at: datetime 


class TableUserAccountActionsInsertSchema(StrictBaseModel):
    """ 用户账户行为 Insert Schema """
    user_id: int = Field(..., description="用户ID（外键）")
    action_type: UserAccountActionType = Field(..., description="用户账户操作类型")
    action_detail: str = Field(..., max_length=512, description="用户账户操作细节")
    

class TableUserAccountActionsDeleteWhereSchema(StrictBaseModel):
    """ 用户账户行为 Delete Schema """
    user_id: int | None = Field(default=None, description="用户ID（外键）")  # 因为是删除，需要user_id来定位删除的位置
    action_id: int | None = Field(default=None, description="主键")
    created_at: datetime | None = Field(default=None, description="创建时间")
    
    @model_validator(mode="after")
    def at_least_one_field_must_be_present(self) -> 'TableUserAccountActionsDeleteWhereSchema':
        if not (self.user_id or self.action_id or self.created_at):
            raise ValueError("至少需要提供一个要删除的字段（user_id、action_id或self.created_at）")
        return self
    

class TableUserAccountActionsQueryWhereSchema(StrictBaseModel):
    """ 用户账户行为 Query WHERE Schema """
    action_id: int | None = Field(default=None, description="主键")
    user_id: int | None = Field(default=None, description="用户ID（外键）")
    action_type: UserAccountActionType | None = Field(default=None, description="用户账户操作类型")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")
    
    
"""

### 6. 用户通知与消息 (`user_notifications`)
| 字段名                | 类型                                                                       | 描述       |
| --------------------  | ----------------------------------------------------------------          | -------- |
| `notification_id`     | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                                 | 通知ID（主键） |
| `user_id`             | `INT UNSIGNED NOT NULL FK`                                                | 用户ID（外键） |
| `notification_type`   | `VARCHAR(64) NOT NULL`                                                    | 通知类型     |
| `notification_title`  | `VARCHAR(255) NOT NULL`                                                   | 通知标题     |
| `notification_content`| `TEXT`                                                                    | 通知内容     |
| `is_read`             | `BOOL NOT NULL DEFAULT FALSE`                                            | 是否已读     |
| `created_at`          | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`                             | 创建时间     |
| `updated_at`          | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间     |

CREATE TABLE user_notifications (
  notification_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL,
  notification_type VARCHAR(64) NOT NULL,
  notification_title VARCHAR(255) NOT NULL,
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


class TableUserNotificationsSchema(StrictBaseModel):
    """ 用户通知与消息 Schema"""
    notification_id: int
    user_id: int 
    notification_type: UserNotificationType
    notification_title: str
    notification_content: str
    is_read: bool 
    created_at: datetime
    updated_at: datetime 


class TableUserNotificationsInsertSchema(StrictBaseModel):
    """ 用户通知与消息 Insert Schema """
    user_id: int = Field(..., description="用户ID（外键）")
    notification_type: UserNotificationType = Field(..., description="通知类型")
    notification_title: str = Field(..., description="通知标题")
    notification_content: str = Field(..., description="通知内容")
    is_read: bool = Field(..., description="是否已读")


class TableUserNotificationsUpdateSetSchema(StrictBaseModel):
    """ 用户通知与消息 Update SET Schema """
    notification_type: UserNotificationType | None = Field(default=None, description="通知类型")
    notification_title: str | None = Field(default=None, description="通知标题")
    notification_content: str | None = Field(default=None, description="通知内容")
    is_read: bool | None = Field(default=None, description="是否已读")
    
    @model_validator(mode="after")
    def at_least_one_field_must_be_present(self) -> 'TableUserNotificationsUpdateSetSchema':
        if not (self.notification_type or self.notification_title or self.notification_content or self.is_read):
            raise ValueError("至少需要提供一个要更新的字段（notification_type、notification_title、notification_content或is_read）")
        return self


class TableUserNotificationsUpdateWhereSchema(StrictBaseModel):
    """ 用户通知与消息 Update WHERE Schema """
    user_id: int | None = Field(default=None, description="用户ID（外键）")
    notification_id: int | None = Field(default=None, description="通知ID（主键）")
    is_read: bool | None = Field(default=None, description="是否已读")
    created_at: datetime | None = Field(default=None, description="创建时间")


class TableUserNotificationsDeleteWhereSchema(StrictBaseModel):
    """ 用户通知与消息 Delete WHERE Schema """
    user_id: int | None = Field(default=None, description="用户ID（外键）")  # 因为是删除，需要user_id来定位删除的位置
    notification_id: int | None = Field(default=None, description="通知ID（主键）")
    notification_type: UserNotificationType | None = Field(default=None, description="通知类型")
    notification_title: str | None = Field(default=None, description="通知标题")
    is_read: bool | None = Field(default=None, description="是否已读")
    created_at: datetime | None = Field(default=None, description="创建时间")
    
    @model_validator(mode="after")
    def at_least_one_field_must_be_present(self) -> 'TableUserNotificationsDeleteWhereSchema':
        if not (self.user_id or self.notification_id or self.is_read or self.created_at):
            raise ValueError("至少需要提供一个要删除的字段（user_id、notification_id、is_read或created_at）")
        return self


class TableUserNotificationsQueryWhereSchema(StrictBaseModel):
    """ 用户通知与消息 Query WHERE Schema """
    user_id: int | None = Field(default=None, description="用户ID（外键）")
    notification_id: int | None = Field(default=None, description="通知ID（主键）")
    notification_type: UserNotificationType | None = Field(default=None, description="通知类型")
    notification_title: str | None = Field(default=None, description="通知标题")
    is_read: bool | None = Field(default=None, description="是否已读")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")

"""

### 7. 用户文件 (`user_files`)
| 字段名            | 类型                                                                      | 描述           |
| ---------------- | ----------------------------------------------------------------          | ------------ |
| `file_id`        | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                                 | 文件ID         |
| `user_id`        | `INT UNSIGNED NOT NULL FK`                                                | 用户ID（外键）     |
| `file_path`      | `VARCHAR(512) NOT NULL`                                                   | 文件相对路径       |
| `file_name`      | `VARCHAR(255) NOT NULL`                                                   | 原始文件名        |
| `file_type`      | `VARCHAR(255) NOT NULL`                                                   | 文件类型（如 .png） |
| `file_size`      | `BIGINT UNSIGNED NOT NULL`                                                | 文件大小         |
| `upload_time`    | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP `                            | 上传时间         |
| `is_deleted`     | `BOOL DEFAULT FALSE NOT NULL`                                             | 是否删除         |
| `created_at`     | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`                             | 创建时间         |
| `updated_at`     | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间         |

CREATE TABLE user_files (
  file_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL,
  file_path VARCHAR(512) NOT NULL,
  file_name VARCHAR(255) NOT NULL,
  file_type VARCHAR(255) NOT NULL,
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
class TableUserFilesSchema(StrictBaseModel):
    """ 用户文件 Schema """
    file_id: int
    user_id: int 
    file_name: str 
    file_path: str 
    file_type: str 
    file_size: int 
    upload_time: datetime 
    is_deleted: bool 
    created_at: datetime 
    updated_at: datetime 


class TableUserFilesInsertSchema(StrictBaseModel):
    """ 用户文件 Insert Schema """
    user_id: int = Field(..., description="用户ID（外键）")
    file_path: str = Field(..., min_length=1, max_length=512, description="文件相对路径")
    file_name: str = Field(..., min_length=1, max_length=255, description="原始文件名")
    file_type: str = Field(..., min_length=1, max_length=255, description="文件类型（如 .png）")
    file_size: int = Field(..., description="文件大小")
    upload_time: datetime = Field(..., description="上传时间") 
    is_deleted: bool = Field(default=False, description="是否删除")
    
    
class TableUserFilesUpdateSetSchema(StrictBaseModel):
    """ 用户文件 Update SET Schema """
    file_path: str | None = Field(default=None, min_length=1, max_length=512, description="文件相对路径")
    file_name: str | None = Field(default=None, min_length=1, max_length=255, description="原始文件名")
    file_type: str | None = Field(default=None, min_length=1, max_length=255, description="文件类型（如 .png）")
    file_size: int | None = Field(default=None, description="文件大小")
    upload_time: datetime | None = Field(default=None, description="上传时间")
    is_deleted: bool | None = Field(default=None, description="是否删除")

    @model_validator(mode="after")
    def at_least_one_field_must_be_present(self) -> 'TableUserFilesUpdateSetSchema':
        if not (self.file_path or self.file_name or self.file_type or self.file_size or self.is_deleted or self.upload_time):
            raise ValueError("至少需要提供一个要更新的字段（file_path、file_name、file_type、file_size、is_deleted或upload_time）")
        return self

class TableUserFilesUpdateWhereSchema(StrictBaseModel):
    """ 用户文件 Update WHERE Schema """
    file_id: int | None = Field(default=None, description="文件ID（主键）")
    user_id: int | None = Field(default=None, description="用户ID（外键）")
    file_type: str | None = Field(default=None, min_length=1, max_length=255, description="文件类型（如 .png）")
    is_deleted: bool | None = Field(default=None, description="是否删除")
    created_at: datetime | None = Field(default=None, description="创建时间")
    upload_time: datetime | None = Field(default=None, description="上传时间")
    

class TableUserFilesDeleteSchema(StrictBaseModel):
    """ 用户文件 Delete Schema """
    user_id: int | None = Field(default=None, description="用户ID（外键）")  
    file_id: int | None = Field(default=None, description="文件ID（主键）")
    upload_time: datetime | None = Field(default=None, description="上传时间")
    created_at: datetime | None = Field(default=None, description="创建时间")
    is_deleted: bool | None = Field(default=None, description="是否删除")

    @model_validator(mode="after")
    def at_least_one_field_must_be_present(self) -> 'TableUserFilesDeleteSchema':
        if not (self.user_id or self.file_id or self.upload_time or self.created_at or self.is_deleted):
            raise ValueError("至少需要提供一个要删除的字段（user_id、file_id、upload_time、created_at、is_deleted）")
        return self


class TableUserFilesQueryWhereSchema(StrictBaseModel):
    """ 用户文件 Query WHERE Schema """
    file_id: int | None = Field(default=None, description="文件ID（主键）")
    user_id: int | None = Field(default=None, description="用户ID（外键）")
    file_name: str | None = Field(default=None, min_length=1, max_length=255, description="原始文件名")
    file_type: str | None = Field(default=None, min_length=1, max_length=255, description="文件类型（如 .png）")
    file_size: int | None = Field(default=None, description="文件大小")
    is_deleted: bool | None = Field(default=None, description="是否删除")
    created_at: datetime | None = Field(default=None, description="创建时间")
    upload_time: datetime | None = Field(default=None, description="上传时间")

"""

# TODO 将conversations 和conversations_messages 抽离出来放在一个单独的数据库，并且单独写一个封装类来操作
### 8. 会话表(`conversations`)
| 字段名             | 类型                                                                      | 说明          |
| ----------------- | ----------------------------------------------------------------          | ----------- |
| `conversation_id` | `BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                              | 会话 ID       |
| `user_id`         | `INT UNSIGNED NOT NULL FK`                                                | 用户内部 ID（外键） |
| `title`           | `VARCHAR(255) NOT NULL`                                                   | 会话标题        |
| `message_count`   | `INT UNSIGNED NOT NULL DEFAULT 0`                                         | 消息数量        |
| `created_at`      | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`                             | 创建时间        |
| `updated_at`      | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 修改时间        |

CREATE TABLE conversations (
    conversation_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    message_count INT UNSIGNED NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_conversations_user_id FOREIGN KEY (user_id) 
      REFERENCES users(user_id)
      ON DELETE CASCADE ON UPDATE CASCADE
);


"""
class TableConversationsSchema(StrictBaseModel):
    """ 会话表 """
    conversation_id: int = Field(..., description="会话 ID")
    user_id: int = Field(..., description="用户内部 ID（外键）")
    title: str = Field(..., description="会话标题")
    message_count: int = Field(..., description="消息数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="修改时间")


class TableConversationsInsertSchema(StrictBaseModel):
    """ 会话表 Insert Schema """
    user_id: int = Field(..., description="用户内部 ID（外键）")
    title: str = Field(..., description="会话标题")
    message_count: int = Field(default=0, description="消息数量")


class TableConversationsUpdateSchema(StrictBaseModel):
    """ 会话表 Update Schema """
    title: str | None = Field(default=None, min_length=1, max_length=255, description="会话标题")
    message_count: int | None = Field(default=None, description="消息数量")

    @model_validator(mode="after")
    def at_least_one_field_must_be_present(self) -> 'TableConversationsUpdateSchema':
        if not (self.title or self.message_count):
            raise ValueError("至少需要提供一个要更新的字段（title、message_count）")
        return self
    

class TableConversationsDeleteSchema(StrictBaseModel): 
    """ 会话表 Delete Schema """
    conversation_id: int | None = Field(default=None, description="会话 ID")  # 因为是删除，需要conversation_id来定位删除的位置
    user_id: int | None = Field(default=None, description="用户内部 ID（外键）")
    
    @model_validator(mode="after")
    def at_least_one_field_must_be_present(self) -> 'TableConversationsDeleteSchema':
        if not (self.conversation_id or self.user_id):
            raise ValueError("至少需要提供一个要删除的字段（conversation_id或user_id）")
        return self
    
"""

### 9. 会话消息表(`conversation_messages`)
| 字段名             | 类型                                                              | 说明        |
| -----------------  | ---------------------------------------------------------------- | --------- |
| `message_id`       | `BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                     | 消息 ID     |
| `conversation_id`  | `INT UNSIGNED NOT NULL FK`                                       | 会话 ID（外键） |
| `user_id`          | `INT UNSIGNED NOT NULL FK`                                       | 用户 ID（外键） |
| `sender_role`      | `VARCHAR(64) NOT NULL`                                           | 角色        |
| `message_type`     | `VARCHAR(255) NOT NULL`                                          | 信息类型      |
| `parent_message_id`| `BIGINT UNSIGNED DEFAULT NULL`                                   | 父消息 ID（外键） |
| `content`          | `TEXT DEFAULT NULL`                                              | 内容        |
| `token_count`      | `INT UNSIGNED NOT NULL`                                          | 消息 Token 数（用于统计消耗） |
| `created_at`       | `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`                    | 创建时间      |

CREATE TABLE conversation_messages (
    message_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    conversation_id BIGINT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    sender_role VARCHAR(64) NOT NULL,
    message_type VARCHAR(255) NOT NULL,
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
    

class TableConversationMessagesSchema(StrictBaseModel):
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



class TableConversationMessagesInsertSchema(StrictBaseModel):
    """ 会话消息表 Insert Schema """
    conversation_id: int = Field(..., description="会话 ID（外键）")
    user_id: int = Field(..., description="用户 ID（外键）")
    sender_role: SenderRole = Field(..., description="角色")
    message_type: ConversationMessageType = Field(..., description="信息类型")
    parent_message_id: int | None = Field(..., description="父消息 ID（外键）")
    content: str | None = Field(..., description="内容")
    token_count: int = Field(..., description="消息 Token 数（用于统计消耗）")
    
    
class TableConversationMessagesDeleteSchema(StrictBaseModel):
    """ 会话消息表 Delete Schema """
    message_id: int | None = Field(default=None, description="消息 ID")  # 因为是删除，需要message_id来定位删除的位置
    conversation_id: int | None = Field(default=None, description="会话 ID（外键）")
    user_id: int | None = Field(default=None, description="用户 ID（外键）")
    
    @model_validator(mode="after")
    def at_least_one_field_must_be_present(self) -> 'TableConversationMessagesDeleteSchema':
        if not (self.message_id or self.conversation_id or self.user_id):
            raise ValueError("至少需要提供一个要删除的字段（message_id、conversation_id或user_id）")
        return self   
    
    