# Project:      Agent
# Author:       yomu
# Time:         2025/6/29
# Version:      0.1
# Description:  Response Builder for MySQL Service

"""
响应构建器
统一处理各种响应的构建逻辑
"""

from typing import List, Any, Optional
from datetime import datetime

from Service.MySQLService.schema.response import (
    MySQLServiceResponseErrorCode,
    MySQLServiceErrorDetail,
    MySQLServiceConnectDatabaseResponseData,    
    MySQLServiceConnectDatabaseResponse,
    MySQLServiceQueryResponseData,
    MySQLServiceQueryResponse,
    MySQLServiceInsertResponseData,
    MySQLServiceInsertResponse,
    MySQLServiceDeleteResponseData,
    MySQLServiceDeleteResponse,
    MySQLServiceUpdateResponseData,
    MySQLServiceUpdateResponse,
    MySQLServiceStaticTransactionSQLExecutionResult,
    MySQLServiceStaticTransactionResponseData,
    MySQLServiceStaticTransactionResponse,
    MySQLServiceDynamicTransactionExecuteSQLResponse,
    MySQLServiceDynamicTransactionStartResponse,
    MySQLServiceDynamicTransactionCommitResponse,
    MySQLServiceDynamicTransactionRollbackResponse,
)


class ResponseBuilder:
    """
    响应构建器
    统一构建各种类型的响应对象
    """
    
    @staticmethod
    def build_connection_error_response(operator: str, connection_id: int):
        """构建连接ID不存在的错误响应"""
        return MySQLServiceConnectDatabaseResponse(
            operator=operator,
            message=f"{operator} failed",
            result=False,
            err_code=MySQLServiceResponseErrorCode.CONNECTION_ID_NOT_EXISTS,
            errors=[MySQLServiceErrorDetail(
                code=MySQLServiceResponseErrorCode.CONNECTION_ID_NOT_EXISTS,
                message=f"Connection ID '{connection_id}' does not exist.",
                field="connection_id",
                hint="Please check if the connection ID is correct."
            )]
        )
        
    
    @staticmethod
    def build_connect_success_response(connection_id: int, database: str) -> MySQLServiceConnectDatabaseResponse:
        """构建数据库连接成功响应"""
        return MySQLServiceConnectDatabaseResponse(
            operator="Connect Database",
            result=True,
            message=f"Successfully connected to database '{database}'",
            data=MySQLServiceConnectDatabaseResponseData(connection_id=connection_id)
        )
    
    @staticmethod
    def build_connect_error_response(database: str, error_message: str) -> MySQLServiceConnectDatabaseResponse:
        """构建数据库连接失败响应"""
        return MySQLServiceConnectDatabaseResponse(
            operator="Connect Database",
            result=False,
            message=f"Failed to connect to database '{database}' after 3 retries.",
            level="error",
            err_code=MySQLServiceResponseErrorCode.CONNECT_DATABASE_FAILED,
            errors=[MySQLServiceErrorDetail(
                code=MySQLServiceResponseErrorCode.CONNECT_DATABASE_FAILED,
                message=error_message,
                field="database",
                hint="Please check the database parameters or try again later."
            )],
            data=MySQLServiceConnectDatabaseResponseData(connection_id=-1)
        )
    
    @staticmethod
    def build_query_success_response(query_data: List[MySQLServiceQueryResponseData]) -> MySQLServiceQueryResponse:
        """构建查询成功响应"""
        return MySQLServiceQueryResponse(
            operator="Query",
            message="Query success.",
            result=True,
            data=query_data
        )
    
    @staticmethod
    def build_query_error_response(error_message: str) -> MySQLServiceQueryResponse:
        """构建查询失败响应"""
        return MySQLServiceQueryResponse(
            operator="Query",
            message=error_message,
            result=False,
            err_code=MySQLServiceResponseErrorCode.QUERY_DATABASE_FAILED,
            errors=[MySQLServiceErrorDetail(
                code=MySQLServiceResponseErrorCode.QUERY_DATABASE_FAILED,
                message=error_message,
                field="sql",
                hint="Please check the SQL syntax and parameters or try again later."
            )]
        )
    
    @staticmethod
    def build_insert_success_response(rows_affected: int, last_insert_id: Optional[int] = None) -> MySQLServiceInsertResponse:
        """构建插入成功响应"""
        return MySQLServiceInsertResponse(
            operator="Insert",
            message="Insert success.",
            result=True,
            data=MySQLServiceInsertResponseData(rows_affected=rows_affected, last_insert_id=last_insert_id)
        )
    
    @staticmethod
    def build_insert_error_response(error_message: str) -> MySQLServiceInsertResponse:
        """构建插入失败响应"""
        return MySQLServiceInsertResponse(
            operator="Insert",
            message=error_message,
            result=False,
            err_code=MySQLServiceResponseErrorCode.INSERT_DATABASE_FAILED,
            errors=[MySQLServiceErrorDetail(
                code=MySQLServiceResponseErrorCode.INSERT_DATABASE_FAILED,
                message=error_message,
                field="database",
                hint="Unknown error in database, please check the parameters or try again later."
            )]
        )
    
    @staticmethod
    def build_update_success_response(rows_affected: int) -> MySQLServiceUpdateResponse:
        """构建更新成功响应"""
        return MySQLServiceUpdateResponse(
            operator="Update",
            message="Update success.",
            result=True,
            data=MySQLServiceUpdateResponseData(rows_affected=rows_affected)
        )
    
    @staticmethod
    def build_update_error_response(error_message: str) -> MySQLServiceUpdateResponse:
        """构建更新失败响应"""
        return MySQLServiceUpdateResponse(
            operator="Update",
            message=error_message,
            result=False,
            err_code=MySQLServiceResponseErrorCode.UPDATE_DATABASE_FAILED,
            errors=[MySQLServiceErrorDetail(
                code=MySQLServiceResponseErrorCode.UPDATE_DATABASE_FAILED,
                message=error_message,
                field="sql",
                hint="Please check the SQL syntax and parameters or try again later."
            )]
        )
    
    @staticmethod
    def build_delete_success_response(rows_affected: int) -> MySQLServiceDeleteResponse:
        """构建删除成功响应"""
        return MySQLServiceDeleteResponse(
            operator="Delete",
            message="Delete success.",
            result=True,
            data=MySQLServiceDeleteResponseData(rows_affected=rows_affected)
        )
    
    @staticmethod
    def build_delete_error_response(error_message: str) -> MySQLServiceDeleteResponse:
        """构建删除失败响应"""
        return MySQLServiceDeleteResponse(
            operator="Delete",
            message=error_message,
            result=False,
            data=MySQLServiceDeleteResponseData(rows_affected=-1),
            err_code=MySQLServiceResponseErrorCode.DELETE_DATABASE_FAILED,
            level="error"
        )
    
    @staticmethod
    def build_static_transaction_success_response(
        results: List[MySQLServiceStaticTransactionSQLExecutionResult],
        sql_count: int
    ) -> MySQLServiceStaticTransactionResponse:
        """构建静态事务成功响应"""
        return MySQLServiceStaticTransactionResponse(
            operator="Transaction",
            message="Transaction success.",
            result=True,
            data=MySQLServiceStaticTransactionResponseData(
                operator="static transaction",
                result=True,
                message="Static transaction execute success.",
                sql_count=sql_count,
                transaction_results=results
            )
        )
    
    @staticmethod
    def build_static_transaction_error_response(
        error_message: str, 
        sql_statements: List[str]
    ) -> MySQLServiceStaticTransactionResponse:
        """构建静态事务失败响应"""
        return MySQLServiceStaticTransactionResponse(
            operator="Transaction",
            message="Transaction failed.",
            result=False,
            err_code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
            errors=[MySQLServiceErrorDetail(
                code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                message=error_message,
                field="transaction",
                sql=sql_statements,
                hint="Please check the SQL syntax and parameters or try again later."
            )]
        )
    
    @staticmethod
    def build_dynamic_transaction_start_success_response(session_id: str) -> MySQLServiceDynamicTransactionStartResponse:
        """构建动态事务开始成功响应"""
        return MySQLServiceDynamicTransactionStartResponse(
            operator="Transaction",
            message="Transaction started.",
            result=True,
            session_id=session_id
        )
    
    @staticmethod
    def build_dynamic_transaction_start_error_response(error_message: str) -> MySQLServiceDynamicTransactionStartResponse:
        """构建动态事务开始失败响应"""
        return MySQLServiceDynamicTransactionStartResponse(
            operator="Transaction",
            message="Transaction failed.",
            result=False,
            err_code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
            errors=[MySQLServiceErrorDetail(
                code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                message=error_message,
                hint="Please try again later."
            )]   
        )
    
    @staticmethod
    def build_dynamic_transaction_execute_success_response(
        affected_rows: int, 
        last_insert_id: int
    ) -> MySQLServiceDynamicTransactionExecuteSQLResponse:
        """构建动态事务执行SQL成功响应"""
        return MySQLServiceDynamicTransactionExecuteSQLResponse(
            operator="Transaction Execute SQL",
            message="SQL executed successfully.",
            result=True,
            affected_rows=affected_rows,
            last_insert_id=last_insert_id,
        )
    
    @staticmethod
    def build_dynamic_transaction_execute_error_response(error_message: str) -> MySQLServiceDynamicTransactionExecuteSQLResponse:
        """构建动态事务执行SQL失败响应"""
        return MySQLServiceDynamicTransactionExecuteSQLResponse(
            operator="Transaction Execute SQL",
            message="Failed to execute SQL.",
            result=False,
            err_code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
            errors=[MySQLServiceErrorDetail(
                code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                message=error_message,
                field="sql",
                hint="Please check the SQL syntax and parameters or try again later."
            )]
        )
    
    @staticmethod
    def build_dynamic_transaction_commit_success_response(
        session_id: str, 
        affected_rows: int, 
        executed_sql_count: int
    ) -> MySQLServiceDynamicTransactionCommitResponse:
        """构建动态事务提交成功响应"""
        return MySQLServiceDynamicTransactionCommitResponse(
            operator="Transaction Commit",
            message="Transaction committed successfully.",
            result=True,
            session_id=session_id,
            commit_time=datetime.now(),
            affected_rows=affected_rows,
            executed_sql_count=executed_sql_count
        )
    
    @staticmethod
    def build_dynamic_transaction_commit_error_response(error_message: str) -> MySQLServiceDynamicTransactionCommitResponse:
        """构建动态事务提交失败响应"""
        return MySQLServiceDynamicTransactionCommitResponse(
            operator="Transaction Commit",
            message="Transaction commit failed.",
            result=False,
            err_code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
            errors=[MySQLServiceErrorDetail(
                code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                message=error_message,
                field="commit",
                hint="Please check connection or server status"
            )]
        )
    
    @staticmethod
    def build_dynamic_transaction_rollback_response() -> MySQLServiceDynamicTransactionRollbackResponse:
        """构建动态事务回滚响应"""
        return MySQLServiceDynamicTransactionRollbackResponse(
            operator="Transaction Rollback",
            message="Transaction rolled back successfully.",
            result=True
        )
    
    @staticmethod
    def build_session_not_found_error_response(operator: str, session_id: str):
        """构建会话未找到的错误响应"""
        return {
            "operator": operator,
            "message": f"{operator} failed",
            "result": False,
            "err_code": MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
            "errors": [MySQLServiceErrorDetail(
                code=MySQLServiceResponseErrorCode.TRANSACTION_FAILED,
                message=f"Session ID '{session_id}' does not exist.",
                field="session_id",
                hint="Please check if the session ID is correct."
            )]
        }
