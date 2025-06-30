#!/usr/bin/env python3
"""
清理脚本 - 识别和清理测试文件
"""

import os
import shutil
from pathlib import Path

def get_test_files():
    """识别测试文件"""
    base_dir = Path("/home/yomu/agent")
    
    # 明确的测试文件模式
    test_patterns = [
        "test_*.py",
        "*_test.py", 
        "debug_*.py",
        "verify_*.py",
        "quick_*.py",
        "final_*.py"
    ]
    
    # 特定的测试和验证文件
    specific_test_files = [
        "consul_cleanup.py",
        "debug_external_manager.py",
        "safe_init_test.py",
        "simple_init_test.py",
        "rmlog.py"
    ]
    
    test_files = []
    
    # 查找匹配模式的文件
    for pattern in test_patterns:
        test_files.extend(base_dir.glob(pattern))
    
    # 添加特定测试文件
    for filename in specific_test_files:
        file_path = base_dir / filename
        if file_path.exists():
            test_files.append(file_path)
    
    return test_files

def get_report_files():
    """识别报告文件"""
    base_dir = Path("/home/yomu/agent")
    
    report_files = [
        "IMPORT_COMPATIBILITY_REPORT.md",
        "INTEGRATION_REPORT.md", 
        "MODULE_CLEANUP_SOLUTION.md",
        "TASK_COMPLETION_SUMMARY.md",
        "USAGE_GUIDE.md"
    ]
    
    existing_reports = []
    for filename in report_files:
        file_path = base_dir / filename
        if file_path.exists():
            existing_reports.append(file_path)
    
    return existing_reports

def show_files_to_clean():
    """显示将要清理的文件"""
    print("🔍 识别测试和临时文件")
    print("=" * 60)
    
    test_files = get_test_files()
    report_files = get_report_files()
    
    print(f"\n📝 测试文件 ({len(test_files)} 个):")
    for file_path in sorted(test_files):
        print(f"   - {file_path.name}")
    
    print(f"\n📄 报告文件 ({len(report_files)} 个):")
    for file_path in sorted(report_files):
        print(f"   - {file_path.name}")
    
    return test_files, report_files

if __name__ == "__main__":
    test_files, report_files = show_files_to_clean()
    
    total_files = len(test_files) + len(report_files)
    print(f"\n📊 总计: {total_files} 个文件需要清理")
    
    print("\n⚠️  注意: 这个脚本只是识别文件，不会删除任何内容")
    print("   如需删除，请手动确认后执行删除操作")
