-- ═══════════════════════════════════════════════════════════════════
-- FASE 2 — Cache do dashboard (payload pré-calculado pelo Python)
-- Rodar no SQL Editor do Supabase
-- ═══════════════════════════════════════════════════════════════════

create table if not exists dashboard_cache (
  escopo         text primary key,        -- 'admin' ou nome do super
  payload        jsonb not null,
  atualizado_em  timestamptz default now()
);

alter table dashboard_cache enable row level security;

-- Fase 2 (teste): leitura liberada para a chave publishable.
-- Mesmo nível de exposição do GitHub Pages atual.
-- Na Fase 3 isso será restrito por usuário autenticado.
drop policy if exists "leitura publica cache" on dashboard_cache;
create policy "leitura publica cache" on dashboard_cache
  for select to anon using (true);
