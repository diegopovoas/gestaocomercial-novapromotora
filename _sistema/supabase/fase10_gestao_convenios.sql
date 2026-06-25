-- ═══════════════════════════════════════════════════════════════════
-- FASE 10 — Gestão de Convênios: papel gestor_convenios com payload
-- individual por usuário (1 escopo de dashboard_cache por gestor,
-- igual ao padrão já usado para superintendente).
-- Rodar no SQL Editor do Supabase (ou via psycopg2, idempotente).
-- ═══════════════════════════════════════════════════════════════════

-- 1. Aceitar novo papel gestor_convenios
ALTER TABLE public.perfis DROP CONSTRAINT IF EXISTS perfis_role_check;
ALTER TABLE public.perfis ADD CONSTRAINT perfis_role_check
  CHECK (role IN ('owner','admin','super','regional','comercial','pronto','gestor_convenios'));

-- 2. Tabela de convênios atribuídos a cada gestor_convenios
CREATE TABLE IF NOT EXISTS public.usuarios_convenios_permitidos (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  login      text NOT NULL,
  convenio   text NOT NULL,
  ativo      boolean DEFAULT true,
  criado_em  timestamptz DEFAULT now(),
  UNIQUE(login, convenio)
);
ALTER TABLE public.usuarios_convenios_permitidos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "ucp_admin_all" ON public.usuarios_convenios_permitidos;
CREATE POLICY "ucp_admin_all" ON public.usuarios_convenios_permitidos
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.perfis p
      WHERE p.login = auth.jwt()->>'email'
        AND p.role IN ('owner','admin')
    )
  );

-- 3. RLS do dashboard_cache: gestor_convenios usa o mesmo mecanismo do
--    super — escopo = perfis.entidade (guarda o próprio login).
DROP POLICY IF EXISTS "cache por escopo" ON public.dashboard_cache;
CREATE POLICY "cache por escopo" ON public.dashboard_cache
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.perfis p
      WHERE p.login = auth.jwt()->>'email'
        AND (
          p.role IN ('admin', 'owner')
          OR (p.role = 'super'              AND p.entidade       = dashboard_cache.escopo)
          OR (p.role = 'regional'           AND p.super_entidade = dashboard_cache.escopo)
          OR (p.role = 'comercial'          AND p.super_entidade = dashboard_cache.escopo)
          OR (p.role = 'gestor_convenios'   AND p.entidade       = dashboard_cache.escopo)
        )
    )
  );

-- 4. RPCs para admin gerenciar convênios por gestor

-- Lista o universo de convênios já vistos na produção (para o admin escolher)
CREATE OR REPLACE FUNCTION public.admin_listar_usuario_convenios(p_login text)
RETURNS TABLE(convenio text, ativo boolean)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
  IF NOT public.is_admin() THEN
    RAISE EXCEPTION 'Apenas administradores';
  END IF;
  RETURN QUERY
    SELECT u.convenio, u.ativo
    FROM public.usuarios_convenios_permitidos u
    WHERE u.login = lower(p_login)
    ORDER BY u.convenio;
END $$;

-- Vincula/desvincula um convênio a um gestor
CREATE OR REPLACE FUNCTION public.admin_set_usuario_convenio(p_login text, p_convenio text, p_ativo boolean)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
  IF NOT public.is_admin() THEN
    RAISE EXCEPTION 'Apenas administradores';
  END IF;
  IF p_ativo THEN
    INSERT INTO public.usuarios_convenios_permitidos (login, convenio, ativo)
    VALUES (lower(p_login), trim(p_convenio), true)
    ON CONFLICT (login, convenio) DO UPDATE SET ativo = true;
  ELSE
    DELETE FROM public.usuarios_convenios_permitidos
    WHERE login = lower(p_login) AND convenio = trim(p_convenio);
  END IF;
END $$;

-- 5. Atualizar admin_criar_usuario / admin_editar_usuario para aceitar
--    gestor_convenios — entidade é preenchida automaticamente com o
--    próprio login (chave de escopo do cache), sem depender do admin.
CREATE OR REPLACE FUNCTION public.admin_criar_usuario(
  p_email text, p_senha text, p_nome text,
  p_role text, p_entidade text DEFAULT '',
  p_super text DEFAULT '', p_regional text DEFAULT '')
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
  v_uid uuid;
BEGIN
  IF NOT public.is_admin() THEN
    RAISE EXCEPTION 'Apenas administradores';
  END IF;
  IF p_role NOT IN ('admin','super','regional','comercial','gestor_convenios') THEN
    RAISE EXCEPTION 'Papel invalido: %', p_role;
  END IF;
  IF length(p_senha) < 6 THEN
    RAISE EXCEPTION 'A senha precisa ter pelo menos 6 caracteres';
  END IF;

  v_uid := extensions.uuid_generate_v4();
  INSERT INTO auth.users (
    id, instance_id, email, encrypted_password,
    email_confirmed_at, created_at, updated_at,
    raw_app_meta_data, raw_user_meta_data, aud, role
  ) VALUES (
    v_uid, '00000000-0000-0000-0000-000000000000',
    lower(p_email),
    extensions.crypt(p_senha, extensions.gen_salt('bf')),
    now(), now(), now(),
    '{"provider":"email","providers":["email"]}'::jsonb,
    jsonb_build_object('nome', p_nome),
    'authenticated', 'authenticated'
  );

  INSERT INTO public.perfis (login, nome, role, entidade, super_entidade, regional_entidade)
  VALUES (
    lower(p_email), p_nome, p_role,
    CASE WHEN p_role = 'gestor_convenios' THEN lower(p_email) ELSE NULLIF(p_entidade, '') END,
    CASE WHEN p_role IN ('regional','comercial') THEN NULLIF(p_super, '') ELSE NULL END,
    CASE WHEN p_role = 'comercial' THEN NULLIF(p_regional, '') ELSE NULL END
  );
END $$;

CREATE OR REPLACE FUNCTION public.admin_editar_usuario(
  alvo text, p_nome text, p_role text, p_entidade text, p_super text,
  p_regional text DEFAULT '')
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
  IF NOT public.is_admin() THEN
    RAISE EXCEPTION 'Apenas administradores';
  END IF;
  IF EXISTS (SELECT 1 FROM public.perfis WHERE login = lower(alvo) AND role = 'owner') THEN
    RAISE EXCEPTION 'Usuario owner e protegido';
  END IF;
  IF p_role NOT IN ('admin','super','regional','comercial','gestor_convenios') THEN
    RAISE EXCEPTION 'Papel invalido: %', p_role;
  END IF;
  IF p_role = 'super' AND coalesce(p_entidade, '') = '' THEN
    RAISE EXCEPTION 'Superintendente precisa de entidade';
  END IF;
  IF p_role = 'regional' AND (coalesce(p_entidade, '') = '' OR coalesce(p_super, '') = '') THEN
    RAISE EXCEPTION 'Regional precisa de entidade e superintendente';
  END IF;
  IF p_role = 'comercial' AND (coalesce(p_entidade, '') = '' OR coalesce(p_super, '') = ''
                               OR coalesce(p_regional, '') = '') THEN
    RAISE EXCEPTION 'Comercial precisa de entidade, regional e superintendente';
  END IF;

  UPDATE public.perfis
     SET nome              = p_nome,
         role              = p_role,
         entidade          = CASE WHEN p_role = 'gestor_convenios' THEN lower(alvo)
                                   ELSE NULLIF(p_entidade, '') END,
         super_entidade    = CASE WHEN p_role IN ('regional', 'comercial')
                                  THEN NULLIF(p_super, '') ELSE NULL END,
         regional_entidade = CASE WHEN p_role = 'comercial'
                                  THEN NULLIF(p_regional, '') ELSE NULL END
   WHERE login = lower(alvo);

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Usuario % nao encontrado', alvo;
  END IF;
END $$;

-- 6. Permissões das novas funções
REVOKE EXECUTE ON FUNCTION public.admin_listar_usuario_convenios(text)            FROM public, anon;
REVOKE EXECUTE ON FUNCTION public.admin_set_usuario_convenio(text, text, boolean) FROM public, anon;
REVOKE EXECUTE ON FUNCTION public.admin_criar_usuario(text,text,text,text,text,text,text) FROM public, anon;
REVOKE EXECUTE ON FUNCTION public.admin_editar_usuario(text,text,text,text,text,text)     FROM public, anon;

GRANT EXECUTE ON FUNCTION public.admin_listar_usuario_convenios(text)            TO authenticated;
GRANT EXECUTE ON FUNCTION public.admin_set_usuario_convenio(text, text, boolean) TO authenticated;
GRANT EXECUTE ON FUNCTION public.admin_criar_usuario(text,text,text,text,text,text,text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.admin_editar_usuario(text,text,text,text,text,text)     TO authenticated;
