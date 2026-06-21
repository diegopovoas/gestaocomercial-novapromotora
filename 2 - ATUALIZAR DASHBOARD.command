#!/bin/bash
BASE="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$HOME/.storm_venvs/gestao/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo "ERRO: ambiente Python da Gestao nao encontrado."
    echo "Crie com:"
    echo "  python3 -m venv \"\$HOME/.storm_venvs/gestao\""
    echo "  \"\$HOME/.storm_venvs/gestao/bin/python\" -m pip install pandas openpyxl"
    echo ""
    read
    exit 1
fi

cd "$BASE/_sistema"
echo "Atualizando dashboard..."
echo ""
"$PYTHON" gerar_metas.py
echo ""
echo "Pressione Enter para fechar..."
read
