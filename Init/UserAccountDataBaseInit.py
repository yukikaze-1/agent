# Project:      Agent
# Author:       yomu
# Time:         2024/12/12
# Version:      0.1
# Description:  agent User information database initialize

"""
    初始化用户账户数据库
"""

# TODO Moudle中应该实现一个database 模块
import yaml
import logging
from typing import Dict
from typing import Tuple, Optional
from dotenv import dotenv_values
from Module.Utils.DataBase import DataBase
from Module.Utils.MySQL import MySQLDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class UserAccountDataBase():
    def __init__(self):
        self.db = DataBase(key_type=str, value_type=str)
    
    def query(self, key: str)->Tuple[Optional[str], Optional[str]]:
        """查询数据,如果查到，返回key, value, 没查到返回None, None"""
        return  self.db.query(key)
    
    def insert(self, key:str, value:str)->bool:
        """插入数据"""
        return self.db.insert(key, value)
    
    def modify(self, key:str, new_value:str)->bool:
        """修改数据"""
        return self.db.modify(key, new_value)
    
    def delete(self, key:str)->bool:
        """删除数据"""
        return self.db.delete(key)
    
    def clear(self):
        """清空数据库"""
        self.db.clear()
    
    def __del__(self):
        pass

class UserAccountDataBase_mysql():
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
    def __init__(self):
        self.env_vars = dotenv_values("Init/.env")
        self.config_path = self.env_vars.get("INIT_CONFIG_PATH","")
        self.config = self._load_config(self.config_path)
        self.db_name = self.config["database"]
        self.table = self.config["table"]
        
        self.db = MySQLDatabase()
        self.connect_id = -1
        
        self.connect_to_db()
        
        
    def fetch_user_by_name(self,username: str)-> Optional[Dict]:
        """通过名字来查询用户账号信息"""
        query_sql = f"SELECT * FROM {self.table} WHERE username = %s;"
        result = self.db.query(self.connect_id, sql=query_sql, sql_args=[username,])
        if not result:
            logging.info(f"No such a account named {username}")
            return None
        logging.info(f"Query success. Username:{username}")
        return result
    
    
    def insert_user_info(self, username: str,  password: str)->bool:
        """插入用户信息"""
        insert_sql = f"INSERT INTO {self.table} (username, password) VALUES (%s, %s);"
        result = self.db.insert(self.connect_id, sql=insert_sql, sql_args=[username, password])
        if result:
            # TODO 待修改，正式上线时删掉password
            logging.info(f"Insert userinfo success. Username:{username}, Password:{password}")
            return True
        else:
            logging.info(f"Insert userinfo failed. Username:{username}")
            return False
        
        
    def update_user_password(self, username: str, new_password: str)->bool:
        """修改用户密码"""
        update_sql = f"UPDATE {self.table} SET password = %s WHERE username = %s;"
        result = self.db.modify(self.connect_id, update_sql, [new_password, username])
        if result:
            # TODO 待修改，正式上线时删掉NewPassword
            logging.info(f"Insert userinfo success. Username:{username}, NewPassword:{new_password}")
            return True
        else:
            logging.info(f"Update password failed. Username:{username}")
            return False
        
    
    def connect_to_db(self):
        res = self.db.connect(host=self.config["host"],
                        user=self.config["user"],
                        password=self.config["password"],
                        database=self.config["database"],
                        )
        if res == -1:
            logging.info(f"Connect to database {self.db_name} failed!")
            raise ConnectionError(f"Connect to database {self.db_name} failed!")
        else:    
            self.connect_id = res
            logging.info(f"Connect to database {self.db_name} success!")
            
        
    def _load_config(self, config_path: str) -> Dict:
        """从config_path中读取配置(*.yml)
            
            返回：
                yml文件中配置的字典表示
        """
        if config_path is None:
            raise ValueError(f"Config file {config_path} is empty.Please check the file 'Init/.env'.It should set the 'INIT_CONFIG_PATH'")
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)  # 使用 safe_load 安全地加载 YAML 数据
                res = config["user_account_database_config"]
            return res
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file {config_path} not found.")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing the YAML config file: {e}")
        
    
