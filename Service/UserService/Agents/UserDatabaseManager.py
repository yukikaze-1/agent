# Project:      Agent
# Author:       yomu
# Time:         2025/6/29
# Version:      0.1
# Description:  Unified manager for all user database agents.

import uuid
from typing import Optional, Dict, Any
from logging import Logger

from .BaseDBAgent import BaseDBAgent
from .UserCoreDBAgent import UserCoreDBAgent
from .UserProfileDBAgent import UserProfileDBAgent
from .UserSettingsDBAgent import UserSettingsDBAgent
from .UserLoginLogsDBAgent import UserLoginLogsDBAgent
from .UserAccountActionsDBAgent import UserAccountActionsDBAgent
from .UserNotificationsDBAgent import UserNotificationsDBAgent
from .UserFilesDBAgent import UserFilesDBAgent

from ..UserAccountDatabaseSQLParameterSchema import (
    TableUsersInsertSchema,
    TableUserProfileInsertSchema,
    TableUserSettingsInsertSchema,
    UserStatus
)
from Module.Utils.Logger import setup_logger

class UserDatabaseManager:
    """
    用户数据库管理器，统一管理所有用户相关的数据库操作代理。
    """
    
    def __init__(self, logger: Optional[Logger] = None):
        """
        初始化用户数据库管理器。
        
        :param logger: 日志记录器实例。
        """
        self.logger = logger or setup_logger(name="UserDatabaseManager", log_path="InternalModule")
        
        # 初始化所有代理
        self.user_core_agent = UserCoreDBAgent(logger=self.logger)
        self.user_profile_agent = UserProfileDBAgent(logger=self.logger)
        self.user_settings_agent = UserSettingsDBAgent(logger=self.logger)
        self.user_login_logs_agent = UserLoginLogsDBAgent(logger=self.logger)
        self.user_account_actions_agent = UserAccountActionsDBAgent(logger=self.logger)
        self.user_notifications_agent = UserNotificationsDBAgent(logger=self.logger)
        self.user_files_agent = UserFilesDBAgent(logger=self.logger)
        
        # 所有代理的列表
        self.agents = [
            self.user_core_agent,
            self.user_profile_agent,
            self.user_settings_agent,
            self.user_login_logs_agent,
            self.user_account_actions_agent,
            self.user_notifications_agent,
            self.user_files_agent
        ]
        
        self.is_initialized = False

    async def init_all_connections(self) -> bool:
        """
        初始化所有代理的数据库连接。
        
        :return: 如果所有连接初始化成功返回 True，否则返回 False。
        """
        try:
            # 使用第一个代理建立连接
            await self.user_core_agent.init_connection()
            db_connect_id = self.user_core_agent.db_connect_id
            
            if db_connect_id < 0:
                self.logger.error("Failed to establish database connection")
                return False
            
            # 将连接ID分享给所有代理
            for agent in self.agents:
                agent.db_connect_id = db_connect_id
                agent.sql_executor.db_connect_id = db_connect_id
            
            self.is_initialized = True
            self.logger.info("All database agents initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database connections: {e}")
            return False

    async def insert_new_user(self, account: str, email: str, password_hash: str,
                             user_name: str) -> Optional[int]:
        """
        事务性地插入新用户信息到所有相关表。
        
        :param account: 用户账号
        :param email: 用户邮箱
        :param password_hash: 用户密码哈希
        :param user_name: 用户名
        :return: 成功返回用户ID，失败返回None
        """
        if not self.is_initialized:
            self.logger.error("Database connections not initialized")
            return None
            
        operator = "Insert New User"
        session_id = None
        
        try:
            # 生成用户UUID
            user_uuid = str(uuid.uuid4())
            
            # 生成用户后缀 - 这里需要实现逻辑来获取同名用户的下一个可用后缀
            user_suffix = await self._get_next_user_suffix(user_name)
            
            # 默认用户文件夹路径
            file_folder_path = f"Users/Files/{user_uuid}/"
            
            # 开启事务
            session_id = await self.user_core_agent._start_transaction(
                connection_id=self.user_core_agent.db_connect_id
            )
            if not session_id:
                self.logger.error("Failed to start dynamic transaction")
                return None

            # 1. 插入 users 表
            users_data = TableUsersInsertSchema(
                account=account,
                email=email,
                password_hash=password_hash,
                user_suffix=user_suffix,
                user_name=user_name,
                user_uuid=user_uuid,
                file_folder_path=file_folder_path,
                status=UserStatus.inactive  # 显式设置默认状态
            ).model_dump(exclude_none=True)
            
            insert_users_sql, insert_users_sql_args = self.user_core_agent.sql_builder.build_insert_sql(
                table="users",
                data=users_data
            )
            
            user_id = await self.user_core_agent._execute_transaction_sql(
                session_id=session_id, 
                sql=insert_users_sql, 
                sql_args=insert_users_sql_args
            )
            
            if not user_id:
                self.logger.error(f"[{operator}] Insert users failed, rolling back.")
                await self.user_core_agent._rollback_transaction(session_id)
                return None

            # 2. 插入 user_profile 表
            profile_data = TableUserProfileInsertSchema(user_id=user_id).model_dump(exclude_none=True)
            insert_profile_sql, insert_profile_sql_args = self.user_profile_agent.sql_builder.build_insert_sql(
                table="user_profile",
                data=profile_data
            )

            insert_profile_res = await self.user_core_agent._execute_transaction_sql(
                session_id=session_id,
                sql=insert_profile_sql,
                sql_args=insert_profile_sql_args
            )
            
            if insert_profile_res is None:
                self.logger.error(f"[{operator}] Insert profile failed, rolling back.")
                await self.user_core_agent._rollback_transaction(session_id)
                return None
            
            # 3. 插入 user_settings 表
            user_setting_data = TableUserSettingsInsertSchema(
                user_id=user_id,
                configure={},
                notification_setting={}
            ).model_dump(exclude_none=True)
            
            insert_settings_sql, insert_settings_sql_args = self.user_settings_agent.sql_builder.build_insert_sql(
                table="user_settings",
                data=user_setting_data
            )

            insert_settings_res = await self.user_core_agent._execute_transaction_sql(
                session_id=session_id,
                sql=insert_settings_sql,
                sql_args=insert_settings_sql_args
            )
            if insert_settings_res is None:
                self.logger.error(f"[{operator}] Insert settings failed, rolling back.")
                await self.user_core_agent._rollback_transaction(session_id)
                return None

            # 提交事务
            commit_res = await self.user_core_agent._commit_transaction(session_id)
            if not commit_res:
                self.logger.error(f"[{operator}] Commit failed.")
                return None

            self.logger.info(f"[{operator}] User inserted successfully. user_id={user_id}")
            return user_id
    
        except Exception as e:
            self.logger.error(f"[{operator}] Exception occurred: {e}")
            try:
                if session_id:
                    await self.user_core_agent._rollback_transaction(session_id)
            except Exception as rollback_err:
                self.logger.error(f"[{operator}] Rollback failed: {rollback_err}")
            return None

    async def _get_next_user_suffix(self, user_name: str) -> int:
        """
        获取指定用户名的下一个可用后缀。
        
        :param user_name: 用户名
        :return: 下一个可用的后缀数字
        """
        try:
            # 查询数据库中同名用户的最大后缀
            # 这里使用原生SQL查询，因为需要获取MAX值
            from Service.UserService.UserAccountDatabaseSQLParameterSchema import TableUsersQueryWhereSchema
            
            # 查询同名用户的最大user_suffix
            res = await self.user_core_agent.query_record(
                table="users",
                fields=["MAX(user_suffix) as max_suffix"],
                where_conditions=["user_name = %s"],
                where_values=[user_name]
            )
            
            if res and res.get("rows") and res["rows"][0][0] is not None:
                max_suffix = res["rows"][0][0]
                return max_suffix + 1
            else:
                # 如果没有同名用户，从1开始
                return 1
                
        except Exception as e:
            self.logger.error(f"Failed to get next user suffix for {user_name}: {e}")
            # 如果查询失败，返回一个随机数作为后缀
            import random
            return random.randint(1000, 9999)

    # 代理方法 - 将调用转发给相应的专门代理
    
    # UserCoreDBAgent 方法
    async def fetch_user_id_by_uuid(self, user_uuid: str) -> Optional[int]:
        return await self.user_core_agent.fetch_user_id_by_uuid(user_uuid)
    
    async def fetch_user_id_and_password_hash_by_email_or_account(self, identifier: str):
        return await self.user_core_agent.fetch_user_id_and_password_hash_by_email_or_account(identifier)
    
    async def fetch_uuid_by_user_id(self, user_id: int) -> Optional[str]:
        return await self.user_core_agent.fetch_uuid_by_user_id(user_id)
    
    async def update_user_password_by_user_id(self, user_id: int, new_password_hash: str) -> bool:
        return await self.user_core_agent.update_user_password_by_user_id(user_id, new_password_hash)
    
    # UserProfileDBAgent 方法
    async def fetch_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        return await self.user_profile_agent.fetch_user_profile(user_id)
    
    # UserSettingsDBAgent 方法
    async def fetch_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        return await self.user_settings_agent.fetch_user_settings(user_id)
    
    # UserFilesDBAgent 方法
    async def insert_user_file(self, file_data: Dict[str, Any]) -> Optional[int]:
        """
        插入用户文件记录。
        
        :param file_data: 包含文件信息的字典
        :return: 文件ID，如果失败返回None
        """
        from ..UserAccountDatabaseSQLParameterSchema import TableUserFilesInsertSchema
        try:
            # 将字典转换为 Pydantic 模型
            file_schema = TableUserFilesInsertSchema(**file_data)
            return await self.user_files_agent.insert_file(file_schema)
        except Exception as e:
            self.logger.error(f"Failed to insert user file: {e}")
            return None
    
    async def fetch_user_files(self, user_id: int, limit: int = 50, offset: int = 0):
        return await self.user_files_agent.fetch_user_files(user_id, limit, offset)

    # 清理方法
    async def cleanup(self):
        """
        清理所有代理的资源。
        """
        for agent in self.agents:
            if hasattr(agent, 'client') and agent.client:
                await agent.client.aclose()
        self.logger.info("All database agents cleaned up")
        
