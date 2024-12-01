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
from dotenv import load_dotenv,dotenv_values


# TODO 24/11/30任务，写这个类的注释，完善这个类的所有类成员函数
class InternalModuleManager:
    """
        负责管理启动和关闭 AI agent的各内部模块
        (如各种功能的外部服务器的客户端agent)
    """
        
    def __init__(self):
        self.env_vars = dotenv_values("Init/.env")
        self.config_path = self.env_vars.get("INIT_CONFIG_PATH","")
        self.config: Dict = self._load_config(self.config_path)

        self.support_modules: List[str] = self.config.get('support_modules', [])
        
        # 进程相关 
        self.base_processes: List[Tuple[str, Any]] = []    # 存放已启动的base内部服务模块名字和对象
        self.optional_processes: List[Tuple[str, Any]] = [] # 存放已启动的optional内部服务模块名字和对象
           
        # 要启动的服务
        self.base_modules = self._set_modules(True)         # 要启动的base内部模块
        self.optional_modules = self._set_modules(False)    # 要启动的optional内部模块

    def _set_modules(self,isBase:bool)->List[Tuple[str,str]]:
        """
            设置 要启动的modules
            
            :param isBase: True:base_modules False: optional_modules
            
            返回： 
                module name,module path
        """
        modules_key = "base_modules" if isBase else "optional_modules"
        modules = self.config.get(modules_key, [])
        
        if not modules:
            if isBase:
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
       
    def _init_base_modules(self)->Tuple[bool,List[str],List[str]]:
        """
        启动 最小启动的最基础的内部功能模块
        
        返回:
            是否全部启动成功,
            启动成功的内部base服务模块名字，启动失败的base内部服务模块名字    
        """
        return self._start_modules_sequentially(self.base_modules,True)
 
    def _init_optional_modules(self)->Tuple[bool,List[str],List[str]]:
        """
        启动 可选的内部功能模块
            
        返回:
            是否全部启动成功,
            启动成功的optional内部服务模块名字，启动失败的optional内部服务模块名字
        """
        return  self._start_modules_sequentially(self.optional_modules,False)
    
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
                                   isBaseModule: bool
                                   )->Tuple[bool,List[str],List[str]]:
        """
        顺序启动 内部功能模块
        
        :param modules: 要启动的模块列表。每个元素应包含模型名字和模型路径,比如GPTSoVitsAgent,Module.TTS.GPTSoVits
        :param isBaseModule: 是否是base module
        
        返回:
            是否全部启动成功,
            启动成功的any内部服务模块名字，启动失败的any内部服务模块名字
        """
        success = []
        fail = []
        for module in modules:
            if self._start_single_module(module,isBaseModule):
                success.append(module)
            else:
                fail.append(module)
        
        return (len(fail) == 0, success, fail)

    def init_module(self)->Tuple[bool,
                                Tuple[List[str], List[str]],
                                Tuple[List[str], List[str]]
                                ]:
        """
        初始化启动 内部服务模块
        
        返回:
            是否全部启动成功
            启动成功的base内部服务模块名字，启动失败的base内部服务模块名字
            启动成功的optional内部服务模块名字，启动失败的optional内部服务模块名字
        """
        base = self._init_base_modules()
        optional =  self._init_optional_modules()
        return base, optional
    
    def _stop_base_modules(self):
        """终止 所有 base内部服务模块"""
        for module,_ in self.base_processes:
            self._stop_single_module(module)
    
    def stop_optional_modules(self):
        """终止 所有 optional内部服务模块"""
        for module,_ in self.optional_processes:
            self._stop_single_module(module)
    
    def stop_select_modules(self,modules:List[str]):
        """
        终止 所有选择的optional内部服务模块
        
        注意： 若包含base内部服务模块,则会忽略这些base
        """
        for module in modules:
            self._stop_single_module(module)
    
    def _stop_single_module(self,module:str):
        """终止 单个 Any内部服务模块"""
        # TODO 思考如何实现
        pass
    
    def _stop_all_module(self):
        """终止 所有所有内部服务模块"""
        self.stop_optional_modules()
        self._stop_base_modules()
    
    def _restart_single_module(self,module:str)->bool:
        """重启单个模块"""
        # TODO 要检测该模块是否已经启动，若本身没启动，则不应该重启
        self._stop_single_module(module)
        return self._start_single_module(module)
    
    def _restart_base_module(self)->Tuple[bool,List[str],List[str]]:
        """
        重启 所有的base内部服务模块    
        
        注意：禁止调用！！！
        """
        success = []
        fail = []
        for module in self.base_modules:
            if self._restart_single_module(module):
                success.append(module)
            else:
                fail.append(module)
        return (len(fail) == 0, success, fail)
            
    
    def restart_select_module(self,
                              modules:Optional[List[str]],
                              isAllOpionalModule:Optional[bool]
                              )->Tuple[bool,List[str],List[str]]:
        
        """
        重启 选择的 Optional 内部服务模块
        
        :param modules: 要重启的optional内部服务的名字
        :param isAllOpionalModule: 是否要重启所有optional内部服务，如果此处为True，则modules参数失效
        
        返回:
            全部重启成功还是失败,重新启动(成功/失败)的optional内部服务模块名字
        """
        
        if not modules and not isAllOpionalModule:
            print("param:modules and param:isAllOpionalModule need at least one!Do nothing.")
            return False, [], []
        
        if  modules is None and isAllOpionalModule == False:
            print("When modules is None,isAllOptionalModule shoudle be True!Do nothing")
            return False, [], []
        
        modules_to_restart = self.optional_processes if isAllOpionalModule else modules
        # TODO 如果选择的module没启动，则不会重启该module，还没实现
        success = []
        fail = []
        for module in modules_to_restart:
            if self._restart_single_module(module):
                success.append(module)
            else:
                fail.append(module)

        return (len(fail) == 0, success, fail)
            
    
    def list_started_module(self) -> List[str]:
        """返回已启动的所有内部模块的名字"""
        return self.list_started_base_module() + self.list_started_optional_module()
    
    def list_started_base_module(self)->List[str]:
        """返回已启动的base内部模块的名字"""
        return [name for name, _ in self.base_processes]
    
    def list_started_optional_module(self)->List[str]:
        """返回已启动的optional内部模块的名字"""
        return [name for name, _ in self.optional_processes]
    
    def __del__(self):
        self._stop_all_module()
        
    def _show(self):
        pass


if __name__ == "__main__":
    m = InternalModuleManager()
    m.init_module()
    
    name,gptsovits_agent = m.base_processes[0]
    print(name)
    gptsovits_agent.infer_tts_get("你好")
    
    name,gptsovits_agent = m.base_processes[0]
    print(name)
    