@echo off
REM Project:      Agent
REM Author:       yomu  
REM Time:         2025/01/06
REM Version:      2.0
REM Description:  Agent 系统 Windows 启动脚本

setlocal enabledelayedexpansion

REM 设置颜色
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

REM 获取脚本所在目录
set "AGENT_ROOT=%~dp0"
set "AGENT_ROOT=%AGENT_ROOT:~0,-1%"
set "AGENT_MAIN=%AGENT_ROOT%\agent_v0.1.py"

REM 检查 Python 是否安装
:check_python
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ Python 未安装，请先安装 Python%NC%
    exit /b 1
)

REM 检查 Python 版本
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set python_version=%%i
echo %GREEN%✅ Python 检查通过: %python_version%%NC%
goto setup_environment

:setup_environment
REM 设置环境变量
set "AGENT_HOME=%AGENT_ROOT%"
set "PYTHONPATH=%AGENT_ROOT%;%PYTHONPATH%"
if not defined AGENT_ENV set "AGENT_ENV=development"

echo %GREEN%✅ 环境变量设置完成%NC%
echo %BLUE%📁 AGENT_HOME: %AGENT_HOME%%NC%
echo %BLUE%🐍 PYTHONPATH: %PYTHONPATH%%NC%
echo %BLUE%🏷️  AGENT_ENV: %AGENT_ENV%%NC%
goto main_logic

:show_help
echo %BLUE%Agent 系统启动脚本 (Windows)%NC%
echo.
echo 用法: %~n0 [选项]
echo.
echo 选项:
echo   start                    启动 Agent 系统 (默认开发模式)
echo   check                    仅执行环境检查
echo   help                     显示此帮助信息
echo.
echo 环境变量:
echo   set AGENT_ENV=production     设置运行环境
echo   set LOG_LEVEL=DEBUG          设置日志级别
echo.
echo 示例:
echo   %~n0 start               # 开发模式启动
echo   set AGENT_ENV=production ^&^& %~n0 start  # 生产模式启动
goto :eof

:start_agent
echo %YELLOW%🚀 启动 Agent 系统...%NC%
cd /d "%AGENT_ROOT%"
python "%AGENT_MAIN%" %*
goto :eof

:check_environment
echo %BLUE%🔍 执行环境检查...%NC%
cd /d "%AGENT_ROOT%"
python "%AGENT_MAIN%" --check-only
goto :eof

:main_logic
cd /d "%AGENT_ROOT%"

if "%1"=="start" (
    call :start_agent %*
) else if "%1"=="check" (
    call :check_environment
) else if "%1"=="help" (
    call :show_help
) else if "%1"=="" (
    REM 默认启动
    call :start_agent
) else (
    echo %RED%❌ 未知命令: %1%NC%
    echo.
    call :show_help
    exit /b 1
)

endlocal
