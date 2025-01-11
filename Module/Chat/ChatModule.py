# Project:      Agent
# Author:       yomu
# Time:         2025/01/06
# Version:      0.1
# Description:  chat module 

"""
    负责处理与用户对话的ChatModule
"""
import os
import uvicorn
import httpx
import random
import asyncio
import json
import shutil

from typing import Dict, List, Any, Tuple
from fastapi import (
    FastAPI, Form, UploadFile, HTTPException, status, Body, Response,
    File
)
from dotenv import dotenv_values
from pydantic import BaseModel

from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.schema.runnable import RunnableSerializable


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
    # 定义数据模型
    class Message(BaseModel):
        role: str
        content: str
        

    class TextChatRequest(BaseModel):
        messages: List['ChatModule.Message']
        
        
        
    def __init__(self):
        self.logger = setup_logger(name="ChatModule", log_path="InternalModule")
        
        # 加载环境变量和配置
        self.env_vars = dotenv_values("/home/yomu/agent/Module/Chat/.env")
        self.config_path = self.env_vars.get("CHAT_MODULE_CONFIG_PATH","")
        self.config = load_config(config_path=self.config_path, config_name='ChatModule', logger=self.logger)
        
        # 验证配置文件
        required_keys = ["consul_url", "host", "port", "services", "service_name", "service_id", "health_check_url", "save_dir"]
        validate_config(required_keys, self.config, self.logger)
        
        # 用户上传文件的保存地址
        self.audio_save_dir = self.config.get("save_dir")
        
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
        # 初始化 AsyncClient
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(10.0, read=60.0)
        )
        self.logger.info("Async HTTP Client Initialized")
        
        task = None
        try:
            # 注册服务到 Consul
            self.logger.info("Registering service to Consul...")
            tags = ["ChatModule"]
            await register_service_to_consul(consul_url=self.consul_url,
                                             client=self.client,
                                             logger=self.logger,
                                             service_name=self.service_name,
                                             service_id=self.service_id,
                                             address=self.host,
                                             port=self.port,
                                             tags=tags,
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
        async def user_input_text(chat_request: 'ChatModule.TextChatRequest'):
            """处理用户的文本输入"""
            content = chat_request.messages[0].content
            self.logger.info(f"user input message:{content}")
            return await self._user_input_text(content)
        
        
        @self.app.api_route("/agent/chat/input/audio", methods=["POST"], summary="用户语音输入接口")
        async def user_input_audio(file: UploadFile = File(...)):
            """处理用户的语音输入"""
            # 1. 获取客户端传来的原始文件名
            original_filename = file.filename

            # 2. 可以根据需要生成新的文件名，或直接使用原始文件名
            #    为了避免文件名冲突，可以在前面加 UUID 或时间戳之类
            #    这里演示直接用原始名字
            save_filename = original_filename  # 或用 f"{uuid4()}_{original_filename}"
            
            save_path = os.path.join(self.audio_save_dir, save_filename)
            
            # 3. 一次性读取文件并写入本地（适合中小文件）
            #    如果文件较大，可以考虑分块读取
            contents = await file.read()
            with open(save_path, "wb") as f:
                f.write(contents)
                
            self.logger.info(f"Audio synthesis successful, saved as '{save_path}'")    
            return await self._user_input_audio(save_path)
        
        
        @self.app.api_route("/agent/chat/input/video", methods=["POST"], summary="用户视频输入接口")
        async def user_input_video():
            """处理用户的视频输入"""
            return await self._user_input_video()
        
        
        @self.app.api_route("/agent/chat/input/image", methods=["POST"], summary="用户图片输入接口")
        async def user_input_image():
            """处理用户的视频输入"""
            return await self._user_input_image()
        
    
    # --------------------------------
    # 功能函数
    # --------------------------------  
    async def _user_input_text(self, content: str):
        """处理用户的文本输入"""
        return await self._chat(content)
        
        
    async def _user_input_audio(self, audio_file: str):
        """处理用户的语音输入"""
        # 将用户的语音输入发送给STT(SenseVoiceAgent)进行语音识别
        stt_instance = await self.pick_instance(service_name="SenseVoiceAgent")
        stt_path = "/audio/recognize"
        stt_payload = {
            "audio_path": audio_file
        }
        response = await self.call_service_api(instance=stt_instance, path=stt_path, payload=stt_payload)
        self.logger.info(response)
        res = next(iter(response))
        _, recognize_result = res
        self.logger.info(recognize_result)
        return await self._chat(recognize_result)
        
        
    async def _user_input_video(self, filename: str):
        """处理用户的视频输入"""
        # TODO 暂时未实现视觉Agent，待修改
        # 将视频发送给Vision进行识别
        vision_instance = self.pick_instance(service_name="VisionAgent")
        vision_path = ""
        vision_payload = {
            "user":  "test",
            "content": ""
        }
        vision_response = await self.call_service_api(instance=vision_instance, path=vision_path, payload=vision_payload)
        return await self._chat(vision_response)
    
    
    async def _user_input_image(self):
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
         # 将文本发送给PromptOptimizer进行优化
        po_instance = await self.pick_instance(service_name="PromptOptimizer")
        po_path = "/prompt/optimize"
        po_payload = {
            "user":  "test",
            "content": content
        }
        optimize_content = await self.call_service_api(instance=po_instance, path=po_path, payload=po_payload)
        self.logger.info(f"optimize content: {optimize_content}")
        
        # 将优化后的文本发送给LLM(OllamaAgent)
        llm_instance = await self.pick_instance(service_name="OllamaAgent")
        llm_path = "/agent/chat/to_ollama/chat"
        llm_payload= {
            "user":  "test",
            "content": optimize_content
        }
        content_response = await self.call_service_api(instance=llm_instance, path=llm_path, payload=llm_payload)
        self.logger.info(f"llm response content: {content_response}")
        
        # 将从LLM(OllamaAgent)收到的答复发送给GPTSoVitsAgent进行语音生成
        tts_instance = await self.pick_instance(service_name="GPTSoVitsAgent")
        tts_path = "/predict/sentences"
        tts_payload = {
            "content": content_response['message']['content']
        }
        audio_path: str = await self.call_service_api(instance=tts_instance, path=tts_path, payload=tts_payload)
        self.logger.info(f"audio path : {audio_path}")
        
        # 将文本回复语语音回复返回给客户端
        return await self.return_response(content_response, audio_path)
      
    
    async def return_response(self, content: str, audio_path: str):
        """返回文本+语音文件给客户端"""
        # TODO 选取合适的分隔符
        # 分隔符 
        boundary = "myboundary123456"
        
        # 文本JSON元数据
        metadata = {
            "user": "test",
            "content": content
        }
        metadata_bytes = json.dumps(metadata).encode("utf-8")
        
        # 构造 Part 1 的 HTTP 头部和内容
        # 注意每个 Part 都以 "--boundary" 开头，随后是特定的头部，再加一个空行后是内容
        metadata_part = (
            f"--{boundary}\r\n"
            f"Content-Type: application/json\r\n\r\n"
        ).encode("utf-8") + metadata_bytes + b"\r\n"
        
        # Part 2: 文件（二进制）
        with open(audio_path, "rb") as f:
            file_content = f.read()
            
        # 构造 Part 2 的 HTTP 头部和内容
        file_part = (
            f"--{boundary}\r\n"
            f"Content-Type: application/octet-stream\r\n"
            f"Content-Disposition: attachment; filename={audio_path}\r\n\r\n"
        ).encode("utf-8") + file_content + b"\r\n"
        
        # 结束标识
        end_part = f"--{boundary}--\r\n".encode("utf-8")

        # 拼接最终响应体
        body = metadata_part + file_part + end_part
        
        return Response(
            content=body,
            media_type=f"multipart/mixed; boundary={boundary}",
            # 在实际生产中，也可加上 Content-Length 等头部
        )
    
      
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
    
    