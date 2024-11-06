# Project:      Agent
# Author:       yomu
# Time:         2024/10/24
# Version:      0.1
# Description:  agent memory mangement

import os
import json
import datetime
import uuid
import random
import shutil
import time
import threading
import logging

from dotenv import load_dotenv
from abc import ABC, abstractmethod
from prompt import summarize_keywords
from sortedcontainers import SortedDict

load_dotenv()

logging.basicConfig(filename='short_memory_errors.log', level=logging.ERROR, format='%(asctime)s %(message)s')

memory_format = {
            "id":           0,  # 使用UUID生成唯一ID
            "type":         "memory type ,long or short",  # 记忆类型
            "create_time":  datetime.datetime.now(),  # 记忆创建时间
            "importance":   1-5,  # 重要性级别
            "abstract":     "memory abstract",  # 记忆摘要
            "keywords":      [], #关键词
            "content": { #记忆
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

# 从文件中加载长期记忆并返回 #TODO 这玩意是不是该移动到LongMemory中当做成员函数？
def load_long_memory():
    memory_dir = os.getenv('MEMORY_DIR')
    memory_file = os.path.join(memory_dir,"memory_long.json")
    memory = {}
    
    if os.path.exists(memory_file):
        with open(memory_file,'r') as f:
            try:
                memory = json.load(f)
            except json.JSONDecodeError:
                memory = {}
    else:
        with open(memory_file,'w') as f:
            json.dump(memory,f)
    return memory

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

class Memory(ABC):# TODO 这抽象类有什么用？
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
    
    
"""
长期记忆，将较为重要的记忆存入文件中保存
    1.
"""
        
class LongMemory(Memory):#TODO 按照ShortMemory来实现
    def __init__(self,memory_type='long',max_len=1000,forget_factor=0.5,long_memory_filepath=None):
        self.memory_type = memory_type
        self.max_len = max_len
        self.long_memory_filepath = ""
        self.long_memory = {}
        self.forget_factor = forget_factor
        
        if not long_memory_filepath:
            self.long_memory_filepath = os.getenv("MEMORY_DIR") + "memory_long.json"
        else:
            self.long_memory_filepath = long_memory_filepath
            
    # 生成一条记忆        
    def create_memory(type="long", important=5, abstract="", content="", out_link=""):
        pass

        
    # 在长期记忆中添加一条新memory
    def add_memory(memory):
        pass
    
    # 将长期记忆中id为id的memory删除    
    def removeory_from_id(id):
        pass
    
    # 将长期记忆中找到包含或与content有关的memory并将其删除,返回删除的memory数量以及其id
    def remove_memory_from_content(content):
        pass
    
    # 在id的memory中添加mem   
    def update_memory(id,mem):
        pass
    
    # 从记忆中寻找符合str的记忆并返回其id   
    def find_memory(str):
        pass
    
    # 清除长期记忆（仅清除读取到程序中的dict中的记忆，文件中的仍然保留）
    def clean_memory():
        pass
    
    # 将长期记忆写入文件
    def write_memory_to_file(mem):
        pass
    
    # 从文件中读取长期记忆
    def read_memory_from_file(mem):
        pass
    
    # 当长期记忆很多很冗杂的时候，需要该函数来产生一个概要，返回一个string
    def summary_memory():
        pass
    
    # 当长期记忆超过一定阈值时，会选择删除一些不重要的记忆
    def manage_memory_over_threshold():
        pass
    
    
    
    
class ShortMemory():#TODO 完善功能
    def __init__(self, memory_type='short', max_len=100, forget_factor=0.5, 
                 expiry_minutes=60, filename='short_memory.json',
                 deleted_filename='deleted_memory.json',
                 cleanup_interval_hours=3):
        super().__init__()
        self.memory_type = memory_type  # 记忆类型
        self.max_len = max_len  # 短期记忆的存储上限
        self.forget_factor = forget_factor   #遗忘因子
        self.expiry_minutes = expiry_minutes  # 记忆的有效期（分钟）
        self.filename = filename  # 保存短期记忆的文件名
        self.deleted_filename = deleted_filename  # 保存删除记忆的文件名
        self.cleanup_interval_hours = cleanup_interval_hours  # 定期清理的时间间隔（小时）
        self.short_memory = self.load_memory_from_file()
        self.expiry_index = self.build_expiry_index()  # 维护一个按过期时间排序的索引
        
        # 启动定期清理过期记忆的线程
        # self.cleaner_thread = threading.Thread(target=self.periodic_cleanup, daemon=True)
        # self.cleaner_thread.start()
        
    # 析构函数
    def __del__(self):
        self.clean_memory()
        print("short memory deleted")
        
    # 从文件加载记忆
    def load_memory_from_file(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                try:
                    data = json.load(f)
                    # 将字符串形式的时间转换回 datetime 对象
                    for mem in data.values():
                        mem['create_time'] = datetime.datetime.strptime(mem['create_time'], "%Y-%m-%d %H:%M:%S")
                        mem['expiry_time'] = datetime.datetime.strptime(mem['expiry_time'], "%Y-%m-%d %H:%M:%S")
                        for version in mem['content']['versions']:
                            version['create_time'] = datetime.datetime.strptime(version['create_time'], "%Y-%m-%d %H:%M:%S")
                    return data
                except json.JSONDecodeError:
                    print(f"Error decoding JSON from file {self.filename}. Creating a new empty memory store.")
                    with open(self.filename, 'w') as f:
                        json.dump({}, f)
                    return {}
        else:
            print(f"No such file as {self.filename}. Creating a new empty memory store.")
            with open(self.filename, 'w') as f:
                json.dump({}, f)
        return {}

     # 将记忆保存到文件
    def save_memory_to_file(self):
        try:
            # 创建备份文件（仅在文件有变化时创建备份）
            backup_created = False
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    current_data = f.read()
                new_data = json.dumps(self.short_memory, indent=4, cls=DateTimeEncoder)
                if current_data != new_data:
                    shutil.copy(self.filename, f"{self.filename}.bak")
                    backup_created = True
            with open(self.filename, 'w') as f:
                json.dump(self.short_memory, f, indent=4, cls=DateTimeEncoder)
            # 删除备份文件
            if backup_created and os.path.exists(f"{self.filename}.bak"):
                os.remove(f"{self.filename}.bak")
        except (IOError, OSError) as e:
            logging.error(f"Error saving memory to file {self.filename}: {e}")
            print(f"Error saving memory to file {self.filename}: {e}")
    
    # 将删除的记忆保存到文件
    def save_deleted_memory_to_file(self, deleted_mem):
        try:
            if os.path.exists(self.deleted_filename):
                with open(self.deleted_filename, 'r') as f:
                    deleted_data = json.load(f)
            else:
                deleted_data = {}

            deleted_data[deleted_mem['id']] = deleted_mem

            with open(self.deleted_filename, 'w') as f:
                json.dump(deleted_data, f, indent=4, cls=DateTimeEncoder)
        except (IOError, OSError) as e:
            logging.error(f"Error saving deleted memory to file {self.deleted_filename}: {e}")
            print(f"Error saving deleted memory to file {self.deleted_filename}: {e}")
                            
    # 生成一条记忆(仅生成，没有添加,后续需使用add_memory()添加进去)
    def create_memory(self, type="short", importance=3, abstract="",keywords=[], content="", out_links=[]):
        new_memory = {
            "id": str(uuid.uuid4()),  # 使用UUID生成唯一ID
            "type": type,  # 记忆类型
            "create_time": datetime.datetime.now(),  # 记忆创建时间
            "importance": importance,  # 重要性级别
            "abstract": abstract,  # 记忆摘要
            "keywords": keywords, #关键词
            "content": {    # 记忆内容
                "current_version": content,# 当前版本的记忆内容
                "versions": [] # 旧版本的记忆内容
            },  
            "out_links":  out_links, # 外部链接
            "expiry_time": (datetime.datetime.now() + datetime.timedelta(minutes=self.expiry_minutes)),  # 记忆过期时间
            "is_expired": False  # 记录是否已经过期
        }
        return new_memory
        
   # 在短期记忆中添加一条新memory
    def add_memory(self, mem):
        if len(self.short_memory) >= self.max_len:
            self.forget_memory()
        if len(self.short_memory) >= self.max_len:
            raise MemoryError("Unable to add new memory: memory limit still exceeded after forgetting.")
        self.short_memory[mem['id']] = mem
        expiry_time = mem['expiry_time']
        if expiry_time not in self.expiry_index or not isinstance(self.expiry_index[expiry_time], list):
            self.expiry_index[expiry_time] = []
        self.expiry_index[expiry_time].append(mem['id'])
        self.save_memory_to_file()
    
    # 将短期记忆中id为id的memory删除
    def remove_memory_from_id(self, id):
        if id in self.short_memory:
            deleted_mem = self.short_memory[id]
            expiry_time = deleted_mem['expiry_time']
            self.save_deleted_memory_to_file(deleted_mem)
            del self.short_memory[id]
            if expiry_time in self.expiry_index and isinstance(self.expiry_index[expiry_time], list):
                if id in self.expiry_index[expiry_time]:
                    self.expiry_index[expiry_time].remove(id)
                if not self.expiry_index[expiry_time]:
                    del self.expiry_index[expiry_time]
            self.save_memory_to_file()
            
    # 从短期记忆中寻找符合content的记忆并返回其id
    def find_memory(self, content):
        ids = []
        # 根据content生成keywords
        keywords = set(summarize_keywords(content))
        # 根据keywords来找到对应的记忆
        for mem_id, mem in self.short_memory.items():
            memory_keywords = set(mem['keywords'])
            if keywords & memory_keywords:
                ids.append(mem_id)
        return ids    
    
    # 将短期记忆中找到包含或与content有关的memory并将其删除,返回删除的memory数量以及其id
    def remove_memory_from_content(self,content):
        remove_ids = self.find_memory(content)
        for id in remove_ids:
            self.remove_memory_from_id(id)
        self.save_memory_to_file()
        return len(remove_ids),remove_ids
       
    # 在id=id的memory中更新mem(即项该memory中更新contents中的current_version部分，并更新versions)
    def update_memory(self, id, content):
        if id in self.short_memory:
            # 将当前版本的内容保存到旧版本
            self.short_memory[id]['content']['versions'].append({
                "create_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "content": self.short_memory[id]['content']['current_version']
            })
            # 更新当前版本内容
            self.short_memory[id]['content']['current_version'] = content
            self.save_memory_to_file()
        else:
            print(f"No such memory with id: {id}, doing nothing.")
                
    # 当短期记忆很多很杂的时候，需要该函数来产生一个概要，返回一个string # TODO 该函数应该调用大模型来产生一个概要
    def summary_memory(self):
        summary = "\n".join([f"[{mem['create_time']}] {mem['abstract']}" for mem in self.short_memory.values() if not mem['is_expired']])
        return summary
    
    # 清除记忆
    def clean_memory(self):
        self.short_memory.clear()
        self.expiry_index.clear()
        self.save_memory_to_file()
    
    """   
        # # 选择一些短期记忆并写入文件
        # # (slect_type==0 :随机选择一些短期记忆)
        # # (slect_type==1 :根据后面的ids选择短期记忆)
        # def select_and_write_short_memory_to_file(self, select_type=0, ids=None, filename="short_memory.txt"):
        #     selected_memory = []
        #     if select_type == 0:
        #         selected_memory = random.sample(list(self.short_memory.values()), min(len(self.short_memory), 5))
        #     elif select_type == 1 and ids is not None:
        #         selected_memory = [self.short_memory[mem_id] for mem_id in ids if mem_id in self.short_memory]

        #     try:
        #         with open(filename, 'w') as f:
        #             for mem in selected_memory:
        #                 f.write(f"{mem}\n")
        #     except (IOError, OSError) as e:
        #         print(f"Error writing selected memories to file {filename}: {e}")
    """
    
    # 随机选择一些短期记忆并返回其id
    def select_random_memory_ids(self, num_to_select=5):
        selected_ids = random.sample(list(self.short_memory.keys()), min(len(self.short_memory), num_to_select))
        return selected_ids
    
    # 忘记一些记忆
    def forget_memory(self):
      # 选择重要性小于等于2的记忆
        low_importance_memories = [mem_id for mem_id, mem in self.short_memory.items() if mem['importance'] <= 2]
        num_to_forget = int(len(self.short_memory) * self.forget_factor)
        num_to_forget = min(len(low_importance_memories), num_to_forget)
        memory_ids_to_forget = random.sample(low_importance_memories, num_to_forget)
        if len(memory_ids_to_forget) == 0:
            print("No memory to forget,please check the settings")
        else:
            for mem_id in memory_ids_to_forget:
                self.remove_memory_from_id(mem_id)
            self.save_memory_to_file()
            print(f"Forgot some memeories like: {memory_ids_to_forget} ...")
            
    # 构建过期时间索引
    def build_expiry_index(self):
        expiry_index = SortedDict()
        for mem_id, mem in self.short_memory.items():
            expiry_time = mem['expiry_time']
            if expiry_time not in expiry_index or not isinstance(expiry_index[expiry_time], list):
                expiry_index[expiry_time] = []
            expiry_index[expiry_time].append(mem_id)
        return expiry_index
    
    # 定期清理过期记忆
    def periodic_cleanup(self):
        print("定期清理过期记忆的线程运行中...")
        while True:
            time.sleep(self.cleanup_interval_hours * 60 * 60)  # 使用自定义的时间间隔
            self.expire_memory()
            self.save_memory_to_file()
            
    # 移除过期的记忆 
    def expire_memory(self):
        current_time = datetime.datetime.now()
        expired_keys = [key for key in list(self.expiry_index.keys()) if key < current_time]
        print("待删除的记忆：",expired_keys)
        
        for expiry_time in expired_keys:
            mem_ids = self.expiry_index.pop(expiry_time)
            for mem_id in mem_ids:
                if mem_id in self.short_memory:
                    deleted_mem = self.short_memory[mem_id]
                    self.save_deleted_memory_to_file(deleted_mem)
                    del self.short_memory[mem_id]
        self.save_memory_to_file()


        
        