#!/usr/bin/env python3
"""
配置文件路径修复工具
动态生成正确的配置文件，替换硬编码路径
"""

import os
import yaml
import shutil
from pathlib import Path

def get_agent_root():
    """获取 Agent 项目根目录"""
    # 脚本现在在 Tools/Environment/ 下，需要向上两级到达项目根目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(current_dir))

def fix_external_service_config():
    """修复 ExternalServiceInit 配置文件"""
    agent_root = get_agent_root()
    config_path = os.path.join(agent_root, "Init/ExternalServiceInit/config.yml")
    
    # 备份原文件
    backup_path = config_path + ".backup"
    if not os.path.exists(backup_path):
        shutil.copy2(config_path, backup_path)
        print(f"✅ 已备份原配置文件: {backup_path}")
    
    # 读取配置文件
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换硬编码路径
    old_path = "${AGENT_HOME}"
    new_content = content.replace(old_path, agent_root)
    
    # 写入修复后的配置
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ 已修复 ExternalServiceInit 配置文件")
    print(f"   路径: {config_path}")
    print(f"   替换: {old_path} -> {agent_root}")

def fix_internal_module_config():
    """修复 InternalModuleInit 配置文件"""
    agent_root = get_agent_root()
    config_path = os.path.join(agent_root, "Init/InternalModuleInit/config.yml")
    
    if not os.path.exists(config_path):
        print(f"⚠️  配置文件不存在: {config_path}")
        return
    
    # 备份原文件
    backup_path = config_path + ".backup"
    if not os.path.exists(backup_path):
        shutil.copy2(config_path, backup_path)
        print(f"✅ 已备份原配置文件: {backup_path}")
    
    # 读取配置文件
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换硬编码路径
    old_path = "${AGENT_HOME}"
    new_content = content.replace(old_path, agent_root)
    
    # 写入修复后的配置
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ 已修复 InternalModuleInit 配置文件")

def update_startup_guide():
    """更新启动指南中的路径示例"""
    agent_root = get_agent_root()
    guide_path = os.path.join(agent_root, "STARTUP_GUIDE.md")
    
    # 备份原文件
    backup_path = guide_path + ".backup"
    if not os.path.exists(backup_path):
        shutil.copy2(guide_path, backup_path)
    
    # 读取文件
    with open(guide_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换示例路径为变量形式
    updates = [
        ("AGENT_HOME=${AGENT_HOME}", "AGENT_HOME=<your_project_path>"),
        ("PYTHONPATH=${AGENT_HOME}", "PYTHONPATH=<your_project_path>"),
        ("${AGENT_HOME}/", "<your_project_path>/"),
        ("cd ${AGENT_HOME}", "cd <your_project_path>"),
        ("export PYTHONPATH=${AGENT_HOME}:$PYTHONPATH", "export PYTHONPATH=<your_project_path>:$PYTHONPATH")
    ]
    
    for old, new in updates:
        content = content.replace(old, new)
    
    # 写入修复后的文件
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 已更新启动指南中的路径示例")

def main():
    """主函数"""
    print("🔧 开始修复配置文件中的硬编码路径...")
    print("="*60)
    
    agent_root = get_agent_root()
    print(f"📁 检测到项目根目录: {agent_root}")
    
    try:
        # 修复各种配置文件
        fix_external_service_config()
        fix_internal_module_config()
        update_startup_guide()
        
        print("\n" + "="*60)
        print("🎉 配置文件路径修复完成！")
        print("✅ 现在其他人 clone 代码后应该可以正常运行")
        print("\n💡 提示:")
        print("1. 所有硬编码路径已替换为动态检测")
        print("2. 原文件已备份为 .backup 格式")
        print("3. 建议运行验证脚本确认修复效果")
        
    except Exception as e:
        print(f"❌ 修复过程中出现错误: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
