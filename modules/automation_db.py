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
    dispatch_campaign_id: Optional[str] = None,
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
        # Só inclui a coluna quando de fato usada — evita que a criação de
        # automações comuns quebre em bancos onde a migração da coluna
        # dispatch_campaign_id ainda não foi rodada.
        if dispatch_campaign_id:
            payload["dispatch_campaign_id"] = dispatch_campaign_id
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


def obter_automacao_por_campanha(campaign_id: str) -> Optional[dict]:
    """Acha a automação de busca (se houver) vinculada a essa campanha de disparo — usado em Relatórios."""
    sb = _sb()
    if not sb:
        return None
    try:
        resp = (sb.table("automations").select("id, nome")
                  .eq("dispatch_campaign_id", campaign_id).limit(1).execute())
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception as e:
        logger.error("obter_automacao_por_campanha: %s", e)
        return None


def obter_automacoes_vencidas() -> list[dict]:
    """Retorna automações ativas com proxima_execucao <= agora (UTC)."""
    sb = _sb()
    if not sb:
        return []
    try:
        agora_iso = datetime.now(timezone.utc).isoformat()
        resp = (sb.table("automations")
                  .select("*")
                  .eq("ativa", True)
                  .lte("proxima_execucao", agora_iso)
                  .not_.is_("proxima_execucao", "null")
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

def _apenas_digitos(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def get_telefones_usuario(user_id: str) -> set:
    """
    Retorna set de telefones (normalizados para dígitos) já salvos para o
    usuário (deduplicação). Pagina em blocos de 1000 — o Supabase/PostgREST
    limita cada requisição, e sem paginação usuários com mais de 1000 leads
    salvos teriam parte do histórico ignorada na deduplicação.
    """
    sb = _sb()
    if not sb:
        return set()
    tels = set()
    try:
        page_size = 1000
        offset = 0
        while True:
            resp = (sb.table("leads")
                      .select("telefone, telefone2")
                      .eq("user_id", user_id)
                      .range(offset, offset + page_size - 1)
                      .execute())
            linhas = resp.data or []
            for r in linhas:
                d1 = _apenas_digitos(r.get("telefone", ""))
                d2 = _apenas_digitos(r.get("telefone2", ""))
                if d1:
                    tels.add(d1)
                if d2:
                    tels.add(d2)
            if len(linhas) < page_size:
                break
            offset += page_size
        return tels
    except Exception as e:
        logger.error("get_telefones_usuario: %s", e)
        return tels


def get_cnpjs_usuario(user_id: str) -> set:
    """Retorna set de CNPJs já salvos para o usuário (deduplicação). Pagina em
    blocos de 1000 pelo mesmo motivo de get_telefones_usuario()."""
    sb = _sb()
    if not sb:
        return set()
    cnpjs = set()
    try:
        page_size = 1000
        offset = 0
        while True:
            resp = (sb.table("leads")
                      .select("cnpj")
                      .eq("user_id", user_id)
                      .not_.is_("cnpj", "null")
                      .range(offset, offset + page_size - 1)
                      .execute())
            linhas = resp.data or []
            for r in linhas:
                if r.get("cnpj"):
                    cnpjs.add(r["cnpj"])
            if len(linhas) < page_size:
                break
            offset += page_size
        return cnpjs
    except Exception as e:
        logger.error("get_cnpjs_usuario: %s", e)
        return cnpjs


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
    """
    Salva os leads encontrados por uma automação. Monta as colunas na mão
    (mesma whitelist de salvar_leads() em modules/database.py) em vez de
    espalhar o dict inteiro do resultado — a busca CNPJ retorna campos como
    cnae_codigo/capital_social/matriz_filial que NÃO existem na tabela
    leads, e um INSERT com uma coluna inexistente falha o lote inteiro
    (antes isso derrubava a automação inteira sem salvar nada, retornando
    False silenciosamente pro chamador).
    """
    if not search_id or not leads:
        return False
    sb = _sb()
    if not sb:
        return False
    try:
        rows = [{
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
        } for r in leads]
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
