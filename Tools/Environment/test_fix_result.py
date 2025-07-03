#!/usr/bin/env python3
"""
简化的环境验证脚本，用于测试修复效果
"""

import os
import sys
from pathlib import Path

def get_project_root():
    """获取项目根目录"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(current_dir))

def test_basic_functionality():
    """测试基本功能"""
    print("🧪 测试环境脚本修复效果")
    print("="*50)
    
    project_root = get_project_root()
    print(f"📁 项目根目录: {project_root}")
    
    # 检查关键路径是否存在
    paths_to_check = [
        "Module/Utils",
        "Service/UserService", 
        "Init/ExternalServiceInit",
        "Log",
        "Config",
        "agent_v0.1.py"
    ]
    
    all_good = True
    for path_str in paths_to_check:
        full_path = Path(project_root) / path_str
        if full_path.exists():
            print(f"✅ 路径存在: {path_str}")
        else:
            print(f"❌ 路径不存在: {path_str}")
            all_good = False
    
    if all_good:
        print("\n🎉 所有路径检查通过！环境脚本修复成功")
        return True
    else:
        print("\n⚠️  部分路径检查失败")
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)
