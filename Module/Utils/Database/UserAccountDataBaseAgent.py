# Project:      Agent
# Author:       yomu
# Time:         2024/12/12
# Version:      0.1
# Description:  agent User information database initialize

"""
    用户账户数据库
"""
import httpx
import uuid
import re
import json
from typing import Tuple, Optional, Dict, List, Any
from dotenv import dotenv_values
from logging import Logger
from fastapi import HTTPException
from datetime import datetime


from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config
from Module.Utils.FormatValidate import is_email, is_account_name
from Module.Utils.Database.MySQLHelper import MySQLHelper

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

---

### 2. 用户扩展资料 (`user_profile`)
| 字段名                 | 类型                                                             | 描述          |
| --------------------- | ---------------------------------------------------------------- | ----------- |
| `user_id`             | `INT UNSIGNED PRIMARY KEY FK`                                    | 用户ID（主键+外键） |
| `user_name`           | `VARCHAR(256) NOT NULL`                                          | 用户名         |
| `profile_picture_url` | `VARCHAR(512) NOT NULL DEFAULT 'Resources/img/nahida.jpg'`                | 头像URL地址     |
| `signature`           | `VARCHAR(256) DEFAULT NULL`                                      | 用户个性签名      |
| `created_at`          | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间        |
| `updated_at`          | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 修改时间        |

CREATE TABLE user_profile (
  user_id INT UNSIGNED PRIMARY KEY,
  user_name VARCHAR(256) NOT NULL,
  profile_picture_url VARCHAR(512) NOT NULL DEFAULT 'Resources/img/nahida.jpg',
  signature VARCHAR(256) DEFAULT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_user_profile_user_id FOREIGN KEY (user_id) 
    REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

---

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

---

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

---

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

---

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

---

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


class UserAccountDataBaseAgent():
    """
        数据库:userinfo
        
        配置文件为config.yml,配置文件路径存放在Init/.env中的的INIT_CONFIG_PATH变量中
            配置内容为：
                user_account_database_config：
                    host
                    port
                    user
                    password
                    database
                    charset
                                
        # 需要手动在mysql数据库中创建用户信息数据库 
          TODO 应该让程序自动创建一个数据库，待实现
        (注：1.要先手动创建一个名为userinfo的database才行 2. 创建表的SQL语句见本文件顶部的注释):    
            1. 用户主表 (`users`)
            2. 用户扩展资料 (`user_profile`)
            3. 用户登录认证 (`user_login_logs`)
            4. 用户自定义设置 (`user_settings`)
            5. 用户账户行为 (`user_account_actions`)
            6. 用户通知与消息 (`user_notifications`)
            7. 用户文件 (`user_files`)
    """
    def __init__(self, logger: Optional[Logger]=None):
        self.logger = logger or setup_logger(name="UserAccountDataBaseAgent", log_path="InternalModule")
        
        # 加载环境变量和配置
        self.env_vars = dotenv_values("/home/yomu/agent/Module/Utils/Database/.env")
        self.config_path = self.env_vars.get("USER_ACCOUNT_DATABASE_AGENT_CONFIG_PATH","")
        self.config = load_config(config_path=self.config_path, config_name='UserAccountDataBaseAgent', logger=self.logger)
        
        # 验证配置文件
        required_keys = [ "mysql_host", "mysql_port", "mysql_agent_url", "mysql_user",  "mysql_password", "database", "table", "charset"]
        validate_config(required_keys, self.config, self.logger)
        
        # MySQL配置
        self.mysql_host = self.config.get("mysql_host", "")
        self.mysql_port = self.config.get("mysql_port", "")
        self.mysql_agent_url = self.config.get("mysql_agent_url", "")
        self.mysql_user = self.config.get("mysql_user", "")
        self.mysql_password = self.config.get("mysql_password", "")  
        self.database = self.config.get("database","")
        self.charset = self.config.get("charset", "") 
        
        # 初始化 AsyncClient
        self.client: httpx.AsyncClient = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(10.0, read=60.0)
        )
        
        # 向MySQLAgent注册，返回一个链接id
        self.connect_id: int = -1

        # 初始化 MySQLHelper
        self.mysql_helper = MySQLHelper(
            mysql_agent_url=self.mysql_agent_url,
            connect_id=self.connect_id,
            client=self.client
        )
        

    async def init_connection(self) -> None:
        """
        真正执行连接, 并为 self.connect_id 赋值
        """
        try:
            self.connect_id = await self.connect_to_database()
            if self.connect_id == -1:
                self.logger.error("Failed to connect to database,connect id == -1")
                raise ValueError("Failed to connect to database,connect id == -1")
            else:
                self.logger.info(f"connect_id = {self.connect_id}")
        except Exception as e:
            self.logger.error(f"Failed to init connection: {e}")
            raise
        
    # ------------------------------------------------------------------------------------------------
    # 功能函数---查询表项目
    # ------------------------------------------------------------------------------------------------     
    """
        查询函数封装在了MySQLHelper中的query_one和query_many中
    """
    # ------------------------------------------------------------------------------------------------
    # 功能函数---插入表项目
    # ------------------------------------------------------------------------------------------------
    async def insert_users(self, user_uuid: str, 
                            account: str, email: str,
                            password_hash: str, user_name: str,
                            file_folder_path: str) -> Optional[int]:
        """
        插入 users 表项目

        :param account: 用户账号（必须）
        :param email: 用户邮箱（必须）
        :param password_hash: 用户密码哈希（必须）
        :param user_name: 用户昵称（必须）
        :param file_folder_path: 用户文件夹路径（必须）

        :return: 成功返回 user_id，失败返回 None
        """
        
        data = {
            "user_uuid": user_uuid,
            "account": account,
            "email": email,
            "password_hash": password_hash,
            "user_name": user_name,
            "file_folder_path": file_folder_path
        }

        res = await self.mysql_helper.insert_one(table="users", data=data,
                                     success_msg=f"Inserted user info for account: {account}",
                                     warning_msg=f"User info insert may have failed for account: {account}",
                                     error_msg=f"Insert error for account: {account}")
        if not res:
            self.logger.error(f"Failed to insert user info for account: {account}")
            return None

        try:
            user_id = await self.fetch_user_id_by_uuid(user_uuid)
        except Exception as e:
            self.logger.error(f"Failed to fetch user_id for user_uuid: {user_uuid}. Error: {e}")
            return None
        
        if user_id is None:
            self.logger.warning(f"No user found with UUID: {user_uuid}")
            return None
        return user_id
    
    
    async def insert_user_profile(self, user_id: int,
                                  user_name: str)-> bool:
        """
        插入新用户的个人资料信息到 user_profile 表。

        :param user_id: 用户ID
        :param user_name: 用户名

        :return: 插入是否成功
        """
        
        data = {
            "user_id": user_id,
            "user_name": user_name 
        }

        return await self.mysql_helper.insert_one(table="user_profile", data=data,
                            success_msg=f"Inserted user profile.User id: {user_id}",
                            warning_msg=f"User profile insert may have failed.User id: {user_id}",
                            error_msg=f"Insert error.User id: {user_id}")


    async def insert_user_login_logs(self, user_id: int, 
                                     ip_address: str,
                                     agent: str,
                                     device: str,
                                     os: str,
                                     login_success: bool) -> bool:
        """
        插入用户登录日志到 user_login_logs 表

        :param user_id: 用户ID
        :param ip_address: 登录IP地址
        :param agent: 浏览器代理
        :param device: 登录设备
        :param os: 操作系统
        :param login_success: 登录是否成功

        :return: 插入是否成功
        """
        data = {
            "user_id": user_id,
            "ip_address": ip_address,
            "agent": agent,
            "device": device,
            "os": os,
            "login_success": login_success
        }

        return await self.mysql_helper.insert_one(table="user_login_logs", data=data,
                                     success_msg=f"Inserted user login log.User id: {user_id}",
                                     warning_msg=f"User login log insert may have failed.User id: {user_id}",
                                     error_msg=f"Insert error.User id: {user_id}")


    async def insert_user_settings(self, user_id: int, 
                                   language: str | None = None,
                                   configure : Dict | None = None,
                                   notification_setting: Dict | None = None)-> bool:
        """ 
        插入新用户的个人设置到 user_settings 表

        :param user_id: 用户ID
        :param language: 语言
        :param configure: 用户配置
        :param notification_setting: 通知设置

        :return: 插入是否成功
        """
        
        data = {
            "user_id": user_id,
            "language": language or "zh",
            "configure": json.dumps(configure) if configure else "{}",
            "notification_setting": json.dumps(notification_setting) if notification_setting else "{}"
        }

        return await self.mysql_helper.insert_one(table="user_settings", data=data,
                                     success_msg=f"Inserted user settings.User id: {user_id}",
                                     warning_msg=f"User settings insert may have failed.User id: {user_id}",
                                     error_msg=f"Insert error.User id: {user_id}")
   

    async def insert_user_account_actions(self, user_id: int, 
                                          action_type: str, 
                                          action_time: str) -> bool:
        """
        插入用户账号操作记录到 user_account_actions 表

        :param user_id: 用户ID
        :param action_type: 操作类型
        :param action_time: 操作时间

        :return: 插入是否成功
        """
        data = {
            "user_id": user_id,
            "action_type": action_type,
            "action_time": action_time
        }

        return await self.mysql_helper.insert_one(table="user_account_actions", data=data,
                                     success_msg=f"Inserted user account action.User id: {user_id}",
                                     warning_msg=f"User account action insert may have failed.User id: {user_id}",
                                     error_msg=f"Insert error.User id: {user_id}")


    async def insert_user_notifications(self, user_id: int,
                                        notification_type: str, 
                                        notification_title: str,
                                        notification_content: str,
                                        is_read: bool = False) -> bool:
        """
        插入 user_notifications 表

        :param user_id: 用户ID
        :param notification_type: 通知类型
        :param notification_title: 通知标题
        :param notification_content: 通知内容
        
        :param is_read: 是否已读
        """
        data = {
            "user_id": user_id,
            "notification_type": notification_type,
            "notification_title": notification_title,
            "notification_content": notification_content,
            "is_read": is_read
        }

        return await self.mysql_helper.insert_one(table="user_notifications", data=data,
                                     success_msg=f"Inserted user notification.User id: {user_id}",
                                     warning_msg=f"User notification insert may have failed.User id: {user_id}",
                                     error_msg=f"Insert error.User id: {user_id}")


    async def insert_user_files(self, user_id: int, 
                                file_path: str, 
                                file_name: str,
                                file_type: str, 
                                file_size: int,
                                upload_time: datetime, 
                                is_deleted: bool = False) -> bool:
        """
        插入 user_files

        :param user_id: 用户ID
        :param file_path: 文件路径
        :param file_name: 文件名
        :param file_type: 文件类型
        :param file_size: 文件大小
        :param upload_time: 上传时间        
        :param is_deleted: 是否已删除(非必须)

        :return: 插入是否成功
        """
        
        data = {
            "user_id": user_id,
            "file_path": file_path,
            "file_name": file_name,
            "file_type": file_type,
            "upload_time": upload_time,
            "file_size": file_size,
            "is_deleted": is_deleted
        }
        return await self.mysql_helper.insert_one(table="user_files", data=data,
                            success_msg=f"Inserted user files.User id: {user_id}",
                            warning_msg=f"User files insert may have failed.User id: {user_id}",
                            error_msg=f"Insert error.User id: {user_id}")
     
    # ------------------------------------------------------------------------------------------------
    # 功能函数---更新表项目
    # ------------------------------------------------------------------------------------------------
    async def update_users(self, user_id: int,
                           status: Optional[str] = None,
                           password_hash: Optional[str] = None,
                           last_login_time: Optional[str] = None,
                           last_login_ip: Optional[str] = None,
                           session_token: Optional[str] = None) -> bool:
        """
        更新 users 表

        :param user_id: 用户id
        :param status: 用户状态
        :param password_hash: 用户密码哈希
        :param last_login_time: 用户最后登录时间
        :param last_login_ip: 用户最后登录IP
        :param session_token: 用户会话令牌

        :return: 更新是否成功
        """

        if status is None and password_hash is None and last_login_time is None and last_login_ip is None and session_token is None:
            self.logger.warning(f"Nothing to update in user_settings for user_id: {user_id}.")
            return False
        
        data = {}
        
        if status is not None:
            data["status"] = status

        if password_hash is not None:
            data["password_hash"] = password_hash

        if last_login_time is not None:
            data["last_login_time"] = last_login_time

        if last_login_ip is not None:
            data["last_login_ip"] = last_login_ip

        if session_token is not None:
            data["session_token"] = session_token

        return await self.mysql_helper.update_one(table="users", data=data,
                                        where_conditions=["user_id = %s", "status != %s"],
                                        where_values=[user_id, "deleted"],
                                        success_msg=f"Updated user info.",
                                        warning_msg=f"User info update may have failed.",
                                        error_msg=f"Update error.")
    

    async def update_user_profile(self, user_id: int,
                                    user_name: Optional[str] = None,
                                    profile_picture_url: Optional[str] = None,
                                    signature: Optional[str] = None) -> bool:
        """
        更新 user_profile 表

        :param user_id: 用户ID
        :param user_name: 用户名
        :param profile_picture_url: 用户头像URL
        :param signature: 用户签名

        :return: 更新是否成功
        """

        if user_name is None and profile_picture_url is None and signature is None:
            self.logger.warning(f"Nothing to update in user_profile for user_id: {user_id}.")
            return False
        
        data = {}
        
        if user_name is not None:
            data["user_name"] = user_name
            
        if profile_picture_url is not None:
            data["profile_picture_url"] = profile_picture_url
            
        if signature is not None:
            data["signature"] = signature

        return await self.mysql_helper.update_one(table="user_profile", data=data,
                                                   where_conditions=["user_id = %s"],
                                                   where_values=[user_id],
                                                   success_msg=f"Updated user profile.User id: {user_id}",
                                                   warning_msg=f"User profile update may have failed.User id: {user_id}",
                                                   error_msg=f"Update error.User id: {user_id}")
   
   
    # user_login_logs不应该修改
    
   
    async def update_user_settings(self, user_id: int, 
                                   language: str | None = None,
                                   configure : Dict | None = None,
                                   notification_setting: Dict | None = None) -> bool:
        """
        更新 user_settings（仅更新传入的字段）

        :param user_id: 用户ID
        :param language: 语言设置
        :param configure: 用户配置
        :param notification_setting: 通知设置

        :return: 更新是否成功
        """
        if language is None and notification_setting is None and configure is None:
            self.logger.warning(f"Nothing to update in user_settings for user_id: {user_id}.")
            return False
        
        data = {}
        
        if language is not None:
            data["language"] = language
        
        if notification_setting is not None:
            data["notification_setting"] = notification_setting

        if configure is not None:
            data["configure"] = configure

        return await self.mysql_helper.update_one(table="users", data=data,
                                      where_conditions=["user_id = %s"],
                                      where_values=[user_id],
                                      success_msg=f"Updated user settings. User id: {user_id}",
                                      warning_msg=f"User settings update may have failed. User id: {user_id}",
                                      error_msg=f"Update error. User id: {user_id}")


    async def update_user_account_actions(self, user_id: int,
                                          action_type: str,
                                          action_detail: str) -> bool:
        """
        更新用户的账户操作记录

        :param user_id: 用户ID
        :param action_type: 用户操作类型
        :param action_detail: 用户操作详情

        :return: 更新是否成功
        """
        
        data = {
            "action_type": action_type,
            "action_detail": action_detail
        }

        return await self.mysql_helper.update_one(table="user_account_actions", data=data,
                                      where_conditions=["user_id = %s"],
                                      where_values=[user_id],
                                      success_msg=f"Updated user account actions. User id: {user_id}",
                                      warning_msg=f"User account actions update may have failed. User id: {user_id}",
                                      error_msg=f"Update error. User id: {user_id}")


    async def update_user_notifications(self, user_id: int, is_read: bool) -> bool:
        """
        更新用户的通知状态

        :param user_id: 用户ID
        :param is_read: 是否已读

        :return: 更新是否成功
        """

        data = {"is_read": is_read}

        return await self.mysql_helper.update_one(table="user_notifications", data=data,
                                      where_conditions=["user_id = %s"],
                                      where_values=[user_id],
                                      success_msg=f"Updated user notifications. User id: {user_id}",
                                      warning_msg=f"User notifications update may have failed. User id: {user_id}",
                                      error_msg=f"Update error. User id: {user_id}")
       

    async def update_user_files(self, user_id: int,
                                file_path: Optional[str] = None,
                                file_name: Optional[str] = None,
                                file_type: Optional[str] = None,
                                file_size: Optional[int] = None,
                                is_deleted: Optional[bool] = None) -> bool:
        """
        更新 user_files（仅更新传入的字段）

        :param user_id: 用户ID
        :param file_path: 文件路径
        :param file_name: 文件名
        :param file_type: 文件类型
        :param file_size: 文件大小
        :param is_deleted: 是否已删除
        
        :return: 更新是否成功
        """
        if file_path is None and file_name is None and file_type is None and file_size is None and is_deleted is None:
            self.logger.warning(f"No fields provided to update for user_id: {user_id}")
            return False

        data = {}
        
        if file_path is not None:
            data["file_path"] = file_path

        if file_name is not None:
            data["file_name"] = file_name

        if file_type is not None:
            data["file_type"] = file_type

        if file_size is not None:
            data["file_size"] = file_size

        if is_deleted is not None:
            data["is_deleted"] = is_deleted

        return await self.mysql_helper.update_one(table="user_files", data=data,
                                      where_conditions=["user_id = %s"],
                                      where_values=[user_id],
                                      success_msg=f"Updated user files. User id: {user_id}",
                                      warning_msg=f"User files update may have failed. User id: {user_id}",
                                      error_msg=f"Update error. User id: {user_id}")

    
    # ------------------------------------------------------------------------------------------------
    # 功能函数---删除表项目
    # ------------------------------------------------------------------------------------------------ 
    async def soft_delete_user_by_user_id(self, user_id: int) -> bool:
        """
        软删除用户：设为 'deleted' 并记录删除时间。

        :param user_id: 用户ID
            返回: 更新是否成功
        """
        
        # 1. 将users 表中的 status 设置为 'deleted'
        try:
            res = await self.mysql_helper.update_one(
                table="users",
                data={"status": "deleted", "deleted_at": "CURRENT_TIMESTAMP"},
                where_conditions=["user_id = %s"],
                where_values=[user_id],
                success_msg=f"Soft-deleted user ID: {user_id}",
                warning_msg=f"Soft delete may have failed. User ID: {user_id}",
                error_msg=f"Soft delete error. User ID: {user_id}"
            )
        except Exception as e:
            self.logger.error(f"Soft delete failed! Error: {str(e)}")
            return False
        
        if not res:
            self.logger.warning(f"Soft delete may have failed. User ID: {user_id}")
            return False
        
        return True
        
            
    async def delete_user_by_user_id(self, user_id: int) -> bool:
        """
        根据 user_id 删除用户（包含自动删除 user_profile 中的关联记录）。

        :param user_id: 用户ID
        :return: 删除是否成功
        """
        
        # 1. 删除 users 表中数据(根据user_id)
        try:
            success = await self.mysql_helper.delete_one(table="users",
                                                     where_conditions=["user_id = %s"],
                                                     where_values=[user_id])
        except Exception as e:
            self.logger.error(f"Delete failed! Error: {str(e)}")
            return False

        # 2. 删除 user_profile 表中数据
        # 无需手动，因为user_id是 外键，下面的表同理
        # 3. 删除 user_login_logs 表中数据
        
        # 4. 删除 user_settings 表中数据
        
        # 5. 删除 user_account_actions 表中数据
        
        # 6. 删除 user_notifications 表中数据
        
        # 7. 删除 user_files 表中数据
        
        return True

        
    async def hard_delete_expired_users(self)->bool:
        """
        物理删除已标记为 deleted 超过 30 天的用户。
        """
        sql = """
            DELETE FROM users
            WHERE status = 'deleted' AND deleted_at < (NOW() - INTERVAL 30 DAY);
        """
        payload = {
            "id": self.connect_id,
            "sql": sql,
            "sql_args": []
        }

        try:
            response = await self.client.post(
                url=self.mysql_agent_url + "/database/mysql/delete",
                json=payload,
                timeout=120.0
            )
            response.raise_for_status()
            response_data = response.json()

            if response.status_code == 200:
                self.logger.info("Expired deleted users purged.")
            return True

        except Exception as e:
            self.logger.error(f"Hard delete failed! Error: {str(e)}")
            return False
        

    async def connect_to_database(self) -> int:
        """
        连接MySQL数据库
        返回: 连接ID
        """
        headers = {"Content-Type": "application/json"}
        url = self.mysql_agent_url + "/database/mysql/connect"
        payload = {
            "host": self.mysql_host,
            "port": self.mysql_port,
            "user": self.mysql_user,
            "password": self.mysql_password,
            "database": self.database,
            "charset":  self.charset
        }
        try:
            response = await self.client.post(url=url, json=payload, headers=headers, timeout=120.0)
            response.raise_for_status()
            response_data :Dict = response.json()
            
            if response.status_code == 200:
                id = response_data.get("ConnectionID", -1)
                if id == -1:
                    self.logger.error(f"Failed connect to the database '{self.database}'. Message: '{response_data}'")
                    raise HTTPException(status_code=500, detail="Internal server error. Get the default wrong ConnectionID: -1")
                else: 
                    self.logger.info(f"Success connect to the database '{self.database}'. Message: '{response_data}'")
                    return int(id)
            else:
                self.logger.error(f"Unexpected response structure: {response_data}")
                raise ValueError(f"Failed to connect to the database '{self.database}'")
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Connect to database '{self.database}' failed! HTTP error: {e.response.status_code}, {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        
        except httpx.RequestError as e:
            self.logger.error(f"Connect to database '{self.database}' failed! Request error: {e}")
            raise HTTPException(status_code=503, detail="Failed to communicate with MySQLAgent.")
        
        except Exception as e:
            self.logger.error(f"Connect to database '{self.database}' failed! Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error.")
        
    # ------------------------------------------------------------------------------------------------
    # 封装的上层功能函数
    # ------------------------------------------------------------------------------------------------      
    async def fetch_user_id_by_uuid(self, uuid: str) -> Optional[int]:
        """
        通过 UUID 在 users 表中查询 user_id

        :param uuid: 用户的 UUID

        :return: user_id ，如果未找到则返回 None
        """

        try:
            res = await self.mysql_helper.query_one(
                table="users",
                fields=["user_id"],
                where_conditions=["user_uuid = %s"],
                where_values=[uuid]
            )
        except Exception as e:
            self.logger.error(f"Query failed! Error:{str(e)}")
            return None

        if res is None:
            self.logger.warning(f"No user found with UUID: {uuid}")
            return None

        return res["user_id"]
    

    async def fetch_user_id_and_password_by_email_or_account(self, identifier: str)-> Optional[tuple[int, str]]:
        """
        通过 email 或 account 在 users 表中查询 用户id 和 密码哈希

        :param identifier: 用户的 email 或 account

        :return: (user_id, password_hash) 元组，如果未找到则返回 None
        """
        fields = ["user_id", "password_hash"]
        where_conditions = []
        where_values = []
        
        if is_email(identifier):
            where_conditions.append("email = %s")
            where_values.append(identifier)
        elif is_account_name(identifier):
            where_conditions.append("account = %s")
            where_values.append(identifier)
        else:
            self.logger.warning(f"Invalid identifier: {identifier}. Need email or valid account.")
            return None

        try:
            res = await self.mysql_helper.query_one(
                table="users",
                fields=fields,
                where_conditions=where_conditions,
                where_values=where_values
            )
        except Exception as e:
            self.logger.error(f"{str(e)}")
            return None

        if res is None:
            self.logger.warning(f"No user found with identifier: {identifier}")
            return None

        return res["user_id"], res["password_hash"]


    async def fetch_uuid_by_user_id(self, user_id: int) -> str | None:
        """
        通过 user_id 查询用户的 UUID

        :param user_id: 用户ID

        :return: 用户UUID，如果未找到则返回 None
        """
        try:
            res = await self.mysql_helper.query_one(
                table="users",
                fields=["user_uuid"],
                where_conditions=["user_id = %s"],
                where_values=[user_id]
            )
        except Exception as e:
            self.logger.error(f"Query failed! Error:{str(e)}")
            return None

        if res is None:
            self.logger.warning(f"No user found with user_id: {user_id}")
            return None

        return res["user_uuid"]


    async def update_user_notification_settings(self, user_id: int,
                                                notifications_enabled: Optional[bool] = None,
                                                settings_json: Optional[Dict] = None) -> bool:
        """
        更新用户通知设定

        :param user_id: 用户ID
        :param notifications_enabled: 是否启用通知
        :param settings_json: 通知设定JSON
        
        :return: 更新是否成功
        """
        
        if notifications_enabled is None and settings_json is None:
            self.logger.warning(f"No fields provided to update for user: {user_id}")
            return False
        
        data = {}
        
        if notifications_enabled is not None:
            data["notifications_enabled"] = notifications_enabled

        if settings_json is not None:
            data["settings_json"] = settings_json

        return await self.mysql_helper.update_one(table="user_settings", data=data, 
                                                  where_conditions=["user_id = %s"], 
                                                  where_values=[user_id])

    
    async def insert_new_user(self, account: str, email: str,
                                   password_hash: str, user_name: str) -> Optional[int]:
        """
        插入用户注册信息所有表。
            1. users 表
            2. user_profile 表
            3. user_settings 表
            
        :param: account 用户账号(必须)
        :param: email   用户邮箱(必须)
        :param: password_hash   用户密码hash值(必须)
        :param: user_name   用户名(必须)

        返回 user_id（成功）或 None（失败）
        """
        
        # 生成用户UUID
        user_uuid = str(uuid.uuid4())
        
        # 默认用户文件夹路径
        file_folder_path = f"Users/Files/{user_uuid}/"
        
        # 1. 插入 users 表
        try:
            user_id = await self.insert_users(user_uuid=user_uuid, 
                                              account=account, 
                                              email=email,
                                              password_hash=password_hash,
                                              user_name=user_name,
                                              file_folder_path=file_folder_path)
        except Exception as e:
            self.logger.error(f"Insert users Failed. Error: {e}")
            return None
        
        if user_id is not None:
            self.logger.info(f"Insert users success. user_id: {user_id}")
        else:
            self.logger.warning(f"Insert users Failed. user_id: {user_id}")
            return None
        
        
        # 2. 插入 user_profile 表（使用默认头像）
        try:
            res_insert_user_profile = await self.insert_user_profile(
                                user_id=user_id, 
                                user_name=user_name)
        except Exception as e:
            self.logger.error(f"Insert user profile Failed. Error: {e}")
            return None
        
        if res_insert_user_profile:
            self.logger.info(f"Inserted user profile. User ID: {user_id}")
        else:
            self.logger.warning(f"User profile insert may have failed. User ID: {user_id}")
            return None
        
        
        # 3. 插入 user_settings 表 (使用默认配置)
        try:
            res_insert_user_settings = await self.insert_user_settings(user_id=user_id)
        except Exception as e:
            self.logger.error(f"Insert user settings Failed. Error: {e}")
            return None

        if res_insert_user_settings:
            self.logger.info(f"Inserted user settings. User ID: {user_id}")
        else:
            self.logger.warning(f"User settings insert may have failed. User ID: {user_id}")
            return None
 

    async def update_user_password_by_user_id(self, user_id: int, new_password_hash: str) -> bool:
            """
            根据 user_id 更新用户密码哈希。
                1. 先更新 users 表中的 password_hash 字段
                2. 再向 user_account_actions 表中插入新纪录

            :param user_id: 用户ID
            :param new_password_hash: 新密码哈希

            :return: 更新是否成功
            """
            # 1. 更新 users 表中的 password_hash 字段
            data = {"password_hash": new_password_hash}
            where_conditions = ["user_id = %s"]
            where_values = [user_id]
            
            
            res =  await self.mysql_helper.update_one(table="users", data=data,
                                        where_conditions=where_conditions,
                                        where_values=where_values, 
                                        success_msg=f"Updated user info.",
                                        warning_msg=f"User info update may have failed.",
                                        error_msg=f"Update error.")
            
            if not res:
                self.logger.error(f"Failed to update password. User id: {user_id}") 
                return False
            
            # 2. 向 user_account_actions 表中插入新纪录
            data = {
                "user_id": user_id,
                "action_type": "update_password",
                "action_detail": f"Password updated to {new_password_hash}"
            }
            res = await self.mysql_helper.insert_one(table="user_account_actions",data = data)
            
            if not res:
                self.logger.error(f"Failed to insert user account action. User id: {user_id}")
                return False
            else:
                self.logger.info(f"Success to update password. User id: {user_id}")
                return True
     