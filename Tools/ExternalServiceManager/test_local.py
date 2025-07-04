#!/usr/bin/env python3
"""
简单测试本地化服务管理器
"""

import sys
import os
from pathlib import Path

# 设置路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_import():
    """测试导入功能"""
    print("🔍 测试导入...")
    try:
        from legacy.core import ExternalServiceManager
        print("✅ 成功导入 ExternalServiceManager")
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_creation():
    """测试创建管理器"""
    print("🔍 测试创建管理器...")
    try:
        from service_manager import ExternalServiceManager
        manager = ExternalServiceManager()
        print("✅ 成功创建服务管理器")
        return manager
    except Exception as e:
        print(f"❌ 创建失败: {e}")
        return None

def main():
    print("🚀 开始测试本地化外部服务管理器...")
    
    # 测试导入
    if not test_import():
        return False
    
    # 测试创建
    manager = test_creation()
    if not manager:
        return False
    
    print("🎉 所有测试通过！")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
