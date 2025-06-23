# Author:       yomu
# Time:         2025/6/23
# Version:      0.1
# Description:  SQL Builder Class Definition

"""
    构建SQL语句的工具类
"""

from typing import Dict, List, Any
from logging import Logger

class SQLBuilder:
    """
        构建各种SQL语句
        
        注意：
            1. 该类不负责传入数据的校验，需要字段校验等安全控制需要调用方负责
            2. 该类仅负责构建SQL语句，不负责执行SQL语句，执行SQL语句请使用SQLExecutor类
            3. 该类假设所有构建SQL语句的参数 data 都已经过安全处理，避免SQL注入等安全问题
            4. 该类使用日志记录器记录构建过程中的信息，
               需要在调用前确保已正确配置和传入 logger 实例
            5. 该类不依赖于任何特定的数据库连接或客户端
               只负责构建SQL语句和参数列表
    """
    def __init__(self, logger: Logger):
        self.logger = logger
     

    def build_insert_sql(self, table: str, data: Dict[str, Any]) -> tuple[str, list]:
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
        
        
    def build_update_sql(self, 
                        table: str,
                        data: Dict,
                        where_conditions: List[str] | None = None,
                        where_values: List[Any] | None = None
                        ) -> tuple[str, List[Any]]:
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
            
            self.logger.debug(f"Generated UPDATE SQL: {sql} | Values: {values}")
            return sql, values


    def build_query_sql(self, table: str,
                            fields: List[str] | None = None,
                            where_conditions: List[str] | None = None,
                            where_values: List[Any] | None = None,
                            order_by: str | None = None,
                            limit: int | None = None,
                            offset: int | None = None) -> tuple[str, List]:
            """
            构造通用 SELECT SQL 语句

            :param table: 表名
            :param fields: 要查询的字段
            :param where_conditions: WHERE 条件
            :param where_values: WHERE 条件对应的值
            :param order_by: ORDER BY 子句
            :param limit: LIMIT 子句
            :param offset: OFFSET 子句

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
        
        
    def build_delete_sql(self, table: str,
                        where_conditions: List[str],
                        where_values: List[Any]) -> tuple[str, List[Any]]:
            """
            构造支持复杂 WHERE 条件的 DELETE SQL 语句

            :param table: 表名
            :param where_conditions: WHERE 条件表达式列表（如 ["user_id = %s", "status = %s"]）
            :param where_values: 条件对应的值
            :return: (sql语句, 参数列表)
            """
            if not where_conditions or not where_values:
                raise ValueError("DELETE 操作必须指定 WHERE 条件，防止全表删除")

            if len(where_conditions) != len(where_values):
                raise ValueError("where_conditions 和 where_values 长度不一致")

            where_clause = " AND ".join(where_conditions)
            sql = f"DELETE FROM {table} WHERE {where_clause};"
            self.logger.debug(f"Generated DELETE SQL: {sql} | Values: {where_values}")
            return sql, where_values
