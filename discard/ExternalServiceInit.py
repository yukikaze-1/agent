# Project:      Agent
# Author:       yomu
# Time:         2024/11/27
# Version:      0.1
# Description:  agent external module initialize

"""
    用于启动agent外部服务器模块
    在新进程环境中运行
    
    运行前请 export PYTHONPATH=/home/yomu/agent:$PYTHONPATH
    
    1. LLM
        1) ollama server *
        2) ollama LLM *
    2. TTS
        1) GPTSoVits server *
        2) CosyVoice server
    3. STT
        1) SenseVoice server *
    4. 
"""

import os
import json
import subprocess
import signal
import logging
import shlex
from subprocess import Popen
from threading import Lock
from typing import List, Dict, Optional, Tuple
from dotenv import dotenv_values

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config

# TODO 要支持stop系列函数，则每个模块应添加支持stop的方法
# TODO ollama run llama3.2好像有点问题，没跑起来？

class ExternalServiceManager:
    """
        负责管理启动和关闭 agent的各外部功能服务器模块
        
        base services 只能通过config.yml来修改
        
        # TODO 还没实现
        optional services 可以动态添加
        
        start系列函数：负责启动services
            - start_select_services
            - _start_single_service
            - _start_single_service_aux
            - _start_services_sequentially
            
        init系列函数：负责初始化services配置
            - init_services     *****(请务必在实例化后调用!!!)*****
                                返回: 启动的外部服务器(base + optional)的name和pid。
                                返回: Tuple[ List[Tuple[str,int]], List[Tuple[str,int]] ]
            - _init_optional_services
            - _init_base_services
            
        stop系列函数： 负责停止已启动的services
            - stop_single_service
            - stop_select_services
            - stop_optional_services
            - _stop_base_services
            - _stop_all_services
        
        restart系列函数： 负责重启已启动的services
            - restart_select_services
            - restart_single_service
            - restart_optional_services
            - _restart_base_services
            - _restart_single_services
            
            
        list系列函数：负责得到服务的各种信息
            - list_started_optional_services
            - list_started_base_services
            - list_started_services
        
        其他函数：
            - _get_services     负责读取要启动的services的配置信息
            - generate_service_config       负责生成服务配置信息(添加或临时启动service时使用)
        
        注意!!!:  
            1. 初始化请只调用init_services()方法
            2. 要临时额外启动外部服务请调用start_select_services()方法
        
        如需要添加自定义外部功能服务器模块，则
            1. 在 Init/config.yml中按照下面的格式添加：    
        
                    GPTSovits:                              # 外部服务器的名字
                        script: "xxx.py or ls -l"           # 外部服务器的启动文件 或者 bash命令
                        service_name: "xxx"                 # 启动的服务的名字
                        conda_env: "xxx"                    # conda环境，默认base
                        args: ["-a", "127.0.0.1"]             # 额外参数
                        use_python: true                    # 是否用python启动脚本
                        run_in_background: true             # 是否后台运行
                        is_base: true                       # 是否为基础功能服务器
                        log_file: "xxx.log"                 # log文件名
        
    """  
    def __init__(self):
        # 自身的logger
        self.logger = setup_logger(name="ExternalService",log_path="ExternalService")
        
        # 配置相关
        self.env_vars = dotenv_values("Init/.env")
        self.config_path = self.env_vars.get("INIT_CONFIG_PATH","")
        self.config: Dict = load_config(config_path=self.config_path, config_name='external_services', logger=self.logger) 
        
        self.lock = Lock()
        self.support_services: List[str] = self.config.get('support_services', [])
        
        # 要启动的service的日志路径
        log_base = self.env_vars.get("LOG_PATH")
        if log_base is None:
            raise ValueError("LOG_PATH not set in env_vars")
        self.log_dir = os.path.join(log_base, "ExternalService")
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 进程相关
        self.base_processes: List[Tuple[str,Popen]] = []   # 保存base外部服务器后台进程对象以及名字
        self.optional_processes: List[Tuple[str,Popen]] = []  # 保存optional外部服务器后台进程对象以及名字
        
         
    def init_services(self)->Tuple[ List[Tuple[str,int]], List[Tuple[str,int]] ]:
        """
        返回启动的外部服务器的名字和pid
            base: List[Tuple[str,int]]
            optional: List[Tuple[str,int]]
        """
        base_success, base_fail =  self._init_base_services()
        optional_success, optional_fail =  self._init_optional_services()
        return base_success, optional_success  # 修复：应该返回 optional_success 而不是 optional_fail 
    
    
    def _get_services(self, isBaseServices:bool)-> List[Dict]:
        """
            从self.config中获取要启动的services
            
            :param isBaseServices: True: base_services ; False: optional_services
            
            返回：
                服务器配置字典列表，形式如下:
                
                    [{
                        "script": "xxx.py or bash cmd", # 外部服务器的启动文件或bash命令
                        "service_name": "xxx",          # 启动的服务的名字
                        "conda_env": "xxx",             # conda 环境，默认 base
                        "args": ["-a", "127.0.0.1"],      # 额外参数
                        "use_python": True,             # 是否用 Python 启动脚本
                        "run_in_background": True,      # 是否后台运行
                        "is_base": True,                # 是否为基础功能服务器
                        "log_file": "xxx.log"           # log 文件名
                    }]
        """
        services_key = "base_services" if isBaseServices else "optional_services"
        services: List[Dict] = self.config.get(services_key, [])
        
        # 如果是基础服务，检查是否为空列表
        if not services:
            # 基础服务为空
            if isBaseServices:
                self.logger.warning(f"base services is empty. Please check the {self.config_path}")
                raise ValueError(f"base services is empty. Please check the {self.config_path}")
            else:
                return []
            
        # 提取所有服务的配置字典
        ret = [next(iter(service.values())) for service in services]
        return ret
    
    def _start_single_service(self,service:Dict)->Tuple[bool, Tuple[str,int]]:
        return self._start_single_service_aux(service_script = service["script"],
                                              service_name=service["service_name"],
                                              conda_env_path = service["conda_env"],
                                              args= service["args"],
                                              use_python = service.get("use_python", False),
                                              run_in_background = service.get("run_in_background", False),
                                              is_base = service.get("is_base", False),
                                              log_file = service.get("log_file", None))
            
    def _start_single_service_aux(self,      
                                  service_script: str,
                                  service_name: str,
                                  conda_env_path: str,
                                  args: List[str] = [],
                                  use_python: bool = False, 
                                  run_in_background: bool = False,
                                  is_base: bool = False,
                                  log_file: str | None = None
                                  )->Tuple[bool, Tuple[str,int]]:
        """
        在独立进程中运行外部服务模块。
        
        :returns: 启动是否成功，启动的服务的名字和pid

        :param service_script: 服务模块路径，例如 "Myservice.py"
        :param service_name: 服务模块的名字，例如 "GPTSoVits"
        :param conda_env_path: Conda 环境路径，例如 "/path/to/conda/env"
        :param use_python: 是否使用指定 Conda 环境中的 Python 运行脚本
        :param run_in_background: 是否在后台运行该服务
        :param is_base: 是否是基础服务
        :param log_file: 保存输出日志的文件路径，如果为 ""，则不保存日志
        """
        # TODO 目前该函数无法确定service到底有没有成功启动缺少检测机制
        # 如果启动失败，应该返回[False, (service, -1)],修改此处的机制，就必须修改一系列函数，要检查
        
        if not log_file:  # log_file 为 None 时
            stdout_option = stderr_option = stdin_option = subprocess.DEVNULL
            self.logger.warning(f"Service :'{service_name}' start with no logfile")
        else:
            log_file = os.path.join(self.log_dir, log_file)
            if run_in_background:
                stdout_option = stderr_option = open(log_file, "a")
                stdin_option = subprocess.DEVNULL
            else:
                stdout_option = stderr_option = stdin_option = None
            self.logger.info(f"Start service '{service_name}'with logfile: '{log_file}'")

        # 获取脚本所在的目录，确保工作目录正确
        script_dir = os.path.dirname(service_script) or "/home/yomu"
        
        ret: Tuple[str, int] 

        # TODO 这里为什么需要锁？搞清楚
        with self.lock:
            if use_python:
                # 获取 Conda 环境中的 Python 路径
                python_path = os.path.join(conda_env_path, "bin", "python")
                if not os.path.exists(python_path):
                    self.logger.error(f"Python executable not found in Conda environment: {python_path}")
                    raise FileNotFoundError(f"Python executable not found in Conda environment: {python_path}")

                # 启动服务模块，使用指定的 Python 解释器
                self.logger.info(f"Starting service '{service_name}' at '{service_script}' with Python '{python_path}'")
                
                # 后台运行的程序
                if run_in_background:
                    try:
                        process = subprocess.Popen(
                            args= [python_path, service_script] + args,
                            stdin=stdin_option,
                            stdout=stdout_option,
                            stderr=stderr_option,
                            preexec_fn=os.setsid,  # 使子进程在独立的进程组中运行
                            close_fds=True,  # 确保子进程不继承父进程的文件描述符
                            cwd=script_dir  # 设置工作目录为脚本所在目录
                        )
                        if is_base:
                            self.base_processes.append((service_name, process))
                        else:
                            self.optional_processes.append((service_name, process))
                        ret = (service_name, process.pid)
                        
                    except subprocess.SubprocessError as e:
                        self.logger.error(f"Failed to start background service '{service_name}': {e}")
                        ret = (service_name, -1)
                    
                # 前台运行的程序 
                else:
                    # TODO 对于前台启动的程序还需额外处理
                    try:
                        subprocess.run(service_script, shell=True, check=True, cwd=script_dir)
                        ret = (service_name, -1)  # 前台运行可能没有PID
                    except subprocess.CalledProcessError as e:
                        self.logger.error(f"Service '{service_name}' exited with error: {e}")
            # 不用python
            else:
                # 启动服务模块，直接运行命令（例如 ollama serve）
                self.logger.info(f"Starting service '{service_name}' using system shell")
                command_list = [service_script] + args
                command_str = ' '.join(shlex.quote(arg) for arg in command_list)
                if run_in_background:
                    try:
                        process = subprocess.Popen(
                            args=command_str,
                            shell=True,
                            stdin=stdin_option,
                            stdout=stdout_option,
                            stderr=stderr_option,
                            preexec_fn=os.setsid,  # 使子进程在独立的进程组中运行
                            close_fds=True,  # 确保子进程不继承父进程的文件描述符
                            cwd=script_dir  # 设置工作目录为脚本所在目录
                        )
                        if is_base:
                            self.base_processes.append((service_name,process))
                        else:
                            self.optional_processes.append((service_name,process))
                        ret = (service_name, process.pid)
                    except subprocess.SubprocessError as e:
                        self.logger.error(f"Failed to start background service '{service_name}': {e}")
                        ret = (service_name, -1)
                else:
                    try:
                        subprocess.run(service_script, shell=True, check=True, cwd=script_dir)
                        ret = (service_name, -1)  # 前台运行可能没有PID
                    except subprocess.CalledProcessError as e:
                        self.logger.error(f"Service '{service_name}' exited with error: {e}")
                        ret = (service_name, -1)

        if stdout_option not in [None, subprocess.DEVNULL]:
            stdout_option.close()
        self.logger.info(f"Start service '{service_name}' succeeded!")
        _, _pid = ret
        return (_pid != -1, ret)
    
    def _start_select_services(self,services:List[Dict])->Tuple[bool,List[Tuple[str,int]],List[Tuple[str,int]]]:
        """
        启动 选择的Any外部服务器
        
        参数:
            services (list): 要启动的services名字
        
        返回:
            全部启动成功or失败，启动成功的services名字+pid，启动失败的services名字+pid
        """
        # 获取已启动的services集合
        started_optional_services = {service for service, _ in self.optional_processes}
        started_base_services = {service for service, _ in self.base_processes}
        
        # 过滤出 未启动的且要start的 optional services
        optional_services_to_start = [service for service in services if service.get("service_name") not in started_optional_services] 
        base_services_to_start = [service for service in services if service.get("service_name") not in started_base_services] 
        
        if not optional_services_to_start and not base_services_to_start:
            self.logger.info("No services need to start.Please check the param:services")
            return (False, [], [])
        
        ok1, _base_suceess, _base_fail = self._start_services_sequentially(services=base_services_to_start)
        ok2, _opt_sucess, _opt_fail = self._start_services_sequentially(services=optional_services_to_start)
        
        return (ok1 and ok2, _base_suceess + _opt_sucess, _base_fail + _opt_fail)
                    
    def start_select_services(self,services:List[Dict])->Tuple[bool,List[Tuple[str,int]],List[Tuple[str,int]]]:
        """
        启动 选择的optional外部服务器
        
        如果选择了base外部服务器，则会忽略！！！
        
        返回：
            全部启动成功or失败，启动成功的services名字+pid，启动失败的services 名字+pid
        """
        # 提取出已启动的optional service集合
        started_optional_services = {service for service, _ in self.optional_processes}
        
        # 过滤出 未启动的且要start的 optional services
        services_to_start = [service for service in services if service.get("service_name") not in started_optional_services] 
        
        if not services_to_start:
            self.logger.info("No optional services need to start.Please check the param:services")
            return (False, [], [])
        
        # TODO 要修改此处的机制 ，暂时没考虑启动失败的情况
        return self._start_services_sequentially(services=services_to_start)

    def _start_services_sequentially(self, services: List[Dict])->Tuple[bool, List[Tuple[str,int]], List[Tuple[str,int]]]:
        """
        按顺序启动多个服务模块。
        
        :returns: 启动成功or失败,启动成功的服务的名字和pid的列表，启动失败的服务的名字和pid的列表(-1)

        :param services: 
            服务列表，每个服务是一个字典,形式如下
            
                {
                    "script": "xxx.py or bash cmd", # 外部服务器的启动文件或bash命令
                    "service_name": "xxx",          # 启动的服务的名字
                    "conda_env": "xxx",             # conda 环境，默认 base
                    "args": ["-a", "127.0.0.1"],      # 额外参数
                    "use_python": True,             # 是否用 Python 启动脚本
                    "run_in_background": True,      # 是否后台运行
                    "is_base": True,                # 是否为基础功能服务器
                    "log_file": "xxx.log"           # log 文件名
                }
        
        """
        success: List[Tuple[str, int]] = []
        fail: List[Tuple[str, int]] = []
        
        if services is None:
            return (False, [], [])
        
        for service in services:
            try:
                ok, _service = self._start_single_service(service=service)
                if ok:
                    success.append(_service)
                else:
                    fail.append(_service)
            except Exception as e:
                self.logger.warning(f"Service {service['service_name']} started failed with error: {e}")
                
        return (len(fail) == 0, success, fail)
    
    def _init_optional_services(self)->Tuple[List[Tuple[str,int]],List[Tuple[str,int]]]:
        """启动 可选服务
        
        :returns: 启动成功or失败,启动成功的服务的名字和pid的列表，启动失败的服务的名字和pid的列表(-1)
        """
        # 获取要启动的optional services
        optional_services = self._get_services(isBaseServices=False)
        if not optional_services:
            self.logger.info("No additional external services need to start")
            return ([], [])
        else:
            # TODO 要修改此处的机制 ，暂时没考虑启动失败的情况，需要加入重试机制，使其启动成功，若在最大次数重试之后仍然失败，报warning，但不退出
            is_all_started, success, fail = self._start_services_sequentially(optional_services)
            return (success, fail)

    def _init_base_services(self)-> Tuple[List[Tuple[str,int]], List[Tuple[str,int]]]:
        """启动 基础服务
        
        :returns: 启动成功or失败,启动成功的服务的名字和pid的列表。启动失败的服务的名字和pid的列表(-1)
        """
        base_services = self._get_services(isBaseServices=True)
        if base_services is None:
            raise ValueError("Init base services error:No base services config!!!")
        
        # TODO 要修改此处的机制 ，暂时没考虑启动失败的情况,需要加入重试机制，使其启动成功，若在最大次数重试之后仍然失败，报error，然后退出
        is_all_started, success, fail = self._start_services_sequentially(base_services)
        
        return (success, fail)


    def stop_single_service(self,service:str)->bool:
        """停止 单个外部服务(仅限optionl services)"""
        return self._stop_single_service_aux(service, self.optional_processes, isBaseService=False)
        
    def _stop_single_service(self,service:str, isBaseService:bool)->bool:
        """通用函数 停止 单个Any外部服务"""
        processes: List[Tuple[str,Popen]] = self.base_processes if isBaseService else self.optional_processes
        return self._stop_single_service_aux(service, processes, isBaseService=isBaseService)
    
    def _stop_single_service_aux(self, service:str ,processes: List[Tuple[str,Popen]], isBaseService:bool)->bool:
        """停止 单个Any外部服务
        :processes: 内部保存的(External or Internal)service name + Popen(进程对象)
        :param service: 要stop的service的名字
        :param isBaseService: 是否是base service
        
        返回：
            stop成功与否
        """
        process_type: str = "base" if isBaseService else "optional"
        
        # 检索
        for item in processes:
            service_name, process = item
            if service_name == service:
                if process.poll() is None:  # 如果进程仍在运行
                    self.logger.info(f"Terminating {process_type} process: '{service_name}': {process.pid}")
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)  # 终止整个进程组
                    self.logger.info(f"Terminated {process_type} process: '{service_name}': {process.pid}")
                else:
                    self.logger.info(f"{process_type} process: '{service_name}':{process.pid} is stopped early.But not removed in the list.Now removed.")
                # 将终止的进程从列表中移除
                processes.remove(item)
                return True
            
        self.logger.info(f"{process_type} service '{service}' is not running.No need to stop.Do nothing.")
        return False  

    def _stop_services(self, services: List[str], isBaseService: bool)->Tuple[bool, List[str], List[str]]:
        """
        停止 选择的已启动的Any外部服务器
        
        返回:
            是否全部stop成功，stop成功的service name，stop失败的service name
        """
        success:List[str] = []
        fail:List[str] = []
        
        for service in services:
            if self._stop_single_service(service, isBaseService=isBaseService):
                success.append(service)
            else:
                fail.append(service)
    
        self.logger.info(f"Stopped the select services successfully: {success}")
        if len(fail) > 0:        
            self.logger.warning(f"Stopped the select services failed: {fail}")
                
        return (len(fail) == 0, success, fail)
    
    def _stop_select_services(self,services:List[str])->Tuple[bool, List[str], List[str]]:
        """
        停止 选择的已启动的Any外部服务器
        
        返回:
            是否全部stop成功，stop成功的service name，stop失败的service name
        """
        # 提取出已启动的service集合
        started_optional_services = {service for service, _ in self.optional_processes}
        started_base_services = {service for service, _ in self.base_processes}
        
        # 过滤出 已启动的且要stop的 optional services
        optional_services_to_stop = [service for service in services if service in started_optional_services]
        base_services_to_stop = [service for service in services if service in started_base_services]
        
        if base_services_to_stop is None and optional_services_to_stop is None:
            self.logger.info("No services need to stop.Please check the param:services")
            return (False, [], [])
        
        ok1, opt_success, opt_fail = self._stop_services(optional_services_to_stop, isBaseService=False)
        ok2, base_success, base_fail = self._stop_services(base_services_to_stop, isBaseService=True)
        
        return ok1 and ok2, base_success + opt_success, base_fail + opt_fail
    
    def stop_select_services(self,services:List[str])->Tuple[bool, List[str], List[str]]:
        """
        停止 选择的已启动的optional外部服务器
        
        注意：  如果选择了base外部服务器，则会忽略！！！
        
        返回:
            是否全部stop成功，stop成功的service name，stop失败的service name
        """
        started_optional_services = {service for service, _ in self.optional_processes}
        services_to_stop = [service for service in services if service in started_optional_services]
        
        if services_to_stop is None:
            self.logger.info("No optional services need to stop.Please check the param:services")
            return (False, [], [])
        
        return self._stop_services(services_to_stop, isBaseService=False)
   
    def stop_optional_services(self)->Tuple[bool, List[str], List[str]]:
        """终止 所有可选功能的外部服务器"""
        self.logger.info(f"ExternalServiceManager is now stopping all the optional external services...")
        services_to_stop = [service for service, _ in self.optional_processes]
        return self._stop_services(services_to_stop, isBaseService=False)
    
    def _stop_base_services(self)->Tuple[bool, List[str], List[str]]:
        """终止 所有基础功能的外部服务器"""
        self.logger.info(f"ExternalServiceManager is now stopping all the base external services...")
        services_to_stop = [service for service, _ in self.base_processes]
        return self._stop_services(services_to_stop, isBaseService=True)
    
    def _stop_all_services(self):
        """终止 所有Any外部服务器"""
        self.stop_optional_services()
        self._stop_base_services()
        self.logger.info("ExternalServiceManager cleaned up and all background services are stopped.") 
     
    def _check_service_is_started(self, service: str)->bool:
        """检测 单个service是否已经启动"""
        for name, _ in self.optional_processes:
            if name == service:
                return True
        for name, _ in self.base_processes:
            if name == service:
                return True
        return False
        
    def restart_single_service(self,service:str)->Tuple[bool, Tuple[str,int]]:
        """
        重启 单个 service(仅限optional services)如果包含了base services ，则会忽略
        如果service未启动，则不会执行任何操作。返回(False, ("Not started", -1))
        如果service停止失败，则不会执行任何操作。返回(False, ("Stop failed", -2))
        
        :returns: 是否重启成功，service name， service pid(如果成功，失败则返回值<0) 
        
        :param service: 要重启的service的名字
        :param isBaseService: 是否是base service
        """
        started_optional_services = {service for service, _ in self.optional_processes}
        
        if service not in started_optional_services:
            self.logger.info(f"Optional service {service} is not running.No need to restart it. Do nothing.")
            return (False, ("Not in Optional running service List", -3))

        return self._restart_single_service_aux(service, isBaseService=False)
        
    def _restart_single_service(self, service:str, isBaseService: bool)->Tuple[bool, Tuple[str,int]]:
        """
        重启指定service。
        如果service未启动，则不会执行任何操作。返回(False, ("Not started", -1))
        如果service停止失败，则不会执行任何操作。返回(False, ("Stop failed", -2))
        
        :returns: 是否重启成功，service name， service pid(如果成功，失败则返回值<0) 
        
        :param service: 要重启的service的名字
        :param isBaseService: 是否是base service
        """
        return self._restart_single_service_aux(service, isBaseService=isBaseService)
    
    def _restart_single_service_aux(self, service:str, isBaseService: bool)->Tuple[bool, Tuple[str,int]]:
        """
        重启指定service。
        如果service未启动，则不会执行任何操作。返回(False, ("Not started", -1))
        如果service停止失败，则不会执行任何操作。返回(False, ("Stop failed", -2))
        
        :returns: 是否重启成功，service name， service pid(如果成功，失败则返回值<0) 
        
        :param service: 要重启的service的名字
        :param isBaseService: 是否是base service
        """
        # 检测该service是否已经启动，若本身没启动，则不应该重启
        if not self._check_service_is_started(service):
            self.logger.info(f"The service {service} is not running. No need to restart it. Do nothing.")
            return (False, ("Not started", -1))

        self.logger.info(f"Now starting to restart the service {service}...")
        
        # 尝试停止service
        if not self._stop_single_service(service, isBaseService=isBaseService):
            self.logger.warning(f"Restart service {service} failed. Stopping the service failed. Please check the info.")
            return (False, ("Stop failed", -2))
        
        # 获取要启动service的配置信息
        configs = self._get_services(isBaseServices=isBaseService)
        
        # 获取第一个匹配的配置
        service_config = next((config for config in configs if config["service_name"] == service), None)
        if not service_config:
            raise ValueError(f"Cant get the {service}'s config! Please check the Init/config.yml")
        
        # 尝试启动service
        res, info = self._start_single_service(service=service_config)
        if not res:
            self.logger.warning(f"Restart service {service} failed. Starting the service failed. Please check the info.")
            return (False, ("Start failed", -3))

        self.logger.info(f"Service {service} restarted successfully.")
        return (True, info)
    
    def _restart_services(self, services: List[str], isBaseService: bool)->Tuple[bool,List[Tuple[str,int]],List[Tuple[str,int]]]:
        """
        """
        success: List[Tuple[str,int]] = []
        fail: List[Tuple[str,int]] = []
        
        for service, _ in self.base_processes:
            res, info = self.restart_single_service(service)
            if res:
                success.append(info)
            else:
                fail.append(info)
        
        self.logger.info(f"Restarted the base services successfully:\n \t {success}")
        self.logger.warning(f"Restarted the base services failed:\n \t {fail} ")
        
        return (len(fail) == 0, success, fail)
    
    def _restart_base_services(self)-> Tuple[bool,List[Tuple[str,int]],List[Tuple[str,int]]]:
        """重启 所有基础功能的外部服务器"""
        services_to_restart = [service for service, _ in self.base_processes]
        return self._restart_services(services_to_restart, isBaseService=True)
        
     
    def restart_optional_services(self)-> Tuple[bool,List[Tuple[str,int]],List[Tuple[str,int]]]:
        """重启 所有optional外部服务器"""
        if not self.optional_processes:
            self.logger.info("No optional service is running now.No need to restart them.Do nothing.")
            return (False, [], [])
        
        services_to_restart = [service for service, _ in self.optional_processes]
        return self._restart_services(services_to_restart, isBaseService=False)
    
    def restart_select_services(self, services:List[str])-> Tuple[bool,List[Tuple[str,int]],List[Tuple[str,int]]]:
        """重启 选择的optional外部服务器
        
        返回:
            全部重启成功还是失败, 重新启动(成功/失败)的optional service name
        """
        started_optional_services = {service for service, _ in self.optional_processes}
        services_to_restart = [service for service in services if service in started_optional_services]
        
        if not services_to_restart:
            self.logger.info(f"No service in {services} is running.No need to restart them.Please start them before.")
            return (False, [], []) 
        return self._restart_services(services_to_restart, isBaseService=False)
    
    def _restart_select_services(self, services:List[str])-> Tuple[bool,List[Tuple[str,int]],List[Tuple[str,int]]]:
        """重启 选择的Any外部服务器"""
        # 获取已启动的services
        started_optional_services = {service for service, _ in self.optional_processes}
        started_base_services = {service for service, _ in self.base_processes}
        
        # 获取要restart的且已启动的services
        optional_services_to_restart = [service for service in services if service in started_optional_services]
        base_services_to_restart = [service for service in services if service in started_base_services]
        
        if not optional_services_to_restart and not base_services_to_restart:
            self.logger.info(f"No service in {services} is running.No need to restart them.Please start them before.")
            return (False, [], [])
        
        ok1, opt_success, opt_fail = self._restart_services(optional_services_to_restart, isBaseService=False)
        ok2, base_success, base_fail = self._restart_services(base_services_to_restart, isBaseService=False)
        
        return ok1 and ok2, base_success + opt_success, base_fail + opt_fail
        
    def list_started_services(self, isBaseService: bool)->List[Tuple[str,int]]:
        """返回 已启动的所有外部服务器的名字与pid"""
        if isBaseService == None:
            return [(name, service.pid) for name, service in self.base_processes] + [(name, service.pid) for name, service in self.optional_processes]
        if isBaseService == True:
            return [(name, service.pid) for name, service in self.base_processes]
        else:
            return [(name, service.pid) for name, service in self.optional_processes]
                 
    def __del__(self):
        self._stop_all_services()
        print("ExternalServiceManager deleted")
        
    def _show(self):
        print("Here are the started services:")
        base = [{'name': name, 'pid': pid} for (name, pid) in self.list_started_services(isBaseService=True)]
        opt = [{'name': name, 'pid': pid} for (name, pid) in self.list_started_services(isBaseService=False)]
        self.logger.info(f"Base services: {json.dumps(base)}")
        self.logger.info(f"Optional services: {json.dumps(opt)}")
        
 
    def generate_service_config(self, script: str, service_name:str, conda_env: str,
                                args: List[str], use_python: bool, run_in_background: bool,
                                is_base: bool, log_file: str)->Dict:
        """
        生成service config
        
        :param  script: 外部服务器的启动文件 或者 bash命令
        :param  service_name: 启动的服务的名字
        :param  conda_env: conda环境，默认base
        :param  args: 额外参数
        :param  use_python: 是否用python启动脚本
        :param  run_in_background: 是否后台运行
        :param  is_base: 是否为基础功能服务器
        :param  log_file: log文件名
        """
        ret = {
                "script": script,
                "service_name": service_name,
                "conda_env": conda_env,
                "args": args,
                "use_python": use_python,
                "run_in_background": run_in_background,
                "is_base": is_base,
                "log_file": log_file
        }
        return ret

    def check_service_health(self, service_name: str, timeout: int = 30) -> bool:
        """
        检查服务是否真正启动成功
        
        :param service_name: 服务名称
        :param timeout: 超时时间（秒）
        :return: 服务是否健康
        """
        import time
        try:
            import requests
        except ImportError:
            self.logger.warning("requests module not available, skipping HTTP health checks")
            return True
        
        # 根据服务类型定义不同的健康检查策略
        health_check_configs = {
            "ollama_server": {"url": "http://127.0.0.1:11434/api/tags", "method": "GET"},
            "GPTSoVits_server": {"url": "http://127.0.0.1:9880/health", "method": "GET"},
            "SenseVoice_server": {"url": "http://127.0.0.1:8001/health", "method": "GET"},
            "Consul": {"url": "http://127.0.0.1:8500/v1/status/leader", "method": "GET"}
        }
        
        config = health_check_configs.get(service_name)
        if not config:
            self.logger.warning(f"No health check config for service: {service_name}")
            return True  # 假设服务正常
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(config["url"], timeout=5)
                if response.status_code == 200:
                    self.logger.info(f"Service {service_name} health check passed")
                    return True
            except requests.RequestException:
                pass
            
            time.sleep(2)
        
        self.logger.error(f"Service {service_name} health check failed after {timeout}s")
        return False
    
    def _start_service_with_retry(self, service: Dict, max_retries: int = 3) -> Tuple[bool, Tuple[str, int]]:
        """
        带重试机制的服务启动
        
        :param service: 服务配置
        :param max_retries: 最大重试次数
        :return: (启动成功, (服务名, PID))
        """
        service_name = service.get("service_name", "Unknown")
        
        for attempt in range(max_retries + 1):
            try:
                success, result = self._start_single_service(service)
                
                if success:
                    # 进行健康检查
                    if self.check_service_health(service_name):
                        self.logger.info(f"Service {service_name} started successfully on attempt {attempt + 1}")
                        return True, result
                    else:
                        self.logger.warning(f"Service {service_name} started but health check failed on attempt {attempt + 1}")
                        # 停止失败的服务
                        self._stop_single_service(service_name, service.get("is_base", False))
                        success = False
                
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # 指数退避
                    self.logger.info(f"Retrying service {service_name} in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    import time
                    time.sleep(wait_time)
                    
            except Exception as e:
                self.logger.error(f"Service {service_name} start attempt {attempt + 1} failed with error: {e}")
                
        self.logger.error(f"Service {service_name} failed to start after {max_retries + 1} attempts")
        return False, (service_name, -1)

def main():
    logging.info("Now initialize the service")
    manager = ExternalServiceManager()
    manager.init_services()
    input("enter1")
    manager._show()
    input("enter2")

if __name__ == "__main__":
    main()
