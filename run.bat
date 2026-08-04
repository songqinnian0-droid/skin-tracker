@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ================================
echo   皮肤追踪器 - 一键运行
echo ================================
echo.

REM 首次运行装依赖
if not exist ".installed" (
    echo [首次运行] 正在安装依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 依赖安装失败，请检查网络或 pip
        pause
        exit /b 1
    )
    echo done > .installed
)

REM 跑爬取 + 启动本地网页服务器
python main.py

pause
