#!/usr/bin/env python3
"""
清理 Init/ 目录下的 .md 文件
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def cleanup_init_docs():
    """清理 Init 目录下的 .md 文件"""
    base_dir = Path("/home/yomu/agent")
    init_dir = base_dir / "Init"
    
    # 创建存档目录
    archive_dir = base_dir / "archived_files"
    docs_archive = archive_dir / "init_docs"
    docs_archive.mkdir(parents=True, exist_ok=True)
    
    print("🧹 清理 Init/ 目录下的 .md 文件")
    print("=" * 50)
    
    # 查找所有 .md 文件
    md_files = list(init_dir.rglob("*.md"))
    
    if not md_files:
        print("✅ Init/ 目录下没有找到 .md 文件")
        return 0
    
    print(f"📝 发现 {len(md_files)} 个 .md 文件:")
    
    moved_count = 0
    for md_file in sorted(md_files):
        # 计算相对路径以保持目录结构
        rel_path = md_file.relative_to(init_dir)
        destination = docs_archive / rel_path
        
        # 创建目标目录
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # 移动文件
            shutil.move(str(md_file), str(destination))
            print(f"   ✅ {rel_path}")
            moved_count += 1
        except Exception as e:
            print(f"   ❌ {rel_path}: {e}")
    
    # 创建清理记录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cleanup_log = docs_archive / f"init_docs_cleanup_log_{timestamp}.txt"
    
    with open(cleanup_log, 'w', encoding='utf-8') as f:
        f.write(f"Init 目录 .md 文件清理记录 - {datetime.now()}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"清理的文件 ({moved_count} 个):\n")
        for md_file in sorted(md_files):
            rel_path = md_file.relative_to(init_dir)
            if (docs_archive / rel_path).exists():
                f.write(f"  - {rel_path}\n")
    
    print(f"\n📊 清理总结:")
    print(f"   📝 .md 文件: {moved_count} 个已移动")
    print(f"   📁 存档位置: {docs_archive}")
    print(f"   📋 清理日志: {cleanup_log.name}")
    
    return moved_count

def show_remaining_structure():
    """显示清理后的 Init 目录结构"""
    init_dir = Path("/home/yomu/agent/Init")
    
    print(f"\n📁 清理后的 Init/ 目录结构:")
    print("-" * 40)
    
    def show_tree(path, prefix="", is_last=True):
        """递归显示目录树"""
        if path.is_file():
            print(f"{prefix}{'└── ' if is_last else '├── '}{path.name}")
        elif path.is_dir():
            print(f"{prefix}{'└── ' if is_last else '├── '}{path.name}/")
            children = list(path.iterdir())
            children.sort(key=lambda x: (x.is_file(), x.name))
            
            for i, child in enumerate(children):
                is_last_child = i == len(children) - 1
                new_prefix = prefix + ("    " if is_last else "│   ")
                show_tree(child, new_prefix, is_last_child)
    
    show_tree(init_dir)

if __name__ == "__main__":
    moved_count = cleanup_init_docs()
    show_remaining_structure()
    
    print(f"\n🎉 Init/ 目录 .md 文件清理完成!")
    print(f"   总共处理: {moved_count} 个文件")
    print(f"   状态: ✅ 目录结构保持完整，仅移除文档文件")
