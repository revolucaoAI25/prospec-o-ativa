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

-- ── View auxiliar para o admin ver usuários com stats ─────────
CREATE OR REPLACE VIEW user_stats AS
SELECT
    p.id,
    p.email,
    p.role,
    p.created_at,
    COUNT(DISTINCT s.id)  AS total_searches,
    COUNT(DISTINCT l.id)  AS total_leads,
    MAX(s.created_at)     AS last_search_at
FROM profiles p
LEFT JOIN searches s ON s.user_id = p.id
LEFT JOIN leads    l ON l.user_id = p.id
GROUP BY p.id, p.email, p.role, p.created_at;

-- Permissão da view para admins
-- (a RLS da tabela profiles já cobre o acesso)
