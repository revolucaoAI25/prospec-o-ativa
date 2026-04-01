"""
CRUD de automações — usa service role key para operar sem sessão de usuário.
Permite que o scheduler de background leia e execute automações de qualquer usuário.
"""

from __future__ import annotations
import os
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
    _OK = True
except ImportError:
    _OK = False


def _sb() -> Optional["Client"]:
    """Cliente Supabase com service role — sem dependência de session_state."""
    if not _OK:
        return None
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        # Fallback: tenta st.secrets (para dev local)
        try:
            import streamlit as st
            url = url or st.secrets.get("SUPABASE_URL", "")
            key = key or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
        except Exception:
            pass
    if not url or not key:
        return None
    return create_client(url, key)


# ── CRUD de automações ────────────────────────────────────────────────────────

def listar_automacoes_usuario(user_id: str) -> list[dict]:
    sb = _sb()
    if not sb:
        return []
    try:
        resp = (sb.table("automations")
                  .select("*")
                  .eq("user_id", user_id)
                  .order("created_at", desc=True)
                  .execute())
        return resp.data or []
    except Exception as e:
        logger.error("listar_automacoes_usuario: %s", e)
        return []


def criar_automacao(
    user_id: str,
    nome: str,
    tipo: str,
    filtros: dict,
    sheet_id: str,
    sheet_aba: str,
    dias_semana: list[int],
    horario: str,
    proxima_execucao: Optional[datetime] = None,
) -> Optional[str]:
    """Cria automação e retorna o ID gerado."""
    sb = _sb()
    if not sb:
        return None
    try:
        payload: dict = {
            "user_id":          user_id,
            "nome":             nome,
            "tipo":             tipo,
            "filtros":          filtros,
            "sheet_id":         sheet_id or None,
            "sheet_aba":        sheet_aba or "Leads",
            "dias_semana":      dias_semana,
            "horario":          horario,
            "ativa":            True,
        }
        if proxima_execucao:
            payload["proxima_execucao"] = proxima_execucao.isoformat()
        resp = sb.table("automations").insert(payload).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception as e:
        logger.error("criar_automacao: %s", e)
        return None


def atualizar_automacao(auto_id: str, **campos) -> bool:
    sb = _sb()
    if not sb:
        return False
    try:
        # Converte datetimes para ISO string
        for k, v in campos.items():
            if isinstance(v, datetime):
                campos[k] = v.isoformat()
        sb.table("automations").update(campos).eq("id", auto_id).execute()
        return True
    except Exception as e:
        logger.error("atualizar_automacao: %s", e)
        return False


def deletar_automacao(auto_id: str) -> bool:
    sb = _sb()
    if not sb:
        return False
    try:
        sb.table("automations").delete().eq("id", auto_id).execute()
        return True
    except Exception as e:
        logger.error("deletar_automacao: %s", e)
        return False


def obter_automacoes_vencidas() -> list[dict]:
    """Retorna automações ativas com proxima_execucao <= agora (UTC)."""
    sb = _sb()
    if not sb:
        return []
    try:
        agora_iso = datetime.now(timezone.utc).isoformat()
        resp = (sb.table("automations")
                  .select("*, profiles(google_maps_api_key, maps_api_key_admin, maps_credits_enabled, cdd_credits, maps_credits, google_sheets_creds)")
                  .eq("ativa", True)
                  .lte("proxima_execucao", agora_iso)
                  .is_("proxima_execucao", "not.null")
                  .execute())
        return resp.data or []
    except Exception as e:
        logger.error("obter_automacoes_vencidas: %s", e)
        return []


# ── Log de execuções ──────────────────────────────────────────────────────────

def registrar_execucao(
    auto_id: str,
    user_id: str,
    status: str,
    leads: int = 0,
    erro: str = "",
) -> bool:
    sb = _sb()
    if not sb:
        return False
    try:
        agora = datetime.now(timezone.utc).isoformat()
        sb.table("automation_runs").insert({
            "automation_id":     auto_id,
            "user_id":           user_id,
            "concluida_em":      agora,
            "leads_encontrados": leads,
            "status":            status,
            "erro":              erro or None,
        }).execute()
        return True
    except Exception as e:
        logger.error("registrar_execucao: %s", e)
        return False


def obter_ultimas_execucoes(auto_id: str, limit: int = 5) -> list[dict]:
    sb = _sb()
    if not sb:
        return []
    try:
        resp = (sb.table("automation_runs")
                  .select("*")
                  .eq("automation_id", auto_id)
                  .order("iniciada_em", desc=True)
                  .limit(limit)
                  .execute())
        return resp.data or []
    except Exception as e:
        logger.error("obter_ultimas_execucoes: %s", e)
        return []


# ── Deduplicação ──────────────────────────────────────────────────────────────

def get_telefones_usuario(user_id: str) -> set:
    """Retorna set de telefones já salvos para o usuário (deduplicação)."""
    sb = _sb()
    if not sb:
        return set()
    try:
        resp = (sb.table("leads")
                  .select("telefone, telefone2")
                  .eq("user_id", user_id)
                  .execute())
        tels = set()
        for r in (resp.data or []):
            if r.get("telefone"):
                tels.add(r["telefone"])
            if r.get("telefone2"):
                tels.add(r["telefone2"])
        return tels
    except Exception as e:
        logger.error("get_telefones_usuario: %s", e)
        return set()


def get_cnpjs_usuario(user_id: str) -> set:
    """Retorna set de CNPJs já salvos para o usuário (deduplicação)."""
    sb = _sb()
    if not sb:
        return set()
    try:
        resp = (sb.table("leads")
                  .select("cnpj")
                  .eq("user_id", user_id)
                  .not_.is_("cnpj", "null")
                  .execute())
        return {r["cnpj"] for r in (resp.data or []) if r.get("cnpj")}
    except Exception as e:
        logger.error("get_cnpjs_usuario: %s", e)
        return set()


# ── Persistência de pesquisa + leads (via service role) ───────────────────────

def salvar_pesquisa_scheduler(
    user_id: str,
    nicho: str,
    subnicho: str,
    cidade: str,
    estado: str,
    localidade: str,
    fonte: str,
    total: int,
) -> Optional[str]:
    sb = _sb()
    if not sb:
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
            "total_results": total,
        }).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception as e:
        logger.error("salvar_pesquisa_scheduler: %s", e)
        return None


def salvar_leads_scheduler(search_id: str, user_id: str, leads: list[dict]) -> bool:
    if not search_id or not leads:
        return False
    sb = _sb()
    if not sb:
        return False
    try:
        rows = [{**lead, "search_id": search_id, "user_id": user_id} for lead in leads]
        # Insere em lotes de 500 para evitar timeout
        for i in range(0, len(rows), 500):
            sb.table("leads").insert(rows[i:i+500]).execute()
        return True
    except Exception as e:
        logger.error("salvar_leads_scheduler: %s", e)
        return False


def debit_credits_scheduler(user_id: str, quantidade: int, tipo: str = "cdd") -> bool:
    """Débito atômico via RPC — seguro para chamadas concorrentes."""
    if quantidade <= 0:
        return True
    campo = "cdd_credits" if tipo == "cdd" else "maps_credits"
    sb = _sb()
    if not sb:
        return False
    try:
        sb.rpc("decrement_credits", {
            "p_user_id": user_id,
            "p_campo":   campo,
            "p_delta":   quantidade,
        }).execute()
        return True
    except Exception:
        # Fallback não-atômico
        try:
            resp = sb.table("profiles").select(campo).eq("id", user_id).single().execute()
            saldo = int((resp.data or {}).get(campo, 0))
            novo = max(0, saldo - quantidade)
            sb.table("profiles").update({campo: novo}).eq("id", user_id).execute()
            return True
        except Exception as e:
            logger.error("debit_credits_scheduler: %s", e)
            return False


def get_perfil_usuario(user_id: str) -> dict:
    """Retorna perfil completo do usuário (para o scheduler)."""
    sb = _sb()
    if not sb:
        return {}
    try:
        resp = sb.table("profiles").select("*").eq("id", user_id).single().execute()
        return resp.data or {}
    except Exception as e:
        logger.error("get_perfil_usuario: %s", e)
        return {}
