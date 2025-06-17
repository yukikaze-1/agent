# Project:      Agent
# Author:       yomu
# Time:         2025/6/17
# Version:      0.1
# Description:  format validate funtion

"""
    各种格式验证的工具函数
"""

import re


def is_email(identifier: str) -> bool:
    """验证邮箱格式"""
    return re.match(r"[^@]+@[^@]+\.[^@]+", identifier) is not None


def is_account_name(identifier: str) -> bool:
    """验证账号格式"""
    return re.match(r"^[a-zA-Z0-9_]{3,16}$", identifier) is not None