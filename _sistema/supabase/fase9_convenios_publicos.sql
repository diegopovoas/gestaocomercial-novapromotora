-- ═══════════════════════════════════════════════════════════════════
-- FASE 9 — Convênios Públicos: novo painel + papel gestor_convenios
-- Rodar no SQL Editor do Supabase
-- ═══════════════════════════════════════════════════════════════════

-- 1. Aceitar novo papel gestor_convenios
ALTER TABLE public.perfis DROP CONSTRAINT IF EXISTS perfis_role_check;
ALTER TABLE public.perfis ADD CONSTRAINT perfis_role_check
  CHECK (role IN ('owner','admin','super','regional','comercial','pronto','gestor_convenios'));

-- 2. Tabela de convênios configurados como públicos
CREATE TABLE IF NOT EXISTS public.convenios_publicos_config (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  convenio   text NOT NULL UNIQUE,
  ativo      boolean DEFAULT true,
  criado_em  timestamptz DEFAULT now()
);
ALTER TABLE public.convenios_publicos_config ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "conv_pub_config_read" ON public.convenios_publicos_config;
CREATE POLICY "conv_pub_config_read" ON public.convenios_publicos_config
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.perfis p
      WHERE p.login = auth.jwt()->>'email'
        AND p.role IN ('owner','admin','gestor_convenios')
    )
  );

-- 3. Tabela de vínculo gestor ↔ convênios permitidos
CREATE TABLE IF NOT EXISTS public.gestor_convenios_acesso (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  login      text NOT NULL,
  convenio   text NOT NULL,
  ativo      boolean DEFAULT true,
  UNIQUE(login, convenio)
);
ALTER TABLE public.gestor_convenios_acesso ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "gestor_acesso_admin" ON public.gestor_convenios_acesso;
CREATE POLICY "gestor_acesso_admin" ON public.gestor_convenios_acesso
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.perfis p
      WHERE p.login = auth.jwt()->>'email'
        AND p.role IN ('owner','admin')
    )
  );

DROP POLICY IF EXISTS "gestor_acesso_proprio" ON public.gestor_convenios_acesso;
CREATE POLICY "gestor_acesso_proprio" ON public.gestor_convenios_acesso
  FOR SELECT TO authenticated
  USING (login = auth.jwt()->>'email');

-- 4. Atualizar RLS do dashboard_cache para gestor_convenios
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
          OR (p.role = 'gestor_convenios'   AND dashboard_cache.escopo = 'convenios_publicos')
        )
    )
  );

-- 5. RPCs para gestão de convênios públicos

-- Listar convênios configurados
CREATE OR REPLACE FUNCTION public.admin_listar_convenios_config()
RETURNS TABLE(id bigint, convenio text, ativo boolean)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
  IF NOT public.is_admin() THEN
    RAISE EXCEPTION 'Apenas administradores';
  END IF;
  RETURN QUERY
    SELECT c.id, c.convenio, c.ativo
    FROM public.convenios_publicos_config c
    ORDER BY c.convenio;
END $$;

-- Adicionar/atualizar convênio público
CREATE OR REPLACE FUNCTION public.admin_set_convenio_publico(p_convenio text, p_ativo boolean)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
  IF NOT public.is_admin() THEN
    RAISE EXCEPTION 'Apenas administradores';
  END IF;
  INSERT INTO public.convenios_publicos_config (convenio, ativo)
  VALUES (trim(p_convenio), p_ativo)
  ON CONFLICT (convenio) DO UPDATE SET ativo = p_ativo;
END $$;

-- Remover convênio público
CREATE OR REPLACE FUNCTION public.admin_remover_convenio_publico(p_convenio text)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
  IF NOT public.is_admin() THEN
    RAISE EXCEPTION 'Apenas administradores';
  END IF;
  DELETE FROM public.convenios_publicos_config WHERE convenio = trim(p_convenio);
END $$;

-- Listar convênios de um gestor
CREATE OR REPLACE FUNCTION public.admin_listar_gestor_acesso(p_login text)
RETURNS TABLE(convenio text, ativo boolean)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
  IF NOT public.is_admin() THEN
    RAISE EXCEPTION 'Apenas administradores';
  END IF;
  RETURN QUERY
    SELECT g.convenio, g.ativo
    FROM public.gestor_convenios_acesso g
    WHERE g.login = lower(p_login)
    ORDER BY g.convenio;
END $$;

-- Vincular/desvincular convênio a gestor
CREATE OR REPLACE FUNCTION public.admin_set_gestor_acesso(p_login text, p_convenio text, p_ativo boolean)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
  IF NOT public.is_admin() THEN
    RAISE EXCEPTION 'Apenas administradores';
  END IF;
  IF p_ativo THEN
    INSERT INTO public.gestor_convenios_acesso (login, convenio, ativo)
    VALUES (lower(p_login), trim(p_convenio), true)
    ON CONFLICT (login, convenio) DO UPDATE SET ativo = true;
  ELSE
    DELETE FROM public.gestor_convenios_acesso
    WHERE login = lower(p_login) AND convenio = trim(p_convenio);
  END IF;
END $$;

-- Buscar convênios permitidos do gestor logado (para o front)
CREATE OR REPLACE FUNCTION public.meus_convenios()
RETURNS TABLE(convenio text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
  RETURN QUERY
    SELECT g.convenio
    FROM public.gestor_convenios_acesso g
    WHERE g.login = auth.jwt()->>'email'
      AND g.ativo = true;
END $$;

-- 6. Atualizar admin_criar_usuario para aceitar gestor_convenios
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
    NULLIF(p_entidade, ''),
    CASE WHEN p_role IN ('regional','comercial') THEN NULLIF(p_super, '') ELSE NULL END,
    CASE WHEN p_role = 'comercial' THEN NULLIF(p_regional, '') ELSE NULL END
  );
END $$;

-- 7. Atualizar admin_editar_usuario para aceitar gestor_convenios
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
         entidade          = NULLIF(p_entidade, ''),
         super_entidade    = CASE WHEN p_role IN ('regional', 'comercial')
                                  THEN NULLIF(p_super, '') ELSE NULL END,
         regional_entidade = CASE WHEN p_role = 'comercial'
                                  THEN NULLIF(p_regional, '') ELSE NULL END
   WHERE login = lower(alvo);

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Usuario % nao encontrado', alvo;
  END IF;
END $$;

-- 8. Permissões das novas funções
REVOKE EXECUTE ON FUNCTION public.admin_listar_convenios_config()                FROM public, anon;
REVOKE EXECUTE ON FUNCTION public.admin_set_convenio_publico(text, boolean)      FROM public, anon;
REVOKE EXECUTE ON FUNCTION public.admin_remover_convenio_publico(text)           FROM public, anon;
REVOKE EXECUTE ON FUNCTION public.admin_listar_gestor_acesso(text)               FROM public, anon;
REVOKE EXECUTE ON FUNCTION public.admin_set_gestor_acesso(text, text, boolean)   FROM public, anon;
REVOKE EXECUTE ON FUNCTION public.meus_convenios()                               FROM public, anon;
REVOKE EXECUTE ON FUNCTION public.admin_criar_usuario(text,text,text,text,text,text,text) FROM public, anon;
REVOKE EXECUTE ON FUNCTION public.admin_editar_usuario(text,text,text,text,text,text)     FROM public, anon;

GRANT EXECUTE ON FUNCTION public.admin_listar_convenios_config()                TO authenticated;
GRANT EXECUTE ON FUNCTION public.admin_set_convenio_publico(text, boolean)      TO authenticated;
GRANT EXECUTE ON FUNCTION public.admin_remover_convenio_publico(text)           TO authenticated;
GRANT EXECUTE ON FUNCTION public.admin_listar_gestor_acesso(text)               TO authenticated;
GRANT EXECUTE ON FUNCTION public.admin_set_gestor_acesso(text, text, boolean)   TO authenticated;
GRANT EXECUTE ON FUNCTION public.meus_convenios()                               TO authenticated;
GRANT EXECUTE ON FUNCTION public.admin_criar_usuario(text,text,text,text,text,text,text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.admin_editar_usuario(text,text,text,text,text,text)     TO authenticated;
