"""
Worker de background pro Enriquecimento de Leads via IA — mesmo padrão já
usado pelas Automações (modules/scheduler.py + modules/automation_db.py):
thread daemon, independente de st.session_state, fala com o Supabase via
service role.

Diferença: aqui não é um scheduler recorrente (não fica checando o que
"venceu"), é disparo sob demanda — quando o usuário clica em "Enriquecer"
no app, uma run é criada no banco (ver modules/enrichment_db.py) e uma
thread é disparada NA HORA pra processá-la.

Isso desacopla a busca (que pode levar minutos ou até horas pra um lote
grande, já que cada lead é uma chamada paga à IA com busca na web) da
sessão do navegador: fechar a aba ou cair a conexão não perde nada,
porque cada lead processado já fica salvo no banco assim que termina —
não só no fim do lote inteiro, como era na versão síncrona anterior.
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
    _OK = True
except ImportError:
    _OK = False


def _sb() -> Optional["Client"]:
    """Cliente Supabase com service role — sem dependência de session_state.
    Mesmo padrão de modules/automation_db.py, usado pelo scheduler."""
    if not _OK:
        return None
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        try:
            import streamlit as st
            url = url or st.secrets.get("SUPABASE_URL", "")
            key = key or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
        except Exception:
            pass
    if not url or not key:
        return None
    return create_client(url, key)


_CAMPOS_RESULTADO = (
    "status", "metodo_encontrado", "empresa_nome", "cnpj", "municipio", "uf",
    "website", "cargo", "linkedin_url", "resumo", "socios", "fundacao",
    "processos_jusbrasil", "extras", "erro",
)


def iniciar_execucao(run_id: str) -> None:
    """Dispara o processamento de uma run em background. Não bloqueia —
    volta na hora, a run continua processando na thread."""
    t = threading.Thread(
        target=_processar_run_com_guard, args=(run_id,),
        daemon=True, name=f"EnrichRun-{run_id[:8]}",
    )
    t.start()


def _processar_run_com_guard(run_id: str) -> None:
    try:
        _processar_run(run_id)
    except Exception as e:
        logger.exception("enrichment_worker: erro fatal processando run %s", run_id)
        sb = _sb()
        if sb:
            try:
                sb.table("enrichment_runs").update({
                    "status": "erro", "erro": str(e)[:500],
                    "atualizado_em": datetime.now(timezone.utc).isoformat(),
                }).eq("id", run_id).execute()
            except Exception:
                pass


def _processar_run(run_id: str) -> None:
    from modules import lead_enrichment_ia as enriq

    sb = _sb()
    if not sb:
        logger.error("enrichment_worker: sem client de service role — run %s não processada", run_id)
        return

    run_resp = sb.table("enrichment_runs").select("*").eq("id", run_id).single().execute()
    run = run_resp.data
    if not run:
        logger.error("enrichment_worker: run %s não encontrada", run_id)
        return

    perfil_resp = (sb.table("profiles").select("openai_api_key")
                     .eq("id", run["user_id"]).single().execute())
    openai_key = (perfil_resp.data or {}).get("openai_api_key") or ""

    sb.table("enrichment_runs").update({
        "status": "processando",
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
    }).eq("id", run_id).execute()

    leads = (sb.table("enrichment_leads").select("*")
               .eq("run_id", run_id).order("ordem").execute()).data or []

    opcoes = run.get("opcoes") or {}
    processados = 0

    for lead in leads:
        sb.table("enrichment_leads").update({"status": "processando"}).eq("id", lead["id"]).execute()

        if not openai_key:
            resultado = {
                "status": "erro",
                "erro": "Chave da OpenAI não configurada — cadastre em Configurações.",
            }
        else:
            try:
                resultado = enriq.enriquecer_lead(
                    lead.get("nome_lead") or "", lead.get("email") or "", lead.get("telefone") or "",
                    openai_key,
                    nivel_raciocinio=opcoes.get("nivel_raciocinio", enriq.NIVEL_PADRAO),
                    buscar_socios=opcoes.get("buscar_socios", True),
                    buscar_fundacao=opcoes.get("buscar_fundacao", True),
                    buscar_processos=opcoes.get("buscar_processos", True),
                    campos_customizados=opcoes.get("campos_customizados") or [],
                )
            except Exception as e:
                logger.warning("enrichment_worker: lead %s falhou: %s", lead["id"], e)
                resultado = {"status": "erro", "erro": str(e)[:500]}

        atualizacao = {k: resultado.get(k) for k in _CAMPOS_RESULTADO}
        atualizacao["concluido_em"] = datetime.now(timezone.utc).isoformat()
        sb.table("enrichment_leads").update(atualizacao).eq("id", lead["id"]).execute()

        processados += 1
        sb.table("enrichment_runs").update({
            "processados": processados,
            "atualizado_em": datetime.now(timezone.utc).isoformat(),
        }).eq("id", run_id).execute()

    sb.table("enrichment_runs").update({
        "status": "concluido",
        "concluido_em": datetime.now(timezone.utc).isoformat(),
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
    }).eq("id", run_id).execute()
