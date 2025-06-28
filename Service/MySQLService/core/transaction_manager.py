# Project:      Agent
# Author:       yomu
# Time:         2025/6/29
# Version:      0.1
# Description:  Transaction Manager

"""
事务管理器
负责静态和动态事务的管理
"""

import uuid
import pymysql
import traceback
from typing import Dict, List, Any, Optional
from logging import Logger

from Service.MySQLService.schema.request import MySQLServiceStaticTransactionSQL
from Service.MySQLService.schema.response import MySQLServiceStaticTransactionSQLExecutionResult
from Service.MySQLService.core.connection_manager import MySQLConnectionManager
from Service.MySQLService.core.response_builder import ResponseBuilder


class DynamicTransactionSession:
    """动态事务会话类，用于管理 MySQL 事务"""
    
    def __init__(self, connection: pymysql.connections.Connection):
        self.connection = connection
        self.cursor = connection.cursor()
        self.in_transaction = True
        self.executed_sql_count: int = 0    # 记录执行的SQL语句数量
        self.affected_rows_total: int = 0   # 记录总的受影响行数

    def close(self):
        """关闭会话"""
        self.cursor.close()
        # 注意：不要在这里关闭connection，因为connection由ConnectionManager管理


class TransactionManager:
    """
    事务管理器
    负责处理静态事务和动态事务
    """
    
    def __init__(self, connection_manager: MySQLConnectionManager, logger: Logger):
        self.connection_manager = connection_manager
        self.logger = logger
        
        # 存储动态事务会话(session_id, session对象) 的字典
        self.dynamic_transaction_sessions: Dict[str, DynamicTransactionSession] = {}
    
    async def execute_static_transaction(self, connection_id: int, statements: List[MySQLServiceStaticTransactionSQL]):
        """
        执行静态事务
        
        :param connection_id: 数据库连接ID
        :param statements: 要执行的SQL语句列表
        :return: 事务响应
        """
        # 获取连接对象
        connection = self.connection_manager.get_connection(connection_id)
        
        # 检查连接是否存在
        if connection is None:
            return ResponseBuilder.build_connection_error_response("Transaction", connection_id)
        
        try:
            results = []
            with connection.cursor() as cursor:
                # 显式开启事务
                connection.begin()
                
                # 执行每个SQL请求
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
                self.logger.info(f"Static transaction success. connection_id: {connection_id}")

            # 构建成功响应
            return ResponseBuilder.build_static_transaction_success_response(results, len(statements))
            
        except Exception as e:
            connection.rollback()
            error_message = str(e)
            sql_statements = [sql_request.sql for sql_request in statements]
            
            self.logger.error(
                f"Static transaction failed while executing SQL statements: {sql_statements}. "
                f"connection_id: {connection_id}, error: {e}"
            )
            
            return ResponseBuilder.build_static_transaction_error_response(error_message, sql_statements)
    
    async def start_dynamic_transaction(self, connection_id: int):
        """
        开始动态事务
        
        :param connection_id: 数据库连接ID
        :return: 事务开始响应
        """
        # 获取连接对象
        connection = self.connection_manager.get_connection(connection_id)
        
        # 检查连接是否存在
        if connection is None:
            return ResponseBuilder.build_connection_error_response("Transaction", connection_id)
        
        try:
            # 创建事务会话ID
            session_id = str(uuid.uuid4())
            
            # 创建事务会话
            session = DynamicTransactionSession(connection=connection)
            
            # 开启事务
            connection.begin()
            self.dynamic_transaction_sessions[session_id] = session

            self.logger.info(f"Dynamic transaction started. session_id: {session_id}")
            
            return ResponseBuilder.build_dynamic_transaction_start_success_response(session_id)
            
        except Exception as e:
            error_message = "Failed to start dynamic transaction."
            self.logger.error(
                f"Failed to start dynamic transaction. connection_id: {connection_id}, error: {e}"
            )
            return ResponseBuilder.build_dynamic_transaction_start_error_response(error_message)
    
    async def execute_sql_in_transaction(self, session_id: str, sql: str, sql_args: List[Any] | Dict[str, Any] | None = None):
        """
        在动态事务中执行SQL语句
        
        :param session_id: 事务会话ID
        :param sql: SQL语句
        :param sql_args: SQL语句参数
        :return: 执行响应
        """
        # 获取事务会话对象
        transaction_session = self.dynamic_transaction_sessions.get(session_id)
        
        # 检查会话是否存在
        if transaction_session is None:
            return ResponseBuilder.build_session_not_found_error_response("Transaction Execute SQL", session_id)
        
        try:
            self.logger.info(f"Executing SQL in dynamic transaction. session_id: {session_id}, sql: {sql}, sql_args: {sql_args}")
            
            # 执行SQL语句
            with transaction_session.connection.cursor() as cursor:
                cursor.execute(sql, sql_args or [])
                transaction_session.executed_sql_count += 1
                affected_rows = cursor.rowcount
                last_insert_id = cursor.lastrowid      
                transaction_session.affected_rows_total += affected_rows
                
            self.logger.info(f"Executed SQL in dynamic transaction. session_id: {session_id}")
            
            return ResponseBuilder.build_dynamic_transaction_execute_success_response(affected_rows, last_insert_id)
            
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
            
            return ResponseBuilder.build_dynamic_transaction_execute_error_response(str(e))
    
    async def commit_dynamic_transaction(self, session_id: str):
        """
        提交动态事务
        
        :param session_id: 事务会话ID
        :return: 提交响应
        """
        # 获取事务会话对象
        transaction_session = self.dynamic_transaction_sessions.get(session_id)
        
        # 检查会话是否存在
        if transaction_session is None:
            return ResponseBuilder.build_session_not_found_error_response("Transaction Commit", session_id)
        
        try:
            transaction_session.connection.commit()
            self.logger.info(f"Dynamic transaction committed. session_id: {session_id}")
            
            result = ResponseBuilder.build_dynamic_transaction_commit_success_response(
                session_id=session_id,
                affected_rows=transaction_session.affected_rows_total,
                executed_sql_count=transaction_session.executed_sql_count
            )
        except Exception as e:
            self.logger.error(
                f"Failed to commit dynamic transaction. session_id: {session_id}, error: {e}"
            )
            result = ResponseBuilder.build_dynamic_transaction_commit_error_response(str(e))
        finally:
            # 清理会话
            transaction_session.close()
            self.dynamic_transaction_sessions.pop(session_id, None)
        
        return result
    
    async def rollback_dynamic_transaction(self, session_id: str):
        """
        回滚动态事务
        
        :param session_id: 事务会话ID
        :return: 回滚响应
        """
        # 获取事务会话对象
        transaction_session = self.dynamic_transaction_sessions.get(session_id)
        
        # 检查会话是否存在
        if transaction_session is None:
            return ResponseBuilder.build_session_not_found_error_response("Transaction Rollback", session_id)
        
        try:
            # 回滚事务
            transaction_session.connection.rollback()
            self.logger.info(f"Dynamic transaction rolled back. session_id: {session_id}")
        finally:
            # 清理会话
            transaction_session.close()
            # 从会话列表中移除
            self.dynamic_transaction_sessions.pop(session_id, None)
        
        return ResponseBuilder.build_dynamic_transaction_rollback_response()
    
    def cleanup_all_sessions(self):
        """
        清理所有动态事务会话
        """
        session_ids = list(self.dynamic_transaction_sessions.keys())
        for session_id in session_ids:
            try:
                session = self.dynamic_transaction_sessions[session_id]
                session.connection.rollback()
                session.close()
                self.logger.info(f"Cleaned up transaction session: {session_id}")
            except Exception as e:
                self.logger.error(f"Error cleaning up session {session_id}: {e}")
        
        self.dynamic_transaction_sessions.clear()
        self.logger.info("All dynamic transaction sessions cleaned up")
    
    def get_active_session_count(self) -> int:
        """
        获取活跃的事务会话数量
        
        :return: 活跃会话数量
        """
        return len(self.dynamic_transaction_sessions)
