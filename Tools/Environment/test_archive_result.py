#!/usr/bin/env python3
"""
归档后环境验证脚本
验证所有归档的工具和文档是否正常工作
"""

import os
import sys
import subprocess
from pathlib import Path

def get_project_root():
    """获取项目根目录"""
    return os.path.dirname(os.path.abspath(__file__))

def test_environment_tools():
    """测试环境工具"""
    print("🔧 测试环境工具...")
    
    project_root = get_project_root()
    tools_dir = os.path.join(project_root, "Tools", "Environment")
    
    # 测试的脚本
    scripts_to_test = [
        "quick_verify.py",
        "test_final.py"
    ]
    
    all_passed = True
    
    for script in scripts_to_test:
        script_path = os.path.join(tools_dir, script)
        if os.path.exists(script_path):
            try:
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=project_root
                )
                
                if result.returncode == 0:
                    print(f"✅ {script} - 运行成功")
                else:
                    print(f"❌ {script} - 运行失败")
                    print(f"   错误: {result.stderr}")
                    all_passed = False
                    
            except Exception as e:
                print(f"❌ {script} - 执行异常: {e}")
                all_passed = False
        else:
            print(f"❌ {script} - 文件不存在")
            all_passed = False
    
    return all_passed

def test_directory_structure():
    """测试目录结构"""
    print("\n📁 测试目录结构...")
    
    project_root = get_project_root()
    
    # 检查归档目录
    required_dirs = [
        "Tools/Environment",
        "Tools/Development", 
        "Docs/Reference",
        "Docs/study"
    ]
    
    all_passed = True
    
    for dir_path in required_dirs:
        full_path = os.path.join(project_root, dir_path)
        if os.path.exists(full_path):
            file_count = len(os.listdir(full_path))
            print(f"✅ {dir_path} - 存在 ({file_count} 个文件)")
        else:
            print(f"❌ {dir_path} - 不存在")
            all_passed = False
    
    return all_passed

def test_root_cleanliness():
    """测试根目录整洁性"""
    print("\n🧹 测试根目录整洁性...")
    
    project_root = get_project_root()
    
    # 检查根目录是否还有应该归档的文件
    unwanted_patterns = [
        "test_*.py",
        "fix_*.py", 
        "patch_*.py",
        "check_*.py",
        "final_*.py"
    ]
    
    found_unwanted = []
    
    for item in os.listdir(project_root):
        if os.path.isfile(os.path.join(project_root, item)):
            for pattern in unwanted_patterns:
                if item.startswith(pattern.replace("*", "")):
                    found_unwanted.append(item)
    
    if found_unwanted:
        print("❌ 根目录发现应该归档的文件:")
        for file in found_unwanted:
            print(f"   {file}")
        return False
    else:
        print("✅ 根目录整洁，没有遗留的测试/修复脚本")
        return True

def test_documentation():
    """测试文档完整性"""
    print("\n📖 测试文档完整性...")
    
    project_root = get_project_root()
    
    # 检查重要文档
    important_docs = [
        "README.md",
        "Tools/README.md",
        "Tools/Environment/README.md",
        "Tools/Development/README.md",
        "Docs/README.md",
        "Docs/Reference/README.md"
    ]
    
    all_passed = True
    
    for doc_path in important_docs:
        full_path = os.path.join(project_root, doc_path)
        if os.path.exists(full_path):
            print(f"✅ {doc_path} - 存在")
        else:
            print(f"❌ {doc_path} - 不存在")
            all_passed = False
    
    return all_passed

def main():
    """主函数"""
    print("🌟 Agent 系统归档后验证")
    print("="*60)
    
    project_root = get_project_root()
    print(f"📁 项目根目录: {project_root}")
    
    # 执行各项测试
    tests = [
        ("环境工具测试", test_environment_tools),
        ("目录结构测试", test_directory_structure),
        ("根目录整洁性测试", test_root_cleanliness),
        ("文档完整性测试", test_documentation)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} 执行异常: {e}")
            results.append((test_name, False))
    
    # 输出总结
    print(f"\n{'='*60}")
    print("📊 归档后验证结果:")
    print(f"{'='*60}")
    
    all_passed = True
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not success:
            all_passed = False
    
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 归档验证通过！")
        print("✅ 所有工具和文档都已正确归档")
        print("✅ 根目录保持整洁")
        print("✅ 环境工具工作正常")
        return 0
    else:
        print("⚠️  归档验证部分失败，需要进一步检查")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
