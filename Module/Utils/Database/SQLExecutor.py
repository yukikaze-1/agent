# Author:       yomu
# Time:         2025/6/23
# Version:      0.1
# Description:  SQL Executor Class Definition 

"""
    执行SQL语句的工具类
"""

import httpx
from typing import Dict, List, Any
from logging import Logger

class SQLExecutor:
    """
        SQL 语句执行类
        
        注意：
            1. 该类不负责传入数据的校验，需要字段校验等安全控制需要调用方负责
            2. 该类仅负责执行SQL语句，不负责SQL语句的构建，构建SQL语句请使用SQLBuilder类
            3. 该类假设所有SQL语句都已经过安全处理，
               如使用参数化查询等方式防止SQL注入等安全问题。
            4. 该类使用 httpx.AsyncClient 进行异步HTTP请求，
               需要在调用前确保已正确配置和传入 client 实例。
            5. 该类使用日志记录器记录执行过程中的信息，
               需要在调用前确保已正确配置和传入 logger 实例。
            6. 该类使用数据库连接ID来标识数据库连接，
               需要在调用前确保已正确获取和传入 db_connect_id。
               该 ID 通常存储在 UserAccountDatabaseAgent 中的 connect_id 字段中。
               该ID从 UserAccountDatabaseAgent 中获取。
            7. 该类的所有方法都为异步方法，需要在异步环境中调用。
            8. 该类的所有方法都返回结构化的响应结果，
               上层可以使用 Pydantic 模型进行解析和验证。
            9. 该类的所有方法都不会直接处理异常，
               而是将异常抛出，让上层决定如何处理。
    """
    def __init__(self, db_connect_id: int, logger: Logger, client: httpx.AsyncClient) -> None:
        """
        :param db_connect_id: 数据库连接ID
        :param logger: 日志记录器
        :param client: httpx.AsyncClient 实例，用于发送HTTP请求
        """
        self.logger = logger
        self.db_connect_id = db_connect_id
        self.client = client


    async def _execute_sql(
        self,
        url: str,
        sql: str,
        sql_args: List[Any],
        warning_msg: str,
        success_msg: str,
        error_msg: str,
        timeout: float,
        log_prefix: str
    ) -> Dict[str, Any]:
        """
        执行SQL语句的通用方法
        :param url: MySQL代理的URL
        :param sql: 要执行的SQL语句
        :param sql_args: SQL语句的参数列表
        :param warning_msg: 警告日志信息
        :param success_msg: 成功日志信息
        :param error_msg: 错误日志信息
        :param timeout: 请求超时时间（秒）
        :param log_prefix: 日志前缀，用于标识日志来源
        :return: 响应数据，包含执行结果和其他信息
        :raises httpx.HTTPStatusError: 如果HTTP响应状态码不是2xx
        :raises httpx.RequestError: 如果请求失败
        :raises Exception: 如果发生其他未知异常 
        """
        
        self.logger.info(f"{log_prefix} SQL: {sql} | Args: {sql_args} | URL: {url}")
        
        payload = {
            "id": self.db_connect_id,
            "sql": sql,
            "sql_args": sql_args
        }
        
        try:
            response = await self.client.post(url=url, json=payload, timeout=timeout)
            response.raise_for_status()
            
            try:
                response_data: Dict[str, Any] = response.json()
            except Exception as e:
                self.logger.error(f"{error_msg} - 响应非JSON格式: {e} | 内容: {response.text}")
                raise
            
            if response_data.get("result") is True:
                self.logger.info(success_msg)
            else:
                self.logger.warning(f"{warning_msg} | Message: {response_data.get('message')}")
                
            return response_data
        
        except httpx.HTTPStatusError as e:
            self.logger.error(f"{error_msg} - HTTP 状态异常: {e.response.status_code} | 内容: {e.response.text}")
            raise
        
        except httpx.RequestError as e:
            self.logger.error(f"{error_msg} - 请求失败: {e}")
            raise
        
        except Exception as e:
            self.logger.error(f"{error_msg} - 未知异常: {e}")
            raise


    async def execute_write_sql(self, url, sql, sql_args, warning_msg, success_msg, error_msg, timeout: float = 60.0) -> Dict[str, Any]:
        """
        执行写操作的SQL语句
        :param url: MySQL代理的URL
        :param sql: 要执行的SQL语句
        :param sql_args: SQL语句的参数列表
        :param warning_msg: 警告日志信息
        :param success_msg: 成功日志信息
        :param error_msg: 错误日志信息
        :param timeout: 请求超时时间（秒）
        :return: 响应数据，包含执行结果和其他信息
        """
        return await self._execute_sql(url, sql, sql_args, warning_msg, success_msg, error_msg, timeout, "Executing WRITE")


    async def execute_query_sql(self, url, sql, sql_args, warning_msg, success_msg, error_msg, timeout: float = 60.0) -> Dict[str, Any]:
        """
        执行查询操作的SQL语句
        :param url: MySQL代理的URL
        :param sql: 要执行的SQL语句
        :param sql_args: SQL语句的参数列表
        :param warning_msg: 警告日志信息
        :param success_msg: 成功日志信息
        :param error_msg: 错误日志信息
        :param timeout: 请求超时时间（秒）
        :return: 响应数据，包含执行结果和其他信息
        """
        return await self._execute_sql(url, sql, sql_args, warning_msg, success_msg, error_msg, timeout, "Executing QUERY")