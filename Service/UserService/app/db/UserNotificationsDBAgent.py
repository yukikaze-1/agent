# Project:      Agent
# Author:       yomu
# Time:         2025/6/29
# Version:      0.1
# Description:  Database agent for the user_notifications table.

from typing import Any, Dict, List, Optional
import httpx

from Service.UserService.app.db.BaseDBAgent import BaseDBAgent
from Service.UserService.app.models.UserAccountDatabaseSQLParameterSchema import (
    TableUserNotificationsInsertSchema,
    TableUserNotificationsUpdateSetSchema,
    TableUserNotificationsUpdateWhereSchema,
    TableUserNotificationsDeleteWhereSchema,
    TableUserNotificationsQueryWhereSchema,
    UserNotificationType
)
from Module.Utils.Logger import setup_logger

class UserNotificationsDBAgent(BaseDBAgent):
    """
    数据库代理类，专门用于处理 `user_notifications` 表的相关操作。
    """
    def __init__(self, logger: Optional[Any] = None):
        """
        初始化 UserNotificationsDBAgent。

        :param logger: 日志记录器实例。
        """
        super().__init__(
            agent_name="UserNotificationsDBAgent",
            logger=logger or setup_logger(name="UserNotificationsDBAgent", log_path="InternalModule"),
        )
        self.table_name = "user_notifications"

    async def insert_notification(self, notification_data: TableUserNotificationsInsertSchema) -> bool:
        """
        插入一条新的用户通知。

        :param notification_data: 包含通知信息的 Pydantic 模型。
        :return: 如果插入成功，返回 True；否则返回 False。
        """
        res = await self.insert_record(
            table=self.table_name,
            insert_data=notification_data,
            success_msg="成功插入用户通知。",
            warning_msg="尝试插入用户通知，但未返回新记录。",
            error_msg="插入用户通知失败。"
        )
        if res == -1:
            self.logger.error("插入用户通知失败，返回 -1。")
            return False
        return True

    async def fetch_user_notifications(self, user_id: int, is_read: Optional[bool] = None, 
                                     notification_type: Optional[UserNotificationType] = None, 
                                     limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取用户的通知列表。

        :param user_id: 用户ID。
        :param is_read: 可选的已读状态过滤。
        :param notification_type: 可选的通知类型过滤。
        :param limit: 返回记录的最大数量。
        :return: 包含通知记录的列表。
        """
        where_conditions = ["user_id = %s"]
        where_values: List[Any] = [user_id]
        
        if is_read is not None:
            where_conditions.append("is_read = %s")
            where_values.append(is_read)
            
        if notification_type:
            where_conditions.append("notification_type = %s")
            where_values.append(notification_type.value if hasattr(notification_type, 'value') else str(notification_type))
        
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

    async def mark_notification_as_read(self, notification_id: int) -> bool:
        """
        将指定通知标记为已读。

        :param notification_id: 通知ID。
        :return: 如果更新成功，返回 True；否则返回 False。
        """
        return await self.update_record(
            table=self.table_name,
            update_data=TableUserNotificationsUpdateSetSchema(is_read=True),
            update_where=TableUserNotificationsUpdateWhereSchema(notification_id=notification_id),
            success_msg=f"成功将通知 {notification_id} 标记为已读",
            warning_msg=f"尝试标记通知 {notification_id} 为已读，但未找到匹配项",
            error_msg=f"标记通知 {notification_id} 为已读失败"
        )

    async def mark_all_notifications_as_read(self, user_id: int) -> bool:
        """
        将用户的所有通知标记为已读。

        :param user_id: 用户ID。
        :return: 如果更新成功，返回 True；否则返回 False。
        """
        return await self.update_record(
            table=self.table_name,
            update_data=TableUserNotificationsUpdateSetSchema(is_read=True),
            update_where=TableUserNotificationsUpdateWhereSchema(user_id=user_id, is_read=False),
            success_msg=f"成功将用户 {user_id} 的所有通知标记为已读",
            warning_msg=f"用户 {user_id} 没有未读通知",
            error_msg=f"标记用户 {user_id} 的通知为已读失败"
        )

    async def delete_old_notifications(self, days: int = 30) -> bool:
        """
        删除超过指定天数的旧通知。

        :param days: 保留天数，超过此天数的通知将被删除。
        :return: 如果删除成功，返回 True；否则返回 False。
        """
        where_conditions = ["created_at < (NOW() - INTERVAL %s DAY)"]
        where_values = [days]
        
        deleted_count = await self.delete_record(
            table=self.table_name,
            where_conditions=where_conditions,
            where_values=where_values,
            success_msg=f"成功删除超过{days}天的旧通知",
            warning_msg="删除操作完成，但无匹配通知",
            error_msg="删除旧通知失败"
        )
        
        if deleted_count >= 0:
            if deleted_count > 0:
                self.logger.info(f"删除了 {deleted_count} 条旧通知")
            return True
        else:
            self.logger.error("删除旧通知过程出错")
            return False

    async def get_unread_count(self, user_id: int) -> int:
        """
        获取用户的未读通知数量。

        :param user_id: 用户ID。
        :return: 未读通知数量。
        """
        res = await self.query_record(
            table=self.table_name,
            where_conditions=["user_id = %s", "is_read = %s"],
            where_values=[user_id, False],
            fields=["COUNT(*) as unread_count"]
        )
        
        if res and res.get("rows"):
            return res["rows"][0][0]
        return 0
