# MCP服务框架

这是一个基于FastMCP的面向对象服务框架，让你可以用类的方式组织和管理MCP工具、资源和提示。

## 特性

- 🚀 **面向对象设计**：用类来组织相关的工具和逻辑
- 🔧 **自动注册**：通过装饰器或命名约定自动注册MCP功能
- 🎯 **生命周期管理**：统一的初始化和清理流程
- 📦 **多服务支持**：可以同时管理多个不同的MCP服务
- 🛡️ **类型安全**：完整的类型注解支持

## 快速开始

### 1. 创建基础服务

```python
from MCPService import BaseMCPService, mcp_tool, Context

class MyService(BaseMCPService):
    def __init__(self):
        super().__init__(
            name="我的服务",
            instructions="服务描述"
        )
    
    def setup(self):
        """初始化逻辑"""
        print("服务初始化")
    
    @mcp_tool(title="问候工具")
    async def greet(self, name: str, ctx: Context) -> str:
        """问候用户"""
        await ctx.info(f"问候用户: {name}")
        return f"Hello, {name}!"

# 运行服务
service = MyService()
service.run()
```

### 2. 使用不同的传输方式

```python
# stdio模式（默认，用于Claude Desktop等）
service.run(transport="stdio")

# HTTP模式（用于Web集成）
service.run(transport="streamable-http", host="0.0.0.0", port=8000)

# SSE模式（Server-Sent Events）
service.run(transport="sse", host="0.0.0.0", port=8001)
```

## 装饰器使用

### @mcp_tool - 工具装饰器

```python
@mcp_tool(
    name="calculate_sum",      # 工具名称
    title="数字求和",          # 显示标题
    description="计算数字列表的总和",  # 详细描述
    structured_output=True     # 结构化输出
)
async def calculate_sum(self, numbers: List[int], ctx: Context) -> Dict[str, Any]:
    total = sum(numbers)
    await ctx.info(f"计算 {len(numbers)} 个数字的总和")
    return {"sum": total, "count": len(numbers)}
```

### @mcp_resource - 资源装饰器

```python
@mcp_resource(
    uri="resource://config",
    title="服务配置",
    description="获取服务配置信息",
    mime_type="application/json"
)
def get_config(self) -> str:
    import json
    config = {"version": "1.0", "name": self.name}
    return json.dumps(config)

# 模板资源（带参数）
@mcp_resource(
    uri="resource://user/{user_id}",
    title="用户信息"
)
def get_user_info(self, user_id: str) -> str:
    return f"用户 {user_id} 的信息"
```

### @mcp_prompt - 提示装饰器

```python
@mcp_prompt(
    name="analyze_data",
    title="数据分析提示"
)
def data_analysis_prompt(self, data_type: str) -> List[Dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": "你是数据分析专家"
        },
        {
            "role": "user", 
            "content": f"请分析这个{data_type}数据"
        }
    ]
```

### 约定优于配置

以 `tool_` 开头的方法会自动注册为工具：

```python
async def tool_add(self, a: float, b: float, ctx: Context) -> float:
    """加法运算 - 自动注册为名为 'add' 的工具"""
    return a + b

async def tool_multiply(self, a: float, b: float, ctx: Context) -> float:
    """乘法运算 - 自动注册为名为 'multiply' 的工具"""
    return a * b
```

## Context上下文对象

Context提供了丰富的MCP功能：

```python
async def my_tool(self, data: str, ctx: Context) -> str:
    # 日志记录
    await ctx.info("开始处理")
    await ctx.debug("调试信息")
    await ctx.warning("警告信息")
    await ctx.error("错误信息")
    
    # 进度报告
    await ctx.report_progress(50, 100, "处理中...")
    
    # 读取资源
    config = await ctx.read_resource("resource://config")
    
    # 用户交互
    from pydantic import BaseModel
    class UserChoice(BaseModel):
        confirmed: bool
    
    choice = await ctx.elicit("是否继续？", UserChoice)
    
    # 获取请求信息
    request_id = ctx.request_id
    client_id = ctx.client_id
    
    return "处理完成"
```

## 内置服务示例

### 数据库服务
```python
service = DatabaseService()
service.run(transport="streamable-http", port=8001)
```

### 文件处理服务
```python
service = FileProcessingService() 
service.run(transport="streamable-http", port=8002)
```

### 数学计算服务
```python
service = MathService()
service.run()  # 默认stdio模式
```

## 多服务管理

```python
from MCPService import MultiServiceManager, DatabaseService, FileProcessingService

# 创建管理器
manager = MultiServiceManager()

# 添加服务
manager.add_service("database", DatabaseService())
manager.add_service("file", FileProcessingService())

# 运行特定服务
manager.run_service("database", transport="streamable-http", port=8001)
```

## 命令行使用

```bash
# 运行特定服务
python MCPService.py database stdio
python MCPService.py file streamable-http
python MCPService.py math sse

# 查看可用服务
python MCPService.py
```

## 生命周期管理

```python
class MyService(BaseMCPService):
    def setup(self):
        """服务启动时调用"""
        self.db = connect_database()
        print("数据库连接建立")
    
    def teardown(self):
        """服务关闭时调用"""
        if hasattr(self, 'db'):
            self.db.close()
        print("资源清理完成")
```

## 错误处理

服务框架会自动处理常见错误：

- `KeyboardInterrupt`：优雅关闭服务
- 其他异常：记录错误并重新抛出
- 资源清理：确保 `teardown()` 被调用

## 最佳实践

1. **明确的工具描述**：为每个工具提供清晰的标题和描述
2. **适当的日志记录**：使用Context记录重要操作
3. **进度报告**：对于长时间运行的操作报告进度
4. **错误处理**：妥善处理异常并提供有用的错误信息
5. **资源管理**：在`setup()`和`teardown()`中管理资源

## 扩展示例

```python
class AdvancedService(BaseMCPService):
    def __init__(self):
        super().__init__(
            name="高级服务",
            instructions="展示高级功能的服务",
            host="0.0.0.0",
            port=8000
        )
        self.cache = {}
    
    def setup(self):
        """初始化缓存和其他资源"""
        print("初始化高级服务")
    
    @mcp_tool(title="缓存数据")
    async def cache_data(self, key: str, value: str, ctx: Context) -> str:
        """将数据存储到缓存"""
        self.cache[key] = value
        await ctx.info(f"缓存数据: {key} = {value}")
        return f"已缓存 {key}"
    
    @mcp_tool(title="获取缓存")
    async def get_cached_data(self, key: str, ctx: Context) -> str:
        """从缓存获取数据"""
        if key in self.cache:
            value = self.cache[key]
            await ctx.info(f"缓存命中: {key}")
            return value
        else:
            await ctx.warning(f"缓存未命中: {key}")
            return f"Key '{key}' not found in cache"
    
    @mcp_resource(uri="resource://cache_stats")
    def get_cache_stats(self) -> str:
        """获取缓存统计"""
        import json
        stats = {
            "total_keys": len(self.cache),
            "keys": list(self.cache.keys())
        }
        return json.dumps(stats, ensure_ascii=False)
```

这个框架让MCP服务开发变得更加结构化和易于维护！
