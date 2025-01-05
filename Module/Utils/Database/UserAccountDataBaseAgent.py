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
                    passwword
                    database
                    table
                    charset
                    
        # TODO 应该让程序自动创建一个数据库，待实现            
        需要手动在mysql数据库中创建一个如下的表(注：要先手动创建一个名为userinfo的database才行):    
            CREATE TABLE account (
                id INT AUTO_INCREMENT,      -- 自增列
                username VARCHAR(255) NOT NULL, -- 用户名
                password VARCHAR(255) NOT NULL, -- 密码
                PRIMARY KEY (username),     -- 将 username 设置为主键
                UNIQUE KEY (id)             -- 保证 id 唯一，但不是主键
            );
    """
    def __init__(self, logger: Logger=None):
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
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(10.0, read=60.0)
        )
        
        # 向MySQLAgent注册，返回一个链接id
        self.connect_id: Optional[int] = None
        
        
    async def init_connection(self) -> None:
        """
        真正执行连接, 并为 self.connect_id 赋值
        """
        try:
            self.connect_id = await self.connect_to_database()
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
            response = await self.client.post(url=url, json=payload)
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
            response = await self.client.post(url=url, json=payload)
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
            response = await self.client.post(url=url, json=payload)
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
            response = await self.client.post(url=url, json=payload)
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
            response = await self.client.post(url=url, json=payload, headers=headers)
            response.raise_for_status()
            response_data :Dict = response.json()
            
            if response.status_code == 200:
                id = response_data.get("ConnectionID")
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
        
        
