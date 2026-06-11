-- ═══════════════════════════════════════════════════════════════════
-- GESTÃO COMERCIAL — NOVA PROMOTORA
-- Schema Supabase (rodar no SQL Editor do projeto)
-- ═══════════════════════════════════════════════════════════════════

-- ── Produção mensal (producao_2026.xlsx) ─────────────────────────────
create table if not exists producao (
  id               bigint generated always as identity primary key,
  mes              text not null,              -- '2026-06'
  parceiro         text,
  comercial        text,
  regional         text,
  superintendente  text,
  banco            text,
  convenio         text,
  tipo_operacao    text,
  status_corretor  smallint,
  valor            numeric(14,2) not null default 0
);
create index if not exists idx_producao_mes   on producao (mes);
create index if not exists idx_producao_sup   on producao (superintendente);
create index if not exists idx_producao_reg   on producao (regional);
create index if not exists idx_producao_com   on producao (comercial);

-- ── Digitações (base_digitacoes.xlsx, janela móvel) ──────────────────
create table if not exists digitacoes (
  id               bigint generated always as identity primary key,
  corretor         text,
  comercial        text,
  regional         text,
  superintendente  text,
  banco            text,
  orgao            text,
  operacao         text,
  status           text,
  data             date,
  valor            numeric(14,2) not null default 0
);
create index if not exists idx_dig_data on digitacoes (data);
create index if not exists idx_dig_sup  on digitacoes (superintendente);

-- ── Hierarquia comercial (HIERARQUIA COMERCIAL.xlsx) ─────────────────
create table if not exists hierarquia (
  id                 bigint generated always as identity primary key,
  cod_parceiro       text,
  parceiro           text,
  multilojas_filiado text,
  multilojas_master  text,
  comercial          text,
  regional           text,
  superintendente    text,
  status             text
);
create index if not exists idx_hier_cod on hierarquia (cod_parceiro);

-- ── Metas globais (config/meta_global_2026.xlsx — matriz super × mês) ─
create table if not exists metas_global (
  id               bigint generated always as identity primary key,
  mes              text not null,              -- '2026-06'
  superintendente  text not null,
  meta             numeric(14,2)
);
create index if not exists idx_mglobal_mes on metas_global (mes);

-- ── Metas banco (meta_banco.xlsx, abas metas + comerciais) ───────────
create table if not exists metas_banco (
  id               bigint generated always as identity primary key,
  mes              text not null,
  banco_display    text,
  banco_filtro     text,
  convenio_filtro  text,
  tipo_filtro      text,
  meta_total       numeric(14,2)
);
create table if not exists metas_banco_comerciais (
  id               bigint generated always as identity primary key,
  mes              text not null,
  comercial        text
);

-- ── Calendário de dias úteis (config/calendario.xlsx) ────────────────
create table if not exists calendario (
  mes              text primary key,           -- '2026-06'
  dias_uteis       smallint
);

-- ── Perfis de acesso (substitui auth.json na Fase 3) ────────────────
create table if not exists perfis (
  id               uuid primary key default gen_random_uuid(),
  login            text unique not null,
  nome             text,
  role             text not null check (role in ('admin','super','regional')),
  entidade         text,
  super_entidade   text
);

-- ── Metadados de carga (controle de atualização) ─────────────────────
create table if not exists cargas (
  tabela           text primary key,
  atualizado_em    timestamptz default now(),
  linhas           integer
);

-- ═══════════════════════════════════════════════════════════════════
-- RLS — por enquanto fechado para anon; o ETL usa service_role (bypassa)
-- Fase 2 (leitura no dashboard) vai liberar SELECT via policies
-- ═══════════════════════════════════════════════════════════════════
alter table producao               enable row level security;
alter table digitacoes             enable row level security;
alter table hierarquia             enable row level security;
alter table metas_global           enable row level security;
alter table metas_banco            enable row level security;
alter table metas_banco_comerciais enable row level security;
alter table calendario             enable row level security;
alter table perfis                 enable row level security;
alter table cargas                 enable row level security;
