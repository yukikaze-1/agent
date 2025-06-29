# Project:      Agent
# Author:       yomu
# Time:         2025/06/29
# Version:      0.3
# Description:  User Profile Service - 用户资料管理服务

"""
用户资料管理服务
负责处理用户个人资料修改、设置管理、通知设置等功能
"""

import json
from typing import Optional
from logging import Logger

from Service.UserService.app.db.UserCoreDBAgent import UserCoreDBAgent
from Service.UserService.app.db.UserProfileDBAgent import UserProfileDBAgent
from Service.UserService.app.db.UserSettingsDBAgent import UserSettingsDBAgent
from Service.UserService.app.models.UserServiceResponseType import (
    ModifyProfileResponse,
    ModifyProfileData,
    ModifySettingResponse,
    ModifySettingData,
    ModifyNotificationSettingsResponse,
    ModifyNotificationSettingsData,
    UserServiceResponseErrorCode,
    UserServiceErrorDetail
)
from Service.UserService.app.models.UserAccountDatabaseSQLParameterSchema import (
    TableUsersUpdateSetSchema,
    TableUsersUpdateWhereSchema,
    TableUserProfileUpdateSetSchema,
    TableUserProfileUpdateWhereSchema,
    TableUserSettingsUpdateSetSchema,
    TableUserSettingsUpdateWhereSchema,
    UserLanguage
)


class UserProfileService:
    """
    用户资料管理服务
    负责处理用户个人资料、设置、通知设置等相关业务逻辑
    """
    
    def __init__(self,
                 user_core_db_agent: UserCoreDBAgent,
                 user_profile_db_agent: UserProfileDBAgent,
                 user_settings_db_agent: UserSettingsDBAgent,
                 user_account_actions_db_agent,  # 用于记录操作日志
                 token_verifier,  # 从认证服务注入token验证器
                 logger: Optional[Logger] = None):
        self.user_core_db_agent = user_core_db_agent
        self.user_profile_db_agent = user_profile_db_agent
        self.user_settings_db_agent = user_settings_db_agent
        self.user_account_actions_db_agent = user_account_actions_db_agent
        self.token_verifier = token_verifier
        self.logger = logger
    
    async def modify_profile(self, session_token: str, 
                           user_name: Optional[str], 
                           profile_picture_path: Optional[str], 
                           signature: Optional[str]) -> ModifyProfileResponse:
        """
        修改用户个人信息

        :param session_token: 会话token
        :param user_name: 新用户名
        :param profile_picture_path: 新头像路径
        :param signature: 新签名
        :return: ModifyProfileResponse
        """
        operator = 'usr_modify_profile'
        
        # 步骤1: 验证会话token有效性
        try:
            user_id = self.token_verifier.verify_token(session_token)
        except ValueError as e:
            if self.logger:
                self.logger.warning(f"资料修改请求中的无效会话token：{e}")
            return ModifyProfileResponse(
                operator=operator,
                result=False,
                message="Invalid session token",
                err_code=UserServiceResponseErrorCode.INVALID_TOKEN,
                data=None
            )

        # 步骤2: 构建更新数据
        update_data = {}
        if user_name is not None:
            update_data['user_name'] = user_name
        if profile_picture_path is not None:
            update_data['profile_picture_path'] = profile_picture_path
        if signature is not None:
            update_data['signature'] = signature
            
        if not update_data:
            if self.logger:
                self.logger.warning(f"用户 {user_id} 未提供任何资料更新数据")
            return ModifyProfileResponse(
                operator=operator,
                result=False,
                message="No profile data provided to update",
                err_code=UserServiceResponseErrorCode.INVALID_REQUEST_FORMAT,
                data=None
            )

        # 步骤3: 更新用户基本信息表（如果包含用户名）
        if 'user_name' in update_data:
            try:
                # 获取当前用户的后缀标识
                user_info = await self.user_core_db_agent.fetch_user_info_by_user_id(user_id)
                if user_info and 'user_suffix' in user_info:
                    res_core = await self.user_core_db_agent.update_users(
                        update_data=TableUsersUpdateSetSchema(
                            user_name=update_data['user_name'], 
                            user_suffix=user_info['user_suffix']
                        ),
                        update_where=TableUsersUpdateWhereSchema(user_id=user_id)
                    )
                    if not res_core and self.logger:
                        self.logger.warning(f"用户 {user_id} 的用户名更新失败")
                else:
                    if self.logger:
                        self.logger.error(f"Could not fetch user_suffix for user_id: {user_id}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error updating user_name for user_id {user_id}: {e}")
                # 可以选择在这里返回错误，或者继续尝试更新 profile
        
        # 更新 user_profile 表
        profile_update_data = {k: v for k, v in update_data.items() if k != 'user_name'}
        if profile_update_data:
            try:
                res_profile = await self.user_profile_db_agent.update_user_profile(
                    update_data=TableUserProfileUpdateSetSchema(**profile_update_data),
                    update_where=TableUserProfileUpdateWhereSchema(user_id=user_id)
                )
                if not res_profile and self.logger:
                    self.logger.warning(f"Failed to update user_profile for user_id: {user_id}")
                    # 如果核心信息更新了但这里失败了，可能需要考虑事务
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error updating user_profile for user_id {user_id}: {e}")
                return ModifyProfileResponse(
                    operator=operator,
                    result=False,
                    message="Database error while updating profile.",
                    err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                    data=None
                )

        # 记录个人信息修改动作
        try:
            from Service.UserService.app.models.UserAccountDatabaseSQLParameterSchema import (
                UserAccountActionType,
                TableUserAccountActionsInsertSchema
            )
            await self.user_account_actions_db_agent.insert_account_action(
                action_data=TableUserAccountActionsInsertSchema(
                    user_id=user_id,
                    action_type=UserAccountActionType.profile_update,
                    action_detail=f"User profile updated: {', '.join(update_data.keys())}"
                )
            )
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to log profile update action for user {user_id}: {e}")

        return ModifyProfileResponse(
            operator=operator,
            result=True,
            message="User profile updated successfully.",
            data=ModifyProfileData(
                user_id=user_id,
                user_name=user_name,
                profile_picture_url=profile_picture_path,
                signature=signature
            )
        )

    async def modify_notification_settings(self, session_token: str, settings_json: str) -> ModifyNotificationSettingsResponse:
        """
        修改用户通知设置

        :param session_token: 会话token
        :param settings_json: 新的通知设置 (JSON 字符串)
        :return: ModifyNotificationSettingsResponse
        """
        operator = 'usr_modify_notification_settings'
        
        try:
            user_id = self.token_verifier.verify_token(session_token)
        except ValueError as e:
            if self.logger:
                self.logger.warning(f"Invalid session token provided: {e}")
            return ModifyNotificationSettingsResponse(
                operator=operator,
                result=False,
                message=str(e),
                err_code=UserServiceResponseErrorCode.INVALID_TOKEN,
                data=None
            )
            
        try:
            # 验证 settings_json 是否是有效的 JSON
            settings_dict = json.loads(settings_json)
        except json.JSONDecodeError:
            return ModifyNotificationSettingsResponse(
                operator=operator,
                result=False,
                message="Invalid JSON format for notification settings.",
                err_code=UserServiceResponseErrorCode.INVALID_REQUEST_FORMAT,
                data=None
            )

        try:
            res = await self.user_settings_db_agent.update_user_settings(
                update_data=TableUserSettingsUpdateSetSchema(notification_setting=settings_json),
                update_where=TableUserSettingsUpdateWhereSchema(user_id=user_id)
            )
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error updating notification settings for user {user_id}: {e}")
            return ModifyNotificationSettingsResponse(
                operator=operator,
                result=False,
                message="Database error while updating notification settings.",
                err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                data=None
            )

        if not res:
            return ModifyNotificationSettingsResponse(
                operator=operator,
                result=False,
                message="Failed to update notification settings, user may not exist.",
                err_code=UserServiceResponseErrorCode.ACCOUNT_NOT_FOUND,
                data=None
            )

        # 记录通知设置修改动作
        try:
            from Service.UserService.app.models.UserAccountDatabaseSQLParameterSchema import (
                UserAccountActionType,
                TableUserAccountActionsInsertSchema
            )
            await self.user_account_actions_db_agent.insert_account_action(
                action_data=TableUserAccountActionsInsertSchema(
                    user_id=user_id,
                    action_type=UserAccountActionType.profile_update,
                    action_detail="User notification settings updated"
                )
            )
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to log notification settings update action for user {user_id}: {e}")

        return ModifyNotificationSettingsResponse(
            operator=operator,
            result=True,
            message="Notification settings updated successfully.",
            data=ModifyNotificationSettingsData(
                user_id=user_id,
                notification_settings=settings_dict
            )
        )

    async def modify_settings(self, session_token: str, 
                             language: Optional[UserLanguage], 
                             configure: Optional[str]) -> ModifySettingResponse:
        """
        修改用户个人设置

        :param session_token: 会话token
        :param language: 语言
        :param configure: 配置 (JSON 字符串)
        :return: ModifySettingResponse
        """
        operator = 'usr_modify_settings'
        
        try:
            user_id = self.token_verifier.verify_token(session_token)
        except ValueError as e:
            if self.logger:
                self.logger.warning(f"Invalid session token provided: {e}")
            return ModifySettingResponse(
                operator=operator,
                result=False,
                message=str(e),
                err_code=UserServiceResponseErrorCode.INVALID_TOKEN,
                data=None
            )

        update_data = {}
        configure_dict = None

        if language:
            update_data['language'] = language.value
        
        if configure:
            try:
                configure_dict = json.loads(configure)
                update_data['configure'] = configure_dict
            except json.JSONDecodeError:
                return ModifySettingResponse(
                    operator=operator,
                    result=False,
                    message="Invalid JSON format for configure.",
                    err_code=UserServiceResponseErrorCode.INVALID_REQUEST_FORMAT,
                    data=None
                )
        
        if not update_data:
            return ModifySettingResponse(
                operator=operator,
                result=False,
                message="No settings data provided to update.",
                err_code=UserServiceResponseErrorCode.INVALID_REQUEST_FORMAT,
                data=None
            )

        try:
            res = await self.user_settings_db_agent.update_user_settings(
                update_data=TableUserSettingsUpdateSetSchema(**update_data),
                update_where=TableUserSettingsUpdateWhereSchema(user_id=user_id)
            )
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error updating settings for user {user_id}: {e}")
            return ModifySettingResponse(
                operator=operator,
                result=False,
                message="Database error while updating settings.",
                err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                data=None
            )

        if not res:
            return ModifySettingResponse(
                operator=operator,
                result=False,
                message="Failed to update settings, user may not exist.",
                err_code=UserServiceResponseErrorCode.ACCOUNT_NOT_FOUND,
                data=None
            )

        # 记录设置修改动作
        try:
            from Service.UserService.app.models.UserAccountDatabaseSQLParameterSchema import (
                UserAccountActionType,
                TableUserAccountActionsInsertSchema
            )
            await self.user_account_actions_db_agent.insert_account_action(
                action_data=TableUserAccountActionsInsertSchema(
                    user_id=user_id,
                    action_type=UserAccountActionType.profile_update,
                    action_detail=f"User settings updated: {', '.join(update_data.keys())}"
                )
            )
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to log settings update action for user {user_id}: {e}")

        return ModifySettingResponse(
            operator=operator,
            result=True,
            message="User settings updated successfully.",
            data=ModifySettingData(
                user_id=user_id,
                language=language.value if language else None,
                configure=configure_dict
            )
        )
