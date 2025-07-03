#!/usr/bin/env python3
"""
环境变量验证脚本 - 被子进程调用以验证环境变量是否正确传递
"""

import os
import sys
import json

def check_environment():
    """检查环境变量"""
    result = {
        "success": True,
        "environment": {},
        "errors": [],
        "python_path": sys.path
    }
    
    # 检查关键环境变量
    required_vars = ['AGENT_HOME', 'PYTHONPATH', 'AGENT_ENV']
    
    for var in required_vars:
        value = os.environ.get(var)
        result["environment"][var] = value
        
        if not value:
            result["success"] = False
            result["errors"].append(f"环境变量 {var} 未设置")
    
    # 检查 PYTHONPATH 是否包含 AGENT_HOME
    agent_home = os.environ.get('AGENT_HOME')
    pythonpath = os.environ.get('PYTHONPATH', '')
    
    if agent_home and agent_home not in pythonpath:
        result["success"] = False
        result["errors"].append(f"PYTHONPATH 不包含 AGENT_HOME: {agent_home}")
    
    # 测试模块导入
    try:
        # 添加 AGENT_HOME 到 sys.path
        if agent_home and agent_home not in sys.path:
            sys.path.insert(0, agent_home)
            
        from Module.Utils.Logger import setup_logger
        result["module_import"] = "SUCCESS"
    except ImportError as e:
        result["success"] = False
        result["module_import"] = f"FAILED: {str(e)}"
        result["errors"].append(f"模块导入失败: {str(e)}")
    
    return result

def main():
    """主函数"""
    result = check_environment()
    
    # 输出 JSON 格式结果
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 返回相应的退出码
    return 0 if result["success"] else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
