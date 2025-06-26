# Project:      Agent
# Author:       yomu
# Time:         2025/6/20
# Version:      0.1
# Description:  MySQLService Response Type Definitions


"""
   MySQLService 各种响应的格式定义
"""

from datetime import datetime
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, EmailStr, constr, Field, model_validator

class StrictBaseModel(BaseModel):
    """
    基础模型，所有模型都直接或间接继承自此类
    """
    class Config:
        extra = "forbid"  # 禁止额外字段
        anystr_strip_whitespace = True  # 去除字符串两端空格
        use_enum_values = True  # 使用枚举值而不是枚举对象
        

class MySQLServiceResponseErrorCode(IntEnum):
    """  MySQLService Response 的错误代码类 """
    CONNECT_DATABASE_FAILED = 1001  # 连接数据库失败
    CONNECTION_ID_NOT_EXISTS = 1002  # 连接ID不存在

    QUERY_DATABASE_FAILED = 2001  # 查询数据库失败
    INSERT_DATABASE_FAILED = 3001  # 插入数据库失败
    DELETE_DATABASE_FAILED = 4001  # 删除数据库失败
    UPDATE_DATABASE_FAILED = 5001  # 更新数据库失败
    
    TRANSACTION_FAILED = 6001  # 事务执行失败


class MySQLServiceErrorDetail(StrictBaseModel):
    """ MySQLService详细错误类 """
    code: MySQLServiceResponseErrorCode = Field(..., description="错误代码")
    message: str = Field(..., description="错误信息")
    field: str | None = Field(default=None, description="出错字段，比如 'email'")
    sql: List[str] | None= Field(default=None, description="出错的SQL语句")
    hint: str | None = Field(default=None, description="帮助提示")


class MySQLServiceBaseResponse(StrictBaseModel):
    """ 基础响应格式 所有 MySQLService响应都继承自此类 """
    operator: str = Field(..., description="操作")
    result: bool = Field(..., description="操作结果")
    message: str = Field(..., description="提示信息")
    err_code:  MySQLServiceResponseErrorCode | None = Field(default=None, description="错误代码")
    errors: List[MySQLServiceErrorDetail] | None = Field(default=None, description="详细错误列表")
    elapsed_ms: int | None = Field(default=None, description="服务端处理耗时（毫秒）")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应生成时间")
    level: str | None = Field(default=None, description="提示等级: info / warning / error")
    
# ------------------------------------------------------------------------------------------------
# 数据库连接响应
# ------------------------------------------------------------------------------------------------


class MySQLServiceConnectDatabaseResponseData(StrictBaseModel):
    """  
    连接数据库 附加数据 
    如果connection_id == -1 则表示连接失败
    """    
    connection_id: int = Field(..., description="数据库连接ID")
    
    
class MySQLServiceConnectDatabaseResponse(MySQLServiceBaseResponse):
    """ 连接数据库 Response """
    data: MySQLServiceConnectDatabaseResponseData = Field(..., description="连接数据库附加数据")
    
    

# ------------------------------------------------------------------------------------------------
# 单条CURD响应
# ------------------------------------------------------------------------------------------------ 

class MySQLServiceQueryResponseData(StrictBaseModel):
    """ SQL查询 数据 """
    column_names: List[str] = Field(..., description="查询结果列名列表")
    rows: List[List[Any]] = Field(..., description="查询结果数据行列表，每行是一个列表")
    row_count: int = Field(..., description="查询结果行数")
    total_count: int | None = Field(default=None, description="总记录数（如果适用）")
    page_size: int | None = Field(default=None, description="每页记录数（如果适用）")
    current_page: int | None = Field(default=None, description="当前页码（如果适用）")


class MySQLServiceQueryResponse(MySQLServiceBaseResponse):
    """ SQL查询 Response """
    data : List[MySQLServiceQueryResponseData] | None = Field(default=None, description="查询结果数据列表")



class MySQLServiceInsertResponseData(StrictBaseModel):
    """ SQL插入操作 Response 附加数据 """
    rows_affected: int = Field(..., description="插入的记录数")
    last_insert_id: int | None = Field(default=None, description="自增主键 ID（如果有）")

class MySQLServiceInsertResponse(MySQLServiceBaseResponse):
    """ SQL插入 Response """
    data: MySQLServiceInsertResponseData | None = Field(default=None, description="插入数据附加信息")
    


class MySQLServiceDeleteResponseData(StrictBaseModel):
    """ SQL删除 数据 """
    rows_affected: int = Field(default=-1, description="删除的记录数")

class MySQLServiceDeleteResponse(MySQLServiceBaseResponse):
    """ SQL删除 Response """
    data: MySQLServiceDeleteResponseData = Field(..., description="删除数据附加信息")
    


class MySQLServiceUpdateResponseData(StrictBaseModel):
    """ SQL更新 数据 """
    rows_affected: int = Field(..., description="更新的记录数")

class MySQLServiceUpdateResponse(MySQLServiceBaseResponse):
    """ SQL更新 Response """
    data: MySQLServiceUpdateResponseData | None = Field(default=None, description="更新数据附加信息")
    
    
    
# ------------------------------------------------------------------------------------------------
# 静态事务响应
# ------------------------------------------------------------------------------------------------    
    
class MySQLServiceStaticTransactionSQLExecutionResult(StrictBaseModel):
    """  静态事务单条SQL执行结果 """
    index: int = Field(..., ge=0, description="执行结果索引")
    sql: str = Field(..., description="执行的SQL语句")
    affected_rows: int = Field(..., ge=0, description="受影响的行数")


class MySQLServiceStaticTransactionResponseData(MySQLServiceBaseResponse):
    """ 静态事务 Response 附加数据 """
    sql_count: int = Field(..., ge=0, description="静态事务中执行的 SQL 语句数量")
    transaction_results: List[MySQLServiceStaticTransactionSQLExecutionResult] = Field(..., description="静态事务中每个操作的执行结果列表")


class MySQLServiceStaticTransactionResponse(MySQLServiceBaseResponse):
    """ 静态事务 Response """
    data: MySQLServiceStaticTransactionResponseData | None = Field(default=None, description="静态事务中每个操作的响应列表")
    
    
    
    
# ------------------------------------------------------------------------------------------------
# 动态事务响应
# ------------------------------------------------------------------------------------------------ 
class MySQLServiceDynamicTransactionStartResponse(MySQLServiceBaseResponse):
    """ 动态事务开始 Response """
    session_id: str | None = Field(default=None, description="事务上下文 ID")


class MySQLServiceDynamicTransactionExecuteSQLResponse(MySQLServiceBaseResponse):
    """ 动态事务执行单条SQL的响应 """
    affected_rows: int | None = Field(default=None, description="受影响的行数")
    last_insert_id: int | None = Field(default=None, description="最后插入的ID")

    
class MySQLServiceDynamicTransactionCommitResponse(MySQLServiceBaseResponse):
    """ 动态事务提交 Response """
    session_id: str | None = Field(default=None, description="事务上下文 ID")
    commit_time: datetime | None = Field(default_factory=datetime.now, description="提交时间")
    affected_rows: int | None = Field(default=None, ge=0, description="受影响的行数")
    executed_sql_count: int | None = Field(default=None, ge=0, description="执行的 SQL 语句数量")


class MySQLServiceDynamicTransactionRollbackResponse(MySQLServiceBaseResponse):
    """ 动态事务回滚 Response """
    session_id: str | None = Field(default=None, description="事务上下文 ID")
    message: str | None = Field(default=None, description="回滚操作的提示信息")
    result: bool | None = Field(default=True, description="回滚操作结果，通常为 True")
    level: str | None = Field(default="info", description="提示等级，通常为 info")