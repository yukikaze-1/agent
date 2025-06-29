# Project:      Agent
# Author:       yomu
# Time:         2025/6/28
# Version:      0.1
# Description:  Database agent for the user_profile table.

from typing import Any, Dict, List, Optional
from logging import Logger

from Service.UserService.app.db.BaseDBAgent import BaseDBAgent
from Service.UserService.app.models.UserAccountDatabaseSQLParameterSchema import (
    TableUserProfileUpdateSetSchema,
    TableUserProfileUpdateWhereSchema
)
from Module.Utils.Logger import setup_logger

class UserProfileDBAgent(BaseDBAgent):
    """
    数据库代理类，专门用于处理 `user_profile` 表的相关操作。
    """
    def __init__(self, logger: Optional[Logger] = None):
        """
        初始化 UserProfileDBAgent。

        :param logger: 日志记录器实例。
        """
        super().__init__(
            agent_name="UserProfileDBAgent",
            logger=logger
        )
        self.table_name = "user_profile"

    async def fetch_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        根据 user_id 获取用户个人信息。

        :param user_id: 用户ID。
        :return: 包含用户个人信息的字典，如果未找到则返回 None。
        """
        res = await self.query_record(
            table=self.table_name,
            where_conditions=["user_id = %s"],
            where_values=[user_id]
        )
        if res and res.get("rows"):
            columns = res.get("columns", [])
            rows = res.get("rows", [])
            if columns and rows:
                return dict(zip(columns, rows[0]))
        return None

    async def update_user_profile(self, update_data: TableUserProfileUpdateSetSchema, update_where: TableUserProfileUpdateWhereSchema) -> bool:
        """
        更新用户个人信息。

        :param update_data: 包含要更新的字段和值的 Pydantic 模型。
        :param update_where: 包含更新条件的 Pydantic 模型。
        :return: 如果更新成功，返回 True；否则返回 False。
        """
        return await self.update_record(
            table=self.table_name,
            update_data=update_data,
            update_where=update_where,
            success_msg=f"成功更新用户 {update_where.user_id} 的个人信息。",
            warning_msg=f"尝试更新用户 {update_where.user_id} 的个人信息，但未找到该用户。",
            error_msg=f"更新用户 {update_where.user_id} 的个人信息失败。"
        )
