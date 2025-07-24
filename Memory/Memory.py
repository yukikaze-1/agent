# Project:      Agent
# Author:       yomu
# Time:         2024/10/24
# Version:      0.1
# Description:  agent memory definition

import os
import json
import datetime

from dotenv import load_dotenv
from abc import ABC, abstractmethod

from sortedcontainers import SortedDict

load_dotenv()


memory_format = {
            "id":           0,  # 使用UUID生成唯一ID
            "type":         "memory type ,long or short",  # 记忆类型
            "create_time":  datetime.datetime.now(),  # 记忆创建时间
            "importance":   1-5,  # 重要性级别
            "abstract":     "memory abstract",  # 记忆摘要
            "keywords":      [], #关键词
            "content": { #记忆内容
                "current_version": "memory content",
                "versions": [
                 {
                    "create_time": datetime.datetime.now(), # 旧记忆的创建时间
                    "content": "older version of memory" #旧记忆
                 }
                ]
            },
            "out_links":  [ # 外部链接
                {"url": "file url", "description": "description of the link"}
            ],
            "expiry_time":  "the time of memory that should remove",  # 记忆过期时间
            "is_expired":   " False or True "# 记录是否已经过期
    }


"""
    long memory:
        store at MEMEORY_DIR and the name is : memory_long.json
        this function find the json and load it into list
        then return 
        
    short memory:
        store at the program,when program ends,it will select some memories(some functions do this)
        to append to the long memory file
"""

# 自定义的 JSON 编码器来处理 datetime 对象
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        return super().default(obj)




"""
    抽象基类Memory，定义了Memory类的接口：
        0.生成记忆
        1.添加记忆
        2.删除记忆(id或者模糊匹配)
        3.更新记忆(id)
        4.寻找记忆(id或者模糊匹配)
        5.总结记忆摘要(记忆回顾
        6.清除所有记忆
        
"""

class Memory(ABC):
    # 生成记忆
    @abstractmethod
    def create_memory():
        pass
    
    # 在记忆中添加一条新memory
    @abstractmethod
    def add_memory():
        pass
    
    # 将记忆中id为id的memory删除    
    @abstractmethod
    def removeory_from_id():
        pass
    
    # 将记忆中找到包含或与content有关的memory并将其删除,返回删除的memory数量以及其id
    @abstractmethod
    def removeory_from_content():
        pass
    
    # 在id的memory中添加mem    
    @abstractmethod
    def update_memory(id,mem):
        pass
        
    # 从记忆中寻找符合str的记忆并返回其id
    @abstractmethod
    def find_memory(str):
        pass
    
    # 当记忆很多很冗杂的时候，需要该函数来产生一个概要，返回一个string
    @abstractmethod
    def summary_memory():
        pass       
    
    # 清除记忆
    @abstractmethod
    def clean_memory():
        pass
    
    
      
    
         