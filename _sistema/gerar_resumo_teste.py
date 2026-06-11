#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROTÓTIPO (não publicado) — Tela de entrada "Visão Executiva".
Analisa a carteira e gera: saúde do mês, pontos positivos, pontos de
atenção e um plano de ação sugerido. Saída: teste_resumo.html (local).
"""
import sys
from pathlib import Path

SISTEMA_DIR = Path(__file__).parent
BASE_DIR    = SISTEMA_DIR.parent
sys.path.insert(0, str(SISTEMA_DIR))

import gerar_metas


def brl(v):
    if v is None:
        return '—'
    return 'R$ ' + f'{v:,.0f}'.replace(',', '.')


def m(v):
    if v is None:
        return '—'
    a = abs(v)
    s = '-' if v < 0 else ''
    if a >= 1e9: return f'{s}{a/1e9:.2f}B'
    if a >= 1e6: return f'{s}{a/1e6:.1f}M'
    if a >= 1e3: return f'{s}{a/1e3:.0f}k'
    return f'{s}{a:.0f}'


def analisar(data):
    emp  = data['empresa']
    info = data['info']
    cart = data.get('carteira', {})
    R    = cart.get('resumo', {})

    du_t, du_p = info['dias_uteis_total'], info['dias_uteis_passados']
    du_rest = max(du_t - du_p, 0)

    meta  = emp.get('meta_global_total') or 0
    prod  = emp.get('prod_total') or 0
    proj  = emp.get('proj_total') or 0
    pct   = emp.get('pct_total')
    gap   = emp.get('gap_total') or (meta - proj)

    ritmo_atual = prod / du_p if du_p else 0
    ritmo_nec   = (meta - prod) / du_rest if du_rest else 0

    # churn
    churn = cart.get('churn', [])
    churn_val = sum((c.get('prod_ant') or 0) for c in churn)
    top_churn = churn[:5]

    # abaixo do target / produzindo / novos
    below, producing, todos_parc = [], 0, []
    for s in cart.get('supers', []):
        for r in s.get('regionais', []):
            for c in r.get('comerciais', []):
                for p in c.get('parceiros', []):
                    pj = p.get('proj') or 0
                    if p.get('churn') or pj <= 0:
                        continue
                    producing += 1
                    todos_parc.append((p['nome'], pj, s['nome']))
                    if pj < 25000:
                        below.append(p)

    # concentração: top 10 parceiros
    todos_parc.sort(key=lambda x: -x[1])
    top10_val = sum(v for _, v, _ in todos_parc[:10])
    conc = (top10_val / proj * 100) if proj else 0

    # bancos: maior queda e maior alta (com volume relevante)
    bancos = [b for b in cart.get('por_banco', []) if (b.get('ant') or 0) > 300000]
    bancos_q = sorted([b for b in bancos if (b.get('pct') or 0) < -15], key=lambda b: b['pct'])[:3]
    bancos_a = sorted([b for b in bancos if (b.get('pct') or 0) > 15], key=lambda b: -b['pct'])[:3]

    # supers por atingimento da meta global
    sups = [s for s in data.get('supers', []) if s.get('meta_global')]
    sups_ok   = sorted([s for s in sups if (s.get('pct_global') or 0) >= 100], key=lambda s: -(s['pct_global'] or 0))
    sups_risco = sorted([s for s in sups if (s.get('pct_global') or 0) < 85], key=lambda s: (s['pct_global'] or 0))

    return dict(
        info=info, meta=meta, prod=prod, proj=proj, pct=pct, gap=gap,
        du_t=du_t, du_p=du_p, du_rest=du_rest,
        ritmo_atual=ritmo_atual, ritmo_nec=ritmo_nec,
        n_churn=R.get('n_churn', len(churn)), churn_val=churn_val, top_churn=top_churn,
        n_below=len(below), producing=producing, n_novos=R.get('n_novos', 0),
        conc=conc, bancos_q=bancos_q, bancos_a=bancos_a,
        sups_ok=sups_ok, sups_risco=sups_risco,
        pct_carteira=R.get('pct_proj_ant'),
    )


def montar_html(a):
    pos, neg, acoes = [], [], []

    # ── Positivos ──
    if a['pct'] is not None and a['pct'] >= 100:
        pos.append(f"<b>Meta global no ritmo</b> — projeção em {a['pct']:.0f}% da meta ({m(a['proj'])} vs {m(a['meta'])}).")
    if a['ritmo_atual'] >= a['ritmo_nec'] > 0:
        pos.append(f"<b>Ritmo diário saudável</b> — {m(a['ritmo_atual'])}/dia atual vs {m(a['ritmo_nec'])}/dia necessário para fechar a meta.")
    for s in a['sups_ok'][:3]:
        pos.append(f"<b>{s['nome'].title()}</b> projeta {s['pct_global']:.0f}% da meta — destaque do mês.")
    if a['n_novos'] > 0:
        pos.append(f"<b>{a['n_novos']} parceiros reativados/novos</b> produzindo este mês — energia nova na carteira.")
    for b in a['bancos_a']:
        pos.append(f"<b>{b['nome']}</b> em alta: projeção {b['pct']:+.0f}% vs mês anterior ({m(b['proj'])}).")
    if a['pct_carteira'] is not None and a['pct_carteira'] > 0:
        pos.append(f"<b>Carteira crescendo</b> — projeção {a['pct_carteira']:+.1f}% sobre o mês anterior.")
    if not pos:
        pos.append("Sem destaques positivos relevantes neste corte — atenção total ao plano de ação.")

    # ── Atenção ──
    if a['pct'] is not None and a['pct'] < 100:
        neg.append(f"<b>GAP de {m(a['gap'])}</b> para a meta global — projeção em {a['pct']:.0f}%.")
    if a['ritmo_nec'] > a['ritmo_atual'] > 0:
        delta = a['ritmo_nec'] / a['ritmo_atual'] - 1
        neg.append(f"<b>Ritmo insuficiente</b> — é preciso {m(a['ritmo_nec'])}/dia nos {a['du_rest']} dias úteis restantes ({delta:+.0%} sobre o ritmo atual de {m(a['ritmo_atual'])}/dia).")
    if a['n_churn'] > 0:
        neg.append(f"<b>{a['n_churn']} parceiros em churn</b> — produziam {m(a['churn_val'])} no mês anterior e zeraram.")
    if a['n_below'] > 0 and a['producing'] > 0:
        neg.append(f"<b>{a['n_below']} parceiros abaixo do target</b> de R$ 25 mil ({a['n_below']/a['producing']:.0%} dos {a['producing']} que produzem).")
    for s in a['sups_risco'][:3]:
        neg.append(f"<b>{s['nome'].title()}</b> em risco: {(s['pct_global'] or 0):.0f}% da meta, GAP de {m(s.get('gap_global'))}.")
    for b in a['bancos_q']:
        neg.append(f"<b>{b['nome']}</b> em queda: projeção {b['pct']:+.0f}% vs mês anterior.")
    if a['conc'] > 35:
        neg.append(f"<b>Concentração alta</b> — os 10 maiores parceiros respondem por {a['conc']:.0f}% da projeção.")

    # ── Plano de ação ──
    if a['top_churn']:
        nomes = ', '.join(c['parceiro'].split(' - ', 1)[-1].title() for c in a['top_churn'][:3])
        val5 = sum((c.get('prod_ant') or 0) for c in a['top_churn'])
        acoes.append(f"<b>Resgate de churn (esta semana):</b> contato direto com os 5 maiores que zeraram — juntos valiam {m(val5)}/mês. Começar por: {nomes}.")
    if a['ritmo_nec'] > a['ritmo_atual']:
        acoes.append(f"<b>Cadência diária:</b> acompanhar produção D-1 contra o alvo de {m(a['ritmo_nec'])}/dia. Cobrar plano de recuperação dos supers abaixo de 85%.")
    if a['sups_risco']:
        s0 = a['sups_risco'][0]
        acoes.append(f"<b>War room com {s0['nome'].title()}:</b> menor atingimento ({(s0['pct_global'] or 0):.0f}%). Revisar funil por regional e destravar os 3 maiores parceiros da carteira dele.")
    if a['n_below'] > 0:
        acoes.append(f"<b>Campanha de ticket:</b> dos {a['n_below']} abaixo do target, priorizar os que estão entre R$ 15-25 mil — são os mais próximos de virar; uma operação a mais por parceiro muda o patamar.")
    for b in a['bancos_q'][:1]:
        acoes.append(f"<b>Diagnóstico {b['nome']}:</b> queda de {abs(b['pct']):.0f}% — verificar trava operacional, mudança de tabela/comissão ou migração para concorrente.")
    if a['conc'] > 35:
        acoes.append("<b>Diluir risco:</b> programa de ativação para a base média — meta de +1 operação/mês em 50 parceiros medianos reduz a dependência do top 10.")
    acoes.append("<b>Reativados:</b> garantir segunda operação dos novos/reativados em até 15 dias — parceiro com 2ª operação no 1º mês retém 3x mais.")

    li = lambda items, cor: '\n'.join(f'<li style="margin-bottom:10px;line-height:1.55"><span style="color:{cor};margin-right:6px">●</span>{x}</li>' for x in items)
    ac = '\n'.join(f'<li style="margin-bottom:12px;line-height:1.6">{x}</li>' for x in acoes)

    pct_txt = f"{a['pct']:.0f}%" if a['pct'] is not None else '—'
    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Visão Executiva — PROTÓTIPO</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0b0b17;color:#e8e8f8;font-family:'Segoe UI',system-ui,sans-serif;font-size:14px;padding:28px;max-width:1100px;margin:0 auto}}
.tag{{display:inline-block;background:#eab30822;color:#eab308;border:1px solid #eab30855;border-radius:6px;padding:3px 10px;font-size:11px;font-weight:700;letter-spacing:1px;margin-bottom:14px}}
h1{{font-size:22px;margin-bottom:2px}} .sub{{color:#9090c0;font-size:12px;margin-bottom:26px}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:28px}}
.card{{background:#12121e;border:1px solid #252540;border-radius:12px;padding:16px 18px}}
.card .lbl{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:#6868a0;margin-bottom:6px}}
.card .big{{font-size:24px;font-weight:800}} .card .small{{font-size:11px;color:#9090c0;margin-top:3px}}
.sec{{font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:1.2px;margin:26px 0 14px;display:flex;align-items:center;gap:10px}}
.sec::after{{content:'';flex:1;height:1px;background:#252540}}
.panel{{background:#12121e;border:1px solid #252540;border-radius:12px;padding:18px 22px}}
.duo{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
ul,ol{{padding-left:18px}} b{{color:#fff}}
.ia{{background:linear-gradient(135deg,#12121e,#16162a);border:1px solid #60a5fa44}}
.ia-hdr{{display:flex;align-items:center;gap:8px;font-weight:700;color:#60a5fa;font-size:13px;margin-bottom:14px}}
@media(max-width:800px){{.cards{{grid-template-columns:repeat(2,1fr)}}.duo{{grid-template-columns:1fr}}}}
</style></head><body>
<div class="tag">PROTÓTIPO — NÃO PUBLICADO</div>
<h1>Visão Executiva — Gestão Comercial</h1>
<div class="sub">{a['info'].get('mes_ref','')} · gerado em {a['info'].get('gerado_em','')} · dia útil {a['du_p']} de {a['du_t']}</div>

<div class="cards">
  <div class="card" style="border-top:3px solid #60a5fa"><div class="lbl">Meta Global</div><div class="big">{m(a['meta'])}</div><div class="small">{brl(a['meta'])}</div></div>
  <div class="card"><div class="lbl">Projeção do Mês</div><div class="big" style="color:{'#22c55e' if (a['pct'] or 0)>=100 else '#eab308'}">{m(a['proj'])}</div><div class="small">{pct_txt} da meta</div></div>
  <div class="card"><div class="lbl">Ritmo Atual / Dia</div><div class="big">{m(a['ritmo_atual'])}</div><div class="small">produção ÷ {a['du_p']} dias úteis</div></div>
  <div class="card" style="border-top:3px solid {'#22c55e' if a['ritmo_atual']>=a['ritmo_nec'] else '#ef4444'}"><div class="lbl">Ritmo Necessário / Dia</div><div class="big">{m(a['ritmo_nec'])}</div><div class="small">para fechar a meta em {a['du_rest']} dias úteis</div></div>
</div>

<div class="duo">
  <div>
    <div class="sec" style="color:#22c55e">✦ Pontos Positivos</div>
    <div class="panel"><ul style="list-style:none;padding:0">{li(pos,'#22c55e')}</ul></div>
  </div>
  <div>
    <div class="sec" style="color:#ef4444">⚠ Pontos de Atenção</div>
    <div class="panel"><ul style="list-style:none;padding:0">{li(neg,'#ef4444')}</ul></div>
  </div>
</div>

<div class="sec" style="color:#60a5fa">🤖 Plano de Ação Sugerido</div>
<div class="panel ia">
  <div class="ia-hdr">Análise inteligente da carteira — recomendações priorizadas</div>
  <ol>{ac}</ol>
</div>

<div style="margin-top:22px;font-size:11px;color:#6868a0">
Protótipo gerado localmente a partir dos dados reais do mês. Numa versão futura, esta análise pode ser
redigida pela IA (API do Claude) a cada atualização, com leitura contextual da carteira de cada gestor.
</div>
</body></html>"""


def main():
    print("Processando dados...")
    result = gerar_metas.processar()
    data = result[0]
    a = analisar(data)
    html = montar_html(a)
    out = BASE_DIR / 'teste_resumo.html'
    out.write_text(html, encoding='utf-8')
    print(f"[OK] Protótipo salvo em: {out}")


if __name__ == '__main__':
    main()
