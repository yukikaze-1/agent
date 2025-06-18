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


from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config
from Module.Utils.FormatValidate import is_email, is_account_name

"""
## 用户信息数据库设计

### 1. 用户主表 (`users`)
| 字段名             | 类型                                                             | 描述         |
| ----------------- | ---------------------------------------------------------------- | ---------- |
| `user_id`         | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                        | 用户内部ID（主键） |
| `user_uuid`       | `CHAR(36) NOT NULL UNIQUE`                                       | 用户UUID     |
| `status`          | `ENUM('inactive', 'active','deleted') NOT NULL DEFAULT 'active'` | 用户状态       |
| `account`         | `VARCHAR(255) NOT NULL UNIQUE`                                   | 用户账号       |
| `password_hash`   | `VARCHAR(255) NOT NULL`                                          | 密码哈希值      |
| `email`           | `VARCHAR(255) NOT NULL UNIQUE`                                   | 用户邮箱       |
| `last_login_time` | `DATETIME`                                                       | 最后登录时间     |
| `session_token`   | `VARCHAR(2048)`                                                  | Session令牌  |
| `file_folder_path`| `VARCHAR(512)`                                                   | 用户个人文件夹(默认为UUID为命名)  |
| `created_at`      | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间       |
| `updated_at`      | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 修改时间
| `deleted_at`      | `DATETIME NULL`                                                  | 删除时间 |

CREATE TABLE users (
  user_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_uuid CHAR(36) NOT NULL UNIQUE,
  status ENUM('inactive', 'active','deleted') NOT NULL DEFAULT 'active',
  account VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  last_login_time DATETIME,
  session_token VARCHAR(2048),
  file_folder_path VARCHAR(512) DEFAULT (CONCAT('Users/Files/', user_uuid)),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at DATETIME NULL
);

---

### 2. 用户扩展资料 (`user_profile`)
| 字段名                 | 类型                                                             | 描述          |
| --------------------- | ---------------------------------------------------------------- | ----------- |
| `user_id`             | `INT UNSIGNED PRIMARY KEY`                                       | 用户ID（主键+外键） |
| `user_name`           | `VARCHAR(255)`                                                   | 用户名         |
| `profile_picture_url` | `VARCHAR(512) DEFAULT 'Resources/img/nahida.jpg'`                | 头像URL地址     |
| `signature`           | `VARCHAR(255)`                                                   | 用户个性签名      |
| `created_at`          | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间        |
| `updated_at`          | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 修改时间        |

CREATE TABLE user_profile (
  user_id INT UNSIGNED PRIMARY KEY,
  user_name VARCHAR(255),
  profile_picture_url VARCHAR(512) DEFAULT 'Resources/img/nahida.jpg',
  signature VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_user_profile_user_id FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

---

### 3. 用户登录认证 (`user_login_logs`)
| 字段名           | 类型                                                             | 描述       |
| --------------- | ---------------------------------------------------------------- | -------- |
| `login_id`      | `BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                     | 日志主键     |
| `user_id`       | `INT UNSIGNED`                                                   | 用户ID（外键） |
| `action_type`   | `VARCHAR(255) NOT NULL`                                          | 登录或登出类型  |
| `action_detail` | `VARCHAR(512)`                                                   | 事件详情     |
| `agent`         | `VARCHAR(512)`                                                   | 浏览器代理    |
| `device`        | `VARCHAR(512)`                                                   | 登录设备     |
| `os`            | `VARCHAR(255)`                                                   | 操作系统     |
| `login_success` | `BOOL DEFAULT FALSE`                                             | 是否成功登录   |
| `created_at`    | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间     |
| `updated_at`    | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间     |

CREATE TABLE user_login_logs (
  login_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED,
  action_type VARCHAR(255) NOT NULL,
  action_detail VARCHAR(512),
  agent VARCHAR(512),
  device VARCHAR(512),
  os VARCHAR(255),
  login_success BOOL DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_login_logs_user_id FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

---

### 4. 用户自定义设置 (`user_settings`)
| 字段名                  | 类型                                                             | 描述          |
| ---------------------- | ---------------------------------------------------------------- | ----------- |
| `user_id`              | `INT UNSIGNED PRIMARY KEY`                                       | 用户ID（主键+外键） |
| `language`             | `ENUM('zh', 'en', 'jp') NOT NULL DEFAULT 'zh'`                   | 用户语言偏好      |
| `configure_path`       | `VARCHAR(2048) DEFAULT (CONCAT('Users/Config/', user_uuid))`     | JSON配置路径(不可更改)    |
| `notification_setting` | `JSON`                                                           | 用户通知设置      |
| `created_at`           | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间        |
| `updated_at`           | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间        |

CREATE TABLE user_settings (
  user_id INT UNSIGNED PRIMARY KEY,
  language ENUM('zh', 'en', 'jp') NOT NULL DEFAULT 'zh',
  configure_path VARCHAR(2048) DEFAULT (CONCAT('Users/Config/', user_uuid)),
  notification_setting JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_user_settings_user_id FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

---

### 5. 用户账户行为 (`user_account_actions`)
| 字段名                       | 类型                                                             | 描述       |
| --------------------------- | ---------------------------------------------------------------- | -------- |
| `action_id`                 | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                        | 主键       |
| `user_id`                   | `INT UNSIGNED`                                                   | 用户ID（外键） |
| `action_type`               | `VARCHAR(255)`                                                   | 用户账户操作类型   |
| `action_detail`             | `VARCHAR(512)`                                                   | 用户账户操作细节   |
| `created_at`                | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间     |
| `updated_at`                | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间     |

CREATE TABLE user_account_actions (
  action_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED,
  action_type VARCHAR(255),
  action_detail VARCHAR(512),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_user_actions_user_id FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

---

### 6. 用户通知与消息 (`user_notifications`)
| 字段名                | 类型                                                             | 描述       |
| -------------------- | ---------------------------------------------------------------- | -------- |
| `notification_id`    | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                        | 通知ID（主键） |
| `user_id`            | `INT UNSIGNED`                                                   | 用户ID（外键） |
| `notification_type`  | `ENUM('system', 'security', 'promotion') NOT NULL`               | 通知类型     |
| `notification_title` | `VARCHAR(255) NOT NULL`                                          | 通知标题     |
| `message_content`    | `TEXT`                                                           | 通知内容     |
| `is_read`            | `BOOL DEFAULT FALSE`                                             | 是否已读     |
| `created_at`         | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间     |
| `updated_at`         | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间     |

CREATE TABLE user_notifications (
  notification_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED,
  notification_type ENUM('system', 'security', 'promotion') NOT NULL,
  notification_title VARCHAR(255) NOT NULL,
  message_content TEXT,
  is_read BOOL DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_user_notifications_user_id FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

---

### 7. 用户文件 (`user_files`)
| 字段名            | 类型                                                             | 描述           |
| ---------------- | ---------------------------------------------------------------- | ------------ |
| `file_id`        | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                        | 文件ID         |
| `user_id`        | `INT UNSIGNED`                                                   | 用户ID（外键）     |
| `file_path`      | `VARCHAR(512)`                                                   | 文件相对路径       |
| `file_name`      | `VARCHAR(255)`                                                   | 原始文件名        |
| `file_type`      | `VARCHAR(255)`                                                   | 文件类型（如 .png） |
| `upload_time`    | `DATETIME`                                                       | 上传时间         |
| `file_size`      | `BIGINT UNSIGNED`                                                | 文件大小         |
| `is_deleted`     | `BOOL DEFAULT FALSE`                                             | 是否删除         |
| `created_at`     | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间         |
| `updated_at`     | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间         |

CREATE TABLE user_files (
  file_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED,
  file_path VARCHAR(512),
  file_name VARCHAR(255),
  file_type VARCHAR(255),
  upload_time DATETIME,
  file_size BIGINT UNSIGNED,
  is_deleted BOOL DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_user_files_user_id FOREIGN KEY (user_id) REFERENCES users(user_id)
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
                    
        # TODO 应该让程序自动创建一个数据库，待实现            
        需要手动在mysql数据库中创建用户信息数据库
        (注：1.要先手动创建一个名为userinfo的database才行 2. 创建表的SQL语句见本文件顶部的注释):    
            1. 用户主表 (`users`)
            2. 用户扩展资料 (`user_profile`)
            3. 用户登录认证 (`user_login_logs`)
            4. 用户自定义设置 (`user_settings`)
            5. 用户账户行为 (`user_account_actions`)
            6. 用户通知与消息 (`user_notifications`)
            7. 用户文件 (`user_files`)
    """
    def __init__(self, logger: Logger| None=None):
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
        
    # --------------------------------
    # 功能函数
    # --------------------------------     
    async def fetch_user_id_and_password_by_email_or_account(self, identifier: str)-> Optional[tuple[int, str]]:
        """
        通过 email 或 account 在 users 表中查询 用户id 和 密码哈希

        :param identifier: 用户的 email 或 account
        """
        
        if is_email(identifier):
            query_sql = "SELECT user_id, password_hash FROM users WHERE email = %s;"
            sql_args = [identifier]
        elif is_account_name(identifier):
            query_sql = "SELECT user_id, password_hash FROM users WHERE account = %s;"
            sql_args = [identifier]
        else:
            self.logger.error(f"Invalid identifier: {identifier}. Need email or valid account.")
            return None
        
        url = self.mysql_agent_url + "/database/mysql/query"
        payload = {
            "id": self.connect_id,
            "sql": query_sql,
            "sql_args": sql_args
        }
        try:
            response = await self.client.post(url=url, json=payload, timeout=120.0)
            response.raise_for_status()
            response_data :Dict = response.json()
            
            if response.status_code == 200:
                self.logger.info(f"Query success.")
                result = response_data["Query Result"]
                if result:
                    return result['user_id'] ,result["password_hash"]
                else:
                    self.logger.info(f"No user found with identifier: {identifier}")
                    return None
            else:
                self.logger.error(f"Query failed! Error:{response}")
                return None
            
        except Exception as e:
            self.logger.error(f"Query failed! Error:{str(e)}")
            return None
    

    async def fetch_user_id_by_uuid(self, uuid: str) -> Optional[str]:
        """
        通过 UUID 查询 user_id
        """
        query_sql = "SELECT user_id FROM users WHERE user_uuid = %s;"
        sql_args = [uuid]

        url = self.mysql_agent_url + "/database/mysql/query"
        payload = {
            "id": self.connect_id,
            "sql": query_sql,
            "sql_args": sql_args
        }
        try:
            response = await self.client.post(url=url, json=payload, timeout=120.0)
            response.raise_for_status()
            response_data: Dict = response.json()

            if response.status_code == 200:
                self.logger.info(f"Query success.")
                result = response_data["Result"]

                if result:
                    return result['user_id']
                else:
                    self.logger.info(f"No user found with UUID: {uuid}")
                    return None
            else:
                self.logger.error(f"Query failed! Error:{response}")
                return None

        except Exception as e:
            self.logger.error(f"Query failed! Error:{str(e)}")
            return None


    async def insert_users(self, account: str, email: str,
                       password_hash: str, user_name: Optional[str] = None,
                       signature: Optional[str] = None) -> Optional[str]:
        """
        插入 users（支持可选字段）

        :param account: 用户账号（必须）
        :param email: 用户邮箱（必须）
        :param password_hash: 用户密码哈希（必须）
        :param user_name: 用户昵称（可选）
        :param signature: 用户签名（可选）
        :return: 成功返回 user_id，失败返回 None
        """
        user_uuid = str(uuid.uuid4())
        
        data = {
            "user_uuid": user_uuid,
            "account": account,
            "email": email,
            "password_hash": password_hash
        }
        if user_name is not None:
            data["user_name"] = user_name

        if signature is not None:
            data["signature"] = signature

        res = await self.insert_one(table="users", data=data,
                                     success_msg=f"Inserted user info for account: {account}",
                                     warning_msg=f"User info insert may have failed for account: {account}",
                                     error_msg=f"Insert error for account: {account}")
        if not res:
            self.logger.error(f"Failed to insert user info for account: {account}")
            return None

        user_id = await self.fetch_user_id_by_uuid(user_uuid)
        
        return user_id
    
    
    async def update_users(self, user_id: int, status: Optional[str] = None, password_hash: Optional[str] = None,
                           last_login_time: Optional[str] = None, session_token: Optional[str] = None) -> bool:
        """
        更新 users

        :param user_id: 用户id
        :param status: 用户状态
        :param password_hash: 用户密码哈希
        :param last_login_time: 用户最后登录时间
        :param session_token: 用户会话令牌
        """
        
        if status is None and password_hash is None and last_login_time is None and session_token is None:
            self.logger.warning(f"Nothing to update in user_settings for user_id: {user_id}.")
            return False
        
        data = {}
        
        if status is not None:
            data["status"] = status

        if password_hash is not None:
            data["password_hash"] = password_hash

        if last_login_time is not None:
            data["last_login_time"] = last_login_time

        if session_token is not None:
            data["session_token"] = session_token
        
        where_conditions = ["user_id = %s", "status != %s"]
        
        where_values=[user_id, "deleted"]

        return await self.update_one(table="users", data=data,
                                        where_conditions=where_conditions,
                                        where_values=where_values,
                                        success_msg=f"Updated user info.",
                                        warning_msg=f"User info update may have failed.",
                                        error_msg=f"Update error.")


    async def insert_user_profile(self, user_id: int, account: str ,user_name: str | None = None,  signature: str | None = None)-> bool:
        """
        插入新用户的个人资料信息到 user_profile 表。

        :param user_id: 用户ID
        :param account: 用户账号
        :param user_name: 用户名(非必须)
        :param signature: 用户签名(非必须)

        :return: 插入是否成功
        """
        
        data = {
            "user_id": user_id,
            "user_name": user_name or account,
            "signature": signature or ""
        }

        return await self.insert_one(table="user_profile", data=data,
                            success_msg=f"Inserted user profile.User id: {user_id}",
                            warning_msg=f"User profile insert may have failed.User id: {user_id}",
                            error_msg=f"Insert error.User id: {user_id}")


    async def insert_user_settings(self, user_id: int, language: str | None = None,
                                       configure_json_path: str | None = None,
                                       notification_setting: Dict | None = None)-> bool:
        """ 
        插入新用户的个人设置到 user_settings 表

        :param user_id: 用户ID
        :param language: 语言
        :param configure_json_path: 配置文件路径
        :param notification_setting: 通知设置

        :return: 插入是否成功
        """
        
        data = {
            "user_id": user_id,
            "language": language or "zh",
            "configure_json_path": configure_json_path or "",
            "notification_setting": json.dumps(notification_setting) if notification_setting else "{}"
        }

        return await self.insert_one(table="user_settings", data=data,
                                     success_msg=f"Inserted user settings.User id: {user_id}",
                                     warning_msg=f"User settings insert may have failed.User id: {user_id}",
                                     error_msg=f"Insert error.User id: {user_id}")
        

    async def insert_new_user(self, account: str, email: str,
                                   password_hash: str, user_name: Optional[str]= None,
                                   signature: Optional[str] = None) -> Optional[str]:
        """
        插入用户注册信息所有表。
            1. users 表
            2. user_profile 表
            3. user_settings 表
            
        :param: account 用户账号(必须)
        :param: email   用户邮箱(必须)
        :param: password_hash   用户密码hash值(必须)
        :param: user_name   用户名(非必须)
        :param: signature   用户签名(非必须)

        返回 user_id（成功）或 None（失败）
        """

        # 1. 插入 users 表
        user_id = await self.insert_users(account=account, email=email,
                                          password_hash=password_hash,
                                          user_name=user_name, signature=signature)
        if user_id is not None:
            self.logger.info(f"Insert users success. user_id: {user_id}")
        else:
            self.logger.warning(f"Insert users Failed. user_id: {user_id}")
            raise ValueError(f"Insert users Failed. user_id: {user_id}")
        
        
        # 2. 插入 user_profile 表（使用默认头像）
        res_insert_user_profile = await self.insert_user_profile(
                            user_id=user_id, user_name=user_name,
                            account=account, signature=signature)
        if res_insert_user_profile:
            self.logger.info(f"Inserted user profile. User ID: {user_id}")
        else:
            self.logger.warning(f"User profile insert may have failed. User ID: {user_id}")
            raise ValueError(f"Failed to insert user profile. User ID: {user_id}")
        
        
        # 3. 插入 user_settings 表 (使用默认配置)
        res_insert_user_settings = await self.insert_user_settings(user_id=user_id)
        if res_insert_user_settings:
            self.logger.info(f"Inserted user settings. User ID: {user_id}")
        else:
            self.logger.warning(f"User settings insert may have failed. User ID: {user_id}")
            raise ValueError(f"Failed to insert user settings. User ID: {user_id}")
        

    async def update_user_login_logs(self, user_id: int,
                                     action_type: Optional[str] = None, action_detail: Optional[str] = None,
                                     agent: Optional[str] = None, device: Optional[str] = None, 
                                     os: Optional[str] = None, login_success: bool = False) -> bool:
        """
        更新 user_login_logs 表

        :param user_id: 用户ID
        :param action_type: 操作类型
        :param action_detail: 操作详情
        :param agent: 代理信息
        :param device: 设备信息
        :param os: 操作系统信息
        :param login_success: 登录是否成功

        :return: 更新是否成功
        """
        
        if action_type is None and action_detail is None and agent is None and device is None and os is None and login_success is None:
            self.logger.warning(f"Nothing to update in user_login_logs for user_id: {user_id}.")
            return False
        
        data = {}

        if action_type is not None:
            data["action_type"] = action_type
            
        if action_detail is not None:
            data["action_detail"] = action_detail
            
        if agent is not None:
            data["agent"] = agent
            
        if device is not None:
            data["device"] = device
            
        if os is not None:
            data["os"] = os
            
        if login_success is not None:
            data["login_success"] = login_success
            
        where_conditions = ["user_id = %s"]
        
        where_values=[user_id]

        return await self.update_one(table="user_login_logs", data=data,
                                      where_conditions=where_conditions,
                                      where_values=where_values,
                                      success_msg=f"Updated user login logs. User id: {user_id}",
                                      warning_msg=f"User login logs update may have failed. User id: {user_id}",
                                      error_msg=f"Update error. User id: {user_id}")
   
   
    async def update_user_settings(self, user_id: int, language: Optional[str] = None,
                                   notification_setting: Optional[Dict] = None) -> bool:
        """
        更新 user_settings（仅更新传入的字段）

        :param user_id: 用户ID
        :param language: 语言设置
        :param notification_setting: 通知设置

        :return: 更新是否成功
        """
        if language is None and notification_setting is None:
            self.logger.warning(f"Nothing to update in user_settings for user_id: {user_id}.")
            return False
        
        data = {}
        
        if language is not None:
            data["language"] = language
        
        if notification_setting is not None:
            data["notification_setting"] = notification_setting
        
        where_conditions = ["user_id = %s"]

        where_values = [user_id]

        return await self.update_one(table="users", data=data,
                                      where_conditions=where_conditions,
                                      where_values=where_values,
                                      success_msg=f"Updated user settings. User id: {user_id}",
                                      warning_msg=f"User settings update may have failed. User id: {user_id}",
                                      error_msg=f"Update error. User id: {user_id}")


    async def update_user_account_actions(self, user_id: int, action_type: str, action_detail: str) -> bool:
        """
        更新用户的账户操作记录

        :param user_id: 用户ID
        :param actions: 用户操作记录列表

        :return: 更新是否成功
        """
        
        data = {
            "action_type": action_type,
            "action_detail": action_detail
        }
        
        where_conditions = ["user_id = %s"]
        
        where_values = [user_id]

        return await self.update_one(table="user_account_actions", data=data,
                                      where_conditions=where_conditions,
                                      where_values=where_values,
                                      success_msg=f"Updated user account actions. User id: {user_id}",
                                      warning_msg=f"User account actions update may have failed. User id: {user_id}",
                                      error_msg=f"Update error. User id: {user_id}")


    async def insert_user_notifications(self, user_id: int,
                                        notification_type: str, notification_title: str,
                                        message_content: str, is_read: bool = False) -> bool:
        """
        插入 user_notifications

        :param user_id: 用户ID
        :param notification_type: 通知类型
        :param notification_title: 通知标题
        :param message_content: 消息内容
        :param is_read: 是否已读
        """
        data = {
            "user_id": user_id,
            "notification_type": notification_type,
            "notification_title": notification_title,
            "message_content": message_content,
            "is_read": is_read
        }

        return await self.insert_one(table="user_notifications", data=data,
                                     success_msg=f"Inserted user notification.User id: {user_id}",
                                     warning_msg=f"User notification insert may have failed.User id: {user_id}",
                                     error_msg=f"Insert error.User id: {user_id}")


    async def update_user_notifications(self, user_id: int, is_read: bool) -> bool:
        """
        更新用户的通知状态

        :param user_id: 用户ID
        :param is_read: 是否已读
        """

        data = {
            "is_read": is_read
        }
        
        where_conditions = ["user_id = %s"]

        where_values = [user_id]

        return await self.update_one(table="user_notifications", data=data,
                                      where_conditions=where_conditions,
                                      where_values=where_values,
                                      success_msg=f"Updated user notifications. User id: {user_id}",
                                      warning_msg=f"User notifications update may have failed. User id: {user_id}",
                                      error_msg=f"Update error. User id: {user_id}")


    async def insert_user_files(self, user_id: int, file_path: str, file_name: str,
                               file_type: str, upload_time: str, file_size: int,
                               is_deleted: bool = False) -> bool:
        """
        插入 user_files

        :param user_id: 用户ID
        :param file_path: 文件路径
        :param file_name: 文件名
        :param file_type: 文件类型
        :param upload_time: 上传时间
        :param file_size: 文件大小
        :param is_deleted: 是否已删除(非必须)
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
        return await self.insert_one(table="user_files", data=data,
                            success_msg=f"Inserted user files.User id: {user_id}",
                            warning_msg=f"User files insert may have failed.User id: {user_id}",
                            error_msg=f"Insert error.User id: {user_id}")
        

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

        where_conditions= ["user_id = %s"]
        
        where_values = [user_id]

        # 若无字段可更新，直接返回 False
        if not data:
            self.logger.warning(f"No fields provided to update for user_id: {user_id}")
            return False

        return await self.update_one(table="user_files", data=data,
                                      where_conditions=where_conditions,
                                      where_values=where_values,
                                      success_msg=f"Updated user files. User id: {user_id}",
                                      warning_msg=f"User files update may have failed. User id: {user_id}",
                                      error_msg=f"Update error. User id: {user_id}")


    async def update_user_password_by_user_id(self, user_id: int, new_password_hash: str) -> bool:
            """
            根据 user_id 更新用户密码哈希。
                1. 先更新 users 表中的 password_hash 字段
                2. 再向 user_account_actions 表中插入新纪录

            :param user_id: 用户ID
            :param new_password_hash: 新密码哈希
            """
            # 1. 更新 users 表中的 password_hash 字段
            data = {"password_hash": new_password_hash}
            where_conditions = ["user_id = %s"]
            where_values = [user_id]
            
            
            res =  await self.update_one(table="users", data=data,
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
            res = await self.insert_one(table="user_account_actions",data = data)
            
            if not res:
                self.logger.error(f"Failed to insert user account action. User id: {user_id}")
                return False
            else:
                self.logger.info(f"Success to update password. User id: {user_id}")
                return True


    async def soft_delete_user_by_id(self, user_id: int) -> bool:
        """
        软删除用户：设为 'deleted' 并记录删除时间。
            返回: 更新是否成功
        """
        sql = """
            UPDATE users
            SET status = 'deleted', deleted_at = CURRENT_TIMESTAMP
            WHERE user_id = %s;
        """
        url = self.mysql_agent_url + "/database/mysql/update"
        payload = {
            "id": self.connect_id,
            "sql": sql,
            "sql_args": [user_id]
        }

        try:
            response = await self.client.post( url=url, json=payload, timeout=60.0)
            response.raise_for_status()
            response_data = response.json()

            if response.status_code == 200 and response_data.get("Result") is True:
                self.logger.info(f"Soft-deleted user ID: '{user_id}'.")
                return True
            else:
                self.logger.warning(f"Soft delete may have failed. User ID: '{user_id}'. Response: {response_data}")
                return False

        except Exception as e:
            self.logger.error(f"Soft delete failed! Error: {str(e)}")
            return False
        
            
    async def delete_user_by_id(self, user_id: int) -> bool:
        """
        根据 user_id 删除用户（包含自动删除 user_profile 中的关联记录）。
            返回: 删除是否成功
        """
        delete_sql = "DELETE FROM users WHERE user_id = %s;"
        payload = {
            "id": self.connect_id,
            "sql": delete_sql,
            "sql_args": [user_id]
        }

        try:
            response = await self.client.post(
                url=self.mysql_agent_url + "/database/mysql/delete",
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            response_data = response.json()

            if response.status_code == 200 and response_data.get("Result") is True:
                self.logger.info(f"Successfully deleted user with ID: '{user_id}'.")
                return True
            else:
                self.logger.warning(f"User deletion might have failed. User ID: '{user_id}'. Response: {response_data}")
                return False

        except Exception as e:
            self.logger.error(f"Delete failed! Error: {str(e)}")
            return False

        
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
        
        
    # --------------------------------
    # 工具函数
    # --------------------------------    
    def build_insert_sql(self, table: str, data: Dict) -> tuple[str, list]:
        """
        构造通用 INSERT SQL 语句

        :param table: 表名
        :param data: 要插入的字段和值（key=字段名，value=字段值）

        :return: (sql语句, 参数列表)
        """
        if not data:
            raise ValueError("插入数据不能为空")

        columns = list(data.keys())
        values = list(data.values())

        placeholders = ", ".join(["%s"] * len(columns))
        columns_str = ", ".join(columns)

        sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders});"
        self.logger.debug(f"Generated SQL: {sql} | Values: {values}")
        return sql, values
    
    
    def build_update_sql(self, table: str, data: Dict,
                     where_conditions: Optional[List[str]] = None,
                     where_values: Optional[List] = None) -> tuple[str, List]:
        """
        构造支持复杂 WHERE 条件的 UPDATE SQL 语句

        :param table: 表名
        :param data: 要更新的字段和值（key=字段名，value=字段值）
        :param where_conditions: 更复杂的 WHERE 条件表达式（如 ["user_id = %s", "status != %s"]）
        :param where_values: 与 where_conditions 一一对应的值
        :return: (sql语句, 参数列表)
        """
        if not data:
            raise ValueError("更新字段不能为空")
        
        if where_conditions and where_values and len(where_conditions) != len(where_values):
            raise ValueError("where_conditions 和 where_values 长度不一致")


        set_clause = ", ".join([f"{key} = %s" for key in data])
        values = list(data.values())

        where_clause_parts = []

        if where_conditions:
            where_clause_parts.extend(where_conditions)
            if where_values:
                values.extend(where_values)

        if not where_clause_parts:
            raise ValueError("WHERE 条件不能为空（防止全表更新）")

        where_clause = " AND ".join(where_clause_parts)
        sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause};"

        return sql, values


    async def execute_sql(self, url: str, sql: str, sql_args: List,
                          warning_message: str, success_message: str, error_message: str) -> bool:
        """
            执行sql

        :param url: 请求的URL
        :param sql: 要执行的SQL语句
        :param sql_args: SQL语句的参数
        :param warning_message: 警告消息
        :param success_message: 成功消息
        :param error_message: 错误消息
        """
        
        self.logger.info(f"Executing SQL: {sql} with args: {sql_args}")
        
        payload = {
            "id": self.connect_id,
            "sql": sql,
            "sql_args": sql_args
        }
        
        try:
            response = await self.client.post(url=url, json=payload, timeout=60.0)
            response.raise_for_status()
            response_data = response.json()

            if response.status_code == 200 and response_data.get("Result") is True:
                self.logger.info(success_message)
                return True
            else:
                self.logger.warning(f"{warning_message} | Response: {response_data}")
                return False

        except Exception as e:
            self.logger.error(f"{error_message} : {str(e)}")
            return False
        
        
    async def insert_one(self, table: str, data: Dict,
                     success_msg: str = "Insert Success", warning_msg: str = "Insert Warning.",
                     error_msg: str = "Insert Error.") -> bool:
        """
        插入一条记录

        :param table: 表名
        :param data: 要插入的字段和值（key=字段名，value=字段值）
        """
        if not data:
            self.logger.warning("尝试插入空数据，已跳过。")
            return False

        # 生成sql语句和sql参数
        sql, sql_args = self.build_insert_sql(table, data)
        
        url = self.mysql_agent_url + "/database/mysql/insert"
        
        return await self.execute_sql(url, sql, sql_args, warning_msg, success_msg, error_msg)

    
    async def update_one(self, table: str, data: dict,
                     where_conditions: Optional[List[str]] = None,
                     where_values: Optional[List] = None,
                     success_msg: str = "Update success.",
                     warning_msg: str = "Update warning.",
                     error_msg: str = "Update error.") -> bool:
        """
        通用更新函数：更新一条记录

        :param table: 表名
        :param data: 要更新的字段和值
        :param where_conditions: 复杂 WHERE 条件（如 ["status != %s"]）
        :param where_values: 对应的值（如 ["deleted"]）
        :param success_msg: 成功日志
        :param warning_msg: 警告日志
        :param error_msg: 错误日志
        :return: 是否更新成功
        """
        # 构造 SQL 和参数
        sql, args = self.build_update_sql(
            table=table,
            data=data,
            where_conditions=where_conditions,
            where_values=where_values
        )

        # 发送请求
        url = self.mysql_agent_url + "/database/mysql/update"
        return await self.execute_sql(
            url=url,
            sql=sql,
            sql_args=args,
            success_message=success_msg,
            warning_message=warning_msg,
            error_message=error_msg
        )

