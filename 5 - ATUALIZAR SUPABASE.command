#!/bin/bash
BASE="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE/_sistema"
echo "Publicando no Supabase..."
echo ""
python3 supabase_etl.py && python3 supabase_publicar.py
echo ""
echo "Pressione Enter para fechar..."
read
