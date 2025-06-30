# Project:      Agent
# Author:       yomu
# Time:         2025/01/06
# Version:      2.0
# Description:  统一初始化管理器

"""
统一初始化管理器

这个模块提供了 Agent 系统的统一初始化入口，负责协调和管理：
- 外部服务的启动和管理
- 内部模块的初始化和启动
- 系统健康检查和监控
- 优雅的启动和关闭流程

使用方式：
    from Init import SystemInitializer
    
    initializer = SystemInitializer()
    success = initializer.initialize_all()
    
    if success:
        print("系统初始化成功")
        initializer.start_services()
    
    # 关闭系统
    initializer.shutdown_all()
"""

import os
import time
import asyncio
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from dotenv import dotenv_values

# 导入新的模块化组件（处理直接运行和模块导入两种情况）
try:
    # 尝试相对导入（作为模块导入时）
    from .ExternalServiceInit import ExternalServiceManager
    from .InternalModuleInit import InternalModuleManager
    from .EnvironmentManager import EnvironmentManager
except ImportError:
    # 如果相对导入失败，说明是直接运行脚本，使用绝对导入
    import sys
    import os
    
    # 添加项目根目录到 Python 路径
    project_root = os.path.dirname(os.path.dirname(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # 添加当前目录到 Python 路径
    current_dir = os.path.dirname(__file__)
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    from ExternalServiceInit import ExternalServiceManager
    from InternalModuleInit import InternalModuleManager
    from EnvironmentManager import EnvironmentManager

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config


class InitializationStage(Enum):
    """初始化阶段枚举"""
    NOT_STARTED = "not_started"
    ENVIRONMENT_CHECK = "environment_check"
    EXTERNAL_SERVICES = "external_services"
    INTERNAL_MODULES = "internal_modules"
    FRAMEWORK = "framework"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class InitializationResult:
    """初始化结果数据类"""
    success: bool
    stage: InitializationStage
    message: str
    details: Optional[Dict[str, Any]] = None
    failed_components: Optional[List[str]] = None
    started_components: Optional[List[str]] = None


class SystemInitializer:
    """
    系统统一初始化器
    
    负责整个 Agent 系统的初始化流程，包括：
    - 环境检查和预备工作
    - 外部服务启动
    - 内部模块初始化
    - 框架组件启动
    - 健康检查和状态监控
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化系统初始化器
        
        Args:
            config_path: 配置文件路径，如果未提供则使用默认路径
        """
        self.logger = setup_logger(name="SystemInitializer", log_path="Other")
        
        # 当前初始化状态
        self.current_stage = InitializationStage.NOT_STARTED
        self.initialization_time = None
        
        # 加载配置
        try:
            self.env_vars = dotenv_values("Init/.env")
            self.config_path = config_path or self.env_vars.get("INIT_CONFIG_PATH", "")
            
            # 初始化各个管理器
            self.external_service_manager = None
            self.internal_module_manager = None
            self.frame_manager = None
            self.environment_manager = None
            
            # 状态跟踪
            self.started_services = []
            self.started_modules = []
            self.failed_components = []
            
            self.logger.info("SystemInitializer initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SystemInitializer: {str(e)}")
            raise
    
    def initialize_all(self) -> InitializationResult:
        """
        执行完整的系统初始化流程
        
        Returns:
            InitializationResult: 初始化结果
        """
        start_time = time.time()
        self.initialization_time = start_time
        
        try:
            self.logger.info("=" * 60)
            self.logger.info("开始系统初始化...")
            self.logger.info("=" * 60)
            
            # 阶段1: 环境检查
            result = self._check_environment()
            if not result.success:
                return result
            
            # 阶段2: 初始化外部服务
            result = self._initialize_external_services()
            if not result.success:
                return result
            
            # 阶段3: 初始化内部模块
            result = self._initialize_internal_modules()
            if not result.success:
                return result
            
            # 阶段4: 初始化框架组件
            result = self._initialize_framework()
            if not result.success:
                return result
            
            # 完成初始化
            self.current_stage = InitializationStage.COMPLETED
            elapsed_time = time.time() - start_time
            
            self.logger.info("=" * 60)
            self.logger.info(f"系统初始化完成！总耗时: {elapsed_time:.2f}秒")
            self.logger.info("=" * 60)
            
            return InitializationResult(
                success=True,
                stage=InitializationStage.COMPLETED,
                message=f"系统初始化成功，耗时 {elapsed_time:.2f}秒",
                started_components=self.started_services + self.started_modules,
                details={
                    "external_services": len(self.started_services),
                    "internal_modules": len(self.started_modules),
                    "total_time": elapsed_time
                }
            )
            
        except Exception as e:
            self.current_stage = InitializationStage.FAILED
            error_msg = f"系统初始化失败: {str(e)}"
            self.logger.error(error_msg)
            
            return InitializationResult(
                success=False,
                stage=InitializationStage.FAILED,
                message=error_msg,
                failed_components=self.failed_components
            )
    
    def _check_environment(self) -> InitializationResult:
        """检查环境和依赖"""
        self.current_stage = InitializationStage.ENVIRONMENT_CHECK
        self.logger.info("阶段1: 检查环境和依赖...")
        
        try:
            # 初始化环境管理器
            self.environment_manager = EnvironmentManager()
            
            # 执行完整的环境检查
            env_success, env_results = self.environment_manager.check_all_environment()
            
            # 记录检查结果
            for result in env_results:
                if result.success:
                    self.logger.info(f"✅ {result.category}: {result.message}")
                else:
                    self.logger.warning(f"⚠️  {result.category}: {result.message}")
                    if result.suggestions:
                        for suggestion in result.suggestions:
                            self.logger.info(f"   建议: {suggestion}")
            
            # 获取环境摘要
            env_summary = self.environment_manager.get_environment_summary()
            
            if env_success:
                self.logger.info("✅ 环境检查完成")
                return InitializationResult(
                    success=True,
                    stage=InitializationStage.ENVIRONMENT_CHECK,
                    message="环境检查通过",
                    details={
                        "environment_summary": env_summary,
                        "check_results": [
                            {
                                "category": r.category,
                                "success": r.success,
                                "message": r.message
                            } for r in env_results
                        ]
                    }
                )
            else:
                # 环境检查失败，但可能不是致命错误
                failed_categories = [r.category for r in env_results if not r.success]
                critical_failures = [r for r in env_results if not r.success and r.category in ["目录结构", "用户环境"]]
                
                if critical_failures:
                    return InitializationResult(
                        success=False,
                        stage=InitializationStage.ENVIRONMENT_CHECK,
                        message=f"关键环境检查失败: {[r.category for r in critical_failures]}",
                        failed_components=failed_categories,
                        details={"check_results": env_results}
                    )
                else:
                    # 非关键失败，继续进行但记录警告
                    self.logger.warning(f"环境检查有警告，但继续执行: {failed_categories}")
                    return InitializationResult(
                        success=True,
                        stage=InitializationStage.ENVIRONMENT_CHECK,
                        message=f"环境检查通过（有警告: {failed_categories}）",
                        details={
                            "environment_summary": env_summary,
                            "warnings": failed_categories
                        }
                    )
            
        except Exception as e:
            error_msg = f"环境检查失败: {str(e)}"
            self.logger.error(error_msg)
            return InitializationResult(
                success=False,
                stage=InitializationStage.ENVIRONMENT_CHECK,
                message=error_msg
            )
    
    def _initialize_external_services(self) -> InitializationResult:
        """初始化外部服务"""
        self.current_stage = InitializationStage.EXTERNAL_SERVICES
        self.logger.info("阶段2: 初始化外部服务...")
        
        try:
            # 创建外部服务管理器
            self.external_service_manager = ExternalServiceManager()
            
            # 验证管理器是否正确创建
            if not hasattr(self.external_service_manager, 'init_services'):
                raise Exception("ExternalServiceManager instance is invalid")
            
            # 启动外部服务
            base_services, optional_services = self.external_service_manager.init_services()
            
            # 记录启动的服务
            if base_services:
                self.started_services.extend([name for name, _ in base_services])
                self.logger.info(f"✅ 基础外部服务启动成功: {[name for name, _ in base_services]}")
            
            if optional_services:
                self.started_services.extend([name for name, _ in optional_services])
                self.logger.info(f"✅ 可选外部服务启动成功: {[name for name, _ in optional_services]}")
            
            # 检查服务状态
            service_status = {}
            try:
                if hasattr(self.external_service_manager, 'get_service_status'):
                    service_status = self.external_service_manager.get_service_status()
                else:
                    self.logger.warning("get_service_status method not available")
            except Exception as e:
                self.logger.warning(f"获取外部服务状态失败: {str(e)}")
                service_status = {}
            
            self.logger.info("✅ 外部服务初始化完成")
            return InitializationResult(
                success=True,
                stage=InitializationStage.EXTERNAL_SERVICES,
                message=f"外部服务启动成功，共 {len(self.started_services)} 个服务",
                started_components=self.started_services,
                details={"service_status": service_status}
            )
            
        except Exception as e:
            error_msg = f"外部服务初始化失败: {str(e)}"
            self.logger.error(error_msg)
            self.failed_components.append("external_services")
            
            return InitializationResult(
                success=False,
                stage=InitializationStage.EXTERNAL_SERVICES,
                message=error_msg,
                failed_components=self.failed_components
            )
    
    def _initialize_internal_modules(self) -> InitializationResult:
        """初始化内部模块"""
        self.current_stage = InitializationStage.INTERNAL_MODULES
        self.logger.info("阶段3: 初始化内部模块...")
        
        try:
            # 创建内部模块管理器
            self.internal_module_manager = InternalModuleManager()
            
            # 验证管理器是否正确创建
            if not hasattr(self.internal_module_manager, 'init_modules'):
                raise Exception("InternalModuleManager instance is invalid")
            
            # 启动内部模块
            success, base_success, base_fail, opt_success, opt_fail = self.internal_module_manager.init_modules()
            
            # 记录启动的模块
            self.started_modules.extend(base_success)
            self.started_modules.extend(opt_success)
            
            # 记录失败的模块
            if base_fail:
                self.failed_components.extend(base_fail)
                self.logger.warning(f"⚠️  基础模块启动失败: {base_fail}")
            
            if opt_fail:
                self.failed_components.extend(opt_fail)
                self.logger.warning(f"⚠️  可选模块启动失败: {opt_fail}")
            
            # 检查模块健康状态
            try:
                if hasattr(self.internal_module_manager, 'get_module_status'):
                    health_status = self.internal_module_manager.get_module_status()
                else:
                    self.logger.warning("get_module_status method not available")
                    health_status = {}
            except Exception as e:
                self.logger.warning(f"获取内部模块状态失败: {str(e)}")
                health_status = {}
            
            if self.started_modules:
                self.logger.info(f"✅ 内部模块启动成功: {self.started_modules}")
            
            self.logger.info("✅ 内部模块初始化完成")
            return InitializationResult(
                success=len(self.started_modules) > 0,  # 只要有模块启动成功就算成功
                stage=InitializationStage.INTERNAL_MODULES,
                message=f"内部模块启动完成，成功 {len(self.started_modules)} 个，失败 {len(base_fail + opt_fail)} 个",
                started_components=self.started_modules,
                failed_components=base_fail + opt_fail,
                details={
                    "health_status": health_status,
                    "base_modules": {"success": base_success, "failed": base_fail},
                    "optional_modules": {"success": opt_success, "failed": opt_fail}
                }
            )
            
        except Exception as e:
            error_msg = f"内部模块初始化失败: {str(e)}"
            self.logger.error(error_msg)
            self.failed_components.append("internal_modules")
            
            return InitializationResult(
                success=False,
                stage=InitializationStage.INTERNAL_MODULES,
                message=error_msg,
                failed_components=self.failed_components
            )
    
    def _initialize_framework(self) -> InitializationResult:
        """初始化框架组件"""
        self.current_stage = InitializationStage.FRAMEWORK
        self.logger.info("阶段4: 初始化框架组件...")
        
        try:
            # 创建框架管理器（暂时跳过，等待实现）
            # self.frame_manager = AgentFrameManager()
            # self.frame_manager.init_frame()
            
            self.logger.info("✅ 框架组件初始化完成（跳过未实现的组件）")
            return InitializationResult(
                success=True,
                stage=InitializationStage.FRAMEWORK,
                message="框架组件初始化完成"
            )
            
        except Exception as e:
            error_msg = f"框架组件初始化失败: {str(e)}"
            self.logger.error(error_msg)
            self.failed_components.append("framework")
            
            return InitializationResult(
                success=False,
                stage=InitializationStage.FRAMEWORK,
                message=error_msg,
                failed_components=self.failed_components
            )
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            "initialization_stage": self.current_stage.value,
            "started_services": len(self.started_services),
            "started_modules": len(self.started_modules),
            "failed_components": len(self.failed_components),
            "initialization_time": self.initialization_time
        }
        
        # 添加详细状态
        if self.external_service_manager:
            try:
                if hasattr(self.external_service_manager, 'get_service_status'):
                    status["external_services"] = self.external_service_manager.get_service_status()
                else:
                    status["external_services"] = "方法不可用"
            except Exception as e:
                self.logger.warning(f"获取外部服务状态失败: {str(e)}")
                status["external_services"] = "获取状态失败"
        
        if self.internal_module_manager:
            try:
                if hasattr(self.internal_module_manager, 'get_module_status'):
                    status["internal_modules"] = self.internal_module_manager.get_module_status()
                else:
                    status["internal_modules"] = "方法不可用"
            except Exception as e:
                self.logger.warning(f"获取内部模块状态失败: {str(e)}")
                status["internal_modules"] = "获取状态失败"
        
        return status
    
    def perform_health_check(self) -> Dict[str, Any]:
        """执行系统健康检查"""
        health_report = {
            "timestamp": time.time(),
            "overall_healthy": True,
            "details": {}
        }
        
        try:
            # 检查外部服务健康状态
            if self.external_service_manager:
                try:
                    if hasattr(self.external_service_manager, 'get_service_status'):
                        service_status = self.external_service_manager.get_service_status()
                        health_report["details"]["external_services"] = service_status
                    else:
                        health_report["details"]["external_services"] = "方法不可用"
                except Exception as e:
                    health_report["details"]["external_services"] = f"检查失败: {str(e)}"
                    health_report["overall_healthy"] = False
            
            # 检查内部模块健康状态
            if self.internal_module_manager:
                try:
                    if hasattr(self.internal_module_manager, 'check_all_modules_health'):
                        module_health = self.internal_module_manager.check_all_modules_health()
                        health_report["details"]["internal_modules"] = module_health
                        
                        # 检查是否有不健康的模块
                        for module_name, (is_healthy, message) in module_health.items():
                            if not is_healthy:
                                health_report["overall_healthy"] = False
                                break
                    else:
                        health_report["details"]["internal_modules"] = "方法不可用"
                        
                except Exception as e:
                    health_report["details"]["internal_modules"] = f"检查失败: {str(e)}"
                    health_report["overall_healthy"] = False
            
            self.logger.info(f"健康检查完成: {'健康' if health_report['overall_healthy'] else '存在问题'}")
            return health_report
            
        except Exception as e:
            self.logger.error(f"健康检查失败: {str(e)}")
            health_report["overall_healthy"] = False
            health_report["error"] = str(e)
            return health_report
    
    def shutdown_all(self) -> bool:
        """优雅关闭所有组件"""
        self.logger.info("开始关闭系统...")
        
        success = True
        
        try:
            # 关闭内部模块
            if self.internal_module_manager:
                try:
                    self.logger.info("关闭内部模块...")
                    # 内部模块的析构函数会自动清理
                    del self.internal_module_manager
                    self.internal_module_manager = None
                    self.logger.info("✅ 内部模块关闭完成")
                except Exception as e:
                    self.logger.error(f"关闭内部模块失败: {str(e)}")
                    success = False
            
            # 关闭外部服务
            if self.external_service_manager:
                try:
                    self.logger.info("关闭外部服务...")
                    if hasattr(self.external_service_manager, 'stop_all_services'):
                        self.external_service_manager.stop_all_services()
                    else:
                        self.logger.warning("stop_all_services method not available")
                    self.logger.info("✅ 外部服务关闭完成")
                except Exception as e:
                    self.logger.error(f"关闭外部服务失败: {str(e)}")
                    success = False
            
            if success:
                self.logger.info("✅ 系统关闭完成")
            else:
                self.logger.warning("⚠️  系统关闭时出现部分错误")
            
            return success
            
        except Exception as e:
            self.logger.error(f"系统关闭失败: {str(e)}")
            return False
    
    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            if hasattr(self, 'current_stage') and self.current_stage != InitializationStage.NOT_STARTED:
                self.shutdown_all()
        except:
            pass


def main():
    """主函数 - 演示使用方式"""
    try:
        print("🚀 启动 Agent 系统初始化...")
        
        # 创建系统初始化器
        initializer = SystemInitializer()
        
        # 执行完整初始化
        result = initializer.initialize_all()
        
        if result.success:
            print(f"✅ {result.message}")
            
            # 显示系统状态
            status = initializer.get_system_status()
            print(f"📊 系统状态: {status}")
            
            # 执行健康检查
            health = initializer.perform_health_check()
            print(f"🏥 健康状态: {'健康' if health['overall_healthy'] else '存在问题'}")
            
            # 等待用户输入
            input("按回车键关闭系统...")
            
        else:
            print(f"❌ {result.message}")
            if result.failed_components:
                print(f"失败组件: {result.failed_components}")
        
        # 关闭系统
        print("🔄 正在关闭系统...")
        shutdown_success = initializer.shutdown_all()
        
        if shutdown_success:
            print("✅ 系统已安全关闭")
        else:
            print("⚠️  系统关闭时出现错误")
            
    except KeyboardInterrupt:
        print("\n⚠️  用户中断，正在关闭系统...")
        if 'initializer' in locals():
            initializer.shutdown_all()
    except Exception as e:
        print(f"❌ 系统启动失败: {str(e)}")


if __name__ == "__main__":
    main()
