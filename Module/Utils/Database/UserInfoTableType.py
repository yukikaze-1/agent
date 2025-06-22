# Project:      Agent
# Author:       yomu
# Time:         2025/6/22
# Version:      0.1
# Description:  User information tables pydantic definition

"""
    用户数据库的各表的pydantic
"""

from enum import StrEnum
from typing import Dict, List, Any
from pydantic import BaseModel, EmailStr, constr, Field, model_validator, constr
from datetime import datetime

"""

## 用户信息数据库设计

### 1. 用户主表 (`users`)
| 字段名             | 类型                                                             | 描述         |
| ----------------- | ---------------------------------------------------------------- | ---------- |
| `user_id`         | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                        | 用户内部ID（主键） |
| `user_uuid`       | `CHAR(36) NOT NULL UNIQUE`                                       | 用户UUID     |
| `status`          | `ENUM('inactive', 'active','deleted') NOT NULL DEFAULT 'active'` | 用户状态       |
| `account`         | `VARCHAR(256) NOT NULL UNIQUE`                                   | 用户账号       |
| `password_hash`   | `VARCHAR(256) NOT NULL`                                          | 密码哈希值      |
| `email`           | `VARCHAR(256) NOT NULL UNIQUE`                                   | 用户邮箱       |
| `last_login_time` | `DATETIME`                                                       | 最后登录时间     |
| `last_login_ip`   | `VARCHAR(256)`                                                   | 最后登录IP     |
| `session_token`   | `VARCHAR(2048)`                                                  | Session令牌  |
| `file_folder_path`| `VARCHAR(512) NOT NULL`                                          | 用户个人文件夹(默认为UUID为命名)  |
| `created_at`      | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间       |
| `updated_at`      | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 修改时间
| `deleted_at`      | `DATETIME DEFAULT NULL`                                          | 删除时间 |

CREATE TABLE users (
  user_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_uuid CHAR(36) NOT NULL UNIQUE,
  status ENUM('inactive', 'active', 'deleted') NOT NULL DEFAULT 'active',
  account VARCHAR(256) NOT NULL UNIQUE,
  password_hash VARCHAR(256) NOT NULL,
  email VARCHAR(256) NOT NULL UNIQUE,
  last_login_time DATETIME,
  last_login_ip VARCHAR(256),
  session_token VARCHAR(2048),
  file_folder_path VARCHAR(512)  NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at DATETIME DEFAULT NULL
);
"""

class UserStatus(StrEnum):
    inactive = "inactive"
    active = "active"
    deleted = "deleted"

class TableUsers(BaseModel):
    """ 用户主表 """
    user_id: int = Field(..., description="用户内部ID（主键）")
    user_uuid: str = Field(min_length=36, max_length=36, description="用户UUID")
    status: UserStatus = Field(..., description="用户状态")
    account: str = Field(min_length=1, max_length=256, description="用户账号")
    password_hash: str= Field(min_length=1, max_length=256, description="密码哈希值")
    email: EmailStr = Field(..., description="用户邮箱")
    last_login_time: str | None = Field(default=None, description="最后登录时间")
    last_login_ip: str | None = Field(default=None, description="最后登录IP")
    session_token: str | None = Field(default=None, description="Session令牌")
    file_folder_path: str = Field(min_length=1, max_length=256, description="用户个人文件夹路径")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="修改时间")
    deleted_at: str | None = Field(default=None, description="删除时间")

"""

### 2. 用户扩展资料 (`user_profile`)
| 字段名                        | 类型                                                             | 描述          |
| ---------------------        | ---------------------------------------------------------------- | ----------- |
| `user_id`                    | `INT UNSIGNED PRIMARY KEY FK`                                    | 用户ID（主键+外键） |
| `user_name`                  | `VARCHAR(256) NOT NULL`                                          | 用户名         |
| `profile_picture_url`        | `VARCHAR(512) NOT NULL DEFAULT 'Resources/img/nahida.jpg'`       | 头像URL地址     |
| `signature`                  | `VARCHAR(256) DEFAULT NULL`                                      | 用户个性签名      |
| `created_at`                 | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间        |
| `updated_at`                 | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 修改时间        |
| `profile_picture_updated_at` | `DATETIME DEFAULT CURRENT_TIMESTAMP `                            | 头像URL地址修改时间   |

CREATE TABLE user_profile (
  user_id INT UNSIGNED PRIMARY KEY,
  user_name VARCHAR(256) NOT NULL,
  profile_picture_url VARCHAR(512) NOT NULL DEFAULT 'Resources/img/nahida.jpg',
  signature VARCHAR(256) DEFAULT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  profile_picture_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_user_profile_user_id FOREIGN KEY (user_id) 
    REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
    
  DELIMITER $$

  CREATE TRIGGER trg_update_profile_picture_time
  BEFORE UPDATE ON user_profile
  FOR EACH ROW
  BEGIN
    -- 如果头像字段发生了变化
    IF NOT (NEW.profile_picture_url <=> OLD.profile_picture_url) THEN
        SET NEW.profile_picture_updated_at = CURRENT_TIMESTAMP;
    END IF;
  END$$  
  DELIMITER ;
);

"""
class TableUserProfile(BaseModel):
    """ 用户扩展资料 """
    user_id: int = Field(..., description="用户ID（主键+外键）")
    user_name: str = Field(min_length=1, max_length=256, description="用户名")
    profile_picture_url: str = Field(min_length=1, max_length=512, default="Resources/img/nahida.jpg", description="头像URL地址")
    signature: str | None = Field(default=None, max_length=256, description="用户个性签名")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="修改时间")
    profile_picture_updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="头像URL地址修改时间")

"""

# TODO 将该表修改为只读
### 3. 用户登录认证 (`user_login_logs`)
| 字段名           | 类型                                                             | 描述       |
| --------------- | ---------------------------------------------------------------- | -------- |
| `login_id`      | `BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                     | 日志主键     |
| `user_id`       | `INT UNSIGNED NOT NULL`                                          | 用户ID（外键） |
| `login_time`    | `DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL`                    | 登陆时间     |
| `ip_address`    | `VARCHAR(256) NOT NULL`                                          | 登陆IP      |
| `agent`         | `VARCHAR(512) NOT NULL`                                          | 浏览器代理    |
| `device`        | `VARCHAR(512) NOT NULL`                                          | 登录设备     |
| `os`            | `VARCHAR(512) NOT NULL`                                          | 操作系统     |
| `login_success` | `BOOL DEFAULT FALSE NOT NULL`                                    | 是否成功登录   |
| `created_at`    | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间     |
| `updated_at`    | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间     |

CREATE TABLE user_login_logs (
  login_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL,
  login_time DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
  ip_address VARCHAR(256) NOT NULL,
  agent VARCHAR(512) NOT NULL,
  device VARCHAR(512) NOT NULL,
  os VARCHAR(512) NOT NULL,
  login_success BOOL DEFAULT FALSE NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_login_logs_user_id FOREIGN KEY (user_id) 
    REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

"""

class TableUserLoginLogs(BaseModel):
    """ 用户登录日志 """
    login_id: int = Field(..., description="日志ID（主键）")
    user_id: int = Field(..., description="用户ID（外键）")
    login_time: str = Field(default_factory=lambda: datetime.now().isoformat(), description="登录时间")
    ip_address: str = Field(..., description="登录IP地址")
    agent: str = Field(..., description="浏览器代理")
    device: str = Field(..., description="登录设备")
    os: str = Field(..., description="操作系统")
    login_success: bool = Field(default=False, description="登录是否成功")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="修改时间")

"""

### 4. 用户自定义设置 (`user_settings`)
| 字段名                  | 类型                                                             | 描述          |
| ---------------------- | ---------------------------------------------------------------- | ----------- |
| `user_id`              | `INT UNSIGNED PRIMARY KEY FK`                                    | 用户ID（主键+外键） |
| `language`             | `ENUM('zh', 'en', 'jp') NOT NULL DEFAULT 'zh'`                   | 用户语言偏好      |
| `configure`            | `JSON NOT NULL`                                                  | 用户配置    |
| `notification_setting` | `JSON NOT NULL`                                                  | 用户通知设置      |
| `created_at`           | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间        |
| `updated_at`           | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间        |

CREATE TABLE user_settings (
  user_id INT UNSIGNED PRIMARY KEY,
  language ENUM('zh', 'en', 'jp') NOT NULL DEFAULT 'zh',
  configure JSON NOT NULL,
  notification_setting JSON NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_user_settings_user_id FOREIGN KEY (user_id) 
    REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

"""

class TableUserSettings(BaseModel):
    """ 用户自定义设置 """
    user_id: int = Field(..., description="用户ID（主键+外键）")
    language: str = Field(..., description="用户语言偏好")
    configure: dict = Field(..., description="用户配置")
    notification_setting: dict = Field(..., description="用户通知设置")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="修改时间")

"""

# TODO 将该表修改为只读
### 5. 用户账户行为 (`user_account_actions`)
| 字段名                       | 类型                                                             | 描述       |
| --------------------------- | ---------------------------------------------------------------- | -------- |
| `action_id`                 | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                        | 主键       |
| `user_id`                   | `INT UNSIGNED NOT NULL FK`                                       | 用户ID（外键） |
| `action_type`               | `VARCHAR(256) NOT NULL`                                          | 用户账户操作类型   |
| `action_detail`             | `VARCHAR(512) NOT NULL`                                          | 用户账户操作细节   |
| `created_at`                | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间     |
| `updated_at`                | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间     |

CREATE TABLE user_account_actions (
  action_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL,
  action_type VARCHAR(256) NOT NULL,
  action_detail VARCHAR(512) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_user_actions_user_id FOREIGN KEY (user_id) 
    REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

"""
class TableUserAccountActions(BaseModel):
    """ 用户账户行为 """
    action_id: int = Field(..., description="主键")
    user_id: int = Field(..., description="用户ID（外键）")
    action_type: str = Field(..., description="用户账户操作类型")
    action_detail: str = Field(..., description="用户账户操作细节")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="更新时间")

"""

### 6. 用户通知与消息 (`user_notifications`)
| 字段名                | 类型                                                             | 描述       |
| --------------------  | ---------------------------------------------------------------- | -------- |
| `notification_id`     | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                        | 通知ID（主键） |
| `user_id`             | `INT UNSIGNED NOT NULL FK`                                       | 用户ID（外键） |
| `notification_type`   | `ENUM('system', 'security', 'promotion') NOT NULL`               | 通知类型     |
| `notification_title`  | `VARCHAR(256) NOT NULL`                                          | 通知标题     |
| `notification_content`| `TEXT`                                                           | 通知内容     |
| `is_read`             | `BOOL DEFAULT FALSE`                                             | 是否已读     |
| `created_at`          | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间     |
| `updated_at`          | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间     |

CREATE TABLE user_notifications (
  notification_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL,
  notification_type ENUM('system', 'security', 'promotion') NOT NULL,
  notification_title VARCHAR(256) NOT NULL,
  notification_content TEXT,
  is_read BOOL DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_user_notifications_user_id FOREIGN KEY (user_id) 
    REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

"""
class TableUserNotifications(BaseModel):
    """ 用户通知与消息 """
    notification_id: int = Field(..., description="通知ID（主键）")
    user_id: int = Field(..., description="用户ID（外键）")
    notification_type: str = Field(..., description="通知类型")
    notification_title: str = Field(..., description="通知标题")
    notification_content: str | None = Field(default=None, description="通知内容")
    is_read: bool = Field(default=False, description="是否已读")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="更新时间")

"""

### 7. 用户文件 (`user_files`)
| 字段名            | 类型                                                             | 描述           |
| ---------------- | ---------------------------------------------------------------- | ------------ |
| `file_id`        | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                        | 文件ID         |
| `user_id`        | `INT UNSIGNED NOT NULL FK`                                       | 用户ID（外键）     |
| `file_path`      | `VARCHAR(512) NOT NULL`                                          | 文件相对路径       |
| `file_name`      | `VARCHAR(256) NOT NULL`                                          | 原始文件名        |
| `file_type`      | `VARCHAR(256) NOT NULL`                                          | 文件类型（如 .png） |
| `upload_time`    | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 上传时间         |
| `file_size`      | `BIGINT UNSIGNED NOT NULL`                                       | 文件大小         |
| `is_deleted`     | `BOOL DEFAULT FALSE NOT NULL`                                    | 是否删除         |
| `created_at`     | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间         |
| `updated_at`     | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间         |

CREATE TABLE user_files (
  file_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL,
  file_path VARCHAR(512) NOT NULL,
  file_name VARCHAR(256) NOT NULL,
  file_type VARCHAR(256) NOT NULL,
  upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  file_size BIGINT UNSIGNED NOT NULL,
  is_deleted BOOL DEFAULT FALSE NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_user_files_user_id FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

"""
class TableUserFiles(BaseModel):
    """ 用户文件 """
    file_id: int = Field(..., description="文件ID")
    user_id: int = Field(..., description="用户ID（外键）")
    file_path: str = Field(min_length=1, max_length=512, description="文件相对路径")
    file_name: str = Field(min_length=1, max_length=256, description="原始文件名")
    file_type: str = Field(min_length=1, max_length=256, description="文件类型（如 .png）")
    upload_time: str = Field(default_factory=lambda: datetime.now().isoformat(), description="上传时间")
    file_size: int = Field(..., description="文件大小")
    is_deleted: bool = Field(default=False, description="是否删除")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="更新时间")

"""

# TODO 将conversations 和conversations_messages 抽离出来放在一个单独的数据库，并且单独写一个封装类来操作
### 8. 会话表(`conversations`)
| 字段名             | 类型                                                             | 说明          |
| ----------------- | ---------------------------------------------------------------- | ----------- |
| `conversation_id` | `BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                     | 会话 ID       |
| `user_id`         | `INT UNSIGNED NOT NULL FK`                                       | 用户内部 ID（外键） |
| `title`           | `VARCHAR(256) NOT NULL`                                          | 会话标题        |
| `created_at`      | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间        |
| `updated_at`      | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 修改时间        |

CREATE TABLE conversations (
    conversation_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    title VARCHAR(256) NOT NULL,        
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_conversations_user_id FOREIGN KEY (user_id) 
      REFERENCES users(user_id)
      ON DELETE CASCADE ON UPDATE CASCADE
);


"""
class TableConversations(BaseModel):
    """ 会话表 """
    conversation_id: int = Field(..., description="会话 ID")
    user_id: int = Field(..., description="用户内部 ID（外键）")
    title: str = Field(min_length=1, max_length=256, description="会话标题")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="修改时间")

"""

### 9. 会话消息表(`conversation_messages`)
| 字段名             | 类型                                                    | 说明        |
| -----------------  | ------------------------------------------------------- | --------- |
| `message_id`       | `BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY`            | 消息 ID     |
| `conversation_id`  | `INT UNSIGNED NOT NULL FK`                              | 会话 ID（外键） |
| `user_id`          | `INT UNSIGNED NOT NULL FK`                              | 用户 ID（外键） |
| `sender_role`      | `ENUM('user', 'assistant', 'system') NOT NULL`          | 角色        |
| `message_type`     | `ENUM('text', 'image', 'file', 'audio') DEFAULT 'text'` | 信息类型      |
| `parent_message_id`| `BIGINT UNSIGNED DEFAULT NULL`                          | 父消息 ID（外键） |
| `content`          | `TEXT DEFAULT NULL`                                     | 内容        |
| `token_count`      | `INT UNSIGNED`                                          | 消息 Token 数（用于统计消耗） |
| `created_at`       | `DATETIME DEFAULT CURRENT_TIMESTAMP`                    | 创建时间      |

CREATE TABLE conversation_messages (
    message_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    conversation_id BIGINT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    sender_role ENUM('user', 'assistant', 'system') NOT NULL,
    message_type ENUM('text', 'image', 'file', 'audio') DEFAULT 'text',
    parent_message_id BIGINT UNSIGNED DEFAULT NULL,
    content TEXT DEFAULT NULL,
    token_count INT UNSIGNED,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

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

class TableConversationMessages(BaseModel):
    """ 会话消息表 """
    message_id: int = Field(..., description="消息 ID")
    conversation_id: int = Field(..., description="会话 ID（外键）")
    user_id: int = Field(..., description="用户 ID（外键）")
    sender_role: str = Field(..., description="角色")
    message_type: str = Field(default="text", description="信息类型")
    parent_message_id: int | None = Field(default=None, description="父消息 ID（外键）")
    content: str | None = Field(default=None, description="内容")
    token_count: int = Field(..., description="消息 Token 数（用于统计消耗）")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")


