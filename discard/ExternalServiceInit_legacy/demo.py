#!/usr/bin/env python3
"""
重构版外部服务管理器演示脚本
"""

import sys
import os
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, '${AGENT_HOME}')

from . import ExternalServiceManager
from .exceptions import ServiceStartupError, ServiceConfigError


def main():
    """主函数演示"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("外部服务管理器 - 重构版演示")
    print("使用独立的配置文件: ExternalServiceInit/config.yml")
    print("=" * 60)
    
    try:
        # 创建服务管理器
        print("\n1. 初始化服务管理器...")
        manager = ExternalServiceManager()
        print("✓ 服务管理器初始化成功")
        
        # 启动服务
        print("\n2. 启动外部服务...")
        base_services, optional_services = manager.init_services()
        
        print(f"✓ 基础服务启动完成: {len(base_services)} 个")
        for name, pid in base_services:
            print(f"  - {name} (PID: {pid})")
            
        print(f"✓ 可选服务启动完成: {len(optional_services)} 个")
        for name, pid in optional_services:
            print(f"  - {name} (PID: {pid})")
        
        # 显示服务状态
        print("\n3. 服务状态:")
        status = manager.get_service_status()
        
        print("基础服务:")
        for service in status["base_services"]:
            print(f"  - {service['name']}: {service['status']} (PID: {service['pid']})")
        
        print("可选服务:")
        for service in status["optional_services"]:
            print(f"  - {service['name']}: {service['status']} (PID: {service['pid']})")
        
        # 等待用户输入
        input("\n按Enter键继续或Ctrl+C退出...")
        
    except ServiceConfigError as e:
        print(f"✗ 配置错误: {e}")
        return 1
    except ServiceStartupError as e:
        print(f"✗ 服务启动错误: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\n检测到用户中断...")
    except Exception as e:
        print(f"✗ 未知错误: {e}")
        return 1
    finally:
        # 清理资源
        try:
            print("\n4. 停止所有服务...")
            if 'manager' in locals():
                manager.stop_all_services()
                print("✓ 所有服务已停止")
        except Exception as e:
            print(f"✗ 停止服务时出错: {e}")
    
    print("\n演示完成!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
