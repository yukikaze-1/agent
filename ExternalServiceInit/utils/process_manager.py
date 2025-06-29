"""
进程管理模块
"""

import os
import signal
import subprocess
import shlex
from typing import List, Dict, Tuple, Optional, Union, Any
from subprocess import Popen
import logging
from ..exceptions import ServiceStartupError, ServiceStopError


class ProcessManager:
    """进程管理器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def create_process(self, 
                      service_config: Dict,
                      log_dir: str) -> Tuple[bool, Tuple[str, int]]:
        """
        创建服务进程
        
        :param service_config: 服务配置
        :param log_dir: 日志目录
        :return: (成功标志, (服务名, PID))
        """
        service_name = service_config["service_name"]
        service_script = service_config["script"]
        conda_env_path = service_config["conda_env"]
        args = service_config.get("args", [])
        use_python = service_config.get("use_python", False)
        run_in_background = service_config.get("run_in_background", True)
        log_file = service_config.get("log_file")
        
        try:
            # 准备日志文件
            stdout_option, stderr_option, stdin_option = self._prepare_log_files(
                service_name, log_file, log_dir, run_in_background
            )
            
            # 准备工作目录
            script_dir = os.path.dirname(service_script) or "/home/yomu"
            
            # 创建进程
            if use_python:
                process = self._create_python_process(
                    service_name, service_script, conda_env_path, args,
                    run_in_background, script_dir,
                    stdout_option, stderr_option, stdin_option
                )
            else:
                process = self._create_shell_process(
                    service_name, service_script, args,
                    run_in_background, script_dir,
                    stdout_option, stderr_option, stdin_option
                )
            
            # 清理文件句柄
            self._cleanup_file_handles(stdout_option, stderr_option)
            
            if process:
                self.logger.info(f"Process created for service '{service_name}' with PID: {process.pid}")
                return True, (service_name, process.pid)
            else:
                return False, (service_name, -1)
                
        except Exception as e:
            self.logger.error(f"Failed to create process for service '{service_name}': {e}")
            raise ServiceStartupError(service_name, str(e))
    
    def _prepare_log_files(self, service_name: str, log_file: Optional[str], 
                          log_dir: str, run_in_background: bool) -> Tuple[Any, Any, Any]:
        """准备日志文件句柄"""
        if not log_file:
            self.logger.warning(f"Service '{service_name}' starts with no logfile")
            return subprocess.DEVNULL, subprocess.DEVNULL, subprocess.DEVNULL
        
        log_file_path = os.path.join(log_dir, log_file)
        self.logger.info(f"Start service '{service_name}' with logfile: '{log_file_path}'")
        
        if run_in_background:
            stdout = stderr = open(log_file_path, "a")
            stdin = subprocess.DEVNULL
        else:
            stdout = stderr = stdin = None
            
        return stdout, stderr, stdin
    
    def _create_python_process(self, service_name: str, service_script: str,
                             conda_env_path: str, args: List[str],
                             run_in_background: bool, script_dir: str,
                             stdout, stderr, stdin) -> Optional[Popen]:
        """创建Python进程"""
        python_path = os.path.join(conda_env_path, "bin", "python")
        
        if not os.path.exists(python_path):
            raise ServiceStartupError(
                service_name,
                f"Python executable not found in conda environment: {python_path}"
            )
        
        self.logger.info(f"Starting service '{service_name}' at '{service_script}' with Python '{python_path}'")
        
        if run_in_background:
            return subprocess.Popen(
                args=[python_path, service_script] + args,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                preexec_fn=os.setsid,
                close_fds=True,
                cwd=script_dir
            )
        else:
            # 前台运行
            subprocess.run(
                args=[python_path, service_script] + args,
                check=True,
                cwd=script_dir
            )
            return None
    
    def _create_shell_process(self, service_name: str, service_script: str,
                            args: List[str], run_in_background: bool,
                            script_dir: str, stdout, stderr, stdin) -> Optional[Popen]:
        """创建Shell进程"""
        self.logger.info(f"Starting service '{service_name}' using system shell")
        
        command_list = [service_script] + args
        command_str = ' '.join(shlex.quote(arg) for arg in command_list)
        
        if run_in_background:
            return subprocess.Popen(
                args=command_str,
                shell=True,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                preexec_fn=os.setsid,
                close_fds=True,
                cwd=script_dir
            )
        else:
            subprocess.run(command_str, shell=True, check=True, cwd=script_dir)
            return None
    
    def _cleanup_file_handles(self, stdout, stderr):
        """清理文件句柄"""
        if stdout not in [None, subprocess.DEVNULL] and stdout == stderr:
            # 如果stdout和stderr是同一个文件对象，只关闭一次
            stdout.close()
        else:
            if stdout not in [None, subprocess.DEVNULL]:
                stdout.close()
            if stderr not in [None, subprocess.DEVNULL]:
                stderr.close()
    
    def terminate_process(self, process: Popen, service_name: str, 
                         graceful_timeout: int = 10) -> bool:
        """
        终止进程
        
        :param process: 进程对象
        :param service_name: 服务名称
        :param graceful_timeout: 优雅关闭超时时间
        :return: 是否成功终止
        """
        if process.poll() is not None:
            self.logger.info(f"Process for service '{service_name}' already terminated")
            return True
        
        try:
            self.logger.info(f"Terminating process for service '{service_name}': {process.pid}")
            
            # 首先尝试优雅关闭
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            
            # 等待进程终止
            try:
                process.wait(timeout=graceful_timeout)
                self.logger.info(f"Process for service '{service_name}' terminated gracefully")
                return True
            except subprocess.TimeoutExpired:
                # 强制关闭
                self.logger.warning(f"Force killing process for service '{service_name}'")
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait()
                return True
                
        except (OSError, ProcessLookupError) as e:
            self.logger.error(f"Failed to terminate process for service '{service_name}': {e}")
            raise ServiceStopError(service_name, str(e))
    
    def cleanup_existing_processes(self, service_name: str, script_path: str) -> bool:
        """
        清理已存在的同名服务进程
        
        :param service_name: 服务名称
        :param script_path: 脚本路径
        :return: 是否有进程被清理
        """
        cleaned = False
        try:
            # 查找匹配的进程
            cmd = f"pgrep -f '{script_path}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                self.logger.info(f"Found {len(pids)} existing {service_name} processes")
                
                for pid in pids:
                    try:
                        pid_num = int(pid.strip())
                        self.logger.info(f"Terminating existing {service_name} process {pid_num}")
                        os.kill(pid_num, signal.SIGTERM)
                        cleaned = True
                    except (ValueError, ProcessLookupError, PermissionError) as e:
                        self.logger.warning(f"Failed to terminate PID {pid}: {e}")
                        
                # 等待进程终止
                if cleaned:
                    import time
                    time.sleep(2)
                    
                    # 强制杀死仍在运行的进程
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if result.returncode == 0 and result.stdout.strip():
                        remaining_pids = result.stdout.strip().split('\n')
                        for pid in remaining_pids:
                            try:
                                pid_num = int(pid.strip())
                                self.logger.warning(f"Force killing {service_name} process {pid_num}")
                                os.kill(pid_num, signal.SIGKILL)
                            except (ValueError, ProcessLookupError, PermissionError) as e:
                                self.logger.warning(f"Failed to force kill PID {pid}: {e}")
                        
        except Exception as e:
            self.logger.warning(f"Error during process cleanup for {service_name}: {e}")
            
        return cleaned
