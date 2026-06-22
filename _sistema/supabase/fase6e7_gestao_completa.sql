-- ═══════════════════════════════════════════════════════════════════
-- FASE 6 — Papel "comercial" (acesso travado no próprio comercial)
-- Rodar no SQL Editor do Supabase
-- ═══════════════════════════════════════════════════════════════════

-- 1. Aceita o papel comercial + coluna da regional dele
alter table public.perfis drop constraint if exists perfis_role_check;
alter table public.perfis add constraint perfis_role_check
  check (role in ('admin', 'super', 'regional', 'comercial', 'pronto'));
alter table public.perfis add column if not exists regional_entidade text;

-- 2. Comercial lê o payload do superintendente dele (a visão é travada no app)
drop policy if exists "cache por escopo" on dashboard_cache;
create policy "cache por escopo" on dashboard_cache
  for select to authenticated
  using (
    exists (
      select 1 from perfis p
      where p.login = auth.jwt()->>'email'
        and (
          p.role = 'admin'
          or (p.role = 'super'     and p.entidade       = dashboard_cache.escopo)
          or (p.role = 'regional'  and p.super_entidade = dashboard_cache.escopo)
          or (p.role = 'comercial' and p.super_entidade = dashboard_cache.escopo)
        )
    )
  );

-- 3. Listagem inclui a regional do comercial
drop function if exists public.admin_listar_usuarios();
create or replace function public.admin_listar_usuarios()
returns table(login text, nome text, role text, entidade text,
              super_entidade text, regional_entidade text, bloqueado boolean)
language plpgsql security definer set search_path = ''
as $$
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores';
  end if;
  return query
    select p.login, p.nome, p.role, p.entidade, p.super_entidade, p.regional_entidade,
           coalesce(u.banned_until > now(), false) as bloqueado
    from public.perfis p
    left join auth.users u on u.email = p.login
    order by p.role, p.login;
end $$;

-- 4. Edição com suporte a comercial
drop function if exists public.admin_editar_usuario(text, text, text, text, text);
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
  if p_role not in ('admin', 'super', 'regional', 'comercial', 'pronto') then
    raise exception 'Papel inválido: %', p_role;
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
    raise exception 'Usuário % não encontrado', alvo;
  end if;
end $$;

-- Permissões
revoke execute on function public.admin_listar_usuarios() from public, anon;
revoke execute on function public.admin_editar_usuario(text,text,text,text,text,text) from public, anon;
grant  execute on function public.admin_listar_usuarios() to authenticated;
grant  execute on function public.admin_editar_usuario(text,text,text,text,text,text) to authenticated;

-- ═══════════════════════════════════════════════════════════════════
-- FASE 7 — Criação de usuário pelo painel do app
-- ═══════════════════════════════════════════════════════════════════

create or replace function public.admin_criar_usuario(
  p_email text, p_senha text, p_nome text, p_role text,
  p_entidade text default '', p_super text default '', p_regional text default '')
returns void
language plpgsql security definer set search_path = ''
as $$
declare
  uid uuid := gen_random_uuid();
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores';
  end if;
  if p_email !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' then
    raise exception 'E-mail inválido: %', p_email;
  end if;
  if length(coalesce(p_senha, '')) < 6 then
    raise exception 'A senha precisa ter pelo menos 6 caracteres';
  end if;
  if p_role not in ('admin', 'super', 'regional', 'comercial', 'pronto') then
    raise exception 'Papel inválido: %', p_role;
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
  if exists (select 1 from auth.users where email = lower(p_email)) then
    raise exception 'Já existe usuário com o e-mail %', p_email;
  end if;

  insert into auth.users (instance_id, id, aud, role, email, encrypted_password,
    email_confirmed_at, raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
    confirmation_token, recovery_token, email_change, email_change_token_new, email_change_token_current)
  values ('00000000-0000-0000-0000-000000000000', uid, 'authenticated', 'authenticated',
    lower(p_email), extensions.crypt(p_senha, extensions.gen_salt('bf')),
    now(), '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb, now(), now(),
    '', '', '', '', '');

  insert into auth.identities (id, user_id, provider_id, identity_data, provider,
    last_sign_in_at, created_at, updated_at)
  values (gen_random_uuid(), uid, uid::text,
    jsonb_build_object('sub', uid::text, 'email', lower(p_email), 'email_verified', true),
    'email', now(), now(), now());

  insert into public.perfis (login, nome, role, entidade, super_entidade, regional_entidade)
  values (lower(p_email), p_nome, p_role,
          nullif(p_entidade, ''),
          case when p_role in ('regional', 'comercial') then nullif(p_super, '') else null end,
          case when p_role = 'comercial' then nullif(p_regional, '') else null end);
end $$;

revoke execute on function public.admin_criar_usuario(text,text,text,text,text,text,text) from public, anon;
grant  execute on function public.admin_criar_usuario(text,text,text,text,text,text,text) to authenticated;
