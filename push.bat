@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ================================
echo   推送本地数据到 GitHub Pages
echo ================================
echo.

REM 用完整路径调用 git（不依赖 PATH）
set GIT="C:\Program Files\Git\bin\git.exe"
if not exist %GIT% (
    set GIT=git
)

REM 只提交数据文件的变化
%GIT% add skins.db data.json
%GIT% diff --cached --quiet
if %errorlevel% == 0 (
    echo 数据没有变化，无需推送
    pause
    exit /b 0
)

for /f "tokens=1-3 delims=/- " %%a in ('date /t') do set today=%%a-%%b-%%c
%GIT% commit -m "chore: manual update %today%"
if errorlevel 1 (
    echo 提交失败
    pause
    exit /b 1
)

%GIT% push
if errorlevel 1 (
    echo 推送失败，请检查网络或 GitHub 认证
    pause
    exit /b 1
)

echo.
echo ================================
echo  推送成功！网站将在 1-2 分钟后更新
echo  https://songqinnian0-droid.github.io/skin-tracker/
echo ================================
pause
