# Project:      Agent
# Author:       yomu
# Time:         2024/12/12
# Version:      0.1
# Description:  MySQLService definition

"""
    MySQL的代理
    提供MySQL的封装
    使用pymsql
"""

import uvicorn
import httpx
import asyncio
import uuid
import pymysql
import traceback
from datetime import datetime
from pymysql import Connection
from pymysql.cursors import Cursor
from logging import Logger
from typing import List, Optional, Tuple, Dict, Any, AsyncGenerator
from dotenv import dotenv_values
from fastapi import FastAPI, Form, Body, HTTPException
from pydantic import BaseModel, Field, model_validator
from contextlib import asynccontextmanager

import pymysql.cursors

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config
from Module.Utils.ToolFunctions import retry
from Module.Utils.FastapiServiceTools import (
    get_service_instances,
    update_service_instances_periodically,
    register_service_to_consul,
    unregister_service_from_consul
)

from Service.MySQLService.schema.response import (
    MySQLServiceResponseErrorCode,
    MySQLServiceErrorDetail,
    MySQLServiceConnectDatabaseResponseData,    
    MySQLServiceConnectDatabaseResponse,
    MySQLServiceQueryResponseData,
    MySQLServiceQueryResponse,
    MySQLServiceInsertResponseData,
    MySQLServiceInsertResponse,
    MySQLServiceDeleteResponseData,
    MySQLServiceDeleteResponse,
    MySQLServiceUpdateResponseData,
    MySQLServiceUpdateResponse,
    MySQLServiceStaticTransactionSQLExecutionResult,
    MySQLServiceStaticTransactionResponseData,
    MySQLServiceStaticTransactionResponse,
    MySQLServiceDynamicTransactionExecuteSQLResponse,
    MySQLServiceDynamicTransactionStartResponse,
    MySQLServiceDynamicTransactionCommitResponse,
    MySQLServiceDynamicTransactionRollbackResponse,
)
from Service.MySQLService.schema.request import (
    MySQLServiceSQLRequest, 
    MySQLServiceConnectRequest,
    MySQLServiceStaticTransactionSQL,
    MySQLServiceStaticTransactionRequest,
    MySQLServiceDynamicTransactionStartRequest,
    MySQLServiceDynamicTransactionCommitRequest,
    MySQLServiceDynamicTransactionRollbackRequest,
    MySQLServiceDynamicTransactionExecuteSQLRequest
)


class MySQLServiceDynamicTransactionSession:
    """  动态事务会话类，用于管理 MySQL 事务。"""
    def __init__(self, connection: pymysql.connections.Connection):
        self.connection = connection
        self.cursor = connection.cursor()
        self.in_transaction = True
        self.executed_sql_count: int = 0    # 记录执行的SQL语句数量
        self.affected_rows_total: int = 0   # 记录总的受影响行数

    def close(self):
        self.cursor.close()
        # self.connection.close()
        

class MySQLService:
    """
    MySQL fastapi 微服务类
    用于管理 MySQL 数据库连接池。
    提供单条SQL语句的执行。
    提供静态、动态事务执行。
    """
    def __init__(self):
        self.logger = setup_logger(name="MySQLService", log_path="InternalModule")

        # 加载环境变量和配置
        self.env_vars = dotenv_values("${AGENT_HOME}/Module/Utils/Database/.env")
        self.config_path = self.env_vars.get("MYSQL_SERVICE_CONFIG_PATH", "")
        self.config: Dict = load_config(config_path=self.config_path, config_name='MySQLService', logger=self.logger)
        
        # 验证配置文件
        required_keys = ["consul_url", "host", "port" ,"service_name", "service_id", "health_check_url"]
        validate_config(required_keys, self.config, self.logger)
        
        # Consul URL，确保包含协议前缀
        self.consul_url: str = self.config.get("consul_url", "http://127.0.0.1:8500")
        if not self.consul_url.startswith("http://") and not self.consul_url.startswith("https://"):
            self.consul_url = "http://" + self.consul_url
            self.logger.info(f"Consul URL adjusted to include http://: {self.consul_url}") 
        
        # 微服务本身地址
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 20050)
        
        # 服务注册信息
        self.service_name = self.config.get("service_name", "OllamaAgent")
        self.service_id = self.config.get("service_id", f"{self.service_name}-{self.host}:{self.port}")
        self.health_check_url = self.config.get("health_check_url", f"http://{self.host}:{self.port}/health")
        
           
        # MySQLService连接mysql的序号，每连接一个mysql数据库，该ids++
        self.ids = 0
        
        # 存储 (connection_id, connection对象) 的字典
        self.connections: Dict[int, pymysql.connections.Connection] = {}
        
        # 存储动态事务会话(transaction session token, transaction session对象) 的字典
        self.dynamic_transaction_sessions: Dict[str, MySQLServiceDynamicTransactionSession] = {}

        # 初始化 httpx.AsyncClient
        self.client:  httpx.AsyncClient   # 在lifespan中初始化
        
        # 初始化 FastAPI 应用，使用生命周期管理
        self.app = FastAPI(lifespan=self.lifespan)
                
        # 设置路由
        self.setup_routes()
        
    
    @asynccontextmanager
    async def lifespan(self, app: FastAPI)-> AsyncGenerator[None, None]:
        """管理应用生命周期"""
        self.logger.info("Starting lifespan...")

        try:
            # 初始化 AsyncClient
            self.client = httpx.AsyncClient(
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                timeout=httpx.Timeout(10.0, read=60.0)
            )
            self.logger.info("Async HTTP Client Initialized")

            # # 注册服务到 Consul
            # self.logger.info("Registering service to Consul...")
            # tags = ["MySQLService"]
            # await register_service_to_consul(consul_url=self.consul_url,
            #                                  client=self.client,
            #                                  logger=self.logger,
            #                                  service_name=self.service_name,
            #                                  service_id=self.service_id,
            #                                  address=self.host,
            #                                  port=self.port,
            #                                  tags=tags,
            #                                  health_check_url=self.health_check_url)
            # self.logger.info("Service registered to Consul.")

            yield  # 应用正常运行

        except Exception as e:
            self.logger.error(f"Exception during lifespan: {e}")
            raise

        finally:                
            # 注销服务从 Consul
            # try:
            #     self.logger.info("Deregistering service from Consul...")
            #     await unregister_service_from_consul(consul_url=self.consul_url,
            #                                          client=self.client,
            #                                          logger=self.logger,
            #                                          service_id=self.service_id)
            #     self.logger.info("Service deregistered from Consul.")
            # except Exception as e:
            #     self.logger.error(f"Error while deregistering service: {e}")    
             
            # 关闭所有数据库连接    
            self.close_all()
            
            # 关闭 AsyncClient
            self.logger.info("Shutting down Async HTTP Client")
            if self.client:
                await self.client.aclose() 
            
        
    # --------------------------------
    # 设置路由
    # --------------------------------
    def setup_routes(self):
        """设置 API 路由"""
        
        @self.app.get("/health", summary="健康检查接口")
        async def health_check():
            """返回服务的健康状态"""
            return {"status": "healthy"}
        
        
        @self.app.post("/database/mysql/insert", summary="插入接口", response_model=MySQLServiceInsertResponse)
        async def insert(payload: MySQLServiceSQLRequest):
            return await self._insert(payload.connection_id, payload.sql, payload.sql_args)

        
        @self.app.post("/database/mysql/update", summary="更新接口", response_model=MySQLServiceUpdateResponse)
        async def update(payload: MySQLServiceSQLRequest):
            return await self._update(payload.connection_id, payload.sql, payload.sql_args)


        @self.app.post("/database/mysql/delete", summary= "删除接口", response_model=MySQLServiceDeleteResponse)
        async def delete(payload: MySQLServiceSQLRequest):
            return await self._delete(payload.connection_id, payload.sql, payload.sql_args)


        @self.app.post("/database/mysql/query", summary= "查询接口", response_model=MySQLServiceQueryResponse)
        async def query(payload: MySQLServiceSQLRequest):
            return await self._query(payload.connection_id, payload.sql, payload.sql_args)


        @self.app.post("/database/mysql/connect", summary= "连接接口", response_model=MySQLServiceConnectDatabaseResponse)
        async def connect(payload: MySQLServiceConnectRequest):
            return await self._connect_database(payload.host, payload.port, payload.user, payload.password, payload.database,  payload.charset)


        @self.app.post("/database/mysql/static_transaction", summary="静态事务接口", response_model=MySQLServiceStaticTransactionResponse)
        async def transaction(payload: MySQLServiceStaticTransactionRequest):
            return await self._static_transaction(payload.connection_id, payload.sql_requests)


        @self.app.post("/database/mysql/dynamic_transaction/start", summary="开始动态事务",response_model=MySQLServiceDynamicTransactionStartResponse)
        async def start_dynamic_transaction(req: MySQLServiceDynamicTransactionStartRequest):
            return await self._start_dynamic_transaction(req.connection_id)


        @self.app.post("/database/mysql/dynamic_transaction/execute", summary="执行动态事务", response_model=MySQLServiceDynamicTransactionExecuteSQLResponse)
        async def execute_sql(req: MySQLServiceDynamicTransactionExecuteSQLRequest):
            return await self._execute_sql(req.session_id, req.sql, req.sql_args)


        @self.app.post("/database/mysql/dynamic_transaction/commit", summary="提交动态事务", response_model=MySQLServiceDynamicTransactionCommitResponse)
        async def commit_transaction(req: MySQLServiceDynamicTransactionCommitRequest):
            return await self._commit_transaction(req.session_id)


        @self.app.post("/database/mysql/dynamic_transaction/rollback", summary="回滚动态事务", response_model=MySQLServiceDynamicTransactionRollbackResponse)
        async def rollback_transaction(req: MySQLServiceDynamicTransactionRollbackRequest):
            return await self._rollback_transaction(req.session_id)

    # --------------------------------
    # 功能函数
    # --------------------------------
    async def _start_dynamic_transaction(self, connection_id: int) -> MySQLServiceDynamicTransactionStartResponse:
        """
        开始一个动态事务。
        
        :param connection_id: 数据库连接ID
        """
        operator = "Transaction"

        # 获取链接对象
        connection = self.connections.get(connection_id)

        # 链接ID不存在
        if connection is None:
            return MySQLServiceDynamicTransactionStartResponse(
                operator=operator,
                message=f"Transaction failed",
                result=False,
                err_code=MySQLServiceResponseErrorCode.CONNECTION_ID_NOT_EXISTS,
                errors=[MySQLServiceErrorDetail(
                    code=MySQLServiceResponseErrorCode.CONNECTION_ID_NOT_EXISTS,
                    message=f"Connection ID '{connection_id}' does not exist.",
                    field="connection_id",
                    hint="Please check if the connection ID is correct."
                )]
            )

        try:
            # 创建一个新的事务上下文、
            
            # 创建事务会话id
            session_id = str(uuid.uuid4())
                
            # 创建事务会话
            session = MySQLServiceDynamicTransactionSession(connection=connection)
            
            # 开启事务
            connection.begin()
            self.dynamic_transaction_sessions[session_id] = session

            self.logger.info(f"Dynamic transaction started. session_id: {session_id}")

            return MySQLServiceDynamicTransactionStartResponse(
                operator=operator,
                message="Transaction started.",
                result=True,
                session_id=session_id
            )

        except Exception as e:
            self.logger.error(
                f"Failed to start dynamic transaction. connection_id: {connection_id}, error: {e}"
            )
            return MySQLServiceDynamicTransactionStartResponse(
                operator=operator,
                message="Transaction failed.",
                result=False,
                err_code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                errors=[MySQLServiceErrorDetail(
                    code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                    message="Failed to start dynamic transaction.",
                    hint="Please try again later."
                )]   
            )
            

    async def _execute_sql(self, 
                           session_id: str,
                           sql: str,
                           sql_args: List[Any] | Dict[str, Any] | None = None
                           ) -> MySQLServiceDynamicTransactionExecuteSQLResponse:
        """
        在动态事务中执行 SQL 语句。
        
        :param session_id: 事务上下文 ID
        :param sql: 要执行的 SQL 语句
        :param sql_args: SQL 语句参数
        """
        operator = "Transaction Execute SQL"
        
        # 获取事务会话对象
        transaction_session = self.dynamic_transaction_sessions.get(session_id)

        # 会话不存在
        if transaction_session is None:
            return MySQLServiceDynamicTransactionExecuteSQLResponse(
                operator=operator,
                message=f"Transaction failed",
                result=False,
                err_code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                errors=[MySQLServiceErrorDetail(
                    code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                    message=f"Session ID '{session_id}' does not exist.",
                    field="session_id",
                    hint="Please check if the session ID is correct."
                )]
            )

        try:
            self.logger.info(f"Executing SQL in dynamic transaction. session_id: {session_id}, sql: {sql}, sql_args: {sql_args}")
            # 执行 SQL 语句
            with transaction_session.connection.cursor() as cursor:
                cursor.execute(sql, sql_args or [])
                transaction_session.executed_sql_count += 1
                affected_rows = cursor.rowcount
                last_insert_id = cursor.lastrowid      
                transaction_session.affected_rows_total += affected_rows
                          
                self.logger.info(f"Executed SQL in dynamic transaction. session_id: {session_id}, sql: {sql}, sql_args: {sql_args}, ")

            return MySQLServiceDynamicTransactionExecuteSQLResponse(
                operator=operator,
                message="SQL executed successfully.",
                result=True,
                affected_rows=affected_rows,
                last_insert_id=last_insert_id,
            )

        except Exception as e:
            self.logger.error(
                f"Failed to execute SQL. session_id: {session_id}, error: {e}\n{traceback.format_exc()}"
            )
            # 回滚事务
            transaction_session.connection.rollback()
            # 关闭会话
            transaction_session.close()
            # 从会话列表中移除
            self.dynamic_transaction_sessions.pop(session_id, None)
            return MySQLServiceDynamicTransactionExecuteSQLResponse(
                operator=operator,
                message="Failed to execute SQL.",
                result=False,
                err_code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                errors=[MySQLServiceErrorDetail(
                    code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                    message=str(e),
                    field="sql",
                    hint="Please check the SQL syntax and parameters or try again later."
                )]
            )
    
    
    async def _commit_transaction(self, session_id: str) -> MySQLServiceDynamicTransactionCommitResponse:
        """
        提交动态事务。
        
        :param session_id: 事务上下文 ID
        """
        operator = "Transaction Commit"
        
        # 获取事务会话对象
        transaction_session = self.dynamic_transaction_sessions.get(session_id)

        # 会话不存在
        if transaction_session is None:
            return MySQLServiceDynamicTransactionCommitResponse(
                operator=operator,
                message=f"Transaction commit failed",
                result=False,
                err_code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                errors=[MySQLServiceErrorDetail(
                    code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                    message=f"Session ID '{session_id}' does not exist.",
                    field="session_id",
                    hint="Please check if the session ID is correct."
                )]
            )

        try:
            transaction_session.connection.commit()
            self.logger.info(f"Dynamic transaction committed. session_id: {session_id}")

            result = MySQLServiceDynamicTransactionCommitResponse(
                operator=operator,
                message="Transaction committed successfully.",
                result=True,
                session_id=session_id,
                commit_time=datetime.now(),
                affected_rows=transaction_session.affected_rows_total,
                executed_sql_count=transaction_session.executed_sql_count
            )
        except Exception as e:
            self.logger.error(
                f"Failed to commit dynamic transaction. session_id: {session_id}, error: {e}"
            )
            result = MySQLServiceDynamicTransactionCommitResponse(
                operator=operator,
                message="Transaction commit failed.",
                result=False,
                err_code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                errors=[MySQLServiceErrorDetail(
                    code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                    message=str(e),
                    field="commit",
                    hint="Please check connection or server status"
                )]
            )
        finally:
            transaction_session.close()
            self.dynamic_transaction_sessions.pop(session_id, None)

        return result

    
    async def _static_transaction(self,
                           connection_id: int,
                           statements: List[MySQLServiceStaticTransactionSQL]
                           ) -> MySQLServiceStaticTransactionResponse:
        """
        处理一组 SQL 请求作为一个静态事务。
        
        :param connection_id: 数据库连接ID
        :param statements: 要执行的 SQL 请求列表，每个请求包含 SQL 语句和参数
        """
        operator = "Transaction"
            
        # 获取链接对象
        connection = self.connections.get(connection_id)
        
        # 链接ID不存在
        if connection is None:
            return MySQLServiceStaticTransactionResponse(
                operator=operator,
                message=f"Transaction failed",
                result=False,
                err_code=MySQLServiceResponseErrorCode.CONNECTION_ID_NOT_EXISTS,
                errors=[MySQLServiceErrorDetail(
                    code=MySQLServiceResponseErrorCode.CONNECTION_ID_NOT_EXISTS,
                    message=f"Connection ID '{connection_id}' does not exist.",
                    field="connection_id",
                    hint="Please check if the connection ID is correct."
                )]
            )
        
        try:
            results = []
            with connection.cursor() as cursor:
                 # 显式开启事务
                connection.begin()
                
                # 执行每个 SQL 请求
                for i, sql_request in enumerate(statements):
                    cursor.execute(sql_request.sql, sql_request.sql_args or [])
                    # 记录执行结果
                    self.logger.debug(f"[Transaction] Executed: {sql_request.sql} | args={sql_request.sql_args}")
                    # 将执行结果添加到结果列表
                    results.append(
                        MySQLServiceStaticTransactionSQLExecutionResult(
                            index=i,
                            sql=sql_request.sql,
                            affected_rows=cursor.rowcount
                        )
                    )

                # 提交事务
                connection.commit()
                self.logger.info(f"Transaction success. connection_id: {connection_id}")

            # 执行成功，返回Response
            return MySQLServiceStaticTransactionResponse(
                operator=operator,
                message="Transaction success.",
                result=True,
                data=MySQLServiceStaticTransactionResponseData(
                    operator="static transaction",
                    result=True,
                    message=f"Static transaction execute success.",
                    sql_count=len(statements),
                    transaction_results=results
                )
            )
            
        except Exception as e:
            connection.rollback()
            self.logger.error(
                f"Transaction failed while executing SQL statements:{[sql_request.sql for sql_request in statements]}."
                f"connection_id: {connection_id}, error: {e}"
            )

            return MySQLServiceStaticTransactionResponse(
                operator=operator,
                message=f"Transaction failed.",
                result=False,
                err_code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                errors=[
                    MySQLServiceErrorDetail(
                        code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                        message=str(e),
                        field="transaction",
                        sql=[sql_request.sql for sql_request in statements],
                        hint="Please check the SQL syntax and parameters or try again later."
                    )
                ]
            )
            
   
    async def _rollback_transaction(self, session_id: str) -> MySQLServiceDynamicTransactionRollbackResponse:
        """
        回滚动态事务。
        
        :param session_id: 事务上下文 ID
        """
        operator = "Transaction Rollback"
        
        # 获取事务会话对象
        transaction_session = self.dynamic_transaction_sessions.get(session_id)

        # 会话不存在
        if transaction_session is None:
            return MySQLServiceDynamicTransactionRollbackResponse(
                operator=operator,
                message=f"Transaction rollback failed",
                result=False,
                err_code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                errors=[MySQLServiceErrorDetail(
                    code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                    message=f"Session ID '{session_id}' does not exist.",
                    field="session_id",
                    hint="Please check if the session ID is correct."
                )]
            )

        try:
            # 回滚事务
            transaction_session.connection.rollback()
            self.logger.info(f"Dynamic transaction rolled back. session_id: {session_id}")
            
        finally:
            # 关闭会话
            transaction_session.close()
            # 从会话列表中移除
            self.dynamic_transaction_sessions.pop(session_id, None)

            return MySQLServiceDynamicTransactionRollbackResponse(
                operator=operator,
                message="Transaction rolled back successfully.",
                result=True
            )
            
            
    async def _query(self, connection_id: int, sql: str, sql_args: List[Any]) -> MySQLServiceQueryResponse:
        """
        查询
        
        :param connection_id: 数据库连接ID
        :param sql: SQL语句
        :param sql_args: SQL语句参数

        Returns: QueryResponse
        """
        operator = "Query"
        
        # 获取链接ID
        connection=self.connections.get(connection_id)

        # 链接ID不存在
        if connection is None:
            return MySQLServiceQueryResponse(
                operator=operator,
                message=f"Query failed",
                result=False,
                err_code=MySQLServiceResponseErrorCode.CONNECTION_ID_NOT_EXISTS,
                errors=[MySQLServiceErrorDetail(
                    code=MySQLServiceResponseErrorCode.CONNECTION_ID_NOT_EXISTS,
                    message=f"Connection ID '{connection_id}' does not exist.",
                    field="connection_id",
                    hint="Please check if the connection ID is correct."
                )]
            )

        try:
            # 查询
            query_data: List[MySQLServiceQueryResponseData] = await self._query_with_retry(connection=connection, sql=sql, sql_args=sql_args)
            self.logger.debug(f"Query success. sql: '{sql}', sql_args:'{sql_args}'")
            
            return MySQLServiceQueryResponse(
                operator=operator,
                message="Query success.",
                result=True,
                data=query_data
            )
        except Exception as e:
            message = f"Query failed after 3 retries! Error:{str(e)}"
            self.logger.error(message)
            
            return MySQLServiceQueryResponse(
                operator=operator,
                message=message,
                result=False,
                err_code=MySQLServiceResponseErrorCode.QUERY_DATABASE_FAILED,
                errors=[MySQLServiceErrorDetail(
                    code=MySQLServiceResponseErrorCode.QUERY_DATABASE_FAILED,
                    message=message,
                    field="sql",
                    hint="Please check the SQL syntax and parameters or try again later."
                )]
            )
                

    @retry(retries=3, delay=1.0, backoff=2.0, exceptions=(pymysql.MySQLError,), on_failure=lambda e: print(f"[ERROR] 最终重试失败: {e}"))  
    async def _query_with_retry(self, connection: Connection, sql: str, sql_args: List[Any]) -> List[MySQLServiceQueryResponseData]:
        """
        查询 (附带重试机制)
        
        :param connection: 数据库连接对象
        :param sql: SQL语句
        :param sql_args: SQL语句参数

        Returns: List[QueryResult]
        """

        try:
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, sql_args)
                query_result = cursor.fetchall()
                return [
                    MySQLServiceQueryResponseData(
                        column_names=list(query_result[0].keys()) if query_result else [],
                        rows=[list(row.values()) for row in query_result] if query_result else [],
                        row_count=len(query_result)
                    )
                ]
        except Exception as e:
            self.logger.error(f"Query failed!in function: _query_with_retry：ERROR:{e}\n{traceback.format_exc()}")
            raise


    async def _insert(self, connection_id: int, sql: str, sql_args: List[Any])-> MySQLServiceInsertResponse:
        """
        插入
        
        :param connection_id: 数据库连接ID
        :param sql: SQL语句
        :param sql_args: SQL语句参数

        Returns: InsertResponse
        """
        
        operator = "Insert"
        
        # 获取链接ID
        connection=self.connections.get(connection_id)
        
        # 链接ID不存在
        if connection is None:
            return MySQLServiceInsertResponse(
                operator=operator,
                message=f"Insert failed",
                result=False,
                err_code=MySQLServiceResponseErrorCode.CONNECTION_ID_NOT_EXISTS,
                errors=[MySQLServiceErrorDetail(
                    code=MySQLServiceResponseErrorCode.CONNECTION_ID_NOT_EXISTS,
                    message=f"Connection ID '{connection_id}' does not exist.",
                    field="connection_id",
                    hint="Please check if the connection ID is correct."
                )]
            )
        

        try:
            rows_affected =  await self._insert_with_retry(connection=connection, sql=sql, sql_args=sql_args)
            self.logger.info(f"Insert success. sql: '{sql}', sql_args:'{sql_args}'")
            
            #插入成功 返回Response
            return MySQLServiceInsertResponse(
                    operator=operator,
                    message=f"Insert success.",
                    result=True,
                    data=MySQLServiceInsertResponseData(rows_affected=rows_affected)
            )
        except Exception as e:
                message= f"Insert failed after 3 retries! Error:{str(e)}"
                self.logger.error(message)
                
                # 插入失败，且已重试三次，返回Response
                return MySQLServiceInsertResponse(
                    operator=operator,
                    message=message,
                    result=False,
                    err_code=MySQLServiceResponseErrorCode.INSERT_DATABASE_FAILED,
                    errors=[MySQLServiceErrorDetail(
                        code=MySQLServiceResponseErrorCode.INSERT_DATABASE_FAILED,
                        message=message,
                        field="database",
                        hint="Unknown error in database, please check the paramters or try again later."
                    )]
                )


    @retry(retries=3, delay=1.0, backoff=2.0, exceptions=(pymysql.MySQLError,), on_failure=lambda e: print(f"[ERROR] 最终重试失败: {e}"))
    async def _insert_with_retry(self, connection: Connection, sql: str, sql_args: List[Any]) -> int:
        """
        插入
        
        :param connection: 数据库连接
        :param sql: SQL语句
        :param sql_args: SQL语句参数

        Returns: None
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, sql_args)
                connection.commit()
                return cursor.rowcount
        except Exception as e:
            self.logger.error(f"insert failed!：{e}\n{traceback.format_exc()}")
            raise
        
        
    async def _delete(self, connection_id: int, sql: str, sql_args: List[Any])-> MySQLServiceDeleteResponse:
        """
        删除数据

        :param connection_id: 数据库连接ID
        :param sql: SQL语句
        :param sql_args: SQL语句参数
        
        Returns:
        """
        
        operator = "Delete"

        # 获取链接ID
        connection=self.connections.get(connection_id)

        # 链接ID不存在
        if connection is None:
            return MySQLServiceDeleteResponse(
                operator=operator,
                message=f"Delete failed",
                result=False,
                data=MySQLServiceDeleteResponseData(rows_affected=-1),
                err_code=MySQLServiceResponseErrorCode.CONNECTION_ID_NOT_EXISTS,
                errors=[MySQLServiceErrorDetail(
                    code=MySQLServiceResponseErrorCode.CONNECTION_ID_NOT_EXISTS,
                    message=f"Connection ID '{connection_id}' does not exist.",
                    field="connection_id",
                    hint="Please check if the connection ID is correct."
                )]
            )
            
        try:
            rows_affected =  await self._delete_with_retry(connection=connection, sql=sql, sql_args=sql_args)
            self.logger.info(f"Delete success. sql: '{sql}', sql_args:'{sql_args}'")
            
            # 删除成功 返回Response
            return MySQLServiceDeleteResponse(
                operator=operator,
                message=f"Delete success.",
                result=True,
                data=MySQLServiceDeleteResponseData(rows_affected=rows_affected)
            )
        except Exception as e:
            message = f"Delete failed after 3 retries! Error:{str(e)}"
            self.logger.error(message)
            
            # 删除失败，且已重试三次，返回Response
            return MySQLServiceDeleteResponse(
                operator=operator,
                message=message,
                result=False,
                data= MySQLServiceDeleteResponseData(rows_affected=-1),
                err_code=MySQLServiceResponseErrorCode.DELETE_DATABASE_FAILED,
                level="error"
            )
            
    
    @retry(retries=3, delay=1.0, backoff=2.0, exceptions=(pymysql.MySQLError,), on_failure=lambda e: print(f"[ERROR] 最终重试失败: {e}"))  
    async def _delete_with_retry(self, connection: Connection, sql: str, sql_args: List[Any]) -> int:
        """
        删除数据（带重试机制）

        :param connection: 数据库连接
        :param sql: SQL语句
        :param sql_args: SQL语句参数

        Returns: 删除了几行
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, sql_args)
                connection.commit()
                
                # 检查是否删除了记录
                if cursor.rowcount > 0:
                    message = f"Delete success, {cursor.rowcount} rows affected"
                    self.logger.info(message)
                else:
                    message = f"Delete success, but no rows were affected"
                    self.logger.warning(message)
                return cursor.rowcount
                    
        except Exception as e:
            self.logger.error(f"Delete Failed：{e}\n{traceback.format_exc()}")
            raise


    async def _update(self, connection_id: int, sql: str, sql_args: List[Any])-> MySQLServiceUpdateResponse:
        """
        更新数据
        
        :param connection_id: 数据库连接ID
        :param sql: SQL语句
        :param sql_args: SQL语句参数

        Returns: UpdateResponse
        """
        
        operator = "Update"
        
        # 获取链接ID
        connection=self.connections.get(connection_id)

        # 链接ID不存在
        if connection is None:
            return MySQLServiceUpdateResponse(
                operator=operator,
                message=f"Update failed",
                result=False,
                err_code=MySQLServiceResponseErrorCode.CONNECTION_ID_NOT_EXISTS,
                errors=[MySQLServiceErrorDetail(
                    code=MySQLServiceResponseErrorCode.CONNECTION_ID_NOT_EXISTS,
                    message=f"Connection ID '{connection_id}' does not exist.",
                    field="connection_id",
                    hint="Please check if the connection ID is correct."
                )]
            )  
         
        try:
            # 更新数据
            rows_affected =  await self._update_with_retry(connection=connection, sql=sql, sql_args=sql_args)
            self.logger.info(f"Update success. sql: '{sql}', sql_args:'{sql_args}'")
            
            # 更新成功 返回Response
            return MySQLServiceUpdateResponse(
                operator=operator,
                message=f"Update success.",
                result=True,
                data= MySQLServiceUpdateResponseData(rows_affected=rows_affected)
            ) 
            
        except Exception as e:
            message = f"Update failed after 3 retries! Error:{str(e)}"
            self.logger.error(message)
            
            # 更新失败，且已重试三次，返回Response
            return MySQLServiceUpdateResponse(
                operator=operator,
                message=message,
                result=False,
                err_code=MySQLServiceResponseErrorCode.UPDATE_DATABASE_FAILED,
                errors=[MySQLServiceErrorDetail(
                    code=MySQLServiceResponseErrorCode.UPDATE_DATABASE_FAILED,
                    message=message,
                    field="sql",
                    hint="Please check the SQL syntax and parameters or try again later."
                )]
            )
            
        
    @retry(retries=3, delay=1.0, backoff=2.0, exceptions=(pymysql.MySQLError,), on_failure=lambda e: print(f"[ERROR] 最终重试失败: {e}"))      
    async def _update_with_retry(self, connection: Connection, sql: str, sql_args: List[Any])-> int:
        """
        更新数据（带重试机制）

        :param connection: 数据库连接
        :param sql: SQL语句
        :param sql_args: SQL语句参数
        
        Returns: 受影响的纪录数
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, sql_args)
                connection.commit()
                
                # 检查是否更新了记录
                if cursor.rowcount > 0:
                    message = f"Update success, {cursor.rowcount} rows affected"
                    self.logger.info(message)
                else:
                    message = f"Update success, but no rows were affected"
                    self.logger.warning(message)
                return cursor.rowcount
                    
        except Exception as e:
            self.logger.error(f"Update Failed：{e}\n{traceback.format_exc()}")
            raise
           
    
    async def _connect_database(self,
                                host: str, port: int, 
                                user: str, password: str, 
                                database: str, charset: str
                                ) -> MySQLServiceConnectDatabaseResponse:
        """
        创建一个新的 MySQL 数据库连接，并返回其 ID。
        如果失败，重试三次。最终如果失败，则返回一个错误响应，而不会返回ID。

        :param host: 数据库主机名
        :param user: 数据库用户名
        :param password: 数据库密码
        :param database: 数据库名称
        :param port: 数据库端口，默认为 3306
        :param charset: 字符集，默认为 'utf8mb4'
        :return: 
        """
        
        operator: str = "Connect Database"
        
        try:
            # 获取链接ID 和 链接对象
            connection_id, connection = await self._connect_database_with_retry(
                host=host, port=port, user=user, password=password, 
                database=database, charset=charset
            )

            # 存储连接
            self.connections[connection_id] = connection
            self.logger.info(f"Success connect database:'{database}'，connection_id='{connection_id}'")
            
            # 返回结果
            return MySQLServiceConnectDatabaseResponse(
                operator=operator,
                result=True,
                message=f"Success connect database:'{database}'",
                data=MySQLServiceConnectDatabaseResponseData(connection_id=connection_id)
            )
        
        except Exception as e:
            message = f"Failed to connect database '{database}' after 3 retries."
            self.logger.error(message)
            
            # 返回错误响应
            return MySQLServiceConnectDatabaseResponse(
                operator=operator,
                result=False,
                message=message,
                level="error",
                err_code=MySQLServiceResponseErrorCode.CONNECT_DATABASE_FAILED,
                errors=[MySQLServiceErrorDetail(
                    code=MySQLServiceResponseErrorCode.CONNECT_DATABASE_FAILED,
                    message=message,
                    field="database",
                    hint="Please check the database parameters or try again later."
                )],
                data=MySQLServiceConnectDatabaseResponseData(connection_id=-1)  # -1表示连接失败
            )
    
    
    @retry(retries=3, delay=1.0, backoff=2.0, exceptions=(pymysql.MySQLError,), on_failure=lambda e: print(f"[ERROR] 最终重试失败: {e}"))  
    async def _connect_database_with_retry(self, 
                                           host: str, port: int,
                                           user: str, password: str,
                                           database: str, charset: str
                                           ) -> Tuple[int, Connection]:
        """
        创建一个新的 MySQL 数据库连接，并返回其 (ID, Connection)。

        :param host: 数据库主机名
        :param user: 数据库用户名
        :param password: 数据库密码
        :param database: 数据库名称
        :param port: 数据库端口，默认为 3306
        :param charset: 字符集，默认为 'utf8mb4'
        :return: 新建连接的 (ID, Connection)
        """
        try:
            connection = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                charset=charset,
                connect_timeout=5,   # TCP 连接超时时间
                read_timeout=10,     # 读取结果超时时间
                write_timeout=10     # 写入语句超时时间
            )
            # 保存内部序号
            connection_id = self.ids
            self.ids += 1
            return connection_id, connection
        
        # 捕获可能产生的所有异常。 pymysql.MySQLError是所有 PyMySQL 异常的基类
        except pymysql.MySQLError as e:
            self.logger.error(f"Connect database failed：{e}\n{traceback.format_exc()}")
            raise  # 必须抛出让 @retry 机制知道要重试
            

    def close(self, connection_id: int) -> bool:
        """
        根据连接 ID 关闭对应的数据库连接。

        :param connection_id: 要关闭的连接 ID
        :return bool: 是否成功关闭
        """
        if connection_id not in self.connections:
            self.logger.error(f"No such connection ID: {connection_id}")
            return False
        connection = self.connections[connection_id]
        try:
            connection.close()
            del self.connections[connection_id]
            return True
        except pymysql.MySQLError as e:
            self.logger.error(f"Failed to close the connection with mysql database : {e}")
            raise


    def close_all(self) -> None:
        """
        关闭所有数据库连接。
        """
        ids = list(self.connections.keys())
        for connection_id in ids:
            try:
                res = self.close(connection_id)
                if res:
                    self.logger.info(f"Success to close the connection with mysql databse.")
                    self.connections.pop(connection_id, None)
                else:
                    self.logger.error(f"Failed to close the connection with mysql databse.")
                
            except pymysql.MySQLError as e:
                self.logger.error(f"Failed to close the connection with mysql databse : {e}")

        self.connections.clear()


    def __del__(self):
        """
        析构函数，关闭所有连接。
        """
        self.close_all()
        self.logger.info("ALL MySQL connections are closed.")
        
        
    def run(self):
        uvicorn.run(self.app, host=self.host, port=self.port)
        
        
def main():
    agent = MySQLService()
    agent.run()


if __name__ == "__main__":
    main()

