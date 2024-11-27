# Project:      Agent
# Author:       yomu
# Time:         2024/11/27
# Version:      0.1
# Description:  agent external module initialize

import os
import subprocess
import signal
import logging
from typing import List,Dict
from concurrent.futures import ProcessPoolExecutor
from dotenv import load_dotenv

load_dotenv()

class ServiceManager:
    """
        负责管理启动和关闭 agent的各外部功能服务器模块
        
        如需要自定义外部功能服务器模块，则需要按照下面的格式：    
        {
            "script": xxx.py 或者 ls -l,        # 外部服务器的启动文件 或者 bash命令
            "conda_env": xxx,                   # conda环境，默认base
            "args": ["-a", "0.0.0.0"],          # 额外参数
            "use_python": True,                 # 是否用python启动脚本
            "run_in_background": True,          # 是否后台运行
            "is_base": True,                    # 是否为基础功能服务器
            "log_file": "xxx.log"               # log文件名
        } 
    """ 
    def __init__(self,
                 services: List[Dict] = [],
                 conda_env_path: str = os.getenv("CONDA_ENV_PATH","/home/yomu/data/anaconda3/envs"),
                 conda_base_env_path: str = os.getenv("CONDA_BASE_ENV_PATH","/home/yomu/data/anaconda3")):
        """
            初始化服务管理器，加载环境变量
            
            :param services
        """
        load_dotenv()
        
        self.log_dir = os.path.join(os.getenv("LOG_PATH"), "External_service")
        os.makedirs(self.log_dir, exist_ok=True)  # 创建日志目录
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')        
        
        self.base_processes = []    # 用于保存基础外部服务器后台进程对象
        self.opt_processes = []     # 用于保存可选外部服务器后台进程对象
        
        self.conda_env_path = conda_env_path    # conda环境path
        self.conda_base_env_path = conda_base_env_path  # conda base环境 path
        self.base_services = self._init_base()     # 要启动的基本外部功能服务器
        self.opt_services = services   # 要启动的可选外部功能服务器
        
    def _init_base(self)-> List[Dict]:
        """只启动最基础的外部功能服务器，如ollama、语音合成和语音识别"""
        ret = []
        ret.append( 
            {"script": "ollama serve",
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
             "conda_env": os.path.join(self.conda_env_path, "GPTSoVits"),
             "args": ["-a", "0.0.0.0","-p","10010"],
             "use_python": True,
             "run_in_background": True,
             "is_base": True,
             "log_file": "GPTSoVits_server.log"},  # GPTSoVits server
        )
        ret.append(
            {"script": SenseVoice_server,
             "conda_env": os.path.join(self.conda_env_path, "SenseVoice"),
             "args": [],
             "use_python": True,
             "run_in_background": True,
             "is_base": True,
             "log_file": "SenseVoice_server.log"},  # SenseVoice server
        )
        return ret
    
    def init(self):
        self._init_base_services()
        self._init_opt_services()
        
    def _run_service(self,
                    service_script: str,
                    conda_env_path: str,
                    args: List[str] = [],
                    use_python: bool = False, 
                    run_in_background: bool = False,
                    is_base: bool = False,
                    log_file: str = ""):
        """
        在独立进程中运行外部服务模块。

        :param service_script: 服务模块路径，例如 "Myservice.py"
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

        if use_python:
            # 获取 Conda 环境中的 Python 路径
            python_path = os.path.join(conda_env_path, "bin", "python")
            if not os.path.exists(python_path):
                raise FileNotFoundError(f"Python executable not found in Conda environment: {python_path}")

            # 启动服务模块，使用指定的 Python 解释器
            print(f"Starting service {service_script} with Python {python_path}")
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
                    self.base_processes.append(process)
                else:
                    self.opt_processes.append(process)
            else:
                subprocess.run([python_path, service_script], check=True, cwd=script_dir)
        else:
            # 启动服务模块，直接运行命令（例如 ollama serve）
            print(f"Starting service {service_script} using system shell")
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
                    self.base_processes.append(process)
                else:
                    self.opt_processes.append(process)
            else:
                subprocess.run(service_script, shell=True, check=True, cwd=script_dir)

        if stdout_option not in [None, subprocess.DEVNULL]:
            stdout_option.close()
        print(f"Start service {service_script} succeeded!")
        

    def _start_services_sequentially(self, services: List[Dict]):
        """
        按顺序启动多个服务模块。

        :param services: 服务列表，每个服务是一个字典
        """
        for service in services:
            print(f"strat the service: {service}")
            try:
                self._run_service(service_script = service["script"],
                                 conda_env_path = service["conda_env"],
                                 args= service["args"],
                                 use_python = service.get("use_python", False),
                                 run_in_background = service.get("run_in_background", False),
                                 is_base = service.get("is_base", False),
                                 log_file = service.get("log_file", None)
                                 )
                print(f"Service {service} started successfully.")
            except Exception as e:
                print(f"Service failed with error: {e}")
    
    def _init_opt_services(self):
        """启动可选服务"""
        if self.opt_services :
            self._start_services_sequentially(self.opt_services)
        else:
            print("No additional external server need to be start")

    def _init_base_services(self):
        """启动基础服务"""
        self._start_services_sequentially(self.base_services)
    
    def _stop_service(self):
        """
        在 ServiceManager 对象析构时，终止所有后台进程。
        """
        # 终止可选功能的后台进程
        for process in self.opt_processes:
            if process.poll() is None:  # 如果进程仍在运行
                print(f"Terminating opt process {process.pid}")
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)  # 终止整个进程组
        
        # 终止基本功能的后台进程
        for process in self.base_processes:
            if process.poll() is None:  # 如果进程仍在运行
                print(f"Terminating base process {process.pid}")
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)  # 终止整个进程组

        print("ServiceManager cleaned up and all background services are stopped.") 
                
    def __del__(self):
        self._stop_service()
        
    def _show(self):
        for p in self.base_processes:
            print(f"base pid: {p.pid} {p}")
        for p in self.opt_processes:
            print(f"opt pid: {p.pid} {p}")
 
 
 
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
    manager = ServiceManager()
    manager.init()
    input("enter1")
    manager._show()
    input("enter2")
    print("Now service initialized")

if __name__ == "__main__":
    main()
