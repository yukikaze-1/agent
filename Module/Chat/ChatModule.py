# Project:      Agent
# Author:       yomu
# Time:         2025/01/06
# Version:      0.1
# Description:  chat module 

"""
    负责处理与用户对话的ChatModule
"""
import uvicorn
import httpx
import random
import asyncio
from typing import Dict, List, Any, Tuple
from fastapi import FastAPI, Form, UploadFile, HTTPException, status, Body
from dotenv import dotenv_values

from Module.Utils.ConfigTools import load_config, validate_config
from Module.Utils.Logger import setup_logger
from Module.Utils.FastapiServiceTools import (
    get_service_instances,
    register_service_to_consul,
    unregister_service_from_consul
)


class ChatModule:
    """
        负责处理与用户对话
            1. 负责将用户的各种输入进行转换
            2. 负责将用户输入发送给LLM，并接受相应的输出
            3. 将LLM的输出文本进行语音转换 
            4. 汇聚LLM的输出文本和语音，一同返回给客户端
    """
    def __init__(self):
        self.logger = setup_logger(name="ChatModule", log_path="InternalModule")
        
        # 加载环境变量和配置
        self.env_vars = dotenv_values("/home/yomu/agent/Module/Chat/.env")
        self.config_path = self.env_vars.get("CHAT_MODULE_CONFIG_PATH","")
        self.config = load_config(config_path=self.config_path, config_name='ChatModule', logger=self.logger)
        
        # 验证配置文件
        required_keys = ["consul_url", "host", "port", "services", "service_name", "service_id", "health_check_url"]
        validate_config(required_keys, self.config, self.logger)
        
        # 微服务本身地址
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 20060)
        
        # Consul URL，确保包含协议前缀
        self.consul_url: str = self.config.get("consul_url", "http://127.0.0.1:8500")
        if not self.consul_url.startswith("http://") and not self.consul_url.startswith("https://"):
            self.consul_url = "http://" + self.consul_url
            self.logger.info(f"Consul URL adjusted to include http://: {self.consul_url}")
        
        
        # 服务注册信息
        self.service_name = self.config.get("service_name", "ChatModule")
        self.service_id = self.config.get("service_id", f"{self.service_name}-{self.host}:{self.port}")
        self.health_check_url = self.config.get("health_check_url", f"http://{self.host}:{self.port}/health")
        
        # 初始化 httpx.AsyncClient
        self.client = None  # 在lifespan中初始化
        
        # 初始化 FastAPI 应用，使用生命周期管理
        self.app = FastAPI(lifespan=self.lifespan)
        
        # 设置路由
        self.setup_routes()
        
    
    async def lifespan(self, app: FastAPI):
        """管理应用生命周期"""
        # 应用启动时执行
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(10.0, read=60.0)
        )
        self.logger.info("Async HTTP Client Initialized")
        
        task = None
        try:
            # 注册服务到 Consul
            await register_service_to_consul(consul_url=self.consul_url,
                                             client=self.client,
                                             logger=self.logger,
                                             service_name=self.service_name,
                                             service_id=self.service_id,
                                             address=self.host,
                                             port=self.port,
                                             health_check_url=self.health_check_url)
            yield  # 应用正常运行
            
        except Exception as e:
            self.logger.error(f"Exception during lifespan: {e}")
            raise
        
        finally:                
            # 注销服务从 Consul
            try:
                self.logger.info("Deregistering service from Consul...")
                await unregister_service_from_consul(consul_url=self.consul_url,
                                                     client=self.client,
                                                     logger=self.logger,
                                                     service_id=self.service_id)
                self.logger.info("Service deregistered from Consul.")
            except Exception as e:
                self.logger.error(f"Error while deregistering service: {e}")
                
            # 关闭 AsyncClient
            self.logger.info("Shutting down Async HTTP Client")
            if self.client:
                await self.client.aclose()
                    
    
    async def pick_instance(self, service_name: str):
        """随机选取一个实例"""
        instances = await get_service_instances(self.consul_url, service_name, self.client, self.logger)
        if not instances:
            raise RuntimeError(f"No available instances for service '{service_name}'")

        return random.choice(instances)

        # 或者轮询、权重等更复杂策略
    
    
    # --------------------------------
    # 3. 请求转发逻辑
    # --------------------------------    
    def setup_routes(self):
        """设置路由"""
        
        @self.app.get("/health")
        async def health_check():
            """健康检查接口"""
            return {"status": "healthy"}
        
        
        @self.app.api_route("/agent/chat/input/text", methods=["POST"], summary="用户文本输入接口")
        async def user_input_text(content: str=Form(...)):
            """处理用户的文本输入"""
            return await self._user_input_text(content)
        
        
        @self.app.api_route("/agent/chat/input/audio", methods=["POST"], summary="用户语音输入接口")
        async def user_input_audio():
            """处理用户的语音输入"""
            return await self._user_input_audio()
        
        
        @self.app.api_route("/agent/chat/input/video", methods=["POST"], summary="用户视频输入接口")
        async def user_input_video():
            """处理用户的视频输入"""
            return await self._user_input_video()
        
        @self.app.api_route("/agent/chat/input/picture", methods=["POST"], summary="用户图片输入接口")
        async def user_input_picture():
            """处理用户的视频输入"""
            return await self._user_input_picture()
        
    
    # --------------------------------
    # 功能函数
    # --------------------------------  
    async def _user_input_text(self, content: str):
        """处理用户的文本输入"""
        return await self._chat(content)
        
        
    async def _user_input_audio(self, audio_file):
        """处理用户的语音输入"""
        # 将用户的语音输入发送给STT(SenseVoiceAgent)进行语音识别
        stt_instance = self.pick_instance(service_name="SenseVoiceAgent")
        stt_path = "/audio/infer"
        stt_payload = {
            
        }
        recognize_result = await self.call_service_api(instance=stt_instance, path=stt_path, payload=stt_payload)
       
        return await self._chat(recognize_result)
        
        
    async def _user_input_video(self):
        """处理用户的视频输入"""
        # TODO 暂时未实现视觉Agent，待修改
        # 将视频发送给Vision进行识别
        vision_instance = self.pick_instance(service_name="VisionAgent")
        vision_path = ""
        vision_payload = {
            
        }
        vision_response = await self.call_service_api(instance=vision_instance, path=vision_path, payload=vision_payload)
        return await self._chat(vision_response)
    
    
    async def _user_input_picture(self):
        """处理用户的图片输入"""
        # TODO 暂时未实现视觉Agent，待修改
        # 将图片发送给Vision进行识别
        vision_instance = self.pick_instance(service_name="VisionAgent")
        vision_path = ""
        vision_payload = {
            
        }
        vision_response = await self.call_service_api(instance=vision_instance, path=vision_path, payload=vision_payload)
        return await self._chat(vision_response)
    
    
    async def _chat(self, content: str):
        """通用函数"""
         # 将语音识别的结果发送给PromptOptimizer进行优化
        po_instance = self.pick_instance(service_name="PromptOptimizer")
        po_path = ""
        po_payload = {
            
        }
        optimize_content = await self.call_service_api(instance=po_instance, path=po_path, payload=po_payload)
        # 将优化后的文本发送给LLM(OllamaAgent)
        llm_instance = self.pick_instance(service_name="OllamaAgent")
        llm_path = ""
        llm_payload= {
            
        }
        content_response = await self.call_service_api(instance=llm_instance, path=llm_path, payload=llm_payload)
        # 将从LLM(OllamaAgent)收到的答复发送给GPTSoVitsAgent进行语音生成
        tts_instance = self.pick_instance(service_name="GPTSoVitsAgent")
        tts_path = ""
        tts_payload = {
            
        }
        audio_response = await self.call_service_api(instance=tts_instance, path=tts_path, payload=tts_payload)
        # 将文本回复语语音回复返回给客户端
        return {"Content": content_response, "Audio": audio_response}
      
    # TODO 将这个函数完善并抽象出来放到ServiceTools.py中去
    async def call_service_api(self, instance: Dict, path: str, payload: Dict) -> Dict:
        """
        向指定微服务地址 instance 发起 POST 请求。
        :param instance: 形如 {"address": "192.168.1.100", "port": 20010}
        :param path: 例如 "/some/endpoint"
        :param payload: 请求体
        :return: 返回的 JSON 数据
        """
        base_url = f"http://{instance['address']}:{instance['port']}"
        url = base_url + path
        
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()    
    
    
    def run(self):
        uvicorn.run(self.app, host=self.host, port=self.port)
        

def main():
    module = ChatModule()
    module.run()
    
    
if __name__ == "__main__":
    main()
    
    