@echo off
chcp 65001 >nul
cd /d "%~dp0"
REM 只启动网页服务器，不重新爬取（用于快速查看已有数据）
python main.py serve
