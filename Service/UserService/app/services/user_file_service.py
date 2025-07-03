# Project:      Agent
# Author:       yomu
# Time:         2025/06/29
# Version:      0.3
# Description:  User File Service - 用户文件管理服务

"""
用户文件管理服务
负责处理用户文件上传、下载、删除等文件管理相关功能
"""

from typing import Optional
from datetime import datetime
from pathlib import Path
from logging import Logger
from fastapi import UploadFile

from Service.UserService.app.db.UserDatabaseManager import UserDatabaseManager
from Service.UserService.app.db.UserAccountActionsDBAgent import UserAccountActionsDBAgent
from Service.UserService.app.models.UserServiceResponseType import (
    UploadFileResponse,
    UploadFileData,
    UserServiceResponseErrorCode,
    UserServiceErrorDetail
)
from Service.UserService.app.models.UserAccountDatabaseSQLParameterSchema import (
    UserAccountActionType,
    TableUserAccountActionsInsertSchema
)


class UserFileService:
    """
    用户文件管理服务
    负责处理用户文件的上传、存储、管理等业务逻辑
    """
    
    def __init__(self,
                 user_database_manager: UserDatabaseManager,
                 user_account_actions_db_agent: UserAccountActionsDBAgent,
                 token_verifier,  # 从认证服务注入token验证器
                 upload_file_max_size: int = 1024 * 1024 * 1024,  # 1GB
                 file_storage_path: str = "${AGENT_HOME}/Users/Files",
                 logger: Optional[Logger] = None):
        self.user_database_manager = user_database_manager
        self.user_account_actions_db_agent = user_account_actions_db_agent
        self.token_verifier = token_verifier
        self.upload_file_max_size = upload_file_max_size
        self.file_storage_path = file_storage_path
        self.logger = logger
    
    async def upload_file(self, session_token: str, file: UploadFile) -> UploadFileResponse:
        """
        用户上传文件
        
        :param session_token: 会话token
        :param file: 上传的文件
        :return: UploadFileResponse
        """
        operator = 'usr_upload_file'

        # 步骤1: 验证文件名有效性
        if not file.filename:
            if self.logger:
                self.logger.warning("文件上传请求缺少文件名")
            return UploadFileResponse(
                operator=operator,
                result=False,
                message="File name is missing",
                err_code=UserServiceResponseErrorCode.INVALID_REQUEST_FORMAT,
                data=None
            )

        # 步骤2: 验证会话token有效性
        try:
            user_id = self.token_verifier.verify_token(session_token)
        except ValueError as e:
            if self.logger:
                self.logger.warning(f"文件上传请求中的无效会话token：{e}")
            return UploadFileResponse(
                operator=operator,
                result=False,
                message="Invalid session token",
                err_code=UserServiceResponseErrorCode.INVALID_TOKEN,
                errors=[UserServiceErrorDetail(
                    code=UserServiceResponseErrorCode.INVALID_TOKEN,
                    message=str(e)
                )],
                data=None
            )

        # 2. 检查文件大小
        # file.size is optional and can be None
        file_size = file.size or 0
        if file_size > self.upload_file_max_size:
            message = f"File size {file_size} exceeds the limit of {self.upload_file_max_size} bytes."
            if self.logger:
                self.logger.warning(message)
            return UploadFileResponse(
                operator=operator,
                result=False,
                message=message,
                err_code=UserServiceResponseErrorCode.FILE_TOO_LARGE,
                errors=[UserServiceErrorDetail(
                    code=UserServiceResponseErrorCode.FILE_TOO_LARGE,
                    message=message
                )],
                data=None
            )

        # 3. 保存文件到服务器
        try:
            # 构建文件保存路径
            user_files_dir = Path(f"{self.file_storage_path}/{user_id}")
            user_files_dir.mkdir(parents=True, exist_ok=True)
            
            # 防止文件名冲突
            file_path = user_files_dir / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
            
            # 异步写入文件
            with open(file_path, "wb") as buffer:
                while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                    buffer.write(content)
            
            if self.logger:
                self.logger.info(f"User {user_id} uploaded file '{file.filename}' to '{file_path}'")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error saving uploaded file for user {user_id}: {e}")
            return UploadFileResponse(
                operator=operator,
                result=False,
                message="Failed to save uploaded file.",
                err_code=UserServiceResponseErrorCode.UNKNOWN_ERROR,
                errors=[UserServiceErrorDetail(
                    code=UserServiceResponseErrorCode.UNKNOWN_ERROR,
                    message=str(e)
                )],
                data=None
            )

        # 4. 将文件信息存入数据库
        try:
            # 构建相对路径 - 相对于项目根目录，以Users/Files/开头
            relative_file_path = f"Users/Files/{user_id}/{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
            
            file_data_dict = {
                "user_id": user_id,
                "file_name": file.filename,
                "file_type": file.content_type or "application/octet-stream",
                "file_path": relative_file_path,  # 使用相对路径
                "file_size": file_size,
                "upload_time": datetime.now()
            }
            
            res = await self.user_database_manager.insert_user_file(
                file_data_dict
            )

            if res:
                if self.logger:
                    self.logger.info(f"Successfully handled file upload for user {user_id}, file '{file.filename}'")
                
                # 记录文件上传动作
                try:
                    await self.user_account_actions_db_agent.insert_account_action(
                        action_data=TableUserAccountActionsInsertSchema(
                            user_id=user_id,
                            action_type=UserAccountActionType.profile_update,
                            action_detail=f"File uploaded: {file.filename}"
                        )
                    )
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Failed to log file upload action for user {user_id}: {e}")
                
                return UploadFileResponse(
                    operator=operator,
                    result=True,
                    message="File uploaded successfully.",
                    data=UploadFileData(
                        file_name=file.filename,
                        file_path=relative_file_path,  # 使用相对路径
                        file_size=file_size,
                        file_type=file.content_type
                    )
                )
            else:
                # 如果数据库插入失败，可以选择删除已保存的文件以保持一致性
                # os.remove(file_path)
                if self.logger:
                    self.logger.error(f"Failed to insert file info for user {user_id}, file '{file.filename}'")
                return UploadFileResponse(
                    operator=operator,
                    result=False,
                    message="Failed to record file information.",
                    err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                    errors=[UserServiceErrorDetail(
                        code=UserServiceResponseErrorCode.DATABASE_ERROR,
                        message="Failed to insert file info into database."
                    )],
                    data=None
                )

        except Exception as e:
            if self.logger:
                self.logger.error(f"Database error during file info insertion for user {user_id}: {e}")
            # 如果数据库插入失败，可以选择删除已保存的文件以保持一致性
            # os.remove(file_path)
            return UploadFileResponse(
                operator=operator,
                result=False,
                message="A database error occurred while recording file information.",
                err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                errors=[UserServiceErrorDetail(
                    code=UserServiceResponseErrorCode.DATABASE_ERROR,
                    message=str(e)
                )],
                data=None
            )
