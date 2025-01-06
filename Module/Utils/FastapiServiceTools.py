# Project:      Agent
# Author:       yomu
# Time:         2025/01/07
# Version:      0.1
# Description:  service tools

"""
    存放一些Fastapi微服务需要的一些通用函数
"""

import httpx
import asyncio
from logging import Logger
from fastapi import HTTPException
from typing import List, Dict
from pydantic import BaseModel

# --------------------------------
# 服务发现
# --------------------------------

# class GetServiceInstancesRequest(BaseModel):
#     consul_url: str
#     service_name: str
#     client: httpx.AsyncClient
#     logger: Logger
#     model_config = {"arbitrary_types_allowed": True}

    

async def get_service_instances(consul_url: str, service_name: str, client: httpx.AsyncClient,logger: Logger) -> List[Dict]:
    """从 Consul 拉取服务实例列表"""
    url = f"{consul_url}/v1/catalog/service/{service_name}"
    try:
        response = await client.get(url)
        if response.is_success:
            instances = [
                {"address": instance["Address"], "port": instance["ServicePort"]}
                for instance in response.json()
            ]
            if instances:
                logger.info(f"Successfully fetched service instances for '{service_name}' from Consul.")
                logger.debug(f"Service instances for '{service_name}': {instances}")
            else:
                logger.error(f"No service instances found for '{service_name}' in Consul.")
                # 可选择抛出异常或采取其他措施
                # raise ValueError(f"No service instances found for '{service_name}' in Consul.")
            return instances
        else:
            logger.warning(f"Failed to fetch service instances for '{service_name}': {response.status_code}")
    except httpx.RequestError as exc:
        logger.error(f"Error fetching service instances from Consul for '{service_name}': {exc}")
    return []
    
# --------------------------------
# 服务动态更新
# --------------------------------    

# class UpdateServiceInstancesPeriodicallyRequest(BaseModel):
#     service_instances: Dict[str, List[Dict]]
#     config: Dict
#     logger: Logger
#     model_config = {"arbitrary_types_allowed": True}
    

async def update_service_instances_periodically(consul_url: str, client: httpx.AsyncClient, service_instances: Dict[str, List[Dict]], config: Dict, logger: Logger):
    """后台任务：定期更新服务实例"""
    while True:
        try:
            logger.info("Updating service instances...")
            # 从配置中动态获取需要监控的服务列表
            services = config.get("services", ["UserService"])
            for service_name in services:
                instances = await get_service_instances(consul_url=consul_url,
                                                        service_name=service_name,
                                                        client=client,
                                                        logger=logger)
                service_instances[service_name] = instances
                logger.debug(f"Service '{service_name}' instances updated: {instances}")
        except Exception as e:
            logger.error(f"Error updating service instances: {e}")
        await asyncio.sleep(10)  # 每 10 秒更新一次   
        
    
# --------------------------------
#  Consul 服务注册
# --------------------------------

# class RegisterServiceToConsulRequest(BaseModel):
#     consul_url: str
#     client: httpx.AsyncClient
#     logger: Logger
#     service_name: str
#     service_id: str
#     address: str
#     port: int
#     health_check_url: str
#     retries: int=3
#     delay: float=2.0
#     model_config = {"arbitrary_types_allowed": True}
    
    
async def register_service_to_consul(consul_url: str, client: httpx.AsyncClient, logger: Logger, service_name: str, service_id: str, address: str, port: int, health_check_url: str, retries=3, delay=2.0):
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
            response = await client.put(f"{consul_url}/v1/agent/service/register", json=payload)
            if response.status_code == 200:
                logger.info(f"Service '{service_name}' registered successfully to Consul.")
                return
            else:
                logger.warning(f"Attempt {attempt}: Failed to register service '{service_name}': {response.status_code}, {response.text}")
        except Exception as e:
            logger.error(f"Attempt {attempt}: Error while registering service '{service_name}': {e}")
        
        if attempt < retries:
            logger.info(f"Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
    logger.error(f"All {retries} attempts to register service '{service_name}' failed.")
    raise HTTPException(status_code=500, detail="Service registration failed.")


# --------------------------------
#  Consul 服务注销
# --------------------------------
# class UnregisterServiceFromConsul(BaseModel):
#     consul_url: str
#     client: httpx.AsyncClient
#     logger: Logger
#     service_id: str
#     model_config = {"arbitrary_types_allowed": True}
    
    
async def unregister_service_from_consul(consul_url: str, client: httpx.AsyncClient, logger: Logger, service_id: str):
    """从 Consul 注销该微服务网关"""
    try:
        response = await client.put(f"{consul_url}/v1/agent/service/deregister/{service_id}")
        if response.status_code == 200:
            logger.info(f"Service with ID '{service_id}' deregistered successfully from Consul.")
        else:
            logger.warning(f"Failed to deregister service ID '{service_id}': {response.status_code}, {response.text}")
    except Exception as e:
        logger.error(f"Error while deregistering service ID '{service_id}': {e}")
