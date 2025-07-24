import os     
import json
from Memory.Memory import Memory     

class LongMemory(Memory):
    def __init__(self,memory_type='long',max_len=1000,forget_factor=0.5,long_memory_filepath=None):
        self.memory_type = memory_type
        self.max_len = max_len
        self.long_memory_filepath = ""
        self.long_memory = {}
        self.forget_factor = forget_factor
        
        if not long_memory_filepath:
            self.long_memory_filepath = os.getenv("MEMORY_DIR", "") + "memory_long.json"
        else:
            self.long_memory_filepath = long_memory_filepath
            
    # 生成一条记忆        
    def create_memory(self, type="long", important=5, abstract="", content="", out_link=""):
        pass

        
    # 在长期记忆中添加一条新memory
    def add_memory(self, memory):
        pass
    
    # 将长期记忆中id为id的memory删除    
    def remove_memory_from_id(self, id):
        pass
    
    # 将长期记忆中找到包含或与content有关的memory并将其删除,返回删除的memory数量以及其id
    def remove_memory_from_content(self, content):
        pass

    # 在id的memory中添加mem
    def update_memory(self, id, mem):
        pass

    # 从记忆中寻找符合str的记忆并返回其id
    def find_memory(self, str):
        pass
    
    # 清除长期记忆（仅清除读取到程序中的dict中的记忆，文件中的仍然保留）
    def clean_memory(self):
        pass
    
    # 将长期记忆写入文件
    def write_memory_to_file(self, mem):
        pass
    
    # 从文件中读取长期记忆
    # 从文件中加载长期记忆并返回 #TODO 这玩意是不是该移动到LongMemory中当做成员函数？
    def load_long_memory_from_file(self):
        memory_dir: str = os.getenv('MEMORY_DIR', "")
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
    
    # 当长期记忆很多很冗杂的时候，需要该函数来产生一个概要，返回一个string
    def summary_memory(self):
        pass
    
    # 当长期记忆超过一定阈值时，会选择删除一些不重要的记忆
    def manage_memory_over_threshold(self):
        pass
    
 