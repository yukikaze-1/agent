#!/usr/bin/env python3
"""
将Ollama服务注册到Consul

使用方法：
python register_ollama.py [--port 11434] [--consul-url http://127.0.0.1:8500]
"""

import requests
import argparse
import sys
import time


def check_ollama_running(ollama_host: str, ollama_port: int) -> bool:
    """检查Ollama是否正在运行"""
    try:
        response = requests.get(f"http://{ollama_host}:{ollama_port}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def register_ollama_to_consul(consul_url: str, ollama_host: str, ollama_port: int) -> bool:
    """将Ollama注册到Consul"""
    
    service_definition = {
        "ID": "ollama_server",
        "Name": "ollama_server", 
        "Tags": ["llm", "ollama", "ai"],
        "Address": ollama_host,
        "Port": ollama_port,
        "Check": {
            "HTTP": f"http://{ollama_host}:{ollama_port}/api/tags",
            "Interval": "10s",
            "Timeout": "3s"
        }
    }
    
    try:
        response = requests.put(
            f"{consul_url}/v1/agent/service/register",
            json=service_definition,
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ Ollama服务注册成功: {ollama_host}:{ollama_port}")
            return True
        else:
            print(f"❌ 注册失败: HTTP {response.status_code}")
            print(f"响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 注册Ollama服务失败: {e}")
        return False


def deregister_ollama_from_consul(consul_url: str) -> bool:
    """从Consul注销Ollama服务"""
    try:
        response = requests.put(f"{consul_url}/v1/agent/service/deregister/ollama_server")
        
        if response.status_code == 200:
            print("✅ Ollama服务注销成功")
            return True
        else:
            print(f"❌ 注销失败: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 注销Ollama服务失败: {e}")
        return False


def check_consul_connection(consul_url: str) -> bool:
    """检查Consul连接"""
    try:
        response = requests.get(f"{consul_url}/v1/status/leader", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="注册Ollama服务到Consul")
    parser.add_argument("--port", type=int, default=11434, help="Ollama端口 (默认: 11434)")
    parser.add_argument("--host", default="127.0.0.1", help="Ollama主机 (默认: 127.0.0.1)")
    parser.add_argument("--consul-url", default="http://127.0.0.1:8500", help="Consul URL")
    parser.add_argument("--deregister", action="store_true", help="注销服务而不是注册")
    parser.add_argument("--check-only", action="store_true", help="只检查服务状态")
    
    args = parser.parse_args()
    
    # 检查Consul连接
    print("检查Consul连接...")
    if not check_consul_connection(args.consul_url):
        print(f"❌ 无法连接到Consul: {args.consul_url}")
        print("请确保Consul正在运行")
        sys.exit(1)
    print("✅ Consul连接正常")
    
    if args.deregister:
        # 注销服务
        success = deregister_ollama_from_consul(args.consul_url)
        sys.exit(0 if success else 1)
    
    if args.check_only:
        # 只检查状态
        print(f"检查Ollama服务状态: {args.host}:{args.port}")
        if check_ollama_running(args.host, args.port):
            print("✅ Ollama服务正在运行")
        else:
            print("❌ Ollama服务未运行")
        return
    
    # 检查Ollama是否运行
    print(f"检查Ollama服务: {args.host}:{args.port}")
    if not check_ollama_running(args.host, args.port):
        print("❌ Ollama服务未运行！")
        print("请先启动Ollama服务：")
        print("  ollama serve")
        sys.exit(1)
    print("✅ Ollama服务正在运行")
    
    # 注册服务
    success = register_ollama_to_consul(args.consul_url, args.host, args.port)
    
    if success:
        print("\n🎉 注册完成！现在可以通过服务发现访问Ollama了")
        print("\n要注销服务，请运行：")
        print(f"python {__file__} --deregister")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
