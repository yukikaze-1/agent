# Project:      Agent
# Author:       yomu
# Time:         2025/01/06
# Version:      2.0
# Description:  Agent environment manager

"""
环境管理器

负责 AI Agent 系统环境的检查、配置和管理，确保系统在正确的环境中运行。

主要功能：
1. 环境变量检查和设置
2. 系统依赖验证  
3. 目录结构管理
4. 资源可用性检查
5. 配置文件验证
6. 用户环境管理
"""

import os
import sys
import platform
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from Module.Utils.Logger import setup_logger

# 可选导入 psutil（用于系统资源检查）
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class EnvironmentLevel(Enum):
    """环境级别枚举"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


@dataclass
class UserEnvironment:
    """用户环境信息"""
    username: str
    user_id: Optional[str] = None
    home_directory: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    permissions: Optional[List[str]] = None


@dataclass
class EnvironmentCheckResult:
    """环境检查结果"""
    success: bool
    category: str
    message: str
    details: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None


class EnvironmentManager:
    """
    环境管理器
    
    统一管理 Agent 系统的运行环境，包括环境变量、依赖检查、
    目录结构、资源验证、用户环境等。
    """
    
    def __init__(self, base_path: str = "/home/yomu/agent", env_level: EnvironmentLevel = EnvironmentLevel.DEVELOPMENT):
        """
        初始化环境管理器
        
        Args:
            base_path: Agent 系统根目录
            env_level: 环境级别
        """
        self.logger = setup_logger(name="EnvironmentManager", log_path="Other")
        self.base_path = Path(base_path)
        self.env_level = env_level
        
        # 必需的环境变量
        self.required_env_vars = {
            "PYTHONPATH": str(self.base_path),
            "AGENT_HOME": str(self.base_path),
            "AGENT_ENV": env_level.value
        }
        
        # 必需的目录结构
        self.required_directories = [
            "Log",
            "Log/ExternalService",
            "Log/InternalModule", 
            "Log/Other",
            "Log/Test",
            "Config",
            "Data",
            "Temp"
        ]
        
        # 当前用户环境
        self.user_environment = None
        
        self.logger.info(f"EnvironmentManager initialized for {env_level.value} environment")
    
    def init_environment(self) -> Tuple[bool, List[EnvironmentCheckResult]]:
        """
        初始化环境（兼容原有接口）
        
        Returns:
            Tuple[bool, List[EnvironmentCheckResult]]: (是否成功, 检查结果列表)
        """
        return self.check_all_environment()
    
    def check_all_environment(self) -> Tuple[bool, List[EnvironmentCheckResult]]:
        """
        执行完整的环境检查
        
        Returns:
            Tuple[bool, List[EnvironmentCheckResult]]: (是否全部通过, 检查结果列表)
        """
        self.logger.info("开始完整环境检查...")
        
        results = []
        overall_success = True
        
        try:
            # 1. 检查用户环境
            user_result = self.check_user_environment()
            results.append(user_result)
            if not user_result.success:
                overall_success = False
            
            # 2. 检查环境变量
            env_result = self.check_environment_variables()
            results.append(env_result)
            if not env_result.success:
                overall_success = False
            
            # 3. 检查目录结构
            dir_result = self.check_directory_structure()
            results.append(dir_result)
            if not dir_result.success:
                overall_success = False
            
            # 4. 检查系统资源
            res_result = self.check_system_resources()
            results.append(res_result)
            # 资源检查失败在开发环境下只是警告
            if not res_result.success and self.env_level == EnvironmentLevel.PRODUCTION:
                overall_success = False
            
            # 5. 检查基本系统信息
            sys_result = self.check_system_info()
            results.append(sys_result)
            
            self.logger.info(f"环境检查完成: {'通过' if overall_success else '失败'}")
            return overall_success, results
            
        except Exception as e:
            error_result = EnvironmentCheckResult(
                success=False,
                category="环境检查",
                message=f"环境检查失败: {str(e)}"
            )
            results.append(error_result)
            self.logger.error(f"环境检查异常: {str(e)}")
            return False, results
    
    def check_user_environment(self) -> EnvironmentCheckResult:
        """检查用户环境"""
        self.logger.info("检查用户环境...")
        
        try:
            import getpass
            
            username = getpass.getuser()
            home_dir = os.path.expanduser("~")
            
            self.user_environment = UserEnvironment(
                username=username,
                home_directory=home_dir,
                user_id=str(os.getuid()) if hasattr(os, 'getuid') else None
            )
            
            details = {
                "username": username,
                "home_directory": home_dir,
                "current_directory": os.getcwd(),
                "user_id": self.user_environment.user_id
            }
            
            return EnvironmentCheckResult(
                success=True,
                category="用户环境",
                message=f"用户环境检查通过 (用户: {username})",
                details=details
            )
            
        except Exception as e:
            return EnvironmentCheckResult(
                success=False,
                category="用户环境",
                message=f"用户环境检查失败: {str(e)}"
            )
    
    def check_environment_variables(self) -> EnvironmentCheckResult:
        """检查环境变量"""
        self.logger.info("检查环境变量...")
        
        try:
            missing_vars = []
            incorrect_vars = []
            suggestions = []
            
            # 检查 PYTHONPATH
            python_path = os.environ.get('PYTHONPATH', '')
            if str(self.base_path) not in python_path:
                missing_vars.append('PYTHONPATH')
                suggestions.append(f"export PYTHONPATH={self.base_path}:$PYTHONPATH")
            
            # 检查其他环境变量
            for var_name, expected_value in self.required_env_vars.items():
                if var_name == 'PYTHONPATH':
                    continue  # 已经检查过了
                    
                current_value = os.environ.get(var_name)
                if not current_value:
                    missing_vars.append(var_name)
                    suggestions.append(f"export {var_name}={expected_value}")
            
            details = {
                "pythonpath": python_path,
                "agent_home": os.environ.get("AGENT_HOME", ""),
                "agent_env": os.environ.get("AGENT_ENV", ""),
                "missing": missing_vars,
                "suggestions": suggestions
            }
            
            if missing_vars:
                return EnvironmentCheckResult(
                    success=False,
                    category="环境变量",
                    message=f"缺少环境变量: {missing_vars}",
                    details=details,
                    suggestions=suggestions
                )
            
            return EnvironmentCheckResult(
                success=True,
                category="环境变量",
                message="环境变量配置正确",
                details=details
            )
            
        except Exception as e:
            return EnvironmentCheckResult(
                success=False,
                category="环境变量",
                message=f"环境变量检查失败: {str(e)}"
            )
    
    def check_directory_structure(self) -> EnvironmentCheckResult:
        """检查和创建目录结构"""
        self.logger.info("检查目录结构...")
        
        try:
            created_dirs = []
            permission_issues = []
            existing_dirs = []
            
            for dir_name in self.required_directories:
                dir_path = self.base_path / dir_name
                
                if not dir_path.exists():
                    try:
                        dir_path.mkdir(parents=True, exist_ok=True)
                        created_dirs.append(str(dir_path))
                        self.logger.info(f"创建目录: {dir_path}")
                    except PermissionError:
                        permission_issues.append(str(dir_path))
                        self.logger.error(f"无法创建目录 {dir_path}: 权限不足")
                else:
                    existing_dirs.append(str(dir_path))
                    # 检查写权限
                    if not os.access(dir_path, os.W_OK):
                        permission_issues.append(str(dir_path))
            
            details = {
                "created_directories": created_dirs,
                "existing_directories": existing_dirs,
                "permission_issues": permission_issues,
                "base_path": str(self.base_path)
            }
            
            if permission_issues:
                return EnvironmentCheckResult(
                    success=False,
                    category="目录结构",
                    message=f"目录权限问题: {permission_issues}",
                    details=details,
                    suggestions=[f"请检查目录权限: chmod 755 {' '.join(permission_issues)}"]
                )
            
            message = "目录结构检查通过"
            if created_dirs:
                message += f" (创建了 {len(created_dirs)} 个目录)"
            
            return EnvironmentCheckResult(
                success=True,
                category="目录结构",
                message=message,
                details=details
            )
            
        except Exception as e:
            return EnvironmentCheckResult(
                success=False,
                category="目录结构",
                message=f"目录结构检查失败: {str(e)}"
            )
    
    def check_system_resources(self) -> EnvironmentCheckResult:
        """检查系统资源"""
        self.logger.info("检查系统资源...")
        
        if not PSUTIL_AVAILABLE:
            return EnvironmentCheckResult(
                success=True,
                category="系统资源",
                message="psutil 未安装，跳过详细资源检查",
                details={"psutil_available": False},
                suggestions=["安装 psutil 以获得详细的系统资源信息: pip install psutil"]
            )
        
        try:
            import psutil
            
            # 检查磁盘空间
            disk_usage = psutil.disk_usage(str(self.base_path))
            free_space_gb = disk_usage.free / (1024**3)
            total_space_gb = disk_usage.total / (1024**3)
            
            # 检查内存
            memory = psutil.virtual_memory()
            total_memory_gb = memory.total / (1024**3)
            available_memory_gb = memory.available / (1024**3)
            memory_percent = memory.percent
            
            # 检查CPU
            cpu_count = psutil.cpu_count()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            warnings = []
            errors = []
            
            # 磁盘空间检查（最少需要 2GB）
            min_disk_gb = 2.0
            if free_space_gb < min_disk_gb:
                errors.append(f"磁盘空间不足: {free_space_gb:.1f}GB < {min_disk_gb}GB")
            elif free_space_gb < 5.0:
                warnings.append(f"磁盘空间较少: {free_space_gb:.1f}GB")
            
            # 内存检查（最少需要 2GB）
            min_memory_gb = 2.0
            if total_memory_gb < min_memory_gb:
                errors.append(f"系统内存不足: {total_memory_gb:.1f}GB < {min_memory_gb}GB")
            elif memory_percent > 90:
                warnings.append(f"内存使用率过高: {memory_percent:.1f}%")
            
            details = {
                "disk_free_gb": round(free_space_gb, 2),
                "disk_total_gb": round(total_space_gb, 2),
                "memory_total_gb": round(total_memory_gb, 2),
                "memory_available_gb": round(available_memory_gb, 2),
                "memory_percent": round(memory_percent, 1),
                "cpu_count": cpu_count,
                "cpu_percent": round(cpu_percent, 1),
                "psutil_available": True
            }
            
            if errors:
                return EnvironmentCheckResult(
                    success=False,
                    category="系统资源",
                    message=f"系统资源不足: {'; '.join(errors)}",
                    details=details,
                    suggestions=["请释放磁盘空间或关闭不必要的程序"]
                )
            
            message = "系统资源检查通过"
            if warnings:
                message += f" (警告: {'; '.join(warnings)})"
            
            return EnvironmentCheckResult(
                success=True,
                category="系统资源",
                message=message,
                details=details
            )
            
        except Exception as e:
            return EnvironmentCheckResult(
                success=True,  # 资源检查失败不阻止系统启动
                category="系统资源",
                message=f"系统资源检查失败: {str(e)} (不影响启动)"
            )
    
    def check_system_info(self) -> EnvironmentCheckResult:
        """检查系统基本信息"""
        self.logger.info("检查系统信息...")
        
        try:
            details = {
                "platform": platform.platform(),
                "system": platform.system(),
                "release": platform.release(),
                "python_version": platform.python_version(),
                "python_executable": sys.executable,
                "architecture": platform.architecture()[0],
                "processor": platform.processor(),
                "hostname": platform.node()
            }
            
            # 检查 Python 版本
            python_version = tuple(map(int, platform.python_version().split('.')))
            min_python = (3, 8)  # 最低要求 Python 3.8
            
            if python_version < min_python:
                return EnvironmentCheckResult(
                    success=False,
                    category="系统信息",
                    message=f"Python 版本过低: {platform.python_version()} < 3.8",
                    details=details,
                    suggestions=["请升级到 Python 3.8 或更高版本"]
                )
            
            return EnvironmentCheckResult(
                success=True,
                category="系统信息",
                message=f"系统信息检查通过 (Python {platform.python_version()}, {platform.system()})",
                details=details
            )
            
        except Exception as e:
            return EnvironmentCheckResult(
                success=True,  # 系统信息检查失败不阻止启动
                category="系统信息",
                message=f"系统信息检查失败: {str(e)}"
            )
    
    def get_environment_summary(self) -> Dict[str, Any]:
        """获取环境信息摘要"""
        try:
            summary = {
                "base_path": str(self.base_path),
                "env_level": self.env_level.value,
                "python_version": platform.python_version(),
                "platform": platform.system(),
                "timestamp": __import__("time").time()
            }
            
            if self.user_environment:
                summary["user"] = {
                    "username": self.user_environment.username,
                    "home_directory": self.user_environment.home_directory,
                    "user_id": self.user_environment.user_id
                }
            
            # 添加环境变量信息
            summary["environment_vars"] = {
                "pythonpath": os.environ.get("PYTHONPATH", ""),
                "agent_home": os.environ.get("AGENT_HOME", ""),
                "agent_env": os.environ.get("AGENT_ENV", "")
            }
            
            return summary
            
        except Exception as e:
            return {"error": str(e)}
    
    def setup_recommended_environment(self) -> bool:
        """设置推荐的环境配置"""
        self.logger.info("设置推荐的环境配置...")
        
        try:
            # 这里可以添加自动设置环境的逻辑
            # 比如创建 .env 文件、设置环境变量等
            
            success, results = self.check_all_environment()
            
            if not success:
                self.logger.warning("环境仍有问题，请查看检查结果")
                for result in results:
                    if not result.success and result.suggestions:
                        self.logger.info(f"建议 ({result.category}): {'; '.join(result.suggestions)}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"环境设置失败: {str(e)}")
            return False