# Project:      Agent
# Author:       yomu
# Time:         2024/12/12
# Version:      0.1
# Description:  agent database module

"""
    agent数据库模块
    
"""

from typing import Optional, Tuple, List

# TODO 待实现
class DataBase():
    """
        agent基础模块 数据库模块
        能自定义key type 和value type，默认均为string
        
    """
    def __init__(self, key_type: type=str, value_type: type=str):
        self.db = {}
        self.key_type=key_type 
        self.value_type=value_type 
    
    def init_database(self):
        """初始化一个数据库"""
        # TODO 通过self.key_type和self.value_type来初始化一个数据库
        pass
    
    def query(self, key)->Tuple[Optional[str], Optional[str]]:
        """查询数据"""
        value = self.db.get(key, None)
        if value:
            return key, value
        return None, None
    
    def insert(self, key, value)->bool:
        """插入数据"""
        if not self._type_check(key, value):
            return False
        if key in self.db:
            print("Key is already in the database")
            return False
        self.db[key] = value
        return True
    
    def modify(self, key, new_value)->bool:
        """修改数据"""
        if not self._type_check(key, new_value):
            return False
        
        if key in self.db:
            self.db[key] = new_value
            return True
        
        return False

    
    def delete(self, key)->bool:
        """删除数据"""
        if not self._type_check(key=key):
            return False  # 类型检查失败
        if key in self.db:
            del self.db[key]
            return True
        return False
    
    def clear(self):
        """清空数据库"""
        self.db.clear()
    
    
    def _type_check(self, key=None, value=None)->bool:
        """类型检查"""
        if not key and not value:
            print(f"Key or Value need at least one!")
            return False
        if key and not isinstance(key, self.key_type):
            print(f"Key must be of type {self.key_type.__name__}")
            return False
        if value and not isinstance(value, self.value_type):
            print(f"Value must be of type {self.value_type.__name__}")
            return False
        return True
    
    def __del__(self):
        pass
    