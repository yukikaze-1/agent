"""
STT服务代理

作为内部模块连接外部STT服务（如SenseVoice）的代理。
替代原来的SenseVoiceAgent FastAPI服务。
"""

import os
import asyncio
import httpx
from typing import Dict, Any, Optional, Union, List
from logging import Logger

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config
from Init.ServiceDiscovery import ServiceDiscoveryManager, ExternalServiceConnector


class STTProxy:
    """
    STT服务代理
    
    功能：
    - 连接外部STT服务（SenseVoice等）
    - 提供统一的STT接口
    - 处理音频文件识别
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化STT代理
        
        Args:
            config_path: 配置文件路径
        """
        self.logger = setup_logger(name="STTProxy", log_path="InternalModule")
        
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 服务发现和连接管理器
        self.discovery_manager: Optional[ServiceDiscoveryManager] = None
        self.service_connector: Optional[ExternalServiceConnector] = None
        self.service_client = None
        
        # STT配置
        self.request_timeout = self.config.get("request_timeout", 30.0)
        self.supported_formats = self.config.get("supported_formats", [
            ".wav", ".mp3", ".m4a", ".flac", ".aac"
        ])
        
        self.logger.info("STTProxy initialized")
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """加载配置"""
        if config_path:
            try:
                return load_config(config_path, "stt_proxy", self.logger)
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}")
        
        # 默认配置
        return {
            "request_timeout": 30.0,
            "max_retries": 3,
            "retry_delay": 2.0,
            "supported_formats": [".wav", ".mp3", ".m4a", ".flac", ".aac"],
            "max_file_size": 100 * 1024 * 1024  # 100MB
        }
    
    async def initialize(self):
        """初始化服务连接"""
        self.logger.info("初始化STT服务连接...")
        
        try:
            # 创建服务发现管理器
            consul_url = self.config.get("consul_url", "http://127.0.0.1:8500")
            discovery_config_path = "Init/ServiceDiscovery/config.yml"
            
            self.discovery_manager = ServiceDiscoveryManager(
                consul_url=consul_url,
                config_path=discovery_config_path
            )
            
            # 创建服务连接器
            self.service_connector = ExternalServiceConnector(self.discovery_manager)
            
            # 等待STT服务就绪
            await self.discovery_manager.wait_for_services(timeout=60)
            
            # 获取STT服务客户端
            service_clients = await self.service_connector.initialize_connections()
            self.service_client = service_clients.get("stt_service")
            
            if not self.service_client:
                raise RuntimeError("STT service not available")
            
            self.logger.info(f"✅ STT服务连接成功: {self.service_client.base_url}")
            
        except Exception as e:
            self.logger.error(f"STT服务初始化失败: {e}")
            raise
    
    async def transcribe(self, audio_file_path: str, language: Optional[str] = None, 
                        **kwargs) -> Dict[str, Any]:
        """
        转录音频文件
        
        Args:
            audio_file_path: 音频文件路径
            language: 语言代码（如 'zh', 'en'）
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 转录结果，包含文本和置信度等信息
        """
        if not self.service_client:
            await self.initialize()
        
        # 验证文件
        self._validate_audio_file(audio_file_path)
        
        try:
            # 准备请求数据
            data = {
                "audio_path": audio_file_path,
                "language": language or "auto",
                **kwargs
            }
            
            result = await self._make_request("/transcribe", data)
            
            self.logger.info(f"STT transcription completed for: {audio_file_path}")
            return result
            
        except Exception as e:
            self.logger.error(f"STT transcription failed: {e}")
            raise
    
    async def transcribe_with_upload(self, audio_data: bytes, filename: str = "audio.wav",
                                   language: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        转录音频数据（通过上传）
        
        Args:
            audio_data: 音频数据
            filename: 文件名
            language: 语言代码
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 转录结果
        """
        if not self.service_client:
            await self.initialize()
        
        # 验证文件大小
        max_size = self.config.get("max_file_size", 100 * 1024 * 1024)
        if len(audio_data) > max_size:
            raise ValueError(f"Audio file too large: {len(audio_data)} bytes > {max_size}")
        
        try:
            # 准备多部分上传数据
            files = {
                "audio": (filename, audio_data, "audio/wav")
            }
            
            data = {
                "language": language or "auto",
                **kwargs
            }
            
            result = await self._upload_request("/transcribe_upload", files, data)
            
            self.logger.info(f"STT transcription completed for uploaded audio: {filename}")
            return result
            
        except Exception as e:
            self.logger.error(f"STT transcription with upload failed: {e}")
            raise
    
    async def get_supported_languages(self) -> List[str]:
        """
        获取支持的语言列表
        
        Returns:
            List[str]: 支持的语言代码列表
        """
        if not self.service_client:
            await self.initialize()
        
        if self.service_client is None:
            self.logger.error("服务客户端未能初始化")
            return ["zh", "en", "auto"]
        
        try:
            response = await self.service_client.get("/languages")
            response.raise_for_status()
            result = response.json()
            
            return result.get("languages", ["zh", "en", "auto"])
            
        except Exception as e:
            self.logger.warning(f"Failed to get supported languages: {e}")
            # 返回默认支持的语言
            return ["zh", "en", "auto"]
    
    def _validate_audio_file(self, file_path: str):
        """验证音频文件"""
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        # 检查文件扩展名
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in self.supported_formats:
            raise ValueError(
                f"Unsupported audio format: {file_ext}. "
                f"Supported formats: {self.supported_formats}"
            )
        
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        max_size = self.config.get("max_file_size", 100 * 1024 * 1024)
        if file_size > max_size:
            raise ValueError(f"Audio file too large: {file_size} bytes > {max_size}")
        
        self.logger.debug(f"Audio file validation passed: {file_path}")
    
    async def _make_request(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """发起JSON请求"""
        if self.service_client is None:
            self.logger.error("服务客户端未初始化")
            return {}
            
        max_retries = self.config.get("max_retries", 3)
        retry_delay = self.config.get("retry_delay", 2.0)
        
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
        
        # 如果所有重试都失败，返回空字典
        return {}
    
    async def _upload_request(self, path: str, files: Dict, data: Dict[str, Any]) -> Dict[str, Any]:
        """发起文件上传请求"""
        if self.service_client is None:
            self.logger.error("服务客户端未初始化")
            return {}
            
        max_retries = self.config.get("max_retries", 3)
        retry_delay = self.config.get("retry_delay", 2.0)
        
        for attempt in range(max_retries):
            try:
                response = await self.service_client.post(
                    path,
                    files=files,
                    data=data,
                    timeout=self.request_timeout
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                self.logger.error(f"Upload HTTP error (attempt {attempt + 1}): {e.response.status_code}")
                if attempt == max_retries - 1:
                    raise
                    
            except httpx.RequestError as e:
                self.logger.error(f"Upload request error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
                    
            except Exception as e:
                self.logger.error(f"Upload unexpected error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
            
            # 重试延迟
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
        
        # 如果所有重试都失败，返回空字典
        return {}
    
    async def check_health(self) -> bool:
        """
        检查STT服务健康状态
        
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
        """重新连接STT服务"""
        self.logger.info("重新连接STT服务...")
        
        try:
            if self.service_connector:
                self.service_client = await self.service_connector.reconnect_service("stt_service")
                self.logger.info("✅ STT服务重连成功")
            else:
                await self.initialize()
                
        except Exception as e:
            self.logger.error(f"STT服务重连失败: {e}")
            raise
    
    async def cleanup(self):
        """清理资源"""
        self.logger.info("清理STT代理资源...")
        
        try:
            if self.service_connector:
                await self.service_connector.cleanup()
                
            self.service_client = None
            self.service_connector = None
            self.discovery_manager = None
            
            self.logger.info("STT代理资源清理完成")
            
        except Exception as e:
            self.logger.warning(f"资源清理时出错: {e}")


# 便捷函数
async def create_stt_proxy(config_path: Optional[str] = None) -> STTProxy:
    """
    创建并初始化STT代理
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        STTProxy: 初始化后的STT代理
    """
    proxy = STTProxy(config_path)
    await proxy.initialize()
    return proxy


if __name__ == "__main__":
    # 测试代码
    async def test_stt_proxy():
        proxy = await create_stt_proxy()
        
        try:
            # 测试获取支持的语言
            languages = await proxy.get_supported_languages()
            print(f"Supported languages: {languages}")
            
            # 如果有测试音频文件，可以取消注释下面的代码
            # result = await proxy.transcribe("/path/to/test/audio.wav")
            # print(f"Transcription result: {result}")
            
        finally:
            await proxy.cleanup()
    
    asyncio.run(test_stt_proxy())
