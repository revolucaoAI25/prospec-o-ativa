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
    Isso garante que o RLS seja respeitado.
    """
    if not _OK:
        return None
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_ANON_KEY")
    if not url or not key:
        return None

    user = st.session_state.get("user", {})
    token = user.get("access_token", "")

    sb = create_client(url, key)
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
        })

    try:
        # Insere em lotes de 500 para não exceder limites
        for i in range(0, len(linhas), 500):
            sb.table("leads").insert(linhas[i:i+500]).execute()
        return True
    except Exception:
        return False


def listar_pesquisas(limite: int = 50) -> list[dict]:
    """Retorna pesquisas do usuário logado, mais recentes primeiro."""
    sb = _client_autenticado()
    if not sb:
        return []
    try:
        resp = (sb.table("searches")
                  .select("id, nicho, subnicho, cidade, estado, localidade, fonte, total_results, created_at")
                  .order("created_at", desc=True)
                  .limit(limite)
                  .execute())
        return resp.data or []
    except Exception:
        return []


def buscar_leads_da_pesquisa(search_id: str) -> list[dict]:
    """Retorna todos os leads de uma pesquisa específica."""
    sb = _client_autenticado()
    if not sb:
        return []
    try:
        resp = (sb.table("leads")
                  .select("nome, telefone, telefone2, email, endereco, municipio, uf, cep, site, maps_url, avaliacao, total_avaliacoes, cnpj, nicho, subnicho, fonte")
                  .eq("search_id", search_id)
                  .order("nome")
                  .execute())
        return resp.data or []
    except Exception:
        return []


def deletar_pesquisa(search_id: str) -> tuple[bool, str]:
    """Deleta pesquisa e seus leads (cascade no banco)."""
    sb = _client_autenticado()
    if not sb:
        return False, "Banco não disponível."
    try:
        sb.table("searches").delete().eq("id", search_id).execute()
        return True, "Pesquisa removida."
    except Exception as e:
        return False, str(e)


# ── Configurações do usuário ──────────────────────────────────────────────────

def carregar_configuracoes() -> dict:
    """Carrega configurações do usuário logado."""
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
        return resp.data or {}
    except Exception:
        return {}


def salvar_configuracoes(dados: dict) -> tuple[bool, str]:
    """Atualiza campos de configuração do usuário logado."""
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
        )}
        sb.table("profiles").update(campos).eq("id", user_id).execute()
        return True, "Configurações salvas."
    except Exception as e:
        return False, str(e)
