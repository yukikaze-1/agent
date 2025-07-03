#!/usr/bin/env python3
"""
简化的环境验证脚本
只测试核心功能，避免复杂的子进程操作
"""

import os
import sys
from pathlib import Path

def get_project_root():
    """获取项目根目录"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(current_dir))

def test_basic_paths():
    """测试基本路径"""
    print("🔍 测试基本路径...")
    
    project_root = get_project_root()
    print(f"📁 项目根目录: {project_root}")
    
    # 检查关键路径
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
        if not full_path.exists():
            print(f"❌ 路径不存在: {path_str}")
            all_good = False
        else:
            print(f"✅ 路径存在: {path_str}")
    
    return all_good

def test_module_import():
    """测试模块导入"""
    print("\n🔍 测试模块导入...")
    
    project_root = get_project_root()
    
    # 设置环境变量
    os.environ['AGENT_HOME'] = project_root
    os.environ['PYTHONPATH'] = project_root
    
    # 添加到 sys.path
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    try:
        from Module.Utils.Logger import setup_logger
        print("✅ Module.Utils.Logger 导入成功")
        return True
    except ImportError as e:
        print(f"❌ Module.Utils.Logger 导入失败: {e}")
        return False

def test_env_files():
    """测试环境配置文件"""
    print("\n🔍 测试环境配置文件...")
    
    project_root = get_project_root()
    
    env_files = [
        ".env.global",
        ".env.development"
    ]
    
    all_good = True
    for env_file in env_files:
        file_path = os.path.join(project_root, env_file)
        if os.path.exists(file_path):
            print(f"✅ 环境文件存在: {env_file}")
            
            # 检查是否有硬编码路径
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if "/home/yomu/agent" in content and "${AGENT_HOME}" not in content:
                    print(f"⚠️  {env_file} 包含硬编码路径")
                    all_good = False
        else:
            print(f"❌ 环境文件不存在: {env_file}")
            all_good = False
    
    return all_good

def main():
    """主函数"""
    print("🌍 Agent 系统简化环境验证")
    print("="*50)
    
    tests = [
        ("基本路径测试", test_basic_paths),
        ("模块导入测试", test_module_import),
        ("环境文件测试", test_env_files)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} 执行异常: {e}")
            results.append((test_name, False))
    
    # 输出总结
    print(f"\n{'='*50}")
    print("📊 验证结果:")
    print(f"{'='*50}")
    
    all_passed = True
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not success:
            all_passed = False
    
    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 所有测试通过！")
        print("✅ 环境已正确配置，其他人 clone 后应该可以直接使用")
        return 0
    else:
        print("⚠️  部分测试失败，需要进一步检查")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
