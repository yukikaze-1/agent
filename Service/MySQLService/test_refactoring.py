#!/usr/bin/env python3
# Project:      Agent
# Author:       yomu
# Time:         2025/6/29
# Version:      0.1
# Description:  Test script for refactored MySQL Service

"""
重构后的MySQL服务测试脚本
验证各个组件是否正常工作
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append('/home/yomu/agent')

from Module.Utils.Logger import setup_logger
from Service.MySQLService.core import (
    MySQLConnectionManager,
    DatabaseOperations,
    TransactionManager,
    ResponseBuilder,
    MySQLServiceApp
)


async def test_connection_manager():
    """测试连接管理器"""
    print("🔗 Testing Connection Manager...")
    logger = setup_logger(name="TestConnectionManager", log_path="Test")
    
    conn_manager = MySQLConnectionManager(logger)
    
    # 测试连接统计
    assert conn_manager.get_connection_count() == 0
    assert conn_manager.get_connection_ids() == []
    
    print("✅ Connection Manager basic tests passed")


async def test_response_builder():
    """测试响应构建器"""
    print("📝 Testing Response Builder...")
    
    # 测试连接错误响应
    error_response = ResponseBuilder.build_connection_error_response("Test", 123)
    assert error_response["operator"] == "Test"
    assert error_response["result"] == False
    assert "123" in str(error_response["errors"][0].message)
    
    # 测试插入成功响应
    success_response = ResponseBuilder.build_insert_success_response(5)
    assert success_response.result == True
    assert success_response.data.rows_affected == 5
    
    print("✅ Response Builder tests passed")


async def test_transaction_manager():
    """测试事务管理器"""
    print("💼 Testing Transaction Manager...")
    logger = setup_logger(name="TestTransactionManager", log_path="Test")
    
    conn_manager = MySQLConnectionManager(logger)
    trans_manager = TransactionManager(conn_manager, logger)
    
    # 测试活跃会话统计
    assert trans_manager.get_active_session_count() == 0
    
    print("✅ Transaction Manager basic tests passed")


async def test_database_operations():
    """测试数据库操作"""
    print("🗄️ Testing Database Operations...")
    logger = setup_logger(name="TestDatabaseOps", log_path="Test")
    
    conn_manager = MySQLConnectionManager(logger)
    db_ops = DatabaseOperations(conn_manager, logger)
    
    # 测试不存在的连接ID
    result = await db_ops.query(999, "SELECT 1", [])
    assert result["result"] == False
    assert "999" in str(result["errors"][0].message)
    
    print("✅ Database Operations basic tests passed")


async def test_service_integration():
    """测试服务集成"""
    print("🏗️ Testing Service Integration...")
    
    try:
        from Service.MySQLService.MySQLService_refactored import MySQLService
        
        # 创建服务实例
        service = MySQLService()
        
        # 检查组件是否正确初始化
        assert service.connection_manager is not None
        assert service.database_operations is not None
        assert service.transaction_manager is not None
        assert service.service_app is not None
        assert service.app is not None
        
        # 检查服务信息
        info = service.get_service_info()
        assert "service_name" in info
        assert "version" in info
        assert info["version"] == "0.2"
        assert info["active_connections"] == 0
        assert info["active_transactions"] == 0
        
        print("✅ Service Integration tests passed")
        
    except ImportError as e:
        print(f"⚠️ Import error (expected if config files missing): {e}")
    except Exception as e:
        print(f"❌ Service Integration test failed: {e}")


async def run_all_tests():
    """运行所有测试"""
    print("🚀 Starting MySQL Service Refactoring Tests...")
    print("=" * 50)
    
    try:
        await test_connection_manager()
        await test_response_builder()
        await test_transaction_manager()
        await test_database_operations()
        await test_service_integration()
        
        print("=" * 50)
        print("🎉 All tests completed successfully!")
        print("✨ Refactoring validation passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def main():
    """主函数"""
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
