# Project:      Agent
# Author:       yomu
# Time:         2025/6/20
# Version:      0.1
# Description:  MySQLAgent Response Type Definitions


"""
    Uservice 各种回复的格式定义
"""

from datetime import datetime
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, EmailStr, constr, Field, model_validator


class MySQLAgentResponseErrorCode(IntEnum):
    """  MySQLAgent Response 的错误代码类 """
    CONNECT_DATABASE_FAILED = 1001

class MySQLAgentErrorDetail(BaseModel):
    """ MySQLAgent详细错误类 """
    

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
    
    
class ConnectDatabaseData(BaseModel):
    """  连接数据库 数据"""    
    connection_id: int = Field(..., description="")
    
class ConnectDatabaseResponse(MySQLAgentBaseResponse):
    """ 连接数据库 Response """
    data: ConnectDatabaseData | None = Field(default=None, description="连接数据库附加数据")
    

class QueryData(BaseModel):
    """ SQL查询 数据 """

class QueryResponse(MySQLAgentBaseResponse):
    """ SQL查询 Response """
    
class InsertData(BaseModel):
    """ SQL插入 数据 """

class InsertResponse(MySQLAgentBaseResponse):
    """ SQL插入 Response """
    
class DeleteData(BaseModel):
    """ SQL删除 数据 """

class DeleteResponse(MySQLAgentBaseResponse):
    """ SQL删除 Response """
    
class UpdateData(BaseModel):
    """ SQL更新 数据 """

class UpdateResponse(MySQLAgentBaseResponse):
    """ SQL更新 Response """