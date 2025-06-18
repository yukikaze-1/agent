# Project:      Agent
# Author:       yomu
# Time:         2025/6/18
# Version:      0.1
# Description:  SQL tool function
   
"""
MySQL的各种工具函数
"""

import httpx

from logging import Logger
from typing import Dict, List, Any, Optional

from Module.Utils.Logger import setup_logger

class MySQLHelper:
    """
    MySQL的各种工具函数

    :param mysql_agent_url: MySQL代理的URL
    :param connect_id: MySQL连接ID(eg.存放于UserAccountDatabase中为connect_id)
    :param client: httpx.AsyncClient实例
    :param logger: 日志记录器
    """
    
    def __init__(self, mysql_agent_url: str, connect_id: str, client: httpx.AsyncClient, logger: Optional[Logger]=None) -> None:
        self.logger = logger or setup_logger(name="MySQLHelper", log_path="InternalModule")
        
        self.mysql_agent_url = mysql_agent_url
        self.connect_id = connect_id
        self.client = client
        

    def build_insert_sql(self, table: str, data: Dict) -> tuple[str, list]:
        """
        构造通用 INSERT SQL 语句

        :param table: 表名
        :param data: 要插入的字段和值（key=字段名，value=字段值）

        :return: (sql语句, 参数列表)
        """
        if not data:
            raise ValueError("插入数据不能为空")

        columns = list(data.keys())
        values = list(data.values())

        placeholders = ", ".join(["%s"] * len(columns))
        columns_str = ", ".join(columns)

        sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders});"
        self.logger.debug(f"Generated SQL: {sql} | Values: {values}")
        return sql, values
    
    
    def build_update_sql(self, table: str, data: Dict,
                     where_conditions: Optional[List[str]] = None,
                     where_values: Optional[List] = None) -> tuple[str, List]:
        """
        构造支持复杂 WHERE 条件的 UPDATE SQL 语句

        :param table: 表名
        :param data: 要更新的字段和值（key=字段名，value=字段值）
        :param where_conditions: 更复杂的 WHERE 条件表达式（如 ["user_id = %s", "status != %s"]）
        :param where_values: 与 where_conditions 一一对应的值
        :return: (sql语句, 参数列表)
        """
        if not data:
            raise ValueError("更新字段不能为空")
        
        if where_conditions and where_values and len(where_conditions) != len(where_values):
            raise ValueError("where_conditions 和 where_values 长度不一致")


        set_clause = ", ".join([f"{key} = %s" for key in data])
        values = list(data.values())

        where_clause_parts = []

        if where_conditions:
            where_clause_parts.extend(where_conditions)
            if where_values:
                values.extend(where_values)

        if not where_clause_parts:
            raise ValueError("WHERE 条件不能为空（防止全表更新）")

        where_clause = " AND ".join(where_clause_parts)
        sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause};"

        return sql, values


    def build_query_sql(self, table: str,
                        fields: Optional[List[str]] = None,
                        where_conditions: Optional[List[str]] = None,
                        where_values: Optional[List] = None,
                        order_by: Optional[str] = None,
                        limit: Optional[int] = None,
                        offset: Optional[int] = None) -> tuple[str, List]:
        """
        构造通用 SELECT SQL 语句

        :return: (sql语句, 参数列表)
        """
        if fields:
            field_str = ", ".join(fields)
        else:
            field_str = "*"

        sql = f"SELECT {field_str} FROM {table}"
        args = []

        where_clause_parts = []

        if where_conditions:
            where_clause_parts.extend(where_conditions)
            if where_values:
                args.extend(where_values)

        if where_clause_parts:
            sql += " WHERE " + " AND ".join(where_clause_parts)

        if order_by:
            sql += f" ORDER BY {order_by}"

        if limit is not None:
            sql += " LIMIT %s"
            args.append(limit)

        if offset is not None:
            sql += " OFFSET %s"
            args.append(offset)

        sql += ";"
        self.logger.debug(f"Generated Query SQL: {sql} | Args: {args}")
        return sql, args
    
    
    async def execute_write_sql(self, url: str, sql: str, sql_args: List,
                          warning_msg: str, success_msg: str, error_msg: str) -> bool:
        """
            执行sql

        :param url: 请求的URL
        :param sql: 要执行的SQL语句
        :param sql_args: SQL语句的参数
        :param warning_msg: 警告消息
        :param success_msg: 成功消息
        :param error_msg: 错误消息
        """
        
        self.logger.info(f"Executing WRITE SQL: {sql} | Args: {sql_args}")
        
        payload = {
            "id": self.connect_id,
            "sql": sql,
            "sql_args": sql_args
        }
        
        try:
            response = await self.client.post(url=url, json=payload, timeout=60.0)
            response.raise_for_status()
            response_data = response.json()

            if response.status_code == 200 and response_data.get("Result") is True:
                self.logger.info(success_msg)
                return True
            else:
                self.logger.warning(f"{warning_msg} | Response: {response_data}")
                return False

        except Exception as e:
            self.logger.error(f"{error_msg} : {str(e)}")
            return False
        
        
    async def execute_query_sql(self, url: str, sql: str, sql_args: List,
                            warning_msg: str, success_msg: str, error_msg: str) -> Optional[List[Dict]]:
        """
        执行 查询  SQL

        :param warning_msg: 警告消息
        :param success_msg: 成功消息
        :param error_msg: 错误消息
        """
        self.logger.info(f"Executing QUERY SQL: {sql} | Args: {sql_args}")

        payload = {
            "id": self.connect_id,
            "sql": sql,
            "sql_args": sql_args
        }

        try:
            response = await self.client.post(url=url, json=payload, timeout=60.0)
            response.raise_for_status()
            response_data = response.json()

            if response.status_code == 200 and response_data.get("Result") is True:
                self.logger.info(success_msg)
                return response_data.get("Data") or []
            else:
                self.logger.warning(f"{warning_msg} | Response: {response_data}")
                return None

        except Exception as e:
            self.logger.error(f"{error_msg} : {str(e)}")
            return None
        
    # ---------------------- 封装操作函数 ----------------------
        
    async def insert_one(self, table: str, data: Dict,
                     success_msg: str = "Insert Success", warning_msg: str = "Insert Warning.",
                     error_msg: str = "Insert Error.") -> bool:
        """
        插入一条记录

        :param table: 表名
        :param data: 要插入的字段和值（key=字段名，value=字段值）
        """
        if not data:
            self.logger.warning("尝试插入空数据，已跳过。")
            return False

        # 生成sql语句和sql参数
        sql, sql_args = self.build_insert_sql(table, data)
        
        url = self.mysql_agent_url + "/database/mysql/insert"

        return await self.execute_write_sql(url=url, sql=sql, sql_args=sql_args,
                                            warning_msg=warning_msg,
                                            success_msg=success_msg,
                                            error_msg=error_msg)

    
    async def update_one(self, table: str, data: dict,
                     where_conditions: Optional[List[str]] = None,
                     where_values: Optional[List] = None,
                     success_msg: str = "Update success.",
                     warning_msg: str = "Update warning.",
                     error_msg: str = "Update error.") -> bool:
        """
        通用更新函数：更新一条记录

        :param table: 表名
        :param data: 要更新的字段和值
        :param where_conditions: 复杂 WHERE 条件（如 ["status != %s"]）
        :param where_values: 对应的值（如 ["deleted"]）
        :param success_msg: 成功日志
        :param warning_msg: 警告日志
        :param error_msg: 错误日志
        :return: 是否更新成功
        """
        # 构造 SQL 和参数
        sql, args = self.build_update_sql(
            table=table,
            data=data,
            where_conditions=where_conditions,
            where_values=where_values
        )

        # 发送请求
        url = self.mysql_agent_url + "/database/mysql/update"
        
        return await self.execute_write_sql(url=url, sql=sql, sql_args=args,
                                            success_msg=success_msg,
                                            warning_msg=warning_msg,
                                            error_msg=error_msg)


    async def query_many(self, table: str,
                        fields: Optional[List[str]] = None,
                        where_conditions: Optional[List[str]] = None,
                        where_values: Optional[List] = None,
                        order_by: Optional[str] = None,
                        limit: Optional[int] = None,
                        offset: Optional[int] = None,
                        success_msg: str = "Query success.",
                        warning_msg: str = "Query may have failed.",
                        error_msg: str = "Query error.") -> Optional[List[Dict]]:
        """
        执行 SELECT 查询并返回多条记录

        :return: 查询结果列表，失败时返回 None
        """
        sql, sql_args = self.build_query_sql(
            table=table,
            fields=fields,
            where_conditions=where_conditions,
            where_values=where_values,
            order_by=order_by,
            limit=limit,
            offset=offset
        )
        url = self.mysql_agent_url + "/database/mysql/query"

        self.logger.info(f"Executing query: {sql} with args: {sql_args}")

        payload = {
            "id": self.connect_id,
            "sql": sql,
            "sql_args": sql_args
        }

        try:
            response = await self.client.post(url=url, json=payload, timeout=60.0)
            response.raise_for_status()
            response_data = response.json()

            if response.status_code == 200 and response_data.get("Result") is True:
                self.logger.info(success_msg)
                return response_data.get("Data") or []
            else:
                self.logger.warning(f"{warning_msg} | Response: {response_data}")
                return None
        except Exception as e:
            self.logger.error(f"{error_msg}: {str(e)}")
            return None


    async def query_one(self, table: str,
                    columns: Optional[List[str]] = None,
                    where_conditions: Optional[List[str]] = None,
                    where_values: Optional[List] = None,
                    order_by: Optional[str] = None,
                    warning_msg: str = "Query One Warning.",
                    error_msg: str = "Query One Error.") -> Optional[Dict]:
        """
        执行 SELECT 查询并返回一条记录
        
        """
        # 转发
        result = await self.query_many(table, columns, where_conditions, where_values, limit=1,
                                       order_by=order_by, warning_msg=warning_msg, error_msg=error_msg)
        return result[0] if result else None

