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


class MySQLServiceConnectRequest(StrictBaseModel):
    """ 连接数据库请求格式 """
    host: str = Field(..., description="数据库主机名")
    port: int = Field(..., ge=0, description="数据库端口")
    user: str = Field(..., description="数据库用户名")
    password: str = Field(..., description="数据库密码")
    database: str = Field(..., description="数据库名称")
    charset: str = Field(..., description="数据库字符集")


class MySQLServiceTransactionSQL(StrictBaseModel):
    sql: str = Field(..., description="要执行的 SQL")
    sql_args: Optional[List[Any] | Dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_args(self) -> 'MySQLServiceTransactionSQL':
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


class MySQLServiceTransactionRequest(StrictBaseModel):
    """ 事务请求格式 """
    connection_id: int = Field(..., ge=0, description="数据库连接ID")
    sql_requests: List[MySQLServiceTransactionSQL] = Field(..., min_length=1, max_length=100, description="事务中执行的一组 SQL")

