# Project:      Agent
# Author:       yomu
# Time:         2024/12/12
# Version:      0.1
# Description:  agent User information database initialize

"""
    用户账户数据库管理类
"""
import httpx
import uuid
import re
import json
from typing import Tuple, Optional, Dict, List, Any
from dotenv import dotenv_values
from logging import Logger
from fastapi import HTTPException
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config
from Module.Utils.FormatValidate import is_email, is_account_name
from Module.Utils.Database.SQLBuilder import SQLBuilder
from Module.Utils.Database.SQLExecutor import SQLExecutor
from Module.Utils.ToolFunctions import retry
from Module.Utils.Database.MySQLAgentResponseType import (
    MySQLAgentConnectDatabaseResponse, 
    MySQLAgentInsertResponse, 
    MySQLAgentUpdateResponse, 
    MySQLAgentDeleteResponse, 
    MySQLAgentQueryResponse
)
from Module.Utils.Database.UserAccountDatabaseSQLParameterSchema import (
    SQL_REQUEST_ALLOWED_FIELDS,
    get_allowed_fields,
    filter_writable_fields,
    FieldSelectionSchema,
    StrictBaseModel,
    UserStatus,
    TableUsersSchema, TableUsersInsertSchema, TableUsersUpdateSetSchema, TableUsersUpdateWhereSchema, TableUsersDeleteWhereSchema, TableUsersQueryWhereSchema,
    TableUserProfileSchema, TableUserProfileInsertSchema, TableUserProfileUpdateSetSchema, TableUserProfileUpdateWhereSchema, TableUserProfileDeleteSchema, TableUserProfileQueryWhereSchema,
    TableUserLoginLogsSchema, TableUserLoginLogsInsertSchema, TableUserLoginLogsDeleteWhereSchema, TableUserLoginLogsQueryWhereSchema,
    UserLanguage,
    TableUserSettingsSchema, TableUserSettingsInsertSchema, TableUserSettingsUpdateSetSchema, TableUserSettingsUpdateWhereSchema, TableUserSettingsDeleteWhereSchema, TableUserSettingsQueryWhereSchema,
    UserAccountActionType,
    TableUserAccountActionsSchema, TableUserAccountActionsInsertSchema, TableUserAccountActionsDeleteWhereSchema, TableUserAccountActionsQueryWhereSchema,
    UserNotificationType,
    TableUserNotificationsSchema, TableUserNotificationsInsertSchema, TableUserNotificationsUpdateSetSchema, TableUserNotificationsUpdateWhereSchema, TableUserNotificationsDeleteWhereSchema, TableUserNotificationsQueryWhereSchema,
    TableUserFilesSchema, TableUserFilesInsertSchema, TableUserFilesUpdateSetSchema, TableUserFilesUpdateWhereSchema, TableUserFilesDeleteSchema, TableUserFilesQueryWhereSchema,
    TableConversationsSchema, TableConversationsInsertSchema, TableConversationsUpdateSchema, TableConversationsDeleteSchema
)


class UserAccountDataBaseAgent():
    """
        该类负责用户账户相关数据的管理和操作
        
        主要功能：
            1. 提供用户账户相关数据的增删改查接口
            2. 保存MySQLAgent返回的数据库连接ID
            3. 该类的所有方法都需要在数据库连接成功后才能调用
            4. 该类只为UserService提供服务，UserService会在需要时调用该类的方法

        该Agent管理的数据库名称: userinfo

        注意：
            1. 该类初始化时不进行数据库的连接，只进行参数设置
            2. 该类的init_connection()函数只会在上层UserService中的lifespan中进行手动调用
            3. 该类的所有方法都需要在数据库连接成功后才能调用
            4. 该类只为UserService提供服务，UserService会在需要时调用该类的方法

        配置文件为 config.yml ,配置文件路径存放在 Init/.env 中的 INIT_CONFIG_PATH 变量中
            配置内容为：
                user_account_database_config：
                    host
                    port
                    user
                    password
                    database
                    charset
                                
        ### 需要手动在mysql数据库中创建用户信息数据库 
        
        注：
            1.要先手动创建一个名为userinfo的database才行
            2. 创建表的SQL语句以及各个表的结构见 UserAccountDatabseSQLParameterSchema.py:    
                用户主表 (`users`)
                用户扩展资料 (`user_profile`)
                用户登录认证 (`user_login_logs`)
                用户自定义设置 (`user_settings`)
                用户账户行为 (`user_account_actions`)
                用户通知与消息 (`user_notifications`)
                用户文件 (`user_files`)
                
    """
    def __init__(self, logger: Optional[Logger]=None):
        self.logger = logger or setup_logger(name="UserAccountDataBaseAgent", log_path="InternalModule")
        
        # 加载环境变量和配置
        self.env_vars = dotenv_values("/home/yomu/agent/Module/Utils/Database/.env")
        self.config_path = self.env_vars.get("USER_ACCOUNT_DATABASE_AGENT_CONFIG_PATH","")
        self.config = load_config(config_path=self.config_path, config_name='UserAccountDataBaseAgent', logger=self.logger)
        
        # 验证配置文件
        required_keys = [ "mysql_host", "mysql_port", "mysql_agent_url", "mysql_user",  "mysql_password", "database", "charset"]
        validate_config(required_keys, self.config, self.logger)
        
        # MySQL配置
        self.mysql_host = self.config.get("mysql_host", "")
        self.mysql_port = self.config.get("mysql_port", "")
        self.mysql_agent_url = self.config.get("mysql_agent_url", "")
        self.mysql_user = self.config.get("mysql_user", "")
        self.mysql_password = self.config.get("mysql_password", "")  
        self.database = self.config.get("database","")
        self.charset = self.config.get("charset", "") 
        
        # 初始化 AsyncClient
        self.client: httpx.AsyncClient = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(10.0, read=60.0)
        )
        
        # 向MySQLAgent注册，返回一个MySQL数据库链接id，在MySQLAgent中存放着
        # 一个(id, mysql数据库连接对象)的映射
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
        真正执行连接, 并为 self.db_connect_id 赋值
        在上层的USerService中的lifespan中手动调用。
        该类初始化时不调用。
        """
        try:
            self.db_connect_id = await self.connect_to_database()
            if self.db_connect_id == -1:
                self.logger.error("Failed to connect to database,connect id == -1")
                raise ValueError("Failed to connect to database,connect id == -1")
            else:
                self.logger.info(f"db_connect_id = {self.db_connect_id}")
                # 同步到 SQLExecutor
                self.sql_executor.db_connect_id = self.db_connect_id
        except Exception as e:
            self.logger.error(f"Failed to init connection: {e}")
            raise
        
        
    async def connect_to_database(self) -> int:
        """
        连接MySQL数据库
        返回: 连接ID
        """
        headers = {"Content-Type": "application/json"}
        url = self.mysql_agent_url + "/database/mysql/connect"
        payload = {
            "host": self.mysql_host,
            "port": self.mysql_port,
            "user": self.mysql_user,
            "password": self.mysql_password,
            "database": self.database,
            "charset":  self.charset
        }
        try:
            response = await self.client.post(url=url, json=payload, headers=headers, timeout=120.0)
            response.raise_for_status()
            
            if response.status_code != 200:
                self.logger.error(f"Unexpected response structure: {response.json()}")
                raise ValueError(f"Failed to connect to the database '{self.database}'")
            
            response_dict: Dict = response.json()
            response_data = MySQLAgentConnectDatabaseResponse.model_validate(response_dict)
            
            if response_data.data is None:
                self.logger.error(f"Failed to connect database '{self.database}.'")
                raise HTTPException(status_code=500, detail=f"Internal server error. Failed to connect database '{self.database}.'")
            else:
                id = response_data.data.connection_id
                if id == -1:
                    self.logger.error(f"Failed connect to the database '{self.database}'. Message: '{response_data}'")
                    raise HTTPException(status_code=500, detail="Internal server error. Get the default wrong ConnectionID: -1")
                else: 
                    self.logger.info(f"Success connect to the database '{self.database}'. Message: '{response_data}'")
                    return id
                
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Connect to database '{self.database}' failed! HTTP error: {e.response.status_code}, {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        
        except httpx.RequestError as e:
            self.logger.error(f"Connect to database '{self.database}' failed! Request error: {e}")
            raise HTTPException(status_code=503, detail="Failed to communicate with MySQLAgent.")
        
        except Exception as e:
            self.logger.error(f"Connect to database '{self.database}' failed! Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error.")
        
   
    def extract_where_from_schema(self, schema: StrictBaseModel, keys: List[str]) -> tuple[List[str], List[Any]]:
        """
        从 Pydantic 模型(xxxDeleteSchema or xxxUpdtaeSchema ...)中提取 WHERE 条件和参数值

        :param schema: Pydantic 模型实例（如 DeleteSchema）
        :param keys: 需要构造 WHERE 条件的字段名列表
        :return: (条件表达式列表, 参数值列表)
        """
        conditions = []
        values = []

        for key in keys:
            value = getattr(schema, key)
            if value is None:
                raise ValueError(f"字段 {key} 不能为 None")
            conditions.append(f"{key} = %s")
            values.append(value)

        return conditions, values
       
    
    def extract_select_fields_from_schema(self, schema: FieldSelectionSchema, allowed_keys: List[str])-> Optional[List[str]]:
        """
        从 Pydantic 模型(FieldSelectionSchema)中提取 SELECT 值
        如果传入的FieldSelectionSchema中的fields字段为None，则返回None
        如果经过筛选后没有字段剩余，则返回None
        
        :param schema: Pydantic 模型FieldSelectionSchema实例
        :param allowed_keys: 允许的查询字段(即SELECT字段)
        :return: (条件表达式列表, 参数值列表)
        """
        if schema.fields is None:   
            return None
        
        allowed_fields = [field for field in schema.fields if field in allowed_keys]
    
        disallowed_fields = set(schema.fields) - set(allowed_fields)
        for field in disallowed_fields:
            self.logger.warning(f"Field '{field}' is not allowed in this context. Skipping.")

        return allowed_fields or None
        
        
     
    # ------------------------------------------------------------------------------------------------
    # 功能函数---查询表项目
    # ------------------------------------------------------------------------------------------------     
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

        :param table: 表名
        :param fields: 要查询的字段
        :param where_conditions: WHERE 条件
        :param where_values: WHERE 条件对应的值
        :param order_by: ORDER BY 子句
        :param limit: LIMIT 子句
        :param offset: OFFSET 子句
        :param success_msg: 成功日志
        :param warning_msg: 警告日志
        :param error_msg: 错误日志
        :return: 查询结果列表，失败时返回 None
        """
        sql, sql_args = self.sql_builder.build_query_sql(
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
            "id": self.db_connect_id,
            "sql": sql,
            "sql_args": sql_args
        }

        try:
            # 发送给MySQLAgent
            response = await self.client.post(url=url, json=payload, timeout=60.0)
            response.raise_for_status()
            response_data = response.json()
            
            self.logger.debug(f"In query_many: Response: {response}")

            if response.status_code == 200 and response_data.get("Result") is True:
                self.logger.info(success_msg)
                return response_data.get("Query Result") or []
            else:
                self.logger.warning(f"{warning_msg} | Response: {response_data}")
                return None
        except Exception as e:
            self.logger.error(f"{error_msg}: {str(e)}")
            return None

    async def query_one(self, table: str,
                    fields: Optional[List[str]] = None,
                    where_conditions: Optional[List[str]] = None,
                    where_values: Optional[List] = None,
                    order_by: Optional[str] = None,
                    warning_msg: str = "Query One Warning.",
                    error_msg: str = "Query One Error.") -> Optional[Dict]:
        """
        执行 SELECT 查询并返回一条记录

        :param table: 表名
        :param fields: 要查询的列
        :param where_conditions: WHERE 条件
        :param where_values: WHERE 条件对应的值
        :param order_by: ORDER BY 子句
        :param warning_msg: 警告日志
        :param error_msg: 错误日志
        :return: 查询结果字典，失败时返回 None
        """
        # 转发
        result = await self.query_many(table=table,
                                       fields=fields,
                                       where_conditions=where_conditions,
                                       where_values=where_values,
                                       limit=1,
                                       order_by=order_by,
                                       warning_msg=warning_msg,
                                       error_msg=error_msg)
        return result[0] if result else None

    async def _query_record_by_schema(
        self,
        table: str,
        query_schema: StrictBaseModel,
        select_schema: FieldSelectionSchema,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[dict]:
        """
        根据 Schema 执行查询（自动提取 WHERE）

        :param table: 表名
        :param query_schema: Pydantic 对象，用于生成 WHERE 条件
        :param select_fields: 允许的 WHERE 字段白名单（一般通过 get_allowed_fields(table, "query")）
        :param fields: 要查询的字段（如果为 None 则返回全部字段）
        :param order_by: 排序字段
        :param limit: 限制数量
        :param offset: 偏移量
        :return: 查询结果（列表）
        """
        # 提取 WHERE 条件
        try:
            where_conditions, where_values = self.extract_where_from_schema(
                schema=query_schema,
                keys=list(get_allowed_fields(table=table, action="query"))
            )
        except Exception as e:
            self.logger.error(f"从 QuerySchema 提取 WHERE 条件失败: {e}")
            return []
        
        # 提取 SELECT 字段
        try:
            select_fields = self.extract_select_fields_from_schema(
                schema=select_schema,
                allowed_keys=list(get_allowed_fields(table=table, action="query"))
            )
        except Exception as e:
            self.logger.error(f"从 FieldSelectionSchema 提取 SELECT 字段失败: {e}")
            return []

        if select_fields is None:
            select_fields = ["*"]  # 如果未指定字段，则查询所有字段

        return await self._query_record(
            table=table,
            fields=select_fields,
            where_conditions=where_conditions,
            where_values=where_values,
            order_by=order_by,
            limit=limit,
            offset=offset
        )
        
    async def _query_record(
        self,
        table: str,
        fields: Optional[List[str]] = None,
        where_conditions: Optional[List[str]] = None,
        where_values: Optional[List[Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[dict]:
        """
        通用查询函数

        :param table: 表名
        :param fields: 查询字段列表，默认为 *
        :param where_conditions: WHERE 条件列表（如 ["user_id = %s", "status = %s"]）
        :param where_values: 与条件对应的参数
        :param order_by: 排序条件（如 "created_at DESC"）
        :param limit: 限制返回条数
        :param offset: 偏移量
        :return: 查询结果（列表字典）
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
            return []

        url = self.mysql_agent_url + "/database/mysql/select"

        try:
            response_dict = await self.sql_executor.execute_query_sql(
                url=url,
                sql=sql,
                sql_args=sql_args,
                success_msg=f"查询成功: {table}",
                warning_msg=f"查询完成但无匹配记录: {table}",
                error_msg=f"查询失败: {table}"
            )
            return response_dict.get("data", {}).get("records", [])
        except Exception as e:
            self.logger.error(f"执行 SELECT 失败: {e}")
            return []
        
    # ------------------------------------------------------------------------------------------------
    # 功能函数---插入表项目
    # ------------------------------------------------------------------------------------------------
    async def insert_users(self, insert_data: TableUsersInsertSchema) -> int | None:
        """
        插入 users 表项目

        :param insert_data: TableUsersInsertSchema 对象，包含以下字段：
                account: 用户账号
                email: 用户邮箱
                password_hash: 用户密码哈希
                user_name: 用户昵称
                file_folder_path: 用户文件夹路径

        :return: 成功返回 user_id，失败返回 None
        """
        table = "users"
        
        # 清洗数据
        data = filter_writable_fields(
            schema=insert_data,
            allowed_fields=get_allowed_fields(table=table, action="insert")
        )
        
        # 2. 构造 SQL
        try:
            sql, sql_args = self.sql_builder.build_insert_sql(table, data)
        except Exception as e:
            self.logger.error(f"SQL构建失败: {e}")
            return None
        
        # 构建请求URL
        url = self.mysql_agent_url + "/database/mysql/insert"

        # 执行插入
        try:
            response_dict = await self.sql_executor.execute_insert_sql(url=url, sql=sql, sql_args=sql_args,
                                                warning_msg=f"User info insert may have failed for account: {insert_data.account}",
                                                success_msg=f"User info insert succeeded for account: {insert_data.account}",
                                                error_msg=f"Insert error for account: {insert_data.account}")
            
            # 校验响应结构
            insert_response = MySQLAgentInsertResponse.model_validate(response_dict)
            
            if insert_response.result is False:
                self.logger.error(f"插入失败：{insert_response.message}")
                return None

            if not insert_response.data or insert_response.data.last_insert_id is None:
                self.logger.warning("插入成功但未返回主键 ID")
                return None
    
            return insert_response.data.last_insert_id
        
        except Exception as e:
            self.logger.error(f"插入用户数据失败: {e}")
            return None    

    async def insert_user_profile(self, insert_data: TableUserProfileInsertSchema) -> bool:
        return await self._insert_record(
            table="user_profile",
            insert_data=insert_data,
            warning_msg=f"User profile insert may have failed. User id: {insert_data.user_id}",
            success_msg=f"User profile insert succeeded. User id: {insert_data.user_id}",
            error_msg=f"Insert error. User id: {insert_data.user_id}"
        )

    async def insert_user_login_logs(self, insert_data: TableUserLoginLogsInsertSchema) -> bool:
        return await self._insert_record(
            table="user_login_logs",
            insert_data=insert_data,
            warning_msg=f"User login log insert may have failed. User id: {insert_data.user_id}",
            success_msg=f"User login log insert succeeded. User id: {insert_data.user_id}",
            error_msg=f"Insert error. User id: {insert_data.user_id}"
        )

    async def insert_user_settings(self, insert_data: TableUserSettingsInsertSchema) -> bool:
        return await self._insert_record(
            table="user_settings",
            insert_data=insert_data,
            warning_msg=f"User settings insert may have failed. User id: {insert_data.user_id}",
            success_msg=f"User settings insert succeeded. User id: {insert_data.user_id}",
            error_msg=f"Insert error. User id: {insert_data.user_id}"
        )

    async def insert_user_account_actions(self, insert_data: TableUserAccountActionsInsertSchema) -> bool:
        return await self._insert_record(
            table="user_account_actions",
            insert_data=insert_data,
            warning_msg=f"User account action insert may have failed. User id: {insert_data.user_id}",
            success_msg=f"User account action insert succeeded. User id: {insert_data.user_id}",
            error_msg=f"Insert error. User id: {insert_data.user_id}"
        )

    async def insert_user_notifications(self, insert_data: TableUserNotificationsInsertSchema) -> bool:
        return await self._insert_record(
            table="user_notifications",
            insert_data=insert_data,
            warning_msg=f"User notification insert may have failed. User id: {insert_data.user_id}",
            success_msg=f"User notification insert succeeded. User id: {insert_data.user_id}",
            error_msg=f"Insert error. User id: {insert_data.user_id}"
        )

    async def insert_user_files(self, insert_data: TableUserFilesInsertSchema) -> bool:
        return await self._insert_record(
            table="user_files",
            insert_data=insert_data,
            warning_msg=f"User files insert may have failed. User id: {insert_data.user_id}",
            success_msg=f"User files insert succeeded. User id: {insert_data.user_id}",
            error_msg=f"Insert error. User id: {insert_data.user_id}"
        )
       
    async def _insert_record(
        self,
        table: str,
        insert_data: BaseModel,
        warning_msg: str,
        success_msg: str,
        error_msg: str
    ) -> bool:
        """
        插入记录
        
        :param table: 表名
        :param insert_data: 要插入的数据，必须是一个继承自 BaseModel 的对象
        :param warning_msg: 警告日志信息
        :param success_msg: 成功日志信息
        :param error_msg: 错误日志信息
        :return: 
        """
        # 清洗数据
        data = filter_writable_fields(
            schema=insert_data,
            allowed_fields=get_allowed_fields(table=table, action="insert")
        )
        
        # 构造 SQL
        try:
            sql, sql_args = self.sql_builder.build_insert_sql(table, data)
        except Exception as e:
            self.logger.error(f"SQL构建失败: {e}")
            return False

        # 构建请求URL
        url = self.mysql_agent_url + "/database/mysql/insert"
        
        # 执行插入
        try:
            response_dict = await self.sql_executor.execute_insert_sql(
                url=url,
                sql=sql,
                sql_args=sql_args,
                warning_msg=warning_msg,
                success_msg=success_msg,
                error_msg=error_msg
            )
            # 校验响应结构
            insert_response = MySQLAgentInsertResponse.model_validate(response_dict)
            
            # 检查插入结果
            if insert_response.result is False:
                self.logger.warning(
                    f"{error_msg}：{insert_response.message} | "
                    f"错误码: {insert_response.err_code} | "
                    f"字段错误: {insert_response.errors}"
                )
                return False
            return True
        except Exception as e:
            self.logger.error(f"{error_msg}: {e}")
            return False
        
    # ------------------------------------------------------------------------------------------------
    # 功能函数---更新表项目
    # ------------------------------------------------------------------------------------------------
    async def update_users(self, 
                           update_data: TableUsersUpdateSetSchema,
                           where_conditions: List[str],
                           where_values: List[Any]) -> bool:
        return await self._update_record(
            table="users",
            update_data=update_data,
            where_conditions=where_conditions,
            where_values=where_values,
            warning_msg=f"User info update may have failed. ",
            success_msg=f"User info update succeeded.",
            error_msg=f"Update error."
        )

    async def update_user_profile(self, 
                                  update_data: TableUserProfileUpdateSetSchema,
                                  where_conditions: List[str],
                                  where_values: List[Any]) -> bool:
        return await self._update_record(
            table="user_profile",
            update_data=update_data,
            where_conditions=where_conditions,
            where_values=where_values,
            warning_msg=f"User profile update may have failed.",
            success_msg=f"User profile update succeeded.",
            error_msg=f"Update error."
        )

    async def update_user_settings(self, 
                                   update_data: TableUserSettingsUpdateSetSchema,
                                   where_conditions: List[str],
                                    where_values: List[Any]) -> bool:
        return await self._update_record(
            table="user_settings",
            update_data=update_data,
            where_conditions=where_conditions,
            where_values=where_values,
            warning_msg=f"User settings update may have failed.",
            success_msg=f"User settings update succeeded.",
            error_msg=f"Update error."
        )

    async def update_user_notifications(self, 
                                        update_data: TableUserNotificationsUpdateSetSchema,
                                        where_conditions: List[str],
                                        where_values: List[Any]) -> bool:
        return await self._update_record(
            table="user_notifications",
            update_data=update_data,
            where_conditions=where_conditions,
            where_values=where_values,
            warning_msg=f"User notifications update may have failed. ",
            success_msg=f"User notifications update succeeded. ",
            error_msg=f"Update error. "
        )

    async def update_user_files(self,
                                update_data: TableUserFilesUpdateSetSchema,
                                where_conditions: List[str],
                                where_values: List[Any]) -> bool:
        return await self._update_record(
            table="user_files",
            update_data=update_data,
            where_conditions=where_conditions,
            where_values=where_values,
            warning_msg=f"User files update may have failed.",
            success_msg=f"User files update succeeded.",
            error_msg=f"Update error."
        )
        
    async def _update_record(
        self,
        table: str,
        update_data: BaseModel,
        where_conditions: List[str],
        where_values: List[Any],
        warning_msg: str,
        success_msg: str,
        error_msg: str
    ) -> bool:
        """
        更新指定表的记录(该函数不会抛出异常)
        
        :param  table: 表名
        :param update_data: 要更新的数据，必须是一个继承自 BaseModel 的对象
        :param where_conditions: WHERE 条件表达式列表
        :param where_values: 对应的参数值列表
        :param warning_msg: 警告日志信息
        :param success_msg: 成功日志信息
        :param error_msg: 错误日志信息
        :return: 是否更新成功
        """
        if not where_conditions or not where_values:
            self.logger.error("WHERE 条件缺失，拒绝执行更新")
            return False
        
        if len(where_conditions) != len(where_values):
            self.logger.error("WHERE 条件与值长度不一致")
            return False
        
        # 清洗数据
        data = filter_writable_fields(
            schema=update_data,
            allowed_fields=get_allowed_fields(table=table, action="update")
        )
        
        if not data:
            self.logger.warning(f"{warning_msg}：清洗后无可更新字段")
            return False
        
        # 构造 SQL
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
        
        # 构建URL
        url = self.mysql_agent_url + "/database/mysql/update"
        
        # 执行SQL
        try:
            response_dict = await self.sql_executor.execute_update_sql(
                url=url,
                sql=sql,
                sql_args=sql_args,
                warning_msg=warning_msg,
                success_msg=success_msg,
                error_msg=error_msg
            )
            # 校验响应结构
            update_response = MySQLAgentUpdateResponse.model_validate(response_dict)
            
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
        
    # ------------------------------------------------------------------------------------------------
    # 功能函数---删除表项目
    # ------------------------------------------------------------------------------------------------ 
    async def delete_users(self, delete_data: TableUsersDeleteWhereSchema) -> bool:
        return await self._delete_record_by_schema(
            table="users",
            schema=delete_data,
            success_msg=f"删除用户成功",
            warning_msg=f"删除用户时未命中任何记录",
            error_msg=f"删除用户失败"
        )
    
    async def delete_user_profile(self, delete_data: TableUserProfileDeleteSchema) -> bool:
        return await self._delete_record_by_schema(
            table="user_profile",
            schema=delete_data,
            success_msg=f"删除用户扩展资料成功",
            warning_msg=f"删除用户扩展资料时未命中任何记录",
            error_msg=f"删除用户扩展资料失败"
        )
        
    async def delete_user_login_logs(self, delete_data: TableUserLoginLogsDeleteWhereSchema) -> bool:
        return await self._delete_record_by_schema(
            table="user_login_logs",
            schema=delete_data,
            success_msg=f"删除用户登录日志成功",
            warning_msg=f"删除用户登录日志时未命中任何记录",
            error_msg=f"删除用户登录日志失败"
        )
        
    async def delete_user_settings(self, delete_data: TableUserSettingsDeleteWhereSchema) -> bool:
        return await self._delete_record_by_schema(
            table="user_settings",
            schema=delete_data,
            success_msg=f"删除用户设置成功",
            warning_msg=f"删除用户设置时未命中任何记录",
            error_msg=f"删除用户设置失败"
        )
        
    async def delete_user_account_actions(self, delete_data: TableUserAccountActionsDeleteWhereSchema) -> bool:
        return await self._delete_record_by_schema(
            table="user_account_actions",
            schema=delete_data,
            success_msg=f"删除用户账户行为成功",
            warning_msg=f"删除用户账户行为时未命中任何记录",
            error_msg=f"删除用户账户行为失败"
        )
        
    async def delete_user_notifications(self, delete_data: TableUserNotificationsDeleteWhereSchema) -> bool:
        return await self._delete_record_by_schema(
            table="user_notifications",
            schema=delete_data,
            success_msg=f"删除用户通知成功",
            warning_msg=f"删除用户通知时未命中任何记录",
            error_msg=f"删除用户通知失败"
        )
        
    async def delete_user_files(self, delete_data: TableUserFilesDeleteSchema) -> bool:
        return await self._delete_record_by_schema(
            table="user_files",
            schema=delete_data,
            success_msg=f"删除用户文件成功",
            warning_msg=f"删除用户文件时未命中任何记录",
            error_msg=f"删除用户文件失败"
        )
    
    async def _delete_record_by_schema(self,
                                  table: str,
                                  schema: StrictBaseModel,
                                  success_msg: str = "Delete success.",
                                  warning_msg: str = "Delete warning.",
                                  error_msg: str = "Delete error.") -> bool:
        """
        通用 delete 调用（通过 schema + 表名）
        该函数不会抛出异常
        """
        
        try:
            where_conditions, where_values = self.extract_where_from_schema(
                schema=schema,
                keys=list(get_allowed_fields(table=table, action="delete"))
            )
        except Exception as e:
            self.logger.error(f"提取 WHERE 条件失败: {e}")
            return False

        deleted_count = await self._delete_record(
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

    async def _delete_record(self, table: str,
                     where_conditions: List[str],
                     where_values: List[Any],
                     success_msg: str = "Delete success.",
                     warning_msg: str = "Delete warning.",
                     error_msg: str = "Delete error.") -> int:
        """
        删除记录(该函数不会报异常)

        :param table: 表名
        :param where_conditions: WHERE 条件表达式列表
        :param where_values: 对应参数值
        :param success_msg: 成功日志
        :param warning_msg: 警告日志
        :param error_msg: 错误日志
        :return: 实际删除的行数（0 表示未删，-1 表示失败）
        """
        
        if not where_conditions or not where_values:
            self.logger.warning(f"{warning_msg}：WHERE 条件或值缺失，跳过删除")
            return -1
        
        if len(where_conditions) != len(where_values):
            self.logger.error("WHERE 条件与值长度不一致")
            return -1
        
        # 构造 SQL
        try:
            sql, args = self.sql_builder.build_delete_sql(
                table=table,
                where_conditions=where_conditions,
                where_values=where_values
            )
        except Exception as e:
            self.logger.error(f"SQL构建失败: {e}")
            return -1
        
        # 构建请求URL
        url = self.mysql_agent_url + "/database/mysql/delete"
        
        self.logger.info(f"Executing delete SQL: {sql} with args: {args} | Table: {table} | URL: {url}")
        
        # 执行SQL
        try:
            response_dict = await self.sql_executor.execute_delete_sql(
                url=url,
                sql=sql,
                sql_args=args,
                success_msg=success_msg,
                warning_msg=warning_msg,
                error_msg=error_msg
            )
            # 校验响应结构
            delete_response = MySQLAgentDeleteResponse.model_validate(response_dict)
                        
            if delete_response.result is False:
                self.logger.warning(
                    f"{error_msg}：{delete_response.message} | "
                    f"错误码: {delete_response.err_code} | "
                    f"字段错误: {delete_response.errors}"
                )
                return 0  # 删除失败，返回 0 行受影响
            
            return delete_response.data.rows_affected
        
        except Exception as e:
            self.logger.error(f"{error_msg}: {e}")
            return -1   # 出错，返回 -1


    # ------------------------------------------------------------------------------------------------
    # 软硬删除功能函数
    # ------------------------------------------------------------------------------------------------ 
    async def soft_delete_user_by_user_id(self, user_id: int) -> bool:
        """
        软删除用户：设为 'deleted' 并记录删除时间。

        :param user_id: 用户ID
        :return: 更新是否成功
        """
        update_data= TableUsersUpdateSetSchema(
            status=UserStatus.deleted
        )
        # 1. 将users 表中的 status 设置为 'deleted'
        try:
            res = await self.update_users(
                update_data=update_data,
                where_conditions=["user_id = %s"],
                where_values=[user_id]
            )
        except Exception as e:
            self.logger.error(f"Soft delete failed! Error: {str(e)}")
            return False
        
        if not res:
            self.logger.warning(f"Soft delete may have failed. User ID: {user_id}")
            return False
        
        return True
        
            
    async def hard_delete_user_by_user_id(self, user_id: int) -> bool:
        """
        根据 user_id 删除用户（包含自动删除 user_profile 中的关联记录）。

        :param user_id: 用户ID
        :return: 删除是否成功
        """
        delete_data = TableUsersDeleteWhereSchema(user_id=user_id)
        
        # 1. 删除 users 表中数据(根据user_id)
        try:
            success = await self.delete_users(delete_data=delete_data)
            if not success:
                self.logger.warning(f"Hard delete may have failed. User ID: '{user_id}'")
        except Exception as e:
            self.logger.error(f"Delete failed! User ID: '{user_id}' Error: {str(e)}")
            return False

        # 2. 删除 user_profile 表中数据
        # 无需手动，因为user_id是 外键，下面的表同理
        # 3. 删除 user_login_logs 表中数据
        # 4. 删除 user_settings 表中数据
        # 5. 删除 user_account_actions 表中数据
        # 6. 删除 user_notifications 表中数据
        # 7. 删除 user_files 表中数据
    
        return True

        
    async def hard_delete_expired_users(self, days: int = 30) -> bool:
        """
        物理删除已标记为 deleted 且 deleted_at 超过 days 天的用户。
        """
        table = "users"
        where_conditions = [
            "status = %s",
            "deleted_at < (NOW() - INTERVAL %s DAY)"
        ]
        where_values = ["deleted", days]  # 只有一个需要参数化的字段

        deleted_count = await self._delete_record(
            table=table,
            where_conditions=where_conditions,
            where_values=where_values,
            success_msg="成功删除过期用户",
            warning_msg="删除操作完成，但无匹配用户",
            error_msg="物理删除过期用户失败"
        )

        if deleted_count > 0:
            self.logger.info(f"物理删除 {deleted_count} 条已过期的用户记录")
            return True
        elif deleted_count == 0:
            self.logger.warning("无已过期的 deleted 用户可删除")
            return True
        else:
            self.logger.error("物理删除过程出错")
            return False

        

    
    # ------------------------------------------------------------------------------------------------
    # 封装的上层功能函数
    # ------------------------------------------------------------------------------------------------      
    async def fetch_user_id_by_uuid(self, uuid: str) -> Optional[int]:
        """
        通过 UUID 在 users 表中查询 user_id

        :param uuid: 用户的 UUID

        :return: user_id ，如果未找到则返回 None
        """

        try:
            res = await self.query_one(
                table="users",
                fields=["user_id"],
                where_conditions=["user_uuid = %s"],
                where_values=[uuid]
            )
        except Exception as e:
            self.logger.error(f"Query failed! Error:{str(e)}")
            return None

        if res is None:
            self.logger.warning(f"No user found with UUID: {uuid}")
            return None

        return res["user_id"]
    

    async def fetch_user_id_and_password_by_email_or_account(self, identifier: str)-> Optional[tuple[int, str]]:
        """
        通过 email 或 account 在 users 表中查询 用户id 和 密码哈希

        :param identifier: 用户的 email 或 account

        :return: (user_id, password_hash) 元组，如果未找到则返回 None
        """
        fields = ["user_id", "password_hash"]
        where_conditions = []
        where_values = []
        
        if is_email(identifier):
            where_conditions.append("email = %s")
            where_values.append(identifier)
        elif is_account_name(identifier):
            where_conditions.append("account = %s")
            where_values.append(identifier)
        else:
            self.logger.warning(f"Invalid identifier: {identifier}. Need email or valid account.")
            return None

        try:
            res = await self.query_one(
                table="users",
                fields=fields,
                where_conditions=where_conditions,
                where_values=where_values
            )
        except Exception as e:
            self.logger.error(f"{str(e)}")
            return None

        if res is None:
            self.logger.warning(f"No user found with identifier: {identifier}")
            return None

        return res["user_id"], res["password_hash"]


    async def fetch_uuid_by_user_id(self, user_id: int) -> str | None:
        """
        通过 user_id 查询用户的 UUID

        :param user_id: 用户ID

        :return: 用户UUID，如果未找到则返回 None
        """
        try:
            res = await self.query_one(
                table="users",
                fields=["user_uuid"],
                where_conditions=["user_id = %s"],
                where_values=[user_id]
            )
        except Exception as e:
            self.logger.error(f"Query failed! Error:{str(e)}")
            return None

        if res is None:
            self.logger.warning(f"No user found with user_id: {user_id}")
            return None

        return res["user_uuid"]

    
    async def insert_new_user(self, account: str, email: str, password_hash: str, user_name: str) -> Optional[int]:
        """
        插入用户注册信息所有表。
            1. users 表
            2. user_profile 表
            3. user_settings 表
            
        :param: account 用户账号(必须)
        :param: email   用户邮箱(必须)
        :param: password_hash   用户密码hash值(必须)
        :param: user_name   用户名(必须)

        返回 user_id（成功）或 None（失败）
        """
        
        # 生成用户UUID
        user_uuid = str(uuid.uuid4())
        
        # 默认用户文件夹路径
        file_folder_path = f"Users/Files/{user_uuid}/"
        
        # 开启事务
        # TODO: 这里可以考虑使用事务来确保数据一致性
        
        # 1. 插入 users 表
        # 构建插入数据
        insert_data_users = TableUsersInsertSchema(
            user_uuid=user_uuid,
            account=account,
            email=email,
            password_hash=password_hash,
            file_folder_path=file_folder_path
        )  
        
        try:
            user_id = await self.insert_users(insert_data=insert_data_users)
        except Exception as e:
            self.logger.error(f"Insert users Failed. Error: {e}")
            return None
        
        if user_id is not None:
            self.logger.info(f"Insert users success. user_id: {user_id}")
        else:
            self.logger.warning(f"Insert users Failed. user_id: {user_id}")
            return None
        
        # 2. 插入 user_profile 表（使用默认头像）
        # 构建插入数据
        insert_data_user_profile = TableUserProfileInsertSchema(
            user_id=user_id,  # 这里使用上面插入成功的 user_id
            profile_picture_path=None,  # 默认头像
            signature=""  # 默认签名为空
        )
        
        try:
            res_insert_user_profile = await self.insert_user_profile(insert_data=insert_data_user_profile)
        except Exception as e:
            self.logger.error(f"Insert user profile Failed. Error: {e}")
            return None
        
        if res_insert_user_profile:
            self.logger.info(f"Inserted user profile. User ID: {user_id}")
        else:
            self.logger.warning(f"User profile insert may have failed. User ID: {user_id}")
            return None
        
        
        # 3. 插入 user_settings 表 (使用默认配置)
        # 构建插入数据
        insert_data_user_settings = TableUserSettingsInsertSchema(
            user_id=user_id,
            language=UserLanguage.zh,  # 默认语言
            configure={},  # 默认配置为空
            notification_setting={
                "notifications_enabled": True,# TODO 待在表中增加字段，到时候修改
                "settings_json": {}
            }  # 默认通知设置
        )
        
        try:
            res_insert_user_settings = await self.insert_user_settings(insert_data=insert_data_user_settings)
        except Exception as e:
            self.logger.error(f"Insert user settings Failed. Error: {e}")
            return None

        if res_insert_user_settings:
            self.logger.info(f"Inserted user settings. User ID: {user_id}")
        else:
            self.logger.warning(f"User settings insert may have failed. User ID: {user_id}")
            return None
        
 
    # TODO 待修改，是否需要统一接口参数为 TableUsersInsertSchema?
    async def update_user_password_by_user_id(self, user_id: int, new_password_hash: str) -> bool:
        """
        根据 user_id 更新用户密码哈希，并记录操作日志。
        
        1. 更新 users 表中的 password_hash 字段
        2. 向 user_account_actions 表中插入新纪录
        
        :param user_id: 用户ID
        :param new_password_hash: 新密码哈希
        :return: 是否成功
        """
        # 1. 更新 users 表
        update_success = await self._update_record(
            table="users",
            update_data=TableUsersUpdateSetSchema(password_hash=new_password_hash),
            where_conditions=["user_id = %s"],
            where_values=[user_id],
            success_msg="用户密码更新成功",
            warning_msg="用户密码更新可能未生效",
            error_msg="更新用户密码失败"
        )

        if not update_success:
            self.logger.error(f"用户密码更新失败，user_id={user_id}")
            return False

        # 2. 插入到 user_account_actions 表
        insert_success = await self._insert_record(
            table="user_account_actions",
            insert_data=TableUserAccountActionsInsertSchema(
                user_id=user_id,
                action_type=UserAccountActionType.password_change,
                action_detail=f"Password updated to {new_password_hash}"
            ),
            success_msg="用户行为记录插入成功",
            warning_msg="行为记录可能未插入成功",
            error_msg="插入用户行为记录失败"
        )

        if not insert_success:
            self.logger.error(f"用户行为记录插入失败，user_id={user_id}")
            return False

        self.logger.info(f"用户密码更新完成，user_id={user_id}")
        return True
