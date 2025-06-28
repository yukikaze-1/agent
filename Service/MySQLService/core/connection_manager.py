# Project:      Agent
# Author:       yomu
# Time:         2025/6/29
# Version:      0.1
# Description:  MySQL Connection Manager

"""
MySQL连接管理器
负责MySQL连接的创建、管理和销毁
"""

import pymysql
import traceback
from typing import Dict, Tuple, Optional
from logging import Logger
from pymysql import Connection

from Module.Utils.ToolFunctions import retry


class MySQLConnectionManager:
    """
    MySQL连接管理器
    负责数据库连接的生命周期管理
    """
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self.ids = 0  # 连接ID计数器
        self.connections: Dict[int, pymysql.connections.Connection] = {}
    
    async def connect_database(self, 
                             host: str, 
                             port: int,
                             user: str, 
                             password: str,
                             database: str, 
                             charset: str) -> Tuple[int, Optional[Connection]]:
        """
        创建新的MySQL数据库连接
        
        :param host: 数据库主机名
        :param port: 数据库端口
        :param user: 数据库用户名
        :param password: 数据库密码
        :param database: 数据库名称
        :param charset: 字符集
        :return: (连接ID, 连接对象) 或 (连接ID, None) 如果失败
        """
        try:
            connection_id, connection = await self._connect_database_with_retry(
                host=host, port=port, user=user, password=password, 
                database=database, charset=charset
            )
            
            # 存储连接
            self.connections[connection_id] = connection
            self.logger.info(f"Successfully connected to database '{database}', connection_id={connection_id}")
            
            return connection_id, connection
            
        except Exception as e:
            self.logger.error(f"Failed to connect to database '{database}' after 3 retries: {e}")
            return -1, None
    
    @retry(retries=3, delay=1.0, backoff=2.0, exceptions=(pymysql.MySQLError,), 
           on_failure=lambda e: print(f"[ERROR] Connection retry failed: {e}"))  
    async def _connect_database_with_retry(self, 
                                         host: str, 
                                         port: int,
                                         user: str, 
                                         password: str,
                                         database: str, 
                                         charset: str) -> Tuple[int, Connection]:
        """
        带重试机制的数据库连接创建
        
        :return: (连接ID, 连接对象)
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
            
            # 生成连接ID
            connection_id = self.ids
            self.ids += 1
            
            return connection_id, connection
        
        except pymysql.MySQLError as e:
            self.logger.error(f"Connection failed: {e}\n{traceback.format_exc()}")
            raise  # 重新抛出异常以触发重试机制
    
    def get_connection(self, connection_id: int) -> Optional[Connection]:
        """
        根据连接ID获取连接对象
        
        :param connection_id: 连接ID
        :return: 连接对象或None
        """
        return self.connections.get(connection_id)
    
    def close_connection(self, connection_id: int) -> bool:
        """
        关闭指定的数据库连接
        
        :param connection_id: 要关闭的连接ID
        :return: 是否成功关闭
        """
        if connection_id not in self.connections:
            self.logger.error(f"Connection ID {connection_id} does not exist")
            return False
        
        connection = self.connections[connection_id]
        try:
            connection.close()
            del self.connections[connection_id]
            self.logger.info(f"Successfully closed connection {connection_id}")
            return True
        except pymysql.MySQLError as e:
            self.logger.error(f"Failed to close connection {connection_id}: {e}")
            raise
    
    def close_all_connections(self) -> None:
        """
        关闭所有数据库连接
        """
        connection_ids = list(self.connections.keys())
        for connection_id in connection_ids:
            try:
                if self.close_connection(connection_id):
                    self.logger.info(f"Closed connection {connection_id}")
                else:
                    self.logger.error(f"Failed to close connection {connection_id}")
            except Exception as e:
                self.logger.error(f"Error closing connection {connection_id}: {e}")
        
        self.connections.clear()
        self.logger.info("All MySQL connections closed")
    
    def get_connection_count(self) -> int:
        """
        获取当前连接数量
        
        :return: 连接数量
        """
        return len(self.connections)
    
    def get_connection_ids(self) -> list:
        """
        获取所有连接ID列表
        
        :return: 连接ID列表
        """
        return list(self.connections.keys())
