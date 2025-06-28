# Project:      Agent
# Author:       yomu
# Time:         2025/6/29
# Version:      0.1
# Description:  Database agent for the user_files table.

from typing import Any, Dict, List, Optional
import httpx

from .BaseDBAgent import BaseDBAgent
from ..UserAccountDatabaseSQLParameterSchema import (
    TableUserFilesInsertSchema,
    TableUserFilesUpdateSetSchema,
    TableUserFilesUpdateWhereSchema,
    TableUserFilesDeleteWhereSchema,
    TableUserFilesQueryWhereSchema
)
from Module.Utils.Logger import setup_logger

class UserFilesDBAgent(BaseDBAgent):
    """
    数据库代理类，专门用于处理 `user_files` 表的相关操作。
    """
    def __init__(self, logger: Optional[Any] = None):
        """
        初始化 UserFilesDBAgent。

        :param logger: 日志记录器实例。
        """
        super().__init__(
            agent_name="UserFilesDBAgent",
            logger=logger or setup_logger(name="UserFilesDBAgent", log_path="InternalModule"),
        )
        self.table_name = "user_files"

    async def insert_file(self, file_data: TableUserFilesInsertSchema) -> Optional[int]:
        """
        插入一条新的用户文件记录。

        :param file_data: 包含文件信息的 Pydantic 模型。
        :return: 如果插入成功，返回文件ID；否则返回 None。
        """
        file_id = await self.insert_record(
            table=self.table_name,
            insert_data=file_data,
            success_msg="成功插入用户文件记录。",
            warning_msg="尝试插入用户文件记录，但未返回新记录。",
            error_msg="插入用户文件记录失败。"
        )
        if file_id <= 0:
            self.logger.error("插入用户文件记录失败，返回 -1。")
            return None
        return file_id

    async def fetch_user_files(self, user_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取用户的文件列表。

        :param user_id: 用户ID。
        :param limit: 返回记录的最大数量。
        :param offset: 偏移量，用于分页。
        :return: 包含文件记录的列表。
        """
        res = await self.query_record(
            table=self.table_name,
            where_conditions=["user_id = %s"],
            where_values=[user_id],
            limit=limit,
            offset=offset,
            order_by="uploaded_at DESC"
        )
        
        if res and res.get("rows"):
            columns = res.get("column_names", [])
            rows = res.get("rows", [])
            return [dict(zip(columns, row)) for row in rows]
        return []

    async def fetch_file_by_id(self, file_id: int) -> Optional[Dict[str, Any]]:
        """
        根据文件ID获取文件信息。

        :param file_id: 文件ID。
        :return: 包含文件信息的字典，如果未找到则返回 None。
        """
        res = await self.query_record(
            table=self.table_name,
            where_conditions=["file_id = %s"],
            where_values=[file_id],
            limit=1
        )
        
        if res and res.get("rows"):
            columns = res.get("column_names", [])
            rows = res.get("rows", [])
            if rows:
                return dict(zip(columns, rows[0]))
        return None

    async def update_file(self, update_data: TableUserFilesUpdateSetSchema, 
                         update_where: TableUserFilesUpdateWhereSchema) -> bool:
        """
        更新用户文件信息。

        :param update_data: 包含要更新的字段和值的 Pydantic 模型。
        :param update_where: 包含更新条件的 Pydantic 模型。
        :return: 如果更新成功，返回 True；否则返回 False。
        """
        return await self.update_record(
            table=self.table_name,
            update_data=update_data,
            update_where=update_where,
            success_msg=f"成功更新文件: {update_where.model_dump(exclude_none=True)}",
            warning_msg=f"尝试更新文件但未找到匹配项: {update_where.model_dump(exclude_none=True)}",
            error_msg=f"更新文件失败: {update_where.model_dump(exclude_none=True)}"
        )

    async def delete_file(self, file_id: int) -> bool:
        """
        删除用户文件记录。

        :param file_id: 文件ID。
        :return: 如果删除成功，返回 True；否则返回 False。
        """
        deleted_count = await self.delete_record(
            table=self.table_name,
            where_conditions=["file_id = %s"],
            where_values=[file_id],
            success_msg=f"成功删除文件 {file_id}",
            warning_msg=f"尝试删除文件 {file_id} 但未找到匹配项",
            error_msg=f"删除文件 {file_id} 失败"
        )
        
        if deleted_count > 0:
            return True
        elif deleted_count == 0:
            self.logger.warning(f"文件 {file_id} 不存在")
            return False
        else:
            self.logger.error(f"删除文件 {file_id} 过程出错")
            return False

    async def delete_user_files(self, user_id: int) -> bool:
        """
        删除用户的所有文件记录。

        :param user_id: 用户ID。
        :return: 如果删除成功，返回 True；否则返回 False。
        """
        deleted_count = await self.delete_record(
            table=self.table_name,
            where_conditions=["user_id = %s"],
            where_values=[user_id],
            success_msg=f"成功删除用户 {user_id} 的所有文件",
            warning_msg=f"用户 {user_id} 没有文件记录",
            error_msg=f"删除用户 {user_id} 的文件失败"
        )
        
        if deleted_count >= 0:
            if deleted_count > 0:
                self.logger.info(f"删除了用户 {user_id} 的 {deleted_count} 个文件记录")
            return True
        else:
            self.logger.error(f"删除用户 {user_id} 文件过程出错")
            return False

    async def get_user_file_count(self, user_id: int) -> int:
        """
        获取用户的文件数量。

        :param user_id: 用户ID。
        :return: 文件数量。
        """
        res = await self.query_record(
            table=self.table_name,
            where_conditions=["user_id = %s"],
            where_values=[user_id],
            fields=["COUNT(*) as file_count"]
        )
        
        if res and res.get("rows"):
            return res["rows"][0][0]
        return 0

    async def get_user_total_file_size(self, user_id: int) -> int:
        """
        获取用户文件的总大小（字节）。

        :param user_id: 用户ID。
        :return: 总文件大小。
        """
        res = await self.query_record(
            table=self.table_name,
            where_conditions=["user_id = %s"],
            where_values=[user_id],
            fields=["COALESCE(SUM(file_size), 0) as total_size"]
        )
        
        if res and res.get("rows"):
            return res["rows"][0][0]
        return 0
