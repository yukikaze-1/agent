#!/usr/bin/env python3
"""
最终硬编码路径清理脚本
确保所有硬编码路径都被移除，保证跨平台兼容性
"""

import os
import re
import glob
from pathlib import Path

def get_project_root():
    """获取项目根目录"""
    return os.path.dirname(os.path.abspath(__file__))

def fix_hardcoded_paths_in_file(file_path, project_root):
    """修复单个文件中的硬编码路径"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 替换硬编码路径
        replacements = [
            ('${AGENT_HOME}', '${AGENT_HOME}'),
            ('"${AGENT_HOME}', '"${AGENT_HOME}'),
            ("'${AGENT_HOME}", "'${AGENT_HOME}"),
        ]
        
        for old, new in replacements:
            content = content.replace(old, new)
        
        # 特殊处理 Python 代码中的路径
        if file_path.endswith('.py'):
            # 替换 Python 代码中的硬编码路径
            content = re.sub(
                r'(["\'])${AGENT_HOME}(["\'])',
                lambda m: f'{m.group(1)}{{os.environ.get("AGENT_HOME", "{project_root}"))){m.group(2)}',
                content
            )
            
            # 替换 dotenv_values 中的路径
            content = re.sub(
                r'dotenv_values\(["\']\/home\/yomu\/agent\/([^"\']+)["\']\)',
                r'dotenv_values(os.path.join(os.environ.get("AGENT_HOME", os.getcwd()), r"\1"))',
                content
            )
        
        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复: {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ 修复失败 {file_path}: {e}")
        return False

def main():
    """主函数"""
    print("🧹 最终硬编码路径清理...")
    print("="*60)
    
    project_root = get_project_root()
    print(f"📁 项目根目录: {project_root}")
    
    # 查找需要修复的文件
    patterns = [
        "**/*.py",
        "**/*.yml", 
        "**/*.yaml",
        "**/.env*",
        "**/*.env"
    ]
    
    files_to_fix = set()
    for pattern in patterns:
        files_to_fix.update(glob.glob(pattern, recursive=True))
    
    # 排除一些不需要修复的文件
    exclude_patterns = [
        "*.git*",
        "*__pycache__*",
        "*.backup*",
        "*node_modules*",
        "*.pyc"
    ]
    
    filtered_files = []
    for file_path in files_to_fix:
        if not any(pattern in file_path for pattern in exclude_patterns):
            filtered_files.append(file_path)
    
    print(f"🔍 找到 {len(filtered_files)} 个文件需要检查")
    
    # 修复文件
    fixed_count = 0
    for file_path in filtered_files:
        if os.path.isfile(file_path):
            if fix_hardcoded_paths_in_file(file_path, project_root):
                fixed_count += 1
    
    print(f"\n📊 修复统计:")
    print(f"  检查文件: {len(filtered_files)}")
    print(f"  修复文件: {fixed_count}")
    
    # 最终验证
    print(f"\n🔍 最终验证...")
    remaining_issues = []
    
    for file_path in filtered_files:
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if '${AGENT_HOME}' in content:
                    # 排除注释和文档中的引用
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if '${AGENT_HOME}' in line:
                            # 检查是否是注释或文档
                            stripped = line.strip()
                            if not (stripped.startswith('#') or 
                                   stripped.startswith('//') or
                                   stripped.startswith('*') or
                                   'print(' in line or
                                   'example' in line.lower() or
                                   'demo' in line.lower()):
                                remaining_issues.append(f"{file_path}:{i}: {line.strip()}")
            except:
                pass
    
    if remaining_issues:
        print("⚠️  仍有硬编码路径需要手动处理:")
        for issue in remaining_issues[:10]:  # 只显示前10个
            print(f"  {issue}")
        if len(remaining_issues) > 10:
            print(f"  ... 还有 {len(remaining_issues) - 10} 个问题")
    else:
        print("✅ 没有发现硬编码路径问题")
    
    print(f"\n{'='*60}")
    if fixed_count > 0:
        print(f"🎉 清理完成！修复了 {fixed_count} 个文件")
    else:
        print("✅ 没有发现需要修复的硬编码路径")
    
    print("💡 提示: 现在其他人 clone 代码后应该可以直接运行")
    
    return 0 if not remaining_issues else 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
