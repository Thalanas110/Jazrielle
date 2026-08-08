@echo off
setlocal

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-jazrielle.ps1"
if errorlevel 1 exit /b %errorlevel%
