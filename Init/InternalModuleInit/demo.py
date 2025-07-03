#!/usr/bin/env python3
"""
InternalModuleInit 演示脚本

展示如何使用新的内部模块管理器。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from . import InternalModuleManager


def demonstrate_basic_usage():
    """演示基本用法"""
    print("=" * 50)
    print("InternalModuleInit 基本用法演示")
    print("=" * 50)
    
    try:
        # 创建管理器实例
        print("1. 创建模块管理器...")
        manager = InternalModuleManager()
        print("✅ 管理器创建成功")
        
        # 显示配置信息
        print("\n2. 显示配置信息...")
        print(f"   支持的模块: {manager.support_modules}")
        
        # 初始化模块
        print("\n3. 初始化模块...")
        success, base_success, base_fail, opt_success, opt_fail = manager.init_modules()
        
        print(f"   初始化结果: {'成功' if success else '部分失败'}")
        print(f"   基础模块 - 成功: {base_success}, 失败: {base_fail}")
        print(f"   可选模块 - 成功: {opt_success}, 失败: {opt_fail}")
        
        # 显示运行状态
        print("\n4. 显示运行状态...")
        running_modules = manager.list_started_modules()
        print(f"   运行中的模块: {running_modules}")
        
        # 健康检查
        print("\n5. 健康检查...")
        status = manager.get_module_status()
        print(f"   基础模块健康状态: {status['base_modules']}")
        print(f"   可选模块健康状态: {status['optional_modules']}")
        print(f"   整体健康状态: {'健康' if status['overall_healthy'] else '不健康'}")
        
        # 依赖关系信息
        print("\n6. 依赖关系信息...")
        dependencies = manager.get_dependency_info()
        if dependencies:
            for module, deps in dependencies.items():
                print(f"   {module} 依赖于: {deps}")
        else:
            print("   没有配置依赖关系")
        
        # 停止可选模块
        print("\n7. 停止可选模块...")
        opt_ok, opt_stopped, opt_failed = manager.stop_optional_modules()
        print(f"   停止结果: {'成功' if opt_ok else '部分失败'}")
        print(f"   已停止: {opt_stopped}, 失败: {opt_failed}")
        
        print("\n✅ 演示完成!")
        return True
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def demonstrate_advanced_features():
    """演示高级功能"""
    print("\n" + "=" * 50)
    print("InternalModuleInit 高级功能演示")
    print("=" * 50)
    
    try:
        manager = InternalModuleManager()
        
        # 仅启动基础模块
        print("1. 仅启动基础模块...")
        base_ok, base_success, base_fail = manager._init_base_modules()
        print(f"   基础模块启动: {'成功' if base_ok else '失败'}")
        print(f"   成功: {base_success}, 失败: {base_fail}")
        
        if base_success:
            # 检查单个模块健康状态
            print("\n2. 检查单个模块健康状态...")
            for module in base_success:
                is_healthy, message = manager.check_module_health(module)
                print(f"   {module}: {'健康' if is_healthy else '不健康'} - {message}")
            
            # 获取模块实例
            print("\n3. 获取模块实例...")
            for module in base_success:
                instance = manager.get_module_instance(module)
                if instance:
                    print(f"   {module}: {type(instance).__name__} 实例")
                else:
                    print(f"   {module}: 无法获取实例")
            
            # 重启模块
            if base_success:
                print(f"\n4. 重启模块 {base_success[0]}...")
                restart_success = manager._restart_single_module_aux(base_success[0], isBaseModule=True)
                print(f"   重启结果: {'成功' if restart_success else '失败'}")
        
        print("\n✅ 高级功能演示完成!")
        return True
        
    except Exception as e:
        print(f"\n❌ 高级功能演示过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("InternalModuleInit v2.0 演示程序")
    
    # 检查环境
    pythonpath = os.environ.get('PYTHONPATH', '')
    if '${AGENT_HOME}' not in pythonpath:
        print("⚠️  警告: PYTHONPATH 中可能缺少 ${AGENT_HOME}")
        print("   建议运行: export PYTHONPATH=${AGENT_HOME}:$PYTHONPATH")
    
    try:
        # 基本用法演示
        success1 = demonstrate_basic_usage()
        
        # 高级功能演示
        success2 = demonstrate_advanced_features()
        
        if success1 and success2:
            print("\n🎉 所有演示都成功完成!")
            return True
        else:
            print("\n⚠️  部分演示失败，请检查日志")
            return False
            
    except KeyboardInterrupt:
        print("\n\n用户中断演示")
        return False
    except Exception as e:
        print(f"\n❌ 演示程序出现错误: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
