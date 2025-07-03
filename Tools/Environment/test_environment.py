#!/usr/bin/env python3
"""
测试环境变量传递是否正常工作
"""

import sys
import os

# 添加项目根目录到 Python 路径
AGENT_ROOT = os.path.dirname(os.path.dirname(__file__))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

def test_module_import():
    """测试模块导入是否正常"""
    try:
        print("🧪 测试模块导入...")
        
        # 测试基础导入
        from Module.Utils.Logger import setup_logger
        print("✅ Module.Utils.Logger 导入成功")
        
        from Module.Utils.ConfigTools import load_config
        print("✅ Module.Utils.ConfigTools 导入成功")
        
        # 测试 FastAPI 工具导入
        try:
            from Module.Utils.FastapiServiceTools import register_service_to_consul
            print("✅ Module.Utils.FastapiServiceTools 导入成功")
        except ImportError as e:
            print(f"⚠️  Module.Utils.FastapiServiceTools 导入失败: {e}")
        
        # 测试服务导入
        try:
            from Service.UserService.app.core.config import settings
            print("✅ Service.UserService 配置导入成功")
        except ImportError as e:
            print(f"⚠️  Service.UserService 配置导入失败: {e}")
        
        print("\n📊 环境变量状态:")
        print(f"  AGENT_HOME: {os.environ.get('AGENT_HOME', '未设置')}")
        print(f"  PYTHONPATH: {os.environ.get('PYTHONPATH', '未设置')}")
        print(f"  AGENT_ENV: {os.environ.get('AGENT_ENV', '未设置')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 模块导入测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始环境变量和模块导入测试...")
    print("="*60)
    
    success = test_module_import()
    
    print("\n" + "="*60)
    if success:
        print("✅ 测试通过！环境变量和模块导入正常工作")
        return 0
    else:
        print("❌ 测试失败！请检查环境配置")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
