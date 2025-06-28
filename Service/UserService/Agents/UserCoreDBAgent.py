# Project:      Agent
# Author:       yomu
# Time:         2025/06/28
# Version:      0.1
# Description:  Database agent for the 'users' table.

"""
    负责 users 表的数据库操作
"""
from logging import Logger
from typing import Optional, Tuple, Dict, Any

from Service.UserService.Agents.BaseDBAgent import BaseDBAgent
from Module.Utils.FormatValidate import is_email, is_account_name
from Module.Utils.Logger import setup_logger
from Service.UserService.UserAccountDatabaseSQLParameterSchema import (
    TableUsersQueryWhereSchema,
    TableUsersUpdateSetSchema,
    TableUsersUpdateWhereSchema,
    TableUsersDeleteWhereSchema,
    TableUserAccountActionsInsertSchema,
    UserStatus,
    UserAccountActionType
)

class UserCoreDBAgent(BaseDBAgent):
    def __init__(self, logger: Logger | None = None):
        super().__init__(
            agent_name="UserCoreDBAgent",
            logger=logger or setup_logger(name="UserCoreDBAgent", log_path="InternalModule")
        )

    async def fetch_user_id_by_uuid(self, user_uuid: str) -> Optional[int]:
        """
        通过 UUID 在 users 表中查询 user_id
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

        if not res or not res.get("rows"):
            self.logger.warning(f"No user found with UUID: {user_uuid}")
            return None
        return res["rows"][0][0]

    async def fetch_user_id_and_password_hash_by_email_or_account(self, identifier: str) -> Optional[Tuple[int, str]]:
        """
        通过 email 或 account 在 users 表中查询 用户id 和 密码hash
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
        except Exception as e:
            self.logger.error(f"{str(e)}")
            return None

        if not res or res.get('row_count', 0) == 0:
            self.logger.warning(f"No user found with identifier: {identifier}")
            return None
        
        row = res['rows'][0]
        return row[0], row[1]

    async def fetch_uuid_by_user_id(self, user_id: int) -> Optional[str]:
        """
        通过 user_id 查询用户的 UUID
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

        if not res or not res.get("rows"):
            self.logger.warning(f"No user found with user_id: {user_id}")
            return None
        return res["rows"][0][0]

    async def check_user_exists(self, identifier: str) -> bool:
        """
        通过 email 或 account 检查用户是否存在
        """
        if not is_email(identifier) and not is_account_name(identifier):
            self.logger.warning(f"Invalid identifier: {identifier}. Need email or valid account.")
            return False

        try:
            res = await self.query_record_by_schema(
                table='users',
                query_where=TableUsersQueryWhereSchema(
                    email=identifier if is_email(identifier) else None,
                    account=identifier if is_account_name(identifier) else None
                ),
                select_fields=['user_id']
            )
        except Exception as e:
            self.logger.error(f"Query failed! Error:{str(e)}")
            return False

        # query_record_by_schema returns a dict like {'row_count': 1, ...} or {}
        return res.get('row_count', 0) > 0

    async def fetch_user_info_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        通过 user_id 查询用户核心信息 (account, email, user_name)
        """
        try:
            res = await self.query_record_by_schema(
                table='users',
                query_where=TableUsersQueryWhereSchema(user_id=user_id),
                select_fields=['account', 'email', 'user_name']
            )
        except Exception as e:
            self.logger.error(f"Query failed! Error:{str(e)}")
            return None

        if not res or not res.get("rows"):
            self.logger.warning(f"No user found with user_id: {user_id}")
            return None
        
        columns = res.get("columns", [])
        rows = res.get("rows", [])
        if not rows or not columns:
            return None
            
        user_data = dict(zip(columns, rows[0]))
        return user_data

    async def update_users(self, update_data: TableUsersUpdateSetSchema, update_where: TableUsersUpdateWhereSchema) -> bool:
        """
        更新 users 表
        """
        return await self.update_record(
            table="users",
            update_data=update_data,
            update_where=update_where,
            success_msg=f"成功更新用户: {update_where.model_dump(exclude_none=True)}",
            warning_msg=f"尝试更新用户但未找到匹配项: {update_where.model_dump(exclude_none=True)}",
            error_msg=f"更新用户失败: {update_where.model_dump(exclude_none=True)}"
        )

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
        from .UserAccountActionsDBAgent import UserAccountActionsDBAgent
        actions_agent = UserAccountActionsDBAgent(logger=self.logger)
        # 继承当前连接配置
        actions_agent.mysql_service_url = self.mysql_service_url
        actions_agent.db_connect_id = self.db_connect_id
        actions_agent.sql_executor.db_connect_id = self.db_connect_id
        
        insert_success = await actions_agent.insert_account_action(
            action_data=TableUserAccountActionsInsertSchema(
                user_id=user_id,
                action_type=UserAccountActionType.password_update,
                action_detail=f"用户密码已更新，user_id={user_id}",
            )
        )
        if not insert_success:
            self.logger.error(f"用户密码已更新,但用户行为记录插入失败，user_id={user_id}")

        self.logger.info(f"用户密码更新完成，user_id={user_id}")
        return True

    async def delete_users(self, delete_where: TableUsersDeleteWhereSchema) -> bool:
        """
        硬删除 users 表中的记录
        """
        where_conditions, where_values = self.extract_where_from_schema(schema=delete_where)
        rows_affected = await self.delete_record(
            table="users",
            where_conditions=where_conditions,
            where_values=where_values,
            success_msg=f"成功硬删除用户: {delete_where.model_dump(exclude_none=True)}",
            warning_msg=f"尝试硬删除用户但未找到匹配项: {delete_where.model_dump(exclude_none=True)}",
            error_msg=f"硬删除用户失败: {delete_where.model_dump(exclude_none=True)}"
        )
        return rows_affected != -1

    async def hard_delete_user_by_user_id(self, user_id: int) -> bool:
        """
        根据 user_id 硬删除用户
        """
        try:
            success = await self.delete_users(delete_where=TableUsersDeleteWhereSchema(user_id=user_id))
        except Exception as e:
            self.logger.error(f"Failed to hard delete user with user_id: {user_id}. Error: {str(e)}")
            return False
        return success

    async def soft_delete_user_by_user_id(self, user_id: int) -> bool:
        """
        软删除用户：设为 'deleted' 并记录删除时间。
        """
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

    async def hard_delete_expired_users(self, days: int = 30) -> bool:
        """
        物理删除已标记为 deleted 且 deleted_at 超过 days 天的用户。
        """
        table = "users"
        where_conditions = [
            "status = %s",
            "deleted_at < (NOW() - INTERVAL %s DAY)"
        ]
        where_values = ["deleted", days]

        deleted_count = await self.delete_record(
            table=table,
            where_conditions=where_conditions,
            where_values=where_values,
            success_msg="成功删除过期用户",
            warning_msg="删除操作完成，但无匹配用户",
            error_msg="物理删除过期用户失败"
        )

        if deleted_count >= 0:
            if deleted_count > 0:
                self.logger.info(f"物理删除 {deleted_count} 条已过期的用户记录")
            else:
                self.logger.info("无已过期的 deleted 用户可删除")
            return True
        else:
            self.logger.error("物理删除过程出错")
            return False
