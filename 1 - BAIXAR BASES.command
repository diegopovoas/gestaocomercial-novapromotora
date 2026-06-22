#!/bin/bash
# Passo 1: baixa as 3 bases dos sistemas e troca producao_2026 + base_digitacoes aqui na Gestao.
# (roda o orquestrador que fica na pasta irma "Consumir dados banco de dados")
BASE="$(cd "$(dirname "$0")" && pwd)"
CONSUMIR="$BASE/../Consumir dados banco de dados"
PYTHON="$HOME/.storm_venvs/orquestrador/bin/python"

if [ ! -d "$CONSUMIR" ]; then
    echo "ERRO: nao encontrei a pasta 'Consumir dados banco de dados' ao lado desta."
    echo ""
    read
    exit 1
fi

# Auto-configura os robos na primeira vez neste computador
if [ ! -f "$PYTHON" ]; then
    echo "Primeira vez neste computador — instalando os robos (pode levar alguns minutos)..."
    echo ""
    bash "$CONSUMIR/setup_mac.sh" || { echo "Falha no setup."; read; exit 1; }
    echo ""
fi

cd "$CONSUMIR"
"$PYTHON" orquestrador.py
echo ""
echo "Pressione Enter para fechar..."
read
