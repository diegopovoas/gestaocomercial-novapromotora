# Contexto — Gestão Comercial NOVA PROMOTORA

## Visão Geral
Dashboard de gestão comercial (produção, metas por banco, digitações, hierarquia)
com login individual e visão por escopo: admin vê tudo; superintendente, regional
e comercial veem apenas a própria carteira — garantido pelo banco (RLS).

## Links
- **Dashboard:** https://diegopovoas.github.io/gestaocomercial-novapromotora/
- **GitHub:** https://github.com/diegopovoas/gestaocomercial-novapromotora
- **Supabase:** projeto `drokcguxofvmdrnmedrx` (Intecom - Gestão Comercial, São Paulo)

## Arquitetura
```
Excels (produção, digitações, hierarquia, metas)
    ↓
_sistema/gerar_metas.py  (Python + pandas — cálculo de projeções, hierarquia, churn)
    ├→ dashboard_metas.html   (visão local da diretoria, sem login)
    ├→ index.html / app.html  (app publicado no GitHub Pages — só código, sem dados)
    └→ Supabase dashboard_cache (payloads por escopo: admin + 1 por superintendente)

Login: Supabase Auth (e-mail/senha) → RLS entrega só o payload do escopo do usuário
```

## Arquivos de Entrada (raiz da pasta)
| Arquivo | Conteúdo |
|---|---|
| `producao_2026.xlsx` | Produção mensal (D-1) |
| `base_digitacoes.xlsx` | Digitações (aba Base crua, sem PROCV) |
| `HIERARQUIA COMERCIAL.xlsx` | Hierarquia parceiro→comercial→regional→super |
| `meta_banco.xlsx` | Metas por banco (abas: metas, comerciais) |
| `config/meta_global_2026.xlsx` | Metas globais por superintendente |
| `config/calendario.xlsx` | Dias úteis do mês |

## Como Usar
| Ação | Como |
|---|---|
| Atualizar tudo | `2 - ATUALIZAR DASHBOARD.bat` |
| Re-enviar só dados ao banco | `5 - ATUALIZAR SUPABASE.bat` |
| Gerir usuários (criar/editar/bloquear/excluir/senha) | aba **Usuários** do dashboard (admin) |
| Trocar a própria senha | botão **Senha** no topo do dashboard |

## Papéis de Acesso
- **Admin** → tudo + gestão de usuários
- **Superintendente** → só a própria superintendência
- **Regional** → visão do super travada na sua regional
- **Comercial** → visão travada na própria carteira

## Recuperação de Desastre (recriar o Supabase do zero)
1. Criar projeto no Supabase → rodar no SQL Editor, em ordem:
   `_sistema/supabase/schema.sql` → `fase2_cache.sql` → `fase3_rls.sql` →
   `fase4_admin.sql` → `fase6e7_gestao_completa.sql`
2. Preencher `_sistema/supabase_config.json` (url + sb_secret) e atualizar
   SUPA_URL/SUPA_KEY em `_sistema/gerar_app_supabase.py`
3. Rodar `5 - ATUALIZAR SUPABASE.bat` e depois `2 - ATUALIZAR DASHBOARD.bat`
4. Recriar usuários pela aba Usuários do app

## Backup
A fonte da verdade são os Excels desta pasta (backup no Drive). O Supabase é
derivado e 100% reconstituível. Senhas trocadas pelos usuários vivem só no
Supabase Auth (em recuperação, voltam ao padrão e são redefinidas).
