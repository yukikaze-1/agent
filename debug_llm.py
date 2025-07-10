#!/usr/bin/env python3
"""
LLMProxy调试脚本
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.append('/home/yomu/agent')

from Module.LLM.LLMProxy import LLMProxy

async def debug_llm_proxy():
    print("🔍 开始LLMProxy调试...")
    
    try:
        print("1. 创建LLMProxy实例...")
        proxy = LLMProxy()
        print("✅ LLMProxy实例创建成功")
        
        print("2. 开始初始化...")
        await proxy.initialize()
        print("✅ 初始化成功")
        
        print("3. 测试健康检查...")
        health = await proxy.check_health()
        print(f"✅ 健康检查结果: {health}")
        
        print("4. 测试模型列表...")
        models = await proxy.list_models()
        print(f"✅ 发现 {len(models)} 个模型")
        
        print("5. 清理资源...")
        await proxy.cleanup()
        print("✅ 清理完成")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_llm_proxy())
