"""
应用程序配置和设置管理
"""

import os
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv("${AGENT_HOME}/Service/UserService/config/.env")


class Settings:
    """应用程序设置类"""
    
    def __init__(self):
        # 服务基本信息
        self.service_name: str = "UserService"
        self.service_version: str = "1.0.0"
        
        # 服务器设置
        self.host: str = os.getenv("HOST", "127.0.0.1")
        self.port: int = int(os.getenv("PORT", "20010"))
        
        # JWT认证设置
        self.jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "your_secret_key")
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiration: int = int(os.getenv("JWT_EXPIRATION", "3600"))
        
        # 数据库设置
        self.mysql_service_url: str = os.getenv("MYSQL_SERVICE_URL", "http://127.0.0.1:20001")
        
        # Consul服务发现设置
        self.consul_url: str = os.getenv("CONSUL_URL", "http://127.0.0.1:8500")
        
        # 服务注册信息
        self.service_id: str = os.getenv("SERVICE_ID", f"{self.service_name}-{self.host}:{self.port}")
        self.health_check_url: str = os.getenv("HEALTH_CHECK_URL", f"http://{self.host}:{self.port}/health")
        
        # 文件上传设置
        self.upload_max_size: int = int(os.getenv("UPLOAD_MAX_SIZE", str(1024 * 1024 * 1024)))  # 默认1GB
        self.file_storage_path: str = os.getenv("FILE_STORAGE_PATH", "${AGENT_HOME}/Users/Files")
        
        # 日志设置
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.log_path: str = os.getenv("LOG_PATH", "InternalModule")


# 全局设置实例
settings = Settings()
