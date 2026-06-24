-- ═══════════════════════════════════════════════════════════════════
-- FASE 8 — Owner do sistema
-- Objetivo:
--   - Diego vira role=owner.
--   - owner enxerga tudo como admin.
--   - admin comum nao bloqueia, exclui, reseta senha ou rebaixa owner.
-- ═══════════════════════════════════════════════════════════════════

-- 1. Aceita o papel owner preservando os papeis existentes.
alter table public.perfis drop constraint if exists perfis_role_check;
alter table public.perfis add constraint perfis_role_check
  check (role in ('owner', 'admin', 'super', 'regional', 'comercial', 'pronto'));

-- 2. Admin interno inclui owner.
create or replace function public.is_admin()
returns boolean
language sql stable security definer set search_path = ''
as $$
  select exists (
    select 1 from public.perfis
    where login = (auth.jwt()->>'email') and role in ('admin', 'owner')
  );
$$;

-- 3. Owner le o payload completo de admin.
drop policy if exists "cache por escopo" on public.dashboard_cache;
create policy "cache por escopo" on public.dashboard_cache
  for select to authenticated
  using (
    exists (
      select 1 from public.perfis p
      where p.login = auth.jwt()->>'email'
        and (
          p.role in ('admin', 'owner')
          or (p.role = 'super'     and p.entidade       = dashboard_cache.escopo)
          or (p.role = 'regional'  and p.super_entidade = dashboard_cache.escopo)
          or (p.role = 'comercial' and p.super_entidade = dashboard_cache.escopo)
        )
    )
  );

-- 4. Protege owner contra reset de senha por admin comum.
create or replace function public.admin_reset_senha(alvo text, nova text)
returns void
language plpgsql security definer set search_path = ''
as $$
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores';
  end if;
  if exists (select 1 from public.perfis where login = lower(alvo) and role = 'owner') then
    raise exception 'Usuario owner e protegido';
  end if;
  if length(nova) < 6 then
    raise exception 'A senha precisa ter pelo menos 6 caracteres';
  end if;
  update auth.users
     set encrypted_password = extensions.crypt(nova, extensions.gen_salt('bf'))
   where email = lower(alvo);
  if not found then
    raise exception 'Usuario % nao encontrado', alvo;
  end if;
end $$;

-- 5. Protege owner contra bloqueio/desbloqueio por admin comum.
create or replace function public.admin_bloquear(alvo text, bloquear boolean)
returns void
language plpgsql security definer set search_path = ''
as $$
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores';
  end if;
  if exists (select 1 from public.perfis where login = lower(alvo) and role = 'owner') then
    raise exception 'Usuario owner e protegido';
  end if;
  update auth.users
     set banned_until = case when bloquear then '2999-01-01'::timestamptz else null end
   where email = lower(alvo);
  if not found then
    raise exception 'Usuario % nao encontrado', alvo;
  end if;
end $$;

-- 6. Protege owner contra exclusao por admin comum.
create or replace function public.admin_excluir(alvo text)
returns void
language plpgsql security definer set search_path = ''
as $$
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores';
  end if;
  if exists (select 1 from public.perfis where login = lower(alvo) and role = 'owner') then
    raise exception 'Usuario owner e protegido';
  end if;
  delete from auth.users  where email = lower(alvo);
  delete from public.perfis where login = lower(alvo);
end $$;

-- 7. Protege owner contra edicao/rebaixamento por admin comum.
create or replace function public.admin_editar_usuario(
  alvo text, p_nome text, p_role text, p_entidade text, p_super text,
  p_regional text default '')
returns void
language plpgsql security definer set search_path = ''
as $$
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores';
  end if;
  if exists (select 1 from public.perfis where login = lower(alvo) and role = 'owner') then
    raise exception 'Usuario owner e protegido';
  end if;
  if p_role not in ('admin', 'super', 'regional', 'comercial') then
    raise exception 'Papel invalido: %', p_role;
  end if;
  if p_role = 'super' and coalesce(p_entidade, '') = '' then
    raise exception 'Superintendente precisa de entidade';
  end if;
  if p_role = 'regional' and (coalesce(p_entidade, '') = '' or coalesce(p_super, '') = '') then
    raise exception 'Regional precisa de entidade e superintendente';
  end if;
  if p_role = 'comercial' and (coalesce(p_entidade, '') = '' or coalesce(p_super, '') = ''
                               or coalesce(p_regional, '') = '') then
    raise exception 'Comercial precisa de entidade, regional e superintendente';
  end if;

  update public.perfis
     set nome              = p_nome,
         role              = p_role,
         entidade          = nullif(p_entidade, ''),
         super_entidade    = case when p_role in ('regional', 'comercial')
                                  then nullif(p_super, '') else null end,
         regional_entidade = case when p_role = 'comercial'
                                  then nullif(p_regional, '') else null end
   where login = lower(alvo);

  if not found then
    raise exception 'Usuario % nao encontrado', alvo;
  end if;
end $$;

-- 8. Promove Diego a owner.
update public.perfis
   set role = 'owner',
       entidade = null,
       super_entidade = null,
       regional_entidade = null
 where login = 'diego.povoas@novapromotora.com';

-- 9. Permissoes das funcoes administrativas.
revoke execute on function public.is_admin()                       from public, anon;
revoke execute on function public.admin_reset_senha(text, text)    from public, anon;
revoke execute on function public.admin_bloquear(text, boolean)    from public, anon;
revoke execute on function public.admin_excluir(text)              from public, anon;
revoke execute on function public.admin_editar_usuario(text,text,text,text,text,text) from public, anon;
grant  execute on function public.is_admin()                       to authenticated;
grant  execute on function public.admin_reset_senha(text, text)    to authenticated;
grant  execute on function public.admin_bloquear(text, boolean)    to authenticated;
grant  execute on function public.admin_excluir(text)              to authenticated;
grant  execute on function public.admin_editar_usuario(text,text,text,text,text,text) to authenticated;
