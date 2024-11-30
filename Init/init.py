# Project:      Agent
# Author:       yomu
# Time:         2024/11/30
# Version:      0.1
# Description:  AI agent  initialize

"""
    进行agent的所有初始化
        内部模块初始化:     Init/internal_module_init.py
        外部服务器初始化:   Init/external_service_init.py
        
"""

from external_service_init import ExternalServiceManager
from internal_module_init import InternalModuleManager

# TODO 24/11/30的任务，实现该类
class InitAgent:
    """
        该类初始化整个AI agent
        
    """
    def __init__(self):
        self.external_service_manager = ExternalServiceManager()
        self.internal_module_manager = InternalModuleManager()
    
    