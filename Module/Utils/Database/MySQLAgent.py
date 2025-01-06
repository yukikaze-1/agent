"""
    MySQL的代理
    提供MySQL的封装
    使用pymsql
"""

import uvicorn
import httpx
import asyncio
import pymysql
from logging import Logger
from typing import List, Optional, Tuple, Dict, Any
from dotenv import dotenv_values
from fastapi import FastAPI, Form, Body, HTTPException
from pydantic import BaseModel

import pymysql.cursors

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config
from Module.Utils.FastapiServiceTools import (
    get_service_instances,
    update_service_instances_periodically,
    register_service_to_consul,
    unregister_service_from_consul
)


class SQLRequest(BaseModel):
    id: int
    sql: str
    sql_args: List[str]
    
    
class ConnectRequest(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str
    charset: str
    

class MySQLAgent:
    """
    MySQL代理
    用于管理 MySQL 数据库连接池。
    """
    def __init__(self):
        self.logger = setup_logger(name="MySQLAgent", log_path="InternalModule")

        # 加载环境变量和配置
        self.env_vars = dotenv_values("/home/yomu/agent/Module/Utils/Database/.env") 
        self.config_path = self.env_vars.get("MYSQL_AGENT_CONFIG_PATH","") 
        self.config: Dict = load_config(config_path=self.config_path, config_name='MySQLAgent', logger=self.logger)
        
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
        
        self.ids = 0
        # 存储 (id, connection) 的列表
        self.connections: Dict[int, pymysql.connections.Connection] = {}
        
        # 初始化 httpx.AsyncClient
        self.client = None  # 在lifespan中初始化
        
        # 初始化 FastAPI 应用，使用生命周期管理
        self.app = FastAPI(lifespan=self.lifespan)
        
        # 设置路由
        self.setup_routes()
        
    
    async def lifespan(self, app: FastAPI):
        """管理应用生命周期"""
        self.logger.info("Starting lifespan...")

        try:
            # 初始化 AsyncClient
            self.client = httpx.AsyncClient(
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                timeout=httpx.Timeout(10.0, read=60.0)
            )
            self.logger.info("Async HTTP Client Initialized")

            # 注册服务到 Consul
            self.logger.info("Registering service to Consul...")
            await register_service_to_consul(consul_url=self.consul_url,
                                             client=self.client,
                                             logger=self.logger,
                                             service_name=self.service_name,
                                             service_id=self.service_id,
                                             address=self.host,
                                             port=self.port,
                                             health_check_url=self.health_check_url)
            self.logger.info("Service registered to Consul.")

            yield  # 应用正常运行

        except Exception as e:
            self.logger.error(f"Exception during lifespan: {e}")
            raise

        finally:                
            # 注销服务从 Consul
            try:
                self.logger.info("Deregistering service from Consul...")
                await unregister_service_from_consul(consul_url=self.consul_url,
                                                     client=self.client,
                                                     logger=self.logger,
                                                     service_id=self.service_id)
                self.logger.info("Service deregistered from Consul.")
            except Exception as e:
                self.logger.error(f"Error while deregistering service: {e}")    
             
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
        
        
        @self.app.post("/database/mysql/insert")
        async def insert(payload: SQLRequest):
            return await self._insert(payload.id, payload.sql, payload.sql_args)

        
        @self.app.post("/database/mysql/update", summary="更新接口")
        async def update(payload: SQLRequest):
            return await self._update(payload.id, payload.sql, payload.sql_args)
        
        
        @self.app.post("/database/mysql/delete", summary= "删除接口")
        async def delete(payload: SQLRequest):
            return await self._delete(payload.id, payload.sql, payload.sql_args)
        
        
        @self.app.post("/database/mysql/query", summary= "查询接口")
        async def query(payload: SQLRequest):
            return await self._query(payload.id, payload.sql, payload.sql_args)
        
        
        @self.app.post("/database/mysql/connect", summary= "连接接口")
        async def connect(payload: ConnectRequest):
            return await self._connect(payload.host, payload.port, payload.user, payload.password, payload.database,  payload.charset)
        
    # --------------------------------
    # 功能函数
    # --------------------------------     
    async def _query(self,id: int, sql: str, sql_args: List[str])-> Dict[str, Any]:
        """查询"""
        connection=self.connections[id]
        
        operator = "Query"
        message=f"Query success."
        result = False
        
        if connection:
            try:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, sql_args)
                    result = cursor.fetchone()
                    self.logger.info(f"Operator: {operator}, Message:{message}, Result: {result}")
                    return {"Operator": operator, "Message":message, "Result":result}
                
            except Exception as e:
                message = f"Query failed! Error:{str(e)}"
                self.logger.error(f"Operator: {operator}, Message:{message}, Result: {result}")
                return {"Operator": operator, "Message":message, "Result":result}

        else:
            message = f"ID {id} not exist! Query failed"
            self.logger.error(f"Operator: {operator}, Message:{message}, Result: {result}")
            return {"Operator": operator, "Message":message, "Result":result}
            
                    
    
    async def _insert(self, id: int, sql: str, sql_args: List[str])-> Dict[str, Any]:
        """插入"""
        connection=self.connections[id]
        
        operator = "Insert"
        message=f"Insert success."
        result = False
        
        if connection:
            try:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, sql_args)
                    connection.commit()
                    result = True
                    self.logger.info(f"Operator: {operator}, Message:{message}, Result: {result}")
                    return {"Operator": operator, "Message": message, "Result": result}
                
            except Exception as e:
                message= f"Insert failed,Error:{str(e)}"
                self.logger.error(f"Operator: {operator}, Message:{message}, Result: {result}")
                return {"Operator": operator, "Message":message, "Result":result}
        else:
            message = f"ID {id} not exist! Insert failed"
            self.logger.error(message)    
            return {"Operator": operator, "Message":message, "Result":result}
        
        
    async def _delete(self, id: int, sql: str, sql_args: List[str])-> Dict[str, Any]:
        """删除"""
        connection=self.connections[id]
        
        operator = "Delete"
        message=f"Delete success."
        result = False
        
        if connection:
            try:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, sql_args)
                    connection.commit()
                    result = True
                    
                    # 检查是否删除了记录
                    if cursor.rowcount > 0:
                        message = f"Delete success, {cursor.rowcount} rows affected"
                        self.logger.info(f"Operator: {operator}, Message:{message}, Result: {result}")
                        return {"Operator": operator, "Message":message, "Result":result}
                    else:
                        message = f"Delete success, but no rows were affected"
                        self.logger.warning(f"Operator: {operator}, Message:{message}, Result: {result}")
                        return {"Operator": operator, "Message":message, "Result":result}
                    
            except Exception as e:
                message = f"Delete failed,Error:{str(e)}"
                self.logger.error(f"Operator: {operator}, Message:{message}, Result: {result}")
                return {"Operator": operator, "Message":message, "Result":result}
        else:
            message = f"ID {id} not exist! Delete failed"
            self.logger.error(f"Operator: {operator}, Message:{message}, Result: {result}")
            return {"Operator": operator, "Message":message, "Result":result}
        
    
    async def _update(self, id: int, sql: str, sql_args: List[str])-> Dict[str, Any]:
        """修改"""
        connection=self.connections[id]
        
        operator = "Update"
        message=f"Update success."
        result = False
        
        if connection:
            try:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, sql_args)
                    connection.commit()
                    result = True
                    
                    # 检查是否更新了记录
                    if cursor.rowcount > 0:
                        message = f"Update success, {cursor.rowcount} rows affected"
                        self.logger.info(f"Operator: {operator}, Message:{message}, Result: {result}")
                        return {"Operator": operator, "Message":message, "Result":result}
                    else:
                        message = f"Update success, but no rows were affected"
                        self.logger.warning(f"Operator: {operator}, Message:{message}, Result: {result}")
                        return {"Operator": operator, "Message":message, "Result":result}
                    
            except Exception as e:
                message = f"Update failed,Error:{str(e)}"
                self.logger.error(f"Operator: {operator}, Message:{message}, Result: {result}")
                return {"Operator": operator, "Message":message, "Result":result}
            
        else:
            message = f"ID {id} not exist! Update failed"
            self.logger.error(f"Operator: {operator}, Message:{message}, Result: {result}")
            return {"Operator": operator, "Message":message, "Result":result}
        
    
    async def _connect(self, host: str, port: int, user: str, password: str, database: str, charset: str)-> Dict[str, Any]:
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
        
        operator = "Connect"
        message=f"Connect success."
        result = False
        
        try:
            connection = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                charset=charset
            )
            connection_id = self.ids
            self.ids += 1
            self.connections[connection_id] = connection
            message = f"Connect success. ConnectionID: '{connection_id}'"
            result = True
            self.logger.info(f"Operator: {operator}, Message:{message}, Result: {result}")
            return {"Operator": operator, "Message":message, "Result":result, "ConnectionID": connection_id}
        
        except pymysql.MySQLError as e:
            message = f"Failed to connect with mysql databse : {e}"
            self.logger.error(message)
            return {"Operator": operator, "Message":message, "Result":result, "ConnectionID": -1}
        

    def close(self, id: int) -> bool:
        """
        根据连接 ID 关闭对应的数据库连接。

        :param id: 要关闭的连接 ID
        :return: 是否成功关闭
        """
        if id not in self.connections:
            self.logger.error(f"No such connection ID: {id}")
            return False
        connection = self.connections[id]
        try:
            connection.close()
            del self.connections[id]
            return True
        except pymysql.MySQLError as e:
            self.logger.error(f"Failed to close the connection with mysql database : {e}")
            raise


    def close_all(self) -> None:
        """
        关闭所有数据库连接。
        """
        ids = list(self.connections.keys())
        for id in ids:
            try:
                res = self.close(id)
                if res:
                    self.logger.info(f"Success to close the connection with mysql databse.")
                    del self.connections[id]
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
    agent = MySQLAgent()
    agent.run()


if __name__ == "__main__":
    main()

