# Project:      Agent
# Author:       yomu
# Time:         2025/6/21
# Version:      0.1
# Description:  MySQLAgent Request Type Definitions


"""
    各种MySQLAgent请求的格式定义
"""

from typing import Dict, List, Any
from pydantic import BaseModel, EmailStr, constr, Field, model_validator


class MySQLAgentSQLRequest(BaseModel):
    """ SQL请求格式 """
    connection_id: int = Field(..., description="数据库请求ID")
    sql: str = Field(..., description="SQL语句")
    sql_args: List[Any] = Field(..., description="SQL语句参数")


class MySQLAgentConnectRequest(BaseModel):
    """ 连接数据库请求格式 """
    host: str = Field(..., description="数据库主机名")
    port: int = Field(..., description="数据库端口")
    user: str = Field(..., description="数据库用户名")
    password: str = Field(..., description="数据库密码")
    database: str = Field(..., description="数据库名称")
    charset: str = Field(..., description="数据库字符集")


class MySQLAgentTransactionRequest(BaseModel):
    """ 事务请求格式 """
    connection_id: int = Field(..., description="数据库连接ID")
    sql_requests: List[MySQLAgentSQLRequest] = Field(..., description="一组SQL请求")