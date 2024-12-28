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

import os
import subprocess
from subprocess import Popen
from typing import List, Dict, Tuple
from dotenv import dotenv_values

from Init.ExternalServiceInit import ExternalServiceManager
from Init.InternalModuleInit import InternalModuleManager
from Init.AgentFrameInit import AgentFrameManager
from Service.Gateway.MicroserviceGateway import MicroserviceGateway
from Service.Gateway.APIGateway import APIGateway
from Service.Other.UserService import UserService
from Init.EnvironmentManager import EnvironmentManager

from Module.Utils.Logger import setup_logger
from Module.Utils.LoadConfig import load_config



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
        self.logger = setup_logger(name="AgentInit", log_path="Other")
        
        self.env_vars = dotenv_values("Init/.env")
        self.config_path = self.env_vars.get("INIT_CONFIG_PATH", "")
        self.config = load_config(config_path=self.config_path, config_name="", logger=self.logger)
        
        # 外部服务
        self.external_service_manager = ExternalServiceManager()
        # 内部模块
        self.internal_module_manager = InternalModuleManager()
        # 
        self.frame_manager = AgentFrameManager() 
        # 微服务网关
        self.micro_service_gateway = MicroserviceGateway()
        # API网关
        self.api_gateway = APIGateway()
        # 用户服务
        self.usr_service = UserService()
        
        # TODO 添加client_gui   character
        
    
    def init_agent(self):
        """初始化agent"""
        # 启动外部服务
        self.external_service_manager.init_services()
        # 启动内部模块
        #self.internal_module_manager.init_modules()
        # 初始化框架
        #self.frame_manager.init_frame()
        #启动微服务网关
        #self.micro_service_gateway.run()
        #启动API网关
        #self.api_gateway.run()
        #启动UserService
        
    def start_service(self, command: str, service_name: str):
        """启动服务"""
        
    
    def _start_single_service_aux(self,      
                                  service_script: str,
                                  service_name: str,
                                  conda_env_path: str,
                                  args: List[str] = [],
                                  use_python: bool = False, 
                                  run_in_background: bool = False,
                                  )->Tuple[bool, Tuple[str,int]]:
        """
        在独立进程中运行的模块。
        
        :returns: 启动是否成功，启动的服务的名字和pid

        :param service_script: 服务模块路径，例如 "Myservice.py"
        :param service_name: 服务模块的名字，例如 "GPTSoVits"
        :param conda_env_path: Conda 环境路径，例如 "/path/to/conda/env"
        :param use_python: 是否使用指定 Conda 环境中的 Python 运行脚本
        :param run_in_background: 是否在后台运行该服务
        """

        stdout_option = stderr_option = stdin_option = None
        
        # 获取脚本所在的目录，确保工作目录正确
        script_dir = os.path.dirname(service_script) or "/home/yomu"
        
        ret = ()

        if use_python:
            # 获取 Conda 环境中的 Python 路径
            python_path = os.path.join(conda_env_path, "bin", "python")
            if not os.path.exists(python_path):
                self.logger.error(f"Python executable not found in Conda environment: {python_path}")
                raise FileNotFoundError(f"Python executable not found in Conda environment: {python_path}")
            # 启动服务模块，使用指定的 Python 解释器
            self.logger.info(f"Starting service '{service_name}' at '{service_script}' with Python '{python_path}'")
            
            # 后台运行的程序
            process = subprocess.Popen(
                args = [python_path, service_script] + args,
                stdin=stdin_option,
                stdout=stdout_option,
                stderr=stderr_option,
                preexec_fn=os.setsid,  # 使子进程在独立的进程组中运行
                close_fds=True,  # 确保子进程不继承父进程的文件描述符
                cwd=script_dir  # 设置工作目录为脚本所在目录
            )
            ret = (service_name,process.pid)
                
            

        if stdout_option not in [None, subprocess.DEVNULL]:
            stdout_option.close()
        self.logger.info(f"Start service '{service_name}' succeeded!")
        
        return (True, ret)
        
        
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
