# Project:      Agent
# Author:       yomu
# Time:         2025/6/28
# Version:      0.1
# Description:  Database agent for the user_login_logs table.

from typing import Any, Dict, List, Optional
import httpx

from Service.UserService.app.db.BaseDBAgent import BaseDBAgent
from Service.UserService.app.models.UserAccountDatabaseSQLParameterSchema import (
    TableUserLoginLogsInsertSchema
)
from Module.Utils.Logger import setup_logger

class UserLoginLogsDBAgent(BaseDBAgent):
    """
    数据库代理类，专门用于处理 `user_login_logs` 表的相关操作。
    """
    def __init__(self,
                 db_config: Optional[Dict[str, Any]] = None,
                 db_connection_url: Optional[str] = None,
                 db_connection_id: Optional[str] = None,
                 logger: Optional[Any] = None,
                 client: Optional[httpx.AsyncClient] = None):
        """
        初始化 UserLoginLogsDBAgent。

        :param db_config: 数据库配置字典。
        :param db_connection_url: 数据库连接微服务的URL。
        :param db_connection_id: 数据库连接ID。
        :param logger: 日志记录器实例。
        :param client: httpx.AsyncClient 实例。
        """
        super().__init__(
            agent_name="UserLoginLogsDBAgent",
            logger=logger or setup_logger(name="UserLoginLogsDBAgent", log_path="InternalModule"),
        )
        self.table_name = "user_login_logs"

    async def insert_login_log(self, log_data: TableUserLoginLogsInsertSchema) -> bool:
        """
        插入一条新的登录日志。

        :param log_data: 包含登录日志信息的 Pydantic 模型。
        :return: 如果插入成功，返回 True；否则返回 False。
        """
        res =  await self.insert_record(
            table=self.table_name,
            insert_data=log_data,
            success_msg="成功插入登录日志。",
            warning_msg="尝试插入登录日志，但未返回新记录。",
            error_msg="插入登录日志失败。"
        )
        if res  == -1:
            self.logger.error("插入登录日志失败，返回 -1。")
            return False
        return True
