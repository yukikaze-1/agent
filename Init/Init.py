# Project:      Agent
# Author:       yomu
# Time:         2025/01/06
# Version:      2.0
# Description:  统一初始化管理器

"""
统一初始化管理器

这个模块提供了 Agent 系统的统一初始化入口，采用服务发现架构：
- 外部服务的发现和连接管理
- 内部代理模块的初始化和启动
- 系统健康检查和监控
- 优雅的启动和关闭流程

使用方式：
    from Init import SystemInitializer
    
    initializer = SystemInitializer()
    success = initializer.initialize_all()
    
    if success:
        print("系统初始化成功")
        # 系统已运行，代理模块已就绪
    
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
    from .ServiceDiscovery import ServiceDiscoveryManager, ExternalServiceConnector
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
    
    from ServiceDiscovery import ServiceDiscoveryManager, ExternalServiceConnector
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
    系统统一初始化器（服务发现模式）
    
    负责整个 Agent 系统的初始化流程，包括：
    - 环境检查和预备工作
    - 外部服务的发现和连接
    - 内部代理模块的初始化
    - 框架组件启动
    - 健康检查和状态监控
    
    架构说明：
    - 外部服务：通过 Consul 服务发现连接已运行的服务
    - 内部模块：使用代理模式，在同一进程内运行
    - 通信方式：代理模块通过 HTTP 客户端与外部服务通信
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
            
            # 初始化环境管理器
            self.environment_manager = None
            
            # 服务发现模式的管理器
            self.service_discovery_manager = None
            self.service_connector = None
            
            # 状态跟踪
            self.started_services = []
            self.started_modules = []
            self.failed_components = []
            
            self.logger.info("SystemInitializer initialized successfully (服务发现模式)")
            
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
        """初始化外部服务（服务发现模式）"""
        self.current_stage = InitializationStage.EXTERNAL_SERVICES
        self.logger.info("阶段2: 连接外部服务（服务发现模式）...")
        
        try:
            import asyncio
            
            # 创建服务发现管理器
            consul_url = self.env_vars.get("CONSUL_URL") or "http://127.0.0.1:8500"
            discovery_config_path = "Init/ServiceDiscovery/config.yml"
            
            self.service_discovery_manager = ServiceDiscoveryManager(
                consul_url=consul_url,
                config_path=discovery_config_path
            )
            
            # 创建服务连接器
            self.service_connector = ExternalServiceConnector(self.service_discovery_manager)
            
            async def async_init():
                # 等待外部服务就绪
                self.logger.info("等待外部服务就绪...")
                discovery_manager = self.service_discovery_manager
                if discovery_manager and not await discovery_manager.wait_for_services(timeout=60):
                    raise RuntimeError("外部服务等待超时")
                
                # 初始化服务连接
                self.logger.info("初始化服务连接...")
                service_connector = self.service_connector
                if service_connector:
                    service_clients = await service_connector.initialize_connections()
                    return service_clients
                else:
                    raise RuntimeError("Service connector not initialized")
            
            # 运行异步初始化
            service_clients = asyncio.run(async_init())
            
            # 记录连接的服务
            connected_services = list(service_clients.keys())
            self.started_services.extend(connected_services)
            
            self.logger.info(f"✅ 外部服务连接成功: {connected_services}")
            
            return InitializationResult(
                success=True,
                stage=InitializationStage.EXTERNAL_SERVICES,
                message="外部服务连接成功",
                started_components=connected_services,
                details={
                    "mode": "service_discovery",
                    "connected_services": connected_services,
                    "consul_url": consul_url
                }
            )
            
        except Exception as e:
            error_msg = f"外部服务连接失败: {str(e)}"
            self.logger.error(error_msg)
            return InitializationResult(
                success=False,
                stage=InitializationStage.EXTERNAL_SERVICES,
                message=error_msg,
                details={"mode": "service_discovery"}
            )
    
    def _initialize_internal_modules(self) -> InitializationResult:
        """初始化内部模块（代理模式）"""
        self.current_stage = InitializationStage.INTERNAL_MODULES
        self.logger.info("阶段3: 初始化内部代理模块...")
        
        try:
            import asyncio
            from Module.LLM.LLMProxy import LLMProxy
            from Module.TTS.TTSProxy import TTSProxy
            from Module.STT.STTProxy import STTProxy
            
            # 确保服务连接器可用
            if not self.service_connector:
                raise RuntimeError("Service connector not initialized")
            
            async def async_init_proxies():
                # 初始化代理模块
                proxies = {}
                
                # LLM代理
                try:
                    llm_proxy = LLMProxy()
                    await llm_proxy.initialize()
                    proxies["llm_proxy"] = llm_proxy
                    self.logger.info("✅ LLM代理初始化成功")
                except Exception as e:
                    self.logger.error(f"❌ LLM代理初始化失败: {e}")
                    raise
                
                # TTS代理
                try:
                    tts_proxy = TTSProxy()
                    await tts_proxy.initialize()
                    proxies["tts_proxy"] = tts_proxy
                    self.logger.info("✅ TTS代理初始化成功")
                except Exception as e:
                    self.logger.error(f"❌ TTS代理初始化失败: {e}")
                    raise
                
                # STT代理
                try:
                    stt_proxy = STTProxy()
                    await stt_proxy.initialize()
                    proxies["stt_proxy"] = stt_proxy
                    self.logger.info("✅ STT代理初始化成功")
                except Exception as e:
                    self.logger.error(f"❌ STT代理初始化失败: {e}")
                    raise
                
                return proxies
            
            # 运行异步初始化
            proxies = asyncio.run(async_init_proxies())
            
            # 存储代理模块引用
            self.proxy_modules = proxies
            
            # 记录启动的模块
            proxy_names = list(proxies.keys())
            self.started_modules.extend(proxy_names)
            
            self.logger.info(f"✅ 内部代理模块初始化完成: {proxy_names}")
            
            return InitializationResult(
                success=True,
                stage=InitializationStage.INTERNAL_MODULES,
                message="内部代理模块初始化成功",
                started_components=proxy_names,
                details={
                    "mode": "proxy",
                    "initialized_proxies": proxy_names
                }
            )
            
        except Exception as e:
            error_msg = f"内部代理模块初始化失败: {str(e)}"
            self.logger.error(error_msg)
            return InitializationResult(
                success=False,
                stage=InitializationStage.INTERNAL_MODULES,
                message=error_msg,
                details={"mode": "proxy"}
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
        
        # 添加服务发现相关状态
        if self.service_discovery_manager:
            try:
                status["service_discovery"] = {
                    "consul_available": True,
                    "connected_services": self.started_services
                }
            except Exception as e:
                self.logger.warning(f"获取服务发现状态失败: {str(e)}")
                status["service_discovery"] = {
                    "consul_available": False,
                    "error": str(e)
                }
        
        # 添加代理模块状态
        if hasattr(self, 'proxy_modules'):
            status["proxy_modules"] = {
                "initialized_proxies": list(self.proxy_modules.keys()),
                "count": len(self.proxy_modules)
            }
        
        return status
    
    def perform_health_check(self) -> Dict[str, Any]:
        """执行系统健康检查"""
        health_report = {
            "timestamp": time.time(),
            "overall_healthy": True,
            "details": {}
        }
        
        try:
            # 检查服务发现管理器健康状态
            if self.service_discovery_manager:
                try:
                    # 简单的连通性检查
                    health_report["details"]["service_discovery"] = {
                        "consul_url": self.service_discovery_manager.consul_url if hasattr(self.service_discovery_manager, 'consul_url') else "unknown",
                        "status": "connected" if self.started_services else "no_services"
                    }
                except Exception as e:
                    health_report["details"]["service_discovery"] = f"检查失败: {str(e)}"
                    health_report["overall_healthy"] = False
            
            # 检查代理模块健康状态
            if hasattr(self, 'proxy_modules'):
                try:
                    proxy_health = {}
                    for proxy_name, proxy_instance in self.proxy_modules.items():
                        # 简单检查代理实例是否存在
                        proxy_health[proxy_name] = {
                            "initialized": proxy_instance is not None,
                            "type": type(proxy_instance).__name__
                        }
                    
                    health_report["details"]["proxy_modules"] = proxy_health
                    
                    # 检查是否有不健康的代理
                    for proxy_name, health_info in proxy_health.items():
                        if not health_info["initialized"]:
                            health_report["overall_healthy"] = False
                            break
                            
                except Exception as e:
                    health_report["details"]["proxy_modules"] = f"检查失败: {str(e)}"
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
            # 关闭代理模块
            if hasattr(self, 'proxy_modules'):
                try:
                    self.logger.info("关闭代理模块...")
                    for proxy_name, proxy_instance in self.proxy_modules.items():
                        try:
                            # 如果代理有清理方法，调用它
                            if hasattr(proxy_instance, 'cleanup'):
                                proxy_instance.cleanup()
                            self.logger.info(f"✅ {proxy_name} 关闭完成")
                        except Exception as e:
                            self.logger.error(f"关闭 {proxy_name} 失败: {str(e)}")
                            success = False
                    
                    del self.proxy_modules
                    self.logger.info("✅ 代理模块关闭完成")
                except Exception as e:
                    self.logger.error(f"关闭代理模块失败: {str(e)}")
                    success = False
            
            # 关闭服务连接器
            if self.service_connector:
                try:
                    self.logger.info("关闭服务连接器...")
                    # 服务连接器的清理
                    del self.service_connector
                    self.service_connector = None
                    self.logger.info("✅ 服务连接器关闭完成")
                except Exception as e:
                    self.logger.error(f"关闭服务连接器失败: {str(e)}")
                    success = False
            
            # 关闭服务发现管理器
            if self.service_discovery_manager:
                try:
                    self.logger.info("关闭服务发现管理器...")
                    # 服务发现管理器的清理
                    del self.service_discovery_manager
                    self.service_discovery_manager = None
                    self.logger.info("✅ 服务发现管理器关闭完成")
                except Exception as e:
                    self.logger.error(f"关闭服务发现管理器失败: {str(e)}")
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
