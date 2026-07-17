@echo off
chcp 65001 >nul
title Sage + Ollama Launcher
echo ========================================
echo   Sage AI + Ollama LLM Starter
echo ========================================
echo.

REM Check if we're in the right directory
if not exist "backend\venv\Scripts\python.exe" (
    echo ERROR: Not in the 05_implementation directory.
    echo Please run this from: sage-core\05_implementation\
    pause
    exit /b 1
)

powershell -ExecutionPolicy Bypass -File "start_sage_with_ollama.ps1"

pause
