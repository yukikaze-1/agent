# Project:      Agent
# Author:       yomu
# Time:         2024/12/1
# Version:      0.1
# Description:  AI agent  initialize

"""
    进行agent的所有初始化
        内部模块初始化:     Init/internal_module_init.py
        外部服务器初始化:   Init/external_service_init.py
        agent框架初始化:    Init/agent_frame_init.py
        
"""

from external_service_init import ExternalServiceManager
from internal_module_init import InternalModuleManager
from agent_frame_init import AgentFrameManager

# TODO 24/11/30的任务，实现该类
class InitAgent:
    """
        该类初始化整个AI agent
        
        - external_service_manager: 外部服务器管理类
        - internal_module_manager: 内部服务模块管理类
        - frame_manager:  agent 框架管理类
    """
    def __init__(self):
        self.external_service_manager = ExternalServiceManager()
        self.internal_module_manager = InternalModuleManager()
        self.frame_manager = AgentFrameManager() 
    
    def init_agent(self):
        self.external_service_manager.init_services()
        self.internal_module_manager.init_modules()
        self.frame_manager.init_frame()
    
    def __del__(self):
        pass

