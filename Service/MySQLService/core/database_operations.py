# Project:      Agent
# Author:       yomu
# Time:         2025/6/29
# Version:      0.1
# Description:  Database Operations Manager

"""
数据库操作管理器
负责具体的数据库CRUD操作
"""

import pymysql
import pymysql.cursors
import traceback
from typing import List, Any, Optional
from logging import Logger
from pymysql import Connection

from Module.Utils.ToolFunctions import retry
from Service.MySQLService.schema.response import MySQLServiceQueryResponseData
from Service.MySQLService.core.connection_manager import MySQLConnectionManager
from Service.MySQLService.core.response_builder import ResponseBuilder


class DatabaseOperations:
    """
    数据库操作管理器
    负责执行具体的数据库CRUD操作
    """
    
    def __init__(self, connection_manager: MySQLConnectionManager, logger: Logger):
        self.connection_manager = connection_manager
        self.logger = logger
    
    async def query(self, connection_id: int, sql: str, sql_args: List[Any]):
        """
        执行查询操作
        
        :param connection_id: 数据库连接ID
        :param sql: SQL语句
        :param sql_args: SQL语句参数
        :return: 查询响应
        """
        # 获取连接对象
        connection = self.connection_manager.get_connection(connection_id)
        
        # 检查连接是否存在
        if connection is None:
            return ResponseBuilder.build_connection_error_response("Query", connection_id)
        
        try:
            # 执行查询
            query_data: List[MySQLServiceQueryResponseData] = await self._query_with_retry(
                connection=connection, sql=sql, sql_args=sql_args
            )
            self.logger.debug(f"Query success. sql: '{sql}', sql_args:'{sql_args}'")
            
            return ResponseBuilder.build_query_success_response(query_data)
            
        except Exception as e:
            error_message = f"Query failed after 3 retries! Error: {str(e)}"
            self.logger.error(error_message)
            return ResponseBuilder.build_query_error_response(error_message)
    
    @retry(retries=3, delay=1.0, backoff=2.0, exceptions=(pymysql.MySQLError,), 
           on_failure=lambda e: print(f"[ERROR] Query retry failed: {e}"))  
    async def _query_with_retry(self, connection: Connection, sql: str, sql_args: List[Any]) -> List[MySQLServiceQueryResponseData]:
        """
        执行查询（带重试机制）
        
        :param connection: 数据库连接对象
        :param sql: SQL语句
        :param sql_args: SQL语句参数
        :return: 查询结果列表
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
            self.logger.error(f"Query failed in _query_with_retry: {e}\n{traceback.format_exc()}")
            raise
    
    async def insert(self, connection_id: int, sql: str, sql_args: List[Any]):
        """
        执行插入操作
        
        :param connection_id: 数据库连接ID
        :param sql: SQL语句
        :param sql_args: SQL语句参数
        :return: 插入响应
        """
        # 获取连接对象
        connection = self.connection_manager.get_connection(connection_id)
        
        # 检查连接是否存在
        if connection is None:
            return ResponseBuilder.build_connection_error_response("Insert", connection_id)
        
        try:
            rows_affected, last_insert_id = await self._insert_with_retry(
                connection=connection, sql=sql, sql_args=sql_args
            )
            self.logger.info(f"Insert success. sql: '{sql}', sql_args:'{sql_args}'")
            
            return ResponseBuilder.build_insert_success_response(rows_affected, last_insert_id)
            
        except Exception as e:
            error_message = f"Insert failed after 3 retries! Error: {str(e)}"
            self.logger.error(error_message)
            return ResponseBuilder.build_insert_error_response(error_message)
    
    @retry(retries=3, delay=1.0, backoff=2.0, exceptions=(pymysql.MySQLError,), 
           on_failure=lambda e: print(f"[ERROR] Insert retry failed: {e}"))
    async def _insert_with_retry(self, connection: Connection, sql: str, sql_args: List[Any]) -> tuple[int, Optional[int]]:
        """
        执行插入（带重试机制）
        
        :param connection: 数据库连接
        :param sql: SQL语句
        :param sql_args: SQL语句参数
        :return: (受影响的行数, 自增主键ID)
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, sql_args)
                connection.commit()
                return cursor.rowcount, cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Insert failed: {e}\n{traceback.format_exc()}")
            raise
    
    async def update(self, connection_id: int, sql: str, sql_args: List[Any]):
        """
        执行更新操作
        
        :param connection_id: 数据库连接ID
        :param sql: SQL语句
        :param sql_args: SQL语句参数
        :return: 更新响应
        """
        # 获取连接对象
        connection = self.connection_manager.get_connection(connection_id)
        
        # 检查连接是否存在
        if connection is None:
            return ResponseBuilder.build_connection_error_response("Update", connection_id)
        
        try:
            rows_affected = await self._update_with_retry(
                connection=connection, sql=sql, sql_args=sql_args
            )
            self.logger.info(f"Update success. sql: '{sql}', sql_args:'{sql_args}'")
            
            return ResponseBuilder.build_update_success_response(rows_affected)
            
        except Exception as e:
            error_message = f"Update failed after 3 retries! Error: {str(e)}"
            self.logger.error(error_message)
            return ResponseBuilder.build_update_error_response(error_message)
    
    @retry(retries=3, delay=1.0, backoff=2.0, exceptions=(pymysql.MySQLError,), 
           on_failure=lambda e: print(f"[ERROR] Update retry failed: {e}"))      
    async def _update_with_retry(self, connection: Connection, sql: str, sql_args: List[Any]) -> int:
        """
        执行更新（带重试机制）
        
        :param connection: 数据库连接
        :param sql: SQL语句
        :param sql_args: SQL语句参数
        :return: 受影响的行数
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, sql_args)
                connection.commit()
                
                # 检查是否更新了记录
                if cursor.rowcount > 0:
                    self.logger.info(f"Update success, {cursor.rowcount} rows affected")
                else:
                    self.logger.warning("Update success, but no rows were affected")
                return cursor.rowcount
        except Exception as e:
            self.logger.error(f"Update failed: {e}\n{traceback.format_exc()}")
            raise
    
    async def delete(self, connection_id: int, sql: str, sql_args: List[Any]):
        """
        执行删除操作
        
        :param connection_id: 数据库连接ID
        :param sql: SQL语句
        :param sql_args: SQL语句参数
        :return: 删除响应
        """
        # 获取连接对象
        connection = self.connection_manager.get_connection(connection_id)
        
        # 检查连接是否存在
        if connection is None:
            return ResponseBuilder.build_connection_error_response("Delete", connection_id)
        
        try:
            rows_affected = await self._delete_with_retry(
                connection=connection, sql=sql, sql_args=sql_args
            )
            self.logger.info(f"Delete success. sql: '{sql}', sql_args:'{sql_args}'")
            
            return ResponseBuilder.build_delete_success_response(rows_affected)
            
        except Exception as e:
            error_message = f"Delete failed after 3 retries! Error: {str(e)}"
            self.logger.error(error_message)
            return ResponseBuilder.build_delete_error_response(error_message)
    
    @retry(retries=3, delay=1.0, backoff=2.0, exceptions=(pymysql.MySQLError,), 
           on_failure=lambda e: print(f"[ERROR] Delete retry failed: {e}"))  
    async def _delete_with_retry(self, connection: Connection, sql: str, sql_args: List[Any]) -> int:
        """
        执行删除（带重试机制）
        
        :param connection: 数据库连接
        :param sql: SQL语句
        :param sql_args: SQL语句参数
        :return: 受影响的行数
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, sql_args)
                connection.commit()
                
                # 检查是否删除了记录
                if cursor.rowcount > 0:
                    self.logger.info(f"Delete success, {cursor.rowcount} rows affected")
                else:
                    self.logger.warning("Delete success, but no rows were affected")
                return cursor.rowcount
        except Exception as e:
            self.logger.error(f"Delete failed: {e}\n{traceback.format_exc()}")
            raise
