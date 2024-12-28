# Project:      Agent
# Author:       yomu
# Time:         2024/12/12
# Version:      0.1
# Description:  agent User information database initialize

"""
    初始化用户账户数据库
"""

from typing import Dict
from typing import Tuple, Optional
from dotenv import dotenv_values
from logging import Logger

from Module.Utils.Logger import setup_logger
from Module.Utils.LoadConfig import load_config
from Module.Utils.Database.MySQLAgent import MySQLAgent


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
        
        self.env_vars = dotenv_values("/home/yomu/agent/Module/Utils/Database/.env")
        self.config_path = self.env_vars.get("USER_ACCOUNT_DATABASE_AGENT_CONFIG_PATH","")
        self.config = load_config(config_path=self.config_path, config_name='UserAccountDataBaseAgent', logger=self.logger)
        
        self.db_name = self.config.get("database","")
        self.table = self.config.get("table", "")
        
        self.db = MySQLAgent(logger=self.logger)
        self.connect_id = -1
        
        self.connect_to_db()
        
        
    def fetch_user_by_name(self,username: str)-> Optional[Dict]:
        """通过名字来查询用户账号信息"""
        query_sql = f"SELECT * FROM {self.table} WHERE username = %s;"
        result = self.db.query(self.connect_id, sql=query_sql, sql_args=[username,])
        if not result:
            self.logger.info(f"No such a account named {username}")
            return None
        self.logger.info(f"Query success. Username:{username}")
        return result
    
    
    def insert_user_info(self, username: str,  password: str)->bool:
        """插入用户信息"""
        insert_sql = f"INSERT INTO {self.table} (username, password) VALUES (%s, %s);"
        result = self.db.insert(self.connect_id, sql=insert_sql, sql_args=[username, password])
        if result:
            # TODO 待修改，正式上线时删掉password
            self.logger.info(f"Insert userinfo success. Username:{username}, Password:{password}")
            return True
        else:
            self.logger.warning(f"Insert userinfo failed. Username:{username}")
            return False
        
        
    def update_user_password(self, username: str, new_password: str)->bool:
        """修改用户密码"""
        update_sql = f"UPDATE {self.table} SET password = %s WHERE username = %s;"
        result = self.db.modify(self.connect_id, update_sql, [new_password, username])
        if result:
            # TODO 待修改，正式上线时删掉NewPassword
            self.logger.info(f"Insert userinfo success. Username:{username}, NewPassword:{new_password}")
            return True
        else:
            self.logger.warning(f"Update password failed. Username:{username}")
            return False
        
    
    def connect_to_db(self):
        res = self.db.connect(host=self.config["host"],
                        user=self.config["user"],
                        password=self.config["password"],
                        database=self.config["database"],
                        )
        if res == -1:
            self.logger.error(f"Connect to database '{self.db_name}' failed!")
            raise ConnectionError(f"Connect to database '{self.db_name}' failed!")
        else:    
            self.connect_id = res
            self.logger.info(f"Connect to database '{self.db_name}' success!")
            
        
