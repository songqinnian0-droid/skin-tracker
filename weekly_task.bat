@echo off
REM 静默版：只爬取，不启动网页。用于每周任务计划自动运行。
REM 日志会追加到 logs\weekly.log
chcp 65001 >nul
cd /d "%~dp0"

if not exist "logs" mkdir logs

echo. >> logs\weekly.log
echo ========== %date% %time% ========== >> logs\weekly.log
python main.py fetch >> logs\weekly.log 2>&1
