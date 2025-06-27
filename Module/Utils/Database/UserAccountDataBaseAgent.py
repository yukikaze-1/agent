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

from Module.Utils.Database.MySQLServiceRequestType import (
    MySQLServiceConnectRequest,
    MySQLServiceStaticTransactionRequest,
    MySQLServiceStaticTransactionSQL,
    MySQLServiceDynamicTransactionBaseRequest,
    MySQLServiceDynamicTransactionStartRequest,
    MySQLServiceDynamicTransactionCommitRequest,
    MySQLServiceDynamicTransactionRollbackRequest,
    MySQLServiceDynamicTransactionExecuteSQLRequest
)
from Module.Utils.Database.MySQLServiceResponseType import (
    MySQLServiceConnectDatabaseResponse, 
    MySQLServiceInsertResponse, 
    MySQLServiceUpdateResponse, 
    MySQLServiceDeleteResponse, 
    MySQLServiceQueryResponse,
    MySQLServiceDynamicTransactionStartResponse,
    MySQLServiceDynamicTransactionCommitResponse,
    MySQLServiceDynamicTransactionRollbackResponse,
    MySQLServiceDynamicTransactionExecuteSQLResponse
)
from Module.Utils.Database.UserAccountDatabaseSQLParameterSchema import (
    get_allowed_query_select_fields,
    InsertSchema,
    QueryWhereSchema,
    DeleteWhereSchema,
    UpdateWhereSchema,
    UpdateSetSchema,
    StrictBaseModel,
    UserStatus,
    TableUsersSchema, TableUsersInsertSchema, TableUsersUpdateSetSchema, TableUsersUpdateWhereSchema, TableUsersDeleteWhereSchema, TableUsersQueryWhereSchema,
    TableUserProfileSchema, TableUserProfileInsertSchema, TableUserProfileUpdateSetSchema, TableUserProfileUpdateWhereSchema, TableUserProfileDeleteWhereSchema, TableUserProfileQueryWhereSchema,
    TableUserLoginLogsSchema, TableUserLoginLogsInsertSchema, TableUserLoginLogsDeleteWhereSchema, TableUserLoginLogsQueryWhereSchema,
    UserLanguage,
    TableUserSettingsSchema, TableUserSettingsInsertSchema, TableUserSettingsUpdateSetSchema, TableUserSettingsUpdateWhereSchema, TableUserSettingsDeleteWhereSchema, TableUserSettingsQueryWhereSchema,
    UserAccountActionType,
    TableUserAccountActionsSchema, TableUserAccountActionsInsertSchema, TableUserAccountActionsDeleteWhereSchema, TableUserAccountActionsQueryWhereSchema,
    UserNotificationType,
    TableUserNotificationsSchema, TableUserNotificationsInsertSchema, TableUserNotificationsUpdateSetSchema, TableUserNotificationsUpdateWhereSchema, TableUserNotificationsDeleteWhereSchema, TableUserNotificationsQueryWhereSchema,
    TableUserFilesSchema, TableUserFilesInsertSchema, TableUserFilesUpdateSetSchema, TableUserFilesUpdateWhereSchema, TableUserFilesDeleteWhereSchema, TableUserFilesQueryWhereSchema,
    TableConversationsSchema, TableConversationsInsertSchema, TableConversationsUpdateSchema, TableConversationsDeleteSchema
)


def transfer_dict_in_schema_to_json(data: dict) -> dict:
    """ 
    将字典中的字典值转换为 JSON 字符串
    用于准备 SQL 参数，具体为将各种Schema中包含的dict转为json，确保嵌套字典可以正确存储到数据库中的json字段中。
    举例：
        insert_data = XXXSchema(...) # 构建Schema
        data = insert_data.model_dump(exclude_none=True) # Schema转为dict
        data = transfer_dict_in_schema_to_json(data) # Schema中的dict类型转为json
        
    :param data: 已经经过.model_dump()的Schema数据。
    """
    return {
        k: json.dumps(v) if isinstance(v, dict) else v
        for k, v in data.items()
    }


class UserAccountDataBaseAgent():
    """
        该类负责用户账户相关数据的管理和操作
        
        主要功能：
            1. 提供用户账户相关数据的增删改查接口
            2. 保存MySQLService返回的数据库连接ID
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
        required_keys = [ "mysql_host", "mysql_port", "mysql_service_url", "mysql_user",  "mysql_password", "database", "charset"]
        validate_config(required_keys, self.config, self.logger)
        
        # MySQL配置
        self.mysql_host = self.config.get("mysql_host", "")
        self.mysql_port = self.config.get("mysql_port", "")
        self.mysql_service_url = self.config.get("mysql_service_url", "")
        self.mysql_user = self.config.get("mysql_user", "")
        self.mysql_password = self.config.get("mysql_password", "")  
        self.database = self.config.get("database","")
        self.charset = self.config.get("charset", "") 
        
        # 初始化 AsyncClient
        self.client: httpx.AsyncClient = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(10.0, read=60.0)
        )
        
        # 向MySQLService注册，返回一个MySQL数据库链接id，在MySQLService中存放着
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
        返回: 成功时连接ID(非负)，失败时返回-1
        """
        
        url = self.mysql_service_url + "/database/mysql/connect"
        
        request = MySQLServiceConnectRequest(
            host=self.mysql_host,
            port=self.mysql_port,
            user=self.mysql_user,
            password=self.mysql_password,
            database=self.database,
            charset=self.charset
        )
        
        payload = request.model_dump(mode="json", exclude_none=True)
        
        try:
            response = await self.client.post(url=url, json=payload, timeout=120.0)
            response.raise_for_status()
            
            if response.status_code != 200:
                self.logger.error(f"Unexpected response structure: {response.json()}")
                raise ValueError(f"Failed to connect to the database '{self.database}'")
            
            response_dict: Dict = response.json()
            response_data = MySQLServiceConnectDatabaseResponse.model_validate(response_dict)
            
            return response_data.data.connection_id 
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Connect to database '{self.database}' failed! HTTP error: {e.response.status_code}, {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        
        except httpx.RequestError as e:
            self.logger.error(f"Connect to database '{self.database}' failed! Request error: {e}")
            raise HTTPException(status_code=503, detail="Failed to communicate with MySQLService.")
        
        except Exception as e:
            self.logger.error(f"Connect to database '{self.database}' failed! Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error.")
        
   
    def extract_where_from_schema(self, schema: QueryWhereSchema | UpdateWhereSchema | DeleteWhereSchema) -> tuple[list[str], list[Any]]:
        """
        从 Pydantic 模型中提取 WHERE 条件和参数值。

        :param schema: Pydantic 模型实例（如 QueryWhereSchema | UpdateWhereSchema | DeleteWhereSchema）
        :return: (条件表达式列表, 参数值列表)
        """
        conditions = []
        values = []

        for key, value in schema.model_dump(exclude_none=True).items():
            conditions.append(f"{key} = %s")
            values.append(value)

        return conditions, values        
        
     
    # ------------------------------------------------------------------------------------------------
    # 功能函数---查询表项目
    # ------------------------------------------------------------------------------------------------     
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

        :param table: 表名
        :param query_where: Pydantic 对象，用于生成 WHERE 条件
        :param select_fields: 允许的 WHERE 字段列表
        :param fields: 要查询的字段（如果为 None 则返回全部字段）
        :param order_by: 排序字段
        :param limit: 限制数量
        :param offset: 偏移量
        :return: 查询结果（列表）
        """
        # 提取 WHERE 条件
        try:
            where_conditions, where_values = self.extract_where_from_schema(schema=query_where)
        except Exception as e:
            self.logger.error(f"从 QuerySchema 提取 WHERE 条件失败: {e}")
            return {}
        
        if not select_fields:
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
    ) -> Dict:
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
            if response_dict:
                return response_dict.get("data", {})
            else:
                return {}
        except Exception as e:
            self.logger.error(f"执行 SELECT 失败: {e}")
            return {}
        
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
        
        # # 清洗数据
        # data = filter_writable_fields(
        #     schema=insert_data,
        #     allowed_fields=get_allowed_fields(table=table, action="insert")
        # )

        data = insert_data.model_dump(exclude_none=True)
        # 2. 构造 SQL
        try:
            sql, sql_args = self.sql_builder.build_insert_sql(table, data)
        except Exception as e:
            self.logger.error(f"SQL构建失败: {e}")
            return None
        
        # 构建请求URL
        url = self.mysql_service_url + "/database/mysql/insert"

        # 执行插入
        try:
            response_dict = await self.sql_executor.execute_insert_sql(url=url, sql=sql, sql_args=sql_args,
                                                warning_msg=f"User info insert may have failed for account: {insert_data.account}",
                                                success_msg=f"User info insert succeeded for account: {insert_data.account}",
                                                error_msg=f"Insert error for account: {insert_data.account}")
            
            # 校验响应结构
            insert_response = MySQLServiceInsertResponse.model_validate(response_dict)
            
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
        insert_data: InsertSchema,
        warning_msg: str,
        success_msg: str,
        error_msg: str
    ) -> bool:
        """
        插入记录。
        
        :param table: 表名
        :param insert_data: 要插入的数据，必须是一个继承自 InsertSchema 的对象
        :param warning_msg: 警告日志信息
        :param success_msg: 成功日志信息
        :param error_msg: 错误日志信息
        :return: 
        """
        # # 清洗数据
        # data = filter_writable_fields(
        #     schema=insert_data,
        #     allowed_fields=get_allowed_fields(table=table, action="insert")
        # )
        
        # 构造 SQL
        data = insert_data.model_dump(exclude_none=True)
        
        data = transfer_dict_in_schema_to_json(data)  # 将字典中的字典值转换为 JSON 字符串
        
        try:
            sql, sql_args = self.sql_builder.build_insert_sql(table=table, data=data)
        except Exception as e:
            self.logger.error(f"SQL构建失败: {e}")
            return False

        # 构建请求URL
        url = self.mysql_service_url + "/database/mysql/insert"
        
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
            insert_response = MySQLServiceInsertResponse.model_validate(response_dict)
            
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
                           update_where: TableUsersUpdateWhereSchema) -> bool:
        return await self._update_record(
            table="users",
            update_data=update_data,
            update_where=update_where,
            warning_msg=f"User info update may have failed. ",
            success_msg=f"User info update succeeded.",
            error_msg=f"Update error."
        )

    async def update_user_profile(self, 
                                  update_data: TableUserProfileUpdateSetSchema,
                                  update_where: TableUserProfileUpdateWhereSchema) -> bool:
        return await self._update_record(
            table="user_profile",
            update_data=update_data,
            update_where=update_where,
            warning_msg=f"User profile update may have failed.",
            success_msg=f"User profile update succeeded.",
            error_msg=f"Update error."
        )

    async def update_user_settings(self, 
                                   update_data: TableUserSettingsUpdateSetSchema,
                                   update_where: TableUserSettingsUpdateWhereSchema) -> bool:
        return await self._update_record(
            table="user_settings",
            update_data=update_data,
            update_where=update_where,
            warning_msg=f"User settings update may have failed.",
            success_msg=f"User settings update succeeded.",
            error_msg=f"Update error."
        )

    async def update_user_notifications(self, 
                                        update_data: TableUserNotificationsUpdateSetSchema,
                                        update_where: TableUserNotificationsUpdateWhereSchema) -> bool:
        return await self._update_record(
            table="user_notifications",
            update_data=update_data,
            update_where=update_where,
            warning_msg=f"User notifications update may have failed. ",
            success_msg=f"User notifications update succeeded. ",
            error_msg=f"Update error. "
        )

    async def update_user_files(self, update_data: TableUserFilesUpdateSetSchema, 
                                update_where: TableUserFilesUpdateWhereSchema) -> bool:
        return await self._update_record(
            table="user_files",
            update_data=update_data,
            update_where=update_where,
            warning_msg=f"User files update may have failed.",
            success_msg=f"User files update succeeded.",
            error_msg=f"Update error."
        )
        
    async def _update_record(
        self,
        table: str,
        update_data: UpdateSetSchema,
        update_where: UpdateWhereSchema,
        warning_msg: str,
        success_msg: str,
        error_msg: str
    ) -> bool:
        """
        更新指定表的记录(该函数不会抛出异常)
        
        :param  table: 表名
        :param update_data: 要更新的数据，必须是一个继承自 StrictBaseModel 的对象
        :param where_conditions: WHERE 条件表达式列表
        :param where_values: 对应的参数值列表
        :param warning_msg: 警告日志信息
        :param success_msg: 成功日志信息
        :param error_msg: 错误日志信息
        :return: 是否更新成功
        """
        # # 清洗数据
        # data = filter_writable_fields(
        #     schema=update_data,
        #     allowed_fields=get_allowed_fields(table=table, action="update")
        # )
        
        where_conditions, where_values = self.extract_where_from_schema(schema=update_where)

        data = update_data.model_dump(exclude_none=True)
        
        data = transfer_dict_in_schema_to_json(data)  # 将字典中的字典值转换为 JSON 字符串
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
        url = self.mysql_service_url + "/database/mysql/update"
        
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
        
    # ------------------------------------------------------------------------------------------------
    # 功能函数---删除表项目
    # ------------------------------------------------------------------------------------------------ 
    async def delete_users(self, delete_data: TableUsersDeleteWhereSchema) -> bool:
        return await self._delete_record_by_schema(
            table="users",
            delete_where=delete_data,
            success_msg=f"删除用户成功",
            warning_msg=f"删除用户时未命中任何记录",
            error_msg=f"删除用户失败"
        )
    
    async def delete_user_profile(self, delete_data: TableUserProfileDeleteWhereSchema) -> bool:
        return await self._delete_record_by_schema(
            table="user_profile",
            delete_where=delete_data,
            success_msg=f"删除用户扩展资料成功",
            warning_msg=f"删除用户扩展资料时未命中任何记录",
            error_msg=f"删除用户扩展资料失败"
        )
        
    async def delete_user_login_logs(self, delete_data: TableUserLoginLogsDeleteWhereSchema) -> bool:
        return await self._delete_record_by_schema(
            table="user_login_logs",
            delete_where=delete_data,
            success_msg=f"删除用户登录日志成功",
            warning_msg=f"删除用户登录日志时未命中任何记录",
            error_msg=f"删除用户登录日志失败"
        )
        
    async def delete_user_settings(self, delete_data: TableUserSettingsDeleteWhereSchema) -> bool:
        return await self._delete_record_by_schema(
            table="user_settings",
            delete_where=delete_data,
            success_msg=f"删除用户设置成功",
            warning_msg=f"删除用户设置时未命中任何记录",
            error_msg=f"删除用户设置失败"
        )
        
    async def delete_user_account_actions(self, delete_data: TableUserAccountActionsDeleteWhereSchema) -> bool:
        return await self._delete_record_by_schema(
            table="user_account_actions",
            delete_where=delete_data,
            success_msg=f"删除用户账户行为成功",
            warning_msg=f"删除用户账户行为时未命中任何记录",
            error_msg=f"删除用户账户行为失败"
        )
        
    async def delete_user_notifications(self, delete_data: TableUserNotificationsDeleteWhereSchema) -> bool:
        return await self._delete_record_by_schema(
            table="user_notifications",
            delete_where=delete_data,
            success_msg=f"删除用户通知成功",
            warning_msg=f"删除用户通知时未命中任何记录",
            error_msg=f"删除用户通知失败"
        )
        
    async def delete_user_files(self, delete_data: TableUserFilesDeleteWhereSchema) -> bool:
        return await self._delete_record_by_schema(
            table="user_files",
            delete_where=delete_data,
            success_msg=f"删除用户文件成功",
            warning_msg=f"删除用户文件时未命中任何记录",
            error_msg=f"删除用户文件失败"
        )
    
    async def _delete_record_by_schema(self,
                                  table: str,
                                  delete_where: DeleteWhereSchema,
                                  success_msg: str = "Delete success.",
                                  warning_msg: str = "Delete warning.",
                                  error_msg: str = "Delete error.") -> bool:
        """
        通用 delete 调用（通过 schema + 表名）
        该函数不会抛出异常
        """
        
        try:
            where_conditions, where_values = self.extract_where_from_schema(schema=delete_where)
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
        url = self.mysql_service_url + "/database/mysql/delete"
        
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
            delete_response = MySQLServiceDeleteResponse.model_validate(response_dict)
                        
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
        # 1. 将users 表中的 status 设置为 'deleted'
        try:
            res = await self.update_users(
                update_data=TableUsersUpdateSetSchema(status=UserStatus.deleted),
                update_where=TableUsersUpdateWhereSchema(user_id=user_id)
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
    # 动态事务相关功能函数
    # ------------------------------------------------------------------------------------------------   
    async def _send_dynamic_transaction_request(self, request: MySQLServiceDynamicTransactionBaseRequest)-> httpx.Response:
        """
        向 MySQL Service 发送动态事务的请求。

        自动根据请求类型路由到正确的接口。
        """
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
    
    
    async def _execute_transaction_sql(self, session_id: str, sql: str, sql_args: list | dict | None = None) -> Optional[int]:
        """
            执行一条 SQL 语句。
            
            返回：
                - 如果是 INSERT，则返回 last_insert_id（可能为 0）
                - 如果是 UPDATE/DELETE，返回 1 表示成功
                - 如果失败，返回 None
        """
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
        req = MySQLServiceDynamicTransactionStartRequest(connection_id=connection_id)
        res = await self._send_dynamic_transaction_request(request=req)
        session_id = res.json().get("session_id")
        if not session_id:
            self.logger.error("[Start Transaction] session_id missing in response")
            return None
        return session_id
    
    
    async def _commit_transaction(self, session_id: str) -> bool:
        """ 提交事务 """
        req = MySQLServiceDynamicTransactionCommitRequest(session_id=session_id)
        res = await self._send_dynamic_transaction_request(request=req)
        result = res.json()
        return result.get("result", False)


    async def _rollback_transaction(self, session_id: str) -> None:
        """事务失败时回滚"""
        rollback_req = MySQLServiceDynamicTransactionRollbackRequest(session_id=session_id)
        await self._send_dynamic_transaction_request(request=rollback_req)    
        
        
    # ------------------------------------------------------------------------------------------------
    # 封装的上层功能函数
    # ------------------------------------------------------------------------------------------------      
    async def fetch_user_id_by_uuid(self, user_uuid: str) -> Optional[int]:
        """
        通过 UUID 在 users 表中查询 user_id

        :param user_uuid: 用户的 UUID

        :return: user_id ，如果未找到则返回 None
        """

        try:
            res = await self.query_record_by_schema(
                table='users',
                query_where=TableUsersQueryWhereSchema(user_uuid=user_uuid),
                select_fields=['user_id']
            )
            
        except Exception as e:
            self.logger.error(f"Query failed! Error:{str(e)}")
            return None

        if res is None:
            self.logger.warning(f"No user found with UUID: {user_uuid}")
            return None
        # TODO 这里的返回值方式有问题，待修改
        return res[0]["user_id"]
    

    async def fetch_user_id_and_password_hash_by_email_or_account(self, identifier: str)-> Optional[tuple[int, str]]:
        """
        通过 email 或 account 在 users 表中查询 用户id 和 密码hash

        :param identifier: 用户的 email 或 account

        :return: (user_id, password_hash) 元组，如果未找到则返回 None
        """
        select_fields = ["user_id", "password_hash"]
        
        if not is_email(identifier) and not is_account_name(identifier):
            self.logger.warning(f"Invalid identifier: {identifier}. Need email or valid account.")
            return None

        try:
            res = await self.query_record_by_schema(
                table='users',
                query_where=TableUsersQueryWhereSchema(
                    email=identifier if is_email(identifier) else None,
                    account=identifier if is_account_name(identifier) else None
                ),
                select_fields=select_fields,
            )
            self.logger.info(f"in function:fetch_user_id_and_password_hash_by_email_or_account;res={res}")
        except Exception as e:
            self.logger.error(f"{str(e)}")
            return None

        if res[0]['row_count'] == 0:
            self.logger.warning(f"No user found with identifier: {identifier}")
            return None
        
        row = res[0]['rows'][0]
        
        return row[0], row[1]


    async def fetch_uuid_by_user_id(self, user_id: int) -> str | None:
        """
        通过 user_id 查询用户的 UUID

        :param user_id: 用户ID
        :return: 用户UUID，如果未找到则返回 None
        eg. res in fetch_uuid_by_user_id response: [
            {
                'column_names': ['user_uuid'], 
                'rows': [
                    ['05560daa-934b-4544-9ad8-355a79ea159e']
                ], 
                'row_count': 1, 
                'total_count': None, 
                'page_size': None, 
                'current_page': None
            }
        ]
        """
        try:
            res = await self.query_record_by_schema(
                table='users',
                query_where=TableUsersQueryWhereSchema(user_id=user_id),
                select_fields=['user_uuid'],
            )
        except Exception as e:
            self.logger.error(f"Query failed! Error:{str(e)}")
            return None

        if res is None:
            self.logger.warning(f"No user found with user_id: {user_id}")
            return None
        self.logger.info(f"res in fetch_uuid_by_user_id: {res}")
        return res[0]["rows"][0][0]

    
    async def insert_new_user(self, account: str, email: str, password_hash: str,
                             user_suffix: int, user_name: str) -> Optional[int]:
        """
        插入用户注册信息所有表。
            1. users 表
            2. user_profile 表
            3. user_settings 表
            
        :param: account 用户账号(必须)
        :param: email   用户邮箱(必须)
        :param: password_hash   用户密码hash值(必须)
        :param: user_name   用户名(必须)
        :param: user_suffix 用户名后缀(必须)

        返回 user_id（成功）或 None（失败）
        """
        operator = "Insert New User"
        session_id = None
        try:
            # 生成用户UUID
            user_uuid = str(uuid.uuid4())
            
            # 默认用户文件夹路径
            file_folder_path = f"Users/Files/{user_uuid}/"
            
            # 开启事务
            session_id = await self._start_transaction(connection_id=self.db_connect_id)
            if not session_id:
                self.logger.error("Failed to start dynamic transaction")
                return None

            # 1. 插入 users 表
            # 构建插入数据
            # 使用 TableUsersInsertSchema 来构建插入数据
            users_data = TableUsersInsertSchema(
                account=account,
                email=email,
                password_hash=password_hash,
                user_suffix=user_suffix,
                user_name=user_name,
                user_uuid=user_uuid,
                file_folder_path=file_folder_path
            ).model_dump(exclude_none=True)
            
            insert_users_sql, insert_users_sql_args = self.sql_builder.build_insert_sql(
                table="users",
                data=users_data
            )
            
            user_id = await self._execute_transaction_sql(
                session_id=session_id, 
                sql=insert_users_sql, 
                sql_args=insert_users_sql_args
            )
            
            if not user_id:
                self.logger.error(f"[{operator}] Insert users failed, rolling back.")
                await self._rollback_transaction(session_id)
                return None

            # 2. 插入 user_profile 表（使用默认头像）
            # 构建插入数据
            profile_data = TableUserProfileInsertSchema(user_id=user_id).model_dump(exclude_none=True)
            insert_profile_sql, insert_profile_sql_args = self.sql_builder.build_insert_sql(
                table="user_profile",
                data=profile_data
            )

            insert_profile_res = await self._execute_transaction_sql(
                session_id=session_id,
                sql=insert_profile_sql,
                sql_args=insert_profile_sql_args
            )
            self.logger.info(f"[{operator}] Insert profile res: {insert_profile_res}")
            
            if insert_profile_res is None:
                self.logger.error(f"[{operator}] Insert profile failed, rolling back.")
                await self._rollback_transaction(session_id)
                return None
            
            # 3. 插入 user_settings 表 (使用默认配置)
            # 构建插入数据
            user_setting_data = TableUserSettingsInsertSchema(
                    user_id=user_id,
                    configure={},
                    notification_setting={}
                ).model_dump(exclude_none=True)
            
            insert_settings_sql, insert_settings_sql_args = self.sql_builder.build_insert_sql(
                table="user_settings",
                data=user_setting_data
            )

            insert_settings_res = await self._execute_transaction_sql(
                session_id=session_id,
                sql=insert_settings_sql,
                sql_args=insert_settings_sql_args
            )
            if insert_settings_res is None:
                self.logger.error(f"[{operator}] Insert settings failed, rolling back.")
                await self._rollback_transaction(session_id)
                return None

            commit_res = await self._commit_transaction(session_id)
            if not commit_res:
                self.logger.error(f"[{operator}] Commit failed.")
                return None

            self.logger.info(f"[{operator}] User inserted successfully. user_id={user_id}")
            return user_id
    
        except Exception as e:
            self.logger.error(f"[{operator}] Exception occurred: {e}")
            try:
                if session_id:
                    await self._rollback_transaction(session_id)
            except Exception as rollback_err:
                self.logger.error(f"[{operator}] Rollback failed: {rollback_err}")
            return None
        
        
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
        success = await self.update_users(
            update_data=TableUsersUpdateSetSchema(password_hash=new_password_hash),
            update_where=TableUsersUpdateWhereSchema(user_id=user_id)
        )
        if not success:
            self.logger.warning(f"用户密码更新可能失败，user_id={user_id}")
            return False

        # 2. 插入到 user_account_actions 表
        insert_success = await self.insert_user_account_actions(
            insert_data=TableUserAccountActionsInsertSchema(
                user_id=user_id,
                action_type=UserAccountActionType.password_update,
                action_detail=f"用户密码已更新，user_id={user_id}",
            )
        )
        if not insert_success:
            self.logger.error(f"用户密码已更新,但用户行为记录插入失败，user_id={user_id}")

        self.logger.info(f"用户密码更新完成，user_id={user_id}")
        return True
