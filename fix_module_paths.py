#!/usr/bin/env python3
"""
批量修复 Module 和 Service 中的环境变量路径问题
"""

import os
import re
import sys

def get_project_root():
    """获取项目根目录"""
    return os.path.dirname(os.path.abspath(__file__))

def fix_dotenv_values_paths(file_path):
    """修复文件中的 dotenv_values 路径问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找 dotenv_values("${AGENT_HOME}/...") 模式
        pattern = r'dotenv_values\("(\$\{AGENT_HOME\}/[^"]+)"\)'
        matches = re.findall(pattern, content)
        
        if not matches:
            return False
        
        print(f"修复文件: {file_path}")
        for match in matches:
            print(f"  发现路径: {match}")
        
        # 确保导入了 os 模块
        if 'import os' not in content and 'from os' not in content:
            # 在第一个 import 之前添加 os 导入
            import_pattern = r'(import\s+\w+|from\s+\w+\s+import)'
            first_import_match = re.search(import_pattern, content)
            if first_import_match:
                insert_pos = first_import_match.start()
                content = content[:insert_pos] + 'import os\n' + content[insert_pos:]
            else:
                # 如果没有找到其他导入，在文件开头添加
                content = 'import os\n' + content
        
        # 替换 dotenv_values 调用
        def replace_dotenv_call(match):
            old_path = match.group(1)
            # 提取相对路径部分
            relative_path = old_path.replace('${AGENT_HOME}/', '')
            
            replacement = f'''dotenv_values(os.path.join(
            os.environ.get('AGENT_HOME', os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "{relative_path}"
        ))'''
            return replacement
        
        new_content = re.sub(pattern, replace_dotenv_call, content)
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"  ✅ 修复完成")
        return True
        
    except Exception as e:
        print(f"  ❌ 修复失败: {e}")
        return False

def main():
    """主函数"""
    project_root = get_project_root()
    
    # 要检查的关键服务文件
    service_files = [
        "Module/LLM/OllamaAgent.py",
        "Module/Chat/ChatModule.py", 
        "Module/Input/UserTextInputProcessModule.py",
        "Module/Input/PromptOptimizer.py",
        "Module/STT/SenseVoice/SenseVoiceAgent.py",
        "Module/TTS/GPTSoVits/GPTSoVitsAgent.py",
        "Service/UserService/app/db/BaseDBAgent.py"
    ]
    
    print("🔧 开始批量修复环境变量路径问题...")
    
    fixed_count = 0
    for service_file in service_files:
        file_path = os.path.join(project_root, service_file)
        if os.path.exists(file_path):
            if fix_dotenv_values_paths(file_path):
                fixed_count += 1
        else:
            print(f"⚠️  文件不存在: {service_file}")
    
    print(f"\n📊 修复总结:")
    print(f"  检查文件: {len(service_files)} 个")
    print(f"  修复文件: {fixed_count} 个")
    
    if fixed_count > 0:
        print("\n✅ 批量修复完成！")
        return 0
    else:
        print("\n✅ 没有发现需要修复的文件")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
