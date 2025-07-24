"""
TTS服务代理

作为内部模块连接外部TTS服务（如GPTSoVits）的代理。
替代原来的GPTSoVitsAgent FastAPI服务。
"""

import os
import datetime
import asyncio
import aiofiles
import httpx
from typing import Dict, Any, Optional, Union, List
from logging import Logger
from urllib.parse import urljoin

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config
from Init.ServiceDiscovery import ServiceDiscoveryManager, ExternalServiceConnector


class TTSProxy:
    """
    TTS服务代理
    
    功能：
    - 连接外部TTS服务（GPTSoVits等）
    - 提供统一的TTS接口
    - 处理音频文件保存和管理
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化TTS代理
        
        Args:
            config_path: 配置文件路径
        """
        self.logger = setup_logger(name="TTSProxy", log_path="InternalModule")
        
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 服务发现和连接管理器
        self.discovery_manager: Optional[ServiceDiscoveryManager] = None
        self.service_connector: Optional[ExternalServiceConnector] = None
        self.service_client = None
        
        # TTS配置
        self.save_dir = self.config.get("save_dir", "${AGENT_HOME}/Temp")
        self.default_character = self.config.get("default_character", "Elysia")
        self.request_timeout = self.config.get("request_timeout", 60.0)
        
        # 角色配置
        self.characters = self.config.get("characters", {})
        
        # 确保保存目录存在
        self._ensure_save_dir()
        
        self.logger.info("TTSProxy initialized")
        
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """加载配置"""
        if config_path:
            try:
                return load_config(config_path, "tts_proxy", self.logger)
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}")
                self.logger.info("Using default configuration.")
        
        # 默认配置
        default_config: Dict[str, Any] = {
            "save_dir": "${AGENT_HOME}/Temp",
            "default_character": "Elysia",
            "request_timeout": 60.0,
            "max_retries": 3,
            "retry_delay": 2.0,
            "characters": {
                "Elysia": {
                    "gpt_path": "/home/yomu/GPTSoVits/GPT_SoVITS/pretrained_models/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt",
                    "sovits_path": "/home/yomu/GPTSoVits/GPT_SoVITS/pretrained_models/s2G488k.pth",
                    "ref_audio": "/home/yomu/data/audio/reference/audio/elysia.wav",
                    "ref_audio_text": "我的话，嗯哼，更多是靠少女的小心思吧~。看看你现在的表情。好想去那里。"
                }
            }
        }
        return default_config
    
    
    def _ensure_save_dir(self):
        """确保保存目录存在"""
        # 展开环境变量
        save_dir = os.path.expandvars(self.save_dir)
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)
            self.logger.info(f"Created save directory: {save_dir}")
        
        self.save_dir = save_dir
        
    
    async def initialize(self):
        """初始化服务连接"""
        self.logger.info("初始化TTS服务连接...")
        
        try:
            # 创建服务发现管理器
            consul_url = self.config.get("consul_url", "http://127.0.0.1:8500")
            # 使用TTS专用的服务发现配置
            discovery_config_path = "Init/ServiceDiscovery/tts_config.yml"
            
            self.discovery_manager = ServiceDiscoveryManager(
                consul_url=consul_url,
                config_path=discovery_config_path
            )
            
            # 创建服务连接器
            self.service_connector = ExternalServiceConnector(self.discovery_manager)
            
            # 等待TTS服务就绪
            await self.discovery_manager.wait_for_services(timeout=60)
            
            # 获取TTS服务客户端
            service_clients = await self.service_connector.initialize_connections()
            self.service_client = service_clients.get("tts_service")
            
            if not self.service_client:
                raise RuntimeError("TTS service not available")
            
            self.logger.info(f"✅ TTS服务连接成功: {self.service_client.base_url}")
            
        except Exception as e:
            self.logger.error(f"TTS服务初始化失败: {e}")
            raise
        
    
    async def synthesize(self, text: str, character: Optional[str] = None, 
                        save_file: bool = True, **kwargs) -> Union[str, bytes]:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            character: 角色名称，如果不指定则使用默认角色
            save_file: 是否保存为文件
            **kwargs: 其他参数
            
        Returns:
            Union[str, bytes]: 如果save_file=True返回文件路径，否则返回音频数据
        """
        if not self.service_client:
            await self.initialize()
        
        character = character or self.default_character
        character_config = self.characters.get(character, {})
        
        if not character_config:
            raise ValueError(f"Character '{character}' not configured")
        
        # 构建请求参数
        params = {
            "text": text,
            "text_lang": kwargs.get("text_lang", "zh"),
            "ref_audio_path": character_config.get("ref_audio", ""),
            "prompt_text": character_config.get("ref_audio_text", ""),
            "prompt_lang": kwargs.get("prompt_lang", "zh"),
            "text_split_method": kwargs.get("text_split_method", "cut5"),
            "batch_size": kwargs.get("batch_size", 20),
            "media_type": kwargs.get("media_type", "wav"),
            "streaming_mode": kwargs.get("streaming_mode", True)
        }
        
        try:
            if save_file:
                # 保存为文件
                file_path = await self._synthesize_and_save(params)
                self.logger.info(f"TTS synthesis completed, saved to: {file_path}")
                return file_path
            else:
                # 返回音频数据
                audio_data = await self._synthesize_raw(params)
                self.logger.info(f"TTS synthesis completed, returned {len(audio_data)} bytes")
                return audio_data
                
        except Exception as e:
            self.logger.error(f"TTS synthesis failed: {e}")
            raise
        
    
    async def _synthesize_and_save(self, params: Dict[str, Any]) -> str:
        """合成语音并保存文件"""
        if not self.service_client:
            raise RuntimeError("TTS service not initialized")
            
        # 生成唯一文件名
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S%f")
        filename = os.path.join(self.save_dir, f"{timestamp}_tts_output.wav")
        
        max_retries = self.config.get("max_retries", 3)
        retry_delay = self.config.get("retry_delay", 2.0)
        
        for attempt in range(max_retries):
            try:
                # 发起请求
                response = await self.service_client.get(
                    path="/tts",
                    params=params,
                    timeout=self.request_timeout
                )
                response.raise_for_status()
                
                # 异步保存文件
                async with aiofiles.open(filename, 'wb') as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        if chunk:
                            await f.write(chunk)
                
                return filename
                
            except Exception as e:
                self.logger.warning(f"TTS synthesis attempt {attempt + 1} failed: {e}")
                
                if attempt == max_retries - 1:
                    raise
                
                # 重试延迟
                await asyncio.sleep(retry_delay * (attempt + 1))
        
        # 如果所有重试都失败，抛出异常
        raise RuntimeError("TTS synthesis failed after all retries")
    
    
    async def _synthesize_raw(self, params: Dict[str, Any]) -> bytes:
        """合成语音并返回原始数据"""
        if not self.service_client:
            raise RuntimeError("TTS service not initialized")
            
        max_retries = self.config.get("max_retries", 3)
        retry_delay = self.config.get("retry_delay", 2.0)
        
        for attempt in range(max_retries):
            try:
                response = await self.service_client.get(
                    "/tts",
                    params=params,
                    timeout=self.request_timeout
                )
                response.raise_for_status()
                
                # 收集所有数据
                audio_data = b""
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    if chunk:
                        audio_data += chunk
                
                return audio_data
                
            except Exception as e:
                self.logger.warning(f"TTS synthesis attempt {attempt + 1} failed: {e}")
                
                if attempt == max_retries - 1:
                    raise
                
                # 重试延迟
                await asyncio.sleep(retry_delay * (attempt + 1))
        
        # 如果所有重试都失败，抛出异常
        raise RuntimeError("TTS synthesis failed after all retries")
    
    
    async def set_character_weights(self, character: str, gpt_path: str, sovits_path: str) -> bool:
        """
        设置角色权重
        
        Args:
            character: 角色名称
            gpt_path: GPT权重路径
            sovits_path: SoVits权重路径
            
        Returns:
            bool: 是否设置成功
        """
        if not self.service_client:
            await self.initialize()
        
        if not self.service_client:
            raise RuntimeError("TTS service not available")
        
        try:
            # 设置GPT权重
            gpt_response = await self.service_client.get(
                "/set_gpt_weights",
                params={"weights_path": gpt_path}
            )
            gpt_response.raise_for_status()
            
            # 设置SoVits权重
            sovits_response = await self.service_client.get(
                "/set_sovits_weights", 
                params={"weights_path": sovits_path}
            )
            sovits_response.raise_for_status()
            
            # 更新本地配置
            if character not in self.characters:
                self.characters[character] = {}
            
            self.characters[character].update({
                "gpt_path": gpt_path,
                "sovits_path": sovits_path
            })
            
            self.logger.info(f"✅ 角色权重设置成功: {character}")
            return True
            
        except Exception as e:
            self.logger.error(f"设置角色权重失败: {e}")
            return False
    
    async def list_characters(self) -> List[str]:
        """
        获取可用角色列表
        
        Returns:
            List[str]: 角色名称列表
        """
        return list(self.characters.keys())
    
    
    async def get_character_config(self, character: str) -> Optional[Dict[str, Any]]:
        """
        获取角色配置
        
        Args:
            character: 角色名称
            
        Returns:
            Dict[str, Any]: 角色配置，如果不存在返回None
        """
        return self.characters.get(character)
    
    
    async def check_health(self) -> bool:
        """
        检查TTS服务健康状态
        
        Returns:
            bool: 是否健康
        """
        try:
            if not self.service_client:
                return False
                
            response = await self.service_client.get("/health", timeout=5.0)
            return response.status_code == 200
            
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            return False
        
    
    async def reconnect(self):
        """重新连接TTS服务"""
        self.logger.info("重新连接TTS服务...")
        
        try:
            if self.service_connector:
                self.service_client = await self.service_connector.reconnect_service("tts_service")
                self.logger.info("✅ TTS服务重连成功")
            else:
                await self.initialize()
                
        except Exception as e:
            self.logger.error(f"TTS服务重连失败: {e}")
            raise
        
    
    async def cleanup(self):
        """清理资源"""
        self.logger.info("清理TTS代理资源...")
        
        try:
            if self.service_connector:
                await self.service_connector.cleanup()
                
            self.service_client = None
            self.service_connector = None
            self.discovery_manager = None
            
            self.logger.info("TTS代理资源清理完成")
            
        except Exception as e:
            self.logger.warning(f"资源清理时出错: {e}")


# 便捷函数
async def create_tts_proxy(config_path: Optional[str] = None) -> TTSProxy:
    """
    创建并初始化TTS代理
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        TTSProxy: 初始化后的TTS代理
    """
    proxy = TTSProxy(config_path)
    await proxy.initialize()
    return proxy


if __name__ == "__main__":
    # 测试代码
    async def test_tts_proxy():
        proxy = await create_tts_proxy()
        
        try:
            # 测试语音合成
            file_path = await proxy.synthesize("你好，这是一个测试。")
            print(f"TTS output saved to: {file_path}")
            
            # 测试角色列表
            characters = await proxy.list_characters()
            print(f"Available characters: {characters}")
            
        finally:
            await proxy.cleanup()
    
    asyncio.run(test_tts_proxy())
