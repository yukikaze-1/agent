#!/usr/bin/env python3
"""
配置文件验证脚本
"""

import sys
import os
import yaml
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, '/home/yomu/agent')

from .utils.config_validator import ServiceConfigValidator


def validate_config_file(config_path: str) -> bool:
    """验证配置文件"""
    try:
        print(f"正在验证配置文件: {config_path}")
        
        # 读取配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print("✓ 配置文件格式正确")
        
        # 获取外部服务配置
        external_services = config.get('external_services', {})
        base_services = external_services.get('base_services', [])
        optional_services = external_services.get('optional_services', [])
        
        # 处理None值
        if base_services is None:
            base_services = []
        if optional_services is None:
            optional_services = []
            
        print(f"✓ 找到 {len(base_services)} 个基础服务")
        print(f"✓ 找到 {len(optional_services)} 个可选服务")
        
        # 创建验证器
        validator = ServiceConfigValidator()
        
        # 验证基础服务
        if base_services:
            print("\n验证基础服务配置:")
            for service_item in base_services:
                if isinstance(service_item, dict) and len(service_item) == 1:
                    service_name = list(service_item.keys())[0]
                    service_config = list(service_item.values())[0]
                    
                    # 标准化配置
                    normalized_config = validator.normalize_service_config(service_config)
                    
                    try:
                        validator.validate_service_config(normalized_config)
                        print(f"  ✓ {service_name}")
                    except Exception as e:
                        print(f"  ✗ {service_name}: {e}")
                        return False
        
        # 验证可选服务
        if optional_services:
            print("\n验证可选服务配置:")
            for service_item in optional_services:
                if isinstance(service_item, dict) and len(service_item) == 1:
                    service_name = list(service_item.keys())[0]
                    service_config = list(service_item.values())[0]
                    
                    # 标准化配置
                    normalized_config = validator.normalize_service_config(service_config)
                    
                    try:
                        validator.validate_service_config(normalized_config)
                        print(f"  ✓ {service_name}")
                    except Exception as e:
                        print(f"  ✗ {service_name}: {e}")
                        return False
        
        # 检查其他重要配置
        print("\n验证其他配置:")
        
        # 检查重试配置
        retry_config = config.get('retry_config', {})
        if retry_config:
            required_retry_fields = ['max_retries', 'base_delay', 'max_delay', 'backoff_factor']
            for field in required_retry_fields:
                if field in retry_config:
                    print(f"  ✓ retry_config.{field}: {retry_config[field]}")
                else:
                    print(f"  ! retry_config.{field}: 使用默认值")
        
        # 检查健康检查配置
        health_check = config.get('health_check', {})
        if health_check:
            print(f"  ✓ health_check.default_timeout: {health_check.get('default_timeout', 30)}")
            print(f"  ✓ health_check.check_interval: {health_check.get('check_interval', 2)}")
        
        # 检查IP端口配置
        ip_port = external_services.get('ip_port', [])
        if ip_port:
            print(f"\n✓ 找到 {len(ip_port)} 个服务的IP端口配置")
            for port_config in ip_port:
                if isinstance(port_config, dict):
                    for service_name, port_info in port_config.items():
                        print(f"  ✓ {service_name}: {port_info[0]}:{port_info[1]}")
        
        print("\n🎉 配置文件验证通过！")
        return True
        
    except FileNotFoundError:
        print(f"✗ 配置文件不存在: {config_path}")
        return False
    except yaml.YAMLError as e:
        print(f"✗ YAML格式错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 验证失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("ExternalServiceInit 配置文件验证工具")
    print("=" * 60)
    
    # 验证新配置文件
    new_config = "/home/yomu/agent/ExternalServiceInit/config.yml"
    old_config = "/home/yomu/agent/Init/config.yml"
    
    success = True
    
    print("\n1. 验证新的独立配置文件:")
    if os.path.exists(new_config):
        success &= validate_config_file(new_config)
    else:
        print(f"✗ 配置文件不存在: {new_config}")
        success = False
    
    print("\n2. 检查原配置文件清理情况:")
    if os.path.exists(old_config):
        try:
            with open(old_config, 'r', encoding='utf-8') as f:
                old_content = f.read()
            
            if 'external_services:' in old_content and 'base_services:' in old_content:
                if '已迁移到 ExternalServiceInit' in old_content:
                    print("✓ 原配置文件已正确清理并添加迁移说明")
                else:
                    print("! 原配置文件中仍有外部服务配置，建议清理")
            else:
                print("✓ 原配置文件中的外部服务配置已清理")
                
        except Exception as e:
            print(f"✗ 检查原配置文件失败: {e}")
    
    print("\n3. 检查环境文件:")
    env_file = "/home/yomu/agent/ExternalServiceInit/.env"
    if os.path.exists(env_file):
        print(f"✓ 环境文件存在: {env_file}")
        try:
            with open(env_file, 'r') as f:
                env_content = f.read()
            if 'LOG_PATH' in env_content:
                print("✓ LOG_PATH 配置存在")
            else:
                print("! LOG_PATH 配置缺失")
        except Exception as e:
            print(f"✗ 读取环境文件失败: {e}")
    else:
        print(f"! 环境文件不存在: {env_file}")
    
    if success:
        print("\n🎉 所有验证通过！配置文件迁移成功！")
        return 0
    else:
        print("\n❌ 验证失败，请检查配置文件！")
        return 1


if __name__ == "__main__":
    sys.exit(main())
