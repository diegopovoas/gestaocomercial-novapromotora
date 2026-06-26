-- =====================================================================
-- PAINEL DE CONTROLE DE USO — Gestão Comercial Nova Promotora
-- Execute no SQL Editor do Supabase: https://supabase.com/dashboard
-- =====================================================================

-- 1. Tabela de log de logins
CREATE TABLE IF NOT EXISTS public.login_log (
  id bigserial PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  login text NOT NULL,
  logged_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS login_log_login_idx ON public.login_log(login);
CREATE INDEX IF NOT EXISTS login_log_at_idx    ON public.login_log(logged_at DESC);

-- Garante que apenas admins leem a tabela via REST (acesso direto bloqueado)
ALTER TABLE public.login_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "admins_podem_ler_login_log"
  ON public.login_log FOR SELECT
  USING (public.is_admin());

-- 2. Função trigger
CREATE OR REPLACE FUNCTION public._on_auth_login()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  IF NEW.last_sign_in_at IS DISTINCT FROM OLD.last_sign_in_at
     AND NEW.last_sign_in_at IS NOT NULL THEN
    INSERT INTO public.login_log(user_id, login, logged_at)
    VALUES (NEW.id, NEW.email, NEW.last_sign_in_at);
  END IF;
  RETURN NEW;
END;
$$;

-- 3. Trigger em auth.users
DROP TRIGGER IF EXISTS trg_auth_login ON auth.users;
CREATE TRIGGER trg_auth_login
  AFTER UPDATE ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public._on_auth_login();

-- 4. RPC para o owner buscar dados de uso
CREATE OR REPLACE FUNCTION public.owner_painel_uso()
RETURNS TABLE(
  login            text,
  nome             text,
  role             text,
  entidade         text,
  super_entidade   text,
  regional_entidade text,
  criado_em        timestamptz,
  ultimo_acesso    timestamptz,
  dias_sem_acesso  int,
  logins_30d       bigint,
  bloqueado        boolean
) LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  -- Só owner pode chamar
  IF NOT EXISTS (
    SELECT 1 FROM public.perfis
    WHERE login = auth.jwt()->>'email' AND role = 'owner'
  ) THEN
    RAISE EXCEPTION 'Acesso restrito ao owner';
  END IF;

  RETURN QUERY
    SELECT
      p.login,
      p.nome,
      p.role,
      p.entidade,
      p.super_entidade,
      p.regional_entidade,
      u.created_at                                          AS criado_em,
      u.last_sign_in_at                                     AS ultimo_acesso,
      CASE WHEN u.last_sign_in_at IS NULL THEN NULL
           ELSE EXTRACT(DAY FROM now() - u.last_sign_in_at)::int
      END                                                   AS dias_sem_acesso,
      COALESCE(ll.cnt, 0)                                   AS logins_30d,
      COALESCE(u.banned_until > now(), false)               AS bloqueado
    FROM public.perfis p
    LEFT JOIN auth.users u ON u.email = p.login
    LEFT JOIN (
      SELECT l.login, count(*) AS cnt
      FROM public.login_log l
      WHERE l.logged_at >= now() - interval '30 days'
      GROUP BY l.login
    ) ll ON ll.login = p.login
    ORDER BY p.role, p.login;
END;
$$;

-- Confirma
SELECT 'Instalação concluída com sucesso!' AS status;
