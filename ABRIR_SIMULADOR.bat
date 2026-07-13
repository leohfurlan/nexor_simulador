@echo off
setlocal
title Nexor - Simulador Tributario

cd /d "%~dp0"

where powershell.exe >nul 2>nul
if errorlevel 1 (
    echo ERRO: O Windows PowerShell nao foi encontrado neste computador.
    echo Entre em contato com o suporte responsavel pelo Nexor.
    echo.
    pause
    exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar_simulador.ps1"
set "RESULTADO=%ERRORLEVEL%"

if not "%RESULTADO%"=="0" (
    echo.
    echo O simulador nao conseguiu iniciar.
    echo Fotografe esta tela e envie ao suporte responsavel pelo Nexor.
    echo.
    pause
)

exit /b %RESULTADO%
