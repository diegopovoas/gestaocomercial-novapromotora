@echo off
title 1 - Baixar Bases - Nova Promotora
:: Passo 1: baixa as 3 bases e troca producao_2026 + base_digitacoes aqui na Gestao.
:: (roda o orquestrador da pasta irma "Consumir dados banco de dados")
set GESTAO=%~dp0
set CONSUMIR=%GESTAO%..\Consumir dados banco de dados
set PYTHON=%USERPROFILE%\.storm_venvs\orquestrador\Scripts\python.exe

if not exist "%CONSUMIR%" (
    echo ERRO: nao encontrei a pasta "Consumir dados banco de dados" ao lado desta.
    echo.
    pause
    exit /b 1
)

:: Auto-configura os robos na primeira vez neste computador
if not exist "%PYTHON%" (
    echo Primeira vez neste computador - instalando os robos ^(pode levar alguns minutos^)...
    echo.
    call "%CONSUMIR%\setup_windows.bat"
    echo.
)

cd /d "%CONSUMIR%"
"%PYTHON%" orquestrador.py
echo.
echo Pressione qualquer tecla para fechar...
pause > nul
