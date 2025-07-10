#!/usr/bin/env python3
"""
通用服务注册到Consul的脚本

支持注册任何HTTP服务到Consul进行服务发现
"""

import requests
import argparse
import json
import sys


def register_service_to_consul(consul_url: str, service_config: dict) -> bool:
    """将服务注册到Consul"""
    try:
        response = requests.put(
            f"{consul_url}/v1/agent/service/register",
            json=service_config,
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ 服务注册成功: {service_config['Name']} -> {service_config['Address']}:{service_config['Port']}")
            return True
        else:
            print(f"❌ 注册失败: HTTP {response.status_code}")
            print(f"响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 注册服务失败: {e}")
        return False


def deregister_service_from_consul(consul_url: str, service_id: str) -> bool:
    """从Consul注销服务"""
    try:
        response = requests.put(f"{consul_url}/v1/agent/service/deregister/{service_id}")
        
        if response.status_code == 200:
            print(f"✅ 服务注销成功: {service_id}")
            return True
        else:
            print(f"❌ 注销失败: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 注销服务失败: {e}")
        return False


def list_registered_services(consul_url: str):
    """列出已注册的服务"""
    try:
        response = requests.get(f"{consul_url}/v1/agent/services")
        if response.status_code == 200:
            services = response.json()
            print("已注册的服务:")
            for service_id, service_info in services.items():
                print(f"  - {service_info['Service']} (ID: {service_id}) -> {service_info['Address']}:{service_info['Port']}")
        else:
            print(f"❌ 获取服务列表失败: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ 获取服务列表失败: {e}")


# 预定义的服务配置
PREDEFINED_SERVICES = {
    "ollama": {
        "ID": "ollama_server",
        "Name": "ollama_server",
        "Tags": ["llm", "ollama", "ai"],
        "Address": "127.0.0.1",
        "Port": 11434,
        "Check": {
            "HTTP": "http://127.0.0.1:11434/api/tags",
            "Interval": "10s",
            "Timeout": "3s"
        }
    },
    "gpt-sovits": {
        "ID": "GPTSoVits_server",
        "Name": "GPTSoVits_server", 
        "Tags": ["tts", "gpt-sovits", "ai"],
        "Address": "127.0.0.1",
        "Port": 9880,
        "Check": {
            "HTTP": "http://127.0.0.1:9880/health",
            "Interval": "10s",
            "Timeout": "3s"
        }
    },
    "sensevoice": {
        "ID": "SenseVoice_server",
        "Name": "SenseVoice_server",
        "Tags": ["stt", "sensevoice", "ai"], 
        "Address": "127.0.0.1",
        "Port": 20042,
        "Check": {
            "HTTP": "http://127.0.0.1:20042/health",
            "Interval": "10s",
            "Timeout": "3s"
        }
    }
}


def main():
    parser = argparse.ArgumentParser(description="通用服务注册到Consul")
    parser.add_argument("--consul-url", default="http://127.0.0.1:8500", help="Consul URL")
    parser.add_argument("--list", action="store_true", help="列出已注册的服务")
    parser.add_argument("--deregister", help="注销指定服务ID")
    
    # 预定义服务选项
    parser.add_argument("--service", choices=PREDEFINED_SERVICES.keys(), 
                       help="注册预定义服务")
    
    # 自定义服务选项
    parser.add_argument("--custom", help="自定义服务配置JSON文件路径")
    parser.add_argument("--name", help="服务名称")
    parser.add_argument("--host", default="127.0.0.1", help="服务主机")
    parser.add_argument("--port", type=int, help="服务端口")
    parser.add_argument("--health-path", default="/health", help="健康检查路径")
    
    args = parser.parse_args()
    
    # 检查Consul连接
    try:
        response = requests.get(f"{args.consul_url}/v1/status/leader", timeout=5)
        if response.status_code != 200:
            raise Exception("Consul not available")
        print("✅ Consul连接正常")
    except Exception:
        print(f"❌ 无法连接到Consul: {args.consul_url}")
        sys.exit(1)
    
    if args.list:
        list_registered_services(args.consul_url)
        return
    
    if args.deregister:
        success = deregister_service_from_consul(args.consul_url, args.deregister)
        sys.exit(0 if success else 1)
    
    if args.service:
        # 注册预定义服务
        service_config = PREDEFINED_SERVICES[args.service].copy()
        success = register_service_to_consul(args.consul_url, service_config)
        sys.exit(0 if success else 1)
    
    if args.custom:
        # 从JSON文件加载自定义配置
        try:
            with open(args.custom, 'r') as f:
                service_config = json.load(f)
            success = register_service_to_consul(args.consul_url, service_config)
            sys.exit(0 if success else 1)
        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
            sys.exit(1)
    
    if args.name and args.port:
        # 自定义快速注册
        service_config = {
            "ID": args.name,
            "Name": args.name,
            "Address": args.host,
            "Port": args.port,
            "Check": {
                "HTTP": f"http://{args.host}:{args.port}{args.health_path}",
                "Interval": "10s",
                "Timeout": "3s"
            }
        }
        success = register_service_to_consul(args.consul_url, service_config)
        sys.exit(0 if success else 1)
    
    # 如果没有指定操作，显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
