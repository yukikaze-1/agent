"""
FastAPI 用户服务应用程序
主应用工厂和配置管理
"""

import uvicorn
import httpx
import asyncio
import concurrent.futures
from typing import Dict, List, Any, AsyncGenerator, Optional
from fastapi import FastAPI
from contextlib import asynccontextmanager
from logging import Logger

from Service.UserService.app.core.config import settings
from Service.UserService.app.db.UserDatabaseManager import UserDatabaseManager
from Service.UserService.app.services.user_auth_service import UserAuthService
from Service.UserService.app.services.user_account_service import UserAccountService
from Service.UserService.app.services.user_profile_service import UserProfileService
from Service.UserService.app.services.user_file_service import UserFileService
from Service.UserService.app.api.v1.user_controller import UserController
from Module.Utils.Logger import setup_logger
from Module.Utils.FastapiServiceTools import (
    register_service_to_consul,
    unregister_service_from_consul
)


class UserServiceApp:
    """
    主用户服务应用程序类
    负责应用程序的初始化、配置和生命周期管理
    """
    
    def __init__(self):
        # 初始化日志器
        self.logger = setup_logger(name=settings.service_name, log_path="InternalModule")
        
        # 初始化HTTP客户端（将在生命周期中设置）
        self.client: Optional[httpx.AsyncClient] = None
        
        # 初始化线程池
        self.executor = concurrent.futures.ThreadPoolExecutor()
        
        # 初始化服务实例（将在生命周期中初始化）
        self.user_database_manager: Optional[UserDatabaseManager] = None
        self.auth_service: Optional[UserAuthService] = None
        self.account_service: Optional[UserAccountService] = None
        self.profile_service: Optional[UserProfileService] = None
        self.file_service: Optional[UserFileService] = None
        self.controller: Optional[UserController] = None
        
        # 创建带有生命周期管理的FastAPI应用
        self.app = FastAPI(
            title=settings.service_name,
            version=settings.service_version,
            description="User Service API",
            lifespan=self.lifespan
        )
    
    def _initialize_services(self):
        """初始化所有服务实例"""
        # 初始化数据库管理器
        self.user_database_manager = UserDatabaseManager()
        
        # 初始化认证服务
        self.auth_service = UserAuthService(
            user_core_db_agent=self.user_database_manager.user_core_agent,
            user_profile_db_agent=self.user_database_manager.user_profile_agent,
            user_login_logs_db_agent=self.user_database_manager.user_login_logs_agent,
            jwt_secret_key=settings.jwt_secret_key,
            jwt_algorithm=settings.jwt_algorithm,
            jwt_expiration=settings.jwt_expiration,
            logger=self.logger
        )
        
        # 初始化账户管理服务
        self.account_service = UserAccountService(
            user_core_db_agent=self.user_database_manager.user_core_agent,
            user_account_actions_db_agent=self.user_database_manager.user_account_actions_agent,
            user_database_manager=self.user_database_manager,
            password_hasher=self.auth_service,
            token_verifier=self.auth_service,
            logger=self.logger
        )
        
        # 初始化用户资料服务
        self.profile_service = UserProfileService(
            user_core_db_agent=self.user_database_manager.user_core_agent,
            user_profile_db_agent=self.user_database_manager.user_profile_agent,
            user_settings_db_agent=self.user_database_manager.user_settings_agent,
            user_account_actions_db_agent=self.user_database_manager.user_account_actions_agent,
            token_verifier=self.auth_service,
            logger=self.logger
        )
        
        # 初始化文件管理服务
        self.file_service = UserFileService(
            user_database_manager=self.user_database_manager,
            user_account_actions_db_agent=self.user_database_manager.user_account_actions_agent,
            token_verifier=self.auth_service,
            upload_file_max_size=settings.upload_max_size,
            file_storage_path=settings.file_storage_path,
            logger=self.logger
        )
        
        # 初始化控制器（设置所有路由）
        self.controller = UserController(
            app=self.app,
            auth_service=self.auth_service,
            account_service=self.account_service,
            profile_service=self.profile_service,
            file_service=self.file_service,
            logger=self.logger
        )
    
    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncGenerator[None, None]:
        """应用程序生命周期管理"""
        # 启动阶段
        self.logger.info(f"正在启动 {settings.service_name} v{settings.service_version}")
        
        # 初始化HTTP客户端
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(10.0, read=60.0)
        )
        self.logger.info("HTTP客户端已初始化")
        
        # 初始化所有服务
        self._initialize_services()
        self.logger.info("所有服务已初始化")
        
        # 初始化数据库连接
        try:
            if self.user_database_manager:
                await self.user_database_manager.init_all_connections()
                self.logger.info("数据库连接已初始化")
        except Exception as e:
            self.logger.warning(f"Failed to initialize database connections: {e}")
        
        # 注册服务到Consul
        try:
            # 确保Consul URL包含协议前缀
            consul_url = settings.consul_url
            if not consul_url.startswith("http://") and not consul_url.startswith("https://"):
                consul_url = "http://" + consul_url
                self.logger.info(f"Consul URL adjusted to include http://: {consul_url}")
            
            self.logger.info("Registering service to Consul...")
            tags = [settings.service_name, "UserService"]
            await register_service_to_consul(
                consul_url=consul_url,
                client=self.client,
                logger=self.logger,
                service_name=settings.service_name,
                service_id=settings.service_id,
                address=settings.host,
                port=settings.port,
                tags=tags,
                health_check_url=settings.health_check_url
            )
            self.logger.info("Service registered to Consul successfully")
        except Exception as e:
            self.logger.error(f"Failed to register service to Consul: {e}")
            # 不因为Consul注册失败而停止服务启动
        
        self.logger.info(f"{settings.service_name}已成功启动 {settings.host}:{settings.port}")
        
        yield  # 应用程序运行中
        
        # 关闭阶段
        self.logger.info(f"正在关闭 {settings.service_name}")
        
        # 从Consul注销服务
        try:
            consul_url = settings.consul_url
            if not consul_url.startswith("http://") and not consul_url.startswith("https://"):
                consul_url = "http://" + consul_url
                
            self.logger.info("Deregistering service from Consul...")
            await unregister_service_from_consul(
                consul_url=consul_url,
                client=self.client,
                logger=self.logger,
                service_id=settings.service_id
            )
            self.logger.info("Service deregistered from Consul successfully")
        except Exception as e:
            self.logger.error(f"Error while deregistering service from Consul: {e}")
        
        # 清理数据库连接
        if self.user_database_manager:
            await self.user_database_manager.cleanup()
            self.logger.info("数据库连接已关闭")
        
        # 关闭HTTP客户端
        if self.client:
            await self.client.aclose()
            self.logger.info("HTTP客户端已关闭")
        
        # 关闭线程池
        self.executor.shutdown(wait=True)
        self.logger.info("线程池已关闭")
        
        self.logger.info(f"{settings.service_name}关闭完成")
    
    def run(self):
        """运行应用程序"""
        uvicorn.run(
            self.app,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower()
        )


# 创建全局应用实例
def create_app() -> FastAPI:
    """应用程序工厂函数"""
    app_instance = UserServiceApp()
    return app_instance.app


# 全局app变量，供uvicorn使用
app = create_app()


# 直接执行入口
if __name__ == "__main__":
    app_instance = UserServiceApp()
    app_instance.run()
