#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE 2 — Publica os payloads do dashboard no Supabase (dashboard_cache).

Normalmente não precisa rodar manualmente: o gerar_metas.py já publica
automaticamente ao final de cada atualização. Este script existe para
republicar sem regenerar os HTMLs do GitHub Pages.
"""
import sys
from pathlib import Path

SISTEMA_DIR = Path(__file__).parent
sys.path.insert(0, str(SISTEMA_DIR))

import gerar_metas  # reusa todo o pipeline


def main():
    print("\n=== PUBLICAR DASHBOARD NO SUPABASE ===\n")
    print("Processando dados...")
    result = gerar_metas.processar()
    data = result[0]

    print("Processando digitações...")
    dig_records, dig_estrat_json, dig_periodo = gerar_metas.processar_digitacoes()

    print("Publicando payloads...")
    gerar_metas._publicar_supabase(data, dig_records, dig_estrat_json, dig_periodo)
    print("\n[OK] Concluído!")


if __name__ == '__main__':
    main()
