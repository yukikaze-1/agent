#!/usr/bin/env python3
"""
配置文件动态路径处理工具
在配置加载时动态替换路径变量
"""

import os
import re
import yaml
from pathlib import Path

def get_agent_root():
    """获取 Agent 项目根目录"""
    # 从当前文件位置向上查找项目根目录
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    
    # 查找包含 agent_v0.1.py 的目录作为项目根目录
    while current_dir != "/":
        if os.path.exists(os.path.join(current_dir, "agent_v0.1.py")):
            return current_dir
        current_dir = os.path.dirname(current_dir)
    
    # 如果没找到，使用当前目录的上级
    return os.path.dirname(current_dir) if current_dir != "/" else os.getcwd()

def expand_config_paths(config_data, agent_root=None):
    """
    展开配置文件中的路径变量
    
    Args:
        config_data: 配置数据（字典、列表或字符串）
        agent_root: 项目根目录路径
    
    Returns:
        处理后的配置数据
    """
    if agent_root is None:
        agent_root = get_agent_root()
    
    if isinstance(config_data, dict):
        return {key: expand_config_paths(value, agent_root) for key, value in config_data.items()}
    elif isinstance(config_data, list):
        return [expand_config_paths(item, agent_root) for item in config_data]
    elif isinstance(config_data, str):
        # 替换路径变量
        expanded = config_data
        
        # 替换 ${AGENT_HOME} 变量
        expanded = expanded.replace("${AGENT_HOME}", agent_root)
        
        # 替换硬编码的 ${AGENT_HOME} 路径
        expanded = expanded.replace("${AGENT_HOME}", agent_root)
        
        # 处理相对路径
        if expanded.startswith("./"):
            expanded = os.path.join(agent_root, expanded[2:])
        
        return expanded
    else:
        return config_data

def load_config_with_path_expansion(config_file_path):
    """
    加载配置文件并展开路径变量
    
    Args:
        config_file_path: 配置文件路径
        
    Returns:
        处理后的配置数据
    """
    agent_root = get_agent_root()
    
    # 如果配置文件路径是相对路径，转换为绝对路径
    if not os.path.isabs(config_file_path):
        config_file_path = os.path.join(agent_root, config_file_path)
    
    # 读取配置文件
    with open(config_file_path, 'r', encoding='utf-8') as f:
        if config_file_path.endswith('.yml') or config_file_path.endswith('.yaml'):
            config_data = yaml.safe_load(f)
        else:
            # 对于其他格式，按行读取并处理
            lines = f.readlines()
            config_data = [line.strip() for line in lines if line.strip()]
    
    # 展开路径变量
    expanded_config = expand_config_paths(config_data, agent_root)
    
    return expanded_config

def patch_external_service_config():
    """修补 ExternalServiceInit 配置加载"""
    agent_root = get_agent_root()
    config_path = os.path.join(agent_root, "Init/ExternalServiceInit/config.yml")
    
    if not os.path.exists(config_path):
        print(f"⚠️  配置文件不存在: {config_path}")
        return False
    
    try:
        # 加载并处理配置
        expanded_config = load_config_with_path_expansion(config_path)
        
        # 写回配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(expanded_config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ 已修补 ExternalServiceInit 配置文件")
        return True
        
    except Exception as e:
        print(f"❌ 修补配置文件失败: {e}")
        return False

if __name__ == "__main__":
    print("🔧 开始修补配置文件路径...")
    
    success = patch_external_service_config()
    
    if success:
        print("✅ 配置文件路径修补完成")
    else:
        print("❌ 配置文件路径修补失败")
