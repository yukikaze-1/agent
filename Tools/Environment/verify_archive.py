#!/usr/bin/env python3
"""
验证根目录清理和归档工作是否完整
"""

import os
import glob
from pathlib import Path

def check_root_directory_cleanliness():
    """检查根目录是否已清理干净"""
    agent_home = Path("/home/yomu/agent")
    
    print("🔍 检查根目录清理状况...")
    print("=" * 60)
    
    # 应该保留的文件和目录
    expected_items = {
        # 重要文件
        "README.md", "LICENSE", "requirement.txt", 
        "agent_v0.1.py", "agent.sh", "install.sh", "verify.sh",
        "start_agent.sh", "start_agent.bat", "agent_env.yml",
        
        # 环境变量文件
        ".env", ".env.development", ".env.global", ".env.production",
        
        # Git相关
        ".git", ".gitignore",
        
        # 主要目录
        "Archive", "Client", "Config", "Core", "Data", "Docs", 
        "Functions", "Init", "Log", "Memory", "Module", "Other", 
        "Plan", "Prompt", "Resources", "Service", "Temp", "Tools", 
        "Users", "discard", "${AGENT_HOME}"
    }
    
    # 获取当前根目录的所有项目
    current_items = set()
    for item in agent_home.iterdir():
        current_items.add(item.name)
    
    # 检查是否有意外的文件
    unexpected_items = current_items - expected_items
    
    if unexpected_items:
        print("⚠️  发现可能需要进一步处理的文件:")
        for item in sorted(unexpected_items):
            item_path = agent_home / item
            if item_path.is_file():
                print(f"  📄 文件: {item}")
            else:
                print(f"  📁 目录: {item}")
    else:
        print("✅ 根目录已清理干净，没有发现意外的文件")
    
    return len(unexpected_items) == 0

def check_archive_structure():
    """检查归档目录结构"""
    archive_path = Path("/home/yomu/agent/Archive")
    
    print("\n📁 检查归档目录结构...")
    print("=" * 60)
    
    if not archive_path.exists():
        print("❌ 归档目录不存在")
        return False
    
    expected_subdirs = ["test_scripts", "utility_scripts", "docs", "temporary_files"]
    
    for subdir in expected_subdirs:
        subdir_path = archive_path / subdir
        if subdir_path.exists():
            files = list(subdir_path.iterdir())
            print(f"✅ {subdir}/ - {len(files)} 个文件")
            for file in sorted(files):
                print(f"   📄 {file.name}")
        else:
            print(f"❌ 缺少子目录: {subdir}/")
            return False
    
    readme_path = archive_path / "README.md"
    if readme_path.exists():
        print("✅ 归档说明文件存在")
    else:
        print("❌ 缺少归档说明文件")
        return False
    
    return True

def check_gitignore_updated():
    """检查.gitignore是否已更新"""
    gitignore_path = Path("/home/yomu/agent/.gitignore")
    
    print("\n📝 检查.gitignore更新...")
    print("=" * 60)
    
    if not gitignore_path.exists():
        print("❌ .gitignore文件不存在")
        return False
    
    try:
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "Archive/" in content:
            print("✅ .gitignore已包含Archive/目录")
            return True
        else:
            print("❌ .gitignore未包含Archive/目录")
            return False
            
    except Exception as e:
        print(f"❌ 读取.gitignore失败: {e}")
        return False

def main():
    print("🗂️  验证根目录清理和归档工作")
    print("=" * 60)
    
    # 执行检查
    root_clean = check_root_directory_cleanliness()
    archive_ok = check_archive_structure()
    gitignore_ok = check_gitignore_updated()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 验证结果总结:")
    
    if root_clean and archive_ok and gitignore_ok:
        print("🎉 所有检查通过！根目录清理和归档工作完成")
        print("\n✨ 项目根目录现在更加整洁，所有临时文件和测试脚本都已妥善归档")
        return True
    else:
        print("⚠️  还有一些项目需要处理:")
        if not root_clean:
            print("   - 根目录可能还有文件需要处理")
        if not archive_ok:
            print("   - 归档目录结构不完整")
        if not gitignore_ok:
            print("   - .gitignore需要更新")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
