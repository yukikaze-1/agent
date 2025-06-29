# Project:      Agent
# Author:       yomu
# Time:         2025/06/29
# Version:      0.3
# Description:  User Authentication Service - 用户认证服务

"""
用户认证服务
负责处理用户登录、JWT令牌生成/验证、密码验证等认证相关功能
"""

from typing import Optional, Tuple
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
from logging import Logger

from Service.UserService.app.db.UserCoreDBAgent import UserCoreDBAgent
from Service.UserService.app.db.UserProfileDBAgent import UserProfileDBAgent
from Service.UserService.app.db.UserLoginLogsDBAgent import UserLoginLogsDBAgent
from Service.UserService.app.models.UserServiceResponseType import (
    LoginResponse,
    LoginData,
    UserServiceResponseErrorCode,
    UserServiceErrorDetail
)
from Service.UserService.app.models.UserAccountDatabaseSQLParameterSchema import (
    UserStatus,
    TableUsersUpdateWhereSchema,
    TableUsersUpdateSetSchema,
    TableUserLoginLogsInsertSchema
)


class UserAuthService:
    """
    用户认证服务类
    负责处理所有与用户认证相关的业务逻辑，包括登录验证、密码加密、JWT令牌管理等
    """
    
    def __init__(self, 
                 user_core_db_agent: UserCoreDBAgent,
                 user_profile_db_agent: UserProfileDBAgent,
                 user_login_logs_db_agent: UserLoginLogsDBAgent,
                 jwt_secret_key: str,
                 jwt_algorithm: str = "HS256",
                 jwt_expiration: int = 3600,
                 logger: Optional[Logger] = None):
        # 步骤1: 设置数据库代理实例
        self.user_core_db_agent = user_core_db_agent
        self.user_profile_db_agent = user_profile_db_agent
        self.user_login_logs_db_agent = user_login_logs_db_agent
        
        # 步骤2: 设置JWT配置参数
        self.jwt_secret_key = jwt_secret_key
        self.jwt_algorithm = jwt_algorithm
        self.jwt_expiration = jwt_expiration
        
        # 步骤3: 初始化密码加密上下文
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # 步骤4: 设置日志器
        self.logger = logger
    
    def create_access_token(self, user_id: int) -> str:
        """
        创建JWT访问令牌
        
        :param user_id: 用户ID
        :return: JWT令牌字符串
        """
        try:
            # 步骤1: 设置令牌过期时间（注意这里使用秒，不是分钟）
            expire = datetime.utcnow() + timedelta(seconds=self.jwt_expiration)
            
            # 步骤2: 构建JWT载荷
            payload = {
                "user_id": user_id,
                "exp": expire,
                "iat": datetime.utcnow()
            }
            
            # 步骤3: 编码JWT令牌
            encoded_jwt = jwt.encode(payload, self.jwt_secret_key, algorithm=self.jwt_algorithm)
            
            if self.logger:
                self.logger.info(f"JWT令牌创建成功 - 用户ID: {user_id}")
            return encoded_jwt
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"JWT令牌创建失败: {str(e)}")
            raise ValueError("Failed to create JWT token")
    
    def verify_token(self, token: str) -> int:
        """
        验证JWT令牌并返回用户ID
        
        :param token: JWT令牌字符串
        :return: 用户ID
        :raises ValueError: Token验证失败时抛出异常
        """
        try:
            # 步骤1: 解码并验证JWT令牌
            payload = jwt.decode(token, self.jwt_secret_key, algorithms=[self.jwt_algorithm])
            
            # 步骤2: 验证令牌是否包含用户ID
            user_id = payload.get("user_id")
            if user_id is None:
                if self.logger:
                    self.logger.warning("JWT令牌验证失败：缺少用户ID")
                raise ValueError("Missing user_id in token")
            
            if self.logger:
                self.logger.debug(f"JWT令牌验证成功 - 用户ID: {user_id}")
            return user_id
            
        except JWTError as e:
            if self.logger:
                self.logger.warning(f"JWT令牌验证失败: {str(e)}")
            raise ValueError("Invalid or expired token")
        except Exception as e:
            if self.logger:
                self.logger.error(f"JWT令牌验证过程中发生错误: {str(e)}")
            raise ValueError("Token verification failed")
    
    def hash_password(self, password: str) -> str:
        """
        对密码进行哈希加密
        
        :param password: 明文密码
        :return: 哈希后的密码
        """
        try:
            hashed = self.pwd_context.hash(password)
            if self.logger:
                self.logger.debug("密码哈希加密成功")
            return hashed
        except Exception as e:
            if self.logger:
                self.logger.error(f"密码哈希加密失败: {str(e)}")
            raise ValueError("Failed to hash password")
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        验证密码是否正确
        
        :param plain_password: 明文密码
        :param hashed_password: 哈希后的密码
        :return: 密码是否匹配
        """
        try:
            result = self.pwd_context.verify(plain_password, hashed_password)
            if self.logger:
                self.logger.debug(f"密码验证结果: {'成功' if result else '失败'}")
            return result
        except Exception as e:
            if self.logger:
                self.logger.error(f"密码验证过程中发生错误: {str(e)}")
            return False
    
    async def login(self, identifier: str, password: str, ip_address: str, 
                   agent: str, device: str, os: str) -> LoginResponse:
        """
        用户登录验证
        
        :param identifier: 用户标识符（用户名或邮箱）
        :param password: 密码
        :param ip_address: 客户端IP地址
        :param agent: 用户代理字符串
        :param device: 设备信息
        :param os: 操作系统信息
        :return: LoginResponse
        """
        operator = 'usr_login'
        
        # 步骤1: 查询用户信息
        try:
            result = await self.user_core_db_agent.fetch_user_id_and_password_hash_by_email_or_account(identifier=identifier)
        except Exception as e:
            if self.logger:
                self.logger.error(f"查询用户信息时发生数据库错误，用户标识: {identifier}: {e}")
            return LoginResponse(
                operator=operator,
                result=False,
                message="Database error occurred",
                err_code=UserServiceResponseErrorCode.DATABASE_ERROR,
                errors=[UserServiceErrorDetail(
                    code=UserServiceResponseErrorCode.DATABASE_ERROR,
                    message="Internal database error"
                )],
                data=None
            )

        # 步骤2: 验证用户是否存在
        if result is None:
            message = f"Login failed! User '{identifier}' does not exist"
            if self.logger:
                self.logger.info(f"登录失败：用户不存在 - {identifier}")
            return LoginResponse(
                operator=operator,
                result=False,
                message=message,
                err_code=UserServiceResponseErrorCode.ACCOUNT_NOT_FOUND,
                errors=[UserServiceErrorDetail(
                    code=UserServiceResponseErrorCode.ACCOUNT_NOT_FOUND,
                    message=message
                )],
                data=None
            )

        # 步骤3: 获取用户ID和存储的密码哈希
        user_id, stored_password_hash = result
        
        # 步骤4: 验证密码
        if not self.verify_password(password, stored_password_hash):
            if self.logger:
                self.logger.info(f"登录失败：密码错误 - {identifier}")
            
            # 记录失败的登录尝试
            try:
                await self.user_login_logs_db_agent.insert_login_log(
                    log_data=TableUserLoginLogsInsertSchema(
                        user_id=user_id,
                        ip_address=ip_address,
                        agent=agent,
                        device=device,
                        os=os,
                        login_success=False
                    )
                )
            except Exception as e:
                if self.logger:
                    self.logger.error(f"记录失败登录日志时发生错误，用户ID {user_id}: {e}")

            message = "Login failed! Invalid account or password"
            return LoginResponse(
                operator=operator,
                result=False,
                message=message,
                err_code=UserServiceResponseErrorCode.PASSWORD_INCORRECT,
                errors=[UserServiceErrorDetail(
                    code=UserServiceResponseErrorCode.PASSWORD_INCORRECT,
                    message=message
                )],
                data=None
            )

        # 步骤5: 生成访问令牌
        try:
            access_token = self.create_access_token(user_id=user_id)
        except Exception as e:
            if self.logger:
                self.logger.error(f"生成访问令牌失败，用户ID {user_id}: {e}")
            return LoginResponse(
                operator=operator,
                result=False,
                message="Failed to generate access token",
                err_code=UserServiceResponseErrorCode.UNKNOWN_ERROR,
                errors=[UserServiceErrorDetail(
                    code=UserServiceResponseErrorCode.UNKNOWN_ERROR,
                    message="Token generation failed"
                )],
                data=None
            )

        # 步骤6: 更新用户登录信息
        try:
            await self.user_core_db_agent.update_users(
                update_data=TableUsersUpdateSetSchema(
                    session_token=access_token,
                    last_login_ip=ip_address,
                    last_login_time=datetime.now()
                ),
                update_where=TableUsersUpdateWhereSchema(user_id=user_id)
            )
        except Exception as e:
            if self.logger:
                self.logger.warning(f"更新用户登录信息失败，用户ID {user_id}: {e}")
        
        # 步骤7: 记录成功登录日志
        try:
            await self.user_login_logs_db_agent.insert_login_log(
                log_data=TableUserLoginLogsInsertSchema(
                    user_id=user_id,
                    ip_address=ip_address,
                    agent=agent,
                    device=device,
                    os=os,
                    login_success=True
                )
            )
        except Exception as e:
            if self.logger:
                self.logger.error(f"记录成功登录日志失败，用户ID {user_id}: {e}")

        # 步骤8: 获取用户资料信息
        user_profile_info = None
        try:
            user_profile_info = await self.user_profile_db_agent.fetch_user_profile(user_id)
        except Exception as e:
            if self.logger:
                self.logger.warning(f"获取用户资料信息失败，用户ID {user_id}: {e}")
        
        # 步骤9: 构造返回数据
        login_data = LoginData(
            user_id=user_id,
            session_token=access_token,
            status=UserStatus.active.value,
            last_login_ip=ip_address,
            last_login_time=datetime.now(),
            profile_picture_url=user_profile_info.get("profile_picture_path") if user_profile_info else None,
            profile_picture_updated_at=user_profile_info.get("profile_picture_updated_at") if user_profile_info else None,
            signature=user_profile_info.get("signature") if user_profile_info else None
        )

        if self.logger:
            self.logger.info(f"用户登录成功 - {identifier} (用户ID: {user_id})")

        return LoginResponse(
            operator=operator,
            result=True,
            message="Login successful",
            data=login_data
        )
