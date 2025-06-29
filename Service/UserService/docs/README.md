# UserService - 用户管理微服务

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📖 项目简介

UserService 是一个基于 FastAPI 的现代化用户管理微服务，提供完整的用户认证、账户管理、个人资料管理和文件管理功能。项目采用分层架构设计，具有高可维护性、可扩展性和安全性。

## 🏗️ 架构设计

### 分层架构

```
app/
├── main.py                    # FastAPI 应用入口点
├── core/                      # 核心配置层
│   └── config.py             # 应用配置管理
├── api/                       # API 路由层
│   └── v1/
│       └── user_controller.py # HTTP 请求控制器
├── services/                  # 业务逻辑层
│   ├── user_auth_service.py   # 用户认证服务
│   ├── user_account_service.py # 账户管理服务
│   ├── user_profile_service.py # 用户资料服务
│   └── user_file_service.py   # 文件管理服务
├── db/                        # 数据访问层
│   ├── BaseDBAgent.py         # 数据库基础代理
│   ├── UserCoreDBAgent.py     # 用户核心数据代理
│   ├── UserProfileDBAgent.py  # 用户资料数据代理
│   ├── UserDatabaseManager.py # 数据库管理器
│   └── ...                   # 其他专用数据代理
├── models/                    # 数据模型层
│   ├── UserServiceRequestType.py  # 请求数据模型
│   ├── UserServiceResponseType.py # 响应数据模型
│   └── UserAccountDatabaseSQLParameterSchema.py # 数据库参数模型
└── clients/                   # 外部服务客户端
    └── EnvironmentManagerClient.py # 环境管理器客户端
```

### 设计原则

- **🎯 单一职责原则**: 每个服务类专注于单一业务领域
- **🔌 依赖注入**: 通过依赖注入提升可测试性和灵活性  
- **📚 分层架构**: API → 服务 → 数据层的清晰分离
- **🔒 安全优先**: JWT 认证、密码加密、输入验证
- **📊 可观测性**: 详细日志记录和错误跟踪

## ✨ 核心功能

### 🔐 用户认证服务 (UserAuthService)

- **JWT Token 管理**: 生成、验证、刷新访问令牌
- **密码安全**: BCrypt 哈希加密和验证
- **登录管理**: 用户登录认证和登录日志记录
- **会话管理**: 安全的用户会话处理

**核心方法**:
```python
async def login(username: str, password: str) -> LoginResponse
async def create_access_token(user_data: dict) -> str
async def verify_token(token: str) -> dict
async def hash_password(password: str) -> str
async def verify_password(plain_password: str, hashed_password: str) -> bool
```

### 👤 账户管理服务 (UserAccountService)  

- **用户注册**: 新用户账户创建和验证
- **账户注销**: 安全的账户删除流程
- **密码管理**: 密码修改和重置功能
- **账户状态**: 账户激活、禁用状态管理

**核心方法**:
```python
async def register(user_data: RegisterRequest) -> RegisterResponse
async def unregister(user_id: int, password: str) -> UnregisterResponse
async def change_password(user_id: int, old_password: str, new_password: str) -> ModifyPasswordResponse
```

### 👨‍💼 用户资料服务 (UserProfileService)

- **个人资料**: 用户基本信息管理
- **用户设置**: 个性化设置配置
- **通知偏好**: 通知设置和偏好管理
- **数据验证**: 输入数据格式验证

**核心方法**:
```python
async def modify_profile(user_id: int, profile_data: ModifyProfileRequest) -> ModifyProfileResponse
async def modify_settings(user_id: int, settings_data: ModifySettingRequest) -> ModifySettingResponse
async def modify_notification_settings(user_id: int, notification_data: ModifyNotificationSettingsRequest) -> ModifyNotificationSettingsResponse
```

### 📁 文件管理服务 (UserFileService)

- **文件上传**: 安全的文件上传处理
- **存储管理**: 文件存储和组织
- **访问控制**: 基于用户权限的文件访问
- **文件验证**: 文件类型和大小验证

**核心方法**:
```python
async def upload_file(user_id: int, file: UploadFile) -> UploadFileResponse
```

## 🚀 快速开始

### 环境要求

- Python 3.11+
- FastAPI 0.104+
- MySQL 8.0+
- Redis (可选，用于缓存)

### 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd UserService

# 安装 Python 依赖
pip install -r requirements.txt
```

### 配置环境

1. **复制环境变量文件**:
```bash
cp config/.env.example config/.env
```

2. **编辑配置文件** `config/.env`:
```properties
# 服务配置
HOST=127.0.0.1
PORT=20010

# JWT 配置
JWT_SECRET_KEY=your_super_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600

# 数据库配置
MYSQL_SERVICE_URL=http://127.0.0.1:20001

# 文件存储配置
UPLOAD_MAX_SIZE=1073741824
FILE_STORAGE_PATH=/home/yomu/agent/Users/Files

# 日志配置
LOG_LEVEL=INFO
LOG_PATH=InternalModule
```

3. **配置数据库连接** `config/config.yml`:
```yaml
mysql_host: "localhost"
mysql_port: 3306
mysql_user: "your_username"
mysql_password: "your_password"
database: "user_service_db"
charset: "utf8mb4"
```

### 启动服务

#### 方式一：直接运行
```bash
cd /home/yomu/agent
python -m Service.UserService.app.main
```

#### 方式二：使用 Uvicorn
```bash
cd /home/yomu/agent
uvicorn Service.UserService.app.main:create_app --factory --host 0.0.0.0 --port 20010
```

#### 方式三：开发模式
```bash
cd /home/yomu/agent
uvicorn Service.UserService.app.main:create_app --factory --reload --host 0.0.0.0 --port 20010
```

### 验证安装

运行测试脚本验证服务状态：

```bash
# 导入测试
python simple_test.py

# 启动测试  
python test_startup.py
```

## 📡 API 接口

### 认证相关

| 方法 | 端点 | 描述 | 认证要求 |
|------|------|------|----------|
| `POST` | `/usr/login` | 用户登录 | ❌ |
| `POST` | `/usr/register` | 用户注册 | ❌ |

### 账户管理

| 方法 | 端点 | 描述 | 认证要求 |
|------|------|------|----------|
| `POST` | `/usr/change_pwd` | 修改密码 | ✅ |
| `POST` | `/usr/unregister` | 注销账户 | ✅ |

### 用户资料

| 方法 | 端点 | 描述 | 认证要求 |
|------|------|------|----------|
| `POST` | `/usr/modify_profile` | 修改个人资料 | ✅ |
| `POST` | `/usr/modify_settings` | 修改用户设置 | ✅ |
| `POST` | `/usr/modify_notifications` | 修改通知设置 | ✅ |

### 文件管理

| 方法 | 端点 | 描述 | 认证要求 |
|------|------|------|----------|
| `POST` | `/usr/upload_file` | 文件上传 | ✅ |

### 系统监控

| 方法 | 端点 | 描述 | 认证要求 |
|------|------|------|----------|
| `GET` | `/health` | 健康检查 | ❌ |

### 请求示例

#### 用户登录
```bash
curl -X POST "http://localhost:20010/usr/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpassword"
  }'
```

#### 用户注册
```bash
curl -X POST "http://localhost:20010/usr/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "newpassword", 
    "email": "user@example.com",
    "display_name": "New User"
  }'
```

## 🔧 开发指南

### 项目结构说明

```
Service/UserService/
├── app/                          # 主应用目录
│   ├── main.py                   # FastAPI 应用工厂
│   ├── api/v1/                   # API 路由版本管理
│   ├── core/                     # 核心配置和工具
│   ├── services/                 # 业务逻辑服务层
│   ├── db/                       # 数据访问层
│   ├── models/                   # 数据模型和 Schema
│   └── clients/                  # 外部服务客户端
├── config/                       # 配置文件
├── tests/                        # 测试代码
├── docs/                         # 项目文档  
├── legacy/                       # 遗留代码备份
├── .gitignore                    # Git 忽略规则
└── README.md                     # 项目说明文档
```

### 添加新功能

1. **创建新的服务类** (在 `app/services/`):
```python
from Service.UserService.app.db.BaseDBAgent import BaseDBAgent

class NewFeatureService:
    def __init__(self, db_agent: BaseDBAgent, logger):
        self.db_agent = db_agent
        self.logger = logger
    
    async def new_operation(self, data):
        # 实现业务逻辑
        pass
```

2. **添加 API 端点** (在 `app/api/v1/user_controller.py`):
```python
@router.post("/new-endpoint")
async def new_endpoint(request: NewRequest):
    # 调用服务层
    result = await service.new_operation(request.data)
    return result
```

3. **定义数据模型** (在 `app/models/`):
```python
from pydantic import BaseModel

class NewRequest(BaseModel):
    field1: str
    field2: int

class NewResponse(BaseModel):
    result: str
    success: bool
```

### 数据库操作

项目使用自定义的数据库代理层，继承自 `BaseDBAgent`:

```python
# 查询操作
result = await self.db_agent.query_record(
    table="users",
    where_conditions=["username = %s"],
    where_values=[username]
)

# 插入操作  
insert_id = await self.db_agent.insert_record(
    table="users",
    insert_data=user_data,
    success_msg="用户创建成功",
    error_msg="用户创建失败"
)

# 更新操作
success = await self.db_agent.update_record(
    table="users", 
    update_data=update_data,
    update_where=where_condition,
    success_msg="更新成功",
    error_msg="更新失败"
)
```

### 测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试
python -m pytest tests/test_auth_service.py

# 运行测试并生成覆盖率报告
python -m pytest --cov=app tests/
```

## 🐳 Docker 部署

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 20010
CMD ["uvicorn", "Service.UserService.app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "20010"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  userservice:
    build: .
    ports:
      - "20010:20010"
    environment:
      - MYSQL_SERVICE_URL=http://mysql-service:20001
      - JWT_SECRET_KEY=your_secret_key
    depends_on:
      - mysql
      
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: user_service_db
    ports:
      - "3306:3306"
```

## 📊 监控和日志

### 日志配置

项目使用结构化日志记录：

```python
# 日志记录示例
self.logger.info("用户登录成功", extra={
    "user_id": user_id,
    "ip_address": client_ip,
    "timestamp": datetime.now()
})

self.logger.error("数据库连接失败", extra={
    "error": str(exception),
    "operation": "user_login"
})
```

### 健康检查

```bash
# 检查服务状态
curl http://localhost:20010/health

# 预期响应
{
  "status": "healthy",
  "timestamp": "2025-06-29T12:00:00Z",
  "version": "1.0.0"
}
```

## 🔒 安全特性

- **JWT 认证**: 安全的令牌基础认证
- **密码加密**: BCrypt 哈希算法
- **输入验证**: Pydantic 模型验证
- **SQL 注入防护**: 参数化查询
- **CORS 配置**: 跨域请求控制
- **速率限制**: API 调用频率限制 (推荐添加)

## 🚀 性能优化

### 建议的优化措施

1. **数据库连接池**: 使用 SQLAlchemy 或 aiomysql 连接池
2. **Redis 缓存**: 缓存热点数据和会话信息
3. **异步处理**: 充分利用 FastAPI 的异步特性
4. **数据库索引**: 为常用查询字段添加索引
5. **压缩响应**: 启用 Gzip 压缩

### 性能监控

```python
# 添加中间件监控请求时间
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/new-feature`)
3. 提交更改 (`git commit -am 'Add new feature'`)
4. 推送到分支 (`git push origin feature/new-feature`)
5. 创建 Pull Request

### 代码规范

- 遵循 PEP 8 Python 代码规范
- 使用类型提示 (Type Hints)
- 编写文档字符串
- 添加单元测试
- 保持代码覆盖率 > 80%

## 📝 更新日志

### v1.0.0 (2025-06-29)
- ✨ 完成项目重构，采用标准 FastAPI 微服务架构
- 🔧 实现分层设计：API → 服务 → 数据层
- 🔐 完善 JWT 认证和安全机制
- 📚 添加完整的 API 文档
- 🐳 添加 Docker 支持
- ✅ 实现全面的单元测试

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 获取帮助

- **项目文档**: [docs/](docs/)
- **Issue 跟踪**: [GitHub Issues](https://github.com/your-repo/issues)
- **讨论区**: [GitHub Discussions](https://github.com/your-repo/discussions)

## 👥 团队

- **作者**: yomu
- **版本**: 1.0.0
- **维护状态**: 积极维护

---

*本项目是 Agent 系统的核心用户管理服务，为整个平台提供安全可靠的用户认证和管理功能。*活、禁用状态管理**核心方法**:```pythonasync def register(user_data: RegisterRequest) -> RegisterResponseasync def unregister(user_id: int, password: str) -> UnregisterResponseasync def change_password(user_id: int, old_password: str, new_password: str) -> ModifyPasswordResponse```### 👨‍💼 用户资料服务 (UserProfileService)- **个人资料**: 用户基本信息管理- **用户设置**: 个性化设置配置- **通知偏好**: 通知设置和偏好管理- **数据验证**: 输入数据格式验证**核心方法**:```pythonasync def modify_profile(user_id: int, profile_data: ModifyProfileRequest) -> ModifyProfileResponseasync def modify_settings(user_id: int, settings_data: ModifySettingRequest) -> ModifySettingResponseasync def modify_notification_settings(user_id: int, notification_data: ModifyNotificationSettingsRequest) -> ModifyNotificationSettingsResponse```### 📁 文件管理服务 (UserFileService)- **文件上传**: 安全的文件上传处理- **存储管理**: 文件存储和组织- **访问控制**: 基于用户权限的文件访问- **文件验证**: 文件类型和大小验证**核心方法**:```pythonasync def upload_file(user_id: int, file: UploadFile) -> UploadFileResponse```## 🚀 快速开始### 环境要求- Python 3.11+- FastAPI 0.104+- MySQL 8.0+- Redis (可选，用于缓存)### 安装依赖```bash# 克隆项目git clone <repository-url>cd UserService# 安装 Python 依赖pip install -r requirements.txt```### 配置环境1. **复制环境变量文件**:```bashcp config/.env.example config/.env```2. **编辑配置文件** `config/.env`:```properties# 服务配置HOST=127.0.0.1PORT=20010# JWT 配置JWT_SECRET_KEY=your_super_secret_keyJWT_ALGORITHM=HS256JWT_EXPIRATION=3600# 数据库配置MYSQL_SERVICE_URL=http://127.0.0.1:20001# 文件存储配置UPLOAD_MAX_SIZE=1073741824FILE_STORAGE_PATH=/home/yomu/agent/Users/Files# 日志配置LOG_LEVEL=INFO
LOG_PATH=InternalModule
```

3. **配置数据库连接** `config/config.yml`:
```yaml
mysql_host: "localhost"
mysql_port: 3306
mysql_user: "your_username"
mysql_password: "your_password"
database: "user_service_db"
charset: "utf8mb4"
```

### 启动服务

#### 方式一：直接运行
```bash
cd /home/yomu/agent
python -m Service.UserService.app.main
```

#### 方式二：使用 Uvicorn
```bash
cd /home/yomu/agent
uvicorn Service.UserService.app.main:create_app --factory --host 0.0.0.0 --port 20010
```

#### 方式三：开发模式
```bash
cd /home/yomu/agent
uvicorn Service.UserService.app.main:create_app --factory --reload --host 0.0.0.0 --port 20010
```

### 验证安装

运行测试脚本验证服务状态：

```bash
# 导入测试
python simple_test.py

# 启动测试  
python test_startup.py
```

## 📡 API 接口

### 认证相关

| 方法 | 端点 | 描述 | 认证要求 |
|------|------|------|----------|
| `POST` | `/usr/login` | 用户登录 | ❌ |
| `POST` | `/usr/register` | 用户注册 | ❌ |

### 账户管理

| 方法 | 端点 | 描述 | 认证要求 |
|------|------|------|----------|
| `POST` | `/usr/change_pwd` | 修改密码 | ✅ |
| `POST` | `/usr/unregister` | 注销账户 | ✅ |

### 用户资料

| 方法 | 端点 | 描述 | 认证要求 |
|------|------|------|----------|
| `POST` | `/usr/modify_profile` | 修改个人资料 | ✅ |
| `POST` | `/usr/modify_settings` | 修改用户设置 | ✅ |
| `POST` | `/usr/modify_notifications` | 修改通知设置 | ✅ |

### 文件管理

| 方法 | 端点 | 描述 | 认证要求 |
|------|------|------|----------|
| `POST` | `/usr/upload_file` | 文件上传 | ✅ |

### 系统监控

| 方法 | 端点 | 描述 | 认证要求 |
|------|------|------|----------|
| `GET` | `/health` | 健康检查 | ❌ |

### 请求示例

#### 用户登录
```bash
curl -X POST "http://localhost:20010/usr/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpassword"
  }'
```

#### 用户注册
```bash
curl -X POST "http://localhost:20010/usr/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "newpassword", 
    "email": "user@example.com",
    "display_name": "New User"
  }'
```

## 🔧 开发指南

### 项目结构说明

```
Service/UserService/
├── app/                          # 主应用目录
│   ├── main.py                   # FastAPI 应用工厂
│   ├── api/v1/                   # API 路由版本管理
│   ├── core/                     # 核心配置和工具
│   ├── services/                 # 业务逻辑服务层
│   ├── db/                       # 数据访问层
│   ├── models/                   # 数据模型和 Schema
│   └── clients/                  # 外部服务客户端
├── config/                       # 配置文件
├── tests/                        # 测试代码
├── docs/                         # 项目文档  
├── legacy/                       # 遗留代码备份
├── .gitignore                    # Git 忽略规则
└── README.md                     # 项目说明文档
```

### 添加新功能

1. **创建新的服务类** (在 `app/services/`):
```python
from Service.UserService.app.db.BaseDBAgent import BaseDBAgent

class NewFeatureService:
    def __init__(self, db_agent: BaseDBAgent, logger):
        self.db_agent = db_agent
        self.logger = logger
    
    async def new_operation(self, data):
        # 实现业务逻辑
        pass
```

2. **添加 API 端点** (在 `app/api/v1/user_controller.py`):
```python
@router.post("/new-endpoint")
async def new_endpoint(request: NewRequest):
    # 调用服务层
    result = await service.new_operation(request.data)
    return result
```

3. **定义数据模型** (在 `app/models/`):
```python
from pydantic import BaseModel

class NewRequest(BaseModel):
    field1: str
    field2: int

class NewResponse(BaseModel):
    result: str
    success: bool
```

### 数据库操作

项目使用自定义的数据库代理层，继承自 `BaseDBAgent`:

```python
# 查询操作
result = await self.db_agent.query_record(
    table="users",
    where_conditions=["username = %s"],
    where_values=[username]
)

# 插入操作  
insert_id = await self.db_agent.insert_record(
    table="users",
    insert_data=user_data,
    success_msg="用户创建成功",
    error_msg="用户创建失败"
)

# 更新操作
success = await self.db_agent.update_record(
    table="users", 
    update_data=update_data,
    update_where=where_condition,
    success_msg="更新成功",
    error_msg="更新失败"
)
```

### 测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试
python -m pytest tests/test_auth_service.py

# 运行测试并生成覆盖率报告
python -m pytest --cov=app tests/
```

## 🐳 Docker 部署

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 20010
CMD ["uvicorn", "Service.UserService.app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "20010"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  userservice:
    build: .
    ports:
      - "20010:20010"
    environment:
      - MYSQL_SERVICE_URL=http://mysql-service:20001
      - JWT_SECRET_KEY=your_secret_key
    depends_on:
      - mysql
      
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: user_service_db
    ports:
      - "3306:3306"
```

## 📊 监控和日志

### 日志配置

项目使用结构化日志记录：

```python
# 日志记录示例
self.logger.info("用户登录成功", extra={
    "user_id": user_id,
    "ip_address": client_ip,
    "timestamp": datetime.now()
})

self.logger.error("数据库连接失败", extra={
    "error": str(exception),
    "operation": "user_login"
})
```

### 健康检查

```bash
# 检查服务状态
curl http://localhost:20010/health

# 预期响应
{
  "status": "healthy",
  "timestamp": "2025-06-29T12:00:00Z",
  "version": "1.0.0"
}
```

## 🔒 安全特性

- **JWT 认证**: 安全的令牌基础认证
- **密码加密**: BCrypt 哈希算法
- **输入验证**: Pydantic 模型验证
- **SQL 注入防护**: 参数化查询
- **CORS 配置**: 跨域请求控制
- **速率限制**: API 调用频率限制 (推荐添加)

## 🚀 性能优化

### 建议的优化措施

1. **数据库连接池**: 使用 SQLAlchemy 或 aiomysql 连接池
2. **Redis 缓存**: 缓存热点数据和会话信息
3. **异步处理**: 充分利用 FastAPI 的异步特性
4. **数据库索引**: 为常用查询字段添加索引
5. **压缩响应**: 启用 Gzip 压缩

### 性能监控

```python
# 添加中间件监控请求时间
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/new-feature`)
3. 提交更改 (`git commit -am 'Add new feature'`)
4. 推送到分支 (`git push origin feature/new-feature`)
5. 创建 Pull Request

### 代码规范

- 遵循 PEP 8 Python 代码规范
- 使用类型提示 (Type Hints)
- 编写文档字符串
- 添加单元测试
- 保持代码覆盖率 > 80%

## 📝 更新日志

### v1.0.0 (2025-06-29)
- ✨ 完成项目重构，采用标准 FastAPI 微服务架构
- 🔧 实现分层设计：API → 服务 → 数据层
- 🔐 完善 JWT 认证和安全机制
- 📚 添加完整的 API 文档
- 🐳 添加 Docker 支持
- ✅ 实现全面的单元测试

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 获取帮助

- **项目文档**: [docs/](docs/)
- **Issue 跟踪**: [GitHub Issues](https://github.com/your-repo/issues)
- **讨论区**: [GitHub Discussions](https://github.com/your-repo/discussions)

## 👥 团队

- **作者**: yomu
- **版本**: 1.0.0
- **维护状态**: 积极维护

---

*本项目是 Agent 系统的核心用户管理服务，为整个平台提供安全可靠的用户认证和管理功能。*
