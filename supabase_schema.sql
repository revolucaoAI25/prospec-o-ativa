-- ============================================================
-- Prospec-o-Ativa · Supabase Schema
-- Execute este script no SQL Editor do seu projeto Supabase
-- (Database → SQL Editor → New Query → Cole e Execute)
-- ============================================================

-- ── Extensões ────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Perfis de usuários ────────────────────────────────────────
-- Estende auth.users com role e credenciais por usuário
CREATE TABLE IF NOT EXISTS profiles (
    id                   UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    email                TEXT NOT NULL,
    role                 TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    -- Credenciais do usuário (salvas criptografadas via SSL do Supabase)
    google_maps_api_key  TEXT,
    google_client_id     TEXT,
    google_client_secret TEXT,
    google_sheets_creds  JSONB,    -- token OAuth serializado
    app_url              TEXT,     -- URL do app para redirect OAuth
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Pesquisas realizadas ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS searches (
    id            UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    nicho         TEXT,
    subnicho      TEXT,
    cidade        TEXT,
    estado        TEXT,
    localidade    TEXT,
    fonte         TEXT CHECK (fonte IN ('maps', 'receita_federal')),
    total_results INTEGER DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Leads extraídos ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS leads (
    id               UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id          UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    search_id        UUID NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
    nome             TEXT,
    telefone         TEXT,
    telefone2        TEXT,
    email            TEXT,
    endereco         TEXT,
    municipio        TEXT,
    uf               TEXT,
    cep              TEXT,
    site             TEXT,
    maps_url         TEXT,
    avaliacao        REAL,
    total_avaliacoes INTEGER,
    cnpj             TEXT,
    nicho            TEXT,
    subnicho         TEXT,
    fonte            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Índices de performance ────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_searches_user_id  ON searches(user_id);
CREATE INDEX IF NOT EXISTS idx_searches_created  ON searches(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_search_id   ON leads(search_id);
CREATE INDEX IF NOT EXISTS idx_leads_user_id     ON leads(user_id);

-- ── Row Level Security (RLS) ──────────────────────────────────
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE searches ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads    ENABLE ROW LEVEL SECURITY;

-- Usuários veem/editam apenas seu próprio perfil
CREATE POLICY "own_profile" ON profiles
    FOR ALL USING (auth.uid() = id);

-- Admins veem todos os perfis
CREATE POLICY "admin_all_profiles" ON profiles
    FOR ALL USING (
        EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
    );

-- Usuários veem/editam apenas suas próprias pesquisas
CREATE POLICY "own_searches" ON searches
    FOR ALL USING (auth.uid() = user_id);

-- Usuários veem/editam apenas seus próprios leads
CREATE POLICY "own_leads" ON leads
    FOR ALL USING (auth.uid() = user_id);

-- ── Trigger: cria perfil automaticamente ao criar usuário ─────
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    INSERT INTO profiles (id, email, role)
    VALUES (NEW.id, NEW.email, COALESCE(NEW.raw_user_meta_data->>'role', 'user'))
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ── Trigger: atualiza updated_at ──────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS profiles_updated_at ON profiles;
CREATE TRIGGER profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── Créditos por usuário ──────────────────────────────────────
-- Execute este bloco no SQL Editor do Supabase (Database → SQL Editor)
-- se o banco já existia antes desta versão:
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS cdd_credits          INTEGER NOT NULL DEFAULT 0;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS maps_credits         INTEGER NOT NULL DEFAULT 0;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS maps_credits_enabled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS maps_api_key_admin   TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS monthly_cdd_credits  INTEGER NOT NULL DEFAULT 0;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS monthly_maps_credits INTEGER NOT NULL DEFAULT 0;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS credits_renewed_at   DATE;

-- ── View auxiliar para o admin ver usuários com stats ─────────
CREATE OR REPLACE VIEW user_stats AS
SELECT
    p.id,
    p.email,
    p.role,
    p.cdd_credits,
    p.maps_credits,
    p.maps_credits_enabled,
    p.maps_api_key_admin,
    p.monthly_cdd_credits,
    p.monthly_maps_credits,
    p.credits_renewed_at,
    p.created_at,
    COUNT(DISTINCT s.id)  AS total_searches,
    COUNT(DISTINCT l.id)  AS total_leads,
    MAX(s.created_at)     AS last_search_at
FROM profiles p
LEFT JOIN searches s ON s.user_id = p.id
LEFT JOIN leads    l ON l.user_id = p.id
GROUP BY p.id, p.email, p.role, p.cdd_credits, p.maps_credits,
         p.maps_credits_enabled, p.maps_api_key_admin,
         p.monthly_cdd_credits, p.monthly_maps_credits,
         p.credits_renewed_at, p.created_at;

-- Permissão da view para admins
-- (a RLS da tabela profiles já cobre o acesso)

-- ── Função RPC: débito atômico de créditos ────────────────────
-- Garante que o decremento ocorra sem race condition.
-- Executar no SQL Editor do Supabase.
CREATE OR REPLACE FUNCTION decrement_credits(
    p_user_id UUID,
    p_campo   TEXT,
    p_delta   INTEGER
) RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    IF p_campo NOT IN ('cdd_credits', 'maps_credits') THEN
        RAISE EXCEPTION 'Campo inválido: %', p_campo;
    END IF;
    IF p_delta <= 0 THEN
        RETURN;
    END IF;
    EXECUTE format(
        'UPDATE profiles SET %I = GREATEST(0, %I - $1) WHERE id = $2',
        p_campo, p_campo
    ) USING p_delta, p_user_id;
END;
$$;

-- ── Tabela de automações ──────────────────────────────────────
-- Cada registro representa uma busca programada de um usuário.
-- dias_semana: 0=Dom 1=Seg 2=Ter 3=Qua 4=Qui 5=Sex 6=Sáb
CREATE TABLE IF NOT EXISTS automations (
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    nome            TEXT NOT NULL,
    tipo            TEXT NOT NULL CHECK (tipo IN ('maps', 'cnpj')),
    filtros         JSONB NOT NULL DEFAULT '{}',
    sheet_id        TEXT,
    sheet_aba       TEXT DEFAULT 'Leads',
    dias_semana     INTEGER[] NOT NULL DEFAULT ARRAY[1,2,3,4,5],
    horario         TEXT NOT NULL DEFAULT '08:00',
    ativa           BOOLEAN NOT NULL DEFAULT TRUE,
    ultima_execucao TIMESTAMPTZ,
    proxima_execucao TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE automations ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "own_automations"
    ON automations FOR ALL TO authenticated
    USING  (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- ── Tabela de execuções (log de cada vez que uma automação rodou) ──
CREATE TABLE IF NOT EXISTS automation_runs (
    id             UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    automation_id  UUID REFERENCES automations(id) ON DELETE CASCADE NOT NULL,
    user_id        UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    iniciada_em    TIMESTAMPTZ DEFAULT NOW(),
    concluida_em   TIMESTAMPTZ,
    leads_encontrados INTEGER DEFAULT 0,
    status         TEXT CHECK (status IN ('running','success','error','sem_creditos','sem_sheets')),
    erro           TEXT
);

ALTER TABLE automation_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "own_automation_runs"
    ON automation_runs FOR ALL TO authenticated
    USING  (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- ── Instagram / Apify — colunas adicionais ────────────────────
-- Execute no SQL Editor do Supabase se o banco já existia.

-- Créditos Instagram e chave Apify nos perfis
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS instagram_credits         INTEGER NOT NULL DEFAULT 0;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS instagram_credits_enabled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS apify_api_key_admin       TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS monthly_instagram_credits INTEGER NOT NULL DEFAULT 0;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS apify_api_key             TEXT;   -- chave própria do usuário

-- ID numérico do Instagram na tabela de leads
ALTER TABLE leads ADD COLUMN IF NOT EXISTS instagram_id TEXT;

-- Atualizar constraint de fonte das buscas para aceitar 'instagram'
ALTER TABLE searches DROP CONSTRAINT IF EXISTS searches_fonte_check;
ALTER TABLE searches ADD CONSTRAINT searches_fonte_check
    CHECK (fonte IN ('maps', 'receita_federal', 'instagram'));

-- Atualizar view user_stats para incluir campos Instagram
CREATE OR REPLACE VIEW user_stats AS
SELECT
    p.id,
    p.email,
    p.role,
    p.cdd_credits,
    p.maps_credits,
    p.maps_credits_enabled,
    p.maps_api_key_admin,
    p.monthly_cdd_credits,
    p.monthly_maps_credits,
    p.credits_renewed_at,
    p.instagram_credits,
    p.instagram_credits_enabled,
    p.apify_api_key_admin,
    p.monthly_instagram_credits,
    p.created_at,
    COUNT(DISTINCT s.id)  AS total_searches,
    COUNT(DISTINCT l.id)  AS total_leads,
    MAX(s.created_at)     AS last_search_at
FROM profiles p
LEFT JOIN searches s ON s.user_id = p.id
LEFT JOIN leads    l ON l.user_id = p.id
GROUP BY p.id, p.email, p.role, p.cdd_credits, p.maps_credits,
         p.maps_credits_enabled, p.maps_api_key_admin,
         p.monthly_cdd_credits, p.monthly_maps_credits,
         p.credits_renewed_at, p.instagram_credits, p.instagram_credits_enabled,
         p.apify_api_key_admin, p.monthly_instagram_credits, p.created_at;

-- Atualizar função RPC de débito para aceitar 'instagram_credits'
CREATE OR REPLACE FUNCTION decrement_credits(
    p_user_id UUID,
    p_campo   TEXT,
    p_delta   INTEGER
) RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    IF p_campo NOT IN ('cdd_credits', 'maps_credits', 'instagram_credits') THEN
        RAISE EXCEPTION 'Campo inválido: %', p_campo;
    END IF;
    IF p_delta <= 0 THEN
        RETURN;
    END IF;
    EXECUTE format(
        'UPDATE profiles SET %I = GREATEST(0, %I - $1) WHERE id = $2',
        p_campo, p_campo
    ) USING p_delta, p_user_id;
END;
$$;

-- ── Visibilidade do Instagram por usuário ─────────────────────
-- Execute no SQL Editor do Supabase se o banco já existia.
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS instagram_visible BOOLEAN NOT NULL DEFAULT TRUE;

-- ── Pool de chaves Google Maps (rodízio automático) ──────────────
-- Execute no SQL Editor do Supabase se o banco já existia.
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS maps_keys_pool JSONB DEFAULT '[]'::jsonb;

-- ── Pool de chaves Apify (rodízio automático) ─────────────────────
-- Execute no SQL Editor do Supabase se o banco já existia.
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS apify_keys_pool JSONB DEFAULT '[]'::jsonb;

-- ============================================================
-- Ferramenta de Disparo WhatsApp (admin-only)
-- Canal inicial: Evolution API (não-oficial). Deixa espaço pro
-- canal oficial (WhatsApp Business Cloud API) via coluna `canal`.
-- ============================================================

CREATE TABLE IF NOT EXISTS whatsapp_instances (
    id                         UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id                    UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    nome                       TEXT NOT NULL,
    canal                      TEXT NOT NULL DEFAULT 'evolution' CHECK (canal IN ('evolution', 'oficial')),
    evolution_instance_name    TEXT,
    status                     TEXT NOT NULL DEFAULT 'desconectado' CHECK (status IN ('desconectado', 'conectando', 'conectado')),
    numero_conectado           TEXT,
    ultimo_envio_em            TIMESTAMPTZ,
    proximo_envio_liberado_em  TIMESTAMPTZ,
    limite_diario_envios       INTEGER,
    criado_em                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dispatch_campaigns (
    id                UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id           UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    nome              TEXT NOT NULL,
    instance_id       UUID REFERENCES whatsapp_instances(id),
    status            TEXT NOT NULL DEFAULT 'rascunho' CHECK (status IN ('rascunho', 'ativa', 'pausada', 'concluida')),
    tipo_origem       TEXT NOT NULL CHECK (tipo_origem IN ('busca_existente', 'upload', 'auto_trigger', 'sheet_watch')),
    origem_search_id  UUID REFERENCES searches(id),   -- só p/ busca_existente
    filtro_nicho      TEXT,                           -- só p/ auto_trigger
    filtro_subnicho   TEXT,
    filtro_uf         TEXT,
    intervalo_min_seg INTEGER NOT NULL DEFAULT 30,
    intervalo_max_seg INTEGER NOT NULL DEFAULT 90,
    criado_em         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dispatch_cadence_steps (
    id             UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    campaign_id    UUID REFERENCES dispatch_campaigns(id) ON DELETE CASCADE NOT NULL,
    ordem          INTEGER NOT NULL,
    atraso_horas   NUMERIC NOT NULL DEFAULT 0,
    corpo_mensagem TEXT NOT NULL,
    midia_url      TEXT,
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dispatch_targets (
    id                UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    campaign_id       UUID REFERENCES dispatch_campaigns(id) ON DELETE CASCADE NOT NULL,
    nome              TEXT,
    telefone          TEXT NOT NULL,   -- E.164, ex: 5511999999999
    lead_snapshot     JSONB,
    status            TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente', 'enviando', 'enviado', 'concluido', 'falhou', 'removido')),
    current_step_id   UUID REFERENCES dispatch_cadence_steps(id),
    proxima_etapa_em  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reservado_em      TIMESTAMPTZ,
    criado_em         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (campaign_id, telefone)
);
CREATE INDEX IF NOT EXISTS idx_dispatch_targets_scan ON dispatch_targets(campaign_id, status, proxima_etapa_em);
CREATE INDEX IF NOT EXISTS idx_dispatch_targets_tel   ON dispatch_targets(telefone);

CREATE TABLE IF NOT EXISTS dispatch_messages_log (
    id               UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    target_id        UUID REFERENCES dispatch_targets(id) ON DELETE CASCADE NOT NULL,
    campaign_id      UUID REFERENCES dispatch_campaigns(id) ON DELETE CASCADE NOT NULL,
    step_id          UUID REFERENCES dispatch_cadence_steps(id),
    enviado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status           TEXT NOT NULL CHECK (status IN ('sucesso', 'erro')),
    evolution_message_id TEXT,
    erro_msg         TEXT,
    corpo_enviado    TEXT
);

CREATE TABLE IF NOT EXISTS dispatch_sheet_watchers (
    id                       UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    campaign_id              UUID REFERENCES dispatch_campaigns(id) ON DELETE CASCADE NOT NULL,
    sheet_id                 TEXT NOT NULL,
    aba_nome                 TEXT NOT NULL,
    coluna_telefone          TEXT NOT NULL,
    coluna_nome              TEXT,
    ultima_linha_processada  INTEGER NOT NULL DEFAULT 0,
    criado_em                TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Opt-out global: independe de campanha, checado no enrollment de QUALQUER campanha
CREATE TABLE IF NOT EXISTS dispatch_opt_outs (
    telefone   TEXT PRIMARY KEY,
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    motivo     TEXT
);

-- Template reutilizável (corpo + variáveis). Fica pronto pro canal oficial
-- (status_aprovacao) mas sem UI própria até a Fase 3.
CREATE TABLE IF NOT EXISTS message_templates (
    id               UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id          UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    nome             TEXT NOT NULL,
    categoria        TEXT,
    corpo            TEXT NOT NULL,
    variaveis        JSONB DEFAULT '[]'::jsonb,
    canal            TEXT NOT NULL DEFAULT 'evolution' CHECK (canal IN ('evolution', 'oficial')),
    status_aprovacao TEXT NOT NULL DEFAULT 'rascunho',
    criado_em        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Reivindicação atômica de 1 alvo pronto pra envio por instância —
-- evita corrida entre ticks/threads furando o intervalo anti-banimento.
CREATE OR REPLACE FUNCTION claim_dispatch_target(p_instance_id UUID)
RETURNS SETOF dispatch_targets AS $$
    UPDATE dispatch_targets
    SET status = 'enviando', reservado_em = NOW()
    WHERE id = (
        SELECT dt.id FROM dispatch_targets dt
        JOIN dispatch_campaigns dc ON dc.id = dt.campaign_id
        WHERE dc.instance_id = p_instance_id
          AND dc.status = 'ativa'
          AND dt.status = 'pendente'
          AND dt.proxima_etapa_em <= NOW()
        ORDER BY dt.proxima_etapa_em
        LIMIT 1
        FOR UPDATE OF dt SKIP LOCKED
    )
    RETURNING *;
$$ LANGUAGE sql VOLATILE;

-- RLS: só admin (as operações em background usam o cliente service-role,
-- que ignora RLS — isso é defesa em profundidade caso a UI algum dia
-- consulte essas tabelas com o cliente do usuário logado).
ALTER TABLE whatsapp_instances      ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispatch_campaigns      ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispatch_cadence_steps  ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispatch_targets        ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispatch_messages_log   ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispatch_sheet_watchers ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispatch_opt_outs       ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_templates       ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "admin_only_whatsapp_instances" ON whatsapp_instances
    FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));
CREATE POLICY IF NOT EXISTS "admin_only_dispatch_campaigns" ON dispatch_campaigns
    FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));
CREATE POLICY IF NOT EXISTS "admin_only_dispatch_cadence_steps" ON dispatch_cadence_steps
    FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));
CREATE POLICY IF NOT EXISTS "admin_only_dispatch_targets" ON dispatch_targets
    FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));
CREATE POLICY IF NOT EXISTS "admin_only_dispatch_messages_log" ON dispatch_messages_log
    FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));
CREATE POLICY IF NOT EXISTS "admin_only_dispatch_sheet_watchers" ON dispatch_sheet_watchers
    FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));
CREATE POLICY IF NOT EXISTS "admin_only_dispatch_opt_outs" ON dispatch_opt_outs
    FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));
CREATE POLICY IF NOT EXISTS "admin_only_message_templates" ON message_templates
    FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));
