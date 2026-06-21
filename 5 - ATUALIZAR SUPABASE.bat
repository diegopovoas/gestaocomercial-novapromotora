@echo off
title Atualizar Supabase - Nova Promotora
cd /d "%~dp0"
set VENV=%USERPROFILE%\.storm_venvs\gestao
set PYTHON=%VENV%\Scripts\python.exe

:: Auto-configura na primeira vez neste Windows (cria o ambiente Python da Gestao)
if not exist "%PYTHON%" (
    echo Primeira vez neste computador - configurando o ambiente ^(1-2 min^)...
    echo.
    python -m venv "%VENV%"
    if not exist "%PYTHON%" (
        echo ERRO: Python nao encontrado neste Windows.
        echo Instale o Python em https://www.python.org/downloads/  ^(marque "Add Python to PATH"^)
        echo.
        pause
        exit /b 1
    )
    "%PYTHON%" -m pip install --quiet --upgrade pip
    "%PYTHON%" -m pip install --quiet pandas openpyxl
    echo Ambiente configurado.
    echo.
)

echo.
echo === ENVIANDO DADOS BRUTOS PARA O SUPABASE ===
echo.
"%PYTHON%" _sistema\supabase_etl.py
echo.
echo === PUBLICANDO PAYLOADS DO DASHBOARD ===
echo.
"%PYTHON%" _sistema\supabase_publicar.py
echo.
pause
