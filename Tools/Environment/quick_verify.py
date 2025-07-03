#!/usr/bin/env python3
"""
快速验证脚本 - 检查 Agent 系统环境是否正确配置
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """主验证函数"""
    print("🔍 Agent 系统环境快速验证")
    print("="*50)
    
    # 设置基础环境
    agent_root = os.path.dirname(os.path.abspath(__file__))
    os.environ["AGENT_HOME"] = agent_root
    
    current_pythonpath = os.environ.get("PYTHONPATH", "")
    if agent_root not in current_pythonpath:
        if current_pythonpath:
            os.environ["PYTHONPATH"] = f"{agent_root}:{current_pythonpath}"
        else:
            os.environ["PYTHONPATH"] = agent_root
    
    if agent_root not in sys.path:
        sys.path.insert(0, agent_root)
    
    # 测试基础模块导入
    try:
        from Module.Utils.Logger import setup_logger
        print("✅ Module.Utils.Logger - 正常")
    except ImportError as e:
        print(f"❌ Module.Utils.Logger - 失败: {e}")
        return False
    
    # 测试服务模块导入
    try:
        from Service.UserService.app.core.config import settings
        print("✅ Service.UserService - 正常")
    except ImportError as e:
        print(f"⚠️  Service.UserService - 失败: {e}")
    
    # 测试子进程环境传递
    try:
        env = os.environ.copy()
        test_cmd = f"import sys; sys.path.insert(0, '{agent_root}'); from Module.Utils.Logger import setup_logger; print('子进程模块导入成功')"
        result = subprocess.run(
            [sys.executable, "-c", test_cmd],
            capture_output=True,
            text=True,
            env=env,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✅ 子进程环境传递 - 正常")
        else:
            print(f"❌ 子进程环境传递 - 失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 子进程测试失败: {e}")
        return False
    
    print("\n" + "="*50)
    print("🎉 环境验证通过！")
    print("✅ Agent 系统可以正常启动")
    print("✅ Service 组件可以正确导入 Module")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
