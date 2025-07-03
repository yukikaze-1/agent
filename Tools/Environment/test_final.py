#!/usr/bin/env python3
import os
import sys

# 获取项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))

print(f"当前脚本目录: {current_dir}")
print(f"计算的项目根目录: {project_root}")
print(f"agent_v0.1.py 是否存在: {os.path.exists(os.path.join(project_root, 'agent_v0.1.py'))}")

# 设置环境
os.environ['AGENT_HOME'] = project_root
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 测试导入
try:
    from Module.Utils.Logger import setup_logger
    print("✅ 模块导入成功")
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")

print("✅ 归档后的环境脚本工作正常")
