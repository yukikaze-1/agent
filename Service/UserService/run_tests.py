#!/usr/bin/env python3
"""
测试运行脚本
分阶段运行测试，避免一次性运行所有测试导致的错误堆积
"""

import subprocess
import sys
import os

def prepare_environment():
    """准备测试环境变量"""
    env = os.environ.copy()
    
    # 自动检测项目根目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 从 Service/UserService 向上两级到达项目根目录
    agent_home = os.path.dirname(os.path.dirname(current_dir))
    
    # 确保 AGENT_HOME 存在
    if 'AGENT_HOME' not in env:
        env['AGENT_HOME'] = agent_home
    
    # 确保 PYTHONPATH 包含项目根目录
    agent_home = env['AGENT_HOME']
    current_pythonpath = env.get('PYTHONPATH', '')
    if agent_home not in current_pythonpath:
        if current_pythonpath:
            env['PYTHONPATH'] = f"{agent_home}:{current_pythonpath}"
        else:
            env['PYTHONPATH'] = agent_home
    
    # 设置测试环境
    env['AGENT_ENV'] = 'testing'
    
    return env

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    
    # 准备环境变量
    env = prepare_environment()
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            cwd=os.path.join(env['AGENT_HOME'], "Service", "UserService"),
            env=env  # 传递环境变量
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - 通过")
            if result.stdout:
                print("输出:")
                print(result.stdout)
        else:
            print(f"❌ {description} - 失败")
            if result.stdout:
                print("标准输出:")
                print(result.stdout)
            if result.stderr:
                print("错误输出:")
                print(result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 执行命令时出错: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始分阶段测试运行...")
    
    # 测试计划
    test_stages = [
        # 阶段1: 基础语法检查
        ("python -m py_compile tests/conftest.py", "配置文件语法检查"),
        
        # 阶段2: 单个测试文件检查
        ("pytest tests/api/test_user_api.py::TestUserAPI::test_health_check -v", "健康检查API测试"),
        ("pytest tests/unit/test_auth_service.py::TestUserAuthService::test_verify_token_missing_user_id -v", "认证服务单元测试"),
        
        # 阶段3: 完整单元测试
        ("pytest tests/unit/test_auth_service.py -v --tb=short", "认证服务完整测试"),
        ("pytest tests/unit/test_account_service.py -v --tb=short", "账户服务完整测试"),
        
        # 阶段4: API测试
        ("pytest tests/api/ -v --tb=short", "API测试套件"),
        
        # 阶段5: 其他测试
        ("pytest tests/unit/test_db_agents.py -v --tb=short", "数据库代理测试"),
        ("pytest tests/integration/ -v --tb=short", "集成测试"),
        ("pytest tests/performance/ -v --tb=short", "性能测试"),
    ]
    
    passed = 0
    failed = 0
    
    for cmd, description in test_stages:
        if run_command(cmd, description):
            passed += 1
        else:
            failed += 1
        
        # 询问是否继续
        if failed > 0:
            continue_test = input(f"\n⚠️  当前阶段测试失败。是否继续下一阶段？(y/n): ").lower().strip()
            if continue_test != 'y':
                break
    
    print(f"\n{'='*60}")
    print(f"📊 测试结果汇总")
    print(f"{'='*60}")
    print(f"✅ 通过的阶段: {passed}")
    print(f"❌ 失败的阶段: {failed}")
    print(f"📈 总通过率: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("🎉 所有测试阶段都通过了！")
    else:
        print("🔧 需要修复的测试阶段请参考上面的错误信息")

if __name__ == "__main__":
    main()
