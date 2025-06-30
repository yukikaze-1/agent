#!/usr/bin/env python3
"""
配置验证脚本

验证 InternalModuleInit 的配置文件是否正确。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from .utils.config_validator import validate_module_config
from Module.Utils.ConfigTools import load_config
from Module.Utils.Logger import setup_logger


def main():
    """主函数"""
    logger = setup_logger(name="ConfigValidator", log_path="Other")
    
    try:
        # 加载配置
        config_path = "/home/yomu/agent/InternalModuleInit/config.yml"
        config = load_config(config_path=config_path, config_name='internal_modules', logger=logger)
        
        # 验证配置
        logger.info("开始验证配置文件...")
        is_valid = validate_module_config(config, logger)
        
        if is_valid:
            logger.info("✅ 配置文件验证通过!")
            
            # 显示配置摘要
            logger.info("配置摘要:")
            logger.info(f"  支持的模块: {config.get('support_modules', [])}")
            logger.info(f"  基础模块数量: {len(config.get('base_modules', []))}")
            logger.info(f"  可选模块数量: {len(config.get('optional_modules', []))}")
            logger.info(f"  依赖关系: {config.get('dependencies', {})}")
            
            return True
        else:
            logger.error("❌ 配置文件验证失败!")
            return False
            
    except Exception as e:
        logger.error(f"❌ 配置验证过程中出现错误: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
