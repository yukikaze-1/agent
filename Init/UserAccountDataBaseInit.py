# Project:      Agent
# Author:       yomu
# Time:         2024/12/12
# Version:      0.1
# Description:  agent User information database initialize

"""
    初始化用户账户数据库
"""

# TODO Moudle中应该实现一个database 模块

from typing import Tuple, Optional
from Module.Utils.DataBase import DataBase

class UserAccountDataBase():
    def __init__(self):
        self.db = DataBase(key_type=str, value_type=str)
    
    def query(self, key: str)->Optional[str]:
        """查询数据"""
        return key, self.db.query(key)
    
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

