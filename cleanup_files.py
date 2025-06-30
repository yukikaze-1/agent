#!/usr/bin/env python3
"""
文件清理脚本 - 将测试文件移动到存档目录
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def cleanup_files():
    """清理测试文件和报告文件"""
    base_dir = Path("/home/yomu/agent")
    
    # 创建存档目录
    archive_dir = base_dir / "archived_files"
    test_archive = archive_dir / "test_files"
    report_archive = archive_dir / "reports"
    
    test_archive.mkdir(parents=True, exist_ok=True)
    report_archive.mkdir(parents=True, exist_ok=True)
    
    print("🧹 开始清理测试和临时文件")
    print("=" * 50)
    
    # 定义要清理的测试文件
    test_files_to_clean = [
        "consul_cleanup.py",
        "debug_external_manager.py", 
        "debug_init.py",
        "debug_system_init.py",
        "final_integration_test.py",
        "final_verify.py",
        "quick_service_check.py",
        "rmlog.py",
        "safe_init_test.py",
        "simple_init_test.py",
        "test_config.py",
        "test_env_manager.py",
        "test_environment.py",
        "test_full_init.py",
        "test_import_compatibility.py",
        "test_imports.py",
        "test_init_env_integration.py",
        "test_integration.py",
        "test_internal_module.py",
        "test_modified_init.py",
        "test_module_cleanup.py",
        "verify_integration.py"
    ]
    
    # 定义要清理的报告文件
    report_files_to_clean = [
        "IMPORT_COMPATIBILITY_REPORT.md",
        "INTEGRATION_REPORT.md",
        "MODULE_CLEANUP_SOLUTION.md", 
        "TASK_COMPLETION_SUMMARY.md",
        "USAGE_GUIDE.md"
    ]
    
    # 移动测试文件
    print("📝 移动测试文件...")
    moved_tests = 0
    for filename in test_files_to_clean:
        source = base_dir / filename
        if source.exists():
            destination = test_archive / filename
            try:
                shutil.move(str(source), str(destination))
                print(f"   ✅ {filename}")
                moved_tests += 1
            except Exception as e:
                print(f"   ❌ {filename}: {e}")
    
    # 移动报告文件  
    print(f"\n📄 移动报告文件...")
    moved_reports = 0
    for filename in report_files_to_clean:
        source = base_dir / filename
        if source.exists():
            destination = report_archive / filename
            try:
                shutil.move(str(source), str(destination))
                print(f"   ✅ {filename}")
                moved_reports += 1
            except Exception as e:
                print(f"   ❌ {filename}: {e}")
    
    # 移动当前的清理脚本
    cleanup_script = base_dir / "identify_cleanup_files.py"
    if cleanup_script.exists():
        shutil.move(str(cleanup_script), str(test_archive / "identify_cleanup_files.py"))
        moved_tests += 1
    
    print(f"\n📊 清理总结:")
    print(f"   📝 测试文件: {moved_tests} 个已移动")
    print(f"   📄 报告文件: {moved_reports} 个已移动")
    print(f"   📁 存档位置: {archive_dir}")
    
    # 创建清理记录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cleanup_log = archive_dir / f"cleanup_log_{timestamp}.txt"
    
    with open(cleanup_log, 'w', encoding='utf-8') as f:
        f.write(f"文件清理记录 - {datetime.now()}\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"测试文件 ({moved_tests} 个):\n")
        for filename in test_files_to_clean:
            if (test_archive / filename).exists():
                f.write(f"  - {filename}\n")
        f.write(f"\n报告文件 ({moved_reports} 个):\n")
        for filename in report_files_to_clean:
            if (report_archive / filename).exists():
                f.write(f"  - {filename}\n")
    
    print(f"   📋 清理日志: {cleanup_log.name}")
    print(f"\n🎉 清理完成! 文件已移动到存档目录，可以安全删除")
    
    return moved_tests + moved_reports

if __name__ == "__main__":
    total_moved = cleanup_files()
    print(f"\n总共处理了 {total_moved} 个文件")
