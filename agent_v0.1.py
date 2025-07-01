# Project:      Agent
# Author:       yomu
# Time:         2024/10/24
# Version:      0.1
# Description:  agent main

"""
    启动AI agent的入口
"""

import os
import time
import argparse
import subprocess
import sys
from dotenv import load_dotenv

from Init.Init import SystemInitializer

# 加载环境变量
_ = load_dotenv()



def main():
    try:
        print("🚀 启动 Agent 系统初始化...")
        
        # 创建系统初始化器
        initializer = SystemInitializer()
        
        # 执行完整初始化
        result = initializer.initialize_all()
        
        if result.success:
            print(f"✅ {result.message}")
            
            # 显示系统状态
            status = initializer.get_system_status()
            print(f"📊 系统状态: {status}")
            
            # 执行健康检查
            health = initializer.perform_health_check()
            print(f"🏥 健康状态: {'健康' if health['overall_healthy'] else '存在问题'}")
            
            # 等待用户输入
            input("按回车键关闭系统...")
            
        else:
            print(f"❌ {result.message}")
            if result.failed_components:
                print(f"失败组件: {result.failed_components}")
        
        # 关闭系统
        print("🔄 正在关闭系统...")
        shutdown_success = initializer.shutdown_all()
        
        if shutdown_success:
            print("✅ 系统已安全关闭")
        else:
            print("⚠️  系统关闭时出现错误")
            
    except KeyboardInterrupt:
        print("\n⚠️  用户中断，正在关闭系统...")
        if 'initializer' in locals():
            initializer.shutdown_all()
    except Exception as e:
        print(f"❌ 系统启动失败: {str(e)}")
    


if __name__ == "__main__":
    main()
    