# Project:      Agent
# Author:       yomu
# Time:         2025/01/06
# Version:      2.0
# Description:  重构版内部模块管理器

"""
重构版内部模块管理器

用于启动agent内部模块，在当前进程环境(即agent的进程环境)中运行

运行前请设置环境变量：
    export PYTHONPATH=${AGENT_HOME}:$PYTHONPATH

支持的模块类型：
1. LLM: ollama agent (直接使用Langchain的ChatOllama)
2. TTS: GPTSoVits agent, CosyVoice agent  
3. STT: SenseVoice agent
"""

import os
import yaml
import signal
import subprocess
from threading import Lock
from typing import List, Dict, Tuple, Any, Optional
from dotenv import dotenv_values

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config

from ..exceptions import (
    ModuleError, ModuleStartupError, ModuleLoadError, 
    ModuleConfigError, ModuleStopError, ModuleNotFoundError
)
from ..utils import (
    validate_module_config, ModuleLoader, ModuleHealthChecker, 
    DependencyResolver, dynamic_import_module
)


class InternalModuleManager:
    """
    内部模块管理器 - 重构版
    
    负责管理启动和关闭 AI agent的各内部模块
    (如各种功能的外部服务器的客户端agent)
    
    主要功能：
    - 模块启动和停止管理
    - 依赖关系解析
    - 健康检查
    - 配置验证
    - 线程安全操作
    
    方法分类：
    - init系列: 初始化和启动模块
    - start系列: 启动模块的内部实现
    - stop系列: 停止模块
    - restart系列: 重启模块
    - list系列: 获取模块信息
    - health系列: 健康检查
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化内部模块管理器
        
        Args:
            config_path: 配置文件路径，如果未提供则从环境变量读取
        """
        self.logger = setup_logger(name="InternalModule", log_path="InternalModule")
        
        # 加载环境变量和配置
        try:
            env_file_path = "Init/InternalModuleInit/.env"
            if not os.path.exists(env_file_path):
                env_file_path = os.path.join(os.path.dirname(__file__), "../.env")
            
            self.env_vars = dotenv_values(env_file_path)
            self.config_path = config_path or self.env_vars.get("INIT_CONFIG_PATH", "")
            
            if not self.config_path:
                # 使用默认路径 - 更新为新的位置
                self.config_path = "${AGENT_HOME}/Init/InternalModuleInit/config.yml"
                self.logger.warning(f"No config path provided, using default: {self.config_path}")
            
            self.config: Dict = load_config(
                config_path=self.config_path, 
                config_name='internal_modules', 
                logger=self.logger
            )
            
            # 验证配置
            validate_module_config(self.config, self.logger)
            
            self.support_modules: List[str] = self.config.get('support_modules', [])
            
        except Exception as e:
            self.logger.error(f"Failed to initialize configuration: {str(e)}")
            raise ModuleConfigError(f"Configuration initialization failed: {str(e)}") from e
        
        # 线程安全锁
        self.lock = Lock()
        
        # 模块存储
        self.base_processes: List[Tuple[str, Any]] = []      # 基础模块
        self.optional_processes: List[Tuple[str, Any]] = []  # 可选模块
        
        # 工具组件
        self.module_loader = ModuleLoader(self.logger)
        self.health_checker = ModuleHealthChecker(self.logger)
        self.dependency_resolver = DependencyResolver(self.logger)
        
        # 初始化依赖关系（如果配置中有定义）
        self._init_dependencies()
        
        self.logger.info("InternalModuleManager initialized successfully")
    
    def _init_dependencies(self):
        """从配置初始化模块依赖关系"""
        dependencies_config = self.config.get('dependencies', {})
        if dependencies_config:
            self.dependency_resolver.add_dependencies(dependencies_config)
            self.logger.info(f"Loaded {len(dependencies_config)} dependency relationships")
    
    # ================================
    # 初始化和启动方法
    # ================================
    
    def init_modules(self) -> Tuple[bool, List[str], List[str], List[str], List[str]]:
        """
        初始化启动内部服务模块
        
        Returns:
            Tuple[bool, List[str], List[str], List[str], List[str]]:
            (是否全部启动成功, 成功的base模块, 失败的base模块, 成功的optional模块, 失败的optional模块)
        """
        try:
            self.logger.info("Starting module initialization...")
            
            # 启动基础模块
            ok1, base_success, base_fail = self._init_base_modules()
            
            # 启动可选模块
            ok2, opt_success, opt_fail = self._init_optional_modules()
            
            # 记录启动结果
            total_success = len(base_success) + len(opt_success)
            total_fail = len(base_fail) + len(opt_fail)
            
            self.logger.info(
                f"Module initialization completed. "
                f"Success: {total_success}, Failed: {total_fail}"
            )
            
            if base_fail:
                self.logger.error(f"Failed base modules: {base_fail}")
            if opt_fail:
                self.logger.warning(f"Failed optional modules: {opt_fail}")
            
            return (ok1 and ok2, base_success, base_fail, opt_success, opt_fail)
            
        except Exception as e:
            self.logger.error(f"Module initialization failed: {str(e)}")
            raise ModuleStartupError("INITIALIZATION", str(e)) from e
    
    def _init_base_modules(self) -> Tuple[bool, List[str], List[str]]:
        """启动基础内部功能模块"""
        modules = self._get_modules(isBaseModules=True)
        return self._start_modules_sequentially(modules, isBaseModules=True)
    
    def _init_optional_modules(self) -> Tuple[bool, List[str], List[str]]:
        """启动可选内部功能模块"""
        modules = self._get_modules(isBaseModules=False)
        return self._start_modules_sequentially(modules, isBaseModules=False)
    
    # ================================
    # 模块启动相关方法
    # ================================
    
    def _get_modules(self, isBaseModules: bool) -> List[Tuple[str, str]]:
        """
        获取要启动的模块列表
        
        Args:
            isBaseModules: True为基础模块，False为可选模块
            
        Returns:
            List[Tuple[str, str]]: [(module_name, module_path), ...]
        """
        modules_key = "base_modules" if isBaseModules else "optional_modules"
        modules = self.config.get(modules_key, [])
        
        if not modules:
            if isBaseModules:
                raise ModuleConfigError(
                    f"Base modules configuration is empty. Please check {self.config_path}"
                )
            else:
                self.logger.info("No optional modules configured")
                return []
        
        result = []
        for module in modules:
            if len(module) == 1:
                module_name = list(module.keys())[0]
                module_path = list(module.values())[0]
                result.append((module_name, module_path))
            else:
                raise ModuleConfigError(
                    f"Module {module} contains more than one entry. "
                    "Each module should have exactly one name-path pair."
                )
        
        return result
    
    def _start_modules_sequentially(self, modules: List[Tuple[str, str]], 
                                  isBaseModules: bool) -> Tuple[bool, List[str], List[str]]:
        """
        按依赖关系顺序启动模块
        
        Args:
            modules: 模块列表
            isBaseModules: 是否为基础模块
            
        Returns:
            Tuple[bool, List[str], List[str]]: (全部成功, 成功列表, 失败列表)
        """
        if not modules:
            return True, [], []
        
        module_names = [name for name, _ in modules]
        module_dict = dict(modules)
        
        try:
            # 解析启动顺序
            ordered_names = self.dependency_resolver.resolve_startup_order(module_names)
            
            success: List[str] = []
            fail: List[str] = []
            
            for module_name in ordered_names:
                module_path = module_dict[module_name]
                try:
                    if self._start_single_module((module_name, module_path), isBaseModules):
                        success.append(module_name)
                        self.logger.info(f"Successfully started {module_name}")
                    else:
                        fail.append(module_name)
                        self.logger.error(f"Failed to start {module_name}")
                        
                        # 如果是基础模块启动失败，考虑是否继续
                        if isBaseModules:
                            self.logger.warning(
                                f"Base module {module_name} failed to start, continuing with remaining modules"
                            )
                            
                except Exception as e:
                    fail.append(module_name)
                    self.logger.error(f"Exception while starting {module_name}: {str(e)}")
            
            module_type = "base" if isBaseModules else "optional"
            self.logger.info(
                f"Finished starting {module_type} modules. "
                f"Success: {len(success)}, Failed: {len(fail)}"
            )
            
            return (len(fail) == 0, success, fail)
            
        except Exception as e:
            self.logger.error(f"Error in sequential module startup: {str(e)}")
            return False, [], module_names
    
    def _start_single_module(self, module: Tuple[str, str], isBaseModule: bool) -> bool:
        """
        启动单个内部服务模块
        
        Args:
            module: (module_name, module_path)
            isBaseModule: 是否为基础模块
            
        Returns:
            bool: 是否启动成功
        """
        module_name, module_path = module
        
        # 检查是否为支持的模块
        if module_name not in self.support_modules:
            self.logger.error(f"Unsupported module: {module_name}")
            return False
        
        # 检查是否已经启动
        if self._check_module_is_started(module_name):
            self.logger.warning(f"Module {module_name} is already started")
            return True
        
        try:
            self.logger.info(f"Starting module: {module_name} from {module_path}")
            
            # 使用模块加载器创建实例
            agent = dynamic_import_module(module_name, module_path, self.logger)
            
            # 添加到相应的列表
            with self.lock:
                if isBaseModule:
                    self.base_processes.append((module_name, agent))
                else:
                    self.optional_processes.append((module_name, agent))
            
            self.logger.info(f"Successfully started module: {module_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start module {module_name}: {str(e)}")
            return False
    
    # ================================
    # 模块停止相关方法
    # ================================
    
    def stop_single_module(self, module: str) -> bool:
        """停止单个可选模块（不包括基础模块）"""
        return self._stop_single_module_aux(module, self.optional_processes, isBaseModule=False)
    
    def _stop_single_module(self, module: str, isBaseModule: bool) -> bool:
        """停止单个模块（内部使用）"""
        processes = self.base_processes if isBaseModule else self.optional_processes
        return self._stop_single_module_aux(module, processes, isBaseModule=isBaseModule)
    
    def _stop_single_module_aux(self, module: str, processes: List[Tuple[str, Any]], 
                              isBaseModule: bool) -> bool:
        """
        停止单个模块的辅助方法
        
        Args:
            module: 模块名称
            processes: 模块进程列表
            isBaseModule: 是否为基础模块
            
        Returns:
            bool: 是否成功停止
        """
        module_type = "base" if isBaseModule else "optional"
        started_modules = {module_name for module_name, _ in processes}
        
        if module not in started_modules:
            self.logger.info(f"Module {module} ({module_type}) is not running")
            return False
        
        self.logger.info(f"Stopping {module_type} module: {module}")
        
        try:
            # 获取依赖于此模块的其他模块
            dependents = self.dependency_resolver.get_dependents(module)
            if dependents:
                running_dependents = [dep for dep in dependents if self._check_module_is_started(dep)]
                if running_dependents:
                    self.logger.warning(
                        f"Module {module} has running dependents: {running_dependents}. "
                        "Consider stopping them first."
                    )
            
            # 停止模块
            with self.lock:
                for i, (module_name, instance) in enumerate(processes):
                    if module_name == module:
                        # 如果模块有清理方法，调用它
                        if hasattr(instance, 'cleanup'):
                            try:
                                instance.cleanup()
                                self.logger.debug(f"Called cleanup method for {module}")
                            except Exception as e:
                                self.logger.warning(f"Cleanup method failed for {module}: {str(e)}")
                        
                        # 从列表中移除
                        processes.pop(i)
                        break
            
            self.logger.info(f"Successfully stopped {module_type} module: {module}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping module {module}: {str(e)}")
            return False
    
    def _stop_modules(self, modules: List[str], isBaseModule: bool) -> Tuple[bool, List[str], List[str]]:
        """批量停止模块"""
        if not modules:
            return True, [], []
        
        # 解析停止顺序（与启动顺序相反）
        try:
            ordered_modules = self.dependency_resolver.resolve_shutdown_order(modules)
        except Exception as e:
            self.logger.warning(f"Failed to resolve shutdown order: {str(e)}. Using original order.")
            ordered_modules = modules
        
        success: List[str] = []
        fail: List[str] = []
        
        for module in ordered_modules:
            if self._stop_single_module(module, isBaseModule=isBaseModule):
                success.append(module)
            else:
                fail.append(module)
        
        module_type = "base" if isBaseModule else "optional"
        self.logger.info(f"Stopped {module_type} modules - Success: {success}, Failed: {fail}")
        
        return len(fail) == 0, success, fail
    
    def stop_optional_modules(self) -> Tuple[bool, List[str], List[str]]:
        """停止所有可选模块"""
        self.logger.info("Stopping all optional modules...")
        if not self.optional_processes:
            self.logger.info("No optional modules running")
            return True, [], []
        
        modules_to_stop = [module for module, _ in self.optional_processes]
        return self._stop_modules(modules_to_stop, isBaseModule=False)
    
    def _stop_base_modules(self) -> Tuple[bool, List[str], List[str]]:
        """停止所有基础模块"""
        self.logger.info("Stopping all base modules...")
        if not self.base_processes:
            self.logger.info("No base modules running")
            return True, [], []
        
        modules_to_stop = [module for module, _ in self.base_processes]
        return self._stop_modules(modules_to_stop, isBaseModule=True)
    
    def stop_select_modules(self, modules: List[str]) -> Tuple[bool, List[str], List[str]]:
        """停止选择的可选模块"""
        started_optional_modules = {module for module, _ in self.optional_processes}
        modules_to_stop = [module for module in modules if module in started_optional_modules]
        
        if not modules_to_stop:
            self.logger.info("No specified optional modules are running")
            return True, [], []
        
        return self._stop_modules(modules_to_stop, isBaseModule=False)
    
    def _stop_all_modules(self):
        """停止所有模块"""
        self.logger.info("Stopping all modules...")
        
        # 先停止可选模块，再停止基础模块
        opt_ok, _, opt_fail = self.stop_optional_modules()
        base_ok, _, base_fail = self._stop_base_modules()
        
        if (opt_ok and base_ok) or (base_ok and not opt_fail):
            self.logger.info("All modules stopped successfully")
        else:
            self.logger.warning("Some modules failed to stop")
        
        # 强制清理任何残留的内部模块进程
        self._force_cleanup_module_processes()
    
    def _force_cleanup_module_processes(self):
        """强制清理内部模块相关的进程"""
        try:
            self.logger.info("Checking for remaining module processes...")
            
            # 定义需要清理的模块进程名称模式
            module_patterns = [
                'OllamaAgent',
                'GPTSoVitsAgent', 
                'SenseVoiceAgent',
                'ChatModule',
                'VisionAgent',
                'PromptOptimizer',
                'UserTextInputProcessModule'
            ]
            
            # 查找并终止相关进程
            for pattern in module_patterns:
                try:
                    # 使用 pgrep 查找匹配的进程
                    result = subprocess.run(
                        ['pgrep', '-f', pattern],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        pids = result.stdout.strip().split('\n')
                        for pid in pids:
                            if pid.isdigit():
                                try:
                                    # 先尝试优雅终止
                                    os.kill(int(pid), signal.SIGTERM)
                                    self.logger.info(f"Sent SIGTERM to {pattern} process {pid}")
                                    
                                    # 等待一下，然后检查是否还存在
                                    import time
                                    time.sleep(1)
                                    
                                    # 如果还存在，强制终止
                                    try:
                                        os.kill(int(pid), 0)  # 检查进程是否仍存在
                                        os.kill(int(pid), signal.SIGKILL)
                                        self.logger.info(f"Force killed {pattern} process {pid}")
                                    except ProcessLookupError:
                                        # 进程已经不存在了
                                        pass
                                        
                                except (ProcessLookupError, ValueError) as e:
                                    self.logger.debug(f"Process {pid} for {pattern} not found or invalid: {e}")
                                except Exception as e:
                                    self.logger.warning(f"Failed to terminate {pattern} process {pid}: {e}")
                                    
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"Timeout while searching for {pattern} processes")
                except Exception as e:
                    self.logger.debug(f"Error searching for {pattern} processes: {e}")
            
            # 额外检查特定端口的进程
            self._cleanup_port_processes()
            
        except Exception as e:
            self.logger.error(f"Error during force cleanup: {e}")
    
    def _cleanup_port_processes(self):
        """清理占用特定端口的进程"""
        # 定义内部模块使用的端口
        module_ports = [20030, 20060, 20020, 20031, 20032, 20033]
        
        for port in module_ports:
            try:
                # 使用 lsof 或 netstat 查找占用端口的进程
                result = subprocess.run(
                    ['lsof', '-ti', f':{port}'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid.isdigit():
                            try:
                                os.kill(int(pid), signal.SIGTERM)
                                self.logger.info(f"Terminated process {pid} using port {port}")
                            except ProcessLookupError:
                                pass
                            except Exception as e:
                                self.logger.warning(f"Failed to terminate process {pid} on port {port}: {e}")
                                
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # lsof 不存在，尝试 netstat
                try:
                    result = subprocess.run(
                        ['netstat', '-tulpn'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if f':{port}' in line and 'LISTEN' in line:
                                # 提取PID
                                parts = line.split()
                                if len(parts) >= 7:
                                    pid_info = parts[-1]
                                    if '/' in pid_info:
                                        pid = pid_info.split('/')[0]
                                        if pid.isdigit():
                                            try:
                                                os.kill(int(pid), signal.SIGTERM)
                                                self.logger.info(f"Terminated process {pid} using port {port}")
                                            except ProcessLookupError:
                                                pass
                                            except Exception as e:
                                                self.logger.warning(f"Failed to terminate process {pid} on port {port}: {e}")
                except Exception as e:
                    self.logger.debug(f"Error checking port {port}: {e}")
    
    # ================================
    # 模块重启相关方法
    # ================================
    
    def restart_single_module(self, module: str) -> bool:
        """重启单个可选模块"""
        return self._restart_single_module_aux(module, isBaseModule=False)
    
    def _restart_single_module_aux(self, module: str, isBaseModule: bool) -> bool:
        """重启模块的辅助方法"""
        if not self._check_module_is_started(module):
            self.logger.info(f"Module {module} is not running, cannot restart")
            return False
        
        self.logger.info(f"Restarting module: {module}")
        
        # 停止模块
        if not self._stop_single_module(module, isBaseModule):
            self.logger.error(f"Failed to stop module {module} during restart")
            return False
        
        # 重新启动模块
        try:
            _, _, module_path = self._get_module_config_by_name(module)
            if not module_path:
                self.logger.error(f"Cannot find configuration for module {module}")
                return False
            
            if self._start_single_module((module, module_path), isBaseModule):
                self.logger.info(f"Successfully restarted module: {module}")
                return True
            else:
                self.logger.error(f"Failed to restart module {module}")
                return False
                
        except Exception as e:
            self.logger.error(f"Exception during restart of module {module}: {str(e)}")
            return False
    
    def restart_optional_modules(self) -> Tuple[bool, List[str], List[str]]:
        """重启所有可选模块"""
        modules_to_restart = [module for module, _ in self.optional_processes]
        return self._restart_modules(modules_to_restart, isBaseModule=False)
    
    def restart_select_modules(self, modules: List[str]) -> Tuple[bool, List[str], List[str]]:
        """重启选择的可选模块"""
        optional_modules = {module for module, _ in self.optional_processes}
        modules_to_restart = [module for module in modules if module in optional_modules]
        
        if not modules_to_restart:
            self.logger.info("No specified optional modules are running")
            return True, [], []
        
        return self._restart_modules(modules_to_restart, isBaseModule=False)
    
    def _restart_modules(self, modules: List[str], isBaseModule: bool) -> Tuple[bool, List[str], List[str]]:
        """批量重启模块"""
        success: List[str] = []
        fail: List[str] = []
        
        for module in modules:
            if self._restart_single_module_aux(module, isBaseModule=isBaseModule):
                success.append(module)
            else:
                fail.append(module)
        
        module_type = "base" if isBaseModule else "optional"
        self.logger.info(f"Restarted {module_type} modules - Success: {success}, Failed: {fail}")
        
        return len(fail) == 0, success, fail
    
    # ================================
    # 信息查询方法
    # ================================
    
    def list_started_modules(self, isBaseModule: Optional[bool] = None) -> List[str]:
        """
        获取已启动的模块列表
        
        Args:
            isBaseModule: None=所有, True=仅基础模块, False=仅可选模块
            
        Returns:
            List[str]: 模块名称列表
        """
        if isBaseModule is None:
            return ([name for name, _ in self.base_processes] + 
                   [name for name, _ in self.optional_processes])
        elif isBaseModule:
            return [name for name, _ in self.base_processes]
        else:
            return [name for name, _ in self.optional_processes]
    
    def get_module_instance(self, module_name: str) -> Optional[Any]:
        """获取模块实例"""
        for name, instance in self.base_processes + self.optional_processes:
            if name == module_name:
                return instance
        return None
    
    def get_module_status(self) -> Dict[str, Any]:
        """获取模块状态摘要"""
        base_health = self.health_checker.get_health_summary(self.base_processes)
        optional_health = self.health_checker.get_health_summary(self.optional_processes)
        
        return {
            "base_modules": {
                "total": len(self.base_processes),
                "healthy": base_health["healthy_count"],
                "unhealthy": base_health["unhealthy_count"],
                "modules": base_health["healthy_modules"],
                "unhealthy_details": base_health["unhealthy_modules"]
            },
            "optional_modules": {
                "total": len(self.optional_processes),
                "healthy": optional_health["healthy_count"],
                "unhealthy": optional_health["unhealthy_count"],
                "modules": optional_health["healthy_modules"],
                "unhealthy_details": optional_health["unhealthy_modules"]
            },
            "overall_healthy": base_health["overall_healthy"] and optional_health["overall_healthy"]
        }
    
    def _get_module_config_by_name(self, module_name: str) -> Tuple[bool, str, str]:
        """
        通过模块名获取模块配置信息
        
        Returns:
            Tuple[bool, str, str]: (是否为基础模块, 模块名, 模块路径)
        """
        # 搜索基础模块
        base_modules = self._get_modules(isBaseModules=True)
        for name, path in base_modules:
            if name == module_name:
                return True, name, path
        
        # 搜索可选模块
        optional_modules = self._get_modules(isBaseModules=False)
        for name, path in optional_modules:
            if name == module_name:
                return False, name, path
        
        return False, module_name, ""
    
    def _check_module_is_started(self, module: str) -> bool:
        """检查模块是否已启动"""
        for name, _ in self.base_processes + self.optional_processes:
            if name == module:
                return True
        return False
    
    # ================================
    # 健康检查方法
    # ================================
    
    def check_module_health(self, module_name: str) -> Tuple[bool, str]:
        """检查单个模块健康状态"""
        instance = self.get_module_instance(module_name)
        if instance is None:
            return False, "Module not found or not running"
        
        return self.health_checker.check_module_health(module_name, instance)
    
    def check_all_modules_health(self) -> Dict[str, Tuple[bool, str]]:
        """检查所有模块健康状态"""
        all_modules = self.base_processes + self.optional_processes
        return self.health_checker.check_modules_health(all_modules)
    
    # ================================
    # 调试和显示方法
    # ================================
    
    def _show(self):
        """显示当前模块状态"""
        base_modules = self.list_started_modules(isBaseModule=True)
        optional_modules = self.list_started_modules(isBaseModule=False)
        
        self.logger.info(f"Started base modules: {base_modules}")
        self.logger.info(f"Started optional modules: {optional_modules}")
        
        # 显示健康状态
        status = self.get_module_status()
        self.logger.info(f"Base modules health: {status['base_modules']}")
        self.logger.info(f"Optional modules health: {status['optional_modules']}")
    
    def get_dependency_info(self) -> Dict[str, List[str]]:
        """获取依赖关系信息"""
        return self.dependency_resolver.get_dependency_graph()
    
    # ================================
    # 清理方法
    # ================================
    
    def __del__(self):
        """析构方法，清理所有模块"""
        try:
            self._stop_all_modules()
            self.logger.info("InternalModuleManager cleaned up")
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")


if __name__ == "__main__":
    """测试代码"""
    try:
        manager = InternalModuleManager()
        success, base_success, base_fail, opt_success, opt_fail = manager.init_modules()
        
        print(f"Initialization result: {success}")
        print(f"Base modules - Success: {base_success}, Failed: {base_fail}")
        print(f"Optional modules - Success: {opt_success}, Failed: {opt_fail}")
        
        manager._show()
        
        # 测试健康检查
        health_status = manager.check_all_modules_health()
        print(f"Health status: {health_status}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
