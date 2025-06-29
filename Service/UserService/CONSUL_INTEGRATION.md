# UserService Consul 集成说明

## 概述

已为新版本的UserService添加了完整的Consul服务注册和发现功能，参考了UserServiceRefactored.py中的实现。

## 新增功能

### 1. Consul服务注册
- ✅ 服务启动时自动注册到Consul
- ✅ 自动健康检查配置
- ✅ 服务关闭时自动注销
- ✅ 错误处理（Consul故障不影响服务启动）

### 2. 配置增强
- ✅ 支持环境变量配置
- ✅ 自动生成服务ID和健康检查URL
- ✅ Consul URL自动添加协议前缀

### 3. 健康检查
- ✅ 提供 `/health` 端点
- ✅ 返回服务状态和版本信息
- ✅ Consul自动监控服务健康状态

## 配置说明

### 环境变量 (.env)
```bash
# UserService基本配置
HOST=127.0.0.1
PORT=20010
CONSUL_URL=http://127.0.0.1:8500
SERVICE_ID=UserService-127.0.0.1:20010
HEALTH_CHECK_URL=http://127.0.0.1:20010/health

# JWT配置
JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600
```

### YAML配置 (config.yml)
```yaml
UserService:
  host: 127.0.0.1
  port: 20010
  consul_url: "http://127.0.0.1:8500"
  service_name: "UserService"
  service_id: "UserService-127.0.0.1:20010"
  health_check_url: "http://127.0.0.1:20010/health"
```

## 核心实现

### 1. 配置类增强 (config.py)
```python
class Settings:
    def __init__(self):
        # Consul配置
        self.consul_url = os.getenv("CONSUL_URL", "http://127.0.0.1:8500")
        self.service_id = os.getenv("SERVICE_ID", f"{self.service_name}-{self.host}:{self.port}")
        self.health_check_url = os.getenv("HEALTH_CHECK_URL", f"http://{self.host}:{self.port}/health")
```

### 2. 生命周期管理 (main.py)
```python
@asynccontextmanager
async def lifespan(self, app: FastAPI):
    # 启动时
    try:
        await register_service_to_consul(
            consul_url=consul_url,
            client=self.client,
            logger=self.logger,
            service_name=settings.service_name,
            service_id=settings.service_id,
            address=settings.host,
            port=settings.port,
            tags=tags,
            health_check_url=settings.health_check_url
        )
    except Exception as e:
        # 错误处理，不影响服务启动
        
    yield
    
    # 关闭时
    try:
        await unregister_service_from_consul(
            consul_url=consul_url,
            client=self.client,
            logger=self.logger,
            service_id=settings.service_id
        )
    except Exception as e:
        # 错误处理
```

## 启动方式

### 1. 直接运行
```bash
cd /home/yomu/agent/Service/UserService
python app/main.py
```

### 2. 模块方式
```bash
cd /home/yomu/agent
python -m Service.UserService.app.main
```

### 3. 使用uvicorn
```bash
cd /home/yomu/agent/Service/UserService
uvicorn app.main:app --host 127.0.0.1 --port 20010
```

## 验证方法

### 1. 检查服务状态
```bash
curl http://127.0.0.1:20010/health
```

### 2. 检查Consul注册
```bash
curl http://127.0.0.1:8500/v1/catalog/service/UserService
```

### 3. 运行测试
```bash
python test_consul_integration.py
```

## 注意事项

1. **Consul依赖**: 确保Consul服务器正在运行
   ```bash
   consul agent -dev
   ```

2. **端口冲突**: 确保端口20010未被占用

3. **网络配置**: 确保服务器可以访问Consul（默认8500端口）

4. **错误处理**: 即使Consul不可用，服务也能正常启动，只是没有服务发现功能

## 与旧版本的对比

| 功能 | 旧版本 | 新版本 |
|------|--------|--------|
| Consul注册 | ❌ | ✅ |
| 健康检查 | ✅ | ✅ |
| 配置管理 | 基础 | 增强 |
| 错误处理 | 基础 | 完善 |
| 生命周期管理 | 基础 | 完整 |

## 日志输出示例

```
INFO:UserService:正在启动 UserService v1.0.0
INFO:UserService:HTTP客户端已初始化
INFO:UserService:所有服务已初始化
INFO:UserService:数据库连接已初始化
INFO:UserService:Registering service to Consul...
INFO:UserService:Service registered to Consul successfully
INFO:UserService:UserService已成功启动 127.0.0.1:20010
```

现在UserService具备了完整的Consul集成功能，可以在微服务架构中实现自动服务发现和健康监控。
