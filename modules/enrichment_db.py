"""
Persistência do Enriquecimento de Leads via IA — runs (execuções em lote)
e os leads de cada uma.

Funções aqui usam o cliente autenticado do usuário logado (respeitam RLS
— cada usuário só vê suas próprias runs). O worker de background
(modules/enrichment_worker.py) usa client próprio com service role, já
que roda fora de qualquer sessão — mesma separação já usada entre
modules/database.py (client do usuário) e modules/automation_db.py
(client de serviço, usado pelo scheduler).
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _client_autenticado():
    from modules.database import _client_autenticado as _ca
    return _ca()


def criar_run(leads: list[dict], opcoes: dict) -> Optional[str]:
    """Cria uma run + os leads dela (todos 'pendente'). Retorna o id da
    run, ou None se falhar. Não processa nada — só registra; quem chama
    ainda precisa disparar o worker (enrichment_worker.iniciar_execucao)."""
    sb = _client_autenticado()
    if not sb:
        return None
    import streamlit as st
    user_id = st.session_state.get("user", {}).get("id")
    if not user_id:
        return None
    try:
        resp = sb.table("enrichment_runs").insert({
            "user_id": user_id, "status": "pendente",
            "total_leads": len(leads), "processados": 0, "opcoes": opcoes,
        }).execute()
        run_id = resp.data[0]["id"]
    except Exception as e:
        logger.error("criar_run: falha ao criar run: %s", e)
        return None

    try:
        linhas = [
            {
                "run_id": run_id, "user_id": user_id, "ordem": i,
                "nome_lead": (lead.get("nome") or "").strip(),
                "email": (lead.get("email") or "").strip(),
                "telefone": (lead.get("telefone") or "").strip(),
                "status": "pendente",
            }
            for i, lead in enumerate(leads)
        ]
        if linhas:
            sb.table("enrichment_leads").insert(linhas).execute()
    except Exception as e:
        logger.error("criar_run: falha ao criar leads da run %s: %s", run_id, e)
        # A run já existe mas ficou sem leads — marca erro pra não ficar
        # "pendente" pra sempre sem nada pra processar.
        try:
            sb.table("enrichment_runs").update({
                "status": "erro", "erro": f"Falha ao registrar leads: {e}"[:500],
            }).eq("id", run_id).execute()
        except Exception:
            pass
        return None

    return run_id


def listar_runs(limite: int = 20) -> list[dict]:
    sb = _client_autenticado()
    if not sb:
        return []
    try:
        resp = (sb.table("enrichment_runs").select("*")
                  .order("criado_em", desc=True).limit(limite).execute())
        return resp.data or []
    except Exception as e:
        logger.error("listar_runs: %s", e)
        return []


def obter_run(run_id: str) -> Optional[dict]:
    sb = _client_autenticado()
    if not sb:
        return None
    try:
        resp = sb.table("enrichment_runs").select("*").eq("id", run_id).single().execute()
        return resp.data
    except Exception as e:
        logger.error("obter_run: %s", e)
        return None


def listar_leads_da_run(run_id: str) -> list[dict]:
    sb = _client_autenticado()
    if not sb:
        return []
    try:
        resp = (sb.table("enrichment_leads").select("*")
                  .eq("run_id", run_id).order("ordem").execute())
        return resp.data or []
    except Exception as e:
        logger.error("listar_leads_da_run: %s", e)
        return []
