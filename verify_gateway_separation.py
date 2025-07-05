#!/usr/bin/env python3
"""
验证APIGateway和MicroServiceGateway分离后的配置
"""

import os
import yaml

def check_config_file(config_path, expected_sections):
    """检查配置文件是否包含预期的部分"""
    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print(f"✅ 配置文件存在: {config_path}")
        
        # 检查预期的配置部分
        for section in expected_sections:
            if section in config:
                print(f"  ✅ 包含 {section} 配置")
            else:
                print(f"  ❌ 缺少 {section} 配置")
                return False
        
        # 检查不应该存在的配置部分
        all_sections = ["APIGateway", "MicroServiceGateway"]
        unexpected_sections = [s for s in all_sections if s not in expected_sections and s in config]
        
        if unexpected_sections:
            print(f"  ⚠️  包含不应该存在的配置: {unexpected_sections}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 读取配置文件失败: {config_path}, 错误: {e}")
        return False

def check_env_file(env_path):
    """检查环境变量文件"""
    if not os.path.exists(env_path):
        print(f"❌ 环境变量文件不存在: {env_path}")
        return False
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"✅ 环境变量文件存在: {env_path}")
        
        # 检查路径是否正确
        if "Service/Gateway/" in content:
            print(f"  ❌ 仍然包含旧的Gateway路径")
            return False
        
        if "Service/APIGateway/" in content and "Service/MicroServiceGateway/" in content:
            print(f"  ✅ 包含正确的分离路径")
            return True
        else:
            print(f"  ❌ 缺少正确的路径配置")
            return False
            
    except Exception as e:
        print(f"❌ 读取环境变量文件失败: {env_path}, 错误: {e}")
        return False

def main():
    agent_home = os.environ.get('AGENT_HOME', '/home/yomu/agent')
    
    print("🔍 验证APIGateway和MicroServiceGateway分离...")
    print("=" * 60)
    
    # 检查APIGateway配置
    print("\n📋 检查APIGateway配置:")
    api_config_path = os.path.join(agent_home, "Service", "APIGateway", "config.yml")
    api_config_ok = check_config_file(api_config_path, ["APIGateway"])
    
    api_env_path = os.path.join(agent_home, "Service", "APIGateway", ".env")
    api_env_ok = check_env_file(api_env_path)
    
    # 检查MicroServiceGateway配置
    print("\n📋 检查MicroServiceGateway配置:")
    micro_config_path = os.path.join(agent_home, "Service", "MicroServiceGateway", "config.yml")
    micro_config_ok = check_config_file(micro_config_path, ["MicroServiceGateway"])
    
    micro_env_path = os.path.join(agent_home, "Service", "MicroServiceGateway", ".env")
    micro_env_ok = check_env_file(micro_env_path)
    
    # 检查ExternalServiceInit配置
    print("\n📋 检查ExternalServiceInit配置:")
    init_config_path = os.path.join(agent_home, "Init", "ExternalServiceInit", "config.yml")
    if os.path.exists(init_config_path):
        try:
            with open(init_config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if "Service/Gateway/" in content:
                print("  ❌ 仍然包含旧的Gateway路径")
                init_config_ok = False
            else:
                print("  ✅ 路径配置已更新")
                init_config_ok = True
        except Exception as e:
            print(f"  ❌ 读取配置失败: {e}")
            init_config_ok = False
    else:
        print("  ❌ ExternalServiceInit配置文件不存在")
        init_config_ok = False
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 验证结果:")
    
    all_ok = all([api_config_ok, api_env_ok, micro_config_ok, micro_env_ok, init_config_ok])
    
    if all_ok:
        print("✅ 所有配置都已正确分离！")
        return True
    else:
        print("❌ 还有配置需要修复")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
