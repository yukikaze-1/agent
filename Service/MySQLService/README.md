# MySQL微服务 (MySQLService)

## 项目概述

MySQL微服务是一个基于FastAPI的高性能数据库访问服务，提供了完整的MySQL数据库操作能力，包括连接管理、CRUD操作、事务支持等功能。该服务采用模块化设计，职责分离清晰，具有良好的可扩展性和可维护性。

### 主要特性

- **连接管理**: 支持多数据库连接的创建、管理和自动回收
- **CRUD操作**: 完整的增删改查操作支持
- **事务支持**: 支持静态事务和动态事务两种模式
- **错误处理**: 完善的错误处理机制和重试机制
- **日志记录**: 详细的操作日志记录和监控
- **服务注册**: 支持Consul服务注册与发现
- **健康检查**: 内置健康检查接口

## 项目结构

```
Service/MySQLService/
├── MySQLService.py          # 主服务类
├── main.py                  # 服务启动入口
├── config.yml              # 配置文件
├── .env                     # 环境变量配置
├── core/                    # 核心模块
│   ├── __init__.py         # 模块导出
│   ├── connection_manager.py    # 连接管理器
│   ├── database_operations.py   # 数据库操作管理器
│   ├── transaction_manager.py   # 事务管理器
│   ├── response_builder.py      # 响应构建器
│   └── service_app.py           # FastAPI应用
└── schema/                  # 数据模型
    ├── request.py          # 请求模型定义
    └── response.py         # 响应模型定义
```

## 核心模块

### 1. MySQLService (主服务类)

主服务类采用组合模式，将不同职责分配给专门的管理器：

- **MySQLConnectionManager**: 连接管理
- **DatabaseOperations**: CRUD操作  
- **TransactionManager**: 事务管理
- **MySQLServiceApp**: FastAPI应用和路由

### 2. 连接管理器 (MySQLConnectionManager)

负责MySQL连接的创建、管理和销毁：

- 支持连接池管理
- 连接自动重试机制
- 连接状态监控
- 连接ID生成和管理

### 3. 数据库操作管理器 (DatabaseOperations)

负责具体的数据库CRUD操作：

- **查询 (Query)**: 支持参数化查询，返回结构化数据
- **插入 (Insert)**: 支持单条和批量插入，返回受影响行数和自增ID
- **更新 (Update)**: 支持条件更新，返回受影响行数
- **删除 (Delete)**: 支持条件删除，返回受影响行数

### 4. 事务管理器 (TransactionManager)

支持两种事务模式：

#### 静态事务
- 一次性提交多个SQL语句
- 自动事务边界管理
- 原子性保证

#### 动态事务
- 支持多步骤事务操作
- 会话ID管理
- 手动提交/回滚控制

### 5. 响应构建器 (ResponseBuilder)

统一的响应构建逻辑：

- 标准化响应格式
- 错误码管理
- 详细错误信息构建

## API接口

### 连接管理

#### 连接数据库
```
POST /database/mysql/connect
```

请求体:
```json
{
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "password",
    "database": "testdb",
    "charset": "utf8mb4"
}
```

### CRUD操作

#### 查询数据
```
POST /database/mysql/query
```

#### 插入数据
```
POST /database/mysql/insert
```

#### 更新数据
```
POST /database/mysql/update
```

#### 删除数据
```
POST /database/mysql/delete
```

### 事务操作

#### 静态事务
```
POST /database/mysql/transaction/static
```

#### 动态事务
```
POST /database/mysql/transaction/dynamic/start     # 开始事务
POST /database/mysql/transaction/dynamic/execute  # 执行SQL
POST /database/mysql/transaction/dynamic/commit   # 提交事务
POST /database/mysql/transaction/dynamic/rollback # 回滚事务
```

### 健康检查
```
GET /health
```

## 配置说明

### config.yml
```yaml
MySQLService:
  host: 127.0.0.1
  port: 20050
  consul_url: "http://127.0.0.1:8500"
  health_check_url: "http://127.0.0.1:20050/health"
  service_name: "MySQLService"
  service_id: "MySQLService-127.0.0.1:20050"
```

### .env
```bash
MYSQL_SERVICE_CONFIG_PATH="/path/to/config.yml"
```

## 安装和运行

### 依赖安装
```bash
pip install fastapi uvicorn pymysql python-dotenv pydantic httpx
```

### 启动服务

#### 方式一：直接运行
```bash
python main.py
```

#### 方式二：使用MySQLService类
```python
from Service.MySQLService.MySQLService import MySQLService

service = MySQLService()
service.run(host="0.0.0.0", port=20050)
```

## 特性详解

### 错误处理机制

- **连接错误**: 自动重试机制，最多重试3次
- **SQL错误**: 详细错误信息记录和返回
- **事务错误**: 自动回滚机制
- **参数验证**: 基于Pydantic的严格参数校验

### 重试机制

使用装饰器实现的智能重试：
- 指数退避算法
- 可配置重试次数
- 异常类型过滤

### 日志系统

- 分级日志记录 (DEBUG, INFO, WARNING, ERROR)
- 操作审计日志
- 性能监控日志
- 日志文件自动轮转

### 安全特性

- SQL注入防护 (参数化查询)
- 连接超时控制
- 操作权限验证
- 输入数据校验

## 监控和运维

### 健康检查

服务提供健康检查接口，返回：
- 服务状态
- 活跃连接数
- 活跃事务数
- 服务版本信息

### 性能指标

- 连接池使用率
- 查询响应时间
- 事务成功率
- 错误率统计

## 使用示例

### Python客户端示例

```python
import httpx
import asyncio

async def example():
    async with httpx.AsyncClient() as client:
        # 连接数据库
        connect_response = await client.post(
            "http://127.0.0.1:20050/database/mysql/connect",
            json={
                "host": "127.0.0.1",
                "port": 3306,
                "user": "root",
                "password": "password",
                "database": "testdb",
                "charset": "utf8mb4"
            }
        )
        
        connection_id = connect_response.json()["data"]["connection_id"]
        
        # 查询数据
        query_response = await client.post(
            "http://127.0.0.1:20050/database/mysql/query",
            json={
                "connection_id": connection_id,
                "sql": "SELECT * FROM users WHERE id = %s",
                "sql_args": [1]
            }
        )
        
        print(query_response.json())

asyncio.run(example())
```

## 版本信息

- **当前版本**: 0.2
- **作者**: yomu
- **最后更新**: 2025年6月29日

## 更新日志

### v0.2 (2025/6/29)
- 重构为模块化设计
- 添加事务管理功能
- 改进错误处理机制
- 优化连接管理
- 添加响应构建器

### v0.1
- 初始版本
- 基础CRUD功能
- 简单连接管理

## 注意事项

1. **连接管理**: 请及时关闭不需要的连接以避免连接泄露
2. **事务使用**: 动态事务需要手动管理生命周期
3. **错误处理**: 建议在客户端实现重试机制
4. **性能优化**: 对于高并发场景，建议配置合适的连接池大小
5. **安全性**: 生产环境中请使用安全的数据库连接参数

## 故障排除

### 常见问题

1. **连接失败**: 检查数据库服务状态和网络连接
2. **权限错误**: 确认数据库用户权限配置
3. **超时错误**: 调整连接和查询超时参数
4. **内存泄露**: 检查连接是否正确关闭

### 调试模式

启用调试日志：
```python
import logging
logging.getLogger("MySQLService").setLevel(logging.DEBUG)
```

## 技术支持

如有问题或建议，请查看日志文件或联系开发团队。

---

**注意**: 本服务仍在持续开发中，部分功能可能会在后续版本中发生变化。
