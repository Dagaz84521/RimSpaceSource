@echo off
REM RimSpace LLM Server 启动脚本

echo ============================================================
echo RimSpace Multi-Agent LLM Server
echo ============================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo [1/3] 检查虚拟环境...
if not exist "venv" (
    echo [创建] 正在创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
)

echo [2/3] 激活虚拟环境并安装依赖...
call venv\Scripts\activate.bat
pip install -r requirements.txt
if errorlevel 1 (
    echo [警告] 依赖安装可能未完全成功
)

echo [3/3] 启动服务器...
echo.
python LLMServer.py

pause
