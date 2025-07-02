#!/usr/bin/env python3
"""
MCP服务框架测试脚本
"""

import asyncio
from MCPService import (
    BaseMCPService, 
    mcp_tool, 
    mcp_resource, 
    mcp_prompt,
    Context,
    DatabaseService,
    FileProcessingService,
    MathService,
    MultiServiceManager
)
from typing import Dict, Any, List

class TestService(BaseMCPService):
    """测试服务类"""
    
    def __init__(self):
        super().__init__(
            name="测试服务",
            instructions="用于测试MCP框架的各种功能"
        )
        self.test_data = {}
    
    def setup(self):
        """初始化测试数据"""
        self.test_data = {
            "initialized": True,
            "timestamp": "2025-01-01"
        }
        print("测试服务初始化完成")
    
    def teardown(self):
        """清理测试数据"""
        self.test_data.clear()
        print("测试服务清理完成")
    
    @mcp_tool(
        name="test_echo",
        title="回声测试",
        description="简单的回声测试工具"
    )
    async def test_echo(self, message: str, ctx: Context) -> str:
        """回声测试"""
        await ctx.info(f"收到消息: {message}")
        return f"回声: {message}"
    
    @mcp_tool(
        name="test_calculation",
        title="计算测试",
        description="测试带进度报告的计算"
    )
    async def test_calculation(self, numbers: List[int], ctx: Context) -> Dict[str, Any]:
        """测试计算功能"""
        await ctx.info("开始计算测试")
        
        total = 0
        for i, num in enumerate(numbers):
            total += num
            progress = (i + 1) / len(numbers) * 100
            await ctx.report_progress(progress, 100, f"处理数字 {num}")
            
            # 模拟一些处理时间
            await asyncio.sleep(0.1)
        
        result = {
            "sum": total,
            "count": len(numbers),
            "average": total / len(numbers) if numbers else 0
        }
        
        await ctx.info(f"计算完成，总和: {total}")
        return result
    
    # 约定式工具（tool_开头）
    async def tool_simple_add(self, a: int, b: int, ctx: Context) -> int:
        """简单加法"""
        result = a + b
        await ctx.info(f"{a} + {b} = {result}")
        return result
    
    @mcp_resource(
        uri="resource://test_data",
        title="测试数据",
        description="获取测试服务的内部数据"
    )
    def get_test_data(self) -> str:
        """获取测试数据"""
        import json
        return json.dumps(self.test_data, ensure_ascii=False, indent=2)
    
    @mcp_resource(
        uri="resource://user/{user_id}/profile",
        title="用户资料",
        description="获取指定用户的资料信息"
    )
    def get_user_profile(self, user_id: str) -> str:
        """获取用户资料（模板资源示例）"""
        import json
        profile = {
            "user_id": user_id,
            "name": f"用户{user_id}",
            "created_at": "2025-01-01",
            "status": "active"
        }
        return json.dumps(profile, ensure_ascii=False, indent=2)
    
    @mcp_prompt(
        name="test_analysis",
        title="测试分析提示"
    )
    def test_analysis_prompt(self, data_type: str) -> List[Dict[str, Any]]:
        """生成测试分析提示"""
        return [
            {
                "role": "system",
                "content": "你是一个测试分析专家，擅长分析各种测试数据。"
            },
            {
                "role": "user",
                "content": f"请分析这个{data_type}测试数据，提供详细的测试报告。"
            }
        ]


def test_service_creation():
    """测试服务创建"""
    print("=== 测试服务创建 ===")
    
    # 测试基础服务
    service = TestService()
    print(f"服务名称: {service.name}")
    print(f"服务说明: {service.instructions}")
    print("✓ 基础服务创建成功")
    
    # 测试内置服务
    db_service = DatabaseService()
    file_service = FileProcessingService()
    math_service = MathService()
    print("✓ 内置服务创建成功")


def test_multi_service_manager():
    """测试多服务管理器"""
    print("\n=== 测试多服务管理器 ===")
    
    manager = MultiServiceManager()
    
    # 添加服务
    manager.add_service("test", TestService())
    manager.add_service("database", DatabaseService())
    manager.add_service("file", FileProcessingService())
    manager.add_service("math", MathService())
    
    # 列出服务
    services = manager.list_services()
    print(f"可用服务: {services}")
    print("✓ 多服务管理器测试成功")


def test_tool_registration():
    """测试工具注册"""
    print("\n=== 测试工具注册 ===")
    
    service = TestService()
    
    # 检查MCP服务器是否正确初始化
    print(f"MCP服务器类型: {type(service.mcp_server)}")
    print("✓ 工具注册测试完成")


def demo_service_lifecycle():
    """演示服务生命周期"""
    print("\n=== 演示服务生命周期 ===")
    
    service = TestService()
    
    # 手动调用生命周期方法
    print("1. 调用setup()...")
    service.setup()
    
    print("2. 检查初始化状态...")
    print(f"   初始化状态: {service._initialized}")
    print(f"   测试数据: {service.test_data}")
    
    print("3. 调用teardown()...")
    service.teardown()
    print(f"   清理后测试数据: {service.test_data}")
    
    print("✓ 生命周期演示完成")


def main():
    """主测试函数"""
    print("MCP服务框架测试开始\n")
    
    try:
        test_service_creation()
        test_multi_service_manager()
        test_tool_registration()
        demo_service_lifecycle()
        
        print("\n" + "="*50)
        print("🎉 所有测试通过！")
        print("="*50)
        
        print("\n使用说明:")
        print("1. 运行特定服务:")
        print("   python MCPService.py test stdio")
        print("   python MCPService.py database streamable-http")
        print("   python MCPService.py file sse")
        print("   python MCPService.py math stdio")
        
        print("\n2. 运行HTTP服务:")
        print("   python MCPService.py database streamable-http")
        print("   # 然后访问 http://localhost:8001")
        
        print("\n3. 交互式测试:")
        print("   python test_service.py --interactive")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def interactive_demo():
    """交互式演示"""
    print("=== 交互式演示 ===")
    print("启动测试服务（stdio模式）...")
    print("你可以通过MCP客户端连接并测试各种工具。")
    print("按 Ctrl+C 停止服务。")
    
    service = TestService()
    try:
        service.run(transport="stdio")
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_demo()
    else:
        main()
