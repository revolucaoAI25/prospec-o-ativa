"""
CRUD da ferramenta de disparo WhatsApp — usa service role key, mesmo padrão
de modules/automation_db.py, pra funcionar tanto na UI (admin logado)
quanto no scheduler de background (sem sessão Streamlit).
"""

from __future__ import annotations
import os
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from modules.phone_utils import normalizar_e164

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
        try:
            import streamlit as st
            url = url or st.secrets.get("SUPABASE_URL", "")
            key = key or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
        except Exception:
            pass
    if not url or not key:
        return None
    return create_client(url, key)


# ── Instâncias WhatsApp ─────────────────────────────────────────────────────

def criar_instancia(user_id: str, nome: str, evolution_instance_name: str) -> Optional[str]:
    sb = _sb()
    if not sb:
        return None
    try:
        resp = sb.table("whatsapp_instances").insert({
            "user_id": user_id,
            "nome": nome,
            "canal": "evolution",
            "evolution_instance_name": evolution_instance_name,
            "status": "conectando",
        }).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception as e:
        logger.error("criar_instancia: %s", e)
        return None


def criar_instancia_oficial(
    user_id: str, nome: str, token: str, phone_number_id: str, waba_id: str = "",
    numero_conectado: str = "",
) -> Optional[str]:
    """Provisiona uma instância do canal oficial pra um cliente — chamado
    pelo admin ao atender uma solicitação (o cliente nunca vê o token)."""
    sb = _sb()
    if not sb:
        return None
    try:
        resp = sb.table("whatsapp_instances").insert({
            "user_id": user_id,
            "nome": nome,
            "canal": "oficial",
            "token_oficial": token,
            "phone_number_id": phone_number_id,
            "waba_id": waba_id or None,
            "numero_conectado": numero_conectado or None,
            "status": "conectado",
        }).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception as e:
        logger.error("criar_instancia_oficial: %s", e)
        return None


def atualizar_instancia(instance_id: str, **campos) -> bool:
    sb = _sb()
    if not sb:
        return False
    try:
        sb.table("whatsapp_instances").update(campos).eq("id", instance_id).execute()
        return True
    except Exception as e:
        logger.error("atualizar_instancia: %s", e)
        return False


def listar_instancias(user_id: str) -> list[dict]:
    sb = _sb()
    if not sb:
        return []
    try:
        resp = (sb.table("whatsapp_instances")
                  .select("*").eq("user_id", user_id)
                  .order("criado_em", desc=True).execute())
        return resp.data or []
    except Exception as e:
        logger.error("listar_instancias: %s", e)
        return []


def obter_instancia(instance_id: str) -> Optional[dict]:
    sb = _sb()
    if not sb:
        return None
    try:
        resp = sb.table("whatsapp_instances").select("*").eq("id", instance_id).single().execute()
        return resp.data
    except Exception:
        return None


def listar_instancias_conectadas() -> list[dict]:
    """Todas as instâncias conectadas de todos os admins — usado pelo scheduler."""
    sb = _sb()
    if not sb:
        return []
    try:
        resp = sb.table("whatsapp_instances").select("*").eq("status", "conectado").execute()
        return resp.data or []
    except Exception as e:
        logger.error("listar_instancias_conectadas: %s", e)
        return []


def deletar_instancia(instance_id: str) -> bool:
    sb = _sb()
    if not sb:
        return False
    try:
        sb.table("whatsapp_instances").delete().eq("id", instance_id).execute()
        return True
    except Exception as e:
        logger.error("deletar_instancia: %s", e)
        return False


# ── Solicitações de conexão do canal oficial ──────────────────────────────
# Cliente não configura token/phone_number_id ele mesmo — só pede, e o admin
# provisiona manualmente (canal oficial é gerenciado pela conta DatafyAPI
# do próprio admin, por enquanto).

def criar_solicitacao_oficial(user_id: str, nome_desejado: str = "", telefone_contato: str = "") -> Optional[str]:
    sb = _sb()
    if not sb:
        return None
    try:
        resp = sb.table("oficial_connection_requests").insert({
            "user_id": user_id,
            "nome_desejado": nome_desejado or None,
            "telefone_contato": telefone_contato or None,
        }).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception as e:
        logger.error("criar_solicitacao_oficial: %s", e)
        return None


def listar_solicitacoes_oficial(status: Optional[str] = None) -> list[dict]:
    """Todas as solicitações (qualquer usuário) — usado pelo painel do admin."""
    sb = _sb()
    if not sb:
        return []
    try:
        q = sb.table("oficial_connection_requests").select("*").order("criado_em", desc=True)
        if status:
            q = q.eq("status", status)
        resp = q.execute()
        return resp.data or []
    except Exception as e:
        logger.error("listar_solicitacoes_oficial: %s", e)
        return []


def listar_solicitacoes_oficial_usuario(user_id: str) -> list[dict]:
    sb = _sb()
    if not sb:
        return []
    try:
        resp = (sb.table("oficial_connection_requests").select("*")
                  .eq("user_id", user_id).order("criado_em", desc=True).execute())
        return resp.data or []
    except Exception as e:
        logger.error("listar_solicitacoes_oficial_usuario: %s", e)
        return []


def atualizar_solicitacao_oficial(req_id: str, **campos) -> bool:
    sb = _sb()
    if not sb:
        return False
    try:
        campos["atualizado_em"] = datetime.now(timezone.utc).isoformat()
        sb.table("oficial_connection_requests").update(campos).eq("id", req_id).execute()
        return True
    except Exception as e:
        logger.error("atualizar_solicitacao_oficial: %s", e)
        return False


def deletar_solicitacao_oficial(req_id: str) -> bool:
    sb = _sb()
    if not sb:
        return False
    try:
        sb.table("oficial_connection_requests").delete().eq("id", req_id).execute()
        return True
    except Exception as e:
        logger.error("deletar_solicitacao_oficial: %s", e)
        return False


# ── Campanhas ────────────────────────────────────────────────────────────────

def criar_campanha(
    user_id: str, nome: str, instance_id: str, tipo_origem: str,
    origem_search_id: Optional[str] = None,
    filtro_nicho: str = "", filtro_subnicho: str = "", filtro_uf: str = "",
    intervalo_min_seg: int = 30, intervalo_max_seg: int = 90,
) -> Optional[str]:
    sb = _sb()
    if not sb:
        return None
    try:
        resp = sb.table("dispatch_campaigns").insert({
            "user_id": user_id,
            "nome": nome,
            "instance_id": instance_id,
            "tipo_origem": tipo_origem,
            "origem_search_id": origem_search_id,
            "filtro_nicho": filtro_nicho or None,
            "filtro_subnicho": filtro_subnicho or None,
            "filtro_uf": filtro_uf or None,
            "intervalo_min_seg": intervalo_min_seg,
            "intervalo_max_seg": intervalo_max_seg,
        }).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception as e:
        logger.error("criar_campanha: %s", e)
        return None


def atualizar_campanha(campaign_id: str, **campos) -> bool:
    sb = _sb()
    if not sb:
        return False
    try:
        sb.table("dispatch_campaigns").update(campos).eq("id", campaign_id).execute()
        return True
    except Exception as e:
        logger.error("atualizar_campanha: %s", e)
        return False


def listar_campanhas(user_id: str) -> list[dict]:
    sb = _sb()
    if not sb:
        return []
    try:
        resp = (sb.table("dispatch_campaigns")
                  .select("*").eq("user_id", user_id)
                  .order("criado_em", desc=True).execute())
        return resp.data or []
    except Exception as e:
        logger.error("listar_campanhas: %s", e)
        return []


def obter_campanha(campaign_id: str) -> Optional[dict]:
    sb = _sb()
    if not sb:
        return None
    try:
        resp = sb.table("dispatch_campaigns").select("*").eq("id", campaign_id).single().execute()
        return resp.data
    except Exception:
        return None


def listar_campanhas_ativas() -> list[dict]:
    sb = _sb()
    if not sb:
        return []
    try:
        resp = sb.table("dispatch_campaigns").select("*").eq("status", "ativa").execute()
        return resp.data or []
    except Exception as e:
        logger.error("listar_campanhas_ativas: %s", e)
        return []


def deletar_campanha(campaign_id: str) -> bool:
    sb = _sb()
    if not sb:
        return False
    try:
        sb.table("dispatch_campaigns").delete().eq("id", campaign_id).execute()
        return True
    except Exception as e:
        logger.error("deletar_campanha: %s", e)
        return False


# ── Monitoramento de Planilha Google (sheet_watch) ────────────────────────────

def criar_sheet_watcher(
    campaign_id: str, sheet_id: str, aba_nome: str,
    coluna_telefone: str, coluna_nome: str = "", ultima_linha_processada: int = 0,
) -> Optional[str]:
    sb = _sb()
    if not sb:
        return None
    try:
        resp = sb.table("dispatch_sheet_watchers").insert({
            "campaign_id": campaign_id,
            "sheet_id": sheet_id,
            "aba_nome": aba_nome,
            "coluna_telefone": coluna_telefone,
            "coluna_nome": coluna_nome or None,
            "ultima_linha_processada": ultima_linha_processada,
        }).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception as e:
        logger.error("criar_sheet_watcher: %s", e)
        return None


def obter_sheet_watcher(campaign_id: str) -> Optional[dict]:
    sb = _sb()
    if not sb:
        return None
    try:
        resp = (sb.table("dispatch_sheet_watchers")
                  .select("*").eq("campaign_id", campaign_id).limit(1).execute())
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception as e:
        logger.error("obter_sheet_watcher: %s", e)
        return None


def atualizar_sheet_watcher(watcher_id: str, **campos) -> bool:
    sb = _sb()
    if not sb:
        return False
    try:
        sb.table("dispatch_sheet_watchers").update(campos).eq("id", watcher_id).execute()
        return True
    except Exception as e:
        logger.error("atualizar_sheet_watcher: %s", e)
        return False


def listar_campanhas_sheet_watch_ativas() -> list[dict]:
    """Campanhas ativas com origem sheet_watch — usado pelo scan lento do scheduler."""
    sb = _sb()
    if not sb:
        return []
    try:
        resp = (sb.table("dispatch_campaigns")
                  .select("*").eq("status", "ativa").eq("tipo_origem", "sheet_watch").execute())
        return resp.data or []
    except Exception as e:
        logger.error("listar_campanhas_sheet_watch_ativas: %s", e)
        return []


# ── Gatilho por filtro (auto_trigger) ─────────────────────────────────────────

def listar_campanhas_auto_trigger_ativas() -> list[dict]:
    """Campanhas ativas com origem auto_trigger — usado pelo scan lento do scheduler."""
    sb = _sb()
    if not sb:
        return []
    try:
        resp = (sb.table("dispatch_campaigns")
                  .select("*").eq("status", "ativa").eq("tipo_origem", "auto_trigger").execute())
        return resp.data or []
    except Exception as e:
        logger.error("listar_campanhas_auto_trigger_ativas: %s", e)
        return []


def buscar_leads_filtro(
    user_id: str, nicho: str = "", subnicho: str = "", uf: str = "", desde: Optional[str] = None,
) -> list[dict]:
    """
    Busca leads do próprio `user_id` que batem com nicho/subnicho/uf (case-
    insensitive, substring), extraídos depois de `desde` (ISO timestamp).
    Usado pela campanha de disparo com gatilho por filtro — escopo
    intencionalmente restrito às extrações do próprio dono da campanha.
    Pagina em blocos de 1000 (limite do PostgREST).
    """
    sb = _sb()
    if not sb:
        return []
    try:
        leads: list[dict] = []
        page_size = 1000
        offset = 0
        while True:
            q = (sb.table("leads")
                   .select("nome, telefone, telefone2, email, endereco, municipio, uf, cep, "
                           "site, maps_url, avaliacao, total_avaliacoes, cnpj, nicho, subnicho, "
                           "fonte, created_at")
                   .eq("user_id", user_id))
            if nicho:
                q = q.ilike("nicho", f"%{nicho}%")
            if subnicho:
                q = q.ilike("subnicho", f"%{subnicho}%")
            if uf:
                q = q.eq("uf", uf.upper())
            if desde:
                q = q.gt("created_at", desde)
            resp = q.order("created_at").range(offset, offset + page_size - 1).execute()
            linhas = resp.data or []
            leads.extend(linhas)
            if len(linhas) < page_size:
                break
            offset += page_size
        return leads
    except Exception as e:
        logger.error("buscar_leads_filtro: %s", e)
        return []


# ── Etapas da cadência ────────────────────────────────────────────────────────

def criar_etapa(campaign_id: str, ordem: int, atraso_horas: float, corpo_mensagem: str, midia_url: str = "") -> Optional[str]:
    sb = _sb()
    if not sb:
        return None
    try:
        resp = sb.table("dispatch_cadence_steps").insert({
            "campaign_id": campaign_id,
            "ordem": ordem,
            "atraso_horas": atraso_horas,
            "corpo_mensagem": corpo_mensagem,
            "midia_url": midia_url or None,
        }).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception as e:
        logger.error("criar_etapa: %s", e)
        return None


def listar_etapas(campaign_id: str) -> list[dict]:
    sb = _sb()
    if not sb:
        return []
    try:
        resp = (sb.table("dispatch_cadence_steps")
                  .select("*").eq("campaign_id", campaign_id)
                  .order("ordem").execute())
        return resp.data or []
    except Exception as e:
        logger.error("listar_etapas: %s", e)
        return []


def deletar_etapa(step_id: str) -> bool:
    sb = _sb()
    if not sb:
        return False
    try:
        sb.table("dispatch_cadence_steps").delete().eq("id", step_id).execute()
        return True
    except Exception as e:
        logger.error("deletar_etapa: %s", e)
        return False


def proxima_etapa(campaign_id: str, current_step_ordem: int) -> Optional[dict]:
    """Retorna a próxima etapa da cadência após `current_step_ordem` (0 = ainda não enviou nenhuma)."""
    etapas = listar_etapas(campaign_id)
    for e in etapas:
        if e["ordem"] > current_step_ordem:
            return e
    return None


# ── Opt-out ────────────────────────────────────────────────────────────────
# Escopado por user_id — opt-out é por cliente, não global. Sem isso, um
# opt-out do cliente A bloquearia silenciosamente disparos do cliente B
# pro mesmo número (relevante agora que Disparos deixou de ser admin-only).

def esta_opt_out(telefone: str, user_id: str) -> bool:
    sb = _sb()
    if not sb:
        return False
    try:
        resp = (sb.table("dispatch_opt_outs").select("telefone")
                  .eq("telefone", telefone).eq("user_id", user_id).limit(1).execute())
        return bool(resp.data)
    except Exception:
        return False


def registrar_opt_out(telefone: str, user_id: str, motivo: str = "") -> bool:
    sb = _sb()
    if not sb:
        return False
    try:
        sb.table("dispatch_opt_outs").upsert(
            {"telefone": telefone, "user_id": user_id, "motivo": motivo or None},
            on_conflict="telefone,user_id",
        ).execute()
        return True
    except Exception as e:
        logger.error("registrar_opt_out: %s", e)
        return False


# ── Alvos (targets) ───────────────────────────────────────────────────────────

def enroll_targets(campaign_id: str, leads: list[dict]) -> dict:
    """
    Inscreve leads numa campanha. `leads` é uma lista de dicts com pelo menos
    'nome' e 'telefone'. Normaliza telefone pra E.164, ignora quem estiver em
    opt-out, ignora duplicata (mesmo telefone já inscrito nesta campanha —
    a constraint UNIQUE(campaign_id, telefone) é a rede de segurança real).
    Retorna {"inscritos", "invalidos", "duplicados", "opt_out"} com as contagens.
    """
    vazio = {"inscritos": 0, "invalidos": 0, "duplicados": 0, "opt_out": 0}
    sb = _sb()
    if not sb:
        return vazio

    campanha = obter_campanha(campaign_id)
    if not campanha:
        return vazio
    dono_user_id = campanha["user_id"]

    etapas = listar_etapas(campaign_id)
    if not etapas:
        return vazio
    primeira = etapas[0]
    atraso_inicial = timedelta(hours=float(primeira.get("atraso_horas") or 0))
    proxima_em = (datetime.now(timezone.utc) + atraso_inicial).isoformat()

    # Normaliza e deduplica telefones em memória primeiro — evita 1 consulta
    # de opt-out por lead (uma planilha de milhares de linhas travaria a UI
    # fazendo centenas de round-trips sequenciais ao banco).
    por_telefone: dict[str, dict] = {}
    invalidos = 0
    duplicados_lote = 0
    for lead in leads:
        tel = normalizar_e164(lead.get("telefone", ""))
        if not tel:
            invalidos += 1
            continue
        if tel in por_telefone:
            duplicados_lote += 1
            continue
        por_telefone[tel] = lead

    if not por_telefone:
        return {"inscritos": 0, "invalidos": invalidos, "duplicados": duplicados_lote, "opt_out": 0}

    opt_outs: set[str] = set()
    try:
        todos_tels = list(por_telefone.keys())
        for i in range(0, len(todos_tels), 500):
            resp = (sb.table("dispatch_opt_outs").select("telefone")
                      .eq("user_id", dono_user_id).in_("telefone", todos_tels[i:i + 500]).execute())
            opt_outs.update(r["telefone"] for r in (resp.data or []))
    except Exception as e:
        logger.error("enroll_targets (checar opt-outs): %s", e)

    linhas = []
    opt_out_count = 0
    for tel, lead in por_telefone.items():
        if tel in opt_outs:
            opt_out_count += 1
            continue
        linhas.append({
            "campaign_id": campaign_id,
            "nome": str(lead.get("nome", "") or ""),
            "telefone": tel,
            "lead_snapshot": lead,
            "status": "pendente",
            "current_step_id": None,
            "proxima_etapa_em": proxima_em,
        })

    if not linhas:
        return {"inscritos": 0, "invalidos": invalidos, "duplicados": duplicados_lote, "opt_out": opt_out_count}

    inscritos = 0
    try:
        for i in range(0, len(linhas), 500):
            resp = (sb.table("dispatch_targets")
                      .upsert(linhas[i:i + 500], on_conflict="campaign_id,telefone", ignore_duplicates=True)
                      .execute())
            inscritos += len(resp.data or [])
    except Exception as e:
        logger.error("enroll_targets: %s", e)

    # Diferença entre o que foi enviado ao upsert e o que voltou = já
    # existia nesta campanha (ignore_duplicates descartou silenciosamente).
    duplicados_db = max(0, len(linhas) - inscritos)
    return {
        "inscritos": inscritos,
        "invalidos": invalidos,
        "duplicados": duplicados_lote + duplicados_db,
        "opt_out": opt_out_count,
    }


def listar_targets_campanha(campaign_id: str) -> list[dict]:
    sb = _sb()
    if not sb:
        return []
    try:
        resp = (sb.table("dispatch_targets")
                  .select("*").eq("campaign_id", campaign_id)
                  .order("criado_em", desc=True).execute())
        return resp.data or []
    except Exception as e:
        logger.error("listar_targets_campanha: %s", e)
        return []


def stats_campanha(campaign_id: str) -> dict:
    targets = listar_targets_campanha(campaign_id)
    stats = {"total": len(targets), "pendente": 0, "enviando": 0, "enviado": 0, "concluido": 0, "falhou": 0, "removido": 0}
    for t in targets:
        s = t.get("status", "pendente")
        stats[s] = stats.get(s, 0) + 1
    return stats


# ── Fila de disparo (usada pelo scheduler) ────────────────────────────────────

def atualizar_target(target_id: str, **campos) -> bool:
    sb = _sb()
    if not sb:
        return False
    try:
        sb.table("dispatch_targets").update(campos).eq("id", target_id).execute()
        return True
    except Exception as e:
        logger.error("atualizar_target: %s", e)
        return False


def claim_target_para_instancia(instance_id: str) -> Optional[dict]:
    """Reivindica atomicamente 1 alvo pronto pra envio pra essa instância (RPC claim_dispatch_target)."""
    sb = _sb()
    if not sb:
        return None
    try:
        resp = sb.rpc("claim_dispatch_target", {"p_instance_id": instance_id}).execute()
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception as e:
        logger.error("claim_target_para_instancia: %s", e)
        return None


def marcar_enviado(target: dict, campaign_id: str, step: dict, evolution_message_id: str, corpo_enviado: str) -> None:
    sb = _sb()
    if not sb:
        return
    try:
        prox = proxima_etapa(campaign_id, step["ordem"])
        agora = datetime.now(timezone.utc)
        if prox:
            atraso = timedelta(hours=float(prox.get("atraso_horas") or 0))
            sb.table("dispatch_targets").update({
                "status": "pendente",
                "current_step_id": step["id"],
                "proxima_etapa_em": (agora + atraso).isoformat(),
                "atualizado_em": agora.isoformat(),
            }).eq("id", target["id"]).execute()
        else:
            sb.table("dispatch_targets").update({
                "status": "concluido",
                "current_step_id": step["id"],
                "atualizado_em": agora.isoformat(),
            }).eq("id", target["id"]).execute()

        sb.table("dispatch_messages_log").insert({
            "target_id": target["id"],
            "campaign_id": campaign_id,
            "step_id": step["id"],
            "status": "sucesso",
            "evolution_message_id": evolution_message_id,
            "corpo_enviado": corpo_enviado,
        }).execute()
    except Exception as e:
        logger.error("marcar_enviado: %s", e)


def marcar_falha(target: dict, campaign_id: str, step: Optional[dict], erro_msg: str, corpo_enviado: str = "") -> None:
    sb = _sb()
    if not sb:
        return
    try:
        sb.table("dispatch_targets").update({
            "status": "falhou",
            "atualizado_em": datetime.now(timezone.utc).isoformat(),
        }).eq("id", target["id"]).execute()
        sb.table("dispatch_messages_log").insert({
            "target_id": target["id"],
            "campaign_id": campaign_id,
            "step_id": step["id"] if step else None,
            "status": "erro",
            "erro_msg": str(erro_msg)[:500],
            "corpo_enviado": corpo_enviado,
        }).execute()
    except Exception as e:
        logger.error("marcar_falha: %s", e)


def requeue_travados(minutos: int = 5) -> int:
    """Recupera alvos travados em 'enviando' há mais de `minutos` (crash mid-send) — entrega é 'pelo menos uma vez'."""
    sb = _sb()
    if not sb:
        return 0
    try:
        limite = (datetime.now(timezone.utc) - timedelta(minutes=minutos)).isoformat()
        resp = (sb.table("dispatch_targets")
                  .update({"status": "pendente"})
                  .eq("status", "enviando")
                  .lt("reservado_em", limite)
                  .execute())
        return len(resp.data or [])
    except Exception as e:
        logger.error("requeue_travados: %s", e)
        return 0


def liberar_proximo_envio(instance_id: str, intervalo_min_seg: int, intervalo_max_seg: int) -> None:
    """Após um envio, sorteia e grava quando a instância pode enviar de novo (rate limit anti-banimento)."""
    sb = _sb()
    if not sb:
        return
    try:
        agora = datetime.now(timezone.utc)
        delay = random.randint(max(1, int(intervalo_min_seg)), max(int(intervalo_min_seg), int(intervalo_max_seg)))
        sb.table("whatsapp_instances").update({
            "ultimo_envio_em": agora.isoformat(),
            "proximo_envio_liberado_em": (agora + timedelta(seconds=delay)).isoformat(),
        }).eq("id", instance_id).execute()
    except Exception as e:
        logger.error("liberar_proximo_envio: %s", e)
