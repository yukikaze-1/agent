# Project:      Agent
# Author:       yomu
# Time:         2025/6/29 (Refactored)
# Version:      0.2
# Description:  Refactored MySQL Service

"""
重构后的MySQL服务
采用模块化设计，职责分离清晰
"""

import uvicorn
from typing import Dict, Optional
from dotenv import dotenv_values

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config
from Service.MySQLService.core import (
    MySQLConnectionManager,
    DatabaseOperations,
    TransactionManager,
    MySQLServiceApp
)


class MySQLService:
    """
    重构后的MySQL微服务主类
    
    采用组合模式，将不同职责分配给专门的管理器：
    - MySQLConnectionManager: 连接管理
    - DatabaseOperations: CRUD操作  
    - TransactionManager: 事务管理
    - MySQLServiceApp: FastAPI应用和路由
    """
    
    def __init__(self):
        # 初始化日志
        self.logger = setup_logger(name="MySQLService", log_path="InternalModule")
        self.logger.info("Initializing MySQL Service...")
        
        # 加载配置
        self._load_configuration()
        
        # 初始化核心组件
        self._initialize_components()
        
        self.logger.info("MySQL Service initialized successfully")
    
    def _load_configuration(self):
        """加载和验证配置"""
        self.logger.info("Loading configuration...")
        
        # 加载环境变量和配置
        self.env_vars = dotenv_values("${AGENT_HOME}/Service/MySQLService/.env")
        self.config_path = self.env_vars.get("MYSQL_SERVICE_CONFIG_PATH", "")
        self.config: Dict = load_config(
            config_path=self.config_path, 
            config_name='MySQLService', 
            logger=self.logger
        )
        
        # 验证配置文件
        required_keys = ["consul_url", "host", "port", "service_name", "service_id", "health_check_url"]
        validate_config(required_keys, self.config, self.logger)
        
        # 处理Consul URL
        self.consul_url: str = self.config.get("consul_url", "http://127.0.0.1:8500")
        if not self.consul_url.startswith("http://") and not self.consul_url.startswith("https://"):
            self.consul_url = "http://" + self.consul_url
            self.config["consul_url"] = self.consul_url
            self.logger.info(f"Consul URL adjusted to include http://: {self.consul_url}")
        
        self.logger.info("Configuration loaded and validated")
    
    def _initialize_components(self):
        """初始化各个组件"""
        self.logger.info("Initializing core components...")
        
        # 初始化连接管理器
        self.connection_manager = MySQLConnectionManager(logger=self.logger)
        self.logger.debug("Connection manager initialized")
        
        # 初始化数据库操作管理器
        self.database_operations = DatabaseOperations(
            connection_manager=self.connection_manager,
            logger=self.logger
        )
        self.logger.debug("Database operations manager initialized")
        
        # 初始化事务管理器
        self.transaction_manager = TransactionManager(
            connection_manager=self.connection_manager,
            logger=self.logger
        )
        self.logger.debug("Transaction manager initialized")
        
        # 初始化FastAPI应用
        self.service_app = MySQLServiceApp(
            connection_manager=self.connection_manager,
            database_operations=self.database_operations,
            transaction_manager=self.transaction_manager,
            config=self.config,
            logger=self.logger
        )
        self.logger.debug("Service application initialized")
        
        # 获取FastAPI应用实例
        self.app = self.service_app.get_app()
        
        self.logger.info("All core components initialized")
    
    def get_service_info(self) -> Dict:
        """
        获取服务信息
        
        :return: 服务信息字典
        """
        return {
            "service_name": self.config.get("service_name"),
            "version": "0.2",
            "host": self.config.get("host"),
            "port": self.config.get("port"),
            "active_connections": self.connection_manager.get_connection_count(),
            "active_transactions": self.transaction_manager.get_active_session_count(),
            "connection_ids": self.connection_manager.get_connection_ids()
        }
    
    def run(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        启动服务
        
        :param host: 主机地址，如果为None则使用配置中的值
        :param port: 端口号，如果为None则使用配置中的值
        """
        run_host = host or self.config.get("host", "127.0.0.1")
        run_port = port or self.config.get("port", 20050)
        
        self.logger.info(f"Starting MySQL Service on {run_host}:{run_port}")
        
        try:
            uvicorn.run(self.app, host=run_host, port=run_port)
        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            raise
    
    def shutdown(self):
        """
        优雅关闭服务
        """
        self.logger.info("Shutting down MySQL Service...")
        
        try:
            # 清理资源
            self.service_app.cleanup_resources()
            self.logger.info("Service shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def __del__(self):
        """
        析构函数
        """
        try:
            self.shutdown()
        except:
            pass  # 避免析构函数中的异常


def main():
    """主函数"""
    try:
        service = MySQLService()
        service.run()
    except KeyboardInterrupt:
        print("\nService stopped by user")
    except Exception as e:
        print(f"Service failed to start: {e}")


if __name__ == "__main__":
    main()
