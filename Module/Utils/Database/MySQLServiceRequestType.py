# Project:      Agent
# Author:       yomu
# Time:         2025/6/21
# Version:      0.1
# Description:  MySQLService Request Type Definitions


"""
    各种MySQLService请求的格式定义
"""

from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, EmailStr, constr, Field, model_validator

class StrictBaseModel(BaseModel):
    """
    基础模型，所有模型都继承自此类
    """
    class Config:
        extra = "forbid"  # 禁止额外字段
        anystr_strip_whitespace = True  # 去除字符串两端空格
        use_enum_values = True  # 使用枚举值而不是枚举对象

# ------------------------------------------------------------------------------------------------
# 单条CURD请求
# ------------------------------------------------------------------------------------------------         

class MySQLServiceSQLRequest(StrictBaseModel):
    """ SQL请求格式 """
    connection_id: int = Field(..., ge=0, description="数据库请求ID")
    sql: str = Field(..., description="SQL语句")
    sql_args: List[Any] = Field(..., description="SQL语句参数")
    
    @model_validator(mode="after")
    def check_safe_sql(self):
        # 检查SQL语句是否以安全的命令开头
        allowed_prefixes = ["SELECT", "INSERT", "UPDATE", "DELETE"]
        if not any(self.sql.upper().startswith(cmd) for cmd in allowed_prefixes):
            raise ValueError("仅支持 SELECT, INSERT, UPDATE, DELETE 语句")
        return self
    
# ------------------------------------------------------------------------------------------------
# 连接数据库请求
# ------------------------------------------------------------------------------------------------ 

class MySQLServiceConnectRequest(StrictBaseModel):
    """ 连接数据库请求格式 """
    host: str = Field(..., description="数据库主机名")
    port: int = Field(..., ge=0, description="数据库端口")
    user: str = Field(..., description="数据库用户名")
    password: str = Field(..., description="数据库密码")
    database: str = Field(..., description="数据库名称")
    charset: str = Field(..., description="数据库字符集")
    
# ------------------------------------------------------------------------------------------------
# 静态事务请求
# ------------------------------------------------------------------------------------------------ 

class MySQLServiceStaticTransactionSQL(StrictBaseModel):
    """ 静态事务中的 SQL 请求格式 """
    sql: str = Field(..., description="要执行的 SQL")
    sql_args: Optional[List[Any] | Dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_args(self) -> 'MySQLServiceStaticTransactionSQL':
        self.sql = self.sql.strip()  # 避免多余空格或换行符
        # 检查 sql 字段是否为空
        if not self.sql:
            raise ValueError("sql 字段不能为空")
        
        # 检查 sql_args 的类型
        if self.sql_args is not None:
            if not isinstance(self.sql_args, (list, dict)):
                raise ValueError("sql_args 必须是 list 或 dict 类型")
            
        # 检查 SQL 语句是否以允许的前缀开头    
        allowed_prefixes = ["SELECT", "INSERT", "UPDATE", "DELETE"]
        if not any(self.sql.upper().startswith(cmd) for cmd in allowed_prefixes):
            raise ValueError("仅支持 SELECT, INSERT, UPDATE, DELETE 语句")
        return self


class MySQLServiceStaticTransactionRequest(StrictBaseModel):
    """ 静态事务请求格式 """
    connection_id: int = Field(..., ge=0, description="数据库连接ID")
    sql_requests: List[MySQLServiceStaticTransactionSQL] = Field(..., min_length=1, max_length=100, description="事务中执行的一组 SQL")


# ------------------------------------------------------------------------------------------------
# 动态事务请求
# ------------------------------------------------------------------------------------------------ 

class MySQLServiceDynamicTransactionStartRequest(StrictBaseModel):
    """ 动态事务start请求格式 """
    connection_id: int = Field(..., ge=0, description="数据库连接ID")


class MySQLServiceDynamicTransactionExecuteSQLRequest(StrictBaseModel):
    """ 动态事务执行 SQL 请求格式 """
    session_id: str = Field(..., description="事务上下文 ID")
    sql: str = Field(..., description="SQL 语句")
    sql_args: List[Any] | Dict[str, Any] | None = Field(default_factory=list)
    
    
class MySQLServiceDynamicTransactionCommitRequest(StrictBaseModel):
    """ 动态事务commit请求格式 """
    session_id: str = Field(..., description="事务上下文 ID")


class MySQLServiceDynamicTransactionRollbackRequest(StrictBaseModel):
    """ 动态事务rollback请求格式 """
    session_id: str = Field(..., description="事务上下文 ID")
