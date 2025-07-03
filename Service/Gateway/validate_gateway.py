#!/usr/bin/env python3
"""
网关健康检查和配置验证脚本
"""

import asyncio
import httpx
import yaml
from typing import Dict, List
import time

class GatewayValidator:
    """网关验证器"""
    
    def __init__(self):
        self.config_path = "${AGENT_HOME}/Service/Gateway/config.yml"
        self.config = self.load_config()
        
    def load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}")
            return {}
    
    async def check_gateway_health(self, gateway_name: str, health_url: str) -> bool:
        """检查网关健康状态"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "healthy":
                        print(f"✅ {gateway_name} 健康检查通过")
                        return True
                    else:
                        print(f"❌ {gateway_name} 健康检查失败: {result}")
                        return False
                else:
                    print(f"❌ {gateway_name} 健康检查失败: HTTP {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ {gateway_name} 健康检查异常: {e}")
            return False
    
    async def check_service_connectivity(self, service_name: str, url: str) -> bool:
        """检查服务连通性"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # 尝试连接服务的健康检查端点
                health_url = f"{url}/health"
                response = await client.get(health_url)
                print(f"✅ {service_name} ({url}) 连通性正常")
                return True
        except Exception as e:
            print(f"❌ {service_name} ({url}) 连通性失败: {e}")
            return False
    
    def validate_config_structure(self) -> bool:
        """验证配置文件结构"""
        print("🔍 验证配置文件结构...")
        
        if not self.config:
            print("❌ 配置文件为空")
            return False
        
        # 验证 MicroServiceGateway 配置
        if "MicroServiceGateway" not in self.config:
            print("❌ 缺少 MicroServiceGateway 配置")
            return False
        
        micro_config = self.config["MicroServiceGateway"]
        required_micro_keys = ["host", "port", "consul_url", "routes", "services"]
        for key in required_micro_keys:
            if key not in micro_config:
                print(f"❌ MicroServiceGateway 缺少配置项: {key}")
                return False
        
        # 验证 APIGateway 配置
        if "APIGateway" not in self.config:
            print("❌ 缺少 APIGateway 配置")
            return False
        
        api_config = self.config["APIGateway"]
        required_api_keys = ["listen_host", "port", "register_address", "consul_url", "routes", "services"]
        for key in required_api_keys:
            if key not in api_config:
                print(f"❌ APIGateway 缺少配置项: {key}")
                return False
        
        print("✅ 配置文件结构验证通过")
        return True
    
    async def run_comprehensive_check(self):
        """运行综合检查"""
        print("=== 网关综合健康检查 ===\n")
        
        # 1. 配置文件验证
        if not self.validate_config_structure():
            return False
        
        # 2. 网关健康检查
        print("\n🏥 网关健康检查...")
        micro_config = self.config["MicroServiceGateway"]
        api_config = self.config["APIGateway"]
        
        micro_health_url = micro_config.get("health_check_url", 
                                          f"http://{micro_config['host']}:{micro_config['port']}/health")
        api_health_url = api_config.get("health_check_url", 
                                       f"http://{api_config['register_address']}:{api_config['port']}/health")
        
        micro_healthy = await self.check_gateway_health("MicroServiceGateway", micro_health_url)
        api_healthy = await self.check_gateway_health("APIGateway", api_health_url)
        
        # 3. 路由服务连通性检查
        print("\n🔗 路由服务连通性检查...")
        connectivity_results = []
        
        # 检查 MicroServiceGateway 的路由
        for service_name, url in micro_config.get("routes", {}).items():
            result = await self.check_service_connectivity(f"Micro-{service_name}", url)
            connectivity_results.append(result)
        
        # 检查 APIGateway 的路由
        for service_name, url in api_config.get("routes", {}).items():
            result = await self.check_service_connectivity(f"API-{service_name}", url)
            connectivity_results.append(result)
        
        # 4. 总结
        print(f"\n📊 检查结果总结:")
        print(f"   MicroServiceGateway: {'✅ 健康' if micro_healthy else '❌ 异常'}")
        print(f"   APIGateway: {'✅ 健康' if api_healthy else '❌ 异常'}")
        print(f"   路由服务连通性: {sum(connectivity_results)}/{len(connectivity_results)} 正常")
        
        all_healthy = micro_healthy and api_healthy and all(connectivity_results)
        print(f"\n🎯 整体状态: {'✅ 所有检查通过' if all_healthy else '❌ 存在问题'}")
        
        return all_healthy

    def show_config_info(self):
        """显示配置信息"""
        print("=== 网关配置信息 ===\n")
        
        if "MicroServiceGateway" in self.config:
            micro_config = self.config["MicroServiceGateway"]
            print("🔹 MicroServiceGateway:")
            print(f"   监听地址: {micro_config.get('host')}:{micro_config.get('port')}")
            print(f"   Consul URL: {micro_config.get('consul_url')}")
            print(f"   路由数量: {len(micro_config.get('routes', {}))}")
            print(f"   服务发现: {micro_config.get('services', [])}")
        
        if "APIGateway" in self.config:
            api_config = self.config["APIGateway"]
            print("\n🔹 APIGateway:")
            print(f"   监听地址: {api_config.get('listen_host')}:{api_config.get('port')}")
            print(f"   注册地址: {api_config.get('register_address')}:{api_config.get('port')}")
            print(f"   Consul URL: {api_config.get('consul_url')}")
            print(f"   路由数量: {len(api_config.get('routes', {}))}")
            print(f"   服务发现: {api_config.get('services', [])}")

async def main():
    """主函数"""
    validator = GatewayValidator()
    
    # 显示配置信息
    validator.show_config_info()
    
    print()
    
    # 运行综合检查
    await validator.run_comprehensive_check()

if __name__ == "__main__":
    asyncio.run(main())
