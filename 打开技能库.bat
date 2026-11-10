@echo off
setlocal
set "PAGE=%~dp0技能库.html"
if not exist "%PAGE%" (
  echo Cannot find: %PAGE%
  pause
  exit /b 1
)
rem 检查编辑服务器是否已在运行，没有则启动（保证保存功能可用）
curl -s -o nul -m 2 http://localhost:8917 >nul 2>&1
if errorlevel 1 (
  echo Starting edit server on port 8917 ...
  start "" /min node "%~dp0edit-server.js"
  timeout /t 1 /nobreak >nul
)
start "" http://localhost:8917
endlocal
