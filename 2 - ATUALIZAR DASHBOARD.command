#!/bin/bash
BASE="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE/_sistema"
echo "Atualizando dashboard..."
echo ""
python3 gerar_metas.py
echo ""
echo "Pressione Enter para fechar..."
read
