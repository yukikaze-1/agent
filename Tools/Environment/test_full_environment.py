#!/usr/bin/env python3
"""
测试 subprocess 环境变量传递的完整验证脚本
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# 确保项目根目录在 Python 路径中
AGENT_ROOT = os.path.dirname(os.path.abspath(__file__))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

def setup_test_environment():
    """设置测试环境变量"""
    os.environ["AGENT_HOME"] = AGENT_ROOT
    os.environ["AGENT_ENV"] = "testing"
    
    # 设置 Python 路径
    current_pythonpath = os.environ.get("PYTHONPATH", "")
    if AGENT_ROOT not in current_pythonpath:
        if current_pythonpath:
            os.environ["PYTHONPATH"] = f"{AGENT_ROOT}:{current_pythonpath}"
        else:
            os.environ["PYTHONPATH"] = AGENT_ROOT
    
    print("✅ 测试环境变量设置完成")
    print(f"📁 AGENT_HOME: {os.environ.get('AGENT_HOME')}")
    print(f"🐍 PYTHONPATH: {os.environ.get('PYTHONPATH')}")

def test_direct_import():
    """测试当前进程的直接导入"""
    print("\n🧪 测试当前进程的模块导入...")
    
    try:
        from Module.Utils.Logger import setup_logger
        print("✅ 当前进程 - Module.Utils.Logger 导入成功")
        return True
    except ImportError as e:
        print(f"❌ 当前进程 - 模块导入失败: {e}")
        return False

def test_subprocess_without_env():
    """测试不传递环境变量的子进程"""
    print("\n🧪 测试不传递环境变量的子进程...")
    
    try:
        # 不传递环境变量
        test_script = os.path.join(AGENT_ROOT, "test_subprocess_env.py")
        result = subprocess.run(
            [sys.executable, test_script],
            capture_output=True,
            text=True,
            timeout=10
            # 注意：没有传递 env 参数
        )
        
        if result.returncode == 0:
            print("⚠️  不传递环境变量的子进程成功运行（可能依赖系统环境）")
            return True
        else:
            print("❌ 不传递环境变量的子进程失败（符合预期）")
            return False
            
    except Exception as e:
        print(f"❌ 子进程测试失败: {e}")
        return False

def test_subprocess_with_env():
    """测试传递环境变量的子进程"""
    print("\n🧪 测试传递环境变量的子进程...")
    
    try:
        # 准备环境变量
        env = os.environ.copy()
        
        test_script = os.path.join(AGENT_ROOT, "test_subprocess_env.py")
        result = subprocess.run(
            [sys.executable, test_script],
            capture_output=True,
            text=True,
            timeout=10,
            env=env  # 传递环境变量
        )
        
        if result.returncode == 0:
            print("✅ 传递环境变量的子进程成功运行")
            
            # 解析结果
            try:
                result_data = json.loads(result.stdout)
                print("📊 子进程环境检查结果:")
                print(f"  成功: {result_data.get('success', False)}")
                print(f"  模块导入: {result_data.get('module_import', 'Unknown')}")
                
                for error in result_data.get('errors', []):
                    print(f"  错误: {error}")
                    
                return result_data.get('success', False)
            except json.JSONDecodeError:
                print("⚠️  无法解析子进程输出，但进程成功运行")
                print(f"输出: {result.stdout}")
                return True
        else:
            print("❌ 传递环境变量的子进程失败")
            print(f"错误输出: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 子进程测试失败: {e}")
        return False

def test_process_manager():
    """测试 ProcessManager 的环境变量传递"""
    print("\n🧪 测试 ProcessManager 的环境变量传递...")
    
    try:
        from Init.ExternalServiceInit.utils.process_manager import ProcessManager
        
        # 创建 ProcessManager 实例
        pm = ProcessManager()
        
        # 测试环境变量准备函数
        env = pm._prepare_environment()
        
        print("📊 ProcessManager 准备的环境变量:")
        print(f"  AGENT_HOME: {env.get('AGENT_HOME', 'Not Set')}")
        print(f"  PYTHONPATH: {env.get('PYTHONPATH', 'Not Set')}")
        print(f"  AGENT_ENV: {env.get('AGENT_ENV', 'Not Set')}")
        
        # 检查关键环境变量
        required_vars = ['AGENT_HOME', 'PYTHONPATH', 'AGENT_ENV']
        all_present = all(env.get(var) for var in required_vars)
        
        if all_present:
            print("✅ ProcessManager 环境变量准备正确")
            return True
        else:
            print("❌ ProcessManager 环境变量准备不完整")
            return False
            
    except Exception as e:
        print(f"❌ ProcessManager 测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始环境变量传递完整测试...")
    print("="*60)
    
    # 设置测试环境
    setup_test_environment()
    
    # 执行各项测试
    tests = [
        ("直接导入测试", test_direct_import),
        ("子进程无环境变量测试", test_subprocess_without_env),
        ("子进程有环境变量测试", test_subprocess_with_env),
        ("ProcessManager测试", test_process_manager),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} 执行异常: {e}")
            results.append((test_name, False))
    
    # 输出总结
    print(f"\n{'='*60}")
    print("📊 测试结果总结:")
    print(f"{'='*60}")
    
    all_passed = True
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not success:
            all_passed = False
    
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 所有测试通过！环境变量传递工作正常")
        print("✅ Service 下的 FastAPI 服务应该能够正确导入 Module.Utils 等模块")
        return 0
    else:
        print("⚠️  部分测试失败，请检查配置")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
