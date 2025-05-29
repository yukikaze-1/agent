# Project:      Agent
# Author:       yomu
# Time:         2024/11/27
# Version:      0.1
# Description:  agent internal module initialize

"""
    用于启动agent内部模块
    在当前进程环境(即agent的进程环境)中运行
    
    运行前请 export PYTHONPATH=/home/yomu/agent:$PYTHONPATH
    
    1. LLM
        1) ollama agent [注：ollama agent直接使用Langchain的ChatOllama即可]
    2. TTS
        1) GPTSoVits agent *
        2) CosyVoice agent
    3. STT
        1) SenseVoice agent *
    4. 
"""

import os
import yaml
import importlib
import logging
from threading import Lock
from typing import List, Dict, Tuple, Any, Optional
from dotenv import dotenv_values

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config


class InternalModuleManager:
    """
        负责管理启动和关闭 AI agent的各内部模块
        (如各种功能的外部服务器的客户端agent)
        
        没有'_'前缀的方法可以调用
        
        有'_'前缀的方法请不要调用！！！
        
        start系列函数：负责启动module
            - _start_single_module
            - _start_modules_sequentially
            
        init系列函数：负责初始化module配置
            - init_modules     *****(请务必在实例化后调用!!!)*****
                                返回:   是否全部启动成功
                                        启动成功的base内部服务模块名字，启动失败的base内部服务模块名字
                                        启动成功的optional内部服务模块名字，启动失败的optional内部服务模块名字
                                        Tuple[bool, List[str], List[str] , List[str], List[str]]
                                
            - _init_base_modules
            - _init_optional_modules
            
        stop系列函数： 负责停止已启动的module
            - stop_single_module
            - stop_optional_modules
            - stop_select_modules
            - _stop_single_module
            - _stop_single_module_aux
            - _stop_modules
            - _stop_base_modules   
            - _stop_select_modules
            - _stop_all_modules
        
        restart系列函数： 负责重启已启动的module
            - restart_select_modules
            - restart_optional_modules
            - restart_single_module
            - _restart_single_module_aux
            - _restart_single_module
            - _restart_modules
            - _restart_base_modules
            - _restart_select_modules   
            
        list系列函数：负责得到module的各种信息
            - list_started_modules
            
        其他函数:
            - _create_agent
            - _get_modules
            - _get_module_config_by_name
            - _check_module_is_started
            - _show
    """
    def __init__(self):
        self.logger = setup_logger(name="InternalModule", log_path="InternalModule")
        
        self.env_vars = dotenv_values("Init/.env")
        self.config_path = self.env_vars.get("INIT_CONFIG_PATH","")
        self.config: Dict = load_config(config_path=self.config_path, config_name='internal_modules', logger=self.logger)
        self.support_modules: List[str] = self.config.get('support_modules', [])
        
        # 用于锁修改已启动module对象列表的代码块
        self.lock = Lock()
        
        # 模块对象相关 
        self.base_processes: List[Tuple[str, Any]] = []    # 存放已启动的base内部服务模块名字和对象
        self.optional_processes: List[Tuple[str, Any]] = [] # 存放已启动的optional内部服务模块名字和对象

    
    def init_modules(self)->Tuple[bool, List[str], List[str] , List[str], List[str]]:
        """
        初始化启动 内部服务模块
        
        返回:
            是否全部启动成功
            启动成功的base内部服务模块名字，启动失败的base内部服务模块名字
            启动成功的optional内部服务模块名字，启动失败的optional内部服务模块名字
        """
        ok1, _base_success, _base_fail = self._init_base_modules()
        ok2, _opt_success, _opt_fail =  self._init_optional_modules()
        
        return (ok1 and ok2, _base_success, _base_fail, _opt_success, _opt_fail)     

    def _get_module_config_by_name(self,module_name: str)->Tuple[bool, str, str]:
        """通过模块名字获取模型信息
        
        返回：
            是否是base module, module_name, module_path
        """
        base_modules = self._get_modules(isBaseModules=True)
        if base_modules:
            for name, path in base_modules:
                if name == module_name:
                    return True, name, path
        
        optional_modules = self._get_modules(isBaseModules=False)
        if optional_modules:
            for name, path in optional_modules:
                if name == module_name:
                    return True, name, path 
        
        return (False, module_name, "")

    def _get_modules(self, isBaseModules:bool)->List[Tuple[str,str]]:
        """
            返回 要启动的[modules + module_path]列表
            
            :param isBase: True:base_modules False: optional_modules
            
            返回： 
                module_name,module_path
        """
        modules_key = "base_modules" if isBaseModules else "optional_modules"
        modules = self.config.get(modules_key, [])
        
        if not modules:
            if isBaseModules:
                raise ValueError(f"base modules is empty. Please check the {self.config_path}")
            else:
                return []
        
        ret = []    
        for module in modules:
            # 确保每个字典只有一个键值对
            if len(module) == 1:
                ret.append((list(module.keys())[0], list(module.values())[0]))
            else:
                raise ValueError(f"Module {module} contains more than one entry. Please check the config file.")
        
        return ret
    
    def _create_agent(self, module_name: str, module_path: str, *args, **kwargs)->Any:
        """
        动态加载模块并实例化类
        
        :param module_name: 模块名字符串 (例如 "GPTSoVitsAgent")
        :param module_path: 模块路径字符串 (例如 "Module.TTS.GPTSoVits.GPTSoVitsAgent")
        :param *args: 传递给类构造函数的位置参数
        :param **kwargs: 传递给类构造函数的关键字参数
        :return: 返回类实例
        """
        try:
            # 动态加载模块
            module = importlib.import_module(module_path)

            # 使用 getattr 获取类
            cls = getattr(module, module_name, None)
            if cls is None:
                raise ValueError(f"Class {module_name} not found in module {module_path}")

            # 实例化并返回对象
            return cls(*args, **kwargs)
        
        except ModuleNotFoundError as e:
            self.logger.error(f"Module {module_path} could not be found")
            raise ImportError(f"Module {module_path} could not be found") from e
        except AttributeError as e:
            self.logger.error(f"Module {module_path} does not contain class {module_name}")
            raise ValueError(f"Module {module_path} does not contain class {module_name}") from e
        except Exception as e:
            self.logger.error(f"Error in _create_agent: {str(e)}")
            raise

            
    def _init_base_modules(self)->Tuple[bool, List[str], List[str]]:
        """
        启动 base内部功能模块
        
        返回:
            是否全部启动成功,
            启动成功的内部base服务模块名字，启动失败的base内部服务模块名字  
        """
        return self._start_modules_sequentially(self._get_modules(isBaseModules=True), isBaseModules=True)
 
    def _init_optional_modules(self)->Tuple[bool,List[str],List[str]]:
        """
        启动 optional内部功能模块
            
        返回:
            是否全部启动成功,
            启动成功的optional内部服务模块名字，启动失败的optional内部服务模块名字
        """
        return  self._start_modules_sequentially(self._get_modules(isBaseModules=False), isBaseModules=False)
    
    def _start_single_module(self, module:Tuple[str,str], isBaseModule: bool)->bool:
        """
            单次启动 一个内部服务模块
            
            :param module: 应包含模型名字和模型路径,比如 [GPTSoVitsAgent, Module.TTS.GPTSoVits]
            :param isBaseModule: 是否是base module
            
            返回:
                是否启动成功
        """
        
        # 获取模块路径和类名
        module_name, module_path = module
        
        # 检查是否是受支持的模块
        if module_name not in self.support_modules:
            self.logger.error(f"Unknown module {module}")
            return False
        
        try:
            # 使用 _create_agent 动态加载模块
            agent = self._create_agent(module_name, module_path, logger=self.logger)
            # 将模块添加到相应的列表
            if isBaseModule:
                self.base_processes.append((module_name, agent))
                self.logger.info(f"Started base module {module}")
            else:
                self.optional_processes.append((module_name, agent))
                self.logger.info(f"Started optional module {module}")
            return True  # 成功启动模块后返回 True
        except Exception as e:
            self.logger.error(f"Failed to start module {module}: {e}")
            return False  # 如果发生异常，返回 False
        
    def _start_modules_sequentially(self,
                                   modules:List[Tuple[str,str]],
                                   isBaseModules: bool
                                   )->Tuple[bool, List[str], List[str]]:
        """
        顺序启动 内部功能模块
        
        :param modules: 要启动的模块列表。每个元素应包含模型名字和模型路径,比如GPTSoVitsAgent,Module.TTS.GPTSoVits
        :param isBaseModule: 是否是base module
        
        返回:
            是否全部启动成功,
            启动成功的any内部服务模块名字，启动失败的any内部服务模块名字
        """
        success:List[str] = []
        fail:List[str] = []
        
        for module in modules:
            if self._start_single_module(module, isBaseModule=isBaseModules):
                success.append(module[0])
            else:
                fail.append(module[0])
        
        return (len(fail) == 0, success, fail)

    def stop_single_module(self, module: str) -> bool:
        """
        终止单个 optional 内部服务模块（如果包含 base modules 则会忽略）。
        """
        return self._stop_single_module_aux(module, self.optional_processes, isBaseModule=False)
    
    def _stop_single_module(self, module: str, isBaseModule: bool) -> bool:
        """
        终止单个 Any 内部服务模块。
        """
        processes = self.base_processes if isBaseModule else self.optional_processes
        return self._stop_single_module_aux(module, processes, isBaseModule=isBaseModule)
    
    def _stop_single_module_aux(self, module: str, processes: List[Tuple[str,Any]], isBaseModule: bool) -> bool:
        """
        通用函数：终止单个Any内部服务模块。
        
        参数:
            module (str): 要停止的模块名称。
            processes (List[Tuple[str,Any]]): 对应模块的进程列表，如 self.base_processes 或 self.optional_processes。
            
        返回:
            bool: 是否成功停止模块。
        """
        module_type = "base" if isBaseModule else "optional"
        started_modules = {module_name for module_name, _ in processes}
        
        # 检查该模块是否已启动
        if module not in started_modules:
            self.logger.info(f"The {module_type} module {module} is not running. No need to stop it.")
            return False

        self.logger.info(f"Start stopping the running {module_type} module {module}...")
        
        # 从列表中移除对应的项（会导致模块被析构）
        # 锁住代码块，确保在多线程时不会有其他线程同时修改 processes 列表
        with self.lock:
            for item in processes:
                module_name, _ = item
                if module_name == module:
                    processes.remove(item)
                    break
        self.logger.info(f"Stopped the running {module_type} module {module}.")
        return True
    
    def _stop_modules(self, modules: List[str], isBaseModule: bool) -> Tuple[bool, List[str], List[str]]:
        success: List[str] = []
        fail: List[str] = []

        for module in modules:
            if self._stop_single_module(module, isBaseModule=isBaseModule):
                success.append(module)
            else:
                fail.append(module)
                
        self.logger.info(f"Stopped the {'base' if isBaseModule else 'optioanl'} modules successfully：\t{success}")
        if len(fail) > 0:
            self.logger.info(f"Stopped the {'base' if isBaseModule else 'optional'} modules failed：\t{fail}")

        return len(fail) == 0, success, fail
    
    def _stop_base_modules(self)->Tuple[bool,List[str],List[str]]:
        """终止 所有 base内部服务模块"""
        self.logger.info("Now starting to stop all the base modules...")
        modules_to_stop = [module for module, _ in self.base_processes]
        return self._stop_modules(modules_to_stop, isBaseModule=True)
        
    def stop_optional_modules(self)->Tuple[bool,List[str],List[str]]:
        """终止 所有 optional内部服务模块"""
        self.logger.info("InternalModuleManager is now stopping all the optional modules...")
        if not self.optional_processes:
            self.logger.info("No running optional modules. Do nothing.")
            return (False, [], [])
        modules_to_stop = [module for module, _ in self.optional_processes]
        return self._stop_modules(modules_to_stop, isBaseModule=False)
          
    def stop_select_modules(self,modules:List[str])->Tuple[bool,List[str],List[str]]:
        """
        终止 所有选择的optional内部服务模块
        
        注意： 若包含base内部服务模块,则会忽略这些base
        返回:
            是否全部stop成功，stop成功的module name，stop失败的module name
        """
        started_optioanal_modules = {module for module, _ in self.optional_processes}
        modules_to_stop = [module for module in modules if module in started_optioanal_modules]
        
        if not modules_to_stop:
            self.logger.info("No optional modules need to stop.Please check the param:modules")
            return (False, [], [])
        
        return self._stop_modules(modules_to_stop, isBaseModule=False)
    
    def _stop_select_modules(self,modules:List[str])->Tuple[bool,List[str],List[str]]:
        """终止 所有选择的Any内部服务模块"""
        
        # 获取 已启动的modules
        started_optional_modules = {module for module, _ in self.optional_processes}
        started_base_modules = {module for module, _ in self.base_processes}
        
        # 过滤出 要stop的且已启动的modules
        optional_modules_to_stop = [module for module in modules if module in started_optional_modules]
        base_modules_to_stop = [module for module in modules if module in started_base_modules]
        
        # 没有要stop的module
        if not optional_modules_to_stop and not base_modules_to_stop :
            self.logger.info("No module in param:modules is running.No need to stop them.Please check the param:modules")
            return (False, [], [])
        
        ok1, opt_success, opt_fail = self._stop_modules(optional_modules_to_stop, isBaseModule=False)
        ok2, base_success, base_fail = self._stop_modules(base_modules_to_stop, isBaseModule=True)
        
        return (ok1 and ok2, base_success + opt_success, base_fail + opt_fail)  
        
    def _stop_all_modules(self):
        """终止 所有所有内部服务模块"""
        ok1, _, opt_fail = self.stop_optional_modules()
        ok2, _, _ =self._stop_base_modules()
        if (ok1 and ok2) or (ok2 and not opt_fail):
            self.logger.info("InternalModuleManager cleaned up and all modules are stopped.")
        else:
            self.logger.info("Some modules failed to stop.")
     
    def _check_module_is_started(self,module:str)->bool:
        """检测 单个模块是否已经启动"""
        for name, _ in self.base_processes:
            if name == module:
                return True
        for name, _ in self.optional_processes:
            if name == module:
                return True
        return False
  
    def _restart_single_module_aux(self, module: str, isBaseModule: bool)->bool:
        """重启指定模块。如果模块未启动，则不会执行任何操作。"""
        # 检测该模块是否已经启动，若本身没启动，则不应该重启
        if not self._check_module_is_started(module):
            self.logger.info(f"模块: {module} 并未运行，无需重启。")
            return False

        self.logger.info(f"开始重启模块: {module}...")
        
        # 尝试停止模块
        if not self._stop_single_module(module, isBaseModule):
            self.logger.info(f"重启模块: {module} 失败.原因:停止该模块失败")
            return False
        
        # 尝试启动模块
        _, _, module_path = self._get_module_config_by_name(module_name=module)
        if not self._start_single_module((module, module_path), isBaseModule):
            self.logger.info(f"重启模块: {module} 失败.原因:启动该模块失败")
            return False

        self.logger.info(f"重启模块: {module} 成功")
        return True
    
    def _restart_single_module(self, module:str, isBaseModule:bool)->bool:
        """重启指定模块。如果模块未启动，则不会执行任何操作"""
        return self._restart_single_module_aux(module, isBaseModule=isBaseModule)
    
    def restart_single_module(self,module:str)->bool:
        """重启 单个optional模块
         
        注意： 若为base内部服务模块,则不会重启 
        """
        # 获取已启动的optional modules
        started_optional_modules = {module for module, _ in self.optional_processes}
        
        if module not in started_optional_modules:
            self.logger.info(f"模块: {module} 并未运行或是基础模块，无需重启。")
            return False

        return self._restart_single_module_aux(module, isBaseModule=False)
    
    def _restart_modules(self, modules: List[str], isBaseModule: bool)->Tuple[bool,List[str],List[str]]:
        """
        通用函数 重启部分modules
        
        返回:
            全部重启成功还是失败,重启成功的模块名字，重启失败的模块名字
        """
        success: List[str] = []
        fail: List[str] = []
        
        for module in modules:
            if self._restart_single_module(module, isBaseModule=isBaseModule):
                success.append(module)
            else:
                fail.append(module)
                
        self.logger.info(f"成功重启了基础模块：\n\t{success}")
        if fail:
            self.logger.info(f"基础模块重启失败：\n\t{fail}")
        return (len(fail) == 0, success, fail)
    
    def _restart_base_modules(self)->Tuple[bool,List[str],List[str]]:
        """
        重启 所有的base内部服务模块    

        返回:
            全部重启成功还是失败,重启成功的模块名字，重启失败的模块名字
        """
        modules_to_restart = [module for module, _ in self.base_processes]
        return self._restart_modules(modules_to_restart, isBaseModule=True)
    
    def restart_optional_modules(self)->Tuple[bool,List[str],List[str]]:
        """ 重启 所有的optional内部服务模块 
        
        返回:
            全部重启成功还是失败,重启成功的模块名字，重启失败的模块名字
        """
        modules_to_restart = [module for module, _ in self.optional_processes]
        return self._restart_modules(modules_to_restart, isBaseModule=False)
    
    def _restart_select_modules(self, modules:List[str])->Tuple[bool,List[str],List[str]]:
        """
        重启 选择的 Any 内部服务模块
        
        返回:
            全部重启成功还是失败,重启成功的模块名字，重启失败的模块名字
        """
        # 获取 已启动的modules
        started_optional_modules = {module for module, _ in self.optional_processes}
        started_base_modules = {module for module, _ in self.base_processes}
        
        # 过滤出 要restart的且已启动的modules
        optional_modules_to_restart = [module for module in modules if module in started_optional_modules]
        base_modules_to_restart = [module for module in modules if module in started_base_modules]
        
        if optional_modules_to_restart is None and base_modules_to_restart is None:
            self.logger.info(f"没有已选中的模型正在运行：{modules}无需重启他们")
            return (False, [], [])
        
        ok1, opt_sucess, opt_fail = self._stop_modules(optional_modules_to_restart, isBaseModule=False)
        ok2, base_success, base_fail = self._stop_modules(base_modules_to_restart, isBaseModule=True)
        return ok1 and ok2, base_success + opt_sucess, base_fail + opt_fail
        
    def restart_select_modules(self, modules:List[str])->Tuple[bool,List[str],List[str]]:
        """
        重启 选择的 Optional 内部服务模块
        
        返回:
            全部重启成功还是失败,重启成功的模块名字，重启失败的模块名字
        """
        # 提取已启动的optional modules
        optional_modules = {module for module, _ in self.optional_processes}
        # 过滤出要restart且已启动的optional modules
        modules_to_restart = [module for module in modules if module in optional_modules]
        
        if modules_to_restart is None:
            self.logger.info(f"没有已选中的模型正在运行：{modules}无需重启他们")
            return (False, [], [])
        
        return self._stop_modules(modules_to_restart, isBaseModule=False)
           
    def list_started_modules(self, isBaseModule: Optional[bool] = None) -> List[str]:
        """
        返回已启动的所有内部模块的名字。
        
        参数:
            isBaseModule (bool): 
                - 如果为 True，返回已启动的 base 模块名字。
                - 如果为 False，返回已启动的 optional 模块名字。
                - 如果为 None，返回所有已启动的模块名字。
        
        返回:
            List[str]: 已启动的模块名称列表。
        """
        if isBaseModule == None:
            return [name for name, _ in self.base_processes] + [name for name, _ in self.optional_processes]
        
        if isBaseModule == True:
            return [name for name, _ in self.base_processes]
        else:
            return [name for name, _ in self.optional_processes]
    
    def __del__(self):
        self._stop_all_modules()
        print("InternalModuleManager deleted")
        
    def _show(self):
        self.logger.info(f"Started base modules: {[module for module in self.list_started_modules(isBaseModule=True)]}")
        self.logger.info(f"Started optional modules: {[module for module in self.list_started_modules(isBaseModule=False)]}")


if __name__ == "__main__":
    m = InternalModuleManager()
    m.init_modules()
    m._show()
    
    input("enter1 GPTSoVits")
    name,gptsovits_agent = m.base_processes[0]
    gptsovits_agent.infer_tts_get("你好")
    
    input("enter2 SenseVoice")
    name,gptsovits_agent = m.base_processes[0]

    