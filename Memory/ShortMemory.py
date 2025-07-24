# Project:      Agent
# Author:       yomu
# Time:         2024/07/17
# Version:      0.1
# Description:  agent short memory

import os
import json
import datetime
import uuid
import random
import shutil
import time
import threading
import logging

from sortedcontainers import SortedDict

from Prompt.prompt import summarize_keywords
from Memory.Memory import Memory, DateTimeEncoder, memory_format



class ShortMemory(Memory):
    """
        短期记忆，存于内存中，定期持久化
    """
    def __init__(self,
                 memory_type='short', 
                 max_len=100, 
                 forget_factor=0.5,
                 expiry_minutes=60, 
                 filename='short_memory.json',
                 deleted_filename='deleted_memory.json',
                 cleanup_interval_hours=3
                 ):
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


        
  