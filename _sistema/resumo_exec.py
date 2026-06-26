# -*- coding: utf-8 -*-
"""
Resumo Executivo — análise inteligente da carteira por escopo.
Gera os insights da aba "📋 Resumo": admin, super, regional e comercial.
Chamado pelo gerar_metas.py via anexar(data).
"""

TARGET = 25000


def _m(v):
    if v is None:
        return '—'
    a, s = abs(v), ('-' if v < 0 else '')
    if a >= 1e9: return f'{s}{a/1e9:.2f}B'
    if a >= 1e6: return f'{s}{a/1e6:.1f}M'
    if a >= 1e3: return f'{s}{a/1e3:.0f}k'
    return f'{s}{a:.0f}'


def _nome_curto(s):
    return str(s).split(' - ', 1)[-1].title()


def _walk_parceiros(nodes_sup):
    """Itera (parceiro, comercial, regional, super) de uma lista de supers da carteira."""
    for s in nodes_sup or []:
        for r in s.get('regionais', []):
            for c in r.get('comerciais', []):
                for p in c.get('parceiros', []):
                    yield p, c, r, s


def _metricas_parceiros(nodes_sup):
    below, quase, producing, novos = [], [], 0, 0
    tops = []
    for p, c, r, s in _walk_parceiros(nodes_sup):
        pj = p.get('proj') or 0
        if p.get('churn') or pj <= 0:
            continue
        producing += 1
        tops.append((p['nome'], pj))
        if (p.get('ant') or 0) == 0 and (p.get('atu') or 0) > 0:
            novos += 1
        if pj < TARGET:
            below.append(p)
            if pj >= TARGET * 0.6:
                quase.append((p['nome'], pj))
    tops.sort(key=lambda x: -x[1])
    quase.sort(key=lambda x: -x[1])
    return below, quase, producing, novos, tops


def _ritmo(meta, prod, du_p, du_rest):
    atual = prod / du_p if du_p else 0
    nec = (meta - prod) / du_rest if (du_rest and meta) else 0
    return atual, nec


def _cards_meta(meta, proj, pct, atual, nec, du_p, du_rest):
    ok = atual >= nec
    return [
        {'lbl': 'Meta do Mês', 'big': _m(meta), 'small': '', 'cor': 'var(--blue)'},
        {'lbl': 'Projeção', 'big': _m(proj),
         'small': (f'{pct:.0f}% da meta' if pct is not None else ''),
         'corv': 'var(--green)' if (pct or 0) >= 100 else 'var(--yellow)'},
        {'lbl': 'Ritmo Atual / Dia', 'big': _m(atual), 'small': f'produção ÷ {du_p} dias úteis'},
        {'lbl': 'Ritmo Necessário / Dia', 'big': _m(nec),
         'small': f'para fechar em {du_rest} dias úteis',
         'cor': 'var(--green)' if ok else 'var(--red)'},
    ]


def _acoes_comuns(acoes, churn_list, quase, n_quase_total):
    if churn_list:
        top = churn_list[:3]
        nomes = ', '.join(_nome_curto(c['parceiro']) for c in top)
        val = sum((c.get('prod_ant') or 0) for c in churn_list[:5])
        acoes.append(f"<b>Resgate de churn (esta semana):</b> os 5 maiores que zeraram valiam {_m(val)}/mês. Começar por: {nomes}.")
    if quase:
        nomes = ', '.join(_nome_curto(n) for n, _ in quase[:3])
        acoes.append(f"<b>Campanha de ticket:</b> {n_quase_total} parceiros entre R$ 15-25 mil — os mais próximos de virar o target. Prioridade: {nomes}.")


def _bullets_metas(node, pos, neg, acoes, du_p, du_rest):
    """Adiciona pontos e ações de meta global + meta banco de um nó (reg/com/sup)."""
    meta  = node.get('meta_global') or 0
    prod  = node.get('prod_total') or 0
    pctg  = node.get('pct_global')
    gapg  = node.get('gap_global')
    if meta > 0 and pctg is not None:
        if pctg >= 100:
            pos.append(f"<b>Meta global no ritmo</b> — {pctg:.0f}% de atingimento projetado.")
        else:
            neg.append(f"<b>GAP de {_m(gapg)} na meta global</b> — projeção em {pctg:.0f}%.")
            atual, nec = _ritmo(meta, prod, du_p, du_rest)
            if nec > atual > 0:
                acoes.append(f"<b>Cadência da meta global:</b> alvo de {_m(nec)}/dia nos {du_rest} dias úteis restantes (ritmo atual: {_m(atual)}/dia).")

    metab = node.get('meta_banco_total') or 0
    pctb  = node.get('pct_banco')
    if metab > 0 and pctb is not None:
        if pctb >= 100:
            pos.append(f"<b>Metas banco no ritmo</b> — {pctb:.0f}% de atingimento ({_m(node.get('proj_banco_total'))} de {_m(metab)}).")
        else:
            neg.append(f"<b>Metas banco em {pctb:.0f}%</b> — projeção {_m(node.get('proj_banco_total'))} de {_m(metab)}.")
            bcs = [b for b in node.get('bancos', []) if (b.get('meta') or 0) > 0 and (b.get('gap') or 0) < 0]
            if bcs:
                pior = min(bcs, key=lambda b: b['gap'])
                acoes.append(f"<b>Metas banco:</b> maior GAP em <b>{pior['nome']}</b> ({_m(pior['gap'])}) — veja o detalhe na aba Meta Banco.")


def _delta(item):
    """Impacto em R$ = proj - ant (negativo = queda, positivo = alta)."""
    return (item.get('proj') or 0) - (item.get('ant') or 0)


def _top_queda(lista, min_ant=0, n=3):
    """Top N itens com maior PERDA em R$ (ant - proj), filtrado por volume mínimo."""
    candidatos = [x for x in lista if (x.get('ant') or 0) > min_ant and _delta(x) < 0]
    return sorted(candidatos, key=lambda x: _delta(x))[:n]  # mais negativo primeiro


def _top_alta(lista, min_ant=0, n=2):
    """Top N itens com maior GANHO em R$ (proj - ant), filtrado por volume mínimo."""
    candidatos = [x for x in lista if (x.get('ant') or 0) > min_ant and _delta(x) > 0]
    return sorted(candidatos, key=lambda x: -_delta(x))[:n]


def _bancos_queda_str(bancos_q):
    partes = [f"<b>{b['nome']}</b> {_m(_delta(b))} ({_m(b.get('ant') or 0)} → {_m(b.get('proj') or 0)})" for b in bancos_q]
    return '; '.join(partes)


def analise_admin(data):
    emp, info, cart = data['empresa'], data['info'], data.get('carteira', {})
    R = cart.get('resumo', {})
    du_t, du_p = info['dias_uteis_total'], info['dias_uteis_passados']
    du_rest = max(du_t - du_p, 0)
    meta, prod = emp.get('meta_global_total') or 0, emp.get('prod_total') or 0
    proj, pct = emp.get('proj_total') or 0, emp.get('pct_total')
    gap = emp.get('gap_total') or (meta - proj)
    atual, nec = _ritmo(meta, prod, du_p, du_rest)

    churn = cart.get('churn', [])
    churn_val = sum((c.get('prod_ant') or 0) for c in churn)
    below, quase, producing, novos, tops = _metricas_parceiros(cart.get('supers'))
    conc = (sum(v for _, v in tops[:10]) / proj * 100) if proj else 0
    top3_val = sum(v for _, v in tops[:3])
    top3_pct = (top3_val / proj * 100) if proj else 0

    # ordena por impacto em R$, não por %
    bancos_q = _top_queda(cart.get('por_banco', []), min_ant=100000, n=3)
    bancos_a = _top_alta(cart.get('por_banco', []),  min_ant=100000, n=2)
    queda_val_bancos = sum(-_delta(b) for b in bancos_q)
    alta_val_bancos  = sum(_delta(b)  for b in bancos_a)

    sups = [s for s in data.get('supers', []) if s.get('meta_global')]
    # supers em risco: ordena pelo GAP em R$ (maior gap primeiro), não por %
    sups_ok    = sorted([s for s in sups if (s.get('pct_global') or 0) >= 100], key=lambda s: -(s.get('proj_total') or 0))
    sups_risco = sorted([s for s in sups if (s.get('pct_global') or 0) < 85],   key=lambda s:  (s.get('gap_global') or 0))

    meta_diaria_ideal = (meta / du_t) if du_t else 0
    vel_pct = (atual / meta_diaria_ideal * 100 - 100) if meta_diaria_ideal and atual else None

    pos, neg, acoes = [], [], []
    if pct is not None and pct >= 100:
        pos.append(f"<b>Meta global no ritmo</b> — projeção em {pct:.0f}% ({_m(proj)} de {_m(meta)}).")
    for s in sups_ok[:3]:
        pos.append(f"<b>{s['nome'].title()}</b> projeta {_m(s.get('proj_total') or 0)} ({s['pct_global']:.0f}% da meta) — destaque do mês.")
    if novos:
        pos.append(f"<b>{novos} parceiros reativados/novos</b> produzindo este mês.")
    for b in bancos_a:
        pos.append(f"<b>{b['nome']}</b> em alta: +{_m(_delta(b))} vs mês anterior ({_m(b.get('ant') or 0)} → {_m(b.get('proj') or 0)}).")
    if (R.get('pct_proj_ant') or 0) > 0:
        pos.append(f"<b>Carteira crescendo</b> — projeção {_m(proj)} ({R['pct_proj_ant']:+.1f}% sobre o mês anterior).")
    if vel_pct is not None and vel_pct > 10:
        pos.append(f"<b>Velocidade acima do ideal</b> — ritmo atual {vel_pct:+.0f}% acima do alvo diário ({_m(meta_diaria_ideal)}/dia).")
    if not pos:
        pos.append("Sem destaques positivos relevantes neste corte.")

    if pct is not None and pct < 100:
        neg.append(f"<b>GAP de {_m(gap)}</b> para a meta global — projeção em {pct:.0f}%.")
    if nec > atual > 0:
        neg.append(f"<b>Ritmo insuficiente</b> — é preciso {_m(nec)}/dia ({nec/atual-1:+.0%} sobre o atual de {_m(atual)}/dia).")
    if churn:
        neg.append(f"<b>{len(churn)} parceiros em churn</b> — representavam {_m(churn_val)}/mês em produção.")
    if below and producing:
        neg.append(f"<b>{len(below)} parceiros abaixo do target</b> de R$ 25 mil — potencial represado de produção.")
    for s in sups_risco[:3]:
        neg.append(f"<b>{s['nome'].title()}</b> em risco: GAP de {_m(abs(s.get('gap_global') or 0))} ({(s.get('pct_global') or 0):.0f}% da meta).")
    if bancos_q:
        neg.append(f"<b>Bancos em queda</b> (impacto total {_m(queda_val_bancos)}): {_bancos_queda_str(bancos_q)}.")
    if conc > 35:
        neg.append(f"<b>Concentração de carteira</b> — top 3 parceiros valem {_m(top3_val)} ({top3_pct:.0f}% da projeção). Risco real se um deles esfriar.")

    _acoes_comuns(acoes, churn, quase, len(quase))
    if sups_risco:
        s0 = sups_risco[0]
        acoes.append(f"<b>War room com {s0['nome'].title()}:</b> GAP de {_m(abs(s0.get('gap_global') or 0))} — revisar funil por regional e destravar os maiores parceiros.")
    if nec > atual:
        acoes.append(f"<b>Cadência diária:</b> alvo de {_m(nec)}/dia — cobrar plano dos supers abaixo de 85% e acompanhar D-1.")
    if bancos_q:
        b0 = bancos_q[0]
        acoes.append(f"<b>Diagnóstico {b0['nome']}:</b> maior perda em R$ ({_m(-_delta(b0))}) — checar trava operacional, tabela/comissão ou migração para concorrente.")
    if novos:
        acoes.append("<b>Reativados:</b> garantir a 2ª operação dos novos em até 15 dias — retenção 3x maior.")
    if conc > 35 and tops:
        acoes.append(f"<b>Hedge de carteira:</b> {_nome_curto(tops[0][0])} representa {_m(tops[0][1])} sozinho — ativar 2-3 parceiros médios como reserva estratégica.")

    return {'titulo': 'Resumo Executivo — Empresa',
            'sub': f"dia útil {du_p} de {du_t} · {info.get('gerado_em','')}",
            'cards': _cards_meta(meta, proj, pct, atual, nec, du_p, du_rest),
            'pos': pos, 'neg': neg, 'acoes': acoes}


def analise_super(data, sup):
    info = data['info']
    cart = sup.get('_carteira', {})
    R = cart.get('resumo', {})
    du_t, du_p = info['dias_uteis_total'], info['dias_uteis_passados']
    du_rest = max(du_t - du_p, 0)
    meta, prod = sup.get('meta_global') or 0, sup.get('prod_total') or 0
    proj, pct, gap = sup.get('proj_total') or 0, sup.get('pct_global'), sup.get('gap_global')
    atual, nec = _ritmo(meta, prod, du_p, du_rest)

    churn = cart.get('churn', [])
    churn_val = sum((c.get('prod_ant') or 0) for c in churn)
    below, quase, producing, novos, tops = _metricas_parceiros(cart.get('supers'))

    regs = []
    for s in cart.get('supers', []):
        regs.extend(s.get('regionais', []))
    regs_rel = [r for r in regs if (r.get('ant') or 0) > 100000]

    bancos_q = _top_queda(cart.get('por_banco', []), min_ant=50000, n=2)
    bancos_a = _top_alta(cart.get('por_banco', []),  min_ant=50000, n=1)
    queda_val_bancos = sum(-_delta(b) for b in bancos_q)

    # regionais: ordena por impacto em R$ (proj - ant), não por %
    regs_q = sorted([r for r in regs_rel if _delta(r) < 0], key=lambda r: _delta(r))[:2]
    regs_a = sorted([r for r in regs_rel if _delta(r) > 0], key=lambda r: -_delta(r))[:2]

    conc = (sum(v for _, v in tops[:5]) / proj * 100) if proj else 0

    pos, neg, acoes = [], [], []
    if pct is not None and pct >= 100:
        pos.append(f"<b>Meta no ritmo</b> — projeção em {pct:.0f}% da meta ({_m(proj)} de {_m(meta)}).")
    for r in regs_a:
        pos.append(f"<b>Regional {r['nome'].title()}</b> ganhou +{_m(_delta(r))} vs mês anterior ({_m(r.get('ant') or 0)} → {_m(r.get('proj') or 0)}).")
    if novos:
        pos.append(f"<b>{novos} parceiros reativados/novos</b> na sua carteira.")
    if (R.get('pct_proj_ant') or 0) > 0:
        pos.append(f"<b>Carteira crescendo</b> — projeção {_m(proj)} ({R['pct_proj_ant']:+.1f}% sobre o mês anterior).")
    for b in bancos_a:
        pos.append(f"<b>{b['nome']}</b> em alta: +{_m(_delta(b))} vs mês anterior ({_m(b.get('ant') or 0)} → {_m(b.get('proj') or 0)}).")
    if not pos:
        pos.append("Sem destaques positivos neste corte — foco no plano de ação.")

    metab, pctb = sup.get('meta_banco_total') or 0, sup.get('pct_banco')
    if metab > 0 and pctb is not None:
        if pctb >= 100:
            pos.append(f"<b>Metas banco no ritmo</b> — {_m(sup.get('proj_banco_total'))} de {_m(metab)} ({pctb:.0f}%).")
        else:
            neg.append(f"<b>Metas banco com GAP</b> — {_m(sup.get('proj_banco_total'))} de {_m(metab)} ({pctb:.0f}%). Detalhe na aba Meta Banco.")

    if pct is not None and pct < 100:
        neg.append(f"<b>GAP de {_m(gap)}</b> — projeção em {pct:.0f}% da meta.")
    if nec > atual > 0:
        neg.append(f"<b>Ritmo:</b> precisa de {_m(nec)}/dia nos {du_rest} dias úteis restantes ({nec/atual-1:+.0%} sobre o atual).")
    if churn:
        neg.append(f"<b>{len(churn)} parceiros zeraram</b> — representavam {_m(churn_val)}/mês em produção.")
    if below and producing:
        neg.append(f"<b>{len(below)} parceiros abaixo do target</b> — potencial de produção represado na carteira.")
    for r in regs_q:
        neg.append(f"<b>Regional {r['nome'].title()}</b> perdeu {_m(-_delta(r))} vs mês anterior ({_m(r.get('ant') or 0)} → {_m(r.get('proj') or 0)}).")
    if bancos_q:
        neg.append(f"<b>Bancos em queda</b> (impacto {_m(queda_val_bancos)}): {_bancos_queda_str(bancos_q)}.")
    if conc > 40:
        neg.append(f"<b>Top 5 parceiros = {conc:.0f}% da projeção</b> ({_m(sum(v for _,v in tops[:5]))}) — risco de dependência elevada.")

    _acoes_comuns(acoes, churn, quase, len(quase))
    if regs_q:
        r0 = regs_q[0]
        acoes.append(f"<b>Reunião com {r0['nome'].title()}:</b> maior perda da carteira ({_m(-_delta(r0))}) — revisar funil comercial a comercial.")
    if nec > atual:
        acoes.append(f"<b>Cadência:</b> alvo diário de {_m(nec)} — distribuir por regional e acompanhar D-1.")
    if bancos_q:
        b0 = bancos_q[0]
        acoes.append(f"<b>Diagnóstico {b0['nome']}:</b> perda de {_m(-_delta(b0))} — verificar problema operacional, comissão ou migração para concorrente.")
    if novos:
        acoes.append("<b>Reativados:</b> garantir a 2ª operação em até 15 dias.")

    return {'titulo': f"Resumo — {sup['nome'].title()}",
            'sub': f"dia útil {du_p} de {du_t} · {info.get('gerado_em','')}",
            'cards': _cards_meta(meta, proj, pct, atual, nec, du_p, du_rest),
            'pos': pos, 'neg': neg, 'acoes': acoes}


def _cards_carteira(node, n_prod):
    ant, atu, proj, pct = node.get('ant'), node.get('atu'), node.get('proj'), node.get('pct')
    meta, pctg = node.get('_meta_global') or 0, node.get('_pct_global')
    cards = []
    if meta > 0:
        cards.append({'lbl': 'Meta Global', 'big': _m(meta), 'small': '', 'cor': 'var(--blue)'})
        cards.append({'lbl': 'Projeção', 'big': _m(proj),
                      'small': (f'{pctg:.0f}% da meta' if pctg is not None else ''),
                      'corv': 'var(--green)' if (pctg or 0) >= 100 else 'var(--yellow)'})
    else:
        cards.append({'lbl': 'Mês Anterior', 'big': _m(ant), 'small': '', 'cor': 'var(--blue)'})
        cards.append({'lbl': 'Projeção', 'big': _m(proj),
                      'small': (f'{pct:+.1f}% vs mês anterior' if pct is not None else ''),
                      'corv': 'var(--green)' if (pct or 0) >= 0 else 'var(--red)'})
    cards.append({'lbl': 'Atual Parcial', 'big': _m(atu),
                  'small': (f'mês anterior: {_m(ant)}' if meta > 0 else '')})
    cards.append({'lbl': 'Vs Mês Anterior', 'big': (f'{pct:+.1f}%' if pct is not None else '—'),
                  'small': '', 'corv': 'var(--green)' if (pct or 0) >= 0 else 'var(--red)',
                  'cor': 'var(--green)' if (pct or 0) >= 0 else 'var(--red)'})
    cards.append({'lbl': 'Parceiros Produzindo', 'big': str(n_prod), 'small': ''})
    return cards


def analise_regional(reg, sup_nome, churn_sup, info, meta_node=None):
    du_t, du_p = info['dias_uteis_total'], info['dias_uteis_passados']
    du_rest = max(du_t - du_p, 0)
    churn = [c for c in churn_sup if c.get('regional') == reg['nome']]
    churn_val = sum((c.get('prod_ant') or 0) for c in churn)
    fake = [{'regionais': [reg]}]
    below, quase, producing, novos, tops = _metricas_parceiros(fake)

    # ordena por impacto em R$
    coms_rel = [c for c in reg.get('comerciais', []) if (c.get('ant') or 0) > 30000]
    coms_q = sorted([c for c in coms_rel if _delta(c) < 0], key=lambda c: _delta(c))[:2]
    coms_a = sorted([c for c in coms_rel if _delta(c) > 0], key=lambda c: -_delta(c))[:2]
    reg_delta = _delta(reg)

    pos, neg, acoes = [], [], []
    if reg_delta > 0:
        pos.append(f"<b>Carteira crescendo</b> — ganho de {_m(reg_delta)} vs mês anterior ({_m(reg.get('ant') or 0)} → {_m(reg.get('proj') or 0)}).")
    for c in coms_a:
        pos.append(f"<b>{c['nome'].title()}</b> ganhou +{_m(_delta(c))} vs mês anterior ({_m(c.get('ant') or 0)} → {_m(c.get('proj') or 0)}).")
    if novos:
        pos.append(f"<b>{novos} parceiros reativados/novos</b> este mês.")
    if not pos:
        pos.append("Sem destaques positivos neste corte.")

    if reg_delta < 0:
        neg.append(f"<b>Projeção em queda</b> — perda de {_m(-reg_delta)} vs mês anterior ({_m(reg.get('ant') or 0)} → {_m(reg.get('proj') or 0)}).")
    if churn:
        neg.append(f"<b>{len(churn)} parceiros zeraram</b> — representavam {_m(churn_val)}/mês.")
    if below and producing:
        neg.append(f"<b>{len(below)} parceiros abaixo do target</b> — potencial de produção represado.")
    for c in coms_q:
        neg.append(f"<b>{c['nome'].title()}</b> perdeu {_m(-_delta(c))} vs mês anterior ({_m(c.get('ant') or 0)} → {_m(c.get('proj') or 0)}).")

    if meta_node:
        _bullets_metas(meta_node, pos, neg, acoes, du_p, du_rest)
        reg = dict(reg, _meta_global=meta_node.get('meta_global'), _pct_global=meta_node.get('pct_global'))
    _acoes_comuns(acoes, churn, quase, len(quase))
    if coms_q:
        c0 = coms_q[0]
        acoes.append(f"<b>1:1 com {c0['nome'].title()}:</b> maior perda da regional ({_m(-_delta(c0))}) — mapear os parceiros que esfriaram.")
    if novos:
        acoes.append("<b>Reativados:</b> 2ª operação em até 15 dias garante retenção.")

    return {'titulo': f"Resumo — Regional {reg['nome'].title()}",
            'sub': f"{sup_nome.title()} · dia útil {du_p} de {du_t}",
            'cards': _cards_carteira(reg, producing),
            'pos': pos, 'neg': neg, 'acoes': acoes}


def analise_comercial(com, reg_nome, sup_nome, churn_sup, info, meta_node=None):
    du_t, du_p = info['dias_uteis_total'], info['dias_uteis_passados']
    du_rest = max(du_t - du_p, 0)
    churn = [c for c in churn_sup if c.get('comercial') == com['nome']]
    churn_val = sum((c.get('prod_ant') or 0) for c in churn)
    fake = [{'regionais': [{'comerciais': [com]}]}]
    below, quase, producing, novos, tops = _metricas_parceiros(fake)
    proj = com.get('proj') or 0
    conc1 = (tops[0][1] / proj * 100) if (tops and proj) else 0

    com_delta = _delta(com)
    pos, neg, acoes = [], [], []
    if com_delta > 0:
        pos.append(f"<b>Sua carteira cresceu</b> +{_m(com_delta)} vs mês anterior ({_m(com.get('ant') or 0)} → {_m(proj)}).")
    if novos:
        pos.append(f"<b>{novos} parceiros reativados/novos</b> — boa ativação!")
    if tops:
        pos.append(f"<b>Maior parceiro:</b> {_nome_curto(tops[0][0])} projetando {_m(tops[0][1])}.")
    if not pos:
        pos.append("Sem destaques positivos neste corte.")

    if com_delta < 0:
        neg.append(f"<b>Projeção em queda</b> — perda de {_m(-com_delta)} vs mês anterior ({_m(com.get('ant') or 0)} → {_m(proj)}).")
    if churn:
        nomes = ', '.join(_nome_curto(c['parceiro']) for c in churn[:5])
        neg.append(f"<b>{len(churn)} parceiros seus zeraram</b> — representavam {_m(churn_val)}: {nomes}.")
    if below:
        neg.append(f"<b>{len(below)} parceiros abaixo de R$ 25 mil</b> — potencial de ticket parado.")
    if conc1 > 40:
        neg.append(f"<b>Dependência:</b> {_nome_curto(tops[0][0])} vale {_m(tops[0][1])} ({conc1:.0f}% da produção) — risco se esfriar.")

    if meta_node:
        _bullets_metas(meta_node, pos, neg, acoes, du_p, du_rest)
        com = dict(com, _meta_global=meta_node.get('meta_global'), _pct_global=meta_node.get('pct_global'))
    if churn:
        nomes = ', '.join(_nome_curto(c['parceiro']) for c in churn[:3])
        acoes.append(f"<b>Ligar hoje:</b> {nomes} — produziam mês passado e zeraram. Entender o motivo e reverter.")
    if quase:
        nomes = ', '.join(_nome_curto(n) for n, _ in quase[:3])
        acoes.append(f"<b>Uma operação a mais:</b> {nomes} estão perto do target de R$ 25 mil — pequeno empurrão muda o patamar.")
    if novos:
        acoes.append("<b>Novos parceiros:</b> agende a 2ª operação em até 15 dias — é o que segura a recorrência.")
    if conc1 > 40:
        acoes.append("<b>Diversificar:</b> ative 2-3 parceiros médios para reduzir dependência do maior.")
    if not acoes:
        acoes.append("<b>Manter o ritmo:</b> carteira saudável — foco em ticket médio e recorrência.")

    return {'titulo': f"Resumo — {com['nome'].title()}",
            'sub': f"{reg_nome.title()} · {sup_nome.title()} · dia útil {du_p} de {du_t}",
            'cards': _cards_carteira(com, producing),
            'pos': pos, 'neg': neg, 'acoes': acoes}


def analise_convenios(cart, info, nome_gestor):
    """Resumo executivo de uma carteira filtrada por convênios."""
    R = cart.get('resumo', {})
    du_t, du_p = info['dias_uteis_total'], info['dias_uteis_passados']
    ant, atu, proj = R.get('prod_anterior') or 0, R.get('prod_atual') or 0, R.get('proj_atual') or 0
    pct = R.get('pct_proj_ant')
    producing = R.get('n_ativos') or R.get('n_parceiros_atu') or 0
    novos, n_churn = R.get('n_novos') or 0, R.get('n_churn') or 0

    churn = cart.get('churn', [])
    churn_val = sum((c.get('prod_ant') or 0) for c in churn)
    below, quase, _producing2, _novos2, tops = _metricas_parceiros(cart.get('supers'))

    # ordena por impacto em R$, não em %
    bancos_q = _top_queda(cart.get('por_banco', []),    min_ant=10000, n=4)
    bancos_a = _top_alta(cart.get('por_banco', []),     min_ant=10000, n=2)
    queda_val_bancos = sum(-_delta(b) for b in bancos_q)

    convs_q = _top_queda(cart.get('por_convenio', []), min_ant=5000, n=4)
    convs_a = _top_alta(cart.get('por_convenio', []),  min_ant=5000, n=3)
    queda_val_convs = sum(-_delta(c) for c in convs_q)

    # diversificação: quanto os top 3 convênios representam
    top3_conv_val = sum(c.get('proj') or 0 for c in sorted(convs, key=lambda c: -(c.get('proj') or 0))[:3])
    top3_conv_pct = (top3_conv_val / proj * 100) if proj else 0

    pos, neg, acoes = [], [], []
    cart_delta = proj - ant
    if cart_delta > 0:
        pos.append(f"<b>Carteira de convênios crescendo</b> +{_m(cart_delta)} vs mês anterior ({_m(ant)} → {_m(proj)}).")
    if novos:
        pos.append(f"<b>{novos} parceiros reativados/novos</b> produzindo este mês.")
    for b in bancos_a:
        pos.append(f"<b>{b['nome']}</b> em alta: +{_m(_delta(b))} vs mês anterior ({_m(b.get('ant') or 0)} → {_m(b.get('proj') or 0)}).")
    for c in convs_a[:2]:
        pos.append(f"<b>Convênio {c['nome']}</b>: +{_m(_delta(c))} vs mês anterior ({_m(c.get('ant') or 0)} → {_m(c.get('proj') or 0)}).")
    if not pos:
        pos.append("Sem destaques positivos relevantes neste corte.")

    if cart_delta < 0:
        neg.append(f"<b>Projeção em queda</b> — perda de {_m(-cart_delta)} vs mês anterior ({_m(ant)} → {_m(proj)}).")
    if bancos_q:
        partes = [f"<b>{b['nome']}</b> {_m(_delta(b))} ({_m(b.get('ant') or 0)} → {_m(b.get('proj') or 0)})" for b in bancos_q]
        neg.append(f"<b>Bancos em queda</b> (impacto total {_m(queda_val_bancos)}): {'; '.join(partes)}.")
    if convs_q:
        partes = [f"<b>{c['nome']}</b> {_m(_delta(c))} ({_m(c.get('ant') or 0)} → {_m(c.get('proj') or 0)})" for c in convs_q]
        neg.append(f"<b>Convênios em queda</b> (impacto total {_m(queda_val_convs)}): {'; '.join(partes)}.")
    if churn:
        neg.append(f"<b>{len(churn)} parceiros em churn</b> — representavam {_m(churn_val)} no mês anterior.")
    if below and producing:
        neg.append(f"<b>{len(below)} parceiros abaixo do target</b> de R$ 25 mil — potencial de produção represado.")
    if top3_conv_pct > 50:
        neg.append(f"<b>Concentração em convênios</b> — top 3 representam {_m(top3_conv_val)} ({top3_conv_pct:.0f}% da projeção). Ampliar base reduz o risco.")

    _acoes_comuns(acoes, churn, quase, len(quase))
    if bancos_q:
        b0 = bancos_q[0]
        acoes.append(f"<b>Diagnóstico {b0['nome']}:</b> maior perda em banco ({_m(-_delta(b0))}: {_m(b0.get('ant') or 0)} → {_m(b0.get('proj') or 0)}) — verificar trava operacional, tabela ou migração de parceiros.")
    if convs_q:
        c0 = convs_q[0]
        acoes.append(f"<b>Convênio prioritário {c0['nome']}:</b> maior perda em R$ ({_m(-_delta(c0))}: {_m(c0.get('ant') or 0)} → {_m(c0.get('proj') or 0)}) — acionar parceiros que operam esse convênio e identificar gargalo.")
    if novos:
        acoes.append("<b>Reativados:</b> garantir a 2ª operação dos novos em até 15 dias — retenção 3x maior.")
    if not acoes:
        acoes.append("<b>Manter o ritmo:</b> carteira saudável — foco em ticket médio e recorrência.")

    return {'titulo': f"Resumo — Gestão de Convênios ({nome_gestor})",
            'sub': f"dia útil {du_p} de {du_t} · {info.get('gerado_em','')}",
            'cards': [
                {'lbl': 'Mês Anterior', 'big': _m(ant), 'small': '', 'cor': 'var(--blue)'},
                {'lbl': 'Projeção', 'big': _m(proj),
                 'small': (f'{pct:+.1f}% vs mês anterior' if pct is not None else ''),
                 'corv': 'var(--green)' if (pct or 0) >= 0 else 'var(--red)'},
                {'lbl': 'Atual Parcial', 'big': _m(atu), 'small': f'mês anterior: {_m(ant)}'},
                {'lbl': 'Parceiros Produzindo', 'big': str(producing), 'small': ''},
            ],
            'pos': pos, 'neg': neg, 'acoes': acoes}


def anexar(data):
    """Calcula e anexa resumo_exec ao data (admin) e _resumo a cada super."""
    info = data['info']
    data['resumo_exec'] = {'principal': analise_admin(data)}

    for sup in data.get('supers', []):
        cart = sup.get('_carteira', {})
        churn_sup = cart.get('churn', [])
        # lookup de metas por nome (hierarquia de metas do próprio super)
        metas_reg, metas_com = {}, {}
        for mr in sup.get('regionais', []):
            metas_reg[mr['nome'].upper()] = mr
            for mc in mr.get('comerciais', []):
                metas_com[mc['nome'].upper()] = mc
        regionais, comerciais = {}, {}
        for s in cart.get('supers', []):
            for r in s.get('regionais', []):
                regionais[r['nome']] = analise_regional(
                    r, sup['nome'], churn_sup, info, metas_reg.get(r['nome'].upper()))
                for c in r.get('comerciais', []):
                    comerciais[c['nome']] = analise_comercial(
                        c, r['nome'], sup['nome'], churn_sup, info, metas_com.get(c['nome'].upper()))
        sup['_resumo'] = {
            'principal': analise_super(data, sup),
            'regionais': regionais,
            'comerciais': comerciais,
        }

    for escopo, g in data.get('_gestores_convenios', {}).items():
        g['resumo_exec'] = {'principal': analise_convenios(g['carteira'], info, g['nome'])}
