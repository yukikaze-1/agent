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
from typing import List, Dict, TypedDict, Optional
from pydantic import BaseModel
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis  # 使用异步 Redis 客户端


# --------------------------------
# 服务发现
# --------------------------------

# class GetServiceInstancesRequest(BaseModel):
#     consul_url: str
#     service_name: str
#     client: httpx.AsyncClient
#     logger: Logger
#     model_config = {"arbitrary_types_allowed": True}

class ServiceInstance(TypedDict):
    address: str
    port: int
    

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
            services = config.get("services")
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
    
   
async def register_service_to_consul(consul_url: str,
                                     client: httpx.AsyncClient,
                                     logger: Logger, service_name: str,
                                     service_id: str, address: str,
                                     port: int,
                                     tags: List[str],
                                     health_check_url: str,
                                     retries=3,
                                     delay=2.0):
    """向 Consul 注册该微服务网关"""
    payload = {
        "Name": service_name,
        "ID": service_id,
        "Address": address,
        "Port": port,
        "Tags": [tag for tag in tags],
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
        

# --------------------------------
# 负载均衡
# --------------------------------
def get_next_instance(service_instances: Dict[str, List[Dict]], service_name: str, load_balancer_index: Dict[str, int], logger: Logger) -> Optional[Dict]:
    """获取服务的下一个实例（轮询负载均衡）"""
    instances = service_instances.get(service_name, [])
    if not instances:
        logger.warning(f"No instances found for service '{service_name}'.")
        return None
    index = load_balancer_index[service_name]
    instance = instances[index]
    load_balancer_index[service_name] = (index + 1) % len(instances)
    logger.debug(f"Selected instance {instance} for service '{service_name}'")
    return instance


# --------------------------------
# 熔断机制
# --------------------------------
def is_instance_healthy(service_name: str, instance: Dict, failure_counts: Dict[str, Dict[str, int]], logger: Logger) -> bool:
    """检查服务实例是否健康"""
    failure_threshold = 3  # 设置失败阈值
    instance_key = f"{instance['address']}:{instance['port']}"
    is_healthy = failure_counts[service_name][instance_key] < failure_threshold
    logger.debug(f"Instance {instance_key} healthy: {is_healthy}")
    return is_healthy


def record_failure(service_name: str, instance: Dict, failure_counts: Dict[str, Dict[str, int]], logger: Logger):
    """记录服务实例的失败次数"""
    instance_key = f"{instance['address']}:{instance['port']}"
    failure_counts[service_name][instance_key] += 1
    logger.warning(f"Recorded failure for {service_name} instance {instance_key}. Total failures: {failure_counts[service_name][instance_key]}")


def reset_failure(service_name: str, instance: Dict, failure_counts: Dict[str, Dict[str, int]], logger: Logger):
    """重置服务实例的失败计数"""
    instance_key = f"{instance['address']}:{instance['port']}"
    failure_counts[service_name][instance_key] = 0
    logger.info(f"Reset failure count for {service_name} instance {instance_key}.")


# --------------------------------
# 限流机制
# --------------------------------
async def setup_redis_limiter(config: Dict, logger: Logger):
    """初始化 Redis 用于限流"""
    redis_host = config.get("redis_host", "127.0.0.1")
    redis_port = config.get("redis_port", 6379)
    redis_db = config.get("redis_db", 0)
    try:
        redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
        await FastAPILimiter.init(redis_client)
        logger.info("FastAPILimiter initialized successfully.")
    except Exception as e:
        await redis_client.aclose()
        logger.error(f"Failed to initialize FastAPILimiter: {e}")
        raise    
    
    # 测试连接
    await redis_client.ping()
    logger.info("Redis connection successful.")
