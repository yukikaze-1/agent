# Project:      Agent
# Author:       yomu
# Time:         2025/01/06
# Version:      0.2
# Description:  Agent 系统主入口

"""
Agent 系统主入口

这是 AI Agent 系统的唯一启动入口，负责：
1. 环境变量的自动设置和管理
2. 系统组件的统一初始化
3. 运行模式的控制和管理
4. 优雅的启动和关闭流程

使用方式：
    python agent_v0.1.py                    # 默认开发模式启动
    python agent_v0.1.py --env production   # 生产模式启动
    python agent_v0.1.py --daemon           # 后台模式启动
    python agent_v0.1.py --check-only       # 仅环境检查
"""

import os
import sys
import time
import argparse
import subprocess
import signal
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# 确保项目根目录在 Python 路径中
AGENT_ROOT = os.path.dirname(os.path.abspath(__file__))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

# 导入系统组件
from Init.Init import SystemInitializer
from Init.EnvironmentManager import EnvironmentManager, EnvironmentLevel


def setup_environment_variables(env_level: str = "development") -> bool:
    """
    设置环境变量
    
    Args:
        env_level: 环境级别 (development/testing/production)
        
    Returns:
        bool: 设置是否成功
    """
    try:
        # 设置基础环境变量
        os.environ["AGENT_HOME"] = AGENT_ROOT
        os.environ["AGENT_ENV"] = env_level
        
        # 设置 Python 路径
        current_pythonpath = os.environ.get("PYTHONPATH", "")
        if AGENT_ROOT not in current_pythonpath:
            if current_pythonpath:
                os.environ["PYTHONPATH"] = f"{AGENT_ROOT}:{current_pythonpath}"
            else:
                os.environ["PYTHONPATH"] = AGENT_ROOT
        
        # 加载全局环境文件（处理变量替换）
        global_env_path = os.path.join(AGENT_ROOT, ".env.global")
        if os.path.exists(global_env_path):
            load_dotenv(global_env_path, override=False)
            # 处理变量替换
            _expand_environment_variables()
        
        # 加载主环境文件
        main_env_path = os.path.join(AGENT_ROOT, ".env")
        if os.path.exists(main_env_path):
            load_dotenv(main_env_path, override=False)
            _expand_environment_variables()
        
        # 根据环境级别加载特定配置
        env_specific_path = os.path.join(AGENT_ROOT, f".env.{env_level}")
        if os.path.exists(env_specific_path):
            load_dotenv(env_specific_path, override=True)
            _expand_environment_variables()
        
        print(f"✅ 环境变量设置完成 (模式: {env_level})")
        print(f"📁 AGENT_HOME: {os.environ.get('AGENT_HOME')}")
        print(f"🐍 PYTHONPATH: {os.environ.get('PYTHONPATH')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 环境变量设置失败: {str(e)}")
        return False


def _expand_environment_variables():
    """
    展开环境变量中的变量引用
    处理 ${VAR_NAME} 格式的变量替换
    """
    import re
    
    # 需要处理的环境变量
    vars_to_expand = [
        'LOG_PATH', 'MODEL_CACHE_PATH', 'TEMP_PATH', 
        'API_KEY_FILE', 'SECRET_KEY_FILE', 'TEST_DATA_PATH'
    ]
    
    for var_name in vars_to_expand:
        var_value = os.environ.get(var_name)
        if var_value and '${' in var_value:
            # 替换 ${AGENT_HOME} 等变量引用
            expanded_value = re.sub(
                r'\$\{([^}]+)\}',
                lambda m: os.environ.get(m.group(1), m.group(0)),
                var_value
            )
            os.environ[var_name] = expanded_value


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="AI Agent 系统主入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s                           # 默认开发模式启动
  %(prog)s --env production          # 生产模式启动
  %(prog)s --daemon                  # 后台模式启动
  %(prog)s --check-only              # 仅环境检查
  %(prog)s --config custom.yml       # 使用自定义配置
        """
    )
    
    parser.add_argument(
        "--env", "--environment",
        choices=["development", "testing", "production"],
        default="development",
        help="运行环境模式 (默认: development)"
    )
    
    parser.add_argument(
        "--daemon", "-d",
        action="store_true",
        help="后台守护进程模式运行"
    )
    
    parser.add_argument(
        "--check-only", "-c",
        action="store_true",
        help="仅执行环境检查，不启动服务"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="指定配置文件路径"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别 (默认: INFO)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        help="指定主服务端口"
    )
    
    parser.add_argument(
        "--no-health-check",
        action="store_true",
        help="跳过健康检查"
    )
    
    return parser.parse_args()


class AgentDaemon:
    """Agent 守护进程管理器"""
    
    def __init__(self, initializer: SystemInitializer):
        self.initializer = initializer
        self.is_running = False
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理函数"""
        print(f"\n🔄 接收到信号 {signum}，正在优雅关闭...")
        self.is_running = False
    
    def run(self):
        """运行守护进程"""
        self.is_running = True
        print("🚀 Agent 系统以守护进程模式启动")
        
        try:
            while self.is_running:
                # 定期健康检查
                health = self.initializer.perform_health_check()
                if not health.get('overall_healthy', False):
                    print("⚠️  健康检查发现问题，详情请查看日志")
                
                # 等待一段时间后再次检查
                time.sleep(30)  # 30秒检查一次
                
        except Exception as e:
            print(f"❌ 守护进程运行错误: {str(e)}")
        finally:
            print("🔄 正在关闭守护进程...")
            self.initializer.shutdown_all()



def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 设置日志级别
        os.environ["LOG_LEVEL"] = args.log_level
        
        print("🚀 启动 Agent 系统...")
        print(f"📋 运行模式: {args.env}")
        print(f"📊 日志级别: {args.log_level}")
        
        # 设置环境变量
        if not setup_environment_variables(args.env):
            print("❌ 环境变量设置失败")
            return 1
        
        # 创建系统初始化器
        initializer = SystemInitializer(config_path=args.config)
        
        # 如果只是环境检查
        if args.check_only:
            print("🔍 执行环境检查...")
            env_manager = EnvironmentManager(
                base_path=AGENT_ROOT,
                env_level=EnvironmentLevel(args.env)
            )
            success, results = env_manager.check_all_environment()
            
            print("\n📋 环境检查结果:")
            for result in results:
                status = "✅" if result.success else "❌"
                print(f"{status} {result.category}: {result.message}")
                if not result.success and result.suggestions:
                    for suggestion in result.suggestions:
                        print(f"   💡 建议: {suggestion}")
            
            return 0 if success else 1
        
        # 执行完整初始化
        print("🔧 开始系统初始化...")
        result = initializer.initialize_all()
        
        if not result.success:
            print(f"❌ {result.message}")
            if result.failed_components:
                print(f"失败组件: {result.failed_components}")
            return 1
        
        print(f"✅ {result.message}")
        
        # 显示系统状态
        if not args.daemon:
            status = initializer.get_system_status()
            print(f"📊 系统状态: 服务 {status.get('started_services', 0)} 个，模块 {status.get('started_modules', 0)} 个")
        
        # 执行健康检查
        if not args.no_health_check:
            health = initializer.perform_health_check()
            health_status = "健康" if health.get('overall_healthy', False) else "存在问题"
            print(f"🏥 健康状态: {health_status}")
        
        # 根据模式运行
        if args.daemon:
            # 守护进程模式
            daemon = AgentDaemon(initializer)
            daemon.run()
        else:
            # 交互模式
            print("\n" + "="*50)
            print("🎉 Agent 系统启动完成！")
            print("💡 可用命令:")
            print("   status  - 查看系统状态")
            print("   health  - 执行健康检查")
            print("   quit    - 退出系统")
            print("="*50)
            
            # 交互式控制循环
            while True:
                try:
                    cmd = input("\nAgent> ").strip().lower()
                    
                    if cmd in ['quit', 'exit', 'q']:
                        break
                    elif cmd == 'status':
                        status = initializer.get_system_status()
                        print(f"📊 系统状态: {status}")
                    elif cmd == 'health':
                        health = initializer.perform_health_check()
                        print(f"🏥 健康检查: {health}")
                    elif cmd == 'help':
                        print("💡 可用命令: status, health, quit")
                    elif cmd == '':
                        continue
                    else:
                        print(f"❓ 未知命令: {cmd}，输入 'help' 查看可用命令")
                        
                except EOFError:
                    break
                except KeyboardInterrupt:
                    print("\n⚠️  收到中断信号...")
                    break
        
        # 关闭系统
        print("\n🔄 正在关闭系统...")
        shutdown_success = initializer.shutdown_all()
        
        if shutdown_success:
            print("✅ 系统已安全关闭")
            return 0
        else:
            print("⚠️  系统关闭时出现错误")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  用户中断，正在关闭系统...")
        if 'initializer' in locals():
            initializer.shutdown_all()
        return 130  # 标准的键盘中断退出码
    except Exception as e:
        print(f"❌ 系统启动失败: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
