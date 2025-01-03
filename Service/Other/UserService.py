# Project:      Agent
# Author:       yomu
# Time:         2024/12/27
# Version:      0.1
# Description:  agent user operation

"""
    负责用户服务，如登录、注册、修改密码、注销账号等
"""

import uvicorn
import httpx
import asyncio
from typing import Dict, List, Any
from fastapi import FastAPI, Form, HTTPException, status
from dotenv import dotenv_values
import concurrent.futures

from Module.Utils.Database.UserAccountDataBaseAgent import  UserAccountDataBaseAgent
from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config, validate_config

# from Service.Other.EnvironmentManagerClient import EnvironmentManagerClient


class UserService:
    """
        负责用户服务：
        
            1. 登陆
            2. 注册
            3. 修改密码
            4. 登出
            5. 注销
    """
    def __init__(self):
        self.logger = setup_logger(name="UserService", log_path="InternalModule")
        
        # 加载环境变量和配置
        self.env_vars = dotenv_values("/home/yomu/agent/Service/Other/.env")
        self.config_path = self.env_vars.get("USER_SERVICE_CONFIG_PATH","")
        self.config = load_config(config_path=self.config_path, config_name='UserService', logger=self.logger)
        
        # 验证配置文件
        required_keys = ["consul_url", "host", "port", "service_name", "service_id", "health_check_url"]
        validate_config(required_keys, self.config, self.logger)
        
        # 用户信息数据库
        self.usr_account_database = UserAccountDataBaseAgent(logger=self.logger)
        
        # Consul URL，确保包含协议前缀
        self.consul_url: str = self.config.get("consul_url", "http://127.0.0.1:8500")
        if not self.consul_url.startswith("http://") and not self.consul_url.startswith("https://"):
            self.consul_url = "http://" + self.consul_url
            self.logger.info(f"Consul URL adjusted to include http://: {self.consul_url}") 
        
        # 微服务本身地址
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 20010)

        # 服务注册信息
        self.service_name = self.config.get("service_name", "UserService")
        self.service_id = self.config.get("service_id", f"{self.service_name}-{self.host}:{self.port}")
        self.health_check_url = self.config.get("health_check_url", f"http://{self.host}:{self.port}/health")
        
        # 初始化 httpx.AsyncClient
        self.client = None  # 在lifespan中初始化
        
        # 初始化 FastAPI 应用，使用生命周期管理
        self.app = FastAPI(lifespan=self.lifespan)
        
        # 线程池
        self.executor = concurrent.futures.ThreadPoolExecutor()
        
        # 初始化 EnvironmentManagerClient
        # self.environment_manager_client = EnvironmentManagerClient(
        #     consul_url=self.consul_url,
        #     service_name="EnvironmentManager",
        #     http_client=self.client
        # )
        
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
        
        try:
            # 注册服务到 Consul
            await self.register_service_to_consul(self.service_name, self.service_id, self.host, self.port, self.health_check_url)
            yield  # 应用正常运行
            
        except Exception as e:
            self.logger.error(f"Exception during lifespan: {e}")
            raise
        
        finally:
            # 注销服务从 Consul
            try:
                self.logger.info("Deregistering service from Consul...")
                await self.unregister_service_from_consul(self.service_id)
                self.logger.info("Service deregistered from Consul.")
            except Exception as e:
                self.logger.error(f"Error while deregistering service: {e}")
                
            # 关闭 AsyncClient
            self.logger.info("Shutting down Async HTTP Client")
            if self.client:
                await self.client.aclose()
                
            # 关闭线程池执行器
            self.logger.info("Shutting down ThreadPoolExecutor")
            self.executor.shutdown(wait=True)           
 
                
                
    # --------------------------------
    # 1. 服务发现
    # --------------------------------
    async def get_service_instances(self, service_name: str) -> List[Dict]:
        """从 Consul 拉取服务实例列表"""
        url = f"{self.consul_url}/v1/catalog/service/{service_name}"
        try:
            response = await self.client.get(url)
            if response.is_success:
                instances = [
                    {"address": instance["Address"], "port": instance["ServicePort"]}
                    for instance in response.json()
                ]
                if instances:
                    self.logger.info(f"Successfully fetched service instances for '{service_name}' from Consul.")
                    self.logger.debug(f"Service instances for '{service_name}': {instances}")
                else:
                    self.logger.error(f"No service instances found for '{service_name}' in Consul.")
                    # 可选择抛出异常或采取其他措施
                    # raise ValueError(f"No service instances found for '{service_name}' in Consul.")
                return instances
            else:
                self.logger.warning(f"Failed to fetch service instances for '{service_name}': {response.status_code}")
        except httpx.RequestError as exc:
            self.logger.error(f"Error fetching service instances from Consul for '{service_name}': {exc}")
        return []
       
    
    # --------------------------------
    # 5. Consul 服务注册与注销
    # --------------------------------
    async def register_service_to_consul(self, service_name, service_id, address, port, health_check_url, retries=3, delay=2.0):
        """向 Consul 注册该微服务网关"""
        payload = {
            "Name": service_name,
            "ID": service_id,
            "Address": address,
            "Port": port,
            "Tags": ["v1", "UserService"],
            "Check": {
                "HTTP": health_check_url,
                "Interval": "10s",
                "Timeout": "5s",
            }
        }

        for attempt in range(1, retries + 1):
            try:
                response = await self.client.put(f"{self.consul_url}/v1/agent/service/register", json=payload)
                if response.status_code == 200:
                    self.logger.info(f"Service '{service_name}' registered successfully to Consul.")
                    return
                else:
                    self.logger.warning(f"Attempt {attempt}: Failed to register service '{service_name}': {response.status_code}, {response.text}")
            except Exception as e:
                self.logger.error(f"Attempt {attempt}: Error while registering service '{service_name}': {e}")
            
            if attempt < retries:
                self.logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

        self.logger.error(f"All {retries} attempts to register service '{service_name}' failed.")
        raise HTTPException(status_code=500, detail="Service registration failed.")
    
    
    async def unregister_service_from_consul(self, service_id: str):
        """从 Consul 注销该微服务网关"""
        try:
            response = await self.client.put(f"{self.consul_url}/v1/agent/service/deregister/{service_id}")
            if response.status_code == 200:
                self.logger.info(f"Service with ID '{service_id}' deregistered successfully from Consul.")
            else:
                self.logger.warning(f"Failed to deregister service ID '{service_id}': {response.status_code}, {response.text}")
        except Exception as e:
            self.logger.error(f"Error while deregistering service ID '{service_id}': {e}")
      
    
    # --------------------------------
    # 6. 请求转发逻辑
    # --------------------------------    
    def setup_routes(self):
        """设置路由"""
        
        @self.app.get("/health")
        async def health_check():
            """健康检查接口"""
            return {"status": "healthy"}
        
        # 用户登录
        @self.app.post("/usr/login/")
        async def usr_login(username: str=Form(...), password: str=Form(...)):
            return await self._usr_login(username, password)

                
        # 用户注册
        @self.app.post("/usr/register/")
        async def usr_register(username: str=Form(...), password: str=Form(...)):
            return await self._usr_register(username, password)
        
        
        # 用户更改密码
        @self.app.post("/usr/change_pwd/")
        async def usr_change_pwd(username: str=Form(...), password: str=Form(...)):
            return await self._usr_change_pwd(username, password)
        
        
        # 用户登出
        @self.app.post("/usr/logout/")
        async def usr_logout(username: str=Form(...)):
            return await self._usr_logout(username)
        
        
        # 用户注销
        @self.app.post("/usr/unregister/")
        async def usr_unregister(username: str=Form(...), password: str=Form(...)):
            return await self._usr_unregister(username, password)
        
        
    # --------------------------------
    # 功能函数
    # --------------------------------    
    async def _usr_login(self, username: str, password: str):
        """验证用户登录"""
        operator = 'usr_login'
        try:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(self.executor, self.usr_account_database.fetch_user_by_name, username)
        except Exception as e:
            self.logger.error(f"Database error during login for user '{username}': {e}")
            # return {"result": False, "message": "Internal server error.", "username": username}
            raise HTTPException(status_code=500, detail="Internal server error.")
            
        result = True
        message = 'Login successfully!'
        
        # 检查用户是否已注册
        if not res:
            result = False
            message = f"Login failed! Username '{username}' does not exist!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}

        
        # 验证用户名和密码是否匹配
        if password != res["password"]:
            result = False
            message = "Login failed! Invalid username or password!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}  

        
        # 记录登录成功
        self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
        return {"result": result, "message": message, "username": username}    
            
    
    async def _usr_register(self, username: str, password: str):
        """用户注册"""
        operator = 'usr_register'
        try:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(self.executor, self.usr_account_database.fetch_user_by_name, username)
        except Exception as e:
            self.logger.error(f"Database error during registration for user '{username}': {e}")
            return {"result": False, "message": "Internal server error.", "username": username}
        
        result = True
        message = 'Register successfully!'
        
        # 如果已注册
        if res:
            result = False
            message = f"Register failed! Username '{username}' already exists!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}  
        
        # 注册
        try:
            res = await loop.run_in_executor(self.executor, self.usr_account_database.insert_user_info, username, password)
        except Exception as e:
            self.logger.error(f"Database error during inserting user '{username}': {e}")
            return {"result": False, "message": "Internal server error.", "username": username}
        
        # 注册成功
        if res:
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}
            # TODO: 添加数据库插入逻辑
            
            # 将来调用 EnvironmentManager
            # env_data = {"username": username}
            # try:
            #     env_response = await environment_manager_client.call_endpoint("initialize_environment", env_data)
            #     print(env_response)
            # except Exception as e:
            #     raise HTTPException(status_code=500, detail="Failed to initialize user environment.")
        
        else:
            result = False
            message = f"Register failed! Inserting username '{username}' to database failed!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}
        
        
    async def _usr_change_pwd(self, username: str, password: str):
        """用户更改密码"""
        operator = 'usr_change_pwd'
        result = True
        message = 'Change password successful!'
        
        # 更新密码
        try:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(self.executor, self.usr_account_database.update_user_password, username, password)
        except Exception as e:
            self.logger.error(f"Database error during password update for user '{username}': {e}")
            return {"result": False, "message": "Internal server error.", "username": username}
        
        # 成功更新密码
        if res:
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}
        else:
            result = False
            message = f"Change password failed! Username '{username}' update in database failed!"
            self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
            return {"result": result, "message": message, "username": username}


    async def _usr_logout(self, username: str):
        """用户登出"""
        # 实现登出逻辑，例如清除用户会话或令牌
        # TODO 清除用户环境
        operator = 'usr_logout'
        result = True
        message = 'Logout successful.'
        self.logger.info(f"Operator:'{operator}', Result:'{result}', Username:'{username}', Message:'{message}'")
        return {"result": result, "message": message, "username": username}
    
    
    async def _usr_unregister(self, username: str, password: str):
        """用户注销账户"""
        operator = 'usr_unregister'
        # try:
        #     loop = asyncio.get_event_loop()
        #     res = await loop.run_in_executor(self.executor, self.usr_account_database.delete_user, username, password)
        # except Exception as e:
        #     self.logger.error(f"Database error during unregistration for user '{username}': {e}")
        #     raise HTTPException(status_code=500, detail="Internal server error.")
        
        # if res:
        #     message = 'Unregistration successful.'
        #     self.logger.info(f"Operator:'{operator}', Result:'True', Username:'{username}', Message:'{message}'")
        #     return {"result": True, "message": message, "username": username}
        # else:
        #     message = 'Unregistration failed. Invalid credentials or user does not exist.'
        #     self.logger.info(f"Operator:'{operator}', Result:'False', Username:'{username}', Message:'{message}'")
        #     raise HTTPException(status_code=400, detail=message)
        
    def run(self):
            uvicorn.run(self.app, host=self.host, port=self.port)
            
        
 
def main():
    service = UserService()
    service.run()
    
    
if __name__ == "__main__":
    main()
    
    