# Project:      Agent
# Author:       yomu
# Time:         2024/12/27
# Version:      0.1
# Description:  load config
"""
    负责从指定yml文件读取配置信息
"""
import yaml
from pathlib import Path
from typing import Dict, Any
from logging import Logger

def load_config(logger: Logger, config_path: str, config_name: str) -> Dict[str, Any]:
        """
        从 config_path 中读取指定的配置 (YAML 文件).

        参数:
            config_path (str): 配置文件的路径。
            config_name (str): 配置项的名称。
            logger (Logger): 用于记录日志的 Logger 实例。

        返回:
            Dict[str, Any]: 指定配置项的字典表示。

        异常:
            ValueError: 当 config_path 为空或 YAML 文件内容为空时。
            FileNotFoundError: 当配置文件不存在或路径不正确时。
            KeyError: 当指定的 config_name 不存在于 YAML 文件中时。
            TypeError: 当指定的 config_name 对应的内容不是字典时。
            yaml.YAMLError: 当 YAML 文件解析出错时。
        """
        config_path: Path = Path(config_path)
        
        # 检查 config_path 是否为空
        if not config_path:
            logger.error("Config path is empty.")
            raise ValueError("Config path is empty.")
        
        # 检查配置文件是否存在且是一个文件
        if not config_path.is_file():
            logger.error(f"Config file '{config_path}' is empty.")
            raise ValueError(f"Config file '{config_path}' is empty.")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)  # 使用 safe_load 安全地加载 YAML 数据
                
                if config is None:
                    logger.error(f"The YAML config file {config_path} is empty.")
                    raise ValueError(f"The YAML config file {config_path} is empty.")
                
                res = config.get(config_name, {})
                
                if res is None:
                    logger.error(f"Config name '{config_name}' not found in '{config_path}'.")
                    raise KeyError(f"Config name '{config_name}' not found in '{config_path}'.")
                
                if not isinstance(res, dict):
                    logger.error(f"Config '{config_name}' is not a dictionary.")
                    raise TypeError(f"Config '{config_name}' is not a dictionary.")
                
                return res
        
        except FileNotFoundError:
            logger.error(f"Config file '{config_path}' was not found during file opening.")
            raise FileNotFoundError(f"Config file '{config_path}' was not found during file opening.") from e
        
        except yaml.YAMLError as e:
            logger.error(f"Error parsing the YAML config file: {e}")
            raise ValueError(f"Error parsing the YAML config file '{config_path}': {e}") from e 
