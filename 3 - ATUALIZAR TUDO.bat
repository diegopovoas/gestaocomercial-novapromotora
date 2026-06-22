@echo off
title 3 - Atualizar Tudo - Nova Promotora
:: Faz TUDO de uma vez: baixa as bases (orquestrador) e depois gera/publica os dashboards.
set GESTAO=%~dp0
set CONSUMIR=%GESTAO%..\Consumir dados banco de dados
set ORQ=%USERPROFILE%\.storm_venvs\orquestrador\Scripts\python.exe
set GEST=%USERPROFILE%\.storm_venvs\gestao\Scripts\python.exe

if not exist "%CONSUMIR%" (
    echo ERRO: nao encontrei a pasta "Consumir dados banco de dados" ao lado desta.
    echo.
    pause
    exit /b 1
)

:: ---------- PASSO 1/2: baixar bases ----------
if not exist "%ORQ%" (
    echo Primeira vez - instalando os robos ^(pode levar alguns minutos^)...
    echo.
    call "%CONSUMIR%\setup_windows.bat"
)
echo ==================================================================
echo   PASSO 1/2 - Baixando bases dos sistemas e atualizando a Gestao
echo ==================================================================
cd /d "%CONSUMIR%"
"%ORQ%" orquestrador.py

:: ---------- PASSO 2/2: atualizar dashboards ----------
if not exist "%GEST%" (
    echo Primeira vez - configurando o ambiente da Gestao...
    python -m venv "%USERPROFILE%\.storm_venvs\gestao"
    "%GEST%" -m pip install --quiet --upgrade pip
    "%GEST%" -m pip install --quiet pandas openpyxl
)
echo.
echo ==================================================================
echo   PASSO 2/2 - Gerando e publicando os dashboards
echo ==================================================================
cd /d "%GESTAO%_sistema"
"%GEST%" gerar_metas.py

echo.
echo TUDO PRONTO. Pressione qualquer tecla para fechar...
pause > nul
