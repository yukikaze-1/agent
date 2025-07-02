# MCP服务框架项目结构

```
MCPService/
├── MCPService.py           # 主框架文件
├── test_service.py         # 测试脚本
├── requirements.txt        # 依赖列表
├── README.md              # 使用文档
└── examples/              # 示例文件夹（可选）
    ├── simple_service.py
    ├── advanced_service.py
    └── production_service.py
```

## 核心组件说明

### 1. BaseMCPService 基类
- 抽象基类，定义了MCP服务的标准结构
- 自动发现和注册装饰器标记的方法
- 提供生命周期管理（setup/teardown）
- 统一的运行接口

### 2. 装饰器系统
- `@mcp_tool()`: 注册工具函数
- `@mcp_resource()`: 注册资源函数  
- `@mcp_prompt()`: 注册提示函数
- 约定式注册：`tool_*` 方法自动注册为工具

### 3. 内置服务示例
- `DatabaseService`: 数据库操作服务
- `FileProcessingService`: 文件处理服务
- `MathService`: 数学计算服务

### 4. 管理工具
- `MultiServiceManager`: 多服务管理器
- `create_service()`: 服务工厂函数

## 技术特性

### ✅ 已实现功能
- [x] 面向对象的服务封装
- [x] 自动工具/资源/提示注册
- [x] 生命周期管理
- [x] 多传输协议支持（stdio/sse/streamable-http）
- [x] Context上下文传递
- [x] 类型安全的装饰器
- [x] 约定优于配置
- [x] 多服务管理
- [x] 错误处理和资源清理

### 🚀 设计优势
1. **开发效率**: 用类组织相关功能，代码更清晰
2. **可维护性**: 统一的注册机制和生命周期管理
3. **可扩展性**: 通过继承轻松创建新服务
4. **生产就绪**: 支持HTTP部署和多服务管理

### 📝 使用模式

#### 简单服务
```python
class MyService(BaseMCPService):
    def setup(self): pass
    
    @mcp_tool()
    async def my_tool(self, ctx: Context): pass
```

#### 复杂服务
```python
class AdvancedService(BaseMCPService):
    def __init__(self):
        self.database = None
        super().__init__(name="高级服务")
    
    def setup(self):
        self.database = connect_db()
    
    def teardown(self):
        if self.database:
            self.database.close()
    
    @mcp_tool()
    async def complex_operation(self, ctx: Context):
        # 使用self.database等实例属性
        pass
```

### 🔧 部署方式

#### 开发模式
```bash
python MCPService.py math stdio
```

#### 生产模式  
```bash
# HTTP服务
python MCPService.py database streamable-http

# 多实例部署
python MCPService.py file streamable-http &
python MCPService.py math streamable-http --port 8002 &
```

#### 容器化部署
```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "MCPService.py", "database", "streamable-http"]
```

## 下一步扩展方向

### 可能的增强功能
1. **配置管理**: 支持配置文件和环境变量
2. **插件系统**: 动态加载服务模块
3. **监控集成**: 健康检查、指标收集
4. **认证授权**: OAuth/JWT支持
5. **中间件系统**: 请求/响应拦截器
6. **服务发现**: Consul/etcd集成
7. **负载均衡**: 多实例支持
8. **日志集成**: 结构化日志输出

这个框架为MCP服务开发提供了一个强大而灵活的基础，让开发者可以专注于业务逻辑而不是底层协议细节。
