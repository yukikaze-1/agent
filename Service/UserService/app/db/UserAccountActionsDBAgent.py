# Project:      Agent
# Author:       yomu
# Time:         2025/6/29
# Version:      0.1
# Description:  Database agent for the user_account_actions table.

from typing import Any, Dict, List, Optional
import httpx

from Service.UserService.app.db.BaseDBAgent import BaseDBAgent
from Service.UserService.app.models.UserAccountDatabaseSQLParameterSchema import (
    TableUserAccountActionsInsertSchema,
    TableUserAccountActionsDeleteWhereSchema,
    TableUserAccountActionsQueryWhereSchema,
    UserAccountActionType
)
from Module.Utils.Logger import setup_logger

class UserAccountActionsDBAgent(BaseDBAgent):
    """
    数据库代理类，专门用于处理 `user_account_actions` 表的相关操作。
    """
    def __init__(self, logger: Optional[Any] = None):
        """
        初始化 UserAccountActionsDBAgent。

        :param logger: 日志记录器实例。
        """
        super().__init__(
            agent_name="UserAccountActionsDBAgent",
            logger=logger or setup_logger(name="UserAccountActionsDBAgent", log_path="InternalModule"),
        )
        self.table_name = "user_account_actions"

    async def insert_account_action(self, action_data: TableUserAccountActionsInsertSchema) -> bool:
        """
        插入一条新的用户账户操作记录。

        :param action_data: 包含操作信息的 Pydantic 模型。
        :return: 如果插入成功，返回 True；否则返回 False。
        """
        res = await self.insert_record(
            table=self.table_name,
            insert_data=action_data,
            success_msg="成功插入用户账户操作记录。",
            warning_msg="尝试插入用户账户操作记录，但未返回新记录。",
            error_msg="插入用户账户操作记录失败。"
        )
        if res == -1:
            self.logger.error("插入用户账户操作记录失败，返回 -1。")
            return False
        return True

    async def fetch_user_actions(self, user_id: int, action_type: Optional[UserAccountActionType] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取用户的操作记录。

        :param user_id: 用户ID。
        :param action_type: 可选的操作类型过滤。
        :param limit: 返回记录的最大数量。
        :return: 包含操作记录的列表。
        """
        where_conditions = ["user_id = %s"]
        where_values: List[Any] = [user_id]
        
        if action_type:
            where_conditions.append("action_type = %s")
            where_values.append(action_type.value if hasattr(action_type, 'value') else str(action_type))
        
        res = await self.query_record(
            table=self.table_name,
            where_conditions=where_conditions,
            where_values=where_values,
            limit=limit,
            order_by="created_at DESC"
        )
        
        if res and res.get("rows"):
            columns = res.get("column_names", [])
            rows = res.get("rows", [])
            return [dict(zip(columns, row)) for row in rows]
        return []

    async def delete_old_actions(self, days: int = 90) -> bool:
        """
        删除超过指定天数的旧操作记录。

        :param days: 保留天数，超过此天数的记录将被删除。
        :return: 如果删除成功，返回 True；否则返回 False。
        """
        where_conditions = ["created_at < (NOW() - INTERVAL %s DAY)"]
        where_values = [days]
        
        deleted_count = await self.delete_record(
            table=self.table_name,
            where_conditions=where_conditions,
            where_values=where_values,
            success_msg=f"成功删除超过{days}天的旧操作记录",
            warning_msg="删除操作完成，但无匹配记录",
            error_msg="删除旧操作记录失败"
        )
        
        if deleted_count >= 0:
            if deleted_count > 0:
                self.logger.info(f"删除了 {deleted_count} 条旧操作记录")
            return True
        else:
            self.logger.error("删除旧操作记录过程出错")
            return False
