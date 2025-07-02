from abc import ABC, abstractmethod
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import Context
from typing import Dict, Any, List, Literal
from functools import wraps

class BaseMCPService(ABC):
    """MCP服务基类"""
    
    def __init__(self, name: str, instructions: str | None = None, **settings):
        self.name = name
        self.instructions = instructions
        self.settings = settings
        
        # 核心组件
        self.mcp_server = FastMCP(
            name=name,
            instructions=instructions,
            **settings
        )
        
         # 状态管理
        self._initialized = False
        self._running = False
        
        # 自动发现和注册
        self._auto_register_methods()
        
    
    def _auto_register_methods(self):
        """自动注册类中的工具、资源和提示"""
         # 遍历类中的所有方法
        for attr_name in dir(self):
            if attr_name.startswith('_'):  # 跳过私有方法
                continue
                
            attr = getattr(self, attr_name)
            if not callable(attr):  # 只处理可调用对象
                continue
            
            # 检查方法是否有MCP装饰器标记
            if hasattr(attr, '_mcp_tool_config'):
                self._register_tool(attr_name, attr)
            elif hasattr(attr, '_mcp_resource_config'):
                self._register_resource(attr_name, attr)
            elif hasattr(attr, '_mcp_prompt_config'):
                self._register_prompt(attr_name, attr)
            elif attr_name.startswith('tool_'):  # 约定优于配置
                self._register_tool_by_convention(attr_name, attr)
    
    def _register_tool(self, name: str, method):
        """注册工具的具体实现"""
        config = method._mcp_tool_config
        
        # 注册到底层FastMCP
        self.mcp_server.add_tool(
            method,
            name=config.get('name', name),
            title=config.get('title'),
            description=config.get('description', method.__doc__),
            **{k: v for k, v in config.items() 
            if k not in ['name', 'title', 'description']}
        )
    
    def _register_tool_by_convention(self, name: str, method):
        """按约定注册工具（tool_开头的方法）"""
        tool_name = name[5:]  # 去掉 'tool_' 前缀
        self.mcp_server.add_tool(
            method,
            name=tool_name,
            title=method.__doc__.split('\n')[0] if method.__doc__ else f'{tool_name} tool',
            description=method.__doc__
        )
    
    def _register_resource(self, name: str, method):
        """注册资源的具体实现"""
        config = method._mcp_resource_config
        uri = config.get('uri', f"resource://{name}")
        
        # 检查是否为模板资源
        if '{' in uri and '}' in uri:
            # 模板资源处理
            self.mcp_server.resource(
                uri,
                name=config.get('name'),
                title=config.get('title'),
                description=config.get('description', method.__doc__),
                mime_type=config.get('mime_type')
            )(method)
        else:
            # 普通资源处理
            from mcp.server.fastmcp.resources import FunctionResource
            resource = FunctionResource.from_function(
                fn=method,
                uri=uri,
                name=config.get('name'),
                title=config.get('title'),
                description=config.get('description', method.__doc__),
                mime_type=config.get('mime_type')
            )
            self.mcp_server.add_resource(resource)
    
    def _register_prompt(self, name: str, method):
        """注册提示的具体实现"""
        config = method._mcp_prompt_config
        from mcp.server.fastmcp.prompts import Prompt
        
        prompt = Prompt.from_function(
            method,
            name=config.get('name', name),
            title=config.get('title'),
            description=config.get('description', method.__doc__)
        )
        self.mcp_server.add_prompt(prompt)
    
    
    @abstractmethod
    def setup(self):
        """子类实现具体的设置逻辑"""
        pass
    

    def teardown(self) -> None:
        """可选的清理逻辑"""
        pass
    
    
    
    def run(self, transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio", **kwargs):
        """完整的生命周期管理"""
        try:
            # 1. 初始化阶段
            if not self._initialized:
                self.setup()
                self._initialized = True
            
            # 2. 运行阶段
            self._running = True
            self.mcp_server.run(transport=transport, **kwargs)
            
        except KeyboardInterrupt:
            print(f"\n{self.name} 正在关闭...")
        except Exception as e:
            print(f"服务运行错误: {e}")
            raise
        finally:
            # 3. 清理阶段
            self._running = False
            self.teardown()

# 装饰器
def mcp_tool(
    name: str | None = None,
    title: str | None = None, 
    description: str | None = None,
    structured_output: bool = False,
    **kwargs
):
    """MCP工具装饰器
    
    设计要点：
    1. 不立即注册，只标记元数据
    2. 支持所有FastMCP的工具参数
    3. 保持方法的原始签名
    """
    def decorator(func):
        # 保存配置到方法上，而不是立即注册
        func._mcp_tool_config = {
            'name': name or func.__name__,
            'title': title,
            'description': description or func.__doc__,
            'structured_output': structured_output,
            **kwargs
        }
        
        # 返回原始函数，不修改行为
        return func
    
    return decorator



def mcp_resource(uri: str, name: str | None = None, title: str | None = None, description: str | None = None, mime_type: str | None = None, **kwargs):
    """MCP资源装饰器"""
    def decorator(func):
        func._mcp_resource_config = {
            'uri': uri,
            'name': name,
            'title': title,
            'description': description or func.__doc__,
            'mime_type': mime_type,
            **kwargs
        }
        return func
    return decorator

def mcp_prompt(name: str | None = None, title: str | None = None, description: str | None = None, **kwargs):
    """MCP提示装饰器"""
    def decorator(func):
        func._mcp_prompt_config = {
            'name': name or func.__name__,
            'title': title,
            'description': description or func.__doc__,
            **kwargs
        }
        return func
    return decorator




# 具体服务实现
class DatabaseService(BaseMCPService):
    def __init__(self):
        super().__init__(
            name="数据库服务",
            instructions="提供数据库查询和管理功能",
            host="0.0.0.0",
            port=8001
        )
        self.db_connection = None
    
    def setup(self):
        """初始化数据库连接"""
        # 这里初始化数据库连接
        self.db_connection = "mock_db_connection"
    
    @mcp_tool(
        name="query_database",
        title="数据库查询",
        description="执行SQL查询"
    )
    async def query_db(self, sql: str, ctx: Context) -> List[Dict[str, Any]]:
        """执行数据库查询"""
        await ctx.info(f"执行SQL查询: {sql}")
        await ctx.report_progress(50, 100, "执行查询...")
        
        # 模拟查询
        result = [{"id": 1, "name": "test"}]
        
        await ctx.report_progress(100, 100, "查询完成")
        await ctx.info(f"查询返回 {len(result)} 条记录")
        return result
    
    @mcp_tool(
        name="get_table_info",
        title="表信息",
        description="获取表结构信息"
    )
    async def get_table_info(self, table_name: str, ctx: Context) -> Dict[str, Any]:
        """获取表结构信息"""
        await ctx.info(f"获取表信息: {table_name}")
        return {
            "table_name": table_name,
            "columns": ["id", "name", "created_at"],
            "row_count": 100
        }

# 文件处理服务示例
class FileProcessingService(BaseMCPService):
    def __init__(self):
        super().__init__(
            name="文件处理服务",
            instructions="提供文件读取、写入和处理功能",
            host="0.0.0.0",
            port=8002
        )
    
    def setup(self):
        """初始化文件处理服务"""
        print("文件处理服务初始化完成")
    
    @mcp_tool(
        name="read_file",
        title="读取文件",
        description="读取指定路径的文件内容"
    )
    async def read_file(self, file_path: str, ctx: Context) -> str:
        """读取文件内容"""
        try:
            await ctx.info(f"开始读取文件: {file_path}")
            await ctx.report_progress(25, 100, "检查文件...")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            await ctx.report_progress(100, 100, "读取完成")
            await ctx.info(f"成功读取文件，长度: {len(content)} 字符")
            return content
        except Exception as e:
            await ctx.error(f"读取文件失败: {str(e)}")
            raise
    
    @mcp_tool(
        name="write_file",
        title="写入文件",
        description="将内容写入到指定文件"
    )
    async def write_file(self, file_path: str, content: str, ctx: Context) -> str:
        """写入文件"""
        try:
            await ctx.info(f"开始写入文件: {file_path}")
            await ctx.report_progress(50, 100, "写入中...")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            await ctx.report_progress(100, 100, "写入完成")
            await ctx.info(f"成功写入 {len(content)} 字符到文件")
            return f"文件 {file_path} 写入成功"
        except Exception as e:
            await ctx.error(f"写入文件失败: {str(e)}")
            raise
    
    @mcp_resource(
        uri="resource://file_stats",
        title="文件统计信息",
        description="获取文件系统统计信息"
    )
    def get_file_stats(self) -> str:
        """获取文件统计信息"""
        import os
        import json
        
        stats = {
            "current_directory": os.getcwd(),
            "total_files": len([f for f in os.listdir('.') if os.path.isfile(f)]),
            "total_directories": len([f for f in os.listdir('.') if os.path.isdir(f)])
        }
        return json.dumps(stats, ensure_ascii=False, indent=2)
    
    @mcp_prompt(
        name="file_analysis",
        title="文件分析提示",
        description="生成文件分析的提示"
    )
    def file_analysis_prompt(self, file_path: str) -> List[Dict[str, Any]]:
        """生成文件分析提示"""
        return [
            {
                "role": "system",
                "content": "你是一个文件分析专家，擅长分析各种类型的文件内容。"
            },
            {
                "role": "user",
                "content": f"请分析文件 {file_path} 的内容，提供详细的分析报告。"
            }
        ]


# 数学计算服务示例
class MathService(BaseMCPService):
    def __init__(self):
        super().__init__(
            name="数学计算服务",
            instructions="提供各种数学计算功能"
        )
    
    def setup(self):
        """初始化数学服务"""
        print("数学计算服务初始化完成")
    
    # 使用约定优于配置的方式
    async def tool_add(self, a: float, b: float, ctx: Context) -> float:
        """加法运算"""
        result = a + b
        await ctx.info(f"计算 {a} + {b} = {result}")
        return result
    
    async def tool_multiply(self, a: float, b: float, ctx: Context) -> float:
        """乘法运算"""
        result = a * b
        await ctx.info(f"计算 {a} × {b} = {result}")
        return result
    
    @mcp_tool(
        name="complex_calculation",
        title="复杂计算",
        description="执行复杂的数学计算"
    )
    async def complex_calc(self, expression: str, ctx: Context) -> Dict[str, Any]:
        """执行复杂计算"""
        try:
            await ctx.info(f"计算表达式: {expression}")
            await ctx.report_progress(25, 100, "解析表达式...")
            
            # 简单的表达式计算（实际应用中应该使用更安全的方法）
            result = eval(expression)
            
            await ctx.report_progress(75, 100, "计算中...")
            
            response = {
                "expression": expression,
                "result": result,
                "type": type(result).__name__
            }
            
            await ctx.report_progress(100, 100, "计算完成")
            await ctx.info(f"计算结果: {result}")
            
            return response
        except Exception as e:
            await ctx.error(f"计算失败: {str(e)}")
            raise


# 工厂函数，用于创建不同类型的服务
def create_service(service_type: str, **kwargs) -> BaseMCPService:
    """服务工厂函数"""
    services = {
        "database": DatabaseService,
        "file": FileProcessingService,
        "math": MathService
    }
    
    if service_type not in services:
        raise ValueError(f"未知的服务类型: {service_type}")
    
    return services[service_type]()


# 多服务管理器
class MultiServiceManager:
    """管理多个MCP服务"""
    
    def __init__(self):
        self.services: Dict[str, BaseMCPService] = {}
    
    def add_service(self, name: str, service: BaseMCPService):
        """添加服务"""
        self.services[name] = service
    
    def run_service(self, name: str, **kwargs):
        """运行指定服务"""
        if name not in self.services:
            raise ValueError(f"服务 {name} 不存在")
        
        print(f"启动服务: {name}")
        self.services[name].run(**kwargs)
    
    def list_services(self) -> List[str]:
        """列出所有服务"""
        return list(self.services.keys())


# 使用示例
if __name__ == "__main__":
    import sys
    
    # 创建服务管理器
    manager = MultiServiceManager()
    
    # 添加不同的服务
    manager.add_service("database", DatabaseService())
    manager.add_service("file", FileProcessingService())
    manager.add_service("math", MathService())
    
    # 根据命令行参数选择服务
    if len(sys.argv) > 1:
        service_name = sys.argv[1]
        transport = sys.argv[2] if len(sys.argv) > 2 else "stdio"
        
        try:
            print(f"可用服务: {manager.list_services()}")
            manager.run_service(service_name, transport=transport)
        except ValueError as e:
            print(f"错误: {e}")
            print(f"可用服务: {manager.list_services()}")
    else:
        # 默认运行数学服务
        print("默认运行数学服务（stdio模式）")
        print("使用方法: python MCPService.py <service_name> [transport]")
        print(f"可用服务: {manager.list_services()}")
        print("可用传输方式: stdio, sse, streamable-http")
        
        service = MathService()
        service.run()

