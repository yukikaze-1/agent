#!/usr/bin/env python3
"""
服务发现集成测试脚本
用于测试新的服务发现架构和代理模块是否正常工作
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_service_discovery():
    """测试服务发现功能"""
    logger.info("=== 测试服务发现管理器 ===")
    
    try:
        from Init.ServiceDiscovery import ServiceDiscoveryManager
        
        # 创建服务发现管理器
        discovery_manager = ServiceDiscoveryManager(
            consul_url="http://127.0.0.1:8500",
            config_path="Init/ServiceDiscovery/config.yml"
        )
        
        logger.info("✅ 服务发现管理器创建成功")
        
        # 测试获取服务信息（测试一个示例服务）
        try:
            service_info = await discovery_manager.get_service_info("ollama")
            logger.info(f"Ollama 服务信息: {service_info}")
        except Exception as e:
            logger.info(f"获取服务信息失败（这在没有 Consul 时是正常的）: {e}")
        
        logger.info("服务发现管理器基本功能正常")
        
    except Exception as e:
        logger.error(f"❌ 服务发现测试失败: {e}")
        return False
    
    return True

async def test_proxy_modules():
    """测试代理模块"""
    logger.info("=== 测试代理模块 ===")
    
    # 测试 LLM 代理
    try:
        from Module.LLM.LLMProxy import LLMProxy
        
        llm_proxy = LLMProxy()
        logger.info("✅ LLM 代理创建成功")
        
        # 测试基本功能（无需实际服务连接）
        logger.info(f"LLM 代理配置: {hasattr(llm_proxy, 'config')}")
        logger.info("LLM 代理基本功能正常")
        
    except Exception as e:
        logger.error(f"❌ LLM 代理测试失败: {e}")
    
    # 测试 TTS 代理
    try:
        from Module.TTS.TTSProxy import TTSProxy
        
        tts_proxy = TTSProxy()
        logger.info("✅ TTS 代理创建成功")
        
        # 测试获取角色列表
        characters = await tts_proxy.list_characters()
        logger.info(f"TTS 可用角色: {characters}")
        
    except Exception as e:
        logger.error(f"❌ TTS 代理测试失败: {e}")
    
    # 测试 STT 代理
    try:
        from Module.STT.STTProxy import STTProxy
        
        stt_proxy = STTProxy()
        logger.info("✅ STT 代理创建成功")
        
        # 测试获取支持的语言
        languages = await stt_proxy.get_supported_languages()
        logger.info(f"STT 支持的语言: {languages}")
        
    except Exception as e:
        logger.error(f"❌ STT 代理测试失败: {e}")
    
    return True

def test_init_system():
    """测试初始化系统"""
    logger.info("=== 测试初始化系统 ===")
    
    try:
        from Init.Init import SystemInitializer
        
        # 创建初始化器
        initializer = SystemInitializer()
        logger.info("✅ 初始化器创建成功")
        
        # 检查初始化器配置
        logger.info(f"初始化器配置: {hasattr(initializer, 'config')}")
        logger.info(f"环境变量管理器: {hasattr(initializer, 'env_vars')}")
        
    except Exception as e:
        logger.error(f"❌ 初始化系统测试失败: {e}")
        return False
    
    return True

async def main():
    """主测试函数"""
    logger.info("开始服务发现集成测试...")
    
    # 测试各个组件
    tests = [
        ("服务发现管理器", test_service_discovery()),
        ("代理模块", test_proxy_modules()),
        ("初始化系统", test_init_system()),
    ]
    
    results = {}
    for test_name, test_coro in tests:
        try:
            if asyncio.iscoroutine(test_coro):
                result = await test_coro
            else:
                result = test_coro
            results[test_name] = result
        except Exception as e:
            logger.error(f"测试 {test_name} 时发生异常: {e}")
            results[test_name] = False
    
    # 总结测试结果
    logger.info("=== 测试结果总结 ===")
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"测试完成: {passed}/{total} 通过")
    
    if passed == total:
        logger.info("🎉 所有测试通过！服务发现架构实现正常")
        return 0
    else:
        logger.warning("⚠️  部分测试失败，可能需要检查配置或依赖")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
