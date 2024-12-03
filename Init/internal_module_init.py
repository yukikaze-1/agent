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
from typing import List,Dict,Tuple,Any,Optional
from dotenv import dotenv_values


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
                                返回:   Tuple[bool, List[str], List[str] , List[str], List[str]]
                                
            - _init_base_modules
            - _init_optional_modules
            
        stop系列函数： 负责停止已启动的module
            - stop_single_module
            - stop_optional_modules
            - stop_select_modules
            - _stop_single_module
            - _stop_single_module_aux
            - _stop_base_modules   
            - _stop_select_modules
            - _stop_all_modules
        
        restart系列函数： 负责重启已启动的module
            - restart_select_modules
            - restart_optional_modules
            - restart_single_module
            - _restart_single_module_aux
            - _restart_single_module
            - _restart_base_modules
            - _restart_select_modules   
            
        list系列函数：负责得到服务的各种信息
            - list_started_module
            
        其他函数:
            - _load_config
            - _create_agent
            - _get_modules
            - _get_module_config
    """
        
    def __init__(self):
        self.env_vars = dotenv_values("Init/.env")
        self.config_path = self.env_vars.get("INIT_CONFIG_PATH","")
        self.config: Dict = self._load_config(self.config_path)

        self.support_modules: List[str] = self.config.get('support_modules', [])
        
        # 进程相关 
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

    def _get_module_config(self,module_name: str)->Tuple[bool, str, str]:
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
        
        return False, module_name, ""

    def _get_modules(self,isBaseModules:bool)->List[Tuple[str,str]]:
        """
            返回 要启动的[modules+module_path]列表
            
            :param isBase: True:base_modules False: optional_modules
            
            返回： 
                module_name,module_path
        """
        modules_key = "base_modules" if isBaseModules else "optional_modules"
        modules = self.config.get(modules_key, [])
        
        if modules is None:
            if isBaseModules:
                raise ValueError(f"base modules is empty. Please check the {self.config_path}")
            else:
                return []
            
        ret = [ (next(iter(module.keys())),next(iter(module.values())))  for module in modules]
        return ret
    
    def _create_agent(self,module_name: str,module_path: str,  *args, **kwargs):
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
                raise ValueError(f"Module {module_name} not found in module {module_path}")
            # 实例化并返回对象
            return cls(*args, **kwargs)
        
        except ModuleNotFoundError as e:
            raise ImportError(f"Module {module_path} could not be found") from e

    def _load_config(self, config_path: str) -> Dict:
        """
            从config_path中读取配置(*.yml)
            
            返回：
                yml文件中配置的字典表示
        """
        if config_path is None:
            raise ValueError(f"Config file {config_path} is empty.Please check the file 'Init/.env'.It should set the 'INIT_CONFIG_PATH'")
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)  # 使用 safe_load 安全地加载 YAML 数据
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file {config_path} not found.")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing the YAML config file: {e}")
  
       
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
    
    
    def _start_single_module(self,module:Tuple[str,str],isBaseModule: bool)->bool:
        """
            单次启动 一个内部服务模块
            
            :param module: 应包含模型名字和模型路径,比如GPTSoVitsAgent,Module.TTS.GPTSoVits
            :param isBaseModule: 是否是base module
            
            返回:
                是否启动成功
        """
        
        # 获取模块路径和类名
        module_name, module_path = module
        # 检查是否是受支持的模块
        if module_name not in self.support_modules:
            print(f"Unknown module {module}")
            return False
        
        try:
            # 使用 _create_agent 动态加载模块
            agent = self._create_agent(module_name, module_path)
            # 将模块添加到相应的列表
            if isBaseModule:
                self.base_processes.append((module, agent))
                print(f"Started base module {module}")
            else:
                self.optional_processes.append((module, agent))
                print(f"Started optional module {module}")
            return True  # 成功启动模块后返回 True
        except Exception as e:
            print(f"Failed to start module {module}: {e}")
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
            if self._start_single_module(module,isBaseModules):
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
            module_type (str): 模块类型描述，例如 'base' 或 'optional'。
            
        返回:
            bool: 是否成功停止模块。
        """
        module_type = "base" if isBaseModule else "optional"
        started_modules = {module_name for module_name, _ in processes}
        
        # 检查该模块是否已启动
        if module not in started_modules:
            print(f"The {module_type} module {module} is not running. No need to stop it.")
            return False

        print(f"Start stopping the running {module_type} module {module}...")
        # 从列表中移除对应的项（会导致模块被析构）
        for item in processes:
            module_name, _ = item
            if module_name == module:
                processes.remove(item)
                break
        print(f"Stopped the running {module_type} module {module}.")
        return True
    
    def _stop_base_modules(self)->Tuple[bool,List[str],List[str]]:
        """终止 所有 base内部服务模块"""
        print("Now starting to stop all the base modules...")
        
        success:List[str] = []
        fail:List[str] = []
        
        for module,_ in self.base_processes:
            if self._stop_single_module(module, isBaseModule=True):
                success.append(module)
            else:
                fail.append(module)
                
        if (len(fail) == 0):
            print(f"Stopped the optioanl modules successfully:\n \t {success}")                     
            print("Stopped all the optional modules...")
        else:
            print(f"Stopped the optioanl modules successfully:\n \t {success}")
            print(f"Stopped the optioanl modules failed:\n \t {fail}")
            print("Some modules stop failed,please check the info.")   
            
        return (len(fail) == 0, success, fail)
        
    def stop_optional_modules(self)->Tuple[bool,List[str],List[str]]:
        """终止 所有 optional内部服务模块"""
        print("Now stop all the optional modules...")
        
        if self.optional_processes is None:
            print("No running optional modules.No need to stop them.Do nothing.")
            return False, [], []
        
        success:List[str] = []
        fail:List[str] = []
        
        for module, _ in self.optional_processes:
            if self._stop_single_module(module,isBaseModule=False):
                success.append(module)
            else:
                fail.append(module)
                     
        if (len(fail) == 0):
            print(f"Stopped the optioanl modules successfully:\n \t {success}")                     
            print("Stopped all the optional modules...")
        else:
            print(f"Stopped the optioanl modules successfully:\n \t {success}")
            print(f"Stopped the optioanl modules failed:\n \t {fail}")
            print("Some modules stop failed,please check the info.")
            
        return (len(fail) == 0, success, fail)
    
    def stop_select_modules(self,modules:List[str])->Tuple[bool,List[str],List[str]]:
        """
        终止 所有选择的optional内部服务模块
        
        注意： 若包含base内部服务模块,则会忽略这些base
        返回:
            是否全部stop成功，stop成功的module name，stop失败的module name
        """
        # 获取 已启动的optional modules
        optioanal_module_names = {module for module, _ in self.optional_processes}
        # 过滤出 要stop的已启动的optional_module
        modules_to_stop = [module for module in modules if module in optioanal_module_names]
        
        if modules_to_stop is None:
            print("No optional modules need to stop.Please check the param:modules")
            return False
        
        success:List[str] = []
        fail:List[str] = []
        
        # 对所有要停止的optional模块进行操作       
        for module in modules_to_stop:
            if self.stop_single_module(module):
                success.append(module)
            else:
                fail.append(module)
                
        print(f"Stopped the select modules successfully:\n \t {success}")
        if (len(fail) == 0):        
            print(f"Stopped the select modules successfully:\n \t {fail}")
        
        return (len(fail) == 0, success, fail)
    
    def _stop_select_modules(self,modules:List[str])->Tuple[bool,List[str],List[str]]:
        """终止 所有选择的Any内部服务模块"""
        
        # 获取 已启动的modules
        started_optional_modules = {module for module, _ in self.optional_processes}
        started_base_modules = {module for module, _ in self.base_processes}
        
        # 过滤出 要stop的且已启动的modules
        optional_modules_to_stop = [module for module in modules if module in started_optional_modules]
        base_modules_to_stop = [module for module in modules if module in started_base_modules]
        
        # 没有要stop的module
        if optional_modules_to_stop is None and base_modules_to_stop is None:
            print("No module in param:modules is running.No need to stop them.Please check the param:modules")
            return False, [], []
        
        success:List[str] = []
        fail:List[str] = []
        
        # stop optional modules
        if optional_modules_to_stop:      
            for module in optional_modules_to_stop:
                if self._stop_single_module(module,isBaseModule=False):
                    success.append(module)
                else:
                    fail.append(module)
        
        # stop base modules
        if base_modules_to_stop:       
            for module in base_modules_to_stop:
                if self._stop_single_module(module,isBaseModule=True):
                    success.append(module)
                else:
                    fail.append(module)
            
        print(f"Stopped the select modules successfully:\n \t {success}")
        if (len(fail) == 0):        
            print(f"Stopped the select modules successfully:\n \t {fail}")
        
        return (len(fail) == 0, success, fail)
        
    def _stop_all_modules(self):
        """终止 所有所有内部服务模块"""
        self.stop_optional_modules()
        self._stop_base_modules()
        print("InternalModuleManager cleaned up and all modules are stopped.")
    
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
        """
        重启指定模块。如果模块未启动，则不会执行任何操作。
        
        参数:
            module (str): 要重启的模块名称。
            isBaseModule (bool): 模块是否为 base 模块.
        
        返回:
            bool: 是否成功重启模块。
        """
        # 检测该模块是否已经启动，若本身没启动，则不应该重启
        if not self._check_module_is_started(module):
            print(f"The module {module} is not running. No need to restart it. Do nothing.")
            return False

        print(f"Starting to restart the module {module}...")
        
        # 尝试停止模块
        if not self._stop_single_module(module, isBaseModule):
            print(f"Restart module {module} failed. Stopping the module failed. Please check the info.")
            return False
        
        # 尝试启动模块
        _, _, module_path = self._get_module_config(module_name=module)
        if not self._start_single_module((module, module_path), isBaseModule):
            print(f"Restart module {module} failed. Starting the module failed. Please check the info.")
            return False

        print(f"Module {module} restarted successfully.")
        return True
    
    def _restart_single_module(self, module:str, isBaseModule:bool)->bool:
        """
        重启指定模块。如果模块未启动，则不会执行任何操作。
        
        参数:
            module (str): 要重启的模块名称。
            isBaseModule (bool): 模块是否为 base 模块.
        
        返回:
            bool: 是否成功重启模块。
        """
        return self._restart_single_module_aux(module, isBaseModule=isBaseModule)
    
    def restart_single_module(self,module:str)->bool:
        """重启 单个optional模块
         
        注意： 若为base内部服务模块,则不会重启 
        """
        # 获取已启动的optioanl modules
        started_optional_modules = {module for module, _ in self.optional_processes}
        
        if module not in started_optional_modules:
            print(f"Optional module {module} is not running.No need to restart.Do nothing.")
            return False

        return self._restart_single_module_aux(module, isBaseModule=False)
    
    def _restart_base_modules(self)->Tuple[bool,List[str],List[str]]:
        """
        重启 所有的base内部服务模块    
        
        注意：禁止调用！！！
        
        返回:
            全部重启成功还是失败,重新启动(成功/失败)的base内部服务模块名字
        """
        success: List[str] = []
        fail: List[str] = []
        
        for module, _ in self.base_processes:
            if self._restart_single_module(module, isBaseModule=True):
                success.append(module)
            else:
                fail.append(module)
                
        print(f"Restarted the base modules successfully:\n \
                \t {success} \n \
                Restarted the base modules failed:\n \
                \t {fail} ")
        return (len(fail) == 0, success, fail)
    
    def restart_optional_modules(self)->Tuple[bool,List[str],List[str]]:
        """ 重启 所有的optional内部服务模块 
        
        返回:
            全部重启成功还是失败, 重新启动(成功/失败)的optional内部服务模块名字
        """
        
        success: List[str] = []
        fail: List[str] = []
        
        for module, _ in self.optional_processes:
            if self._restart_single_module(module, isBaseModule=False):
                success.append(module)
            else:
                fail.append(module)
                
        print(f"Restarted the optional modules successfully:\n \
                \t {success} \n \
                Restarted the optional modules failed:\n \
                \t {fail} ")
        
        return (len(fail) == 0, success, fail)
    
    def _restart_select_modules(self, modules:List[str])->Tuple[bool,List[str],List[str]]:
        """
        重启 选择的 Any 内部服务模块
        
        禁止调用！！！
        
        :param modules: 要重启的Any内部服务的名字
        
        返回:
            全部重启成功还是失败,重新启动(成功/失败)的Any内部服务模块名字
        """
        # 获取 已启动的modules
        started_optional_modules = {module for module, _ in self.optional_processes}
        started_base_modules = {module for module, _ in self.base_processes}
        
        # 过滤出 要restart的且已启动的modules
        optional_modules_to_restart = [module for module in modules if module in started_optional_modules]
        base_modules_to_restart = [module for module in modules if module in started_base_modules]
        
        if optional_modules_to_restart is None and base_modules_to_restart is None:
            print(f"No module in {modules} is running.No need to restart them.Please check the param:modules")
            return False, [], []
        
        success:List[str] = []
        fail:List[str] = []
        
        if optional_modules_to_restart:      
            for module in optional_modules_to_restart:
                if self._restart_single_module(module,isBaseModule=False):
                    success.append(module)
                else:
                    fail.append(module)
            print(f"Restarted the selected optional modules.")
        
        if base_modules_to_restart:       
            for module in base_modules_to_restart:
                if self._restart_single_module(module,isBaseModule=True):
                    success.append(module)
                else:
                    fail.append(module)
            print(f"Restarted the selected base modules.")
            
        print(f"Restarted the select modules successfully:\n \
                \t {success} \n \
                Restarted the select modules failed:\n \
                \t {fail} ")
        
        return (len(fail) == 0, success, fail)
        
    def restart_select_modules(self, modules:List[str])->Tuple[bool,List[str],List[str]]:
        """
        重启 选择的 Optional 内部服务模块
        
        :param modules: 要重启的optional内部服务的名字
        
        返回:
            全部重启成功还是失败,重新启动(成功/失败)的optional内部服务模块名字
        """
        # 提取已启动的optional modules
        optional_modules = {module for module, _ in self.optional_processes}
        # 过滤出要restart且已启动的optioanl modules
        modules_to_restart = [module for module in modules if module in optional_modules]
        
        if modules_to_restart is None:
            print(f"No module in {modules} is running.No need to restart them.Please check the param:modules")
            return False, [], []
        
        success: List[str] = []
        fail: List[str] = []
        
        for module in modules_to_restart:
            if self._restart_single_module(module, isBaseModule=False):
                success.append(module)
            else:
                fail.append(module)
                
        print(f"Restarted the select modules successfully:\n \
                \t {success} \n \
                Restarted the select modules failed:\n \
                \t {fail} ")
        
        return (len(fail) == 0, success, fail)
 
           
    def list_started_module(self, isBaseModule: bool = None) -> List[str]:
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
        base = self.list_started_module(isBaseModule=True)
        optional = self.list_started_module(isBaseModule=False)
        print(f"Startted base modules: {[module for module in base]}")
        print(f"Startted optioanl modules: {[module for module in optional]}")


if __name__ == "__main__":
    m = InternalModuleManager()
    m.init_modules()
    print()
    m._show()
    
    input("enter1 GPTSoVits")
    name,gptsovits_agent = m.base_processes[0]
    gptsovits_agent.infer_tts_get("你好")
    
    input("enter2 SenseVoice")
    name,gptsovits_agent = m.base_processes[0]

    