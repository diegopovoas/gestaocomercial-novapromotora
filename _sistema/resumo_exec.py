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

    bancos = [b for b in cart.get('por_banco', []) if (b.get('ant') or 0) > 300000]
    bancos_q = sorted([b for b in bancos if (b.get('pct') or 0) < -15], key=lambda b: b['pct'])[:2]
    bancos_a = sorted([b for b in bancos if (b.get('pct') or 0) > 15], key=lambda b: -b['pct'])[:2]

    sups = [s for s in data.get('supers', []) if s.get('meta_global')]
    sups_ok = sorted([s for s in sups if (s.get('pct_global') or 0) >= 100], key=lambda s: -(s['pct_global'] or 0))
    sups_risco = sorted([s for s in sups if (s.get('pct_global') or 0) < 85], key=lambda s: (s['pct_global'] or 0))

    pos, neg, acoes = [], [], []
    if pct is not None and pct >= 100:
        pos.append(f"<b>Meta global no ritmo</b> — projeção em {pct:.0f}% da meta.")
    for s in sups_ok[:3]:
        pos.append(f"<b>{s['nome'].title()}</b> projeta {s['pct_global']:.0f}% da meta — destaque do mês.")
    if novos:
        pos.append(f"<b>{novos} parceiros reativados/novos</b> produzindo este mês.")
    for b in bancos_a:
        pos.append(f"<b>{b['nome']}</b> em alta: {b['pct']:+.0f}% vs mês anterior ({_m(b['proj'])}).")
    if (R.get('pct_proj_ant') or 0) > 0:
        pos.append(f"<b>Carteira crescendo</b> — projeção {R['pct_proj_ant']:+.1f}% sobre o mês anterior.")
    if not pos:
        pos.append("Sem destaques positivos relevantes neste corte.")

    if pct is not None and pct < 100:
        neg.append(f"<b>GAP de {_m(gap)}</b> para a meta global — projeção em {pct:.0f}%.")
    if nec > atual > 0:
        neg.append(f"<b>Ritmo insuficiente</b> — é preciso {_m(nec)}/dia ({nec/atual-1:+.0%} sobre o atual de {_m(atual)}/dia).")
    if churn:
        neg.append(f"<b>{len(churn)} parceiros em churn</b> — valiam {_m(churn_val)} no mês anterior.")
    if below and producing:
        neg.append(f"<b>{len(below)} parceiros abaixo do target</b> de R$ 25 mil ({len(below)/producing:.0%} dos {producing} produzindo).")
    for s in sups_risco[:3]:
        neg.append(f"<b>{s['nome'].title()}</b> em risco: {(s['pct_global'] or 0):.0f}% da meta (GAP {_m(s.get('gap_global'))}).")
    for b in bancos_q:
        neg.append(f"<b>{b['nome']}</b> em queda: {b['pct']:+.0f}% vs mês anterior.")
    if conc > 35:
        neg.append(f"<b>Concentração</b> — top 10 parceiros = {conc:.0f}% da projeção.")

    _acoes_comuns(acoes, churn, quase, len(quase))
    if sups_risco:
        s0 = sups_risco[0]
        acoes.append(f"<b>War room com {s0['nome'].title()}:</b> menor atingimento ({(s0['pct_global'] or 0):.0f}%). Revisar funil por regional e destravar os maiores parceiros da carteira.")
    if nec > atual:
        acoes.append(f"<b>Cadência diária:</b> acompanhar D-1 contra o alvo de {_m(nec)}/dia; cobrar plano dos supers abaixo de 85%.")
    for b in bancos_q[:1]:
        acoes.append(f"<b>Diagnóstico {b['nome']}:</b> queda de {abs(b['pct']):.0f}% — checar trava operacional, tabela/comissão ou migração.")
    if novos:
        acoes.append("<b>Reativados:</b> garantir a 2ª operação dos novos em até 15 dias — retenção 3x maior.")

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
    regs_q = sorted([r for r in regs_rel if (r.get('pct') or 0) < -15], key=lambda r: r['pct'])[:2]
    regs_a = sorted([r for r in regs_rel if (r.get('pct') or 0) > 10], key=lambda r: -(r['pct'] or 0))[:2]

    pos, neg, acoes = [], [], []
    if pct is not None and pct >= 100:
        pos.append(f"<b>Meta no ritmo</b> — projeção em {pct:.0f}% da meta.")
    for r in regs_a:
        pos.append(f"<b>Regional {r['nome'].title()}</b> crescendo {r['pct']:+.0f}% vs mês anterior.")
    if novos:
        pos.append(f"<b>{novos} parceiros reativados/novos</b> na sua carteira.")
    if (R.get('pct_proj_ant') or 0) > 0:
        pos.append(f"<b>Carteira crescendo</b> {R['pct_proj_ant']:+.1f}% sobre o mês anterior.")
    if not pos:
        pos.append("Sem destaques positivos neste corte — foco no plano de ação.")

    metab, pctb = sup.get('meta_banco_total') or 0, sup.get('pct_banco')
    if metab > 0 and pctb is not None:
        if pctb >= 100:
            pos.append(f"<b>Metas banco no ritmo</b> — {pctb:.0f}% de atingimento.")
        else:
            neg.append(f"<b>Metas banco em {pctb:.0f}%</b> — projeção {_m(sup.get('proj_banco_total'))} de {_m(metab)}. Detalhe na aba Meta Banco.")

    if pct is not None and pct < 100:
        neg.append(f"<b>GAP de {_m(gap)}</b> — projeção em {pct:.0f}% da meta.")
    if nec > atual > 0:
        neg.append(f"<b>Ritmo:</b> precisa de {_m(nec)}/dia nos {du_rest} dias úteis restantes ({nec/atual-1:+.0%} sobre o atual).")
    if churn:
        neg.append(f"<b>{len(churn)} parceiros zeraram</b> — valiam {_m(churn_val)}/mês.")
    if below and producing:
        neg.append(f"<b>{len(below)} parceiros abaixo do target</b> ({len(below)/producing:.0%} dos {producing} produzindo).")
    for r in regs_q:
        neg.append(f"<b>Regional {r['nome'].title()}</b> em queda: {r['pct']:+.0f}% vs mês anterior.")

    _acoes_comuns(acoes, churn, quase, len(quase))
    if regs_q:
        acoes.append(f"<b>Reunião com {regs_q[0]['nome'].title()}:</b> maior queda da carteira — revisar funil comercial a comercial.")
    if nec > atual:
        acoes.append(f"<b>Cadência:</b> alvo diário de {_m(nec)} — distribuir por regional e acompanhar D-1.")
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

    coms_rel = [c for c in reg.get('comerciais', []) if (c.get('ant') or 0) > 50000]
    coms_q = sorted([c for c in coms_rel if (c.get('pct') or 0) < -20], key=lambda c: c['pct'])[:2]
    coms_a = sorted([c for c in coms_rel if (c.get('pct') or 0) > 10], key=lambda c: -(c['pct'] or 0))[:2]

    pos, neg, acoes = [], [], []
    if (reg.get('pct') or 0) > 0:
        pos.append(f"<b>Carteira crescendo</b> {reg['pct']:+.1f}% vs mês anterior.")
    for c in coms_a:
        pos.append(f"<b>{c['nome'].title()}</b> em alta: {c['pct']:+.0f}%.")
    if novos:
        pos.append(f"<b>{novos} parceiros reativados/novos</b> este mês.")
    if not pos:
        pos.append("Sem destaques positivos neste corte.")

    if (reg.get('pct') or 0) < 0:
        neg.append(f"<b>Projeção em queda</b> {reg['pct']:+.1f}% vs mês anterior.")
    if churn:
        neg.append(f"<b>{len(churn)} parceiros zeraram</b> — valiam {_m(churn_val)}/mês.")
    if below and producing:
        neg.append(f"<b>{len(below)} parceiros abaixo do target</b> ({len(below)/producing:.0%} dos {producing}).")
    for c in coms_q:
        neg.append(f"<b>{c['nome'].title()}</b> em queda: {c['pct']:+.0f}% — precisa de apoio.")

    if meta_node:
        _bullets_metas(meta_node, pos, neg, acoes, du_p, du_rest)
        reg = dict(reg, _meta_global=meta_node.get('meta_global'), _pct_global=meta_node.get('pct_global'))
    _acoes_comuns(acoes, churn, quase, len(quase))
    if coms_q:
        acoes.append(f"<b>1:1 com {coms_q[0]['nome'].title()}:</b> maior queda da regional — mapear os parceiros que esfriaram.")
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

    pos, neg, acoes = [], [], []
    if (com.get('pct') or 0) > 0:
        pos.append(f"<b>Sua carteira cresce</b> {com['pct']:+.1f}% vs mês anterior.")
    if novos:
        pos.append(f"<b>{novos} parceiros reativados/novos</b> — boa ativação!")
    if tops:
        pos.append(f"<b>Maior parceiro:</b> {_nome_curto(tops[0][0])} projetando {_m(tops[0][1])}.")
    if not pos:
        pos.append("Sem destaques positivos neste corte.")

    if (com.get('pct') or 0) < 0:
        neg.append(f"<b>Projeção em queda</b> {com['pct']:+.1f}% vs mês anterior.")
    if churn:
        nomes = ', '.join(_nome_curto(c['parceiro']) for c in churn[:5])
        neg.append(f"<b>{len(churn)} parceiros seus zeraram</b> (valiam {_m(churn_val)}): {nomes}.")
    if below:
        neg.append(f"<b>{len(below)} parceiros abaixo de R$ 25 mil</b> — potencial de ticket parado.")
    if conc1 > 40:
        neg.append(f"<b>Dependência:</b> {_nome_curto(tops[0][0])} é {conc1:.0f}% da sua produção — risco se esfriar.")

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
    """Resumo executivo de uma carteira filtrada por convênios (sem metas —
    convênios públicos não têm meta atribuída)."""
    R = cart.get('resumo', {})
    du_t, du_p = info['dias_uteis_total'], info['dias_uteis_passados']
    ant, atu, proj = R.get('prod_anterior') or 0, R.get('prod_atual') or 0, R.get('proj_atual') or 0
    pct = R.get('pct_proj_ant')
    producing = R.get('n_ativos') or R.get('n_parceiros_atu') or 0
    novos, n_churn = R.get('n_novos') or 0, R.get('n_churn') or 0

    churn = cart.get('churn', [])
    churn_val = sum((c.get('prod_ant') or 0) for c in churn)
    below, quase, _producing2, _novos2, tops = _metricas_parceiros(cart.get('supers'))

    bancos = [b for b in cart.get('por_banco', []) if (b.get('ant') or 0) > 30000]
    bancos_q = sorted([b for b in bancos if (b.get('pct') or 0) < -15], key=lambda b: b['pct'])[:2]
    bancos_a = sorted([b for b in bancos if (b.get('pct') or 0) > 15], key=lambda b: -b['pct'])[:2]

    pos, neg, acoes = [], [], []
    if pct is not None and pct >= 0:
        pos.append(f"<b>Carteira de convênios crescendo</b> {pct:+.1f}% vs mês anterior.")
    if novos:
        pos.append(f"<b>{novos} parceiros reativados/novos</b> produzindo este mês.")
    for b in bancos_a:
        pos.append(f"<b>{b['nome']}</b> em alta: {b['pct']:+.0f}% vs mês anterior ({_m(b['proj'])}).")
    if not pos:
        pos.append("Sem destaques positivos relevantes neste corte.")

    if pct is not None and pct < 0:
        neg.append(f"<b>Projeção em queda</b> {pct:+.1f}% vs mês anterior.")
    if churn:
        neg.append(f"<b>{len(churn)} parceiros em churn</b> — valiam {_m(churn_val)} no mês anterior.")
    if below and producing:
        neg.append(f"<b>{len(below)} parceiros abaixo do target</b> de R$ 25 mil ({len(below)/producing:.0%} dos {producing} produzindo).")
    for b in bancos_q:
        neg.append(f"<b>{b['nome']}</b> em queda: {b['pct']:+.0f}% vs mês anterior.")

    _acoes_comuns(acoes, churn, quase, len(quase))
    for b in bancos_q[:1]:
        acoes.append(f"<b>Diagnóstico {b['nome']}:</b> queda de {abs(b['pct']):.0f}% — checar trava operacional, tabela/comissão ou migração.")
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
