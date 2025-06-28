# Project:      Agent
# Author:       yomu
# Time:         2025/6/28
# Version:      0.1
# Description:  Manages database transactions involving multiple user-related tables.

from typing import Any, Dict, Optional
import httpx

from .BaseDBAgent import BaseDBAgent
from .UserCoreDBAgent import UserCoreDBAgent
from .UserProfileDBAgent import UserProfileDBAgent
from .UserSettingsDBAgent import UserSettingsDBAgent
from ..UserAccountDatabaseSQLParameterSchema import (
    TableUsersInsertSchema,
    TableUserProfileInsertSchema,
    TableUserSettingsInsertSchema
)
from Module.Utils.Logger import setup_logger

class UserTransactionManager(BaseDBAgent):
    """
    管理涉及多个用户相关表的数据库事务。
    """
    def __init__(self,
                 db_config: Optional[Dict[str, Any]] = None,
                 db_connection_url: Optional[str] = None,
                 db_connection_id: Optional[str] = None,
                 logger: Optional[Any] = None,
                 client: Optional[httpx.AsyncClient] = None):
        """
        初始化 UserTransactionManager。

        :param db_config: 数据库配置字典。
        :param db_connection_url: 数据库连接微服务的URL。
        :param db_connection_id: 数据库连接ID。
        :param logger: 日志记录器实例。
        :param client: httpx.AsyncClient 实例。
        """
        super().__init__(
            agent_name="UserTransactionManager",
            logger=logger or setup_logger(name="UserTransactionManager", log_path="InternalModule"),
        )
        self.user_core_agent = UserCoreDBAgent(logger=logger)
        self.user_profile_agent = UserProfileDBAgent(logger=logger)
        self.user_settings_agent = UserSettingsDBAgent(logger=logger)

    async def insert_new_user(self, user_data: Dict[str, Any]) -> Optional[int]:
        """
        以事务方式插入一个新用户及其相关信息。

        :param user_data: 包含新用户信息（users, user_profile, user_settings）的字典。
        :return: 如果成功，返回新用户的 user_id；否则返回 None。
        """
        try:
            # 开始事务
            session_id = await self._start_transaction(connection_id=self.user_core_agent.db_connect_id)
            if not session_id:
                self.logger.error("Failed to start transaction")
                return None

            # 1. Insert into users table
            user_core_data = TableUsersInsertSchema(**user_data['users'])
            users_data = user_core_data.model_dump(exclude_none=True)
            
            insert_users_sql, insert_users_sql_args = self.user_core_agent.sql_builder.build_insert_sql(
                table="users",
                data=users_data
            )
            
            user_id = await self._execute_transaction_sql(
                session_id=session_id,
                sql=insert_users_sql,
                sql_args=insert_users_sql_args
            )
            
            if not user_id:
                await self._rollback_transaction(session_id)
                return None

            # 2. Insert into user_profile table
            user_profile_data = TableUserProfileInsertSchema(user_id=user_id, **user_data.get('user_profile', {}))
            profile_data = user_profile_data.model_dump(exclude_none=True)
            
            insert_profile_sql, insert_profile_sql_args = self.user_profile_agent.sql_builder.build_insert_sql(
                table="user_profile",
                data=profile_data
            )
            
            profile_result = await self._execute_transaction_sql(
                session_id=session_id,
                sql=insert_profile_sql,
                sql_args=insert_profile_sql_args
            )
            
            if profile_result is None:
                await self._rollback_transaction(session_id)
                return None

            # 3. Insert into user_settings table
            user_settings_data = TableUserSettingsInsertSchema(user_id=user_id, **user_data.get('user_settings', {}))
            settings_data = user_settings_data.model_dump(exclude_none=True)
            
            insert_settings_sql, insert_settings_sql_args = self.user_settings_agent.sql_builder.build_insert_sql(
                table="user_settings",
                data=settings_data
            )
            
            settings_result = await self._execute_transaction_sql(
                session_id=session_id,
                sql=insert_settings_sql,
                sql_args=insert_settings_sql_args
            )
            
            if settings_result is None:
                await self._rollback_transaction(session_id)
                return None

            # 提交事务
            commit_success = await self._commit_transaction(session_id)
            if not commit_success:
                self.logger.error("Failed to commit transaction")
                return None

            self.logger.info(f"Successfully inserted new user with user_id: {user_id}")
            return user_id

        except Exception as e:
            self.logger.error(f"Error during new user insertion transaction: {e}")
            try:
                if 'session_id' in locals() and session_id:
                    await self._rollback_transaction(session_id)
            except Exception as rollback_err:
                self.logger.error(f"Rollback failed: {rollback_err}")
            return None

    async def insert_user_file(self, user_id: int, file_data: Dict[str, Any]) -> Optional[int]:
        """
        Inserts a file record for a user.

        :param user_id: The ID of the user uploading the file.
        :param file_data: A dictionary containing the file's metadata.
        :return: The ID of the new file record, or None on failure.
        """
        try:
            from ..UserAccountDatabaseSQLParameterSchema import TableUserFilesInsertSchema

            insert_schema = TableUserFilesInsertSchema(user_id=user_id, **file_data)
            
            file_id = await self.insert_record(
                table="user_files",
                insert_data=insert_schema,
                success_msg="Successfully inserted file record",
                warning_msg="File record inserted but no ID returned",
                error_msg="Failed to insert file record"
            )
            
            if file_id and file_id > 0:
                self.logger.info(f"Successfully inserted file record for user_id: {user_id}, file_id: {file_id}")
                return file_id
            else:
                self.logger.warning(f"Failed to insert file record for user_id: {user_id}")
                return None

        except ImportError:
            self.logger.error("Could not import TableUserFilesInsertSchema. Make sure it is defined in UserAccountDatabaseSQLParameterSchema.py")
            return None
        except Exception as e:
            self.logger.error(f"Error inserting user file record: {e}")
            return None
