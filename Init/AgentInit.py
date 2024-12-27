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
from Module.Utils.Logger import setup_logger

from Init.ExternalServiceInit import ExternalServiceManager
from Init.InternalModuleInit import InternalModuleManager
from Init.AgentFrameInit import AgentFrameManager
from Init.MicroserviceGateway import MicroserviceGateway
from Init.APIGateway import APIGateway
from Init.UserService import UserService
from Init.EnvironmentManager import EnvironmentManager


class InitAgent:
    """
        该类初始化整个AI agent
        
        - external_service_manager: 外部服务器管理类
        - internal_module_manager: 内部服务模块管理类
        - frame_manager:  agent 框架管理类
        - microservice_gateway: 微服务网关
        - api_gateway:  API网关
        - client_gui: 客户端GUI管理类
        - character: 虚拟形象管理类
    """
    def __init__(self):
        self.external_service_manager = ExternalServiceManager()
        self.internal_module_manager = InternalModuleManager()
        self.frame_manager = AgentFrameManager() 
        self.micro_service_gateway = MicroserviceGateway()
        self.api_gateway = APIGateway()
        self.usr_service = UserService()
        # TODO 添加client_gui   character
        
    
    def init_agent(self):
        """初始化agent"""
        # 启动外部服务
        self.external_service_manager.init_services()
        # 启动内部模块
        self.internal_module_manager.init_modules()
        # 初始化框架
        self.frame_manager.init_frame()
        #启动微服务网关
        self.micro_service_gateway.run()
        #启动API网关
        self.api_gateway.run()
        #启动UserService
        
        
    def run(self):
        pass
    
    def __del__(self):
        pass

def main():
    agent = InitAgent()
    agent.init_agent()
    r = input("enter1")
    l = input("enter2")

if __name__ == "__main__":
    main()
