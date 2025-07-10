"""
LLM服务代理

作为内部模块连接外部LLM服务（如Ollama）的代理。
替代原来的OllamaAgent FastAPI服务。
"""

import asyncio
import httpx
from typing import Dict, Any, Optional, List
from logging import Logger

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config
from Init.ServiceDiscovery import ServiceDiscoveryManager, ExternalServiceConnector


class LLMProxy:
    """
    LLM服务代理
    
    功能：
    - 连接外部LLM服务（Ollama等）
    - 提供统一的LLM接口
    - 处理请求路由和错误恢复
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化LLM代理
        
        Args:
            config_path: 配置文件路径
        """
        self.logger = setup_logger(name="LLMProxy", log_path="InternalModule")
        
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 服务发现和连接管理器
        self.discovery_manager: Optional[ServiceDiscoveryManager] = None
        self.service_connector: Optional[ExternalServiceConnector] = None
        self.service_client = None
        
        # 默认模型配置
        self.default_model = self.config.get("default_model", "qwen2.5")
        self.request_timeout = self.config.get("request_timeout", 120.0)
        
        self.logger.info("LLMProxy initialized")
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """加载配置"""
        if config_path:
            try:
                return load_config(config_path, "llm_proxy", self.logger)
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}")
        
        # 默认配置
        return {
            "default_model": "qwen2.5",
            "request_timeout": 120.0,
            "max_retries": 3,
            "retry_delay": 1.0
        }
    
    async def initialize(self):
        """初始化服务连接"""
        self.logger.info("初始化LLM服务连接...")
        
        try:
            # 创建服务发现管理器
            consul_url = self.config.get("consul_url", "http://127.0.0.1:8500")
            # 使用LLM专用的服务发现配置
            discovery_config_path = "Init/ServiceDiscovery/llm_config.yml"
            
            self.discovery_manager = ServiceDiscoveryManager(
                consul_url=consul_url,
                config_path=discovery_config_path
            )
            
            # 创建服务连接器
            self.service_connector = ExternalServiceConnector(self.discovery_manager)
            
            # 等待LLM服务就绪
            await self.discovery_manager.wait_for_services(timeout=60)
            
            # 获取LLM服务客户端
            service_clients = await self.service_connector.initialize_connections()
            self.service_client = service_clients.get("llm_service")
            
            if not self.service_client:
                raise RuntimeError("LLM service not available")
            
            self.logger.info(f"✅ LLM服务连接成功: {self.service_client.base_url}")
            
        except Exception as e:
            self.logger.error(f"LLM服务初始化失败: {e}")
            raise
    
    async def chat(self, message: str, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        与LLM进行对话
        
        Args:
            message: 用户消息
            model: 模型名称，如果不指定则使用默认模型
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: LLM响应
        """
        if not self.service_client:
            await self.initialize()
        
        model = model or self.default_model
        
        # 构建请求数据
        data = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": message
                }
            ],
            "stream": False,
            **kwargs
        }
        
        try:
            response = await self._make_request("/api/chat", data)
            self.logger.debug(f"LLM chat successful for model: {model}")
            return response
            
        except Exception as e:
            self.logger.error(f"LLM chat failed: {e}")
            raise
    
    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        生成文本
        
        Args:
            prompt: 提示文本
            model: 模型名称
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        if not self.service_client:
            await self.initialize()
        
        model = model or self.default_model
        
        # 构建请求数据
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            **kwargs
        }
        
        try:
            response = await self._make_request("/api/generate", data)
            self.logger.debug(f"LLM generate successful for model: {model}")
            return response
            
        except Exception as e:
            self.logger.error(f"LLM generate failed: {e}")
            raise
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        获取可用模型列表
        
        Returns:
            List[Dict[str, Any]]: 模型列表
        """
        if not self.service_client:
            await self.initialize()
        
        try:
            if self.service_client is None:
                self.logger.error("服务客户端未初始化")
                raise RuntimeError("服务客户端未初始化")
                
            response = await self.service_client.get("/api/tags")
            response.raise_for_status()
            result = response.json()
            
            self.logger.debug(f"Retrieved {len(result.get('models', []))} models")
            return result.get('models', [])
            
        except Exception as e:
            self.logger.error(f"Failed to list models: {e}")
            raise
    
    async def _make_request(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发起HTTP请求
        
        Args:
            path: API路径
            data: 请求数据
            
        Returns:
            Dict[str, Any]: 响应数据
        """
        if self.service_client is None:
            self.logger.error("服务客户端未初始化")
            raise RuntimeError("服务客户端未初始化")
            
        max_retries = self.config.get("max_retries", 3)
        retry_delay = self.config.get("retry_delay", 1.0)
        
        for attempt in range(max_retries):
            try:
                response = await self.service_client.post(
                    path,
                    json=data,
                    headers={"Content-Type": "application/json"},
                    timeout=self.request_timeout
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                self.logger.error(f"HTTP error (attempt {attempt + 1}): {e.response.status_code}")
                if attempt == max_retries - 1:
                    raise
                    
            except httpx.RequestError as e:
                self.logger.error(f"Request error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
                    
            except Exception as e:
                self.logger.error(f"Unexpected error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
            
            # 重试延迟
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
        
        # 如果所有重试都失败了，抛出异常
        raise RuntimeError(f"所有重试都失败了，无法完成请求到 {path}")
    
    async def check_health(self) -> bool:
        """
        检查LLM服务健康状态
        
        Returns:
            bool: 是否健康
        """
        try:
            if not self.service_client:
                return False
                
            response = await self.service_client.get("/api/tags", timeout=5.0)
            return response.status_code == 200
            
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            return False
    
    async def reconnect(self):
        """重新连接LLM服务"""
        self.logger.info("重新连接LLM服务...")
        
        try:
            if self.service_connector:
                self.service_client = await self.service_connector.reconnect_service("llm_service")
                self.logger.info("✅ LLM服务重连成功")
            else:
                await self.initialize()
                
        except Exception as e:
            self.logger.error(f"LLM服务重连失败: {e}")
            raise
    
    async def cleanup(self):
        """清理资源"""
        self.logger.info("清理LLM代理资源...")
        
        try:
            if self.service_connector:
                await self.service_connector.cleanup()
                
            self.service_client = None
            self.service_connector = None
            self.discovery_manager = None
            
            self.logger.info("LLM代理资源清理完成")
            
        except Exception as e:
            self.logger.warning(f"资源清理时出错: {e}")


# 便捷函数
async def create_llm_proxy(config_path: Optional[str] = None) -> LLMProxy:
    """
    创建并初始化LLM代理
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        LLMProxy: 初始化后的LLM代理
    """
    proxy = LLMProxy(config_path)
    await proxy.initialize()
    return proxy


if __name__ == "__main__":
    print("开始LLMProxy测试...")
    
    # 测试代码
    async def test_llm_proxy():
        print("创建LLMProxy实例...")
        proxy = await create_llm_proxy()
        
        try:
            print("开始功能测试...")
            
            # 测试健康检查
            health = await proxy.check_health()
            print(f"LLM service health: {health}")
            
            # 测试模型列表
            # models = await proxy.list_models()
            # print(f"Available models: {len(models)}")
            # for model in models[:3]:  # 只显示前3个模型
            #     print(f"  - {model['name']}")
            
            # 测试简单对话
            try:
                print("测试对话功能...")
                response = await proxy.chat("你好呀", model="qwen2.5")
                print(f"Chat response: {response}")
            except Exception as e:
                print(f"Chat test failed: {e}")
            
        finally:
            print("清理资源...")
            await proxy.cleanup()
    
    print("运行异步测试...")
    asyncio.run(test_llm_proxy())
    print("测试完成!")
