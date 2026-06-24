-- ═══════════════════════════════════════════════════════════════════
-- FASE 3 — Segurança real: cada usuário só lê o próprio escopo
-- Rodar no SQL Editor do Supabase
-- ═══════════════════════════════════════════════════════════════════

-- Usuário autenticado lê apenas o próprio perfil
drop policy if exists "perfil proprio" on perfis;
create policy "perfil proprio" on perfis
  for select to authenticated
  using (login = auth.jwt()->>'email');

-- dashboard_cache: remove a leitura pública da Fase 2
drop policy if exists "leitura publica cache" on dashboard_cache;

-- Leitura por escopo: admin vê tudo; super vê sua entidade;
-- regional vê o payload do seu superintendente
drop policy if exists "cache por escopo" on dashboard_cache;
create policy "cache por escopo" on dashboard_cache
  for select to authenticated
  using (
    exists (
      select 1 from perfis p
      where p.login = auth.jwt()->>'email'
        and (
          p.role in ('admin', 'owner')
          or (p.role = 'super'    and p.entidade       = dashboard_cache.escopo)
          or (p.role = 'regional' and p.super_entidade = dashboard_cache.escopo)
        )
    )
  );
