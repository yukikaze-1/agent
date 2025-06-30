#!/usr/bin/env python3
"""
调试配置加载问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from Module.Utils.ConfigTools import load_config
from Module.Utils.Logger import setup_logger

def main():
    logger = setup_logger(name="ConfigDebug", log_path="Other")
    
    # 测试配置加载
    config_path = "/home/yomu/agent/InternalModuleInit/config.yml"
    
    print(f"配置文件路径: {config_path}")
    print(f"文件是否存在: {os.path.exists(config_path)}")
    
    try:
        config = load_config(config_path=config_path, config_name='internal_modules', logger=logger)
        print(f"配置加载成功: {type(config)}")
        print(f"配置内容: {config}")
        
        # 检查具体字段
        print(f"\nbase_modules: {config.get('base_modules', 'NOT_FOUND')} (type: {type(config.get('base_modules', None))})")
        print(f"optional_modules: {config.get('optional_modules', 'NOT_FOUND')} (type: {type(config.get('optional_modules', None))})")
        print(f"support_modules: {config.get('support_modules', 'NOT_FOUND')} (type: {type(config.get('support_modules', None))})")
        
    except Exception as e:
        print(f"配置加载失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
