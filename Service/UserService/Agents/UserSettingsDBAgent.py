# Project:      Agent
# Author:       yomu
# Time:         2025/6/28
# Version:      0.1
# Description:  Database agent for the user_settings table.

from typing import Any, Dict, List, Optional
import httpx

from .BaseDBAgent import BaseDBAgent
from ..UserAccountDatabaseSQLParameterSchema import (
    TableUserSettingsUpdateSetSchema,
    TableUserSettingsUpdateWhereSchema
)
from Module.Utils.Logger import setup_logger

class UserSettingsDBAgent(BaseDBAgent):
    """
    数据库代理类，专门用于处理 `user_settings` 表的相关操作。
    """
    def __init__(self,
                 db_config: Optional[Dict[str, Any]] = None,
                 db_connection_url: Optional[str] = None,
                 db_connection_id: Optional[str] = None,
                 logger: Optional[Any] = None,
                 client: Optional[httpx.AsyncClient] = None):
        """
        初始化 UserSettingsDBAgent。

        :param db_config: 数据库配置字典。
        :param db_connection_url: 数据库连接微服务的URL。
        :param db_connection_id: 数据库连接ID。
        :param logger: 日志记录器实例。
        :param client: httpx.AsyncClient 实例。
        """
        super().__init__(
            agent_name="UserSettingsDBAgent",
            logger=logger or setup_logger(name="UserSettingsDBAgent", log_path="InternalModule"),
        )
        self.table_name = "user_settings"

    async def fetch_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        根据用户ID获取用户设置。

        :param user_id: 用户ID。
        :return: 包含用户设置的字典，如果未找到则返回 None。
        """
        where_conditions = ["user_id = %s"]
        where_values = [user_id]
        records = await self.query_record(
            table=self.table_name,
            where_conditions=where_conditions,
            where_values=where_values,
            limit=1
        )
        if records:
            return records[0]
        return None

    async def update_user_settings(self, update_data: TableUserSettingsUpdateSetSchema, update_where: TableUserSettingsUpdateWhereSchema) -> bool:
        """
        更新用户设置。

        :param update_data: 包含要更新的字段和值的 Pydantic 模型。
        :param update_where: 包含更新条件的 Pydantic 模型。
        :return: 如果更新成功，返回 True；否则返回 False。
        """
        return await self.update_record(
            table=self.table_name,
            update_data=update_data,
            update_where=update_where,
            success_msg="成功更新用户设置。",
            warning_msg="尝试更新用户设置，但未找到匹配项。",
            error_msg="更新用户设置失败。"
        )
