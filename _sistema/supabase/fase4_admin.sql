-- ═══════════════════════════════════════════════════════════════════
-- FASE 4 — Funções administrativas (listar/bloquear/excluir/resetar senha)
-- Só usuários com role=admin no perfis conseguem executar.
-- Rodar no SQL Editor do Supabase
-- ═══════════════════════════════════════════════════════════════════

-- Helper: o usuário logado é admin/owner?
create or replace function public.is_admin()
returns boolean
language sql stable security definer set search_path = ''
as $$
  select exists (
    select 1 from public.perfis
    where login = (auth.jwt()->>'email') and role in ('admin', 'owner')
  );
$$;

-- Listar usuários (com status de bloqueio do Auth)
create or replace function public.admin_listar_usuarios()
returns table(login text, nome text, role text, entidade text,
              super_entidade text, bloqueado boolean)
language plpgsql security definer set search_path = ''
as $$
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores';
  end if;
  return query
    select p.login, p.nome, p.role, p.entidade, p.super_entidade,
           coalesce(u.banned_until > now(), false) as bloqueado
    from public.perfis p
    left join auth.users u on u.email = p.login
    order by p.role, p.login;
end $$;

-- Resetar senha de um usuário
create or replace function public.admin_reset_senha(alvo text, nova text)
returns void
language plpgsql security definer set search_path = ''
as $$
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores';
  end if;
  if length(nova) < 6 then
    raise exception 'A senha precisa ter pelo menos 6 caracteres';
  end if;
  if exists (select 1 from public.perfis where login = lower(alvo) and role = 'owner') then
    raise exception 'Usuário owner é protegido';
  end if;
  update auth.users
     set encrypted_password = extensions.crypt(nova, extensions.gen_salt('bf'))
   where email = lower(alvo);
  if not found then
    raise exception 'Usuário % não encontrado', alvo;
  end if;
end $$;

-- Bloquear / desbloquear acesso
create or replace function public.admin_bloquear(alvo text, bloquear boolean)
returns void
language plpgsql security definer set search_path = ''
as $$
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores';
  end if;
  if exists (select 1 from public.perfis where login = lower(alvo) and role = 'owner') then
    raise exception 'Usuário owner é protegido';
  end if;
  update auth.users
     set banned_until = case when bloquear then '2999-01-01'::timestamptz else null end
   where email = lower(alvo);
  if not found then
    raise exception 'Usuário % não encontrado', alvo;
  end if;
end $$;

-- Excluir usuário (Auth + perfil)
create or replace function public.admin_excluir(alvo text)
returns void
language plpgsql security definer set search_path = ''
as $$
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores';
  end if;
  if exists (select 1 from public.perfis where login = lower(alvo) and role = 'owner') then
    raise exception 'Usuário owner é protegido';
  end if;
  delete from auth.users  where email = lower(alvo);
  delete from public.perfis where login = lower(alvo);
end $$;

-- Permissões: só usuários logados podem chamar (a checagem de admin é interna)
revoke execute on function public.is_admin()                       from public, anon;
revoke execute on function public.admin_listar_usuarios()          from public, anon;
revoke execute on function public.admin_reset_senha(text, text)    from public, anon;
revoke execute on function public.admin_bloquear(text, boolean)    from public, anon;
revoke execute on function public.admin_excluir(text)              from public, anon;
grant  execute on function public.is_admin()                       to authenticated;
grant  execute on function public.admin_listar_usuarios()          to authenticated;
grant  execute on function public.admin_reset_senha(text, text)    to authenticated;
grant  execute on function public.admin_bloquear(text, boolean)    to authenticated;
grant  execute on function public.admin_excluir(text)              to authenticated;
