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
        1) SenseVoice agent 
    4. 
"""

import os
import yaml
import importlib
from typing import List,Dict,Tuple,Any,Optional
from dotenv import load_dotenv,dotenv_values

# from ..Module.TTS.GPTSoVits.GPTSoVitsAgent import GPTSoVitsAgent
# from ..Module.STT.SenseVoice.SenseVoiceAgent import SenseVoiceAgent

# TODO 24/11/30任务，写这个类的注释，完善这个类的所有类成员函数
class InternalModuleManager:
    """
        负责管理启动和关闭 AI agent的各内部模块
        (如各种功能的外部服务器的客户端agent)
    """
    # def __new__(cls,*args,**kwargs):
    #     cls.env_vars = dotenv_values("./.env")
    #     load_dotenv()
    #     return super().__new__(cls)
        
    def __init__(self, config_path: str = "Init/config.yml"):
        # 加载 .env 文件
        self.env_vars = dotenv_values("Init/.env")

        # 配置文件
        self.config: Dict = self._load_config(config_path)

        # 支持的模块列表
        self.support_module: List[str] = self.config.get('support_module', [])

        # 存放已启动的base内部服务模块名字和对象
        self.base_module: List[Tuple[str, Any]] = []

        # 存放已启动的optional内部服务模块名字和对象
        self.optional_module: List[Tuple[str, Any]] = []

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
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)  # 使用 safe_load 安全地加载 YAML 数据
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file {config_path} not found.")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing the YAML config file: {e}")
       
    
    # TODO 以后考虑 将这些配置提取到一个json配置文件中，函数应从该json文件中读取要初始化的内部模块
    def _set_base_module(self)->List[str]:
        """
        设置 最小启动的最基础的内部模块
            1. 语音合成(GPTSoVitsAgent)
            2. 语音识别(SenseVoiceAgent)
        返回:
            一个包含内部服务模块的列表
        """
        # TODO 目前 SenseVoiceAgent 还没实现！现在是还没测试
        ret = []
        ret.append("GPTSoVitsAgent")
        ret.append("SenseVoiceAgent")
        return  ret
    
    # TODO 以后考虑 将这些配置提取到一个json配置文件中，函数应从该json文件中读取要初始化的内部模块
    def _add_optional_module(self)->List[str]:
        """
        添加 可选的内部功能模块

        返回:
            一个包含内部服务模块的列表 或者 空列表  
        """
        ret = []
        return ret
    
    def _init_base_module(self)->Tuple[bool,List[str],List[str]]:
        """
        启动 最小启动的最基础的内部功能模块
        
        (注：ollama llm不在此处，因为langchain提供了ChatOllama这一模块)
        
            1. 语音合成(GPTSoVits)
            2. 语音识别(SenseVoice)
        返回:
            是否全部启动成功,
            启动成功的内部base服务模块名字，启动失败的base内部服务模块名字    
        """
        base_module = self._set_base_module()
        return self._start_module_sequentially(base_module,True)

    
    def _init_optional_module(self)->Tuple[bool,List[str],List[str]]:
        """
        启动 可选的内部功能模块
            
        返回:
            是否全部启动成功,
            启动成功的optional内部服务模块名字，启动失败的optional内部服务模块名字
        """
        optional_module = self._add_optional_module()
        return  self._start_module_sequentially(optional_module,False)
    
    def _start_single_module(self,module:str,isBaseModule: bool)->bool:
        """
            单次启动一个内部服务模块
            
            返回:
                是否启动成功
        """
        # 检查是否是受支持的模块
        module_config = next((item for item in self.config.get('support_module', []) if item[0] == module), None)
        if not module_config:
            print(f"Unknown module {module}")
            return False
        
        try:
            # 获取模块路径和类名
            class_name, module_path = module_config
            # 使用 _create_agent 动态加载模块
            agent = self._create_agent(class_name, module_path)
            # 将模块添加到相应的列表
            if isBaseModule:
                self.base_module.append((module, agent))
                print(f"Started base module {module}")
            else:
                self.optional_module.append((module, agent))
                print(f"Started optional module {module}")
            return True  # 成功启动模块后返回 True
        except Exception as e:
            print(f"Failed to start module {module}: {e}")
            return False  # 如果发生异常，返回 False
        
    
    def _start_module_sequentially(self,
                                   modules:List[str],
                                   isBaseModule: bool
                                   )->Tuple[bool,List[str],List[str]]:
        """
        顺序启动 内部功能模块
            
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
        base = self._init_base_module()
        optional =  self._init_optional_module()
        return base, optional
    
    def _stop_base_module(self):
        """
        终止 所有的base内部服务模块
        
        禁止调用！！！
        """
        # for module, _ in self.base_module:
        #     self._stop_single_module(module)
        for name,agent in self.base_module:
            pass
    
    def stop_optional_module(self):
        """
        终止 所有的optional内部服务模块
        """
        for module,_ in self.optional_module:
            self._stop_single_module(module)
    
    def stop_select_module(self,modules:List[str]):
        """
        终止 所有选择的optional内部服务模块
        
        注意： 若包含base内部服务模块,则会忽略这些base
        """
        for module in modules:
            self._stop_single_module(module)
    
    def _stop_single_module(self,module:str):
        """
        终止 单个Any内部服务模块
        """
        # TODO 思考如何实现
        pass
    
    def _stop_all_module(self):
        """
        终止 所有Any内部服务模块 
        """
        self.stop_optional_module()
        self._stop_base_module()
    
    def _restart_single_module(self,module:str)->bool:
        """重启"""
        self._stop_single_module(module)
        return self._start_single_module(module)
    
    def _restart_base_module(self)->Tuple[bool,List[str],List[str]]:
        """
        重启 所有的base内部服务模块    
        
        注意：禁止调用！！！
        """
        success = []
        fail = []
        for module in self.base_module:
            if self._restart_single_module(module):
                success.append(module)
            else:
                fail.append(module)
        return (len(fail) == 0, success, fail)
            
    
    def restart_select_module(self,
                              modules:List[str],
                              isAllOpionalModule:bool=False
                              )->Tuple[bool,List[str],List[str]]:
        
        """
        重启 选择的Optional 内部服务模块
        
        :param modules: 要重启的optional内部服务的名字
        :param isAllOpionalModule: 是否要重启所有optional内部服务，如果此处为True，则modules参数失效
        
        返回:
            全部重启成功还是失败,重新启动(成功/失败)的optional内部服务模块名字
        """
        modules_to_restart = self.optional_module if isAllOpionalModule else modules
        
        success = []
        fail = []
        for module in modules_to_restart:
            if self._restart_single_module(module):
                success.append(module)
            else:
                fail.append(module)

        return (len(fail) == 0, success, fail)
            
    
    def list_started_module(self) -> List[str]:
        """返回已启动的内部模块的名字"""
        return self.list_started_base_module() + self.list_started_optional_module()
    
    def list_started_base_module(self)->List[str]:
        return [name for name, _ in self.base_module]
    
    def list_started_optional_module(self)->List[str]:
        return [name for name, _ in self.optional_module]
    
    def __del__(self):
        self._stop_all_module()
        
    def _show(self):
        pass


if __name__ == "__main__":
    m = InternalModuleManager()
    m.init_module()
    name,gptsovits_agent = m.base_module[0]
    print(name)
    gptsovits_agent.infer_tts_get("你好")