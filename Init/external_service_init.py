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
import subprocess
from subprocess import Popen
import signal
import logging
from typing import List,Dict,Optional,Tuple
from dotenv import load_dotenv

# TODO 需要在这放一个这个嘛？
load_dotenv()

class ExternalServiceManager:
    """
        负责管理启动和关闭 agent的各外部功能服务器模块
        
        init_services()方法返回启动的外部服务器(base + optional)的名字和pid
            返回：Tuple[ List[Tuple[str,int]], List[Tuple[str,int]] ]
        
        注意!!!:  
            1. 初始化请只调用init_services()方法
            2. 要额外启动外部服务请调用start_select_services()方法
        
        如需要添加自定义外部功能服务器模块，则需要按照下面的格式：    
        {
            "script": xxx.py 或者 ls -l,        # 外部服务器的启动文件 或者 bash命令
            "service_name": xxx                 # 启动的服务的名字
            "conda_env": xxx,                   # conda环境，默认base
            "args": ["-a", "0.0.0.0"],          # 额外参数
            "use_python": True,                 # 是否用python启动脚本
            "run_in_background": True,          # 是否后台运行
            "is_base": True,                    # 是否为基础功能服务器
            "log_file": "xxx.log"               # log文件名
        } 
    """ 
    def __init__(self,
                 services: List[Dict] = None,
                 conda_env_path: str = os.getenv("CONDA_ENV_PATH","/home/yomu/data/anaconda3/envs"),
                 conda_base_env_path: str = os.getenv("CONDA_BASE_ENV_PATH","/home/yomu/data/anaconda3")):
        """
            初始化服务管理器，加载环境变量
            
            :param services:    要启动的服务
            :param conda_env_path:  conda环境path
            :param conda_base_env_path: conda base环境path
        """
        
        # TODO 这玩意放这需要额外参数来定位.env文件吗
        load_dotenv()
        
        # 日志相关
        self.log_dir = os.path.join(os.getenv("LOG_PATH"), "ExternalService")
        os.makedirs(self.log_dir, exist_ok=True)  
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')        
        
        # 进程相关
        self.base_processes: List[Tuple[str,Popen]] = []    # 用于保存基础外部服务器后台进程对象以及名字
        self.optional_processes: List[Tuple[str,Popen]] = []     # 用于保存可选外部服务器后台进程对象以及名字
        
        # conda 环境
        self.conda_env_path = conda_env_path    # conda环境path
        self.conda_base_env_path = conda_base_env_path  # conda base环境 path
        
        # 要启动的服务
        self.base_services = self._add_base_service()     # 要启动的基本外部功能服务器
        self.optional_services = services if services else []  # 要启动的可选外部功能服务器
        
        
    def init_services(self)->Tuple[ List[Tuple[str,int]], List[Tuple[str,int]] ]:
        """
        返回启动的外部服务器的名字和pid
            base: List[Tuple[str,int]]
            optional: List[Tuple[str,int]]
        """
        base =  self._init_base_services()
        optional =  self._init_optional_services()
        return base, optional    
    
    # TODO 将这些配置提取到一个json配置文件中，函数应从该json文件中读取要初始化的外部服务
    def _add_base_service(self)-> List[Dict]:
        """
        添加最小启动的最基础的外部功能服务器
            1. ollama server
            2. ollama llm
            3. 语音合成(GPTSoVits)
            4. 语音识别(SenseVoice)
        """
        ret = []
        ret.append( 
            {"script": "ollama serve",
             "service_name":"ollama_server",
             "conda_env": self.conda_base_env_path,
             "args": [],
             "use_python": False,
             "run_in_background": True,
             "is_base": True,
             "log_file": "ollama_server.log"
             }  # ollama server
        )
        ret. append(            
            {"script": "ollama run llama3.2", 
             "service_name":"ollama_LLM",
             "conda_env": self.conda_base_env_path, 
             "args": [],
             "use_python": False, 
             "run_in_background": True, 
             "is_base": True,
             "log_file": ""
             },  # ollama LLM
        )
        GPTSoVits_server = os.path.join(os.getenv("GPTSOVITS_ROOT"), "api_v2.py")
        SenseVoice_server = os.path.join(os.getenv("SENSEVOICE_ROOT"), "SenseVoice_server.py")
        ret.append(
            {"script": GPTSoVits_server,
             "service_name": "GPTSoVits_server",
             "conda_env": os.path.join(self.conda_env_path, "GPTSoVits"),
             "args": ["-a", "0.0.0.0","-p","9880"],
             "use_python": True,
             "run_in_background": True,
             "is_base": True,
             "log_file": "GPTSoVits_server.log"},  # GPTSoVits server
        )
        # TODO SenseVoice的服务端~/SenseVoice/SenseVoice_server.py还需要改进，添加命令行选项，如"--host","--port"
        ret.append(
            {"script": SenseVoice_server,
             "service_name":"SenseVoice_server",
             "conda_env": os.path.join(self.conda_env_path, "SenseVoice"),
             "args": [],
             "use_python": True,
             "run_in_background": True,
             "is_base": True,
             "log_file": "SenseVoice_server.log"},  # SenseVoice server
        )
        return ret
    
        
    def _run_service(self,
                    service_script: str,
                    service_name: str,
                    conda_env_path: str,
                    args: List[str] = [],
                    use_python: bool = False, 
                    run_in_background: bool = False,
                    is_base: bool = False,
                    log_file: str = ""
                    )->Tuple[str,int]:
        """
        在独立进程中运行外部服务模块。
        
        :returns: 启动的服务的名字和pid

        :param service_script: 服务模块路径，例如 "Myservice.py"
        :param service_name: 服务模块的名字，例如 "GPTSoVits"
        :param conda_env_path: Conda 环境路径，例如 "/path/to/conda/env"
        :param use_python: 是否使用指定 Conda 环境中的 Python 运行脚本
        :param run_in_background: 是否在后台运行该服务
        :param is_base: 是否是基础服务
        :param log_file: 保存输出日志的文件路径，如果为 ""，则不保存日志
        """
        
        if not log_file:  # log_file 为 "" 或 None 时
            stdout_option = stderr_option = stdin_option = subprocess.DEVNULL
            print("No logfile")
        else:
            log_file = os.path.join(self.log_dir, log_file)
            if run_in_background:
                stdout_option = stderr_option = open(log_file, "a")
                stdin_option = subprocess.DEVNULL
            else:
                stdout_option = stderr_option = stdin_option = None
            print(f"logfile: {log_file}")

        # 获取脚本所在的目录，确保工作目录正确
        script_dir = os.path.dirname(service_script) or "/home/yomu"
        
        ret = ()

        if use_python:
            # 获取 Conda 环境中的 Python 路径
            python_path = os.path.join(conda_env_path, "bin", "python")
            if not os.path.exists(python_path):
                raise FileNotFoundError(f"Python executable not found in Conda environment: {python_path}")

            # 启动服务模块，使用指定的 Python 解释器
            print(f"Starting service {service_name} with Python {python_path}")
            if run_in_background:
                process = subprocess.Popen(
                    args = [python_path, service_script] + args,
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
                    self.optional_processes.append(process)
                ret = (service_name,process.pid)
            else:
                subprocess.run([python_path, service_script], check=True, cwd=script_dir)
        else:
            # 启动服务模块，直接运行命令（例如 ollama serve）
            print(f"Starting service {service_name} using system shell")
            if run_in_background:
                process = subprocess.Popen(
                    service_script,
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
                    self.optional_processes.append(process)
                ret = (service_name,process.pid)
            else:
                subprocess.run(service_script, shell=True, check=True, cwd=script_dir)

        if stdout_option not in [None, subprocess.DEVNULL]:
            stdout_option.close()
        print(f"Start service {service_name} succeeded!")

        return ret
        

    def _start_services_sequentially(self, services: List[Dict])->List[Tuple[str,int]]:
        """
        按顺序启动多个服务模块。
        
        :returns: 启动的服务的名字和pid 的列表

        :param services: 服务列表，每个服务是一个字典
        
        """
        ret = []
        for service in services:
            print(f"start the service: {service['service_name']}")
            try:
                ret.append(self._run_service(service_script = service["script"],
                                 service_name=service["service_name"],
                                 conda_env_path = service["conda_env"],
                                 args= service["args"],
                                 use_python = service.get("use_python", False),
                                 run_in_background = service.get("run_in_background", False),
                                 is_base = service.get("is_base", False),
                                 log_file = service.get("log_file", None)
                                 ))
                print(f"Service {service['service_name']} started successfully.")
            except Exception as e:
                print(f"Service {service['service_name']} started failed with error: {e}")
        return ret
    
    def _init_optional_services(self)->List[Tuple[str,int]]:
        """启动 可选服务"""
        if self.optional_services :
            return self._start_services_sequentially(self.optional_services)
        else:
            print("No additional external services need to start")
            return []

    def _init_base_services(self)-> List[Tuple[str,int]]:
        """启动 基础服务"""
        return self._start_services_sequentially(self.base_services)
    
    def _stop_all_services(self):
        """
        终止 所有外部服务器
        
        禁止调用！！！
        """
        self.stop_optional_services()
        self._stop_base_services()
        print("ServiceManager cleaned up and all background services are stopped.") 
        
    def stop_optional_services(self)->bool:
        """终止 所有可选功能的外部服务器"""
        for service_name,process in self.optional_processes:
            if process.poll() is None:  # 如果进程仍在运行
                print(f"Terminating optional process:{service_name}--{process.pid}")
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)  # 终止整个进程组
        print(f"ServiceManager stopped all the optional services")
                
    def _stop_base_services(self)->bool:
        """
        终止 所有基础功能的外部服务器
            
        禁止调用！！！
        """
        for service_name,process in self.base_processes:
            if process.poll() is None:  # 如果进程仍在运行
                print(f"Terminating base process:{service_name}--{process.pid}")
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)  # 终止整个进程组
        print(f"ServiceManager stopped all the base services")
    
    def _restart_base_services(self)->bool:
        """
        重启 所有基础功能的外部服务器
        
        禁止调用！！！
        """
        pass
     
    def restart_optional_services(self)->bool:
        """重启 所有可选功能的外部服务器"""
        pass
    
    def restart_select_services(self)->bool:
        """
        重启 选择的外部服务器
        
        只能选择停止可选的外部服务器！！！
        如果选择了基础的外部服务器，则会忽略！！！
        """
        pass
    
    def start_select_services(self)->bool:
        """启动 选择的外部服务器"""
        pass
    
    def list_started_services(self)->List[Tuple[str,int]]:
        """返回 已启动的所有外部服务器的名字与pid"""
        base = self.list_started_base_services()
        opt = self.list_started_optional_services()
        return base + opt
    
    def list_started_base_services(self)->List[Tuple[str,int]]:
        """返回 已启动的base外部服务器的名字与pid"""
        return [(name,p.pid) for (name,p) in self.base_processes]
    
    def list_started_optional_services(self)->List[Tuple[str,int]]:
        """返回 已启动的optional外部服务器的名字与pid"""
        return [(name,p.pid) for (name,p) in self.optional_processes]
    
    def stop_select_services(self)->bool:
        """
        停止 选择的已启动的可选的外部服务器
        
        只能选择停止可选的外部服务器！！！
        如果选择了基础的外部服务器，则会忽略！！！
        """
        pass
                
    def __del__(self):
        self._stop_all_services()
        
    def _show(self):
        print("Here are the started services:")
        base = self.list_started_base_services()
        opt = self.list_started_optional_services()
        print("Base services:")
        for name,pid in base:
            print(f"{name}-{pid}")
        print("Optional services:")
        for name,pid in opt:
            print(f"{name}-{pid}")
 
 
 
def generate_service(script: str,
                     conda_env: str,
                     args: List[str],
                     use_python: bool,
                     run_in_background: bool,
                     is_base: bool,
                     log_file: str
                     )->Dict:
    """
    生成service
    
    :param  script: 外部服务器的启动文件 或者 bash命令
    :param  conda_env: conda环境，默认base
    :param  args: 额外参数
    :param  use_python: 是否用python启动脚本
    :param  run_in_background: 是否后台运行
    :param  is_base: 是否为基础功能服务器
    :param  log_file: log文件名
    """
    ret = {
            "script": script,
            "conda_env": conda_env,
            "args": args,
            "use_python": use_python,
            "run_in_background": run_in_background,
            "is_base": is_base,
            "log_file": log_file
    }
    return ret


def main():
    print("Now initialize the service")
    manager = ExternalServiceManager()
    manager.init_services()
    input("enter1")
    manager._show()
    input("enter2")

if __name__ == "__main__":
    main()
