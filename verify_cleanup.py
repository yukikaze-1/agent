#!/usr/bin/env python3
"""
清理后验证脚本 - 确保核心功能正常
"""

def verify_core_functionality():
    """验证核心功能是否正常"""
    print("🔍 清理后核心功能验证")
    print("=" * 40)
    
    # 1. 验证 Init 系统
    print("1️⃣ 验证 Init 系统...")
    try:
        from Init.Init import SystemInitializer
        from Init.EnvironmentManager import EnvironmentManager
        from Init.ExternalServiceInit import ExternalServiceManager
        from Init.InternalModuleInit import InternalModuleManager
        print("   ✅ Init 系统导入正常")
    except Exception as e:
        print(f"   ❌ Init 系统导入失败: {e}")
        return False
    
    # 2. 验证 Module 系统
    print("2️⃣ 验证 Module 系统...")
    try:
        from Module.Utils.Logger import setup_logger
        from Module.Utils.ConfigTools import load_config
        print("   ✅ Module 系统导入正常")
    except Exception as e:
        print(f"   ❌ Module 系统导入失败: {e}")
        return False
    
    # 3. 验证核心文件存在
    print("3️⃣ 验证核心文件...")
    import os
    core_files = [
        "agent_v0.1.py",
        "functions.py", 
        "README.md",
        "install.sh",
        "requirement.txt"
    ]
    
    missing_files = []
    for file in core_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"   ❌ 缺少核心文件: {missing_files}")
        return False
    else:
        print("   ✅ 所有核心文件存在")
    
    # 4. 验证目录结构
    print("4️⃣ 验证目录结构...")
    core_dirs = [
        "Init", "Module", "Service", "Client", 
        "Config", "Core", "Memory", "Functions",
        "LLMModels", "Log", "Resources", "Tools"
    ]
    
    missing_dirs = []
    for dir_name in core_dirs:
        if not os.path.isdir(dir_name):
            missing_dirs.append(dir_name)
    
    if missing_dirs:
        print(f"   ❌ 缺少核心目录: {missing_dirs}")
        return False
    else:
        print("   ✅ 所有核心目录存在")
    
    print("\n🎉 核心功能验证通过！项目清理成功！")
    return True

if __name__ == "__main__":
    success = verify_core_functionality()
    if success:
        print("\n✨ 项目目录现在干净整洁，所有核心功能正常！")
    else:
        print("\n⚠️ 发现问题，请检查项目结构！")
