# Project:      Agent
# Author:       yomu
# Time:         2024/12/12
# Version:      0.1
# Description:  agent User information database initialize

"""
    用户账户数据库
"""
import httpx
from typing import Tuple, Optional, Dict
from dotenv import dotenv_values
from logging import Logger
from fastapi import HTTPException

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config

"""
## 用户信息数据库设计

### 1. 用户主表 (`users`)
| 字段名             | 类型                                                             | 描述         |
| ----------------- | ---------------------------------------------------------------- | ---------- |
| `user_id`         | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`                        | 用户内部ID（主键） |
| `user_uuid`       | `CHAR(36) NOT NULL UNIQUE`                                       | 用户UUID     |
| `status`          | `ENUM('inactive', 'active') NOT NULL DEFAULT 'active'`           | 用户状态       |
| `account`         | `VARCHAR(255) NOT NULL UNIQUE`                                   | 用户账号       |
| `password_hash`   | `VARCHAR(255) NOT NULL`                                          | 密码哈希值      |
| `email`           | `VARCHAR(255) NOT NULL UNIQUE`                                   | 用户邮箱       |
| `last_login_time` | `DATETIME`                                                       | 最后登录时间     |
| `session_token`   | `VARCHAR(2048)`                                                  | Session令牌  |
| `created_at`      | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间       |
| `updated_at`      | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 修改时间       |

CREATE TABLE users (
  user_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_uuid CHAR(36) NOT NULL UNIQUE,
  status ENUM('inactive', 'active') NOT NULL DEFAULT 'active',
  account VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  last_login_time DATETIME,
  session_token VARCHAR(2048),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

---

### 2. 用户扩展资料 (`user_profile`)
| 字段名                 | 类型                                                             | 描述          |
| --------------------- | ---------------------------------------------------------------- | ----------- |
| `user_id`             | `INT UNSIGNED PRIMARY KEY`                                       | 用户ID（主键+外键） |
| `user_name`           | `VARCHAR(255)`                                                   | 用户名         |
| `profile_picture_url` | `VARCHAR(512) DEFAULT 'default_profile_picture_url'`                                                   | 头像URL地址     |
| `signature`           | `VARCHAR(255)`                                                   | 用户个性签名      |
| `created_at`          | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间        |
| `updated_at`          | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 修改时间        |

CREATE TABLE user_profile (
  user_id INT UNSIGNED PRIMARY KEY,
  user_name VARCHAR(255),
  profile_picture_url VARCHAR(512) DEFAULT 'default_profile_picture_url',
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
| `history_ip`    | `VARCHAR(255)`                                                   | 登录IP     |
| `history_time`  | `DATETIME`                                                       | 登录时间     |
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
  history_ip VARCHAR(255),
  history_time DATETIME,
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
| `language`             | `ENUM('zh', 'en', 'jp', 'kr') NOT NULL DEFAULT 'zh'`             | 用户语言偏好      |
| `configure_json_path`  | `VARCHAR(2048)`                                                  | JSON配置路径    |
| `notification_setting` | `JSON`                                                           | 用户通知设置      |
| `created_at`           | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间        |
| `updated_at`           | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间        |

CREATE TABLE user_settings (
  user_id INT UNSIGNED PRIMARY KEY,
  language ENUM('zh', 'en', 'jp', 'kr') NOT NULL DEFAULT 'zh',
  configure_json_path VARCHAR(2048),
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
| `register_time`             | `DATETIME`                                                       | 注册时间     |
| `last_password_change_time` | `DATETIME`                                                       | 上次密码变更   |
| `created_at`                | `DATETIME DEFAULT CURRENT_TIMESTAMP`                             | 创建时间     |
| `updated_at`                | `DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间     |

CREATE TABLE user_account_actions (
  action_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED,
  register_time DATETIME,
  last_password_change_time DATETIME,
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
| `user_file_path` | `VARCHAR(510)`                                                   | 文件相对路径       |
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
  user_file_path VARCHAR(510),
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
        表:account
        格式:id, username(PRIMARY KEY), password
        
        配置文件为config.yml,配置文件路径存放在Init/.env中的的INIT_CONFIG_PATH变量中
            配置内容为：
                user_account_database_config：
                    host
                    port
                    user
                    password
                    database
                    table
                    charset
                    
        # TODO 应该让程序自动创建一个数据库，待实现            
        需要手动在mysql数据库中创建用户信息数据库(注：要先手动创建一个名为userinfo的database才行):    
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
        self.table = self.config.get("table", "")
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
    async def fetch_user_by_name(self,username: str)-> Optional[Dict]:
        """通过名字来查询用户账号信息"""
        query_sql = f"SELECT * FROM {self.table} WHERE username = %s;"
        url = self.mysql_agent_url + "/database/mysql/query"
        payload = {
            "id": self.connect_id,
            "sql": query_sql,
            "sql_args": [username]
        }
        try:
            response = await self.client.post(url=url, json=payload, timeout=120.0)
            response.raise_for_status()
            response_data :Dict = response.json()
            
            if response.status_code == 200:
                self.logger.info(f"Query success.")
                result = response_data["Result"]
                if result:
                    return result
                else:
                    self.logger.info(f"No such a account named {username}")
                    return None
            else:
                self.logger.error(f"Query failed! Error:{response}")
                return None
            
        except Exception as e:
            self.logger.error(f"Query failed! Error:{str(e)}")
            return None
    
    
    async def insert_user_info(self, username: str,  password: str)->bool:
        """插入用户信息"""
        insert_sql = f"INSERT INTO {self.table} (username, password) VALUES (%s, %s);"
        url = self.mysql_agent_url + "/database/mysql/insert"
        payload = {
            "id": self.connect_id,
            "sql": insert_sql,
            "sql_args": [username, password]
        }
        try:
            response = await self.client.post(url=url, json=payload, timeout=120.0)
            response.raise_for_status()
            response_data :Dict = response.json()
            
            if response.status_code == 200:
                result = response_data["Result"]
                if result :
                    # TODO 待修改，正式上线时删掉password
                    self.logger.info(f"Insert userinfo success. Username:{username}, Password:{password}")
                    return True
                else:
                    self.logger.warning(f"Insert userinfo failed. Username:{username}")
                    return False
            else:
                self.logger.error(f"Insert userinfo failed! Error:{response}")
                return False
            
        except Exception as e:
            self.logger.error(f"Insert failed! Error:{str(e)}")
            return False
        
        
    async def update_user_password(self, username: str, new_password: str)->bool:
        """修改用户密码"""
        update_sql = f"UPDATE {self.table} SET password = %s WHERE username = %s;"
        url = self.mysql_agent_url + "/database/mysql/update"
        payload = {
            "id": self.connect_id,
            "sql": update_sql,
            "sql_args": [new_password, username]
        }
        try:
            response = await self.client.post(url=url, json=payload, timeout=120.0)
            response.raise_for_status()
            response_data :Dict = response.json()
            
            if response.status_code == 200:
                result = response_data["Result"]
                if result :
                    # TODO 待修改，正式上线时删掉password
                    self.logger.info(f"Update password success. Username:{username}, NewPassword:{new_password}")
                    return True
                else:
                    self.logger.warning(f"Update password failed. Username:{username}")
                    return False
            else:
                self.logger.error(f"Update password failed! Error:{response}")
                return False
            
        except Exception as e:
            self.logger.error(f"Update password failed! Error:{str(e)}")
            return False
        
    
    async def delete_usr_info(self, username: str)->bool:
        """删除用户信息"""
        delete_sql = f"DELETE FROM {self.table} WHERE username=%s;" 
        url = self.mysql_agent_url + "/database/mysql/delete"
        payload = {
            "id": self.connect_id,
            "sql": delete_sql,
            "sql_args": [username]
        }
        try:
            response = await self.client.post(url=url, json=payload, timeout=120.0)
            response.raise_for_status()
            response_data :Dict = response.json()
            
            if response.status_code == 200:
                result = response_data["Result"]
                if result :
                    self.logger.info(f"Delete user success. Username:{username}")
                    return True
                else:
                    self.logger.warning(f"Delete user failed. Username:{username}")
                    return False
            else:
                self.logger.error(f"Delete user failed! Error:{response}")
                return False
            
        except Exception as e:
            self.logger.error(f"Delete user failed! Error:{str(e)}")
            return False
        
    
    async def connect_to_database(self)->int:
        """连接MySQL数据库"""
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
        
        
