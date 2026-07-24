"""
Módulo de persistência no Supabase.

Salva e recupera pesquisas, leads e configurações por usuário.
Toda operação respeita o RLS do Supabase — usuários só veem seus dados.
"""

import os
import json
import streamlit as st
from typing import Optional

try:
    from supabase import create_client, Client
    _OK = True
except ImportError:
    _OK = False


def _apenas_digitos(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def _get_secret(key: str) -> str:
    try:
        v = st.secrets.get(key, "")
        if v:
            return str(v).strip()
    except Exception:
        pass
    return os.getenv(key, "").strip()


def _client_autenticado() -> Optional["Client"]:
    """
    Retorna cliente Supabase autenticado com o token do usuário logado.
    O cliente é cacheado por sessão — create_client() é chamado uma única vez.
    """
    if not _OK:
        return None
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_ANON_KEY")
    if not url or not key:
        return None

    user = st.session_state.get("user", {})
    token = user.get("access_token", "")

    # Reutiliza cliente existente se disponível (evita overhead de create_client a cada chamada)
    sb = st.session_state.get("_sb_client")
    if sb is None:
        sb = create_client(url, key)
        st.session_state["_sb_client"] = sb

    if token:
        sb.postgrest.auth(token)
    return sb


# ── Pesquisas ─────────────────────────────────────────────────────────────────

def salvar_pesquisa(
    nicho: str,
    subnicho: str,
    cidade: str,
    estado: str,
    localidade: str,
    fonte: str,
    total_results: int,
) -> Optional[str]:
    """
    Salva uma pesquisa e retorna o search_id (UUID) ou None em caso de erro.
    Usa o user_id da sessão atual.
    """
    sb = _client_autenticado()
    if not sb:
        return None
    user_id = st.session_state.get("user", {}).get("id")
    if not user_id:
        return None
    st.session_state.pop("_pesquisas_cache", None)  # invalida cache ao salvar nova pesquisa
    try:
        resp = sb.table("searches").insert({
            "user_id":       user_id,
            "nicho":         nicho,
            "subnicho":      subnicho,
            "cidade":        cidade,
            "estado":        estado,
            "localidade":    localidade,
            "fonte":         fonte,
            "total_results": total_results,
        }).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception:
        return None


def salvar_leads(search_id: str, resultados: list[dict]) -> bool:
    """Salva lista de leads vinculados a uma pesquisa. Retorna True se OK."""
    if not search_id or not resultados:
        return False
    sb = _client_autenticado()
    if not sb:
        return False
    user_id = st.session_state.get("user", {}).get("id")
    if not user_id:
        return False

    linhas = []
    for r in resultados:
        linhas.append({
            "user_id":          user_id,
            "search_id":        search_id,
            "nome":             str(r.get("nome", "") or ""),
            "telefone":         str(r.get("telefone", "") or ""),
            "telefone2":        str(r.get("telefone2", "") or ""),
            "email":            str(r.get("email", "") or ""),
            "endereco":         str(r.get("endereco", "") or ""),
            "municipio":        str(r.get("municipio", "") or ""),
            "uf":               str(r.get("uf", "") or ""),
            "cep":              str(r.get("cep", "") or ""),
            "site":             str(r.get("site", "") or ""),
            "maps_url":         str(r.get("maps_url", "") or ""),
            "avaliacao":        r.get("avaliacao") or None,
            "total_avaliacoes": r.get("total_avaliacoes") or None,
            "cnpj":             str(r.get("cnpj", "") or ""),
            "nicho":            str(r.get("nicho_busca", "") or ""),
            "subnicho":         str(r.get("subnicho_busca", "") or ""),
            "fonte":            str(r.get("fonte", "") or ""),
            "instagram_id":     str(r.get("instagram_id", "") or ""),
        })

    try:
        # Insere em lotes de 500 para não exceder limites
        for i in range(0, len(linhas), 500):
            sb.table("leads").insert(linhas[i:i+500]).execute()
        return True
    except Exception:
        return False


def listar_pesquisas(limite: int = 300) -> list[dict]:
    """Retorna pesquisas do usuário logado, mais recentes primeiro. Cacheado por sessão."""
    if "_pesquisas_cache" in st.session_state:
        return st.session_state["_pesquisas_cache"]
    sb = _client_autenticado()
    if not sb:
        return []
    try:
        resp = (sb.table("searches")
                  .select("id, nicho, subnicho, cidade, estado, localidade, fonte, total_results, created_at")
                  .order("created_at", desc=True)
                  .limit(limite)
                  .execute())
        result = resp.data or []
        st.session_state["_pesquisas_cache"] = result
        return result
    except Exception:
        return []


def buscar_leads_da_pesquisa(search_id: str) -> list[dict]:
    """
    Retorna todos os leads de uma pesquisa específica.
    Pagina em blocos de 1000 — buscas grandes (o limite de resultados vai
    até 2000) ultrapassam o limite padrão de linhas por requisição do
    Supabase/PostgREST, e sem paginação os leads do Histórico além da
    linha 1000 seriam perdidos na exportação.
    """
    sb = _client_autenticado()
    if not sb:
        return []
    leads: list[dict] = []
    try:
        page_size = 1000
        offset = 0
        while True:
            resp = (sb.table("leads")
                      .select("nome, telefone, telefone2, email, endereco, municipio, uf, cep, site, maps_url, avaliacao, total_avaliacoes, cnpj, nicho, subnicho, fonte")
                      .eq("search_id", search_id)
                      .order("nome")
                      .range(offset, offset + page_size - 1)
                      .execute())
            linhas = resp.data or []
            leads.extend(linhas)
            if len(linhas) < page_size:
                break
            offset += page_size
        return leads
    except Exception:
        return leads


def buscar_identificadores_existentes() -> tuple[set, set]:
    """
    Retorna (set de telefones, set de CNPJs) já salvos pelo usuário.
    Usado para deduplicação: filtra leads repetidos entre pesquisas.
    Telefones são normalizados para dígitos (sem formatação) para que a
    comparação funcione entre fontes diferentes (Google Maps, Casa dos
    Dados, Apify), que retornam o telefone formatado de jeitos distintos.
    Apenas valores não-vazios são incluídos nos sets.

    Pagina a consulta em blocos de 1000 linhas — o Supabase/PostgREST
    limita cada requisição a 1000 linhas por padrão, e sem paginação
    contas com mais de 1000 leads salvos teriam parte do histórico
    silenciosamente ignorada na deduplicação.
    """
    sb = _client_autenticado()
    if not sb:
        return set(), set()
    telefones = set()
    cnpjs = set()
    try:
        page_size = 1000
        offset = 0
        while True:
            resp = (sb.table("leads")
                      .select("telefone, telefone2, cnpj")
                      .range(offset, offset + page_size - 1)
                      .execute())
            linhas = resp.data or []
            for r in linhas:
                for campo in ("telefone", "telefone2"):
                    d = _apenas_digitos(r.get(campo, ""))
                    if d:
                        telefones.add(d)
                if r.get("cnpj"):
                    cnpjs.add(r["cnpj"])
            if len(linhas) < page_size:
                break
            offset += page_size
        return telefones, cnpjs
    except Exception:
        return telefones, cnpjs


def deletar_pesquisa(search_id: str) -> tuple[bool, str]:
    """Deleta pesquisa e seus leads (cascade no banco)."""
    st.session_state.pop("_pesquisas_cache", None)
    sb = _client_autenticado()
    if not sb:
        return False, "Banco não disponível."
    try:
        sb.table("searches").delete().eq("id", search_id).execute()
        return True, "Pesquisa removida."
    except Exception as e:
        return False, str(e)


# ── Créditos ─────────────────────────────────────────────────────────────────

_CREDIT_FIELDS = (
    "cdd_credits, maps_credits, maps_credits_enabled, "
    "maps_api_key_admin, monthly_cdd_credits, monthly_maps_credits, credits_renewed_at, "
    "instagram_credits, instagram_credits_enabled, apify_api_key_admin, monthly_instagram_credits"
)


def obter_perfil_creditos() -> dict:
    """Retorna todos os campos de crédito do usuário logado."""
    sb = _client_autenticado()
    if not sb:
        return {}
    user_id = st.session_state.get("user", {}).get("id")
    if not user_id:
        return {}
    try:
        resp = sb.table("profiles").select(_CREDIT_FIELDS).eq("id", user_id).single().execute()
        return resp.data or {}
    except Exception:
        return {}


def obter_creditos() -> int:
    """Retorna o saldo de créditos CDD do usuário logado."""
    return int(obter_perfil_creditos().get("cdd_credits", 0))


def obter_creditos_maps() -> int:
    """Retorna o saldo de créditos Maps do usuário logado."""
    return int(obter_perfil_creditos().get("maps_credits", 0))


def _debitar_atomico(campo: str, quantidade: int) -> bool:
    """Debita créditos atomicamente via RPC (sem race condition).
    Se o RPC não existir no Supabase, cai no método de fallback."""
    sb = _client_autenticado()
    if not sb:
        return False
    user_id = st.session_state.get("user", {}).get("id")
    if not user_id:
        return False
    try:
        sb.rpc("decrement_credits", {
            "p_user_id": user_id,
            "p_campo":   campo,
            "p_delta":   quantidade,
        }).execute()
        return True
    except Exception:
        # Fallback: método não-atômico caso a função RPC ainda não exista
        try:
            atual = int((sb.table("profiles")
                           .select(campo)
                           .eq("id", user_id)
                           .single()
                           .execute()
                           .data or {}).get(campo, 0))
            novo = max(0, atual - quantidade)
            sb.table("profiles").update({campo: novo}).eq("id", user_id).execute()
            return True
        except Exception:
            return False


def debitar_creditos(quantidade: int) -> bool:
    """Debita créditos CDD do usuário logado."""
    if quantidade <= 0:
        return True
    return _debitar_atomico("cdd_credits", quantidade)


def debitar_creditos_maps(quantidade: int) -> bool:
    """Debita créditos Maps do usuário logado."""
    if quantidade <= 0:
        return True

    return _debitar_atomico("maps_credits", quantidade)


def obter_creditos_instagram() -> int:
    """Retorna o saldo de créditos Instagram do usuário logado."""
    return int(obter_perfil_creditos().get("instagram_credits", 0))


def debitar_creditos_instagram(quantidade: int) -> bool:
    """Debita créditos Instagram do usuário logado."""
    if quantidade <= 0:
        return True
    return _debitar_atomico("instagram_credits", quantidade)


def buscar_instagram_ids_existentes() -> set:
    """
    Retorna set de instagram_ids já salvos pelo usuário.
    Usado para deduplicação em buscas Instagram subsequentes.
    Pagina em blocos de 1000 pelo mesmo motivo de buscar_identificadores_existentes().
    """
    sb = _client_autenticado()
    if not sb:
        return set()
    ids = set()
    try:
        page_size = 1000
        offset = 0
        while True:
            resp = (sb.table("leads")
                      .select("instagram_id")
                      .range(offset, offset + page_size - 1)
                      .execute())
            linhas = resp.data or []
            for r in linhas:
                if r.get("instagram_id"):
                    ids.add(r["instagram_id"])
            if len(linhas) < page_size:
                break
            offset += page_size
        return ids
    except Exception:
        return ids


def renovar_creditos_se_necessario() -> None:
    """
    Verifica se passaram 30 dias desde a última renovação e, se sim, RESETA
    os créditos para o valor mensal configurado (não acumulativo).
    Chamada uma vez por sessão após login.
    """
    from datetime import date, timedelta
    sb = _client_autenticado()
    if not sb:
        return
    user_id = st.session_state.get("user", {}).get("id")
    if not user_id:
        return
    try:
        perfil = obter_perfil_creditos()
        ultimo = perfil.get("credits_renewed_at")
        hoje = date.today()

        # Renova se nunca renovou ou se passaram 30 dias desde a última renovação
        precisa_renovar = (
            not ultimo or
            hoje >= date.fromisoformat(str(ultimo)[:10]) + timedelta(days=30)
        )
        if not precisa_renovar:
            return

        monthly_cdd  = int(perfil.get("monthly_cdd_credits", 0))
        monthly_maps = int(perfil.get("monthly_maps_credits", 0))
        maps_enabled = bool(perfil.get("maps_credits_enabled", False))

        # RESET (não acumula): substitui o saldo pelo valor mensal
        updates: dict = {"credits_renewed_at": hoje.isoformat()}
        if monthly_cdd > 0:
            updates["cdd_credits"] = monthly_cdd
        if maps_enabled and monthly_maps > 0:
            updates["maps_credits"] = monthly_maps

        sb.table("profiles").update(updates).eq("id", user_id).execute()
    except Exception:
        pass


# ── Configurações do usuário ──────────────────────────────────────────────────

def carregar_configuracoes() -> dict:
    """Carrega configurações do usuário logado. Resultado cacheado por sessão."""
    if "_cfg_cache" in st.session_state:
        return st.session_state["_cfg_cache"]
    sb = _client_autenticado()
    if not sb:
        return {}
    user_id = st.session_state.get("user", {}).get("id")
    if not user_id:
        return {}
    try:
        resp = (sb.table("profiles")
                  .select("google_maps_api_key, google_client_id, google_client_secret, google_sheets_creds, app_url")
                  .eq("id", user_id)
                  .single()
                  .execute())
        result = resp.data or {}
        st.session_state["_cfg_cache"] = result
        return result
    except Exception:
        return {}


def salvar_configuracoes(dados: dict) -> tuple[bool, str]:
    """Atualiza campos de configuração do usuário logado."""
    st.session_state.pop("_cfg_cache", None)  # invalida cache ao salvar
    sb = _client_autenticado()
    if not sb:
        return False, "Banco não disponível."
    user_id = st.session_state.get("user", {}).get("id")
    if not user_id:
        return False, "Usuário não autenticado."
    try:
        # Filtra só campos permitidos
        campos = {k: v for k, v in dados.items() if k in (
            "google_maps_api_key", "google_client_id",
            "google_client_secret", "google_sheets_creds", "app_url",
            "apify_api_key",
        )}
        sb.table("profiles").update(campos).eq("id", user_id).execute()
        return True, "Configurações salvas."
    except Exception as e:
        return False, str(e)


# ── Pool de chaves Maps ───────────────────────────────────────────────────────

def obter_pool_maps_usuario() -> list[dict]:
    """Retorna o pool de chaves Maps do usuário logado."""
    sb = _client_autenticado()
    if not sb:
        return []
    user_id = st.session_state.get("user", {}).get("id")
    if not user_id:
        return []
    try:
        resp = sb.table("profiles").select("maps_keys_pool").eq("id", user_id).single().execute()
        return (resp.data or {}).get("maps_keys_pool") or []
    except Exception:
        return []


def salvar_pool_maps_usuario(pool: list[dict]) -> bool:
    """Salva o pool de chaves Maps do usuário logado."""
    sb = _client_autenticado()
    if not sb:
        return False
    user_id = st.session_state.get("user", {}).get("id")
    if not user_id:
        return False
    try:
        sb.table("profiles").update({"maps_keys_pool": pool}).eq("id", user_id).execute()
        return True
    except Exception:
        return False


def selecionar_chave_maps(pool: list[dict]) -> tuple[str, int, list[dict]]:
    """
    Seleciona a primeira chave disponível no mês atual.
    Reseta o contador de chaves de meses anteriores automaticamente.
    Retorna (api_key, index, pool_atualizado) ou ("", -1, pool) se todas esgotadas.
    """
    from datetime import date
    mes = date.today().strftime("%Y-%m")
    pool_copia = [dict(k) for k in pool]
    for i, entry in enumerate(pool_copia):
        if entry.get("month") != mes:
            entry["usage"] = 0
            entry["month"] = mes
        if int(entry.get("usage", 0)) < int(entry.get("limit", 900)):
            return entry.get("key", ""), i, pool_copia
    return "", -1, pool_copia


def registrar_uso_maps(pool: list[dict], key_idx: int, calls: int) -> list[dict]:
    """Incrementa o contador de uso de uma chave no pool."""
    pool_copia = [dict(k) for k in pool]
    if 0 <= key_idx < len(pool_copia):
        pool_copia[key_idx]["usage"] = int(pool_copia[key_idx].get("usage", 0)) + calls
    return pool_copia


def salvar_pool_maps_por_user_id(user_id: str, pool: list[dict]) -> bool:
    """Salva o pool de chaves Maps de um usuário específico (sem depender de session_state)."""
    if not _OK:
        return False
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_SERVICE_ROLE_KEY") or _get_secret("SUPABASE_ANON_KEY")
    if not url or not key:
        return False
    try:
        from supabase import create_client
        sb = create_client(url, key)
        sb.table("profiles").update({"maps_keys_pool": pool}).eq("id", user_id).execute()
        return True
    except Exception:
        return False


# ── Pool de chaves Apify ──────────────────────────────────────────────────────

def obter_pool_apify_usuario() -> list[dict]:
    """Retorna o pool de chaves Apify do usuário logado."""
    sb = _client_autenticado()
    if not sb:
        return []
    user_id = st.session_state.get("user", {}).get("id")
    if not user_id:
        return []
    try:
        resp = sb.table("profiles").select("apify_keys_pool").eq("id", user_id).single().execute()
        return (resp.data or {}).get("apify_keys_pool") or []
    except Exception:
        return []


def selecionar_chave_apify(pool: list[dict]) -> tuple[str, int, list[dict]]:
    """
    Seleciona a primeira chave Apify disponível no mês atual (dentro do limite).
    Reseta o contador de chaves de meses anteriores automaticamente.

    Se TODAS as chaves já estourarem o limite, não bloqueia a busca —
    continua usando a ÚLTIMA chave do pool mesmo acima do limite (overflow
    suave), já que o Apify é cobrado por uso e não corta o acesso como o
    Google Maps. O contador só volta a respeitar o limite quando o mês
    virar e os contadores forem resetados.

    Retorna (api_key, index, pool_atualizado) ou ("", -1, pool) se o pool
    estiver vazio.
    """
    from datetime import date
    if not pool:
        return "", -1, pool
    mes = date.today().strftime("%Y-%m")
    pool_copia = [dict(k) for k in pool]
    for i, entry in enumerate(pool_copia):
        if entry.get("month") != mes:
            entry["usage"] = 0
            entry["month"] = mes
        if int(entry.get("usage", 0)) < int(entry.get("limit", 900)):
            return entry.get("key", ""), i, pool_copia
    # Todas esgotadas — mantém overflow na última chave em vez de bloquear
    ultimo = len(pool_copia) - 1
    return pool_copia[ultimo].get("key", ""), ultimo, pool_copia


def registrar_uso_apify(pool: list[dict], key_idx: int, calls: int) -> list[dict]:
    """Incrementa o contador de uso de uma chave Apify no pool."""
    pool_copia = [dict(k) for k in pool]
    if 0 <= key_idx < len(pool_copia):
        pool_copia[key_idx]["usage"] = int(pool_copia[key_idx].get("usage", 0)) + calls
    return pool_copia


def salvar_pool_apify_usuario(pool: list[dict]) -> bool:
    """Salva o pool de chaves Apify do usuário logado."""
    sb = _client_autenticado()
    if not sb:
        return False
    user_id = st.session_state.get("user", {}).get("id")
    if not user_id:
        return False
    try:
        sb.table("profiles").update({"apify_keys_pool": pool}).eq("id", user_id).execute()
        return True
    except Exception:
        return False
