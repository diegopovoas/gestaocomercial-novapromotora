@echo off
title Atualizar Dashboard - Nova Promotora
cd /d "%~dp0"
echo.
echo === ATUALIZANDO DASHBOARD DE METAS ===
echo.
echo  Lendo Excel e gerando dashboards...
echo  Aguarde...
echo.
python _sistema\gerar_metas.py
echo.
pause
