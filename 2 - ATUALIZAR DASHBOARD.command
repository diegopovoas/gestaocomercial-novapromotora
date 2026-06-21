#!/bin/bash
BASE="$(cd "$(dirname "$0")" && pwd)"
VENV="$HOME/.storm_venvs/gestao"
PYTHON="$VENV/bin/python"

# Auto-configura na primeira vez neste Mac (cria o ambiente Python da Gestao)
if [ ! -f "$PYTHON" ]; then
    echo "Primeira vez neste computador — configurando o ambiente (1-2 min)..."
    echo ""
    if ! command -v python3 >/dev/null 2>&1; then
        echo "ERRO: Python nao encontrado neste Mac."
        echo "Instale com:  brew install python   (ou baixe em https://www.python.org)"
        echo ""
        read
        exit 1
    fi
    python3 -m venv "$VENV"
    "$PYTHON" -m pip install --quiet --upgrade pip
    "$PYTHON" -m pip install --quiet pandas openpyxl
    echo "Ambiente configurado."
    echo ""
fi

cd "$BASE/_sistema"
echo "Atualizando dashboard..."
echo ""
"$PYTHON" gerar_metas.py
echo ""
echo "Pressione Enter para fechar..."
read
