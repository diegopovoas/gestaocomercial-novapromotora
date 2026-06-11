@echo off
title Atualizar Supabase - Nova Promotora
cd /d "%~dp0"
echo.
echo === ENVIANDO DADOS BRUTOS PARA O SUPABASE ===
echo.
python _sistema\supabase_etl.py
echo.
echo === PUBLICANDO PAYLOADS DO DASHBOARD ===
echo.
python _sistema\supabase_publicar.py
echo.
pause
