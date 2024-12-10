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

from Init.ExternalServiceInit import ExternalServiceManager
from Init.InternalModuleInit import InternalModuleManager
from Init.AgentFrameInit import AgentFrameManager


class InitAgent:
    """
        该类初始化整个AI agent
        
        - external_service_manager: 外部服务器管理类
        - internal_module_manager: 内部服务模块管理类
        - frame_manager:  agent 框架管理类
        - client_gui: 客户端GUI管理类
        - character: 虚拟形象管理类
    """
    def __init__(self):
        self.external_service_manager = ExternalServiceManager()
        self.internal_module_manager = InternalModuleManager()
        self.frame_manager = AgentFrameManager() 
        # TODO 添加client_gui   character
    
    def init_agent(self):
        self.external_service_manager.init_services()
        self.internal_module_manager.init_modules()
        self.frame_manager.init_frame()
    
    def __del__(self):
        pass

