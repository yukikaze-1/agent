import datetime
import json
import os
import shutil
import threading
import uuid
import random
import time
from sortedcontainers import SortedDict

# 确保在测试前导入 ShortMemory 类
from Memory.Memory import *

def test():
    # 创建一个 ShortMemory 实例
    short_memory = ShortMemory(max_len=10, forget_factor=0.5, expiry_minutes=1, cleanup_interval_hours=0.01)
    
    # 创建并添加多个记忆
    for i in range(15):
        mem = short_memory.create_memory(abstract=f"Memory {i+1}", importance= (i % 5) + 1,content=f"This is the content of memory {i+1}.")
        short_memory.add_memory(mem)
    print("Added 15 memories.")
    
    # 显示当前记忆
    print("Current memories:")
    print(json.dumps(short_memory.short_memory, indent=4, cls=DateTimeEncoder))
    
    # 更新一个记忆
    mem_to_update = list(short_memory.short_memory.keys())[0]
    short_memory.update_memory(mem_to_update, "Updated content of memory 1.")
    print(f"Updated memory with ID {mem_to_update}.")
    
    # 显示更新后的记忆
    print("Current memories after update:")
    print(json.dumps(short_memory.short_memory, indent=4, cls=DateTimeEncoder))
    
    # 测试忘记记忆
    short_memory.forget_memory()
    print("Memories after forgetting some:")
    print(json.dumps(short_memory.short_memory, indent=4, cls=DateTimeEncoder))
    
    # 再次测试忘记记忆
    short_memory.forget_memory()
    print("Memories after forgetting some more:")
    print(json.dumps(short_memory.short_memory, indent=4, cls=DateTimeEncoder))
    
    # 等待记忆过期
    print("Waiting for memories to expire...")
    time.sleep(65)  # 等待记忆过期（1分钟）
    short_memory.expire_memory()
    
    # 显示过期检查后的记忆
    print("Memories after expiration check:")
    print(json.dumps(short_memory.short_memory, indent=4, cls=DateTimeEncoder))


# 测试 ShortMemory 类的代码
if __name__ == "__main__":
    test()
    
    