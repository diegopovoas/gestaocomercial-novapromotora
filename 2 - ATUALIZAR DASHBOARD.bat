@echo off
title Atualizar Dashboard - Nova Promotora
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
echo === ATUALIZANDO DASHBOARD DE METAS ===
echo.
echo  Lendo Excel e gerando dashboards...
echo  Aguarde...
echo.
"%PYTHON%" _sistema\gerar_metas.py
echo.
pause
