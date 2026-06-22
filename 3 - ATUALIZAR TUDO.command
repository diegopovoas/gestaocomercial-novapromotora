#!/bin/bash
# Faz TUDO de uma vez: baixa as bases (orquestrador) e depois gera/publica os dashboards.
BASE="$(cd "$(dirname "$0")" && pwd)"
CONSUMIR="$BASE/../Consumir dados banco de dados"
ORQ="$HOME/.storm_venvs/orquestrador/bin/python"
GEST="$HOME/.storm_venvs/gestao/bin/python"

if [ ! -d "$CONSUMIR" ]; then
    echo "ERRO: nao encontrei a pasta 'Consumir dados banco de dados' ao lado desta."
    echo ""
    read
    exit 1
fi

# ---------- PASSO 1/2: baixar bases ----------
if [ ! -f "$ORQ" ]; then
    echo "Primeira vez — instalando os robos (pode levar alguns minutos)..."
    echo ""
    bash "$CONSUMIR/setup_mac.sh" || { echo "Falha no setup dos robos."; read; exit 1; }
fi
echo "=================================================================="
echo "  PASSO 1/2 — Baixando bases dos sistemas e atualizando a Gestao"
echo "=================================================================="
( cd "$CONSUMIR" && "$ORQ" orquestrador.py )

# ---------- PASSO 2/2: atualizar dashboards ----------
if [ ! -f "$GEST" ]; then
    echo "Primeira vez — configurando o ambiente da Gestao..."
    python3 -m venv "$HOME/.storm_venvs/gestao"
    "$GEST" -m pip install --quiet --upgrade pip
    "$GEST" -m pip install --quiet pandas openpyxl
fi
echo ""
echo "=================================================================="
echo "  PASSO 2/2 — Gerando e publicando os dashboards"
echo "=================================================================="
( cd "$BASE/_sistema" && "$GEST" gerar_metas.py )

echo ""
echo "TUDO PRONTO. Pressione Enter para fechar..."
read
