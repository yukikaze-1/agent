# Project:      Agent
# Author:       yomu
# Time:         2024/12/23
# Version:      0.1
# Description:  agent log info module initializer

"""
    负责初始化日志系统
"""

import logging
from logging.handlers import TimedRotatingFileHandler
from dotenv import dotenv_values

# 创建按天分割的日志处理器
file_handler = TimedRotatingFileHandler("app.log", when="midnight", interval=1, encoding="utf-8")
file_handler.suffix = "%Y-%m-%d"  # 设置文件名后缀为日期

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        file_handler,  # 按日期分割的文件处理器
        logging.StreamHandler()  # 控制台处理器
    ]
)

# 获取日志记录器
logger = logging.getLogger("MyApp")