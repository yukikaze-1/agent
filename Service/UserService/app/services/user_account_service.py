# Project:      Agent
# Author:       yomu
# Time:         2025/06/29
# Version:      0.3
# Description:  User Account Service - 用户账户管理服务

"""
用户账户管理服务
负责处理用户注册、注销、修改密码等账户管理相关功能
"""

from typing import Optional
from datetime import datetime
from logging import Logger

from Service.UserService.app.db.UserCoreDBAgent import UserCoreDBAgent
from Service.UserService.app.db.UserAccountActionsDBAgent import UserAccountActionsDBAgent
from Service.UserService.app.db.UserDatabaseManager import UserDatabaseManager
from Service.UserService.app.models.UserServiceResponseType import (
    RegisterResponse,
    RegisterData,
    UnregisterResponse,
    UnregisterData,
    ModifyPasswordResponse,
    ModifyPasswordData,
    UserServiceResponseErrorCode,
    UserServiceErrorDetail
)
from Service.UserService.app.models.UserAccountDatabaseSQLParameterSchema import (
    UserAccountActionType,
    TableUserAccountActionsInsertSchema
)


class UserAccountService:
    """
    用户账户管理服务
    负责处理用户账户的创建、删除、密码管理等业务逻辑
    """
    
    def __init__(self,
                 user_core_db_agent: UserCoreDBAgent,
                 user_account_actions_db_agent: UserAccountActionsDBAgent,
                 user_database_manager: UserDatabaseManager,
                 password_hasher,  # 从认证服务注入密码哈希器
                 token_verifier,  # 从认证服务注入token验证器
                 logger: Optional[Logger] = None):
        self.user_core_db_agent = user_core_db_agent
        self.user_account_actions_db_agent = user_account_actions_db_agent
        self.user_database_manager = user_database_manager
        self.password_hasher = password_hasher
        self.token_verifier = token_verifier
        self.logger = logger
    
    async def register(self, user_name: str, account: str, password: str, email: str) -> RegisterResponse:
        """
        用户注册
        
        :param user_name: 用户名
        :param account: 用户账号
        :param password: 用户密码
        :param email: 用户邮箱
        :return: RegisterResponse
        """
        operator = 'usr_register'
        
        # 步骤1: 检查用户是否已存在
        try:
            # 验证账户是否已注册
            if await self.user_core_db_agent.check_user_exists(identifier=account):
                message = f"Registration failed! Account '{account}' already exists"
                if self.logger:
                    self.logger.info(f"注册失败：账户 {account} 已存在")
                return RegisterResponse(
                    operator=operator,
                    result=False,
                    message=message,
                    err_code=UserServiceResponseErrorCode.ACCOUNT_ALREADY_EXISTS,
                    errors=[UserServiceErrorDetail(
                        code=UserServiceResponseErrorCode.ACCOUNT_ALREADY_EXISTS,
                        message=message,
                        field='account'
                    )],
                    data=None
                )
            
            # 验证邮箱是否已注册
            if await self.user_core_db_agent.check_user_exists(identifier=email):
                message = f"Registration failed! Email '{email}' already exists"
                if self.logger:
                    self.logger.info(f"注册失败：邮箱 {email} 已存在")
                return RegisterResponse(
                    operator=operator,
                    result=False,
                    message=message,
                    err_code=UserServiceResponseErrorCode.EMAIL_ALREADY_EXISTS,
                    errors=[UserServiceErrorDetail(
                        code=UserServiceResponseErrorCode.EMAIL_ALREADY_EXISTS,
                        message=message,
                        field='email'
                    )],
                    data=None
                )
        except Exception as e:
            if self.logger:
                self.logger.error(f"检查用户存在性时发生数据库错误：{e}")
            return RegisterResponse(
                operator=operator,
                result=False,
                message="Database error occurred while checking user existence",
                err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                errors=[UserServiceErrorDetail(
                    code=UserServiceResponseErrorCode.DATABASE_ERROR,
                    message="Internal database error"
                )],
                data=None
            )

        # 步骤2: 对密码进行哈希处理
        hashed_password = self.password_hasher.hash_password(password)

        # 步骤3: 使用用户数据库管理器插入新用户（自动处理用户标识符和文件路径）
        try:
            user_id = await self.user_database_manager.insert_new_user(
                account=account,
                email=email, 
                password_hash=hashed_password,
                user_name=user_name
            )
            if user_id:
                if self.logger:
                    self.logger.info(f"成功注册新用户，用户ID：{user_id}")
                
                # 步骤4: 记录账户创建操作日志
                try:
                    await self.user_account_actions_db_agent.insert_account_action(
                        action_data=TableUserAccountActionsInsertSchema(
                            user_id=user_id,
                            action_type=UserAccountActionType.login,
                            action_detail=f"User account '{account}' created successfully"
                        )
                    )
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"记录账户创建操作失败，用户ID {user_id}：{e}")
                
                return RegisterResponse(
                    operator=operator,
                    result=True,
                    message="Registration successful",
                    data=RegisterData(user_id=user_id)
                )
            else:
                if self.logger:
                    self.logger.error("用户注册失败：事务处理出错")
                return RegisterResponse(
                    operator=operator,
                    result=False,
                    message="Registration failed due to server error",
                    err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                    errors=[UserServiceErrorDetail(
                        code=UserServiceResponseErrorCode.DATABASE_ERROR,
                        message="Failed to create user record"
                    )],
                    data=None
                )
        except Exception as e:
            if self.logger:
                self.logger.error(f"新用户注册过程中发生异常：{e}")
            return RegisterResponse(
                operator=operator,
                result=False,
                message="Unexpected error occurred during registration",
                err_code=UserServiceResponseErrorCode.UNKNOWN_ERROR,
                errors=[UserServiceErrorDetail(
                    code=UserServiceResponseErrorCode.UNKNOWN_ERROR,
                    message=str(e)
                )],
                data=None
            )

    async def change_password(self, session_token: str, new_password: str) -> ModifyPasswordResponse:
        """
        用户修改密码
        
        :param session_token: 会话token
        :param new_password: 新密码
        :return: ModifyPasswordResponse
        """
        operator = 'usr_change_pwd'
        
        # 步骤1: 验证会话token有效性
        try:
            user_id = self.token_verifier.verify_token(session_token)
        except ValueError as e:
            if self.logger:
                self.logger.warning(f"无效的会话token：{e}")
            return ModifyPasswordResponse(
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

        # 步骤2: 对新密码进行哈希处理
        hashed_password = self.password_hasher.hash_password(new_password)

        # 步骤3: 更新数据库中的密码
        try:
            success = await self.user_core_db_agent.update_user_password_by_user_id(
                user_id=user_id,
                new_password_hash=hashed_password
            )
            if success:
                if self.logger:
                    self.logger.info(f"用户 {user_id} 成功修改密码")
                
                # 步骤4: 记录密码修改操作日志
                try:
                    await self.user_account_actions_db_agent.insert_account_action(
                        action_data=TableUserAccountActionsInsertSchema(
                            user_id=user_id,
                            action_type=UserAccountActionType.password_update,
                            action_detail="User password changed successfully"
                        )
                    )
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"记录密码修改操作失败，用户ID {user_id}：{e}")
                
                # 步骤5: 获取用户信息用于响应
                user_info = await self.user_core_db_agent.fetch_user_info_by_user_id(user_id)
                if not user_info:
                    # 即使获取信息失败，密码也已成功修改，返回成功但数据不完整
                    if self.logger:
                        self.logger.warning(f"密码修改成功但无法获取用户 {user_id} 的更新信息")
                    return ModifyPasswordResponse(
                        operator=operator,
                        result=True,
                        message="Password changed successfully, but failed to retrieve updated user info",
                        data=ModifyPasswordData(
                            user_id=user_id, 
                            password_update_time=datetime.now(),
                            account=None,
                            email=None,
                            user_name=None
                        )
                    )

                return ModifyPasswordResponse(
                    operator=operator,
                    result=True,
                    message="Password changed successfully",
                    data=ModifyPasswordData(
                        user_id=user_id,
                        account=user_info.get('account'),
                        email=user_info.get('email'),
                        user_name=user_info.get('user_name'),
                        password_update_time=datetime.now()
                    )
                )
            else:
                if self.logger:
                    self.logger.error(f"用户 {user_id} 密码修改失败：数据库更新操作失败")
                return ModifyPasswordResponse(
                    operator=operator,
                    result=False,
                    message="Failed to change password",
                    err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                    errors=[UserServiceErrorDetail(
                        code=UserServiceResponseErrorCode.DATABASE_ERROR,
                        message="Failed to update password in database"
                    )],
                    data=None
                )
        except Exception as e:
            if self.logger:
                self.logger.error(f"用户 {user_id} 修改密码时发生数据库错误：{e}")
            return ModifyPasswordResponse(
                operator=operator,
                result=False,
                message="Database error occurred",
                err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                errors=[UserServiceErrorDetail(
                    code=UserServiceResponseErrorCode.DATABASE_ERROR,
                    message=str(e)
                )],
                data=None
            )

    async def unregister(self, session_token: str) -> UnregisterResponse:
        """
        用户注销
        
        :param session_token: 会话token
        :return: UnregisterResponse
        """
        operator = 'usr_unregister'
        
        # 步骤1: 验证会话token有效性
        try:
            user_id = self.token_verifier.verify_token(session_token)
        except ValueError as e:
            if self.logger:
                self.logger.warning(f"注销请求中的无效会话token：{e}")
            return UnregisterResponse(
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

        # 步骤2: 执行用户软删除操作
        try:
            success = await self.user_core_db_agent.soft_delete_user_by_user_id(user_id=user_id)
            if success:
                if self.logger:
                    self.logger.info(f"用户 {user_id} 已成功执行软删除操作")
                
                # 步骤3: 记录账户注销操作日志
                try:
                    await self.user_account_actions_db_agent.insert_account_action(
                        action_data=TableUserAccountActionsInsertSchema(
                            user_id=user_id,
                            action_type=UserAccountActionType.account_deletion,
                            action_detail="User account unregistered (soft-deleted)"
                        )
                    )
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"记录账户删除操作失败，用户ID {user_id}：{e}")
                
                return UnregisterResponse(
                    operator=operator,
                    result=True,
                    message="Account unregistered successfully",
                    data=UnregisterData(user_id=user_id)
                )
            else:
                if self.logger:
                    self.logger.error(f"用户 {user_id} 软删除操作失败")
                return UnregisterResponse(
                    operator=operator,
                    result=False,
                    message="Failed to unregister account",
                    err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                    errors=[UserServiceErrorDetail(
                        code=UserServiceResponseErrorCode.DATABASE_ERROR,
                        message="Failed to update user status in database"
                    )],
                    data=None
                )
        except Exception as e:
            if self.logger:
                self.logger.error(f"用户 {user_id} 软删除过程中发生数据库错误：{e}")
            return UnregisterResponse(
                operator=operator,
                result=False,
                message="Database error occurred",
                err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                errors=[UserServiceErrorDetail(
                    code=UserServiceResponseErrorCode.DATABASE_ERROR,
                    message=str(e)
                )],
                data=None
            )
