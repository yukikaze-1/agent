# Project:      Agent
# Author:       yomu
# Time:         2025/06/29
# Version:      0.3
# Description:  Base Database Agent - 数据库代理基类

"""
数据库代理基类
为所有数据库代理提供统一的数据库连接、事务管理和SQL操作功能
"""
import httpx
import json
from typing import Optional, Dict, List, Any
from dotenv import dotenv_values
from logging import Logger
from fastapi import HTTPException

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config
from Service.UserService.app.db.SQLBuilder import SQLBuilder
from Service.UserService.app.db.SQLExecutor import SQLExecutor

from Service.MySQLService.schema.request import (
    MySQLServiceConnectRequest,
    MySQLServiceDynamicTransactionBaseRequest,
    MySQLServiceDynamicTransactionStartRequest,
    MySQLServiceDynamicTransactionCommitRequest,
    MySQLServiceDynamicTransactionRollbackRequest,
    MySQLServiceDynamicTransactionExecuteSQLRequest
)
from Service.MySQLService.schema.response import (
    MySQLServiceConnectDatabaseResponse, 
    MySQLServiceInsertResponse, 
    MySQLServiceUpdateResponse, 
    MySQLServiceDeleteResponse, 
    MySQLServiceQueryResponse
)
from Service.UserService.app.models.UserAccountDatabaseSQLParameterSchema import (
    InsertSchema,
    QueryWhereSchema,
    DeleteWhereSchema,
    UpdateWhereSchema,
    UpdateSetSchema
)


def transfer_dict_in_schema_to_json(data: dict) -> dict:
    """ 
    将字典中的字典值转换为JSON字符串
    用于准备SQL参数，确保嵌套字典可以正确存储到数据库的JSON字段中
    
    :param data: 待转换的字典数据
    :return: 转换后的字典
    """
    return {
        k: json.dumps(v) if isinstance(v, dict) else v
        for k, v in data.items()
    }


class BaseDBAgent:
    """
        该类是所有数据库操作代理的基类

        主要功能：
            1. 初始化通用组件 (Logger, HTTP Client, SQLBuilder, SQLExecutor)
            2. 建立和管理到MySQLService的连接
            3. 提供通用的 CRUD (Create, Read, Update, Delete) 数据库操作方法
    """
    def __init__(self, agent_name: str, logger: Optional[Logger]=None):
        self.logger = logger or setup_logger(name=agent_name, log_path="InternalModule")
        
        # 加载环境变量和配置
        self.env_vars = dotenv_values("${AGENT_HOME}/Service/UserService/config/.env")
        self.config_path = self.env_vars.get("USER_ACCOUNT_DATABASE_AGENT_CONFIG_PATH", "")
        self.config = load_config(config_path=self.config_path, config_name='UserAccountDataBaseAgent', logger=self.logger)
        
        # 验证配置文件
        required_keys = ["mysql_host", "mysql_port", "mysql_service_url", "mysql_user", "mysql_password", "database", "charset"]
        validate_config(required_keys, self.config, self.logger)
        
        # MySQL配置
        self.mysql_service_url = self.config.get("mysql_service_url", "")
        
        # 初始化 AsyncClient
        self.client: httpx.AsyncClient = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(10.0, read=60.0)
        )
        
        self.db_connect_id: int = -1

        # 初始化SQLBuilder 
        self.sql_builder = SQLBuilder(logger=self.logger)
        
        # 初始化SQLExecutor
        self.sql_executor = SQLExecutor(
            db_connect_id=self.db_connect_id,
            client=self.client,
            logger=self.logger
        )

    async def init_connection(self) -> None:
        """
        初始化数据库连接, 并为 self.db_connect_id 赋值
        """
        try:
            self.db_connect_id = await self._connect_to_database()
            if self.db_connect_id == -1:
                self.logger.error("Failed to connect to database, connect id == -1")
                raise ValueError("Failed to connect to database, connect id == -1")
            else:
                self.logger.info(f"db_connect_id = {self.db_connect_id}")
                # 同步到 SQLExecutor
                self.sql_executor.db_connect_id = self.db_connect_id
                
        except Exception as e:
            self.logger.error(f"Failed to init connection: {e}")
            raise
        
    async def _connect_to_database(self) -> int:
        """
        连接MySQL数据库
        返回: 成功时连接ID(非负)，失败时返回-1
        """
        url = self.mysql_service_url + "/database/mysql/connect"
        
        request = MySQLServiceConnectRequest(
            host=self.config.get("mysql_host", ""),
            port=self.config.get("mysql_port", ""),
            user=self.config.get("mysql_user", ""),
            password=self.config.get("mysql_password", ""),
            database=self.config.get("database", ""),
            charset=self.config.get("charset", "")
        )
        
        payload = request.model_dump(mode="json", exclude_none=True)
        
        try:
            response = await self.client.post(url=url, json=payload, timeout=120.0)
            response.raise_for_status()
            
            response_dict: Dict = response.json()
            response_data = MySQLServiceConnectDatabaseResponse.model_validate(response_dict)
            
            return response_data.data.connection_id 
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Connect to database failed! HTTP error: {e.response.status_code}, {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        
        except httpx.RequestError as e:
            self.logger.error(f"Connect to database failed! Request error: {e}")
            raise HTTPException(status_code=503, detail="Failed to communicate with MySQLService.")
        
        except Exception as e:
            self.logger.error(f"Connect to database failed! Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error.")

    def extract_where_from_schema(self, schema: QueryWhereSchema | UpdateWhereSchema | DeleteWhereSchema) -> tuple[list[str], list[Any]]:
        """
        从 Pydantic 模型中提取 WHERE 条件和参数值。
        """
        conditions = []
        values = []

        for key, value in schema.model_dump(exclude_none=True).items():
            conditions.append(f"{key} = %s")
            values.append(value)

        return conditions, values

    async def query_record(
        self,
        table: str,
        fields: Optional[List[str]] = None,
        where_conditions: Optional[List[str]] = None,
        where_values: Optional[List[Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict:
        """
        通用查询函数
        """
        try:
            sql, sql_args = self.sql_builder.build_query_sql(
                table=table,
                fields=fields,
                where_conditions=where_conditions,
                where_values=where_values,
                order_by=order_by,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            self.logger.error(f"构建 SELECT SQL 失败: {e}")
            return {}

        url = self.mysql_service_url + "/database/mysql/query"

        try:
            response_dict = await self.sql_executor.execute_query_sql(
                url=url,
                sql=sql,
                sql_args=sql_args,
                success_msg=f"查询成功: {table}",
                warning_msg=f"查询完成但无匹配记录: {table}",
                error_msg=f"查询失败: {table}"
            )
            if response_dict and response_dict.get("result") is True:
                data_list = response_dict.get("data", [])
                if data_list and len(data_list) > 0:
                    # MySQLService 返回的 data 是 List[MySQLServiceQueryResponseData]
                    # 我们需要提取第一个元素并转换为便于使用的格式
                    query_data = data_list[0]
                    return {
                        "row_count": query_data.get("row_count", 0),
                        "column_names": query_data.get("column_names", []),
                        "rows": query_data.get("rows", [])
                    }
                else:
                    return {"row_count": 0, "column_names": [], "rows": []}
            else:
                return {"row_count": 0, "column_names": [], "rows": []}
        except Exception as e:
            self.logger.error(f"执行 SELECT 失败: {e}")
            return {}

    async def query_record_by_schema(
        self,
        table: str,
        query_where: QueryWhereSchema,
        select_fields: List[str] | None= None,
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Dict:
        """
        根据 Schema 执行查询（自动提取 WHERE）
        """
        try:
            where_conditions, where_values = self.extract_where_from_schema(schema=query_where)
        except Exception as e:
            self.logger.error(f"从 QuerySchema 提取 WHERE 条件失败: {e}")
            return {}
        
        if not select_fields:
            select_fields = ["*"]

        return await self.query_record(
            table=table,
            fields=select_fields,
            where_conditions=where_conditions,
            where_values=where_values,
            order_by=order_by,
            limit=limit,
            offset=offset
        )

    async def insert_record(
        self,
        table: str,
        insert_data: InsertSchema,
        warning_msg: str,
        success_msg: str,
        error_msg: str,
    ) -> int :
        """
        通用插入记录。

        :param table: 要插入的表名。
        :param insert_data: 包含要插入数据的 Pydantic 模型。
        :param warning_msg: 警告日志信息。
        :param success_msg: 成功日志信息。
        :param error_msg: 错误日志信息。
        :return: 成功时返回last_insert_id，失败时返回-1。
        """
        data = insert_data.model_dump(exclude_none=True)
        data = transfer_dict_in_schema_to_json(data)
        
        try:
            sql, sql_args = self.sql_builder.build_insert_sql(table=table, data=data)
        except Exception as e:
            self.logger.error(f"SQL构建失败: {e}")
            return -1 

        url = self.mysql_service_url + "/database/mysql/insert"
        
        try:
            response_dict = await self.sql_executor.execute_insert_sql(
                url=url,
                sql=sql,
                sql_args=sql_args,
                warning_msg=warning_msg,
                success_msg=success_msg,
                error_msg=error_msg
            )
            insert_response = MySQLServiceInsertResponse.model_validate(response_dict)
            
            if  insert_response.result is False:
                self.logger.warning(
                    f"{error_msg}：{insert_response.message} | "
                    f"错误码: {insert_response.err_code} | "
                    f"字段错误: {insert_response.errors}"
                )
                return -1 
            elif insert_response.data is not None and insert_response.data.last_insert_id is not None:
                return insert_response.data.last_insert_id
            return -1
        
        except Exception as e:
            self.logger.error(f"{error_msg}: {e}")
            return -1

    async def update_record(
        self,
        table: str,
        update_data: UpdateSetSchema,
        update_where: UpdateWhereSchema,
        warning_msg: str,
        success_msg: str,
        error_msg: str
    ) -> bool:
        """
        通用更新指定表的记录(该函数不会抛出异常)
        """
        where_conditions, where_values = self.extract_where_from_schema(schema=update_where)
        data = update_data.model_dump(exclude_none=True)
        data = transfer_dict_in_schema_to_json(data)
        
        try:
            sql, sql_args = self.sql_builder.build_update_sql(
                table=table,
                data=data,
                where_conditions=where_conditions,
                where_values=where_values
            )
        except Exception as e:
            self.logger.error(f"SQL构建失败: {e}")
            return False
        
        url = self.mysql_service_url + "/database/mysql/update"
        
        try:
            response_dict = await self.sql_executor.execute_update_sql(
                url=url,
                sql=sql,
                sql_args=sql_args,
                warning_msg=warning_msg,
                success_msg=success_msg,
                error_msg=error_msg
            )
            update_response = MySQLServiceUpdateResponse.model_validate(response_dict)
            
            if update_response.result is False:
                self.logger.warning(
                    f"{error_msg}：{update_response.message} | "
                    f"错误码: {update_response.err_code} | "
                    f"字段错误: {update_response.errors}"
                )
                return False
            return True
        except Exception as e:
            self.logger.error(f"{error_msg}: {e}")
            return False

    async def delete_record(self, table: str,
                     where_conditions: List[str],
                     where_values: List[Any],
                     success_msg: str = "Delete success.",
                     warning_msg: str = "Delete warning.",
                     error_msg: str = "Delete error.") -> int:
        """
        通用删除记录(该函数不会报异常)
        """
        if not where_conditions or not where_values:
            self.logger.warning(f"{warning_msg}：WHERE 条件或值缺失，跳过删除")
            return -1
        
        if len(where_conditions) != len(where_values):
            self.logger.error("WHERE 条件与值长度不一致")
            return -1
        
        try:
            sql, args = self.sql_builder.build_delete_sql(
                table=table,
                where_conditions=where_conditions,
                where_values=where_values
            )
        except Exception as e:
            self.logger.error(f"SQL构建失败: {e}")
            return -1
        
        url = self.mysql_service_url + "/database/mysql/delete"
        
        try:
            response_dict = await self.sql_executor.execute_delete_sql(
                url=url,
                sql=sql,
                sql_args=args,
                success_msg=success_msg,
                warning_msg=warning_msg,
                error_msg=error_msg
            )
            delete_response = MySQLServiceDeleteResponse.model_validate(response_dict)
                        
            if delete_response.result is False:
                self.logger.warning(
                    f"{error_msg}：{delete_response.message} | "
                    f"错误码: {delete_response.err_code} | "
                    f"字段错误: {delete_response.errors}"
                )
                return 0
            
            return delete_response.data.rows_affected
        
        except Exception as e:
            self.logger.error(f"{error_msg}: {e}")
            return -1

    async def delete_record_by_schema(self,
                                  table: str,
                                  delete_where: DeleteWhereSchema,
                                  success_msg: str = "Delete success.",
                                  warning_msg: str = "Delete warning.",
                                  error_msg: str = "Delete error.") -> bool:
        """
        通用 delete 调用（通过 schema + 表名）
        """
        try:
            where_conditions, where_values = self.extract_where_from_schema(schema=delete_where)
        except Exception as e:
            self.logger.error(f"提取 WHERE 条件失败: {e}")
            return False

        deleted_count = await self.delete_record(
            table=table,
            where_conditions=where_conditions,
            where_values=where_values,
            success_msg=success_msg,
            warning_msg=warning_msg,
            error_msg=error_msg
        )

        if deleted_count > 0:
            self.logger.info(f"{success_msg}，已删除 {deleted_count} 条记录 | 表: {table}")
            return True
        elif deleted_count == 0:
            self.logger.warning(f"{warning_msg}：未匹配任何记录 | 表: {table}")
            return True
        else:
            self.logger.error(f"{error_msg} | 表: {table}")
            return False
        
    # ------------------------------------------------------------------------------------------------
    # 动态事务相关功能函数
    # ------------------------------------------------------------------------------------------------   
    async def _send_dynamic_transaction_request(self, request) -> httpx.Response:
        """
        向 MySQL Service 发送动态事务的请求。

        自动根据请求类型路由到正确的接口。
        """
        from Service.MySQLService.schema.request import (
            MySQLServiceDynamicTransactionStartRequest,
            MySQLServiceDynamicTransactionCommitRequest,
            MySQLServiceDynamicTransactionRollbackRequest,
            MySQLServiceDynamicTransactionExecuteSQLRequest
        )
        
        # 映射：类型 -> endpoint path
        endpoint_map = {
            MySQLServiceDynamicTransactionStartRequest: "/database/mysql/dynamic_transaction/start",
            MySQLServiceDynamicTransactionCommitRequest: "/database/mysql/dynamic_transaction/commit",
            MySQLServiceDynamicTransactionRollbackRequest: "/database/mysql/dynamic_transaction/rollback",
            MySQLServiceDynamicTransactionExecuteSQLRequest: "/database/mysql/dynamic_transaction/execute",
        }

        request_type = type(request)
        endpoint = endpoint_map.get(request_type)

        if not endpoint:
            self.logger.error(f"[Dynamic Transaction] Unsupported request type: {request_type}")
            raise ValueError(f"Unsupported request type: {request_type}")

        url = f"{self.mysql_service_url}{endpoint}"

        try:
            response = await self.client.post(url=url, json=request.model_dump(mode="json", exclude_none=False))
            response.raise_for_status()
            return response
        
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error during dynamic transaction: {e.response.status_code}, {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            self.logger.error(f"Request error during dynamic transaction: {e}")
            raise HTTPException(status_code=503, detail="Failed to communicate with MySQLService.")
        except Exception as e:
            self.logger.error(f"Unexpected error during dynamic transaction: {e}")
            raise HTTPException(status_code=500, detail="Internal server error.")
    
    
    async def _execute_transaction_sql(self, session_id: str, sql: str, sql_args = None) -> Optional[int]:
        """
            执行一条 SQL 语句。
            
            返回：
                - 如果是 INSERT，则返回 last_insert_id（可能为 0）
                - 如果是 UPDATE/DELETE，返回 1 表示成功
                - 如果失败，返回 None
        """
        from Service.MySQLService.schema.request import MySQLServiceDynamicTransactionExecuteSQLRequest
        
        self.logger.info(f"[Execute SQL] session_id: {session_id}, sql: {sql}, sql_args: {sql_args}")
        req = MySQLServiceDynamicTransactionExecuteSQLRequest(
            session_id=session_id,
            sql=sql,
            sql_args=sql_args or []
        )
        res = await self._send_dynamic_transaction_request(request=req)
        result = res.json()
        if not result.get("result", False):
            self.logger.error(f"[Execute SQL] Failed: {result}")
            return None
        return result.get("last_insert_id")  # 可能为 None（非 INSERT 语句）
    
    
    async def _start_transaction(self, connection_id: int) -> Optional[str]:
        """ 开始一个动态事务 """
        from Service.MySQLService.schema.request import MySQLServiceDynamicTransactionStartRequest
        
        req = MySQLServiceDynamicTransactionStartRequest(connection_id=connection_id)
        res = await self._send_dynamic_transaction_request(request=req)
        session_id = res.json().get("session_id")
        if not session_id:
            self.logger.error("[Start Transaction] session_id missing in response")
            return None
        return session_id
    
    
    async def _commit_transaction(self, session_id: str) -> bool:
        """ 提交事务 """
        from Service.MySQLService.schema.request import MySQLServiceDynamicTransactionCommitRequest
        
        req = MySQLServiceDynamicTransactionCommitRequest(session_id=session_id)
        res = await self._send_dynamic_transaction_request(request=req)
        result = res.json()
        return result.get("result", False)


    async def _rollback_transaction(self, session_id: str) -> None:
        """事务失败时回滚"""
        from Service.MySQLService.schema.request import MySQLServiceDynamicTransactionRollbackRequest
        
        rollback_req = MySQLServiceDynamicTransactionRollbackRequest(session_id=session_id)
        await self._send_dynamic_transaction_request(request=rollback_req)
