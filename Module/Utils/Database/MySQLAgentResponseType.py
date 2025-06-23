# Project:      Agent
# Author:       yomu
# Time:         2025/6/20
# Version:      0.1
# Description:  MySQLAgent Response Type Definitions


"""
   MySQLAgent 各种回复的格式定义
"""

from datetime import datetime
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, EmailStr, constr, Field, model_validator


class MySQLAgentResponseErrorCode(IntEnum):
    """  MySQLAgent Response 的错误代码类 """
    CONNECT_DATABASE_FAILED = 1001  # 连接数据库失败
    CONNECT_ID_NOT_EXISTED = 1002  # 连接ID不存在

    QUERY_DATABASE_FAILED = 2001  # 查询数据库失败
    INSERT_DATABASE_FAILED = 3001  # 插入数据库失败
    DELETE_DATABASE_FAILED = 4001  # 删除数据库失败
    UPDATE_DATABASE_FAILED = 5001  # 更新数据库失败


class MySQLAgentErrorDetail(BaseModel):
    """ MySQLAgent详细错误类 """
    code: MySQLAgentResponseErrorCode = Field(..., description="错误代码")
    message: str = Field(..., description="错误信息")
    field: str | None = Field(default=None, description="出错字段，比如 'email'")
    hint: str | None = Field(default=None, description="帮助提示")


class MySQLAgentBaseResponse(BaseModel):
    """ 基础回复格式 """
    operator: str = Field(..., description="操作")
    result: bool = Field(..., description="操作结果")
    message: str = Field(..., description="提示信息")
    err_code:  MySQLAgentResponseErrorCode | None = Field(default=None, description="错误代码")
    errors: List[MySQLAgentErrorDetail] | None = Field(default=None, description="详细错误列表")
    elapsed_ms: int | None = Field(default=None, description="服务端处理耗时（毫秒）")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应生成时间")
    level: str | None = Field(default=None, description="提示等级: info / warning / error")
    
    
    
class MySQLAgentConnectDatabaseResponseData(BaseModel):
    """  连接数据库 数据"""    
    connection_id: int = Field(..., description="")
    
class MySQLAgentConnectDatabaseResponse(MySQLAgentBaseResponse):
    """ 连接数据库 Response """
    data: MySQLAgentConnectDatabaseResponseData | None = Field(default=None, description="连接数据库附加数据")



class MySQLAgentQueryResponseData(BaseModel):
    """ SQL查询 数据 """
    column_names: List[str] = Field(..., description="查询结果列名列表")
    rows: List[List[Any]] = Field(..., description="查询结果数据行列表，每行是一个列表")
    row_count: int = Field(..., description="查询结果行数")
    total_count: int | None = Field(default=None, description="总记录数（如果适用）")
    page_size: int | None = Field(default=None, description="每页记录数（如果适用）")
    current_page: int | None = Field(default=None, description="当前页码（如果适用）")

class MySQLAgentQueryResponse(MySQLAgentBaseResponse):
    """ SQL查询 Response """
    data : List[MySQLAgentQueryResponseData] | None = Field(default=None, description="查询结果数据列表")



class MySQLAgentInsertResponseData(BaseModel):
    """ SQL插入操作 Response 附加数据 """
    affect_rows: int = Field(..., description="插入的记录数")
    last_insert_id: int | None = Field(default=None, description="自增主键 ID（如果有）")

class MySQLAgentInsertResponse(MySQLAgentBaseResponse):
    """ SQL插入 Response """
    data: MySQLAgentInsertResponseData | None = Field(default=None, description="插入数据附加信息")
    
    
    
class MySQLAgentDeleteResponseData(BaseModel):
    """ SQL删除 数据 """
    rows_affected: int = Field(..., description="删除的记录数")

class MySQLAgentDeleteResponse(MySQLAgentBaseResponse):
    """ SQL删除 Response """
    data: MySQLAgentDeleteResponseData = Field(..., description="删除数据附加信息")
    
    
    
class MySQLAgentUpdateResponseData(BaseModel):
    """ SQL更新 数据 """
    affect_rows: int = Field(..., description="更新的记录数")

class MySQLAgentUpdateResponse(MySQLAgentBaseResponse):
    """ SQL更新 Response """
    data: MySQLAgentUpdateResponseData | None = Field(default=None, description="更新数据附加信息")
    
    
    
class MySQLAgentTransactionResponseData(BaseModel):
    """ 事务 数据 """
    pass
    
class MySQLAgentTransactionResponse(MySQLAgentBaseResponse):
    """ 事务 Response """
    data: List[MySQLAgentBaseResponse] | None = Field(default=None, description="事务中每个操作的响应列表")