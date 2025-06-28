# Project:      Agent
# Author:       yomu
# Time:         2025/6/29
# Version:      0.1
# Description:  MySQL Service FastAPI Application

"""
MySQL微服务FastAPI应用
负责HTTP路由、服务注册和应用生命周期管理
"""

import httpx
from typing import AsyncGenerator, Dict
from logging import Logger
from contextlib import asynccontextmanager
from fastapi import FastAPI

from Module.Utils.FastapiServiceTools import (
    register_service_to_consul,
    unregister_service_from_consul
)
from Service.MySQLService.schema.request import (
    MySQLServiceSQLRequest, 
    MySQLServiceConnectRequest,
    MySQLServiceStaticTransactionRequest,
    MySQLServiceDynamicTransactionStartRequest,
    MySQLServiceDynamicTransactionCommitRequest,
    MySQLServiceDynamicTransactionRollbackRequest,
    MySQLServiceDynamicTransactionExecuteSQLRequest
)
from Service.MySQLService.schema.response import (
    MySQLServiceConnectDatabaseResponse,
    MySQLServiceQueryResponse,
    MySQLServiceInsertResponse,
    MySQLServiceDeleteResponse,
    MySQLServiceUpdateResponse,
    MySQLServiceStaticTransactionResponse,
    MySQLServiceDynamicTransactionExecuteSQLResponse,
    MySQLServiceDynamicTransactionStartResponse,
    MySQLServiceDynamicTransactionCommitResponse,
    MySQLServiceDynamicTransactionRollbackResponse,
)
from Service.MySQLService.core.connection_manager import MySQLConnectionManager
from Service.MySQLService.core.database_operations import DatabaseOperations
from Service.MySQLService.core.transaction_manager import TransactionManager


class MySQLServiceApp:
    """
    MySQL微服务FastAPI应用
    负责HTTP API和服务注册
    """
    
    def __init__(self, 
                 connection_manager: MySQLConnectionManager,
                 database_operations: DatabaseOperations,
                 transaction_manager: TransactionManager,
                 config: Dict,
                 logger: Logger):
        self.connection_manager = connection_manager
        self.database_operations = database_operations
        self.transaction_manager = transaction_manager
        self.config = config
        self.logger = logger
        
        # 从配置获取服务信息
        self.consul_url = config.get("consul_url", "http://127.0.0.1:8500")
        self.host = config.get("host", "127.0.0.1")
        self.port = config.get("port", 20050)
        self.service_name = config.get("service_name", "MySQLService")
        self.service_id = config.get("service_id", f"{self.service_name}-{self.host}:{self.port}")
        self.health_check_url = config.get("health_check_url", f"http://{self.host}:{self.port}/health")
        
        # 初始化httpx客户端（在lifespan中）
        self.client: httpx.AsyncClient = None
        
        # 初始化FastAPI应用
        self.app = FastAPI(lifespan=self.lifespan)
        
        # 设置路由
        self.setup_routes()
    
    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncGenerator[None, None]:
        """管理应用生命周期"""
        self.logger.info("Starting MySQL Service lifespan...")

        try:
            # 初始化AsyncClient
            self.client = httpx.AsyncClient(
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                timeout=httpx.Timeout(10.0, read=60.0)
            )
            self.logger.info("Async HTTP Client initialized")

            # 注册服务到Consul（目前注释掉，可根据需要启用）
            # self.logger.info("Registering service to Consul...")
            # tags = ["MySQLService"]
            # await register_service_to_consul(
            #     consul_url=self.consul_url,
            #     client=self.client,
            #     logger=self.logger,
            #     service_name=self.service_name,
            #     service_id=self.service_id,
            #     address=self.host,
            #     port=self.port,
            #     tags=tags,
            #     health_check_url=self.health_check_url
            # )
            # self.logger.info("Service registered to Consul")

            yield  # 应用正常运行

        except Exception as e:
            self.logger.error(f"Exception during lifespan: {e}")
            raise

        finally:                
            # 注销服务从Consul（目前注释掉，可根据需要启用）
            # try:
            #     self.logger.info("Deregistering service from Consul...")
            #     await unregister_service_from_consul(
            #         consul_url=self.consul_url,
            #         client=self.client,
            #         logger=self.logger,
            #         service_id=self.service_id
            #     )
            #     self.logger.info("Service deregistered from Consul")
            # except Exception as e:
            #     self.logger.error(f"Error while deregistering service: {e}")    
             
            # 清理资源
            self.cleanup_resources()
            
            # 关闭AsyncClient
            if self.client:
                self.logger.info("Shutting down Async HTTP Client")
                await self.client.aclose()
    
    def cleanup_resources(self):
        """清理资源"""
        # 清理所有事务会话
        self.transaction_manager.cleanup_all_sessions()
        
        # 关闭所有数据库连接    
        self.connection_manager.close_all_connections()
        
        self.logger.info("All resources cleaned up")
    
    def setup_routes(self):
        """设置API路由"""
        
        @self.app.get("/health", summary="健康检查接口")
        async def health_check():
            """返回服务的健康状态"""
            return {
                "status": "healthy",
                "service": self.service_name,
                "connections": self.connection_manager.get_connection_count(),
                "active_transactions": self.transaction_manager.get_active_session_count()
            }
        
        # ================================
        # 连接管理接口
        # ================================
        @self.app.post("/database/mysql/connect", 
                      summary="连接数据库接口", 
                      response_model=MySQLServiceConnectDatabaseResponse)
        async def connect(payload: MySQLServiceConnectRequest):
            """连接到MySQL数据库"""
            connection_id, connection = await self.connection_manager.connect_database(
                host=payload.host,
                port=payload.port,
                user=payload.user,
                password=payload.password,
                database=payload.database,
                charset=payload.charset
            )
            
            if connection is not None:
                from Service.MySQLService.core.response_builder import ResponseBuilder
                return ResponseBuilder.build_connect_success_response(connection_id, payload.database)
            else:
                from Service.MySQLService.core.response_builder import ResponseBuilder
                return ResponseBuilder.build_connect_error_response(payload.database, "Connection failed")

        # ================================
        # CRUD操作接口
        # ================================
        @self.app.post("/database/mysql/query", 
                      summary="查询接口", 
                      response_model=MySQLServiceQueryResponse)
        async def query(payload: MySQLServiceSQLRequest):
            """执行查询操作"""
            return await self.database_operations.query(
                payload.connection_id, payload.sql, payload.sql_args
            )

        @self.app.post("/database/mysql/insert", 
                      summary="插入接口", 
                      response_model=MySQLServiceInsertResponse)
        async def insert(payload: MySQLServiceSQLRequest):
            """执行插入操作"""
            return await self.database_operations.insert(
                payload.connection_id, payload.sql, payload.sql_args
            )

        @self.app.post("/database/mysql/update", 
                      summary="更新接口", 
                      response_model=MySQLServiceUpdateResponse)
        async def update(payload: MySQLServiceSQLRequest):
            """执行更新操作"""
            return await self.database_operations.update(
                payload.connection_id, payload.sql, payload.sql_args
            )

        @self.app.post("/database/mysql/delete", 
                      summary="删除接口", 
                      response_model=MySQLServiceDeleteResponse)
        async def delete(payload: MySQLServiceSQLRequest):
            """执行删除操作"""
            return await self.database_operations.delete(
                payload.connection_id, payload.sql, payload.sql_args
            )

        # ================================
        # 静态事务接口
        # ================================
        @self.app.post("/database/mysql/static_transaction", 
                      summary="静态事务接口", 
                      response_model=MySQLServiceStaticTransactionResponse)
        async def static_transaction(payload: MySQLServiceStaticTransactionRequest):
            """执行静态事务"""
            return await self.transaction_manager.execute_static_transaction(
                payload.connection_id, payload.sql_requests
            )

        # ================================
        # 动态事务接口
        # ================================
        @self.app.post("/database/mysql/dynamic_transaction/start", 
                      summary="开始动态事务",
                      response_model=MySQLServiceDynamicTransactionStartResponse)
        async def start_dynamic_transaction(req: MySQLServiceDynamicTransactionStartRequest):
            """开始动态事务"""
            return await self.transaction_manager.start_dynamic_transaction(req.connection_id)

        @self.app.post("/database/mysql/dynamic_transaction/execute", 
                      summary="执行动态事务", 
                      response_model=MySQLServiceDynamicTransactionExecuteSQLResponse)
        async def execute_sql(req: MySQLServiceDynamicTransactionExecuteSQLRequest):
            """在动态事务中执行SQL"""
            return await self.transaction_manager.execute_sql_in_transaction(
                req.session_id, req.sql, req.sql_args
            )

        @self.app.post("/database/mysql/dynamic_transaction/commit", 
                      summary="提交动态事务", 
                      response_model=MySQLServiceDynamicTransactionCommitResponse)
        async def commit_transaction(req: MySQLServiceDynamicTransactionCommitRequest):
            """提交动态事务"""
            return await self.transaction_manager.commit_dynamic_transaction(req.session_id)

        @self.app.post("/database/mysql/dynamic_transaction/rollback", 
                      summary="回滚动态事务", 
                      response_model=MySQLServiceDynamicTransactionRollbackResponse)
        async def rollback_transaction(req: MySQLServiceDynamicTransactionRollbackRequest):
            """回滚动态事务"""
            return await self.transaction_manager.rollback_dynamic_transaction(req.session_id)
    
    def get_app(self) -> FastAPI:
        """获取FastAPI应用实例"""
        return self.app
