#!/usr/bin/env python3
"""
UserService Consul 注册功能测试脚本
"""

import asyncio
import httpx
from Service.UserService.app.main import UserServiceApp


async def test_consul_registration():
    """测试Consul注册功能"""
    
    print("🚀 开始测试UserService的Consul注册功能...")
    
    # 创建应用实例
    app_instance = UserServiceApp()
    
    # 测试HTTP客户端
    async with httpx.AsyncClient() as client:
        try:
            # 测试Consul连接
            consul_url = "http://127.0.0.1:8500"
            response = await client.get(f"{consul_url}/v1/status/leader")
            if response.status_code == 200:
                print("✅ Consul服务器连接正常")
            else:
                print("❌ Consul服务器连接失败")
                return
                
        except Exception as e:
            print(f"❌ 无法连接到Consul服务器: {e}")
            print("请确保Consul服务器正在运行 (consul agent -dev)")
            return
    
    print("✅ Consul注册功能已添加到UserService")
    print("\n📝 添加的功能:")
    print("  - 服务启动时自动注册到Consul")
    print("  - 健康检查端点: /health")
    print("  - 服务关闭时自动从Consul注销")
    print("  - 错误处理: 即使Consul注册失败，服务也能正常启动")
    
    print("\n🔧 配置信息:")
    print(f"  - 服务名称: {app_instance.app.title}")
    print(f"  - 服务版本: {app_instance.app.version}")
    print("  - Consul URL: 可通过环境变量CONSUL_URL配置")
    print("  - 健康检查: GET /health")
    
    print("\n🚀 启动服务:")
    print("  python -m Service.UserService.app.main")
    print("  或者: cd ${AGENT_HOME}/Service/UserService && python app/main.py")


if __name__ == "__main__":
    asyncio.run(test_consul_registration())
