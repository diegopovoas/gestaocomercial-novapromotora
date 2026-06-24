#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETL — Excels locais → Supabase (Postgres via REST)

Lê os MESMOS arquivos que o gerar_metas.py e sobe para as tabelas do
Supabase. Não interfere no fluxo atual (GitHub Pages segue funcionando).

Config: _sistema/supabase_config.json (gitignored):
  { "url": "https://xxxx.supabase.co", "service_role_key": "eyJ..." }
"""
import sys, io, json, re, math
from pathlib import Path
from datetime import datetime, date

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import urllib.request
import urllib.error

SISTEMA_DIR = Path(__file__).parent
BASE_DIR    = SISTEMA_DIR.parent
CONFIG_FILE = SISTEMA_DIR / "supabase_config.json"

PROD_XLSX  = BASE_DIR / "producao_2026.xlsx"
DIG_XLSX   = BASE_DIR / "base_digitacoes.xlsx"
HIER_XLSX  = BASE_DIR / "HIERARQUIA COMERCIAL.xlsx"
MBANCO_XLSX = BASE_DIR / "meta_banco.xlsx"
MGLOBAL_XLSX = BASE_DIR / "config" / "meta_global_2026.xlsx"
CAL_XLSX   = BASE_DIR / "config" / "calendario.xlsx"

MESES_PT = {'jan':1,'fev':2,'mar':3,'abr':4,'mai':5,'jun':6,
            'jul':7,'ago':8,'set':9,'out':10,'nov':11,'dez':12}

# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def clean_name(s):
    s = str(s).strip()
    return s.split(" - ", 1)[1].strip() if " - " in s else s

def parse_mes(v):
    """Normaliza '2026-06', '06/2026', datetime → '2026-06'."""
    if pd.isna(v):
        return None
    if isinstance(v, (datetime, date, pd.Timestamp)):
        return f"{v.year:04d}-{v.month:02d}"
    s = str(v).strip()
    m = re.match(r'^(\d{4})[-/](\d{1,2})$', s)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
    m = re.match(r'^(\d{1,2})[-/](\d{4})$', s)
    if m:
        return f"{int(m.group(2)):04d}-{int(m.group(1)):02d}"
    return s[:7] if re.match(r'^\d{4}-\d{2}', s) else None

def _nan2none(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if pd.isna(v):
        return None
    return v

def _txt(v):
    v = _nan2none(v)
    return None if v is None else str(v).strip()

def _num(v):
    v = _nan2none(v)
    if v is None:
        return 0
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return 0

# ─────────────────────────────────────────────────────────────────────
# Cliente REST Supabase (sem dependências além da stdlib)
# ─────────────────────────────────────────────────────────────────────

class Supa:
    def __init__(self, url, key):
        self.base = url.rstrip('/') + '/rest/v1'
        self.headers = {
            'apikey': key,
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal',
        }

    def _req(self, method, path, body=None, extra_headers=None):
        h = dict(self.headers)
        if extra_headers:
            h.update(extra_headers)
        data = json.dumps(body).encode('utf-8') if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            detail = e.read().decode('utf-8', errors='replace')[:500]
            raise RuntimeError(f"{method} {path} → HTTP {e.code}: {detail}") from None

    def delete_where(self, table, query):
        """DELETE /table?<query> — query ex.: 'mes=eq.2026-06' ou 'id=gte.0'"""
        return self._req('DELETE', f'/{table}?{query}')

    def insert(self, table, rows, chunk=500):
        for i in range(0, len(rows), chunk):
            self._req('POST', f'/{table}', rows[i:i+chunk])

    def upsert(self, table, rows, on_conflict, chunk=500, resolution='merge-duplicates'):
        for i in range(0, len(rows), chunk):
            self._req('POST', f'/{table}?on_conflict={on_conflict}', rows[i:i+chunk],
                      {'Prefer': f'resolution={resolution},return=minimal'})

    def registrar_carga(self, tabela, linhas):
        self.upsert('cargas', [{
            'tabela': tabela,
            'atualizado_em': datetime.now().astimezone().isoformat(),
            'linhas': linhas,
        }], on_conflict='tabela')

# ─────────────────────────────────────────────────────────────────────
# Cargas
# ─────────────────────────────────────────────────────────────────────

def carga_producao(supa):
    if not PROD_XLSX.exists():
        print("  [PROD] producao_2026.xlsx não encontrado — pulado.")
        return
    df = pd.read_excel(PROD_XLSX)
    df.columns = [str(c).strip() for c in df.columns]
    col_mes = next((c for c in df.columns if 'ês' in c or 'Mes' in c or 'mes' in c.lower()), None)
    col_val = next((c for c in df.columns if 'Valor' in c), None)
    col_sta = next((c for c in df.columns if 'tatus' in c.lower()), None)
    col_tip = next((c for c in df.columns if 'ipo' in c.lower() and 'p' in c.lower()), None)

    rows = []
    for r in df.to_dict('records'):
        mes = parse_mes(r.get(col_mes))
        if not mes:
            continue
        sta = _nan2none(r.get(col_sta))
        rows.append({
            'mes': mes,
            'parceiro':        _txt(r.get('Parceiro')),
            'comercial':       clean_name(r['Comercial'])       if _nan2none(r.get('Comercial'))       else None,
            'regional':        clean_name(r['Regional'])        if _nan2none(r.get('Regional'))        else None,
            'superintendente': clean_name(r['Superintendente']) if _nan2none(r.get('Superintendente')) else None,
            'banco':           _txt(r.get('Banco')),
            'convenio':        _txt(r.get('Convenio')),
            'tipo_operacao':   _txt(r.get(col_tip)) if col_tip else None,
            'status_corretor': int(sta) if sta is not None else None,
            'valor':           _num(r.get(col_val)),
        })
    meses = sorted({r['mes'] for r in rows})
    for m in meses:
        supa.delete_where('producao', f'mes=eq.{m}')
    supa.insert('producao', rows)
    supa.registrar_carga('producao', len(rows))
    print(f"  [PROD] {len(rows)} linhas ({', '.join(meses)})")

def carga_digitacoes(supa):
    if not DIG_XLSX.exists():
        print("  [DIG] base_digitacoes.xlsx não encontrado — pulado.")
        return
    base = pd.read_excel(DIG_XLSX, sheet_name='Base')
    base.columns = [str(c).strip() for c in base.columns]

    def enc(*palavras):
        for c in base.columns:
            cl = c.lower()
            if all(p in cl for p in palavras):
                return c
        return None

    col_corretor = enc('corretor')
    col_banco    = enc('banco', 'empr')
    col_orgao    = enc('convenio') or enc('conv')
    col_operacao = enc('opera')
    col_status   = enc('status')
    col_data     = enc('data', 'digit', 'banco')
    col_valor    = enc('valor', 'base') or enc('produ', 'bruta') or enc('digit')

    df = base[[col_corretor, col_banco, col_orgao, col_operacao,
               col_status, col_data, col_valor]].copy()
    df.columns = ['corretor', 'banco', 'orgao', 'operacao', 'status', 'data', 'valor']

    # Hierarquia externa (mesmo cruzamento do gerar_metas)
    if HIER_XLSX.exists():
        hier = pd.read_excel(HIER_XLSX)
        hier.columns = [str(c).strip() for c in hier.columns]
        hier['_cod'] = hier['Cod Parceiro'].astype(str)
        df['_cod'] = df['corretor'].astype(str).str.extract(r'^(\d+)', expand=False).fillna('')
        df = df.merge(
            hier[['_cod', 'Comercial', 'Regional', 'Superintendente']].rename(
                columns={'Comercial': 'comercial', 'Regional': 'regional',
                         'Superintendente': 'superintendente'}),
            on='_cod', how='left').drop(columns=['_cod'])
    else:
        df['comercial'] = None; df['regional'] = None; df['superintendente'] = None

    def strip_prefix(s):
        s = _txt(s)
        return clean_name(s) if s else None

    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df = df.dropna(subset=['data'])

    rows = []
    for r in df.to_dict('records'):
        rows.append({
            'corretor':        _txt(r['corretor']),
            'comercial':       strip_prefix(r['comercial']),
            'regional':        strip_prefix(r['regional']),
            'superintendente': strip_prefix(r['superintendente']),
            'banco':           _txt(r['banco']),
            'orgao':           _txt(r['orgao']),
            'operacao':        _txt(r['operacao']),
            'status':          _txt(r['status']),
            'data':            r['data'].strftime('%Y-%m-%d'),
            'valor':           _num(r['valor']),
        })
    supa.delete_where('digitacoes', 'id=gte.0')
    supa.insert('digitacoes', rows)
    supa.registrar_carga('digitacoes', len(rows))
    print(f"  [DIG] {len(rows)} linhas")

def carga_hierarquia(supa):
    if not HIER_XLSX.exists():
        print("  [HIER] HIERARQUIA COMERCIAL.xlsx não encontrado — pulado.")
        return
    df = pd.read_excel(HIER_XLSX)
    df.columns = [str(c).strip() for c in df.columns]
    rows = []
    for r in df.to_dict('records'):
        rows.append({
            'cod_parceiro':       _txt(r.get('Cod Parceiro')),
            'parceiro':           _txt(r.get('Parceiro')),
            'multilojas_filiado': _txt(r.get('Multilojas Filiado')),
            'multilojas_master':  _txt(r.get('Multilojas Master')),
            'comercial':          clean_name(r['Comercial'])       if _nan2none(r.get('Comercial'))       else None,
            'regional':           clean_name(r['Regional'])        if _nan2none(r.get('Regional'))        else None,
            'superintendente':    clean_name(r['Superintendente']) if _nan2none(r.get('Superintendente')) else None,
            'status':             _txt(r.get('Status')),
        })
    supa.delete_where('hierarquia', 'id=gte.0')
    supa.insert('hierarquia', rows)
    supa.registrar_carga('hierarquia', len(rows))
    print(f"  [HIER] {len(rows)} linhas")

def carga_metas_global(supa):
    if not MGLOBAL_XLSX.exists():
        print("  [MGLOBAL] meta_global_2026.xlsx não encontrado — pulado.")
        return
    df = pd.read_excel(MGLOBAL_XLSX)
    df.columns = [str(c).strip() for c in df.columns]
    ano = 2026
    rows = []
    for r in df.to_dict('records'):
        sup = _nan2none(r.get('superintendente'))
        if not sup:
            continue
        for abrev, mnum in MESES_PT.items():
            if abrev in df.columns and _nan2none(r.get(abrev)) is not None:
                rows.append({
                    'mes': f"{ano:04d}-{mnum:02d}",
                    'superintendente': clean_name(sup),
                    'meta': _num(r[abrev]),
                })
    supa.delete_where('metas_global', 'id=gte.0')
    supa.insert('metas_global', rows)
    supa.registrar_carga('metas_global', len(rows))
    print(f"  [MGLOBAL] {len(rows)} linhas")

def carga_metas_banco(supa):
    if not MBANCO_XLSX.exists():
        print("  [MBANCO] meta_banco.xlsx não encontrado — pulado.")
        return
    metas = pd.read_excel(MBANCO_XLSX, sheet_name='metas', header=1)
    metas.columns = [str(c).strip() for c in metas.columns]
    rows_m = []
    for r in metas.to_dict('records'):
        mes = parse_mes(r.get('mes'))
        if not mes:
            continue
        rows_m.append({
            'mes': mes,
            'banco_display':   _txt(r.get('banco_display')),
            'banco_filtro':    _txt(r.get('banco_filtro')),
            'convenio_filtro': _txt(r.get('convenio_filtro')),
            'tipo_filtro':     _txt(r.get('tipo_filtro')),
            'meta_total':      _num(r.get('meta_total')),
        })
    supa.delete_where('metas_banco', 'id=gte.0')
    supa.insert('metas_banco', rows_m)

    coms = pd.read_excel(MBANCO_XLSX, sheet_name='comerciais', header=1)
    coms.columns = [str(c).strip() for c in coms.columns]
    rows_c = []
    for r in coms.to_dict('records'):
        mes = parse_mes(r.get('mes'))
        com = _nan2none(r.get('comercial'))
        if mes and com:
            rows_c.append({'mes': mes, 'comercial': clean_name(com)})
    supa.delete_where('metas_banco_comerciais', 'id=gte.0')
    supa.insert('metas_banco_comerciais', rows_c)
    supa.registrar_carga('metas_banco', len(rows_m) + len(rows_c))
    print(f"  [MBANCO] {len(rows_m)} metas + {len(rows_c)} comerciais")

def carga_calendario(supa):
    if not CAL_XLSX.exists():
        print("  [CAL] calendario.xlsx não encontrado — pulado.")
        return
    df = pd.read_excel(CAL_XLSX)
    df.columns = [str(c).strip() for c in df.columns]
    rows = []
    for r in df.to_dict('records'):
        mes = parse_mes(r.get('mes'))
        if mes:
            rows.append({'mes': mes, 'dias_uteis': int(r['dias_uteis'])})
    supa.upsert('calendario', rows, on_conflict='mes')
    supa.registrar_carga('calendario', len(rows))
    print(f"  [CAL] {len(rows)} linhas")

def carga_perfis(supa):
    auth_path = SISTEMA_DIR / 'auth.json'
    if not auth_path.exists():
        print("  [PERFIS] auth.json não encontrado — pulado.")
        return
    users = json.loads(auth_path.read_text(encoding='utf-8'))
    rows = [{
        'login':          u['login'] if '@' in u['login'] else f"{u['login']}@novapromotora.com",
        'nome':           u.get('nome', ''),
        'role':           u.get('role', 'super'),
        'entidade':       u.get('entidade') or None,
        'super_entidade': u.get('super_entidade') or None,
    } for u in users]
    # ignore-duplicates: o painel admin do app é o dono dos perfis existentes
    supa.upsert('perfis', rows, on_conflict='login', resolution='ignore-duplicates')
    supa.registrar_carga('perfis', len(rows))
    print(f"  [PERFIS] {len(rows)} usuários sincronizados (novos adicionados, edições preservadas)")

# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

CONV_PUB_JSON = BASE_DIR / "config" / "convenios_publicos.json"

def carga_convenios_publicos(supa):
    if not CONV_PUB_JSON.exists():
        print("  [CONV PUB] convenios_publicos.json não encontrado — pulado.")
        return
    cfg = json.loads(CONV_PUB_JSON.read_text(encoding='utf-8'))
    convenios = cfg.get('convenios', [])
    gestores = cfg.get('gestores', {})

    if convenios:
        rows_c = [{'convenio': c.strip(), 'ativo': True} for c in convenios if c.strip()]
        supa.delete_where('convenios_publicos_config', 'id=gte.0')
        supa.insert('convenios_publicos_config', rows_c)
        print(f"  [CONV PUB] {len(rows_c)} convênios configurados")
    else:
        print("  [CONV PUB] Nenhum convênio configurado")

    if gestores:
        rows_g = []
        for login, convs in gestores.items():
            for c in convs:
                rows_g.append({'login': login.lower().strip(), 'convenio': c.strip(), 'ativo': True})
        if rows_g:
            supa.delete_where('gestor_convenios_acesso', 'id=gte.0')
            supa.insert('gestor_convenios_acesso', rows_g)
            print(f"  [CONV PUB] {len(rows_g)} vínculos gestor↔convênio")

    supa.registrar_carga('convenios_publicos', len(convenios))

def main():
    print("\n=== ETL SUPABASE — GESTÃO COMERCIAL NOVA PROMOTORA ===\n")
    if not CONFIG_FILE.exists():
        print(f"[ERRO] Config não encontrada: {CONFIG_FILE}")
        print('Crie o arquivo com: {"url": "https://SEU-PROJETO.supabase.co", "service_role_key": "eyJ..."}')
        sys.exit(1)
    cfg = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
    supa = Supa(cfg['url'], cfg['service_role_key'])

    inicio = datetime.now()
    carga_calendario(supa)
    carga_hierarquia(supa)
    carga_producao(supa)
    carga_digitacoes(supa)
    carga_metas_global(supa)
    carga_metas_banco(supa)
    carga_convenios_publicos(supa)
    print(f"\n[OK] ETL concluído em {(datetime.now()-inicio).seconds}s")

if __name__ == '__main__':
    main()
