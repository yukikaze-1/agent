"""
    MySQL的模块类
    提供MySQL的封装
    使用pymsql
"""

import pymysql
from logging import Logger
from typing import List, Optional, Tuple, Dict

import pymysql.cursors


class MySQLAgent:
    """
    MySQL封装类
    用于管理 MySQL 数据库连接池。
    """
    def __init__(self, logger: Logger):
        self.logger = logger
        self.ids = 0
        # 存储 (id, connection) 的列表
        self.connections: Dict[int, pymysql.connections.Connection] = {}
        
    def query(self,id: int, sql: str, sql_args: List[str]):
        """查询"""
        connection=self.connections[id]
        if connection:
            try:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, sql_args)
                    result = cursor.fetchone()
                    return result
            except Exception as e:
                self.logger.error(f"Query failed! Error:{str(e)}")
                return None
        else:
            self.logger.error(f"ID {id} not exist! Query failed")
            
    
    def insert(self, id: int, sql: str, sql_args: List[str])->bool:
        """插入"""
        connection=self.connections[id]
        if connection:
            try:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, sql_args)
                    connection.commit()
                    return True
            except Exception as e:
                self.logger.error(f"Insert failed,Error:{str(e)}")
                return False
        else:
            self.logger.error(f"ID {id} not exist! Insert failed")    
            return False
        
    def delete(self, id: int, sql: str, sql_args: List[str])->bool:
        """删除"""
        connection=self.connections[id]
        if connection:
            try:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, sql_args)
                    connection.commit()
                    
                    # 检查是否删除了记录
                    if cursor.rowcount > 0:
                        self.logger.info(f"Delete success, {cursor.rowcount} rows affected")
                        return True
                    else:
                        self.logger.info(f"Delete success, but no rows were affected")
                        return False
            except Exception as e:
                self.logger.error(f"Delete failed,Error:{str(e)}")
                return False
        else:
            self.logger.error(f"ID {id} not exist! Delete failed")    
            return False
    
    def modify(self, id: int, sql: str, sql_args: List[str])->bool:
        """修改"""
        connection=self.connections[id]
        if connection:
            try:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, sql_args)
                    connection.commit()
                    
                    # 检查是否更新了记录
                    if cursor.rowcount > 0:
                        self.logger.info(f"Update success, {cursor.rowcount} rows affected")
                        return True
                    else:
                        self.logger.warning(f"Update success, but no rows were affected")
                        return False
            except Exception as e:
                self.logger.error(f"Update failed,Error:{str(e)}")
                return False
        else:
            self.logger.error(f"ID {id} not exist! Update failed")    
            return False
    
    def connect(self, host: str, user: str, password: str, database: str, port: int = 3306, charset: str = "utf8mb4") -> int:
        """
        创建一个新的 MySQL 数据库连接，并返回其 ID。

        :param host: 数据库主机名
        :param user: 数据库用户名
        :param password: 数据库密码
        :param database: 数据库名称
        :param port: 数据库端口，默认为 3306
        :param charset: 字符集，默认为 'utf8mb4'
        :return: 新建连接的 ID
        """
        try:
            connection = pymysql.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                port=port,
                charset=charset
            )
            connection_id = self.ids
            self.ids += 1
            self.connections[connection_id] = connection
            return connection_id
        except pymysql.MySQLError as e:
            self.logger.error(f"Failed to connect with mysql databse : {e}")
            return -1

    def close(self, id: int) -> bool:
        """
        根据连接 ID 关闭对应的数据库连接。

        :param id: 要关闭的连接 ID
        :return: 是否成功关闭
        """
        connection = self.connections[id]
        try:
            connection.close()
            return True
        except pymysql.MySQLError as e:
            self.logger.error(f"Failed to close the connection with mysql databse : {e}")
            return False


    def close_all(self) -> None:
        """
        关闭所有数据库连接。
        """
        ids = list(self.connections.keys())
        for id in ids:
            connect = self.connections[id]
            try:
                connect.close()
                del self.connections[id]
            except pymysql.MySQLError as e:
                self.logger.error(f"Failed to close the connection with mysql databse : {e}")

        self.connections.clear()

    def __del__(self):
        """
        析构函数，关闭所有连接。
        """
        self.close_all()
        self.logger.info("ALL MySQL connections are closed.")

