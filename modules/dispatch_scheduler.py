"""
Scheduler de disparo WhatsApp — thread de background que processa a fila de
mensagens pendentes, respeitando o intervalo anti-banimento por instância.

Diferente do AutomationScheduler (modules/scheduler.py), o rate-limit aqui é
por INSTÂNCIA, não por item da fila — por isso o processamento roda inline,
um alvo por instância por tick, nunca em threads paralelas por alvo (evita
corrida onde duas threads liberariam o mesmo envio ao mesmo tempo).

Fase 1: só processa dispatch_targets já inscritos (origem busca_existente /
upload, feitas pela UI). O scan de gatilho automático (auto_trigger /
sheet_watch) entra na Fase 2, como um segundo sub-loop mais lento dentro do
mesmo processo.
"""

from __future__ import annotations
import logging
import threading
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

TICK_SEGUNDOS = 15


def _renderizar_mensagem(corpo: str, lead_snapshot: dict) -> str:
    """Substitui {{variavel}} pelo valor correspondente no snapshot do lead."""
    texto = corpo or ""
    for chave, valor in (lead_snapshot or {}).items():
        texto = texto.replace("{{" + str(chave) + "}}", str(valor or ""))
    return texto


def _instancia_liberada(instance: dict) -> bool:
    proximo = instance.get("proximo_envio_liberado_em")
    if not proximo:
        return True
    try:
        dt_proximo = datetime.fromisoformat(str(proximo).replace("Z", "+00:00"))
        return datetime.now(timezone.utc) >= dt_proximo
    except Exception:
        return True


def _etapa_atual_ordem(campaign_id: str, target: dict, etapas: list[dict]) -> int:
    """Retorna a ordem da última etapa enviada (0 = nenhuma enviada ainda)."""
    current_id = target.get("current_step_id")
    if not current_id:
        return 0
    atual = next((e for e in etapas if e["id"] == current_id), None)
    return atual["ordem"] if atual else 0


def _processar_instancia(instance: dict) -> None:
    from modules import dispatch_db, evolution_api

    if instance.get("status") != "conectado" or not _instancia_liberada(instance):
        return

    instance_id = instance["id"]
    target = dispatch_db.claim_target_para_instancia(instance_id)
    if not target:
        return

    campaign_id = target["campaign_id"]
    campanha = dispatch_db.obter_campanha(campaign_id)
    if not campanha or campanha.get("status") != "ativa":
        # Campanha foi pausada/excluída entre o claim e agora
        dispatch_db.marcar_falha(target, campaign_id, None, "Campanha não está mais ativa nesse momento.")
        return

    etapas = dispatch_db.listar_etapas(campaign_id)
    ordem_atual = _etapa_atual_ordem(campaign_id, target, etapas)
    step = dispatch_db.proxima_etapa(campaign_id, ordem_atual)

    if not step:
        # Defensivo — não deveria acontecer (marcar_enviado já marca 'concluido'
        # quando não há próxima etapa, então o claim não devolveria esse alvo de novo).
        dispatch_db.marcar_enviado(target, campaign_id, {"id": None, "ordem": 10**9}, "", "")
        return

    texto = _renderizar_mensagem(step["corpo_mensagem"], target.get("lead_snapshot") or {})

    try:
        resp = evolution_api.enviar_texto(instance["evolution_instance_name"], target["telefone"], texto)
        msg_id = (resp.get("key") or {}).get("id", "")
        dispatch_db.marcar_enviado(target, campaign_id, step, msg_id, texto)
    except Exception as e:
        logger.error("Falha ao enviar mensagem (target=%s): %s", target["id"], e)
        dispatch_db.marcar_falha(target, campaign_id, step, str(e), texto)

    dispatch_db.liberar_proximo_envio(
        instance_id,
        campanha.get("intervalo_min_seg", 30),
        campanha.get("intervalo_max_seg", 90),
    )


class DispatchScheduler:
    """Thread de background que processa a fila de disparo WhatsApp a cada TICK_SEGUNDOS."""

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="DispatchScheduler")
        self._thread.start()
        logger.info("DispatchScheduler iniciado")

    def _loop(self):
        time.sleep(30)  # aguarda o app terminar de subir
        while self._running:
            try:
                self._tick()
            except Exception as e:
                logger.error("DispatchScheduler tick error: %s", e)
            time.sleep(TICK_SEGUNDOS)

    def _tick(self):
        from modules import dispatch_db
        dispatch_db.requeue_travados()
        for inst in dispatch_db.listar_instancias_conectadas():
            try:
                _processar_instancia(inst)
            except Exception as e:
                logger.error("Erro processando instância %s: %s", inst.get("id"), e)


# ── Singleton global ───────────────────────────────────────────────────────

_instance: DispatchScheduler | None = None
_lock = threading.Lock()


def ensure_started() -> DispatchScheduler:
    """Garante que o scheduler de disparo esteja rodando. Idempotente."""
    global _instance
    if _instance is not None:
        return _instance
    with _lock:
        if _instance is None:
            _instance = DispatchScheduler()
            _instance.start()
    return _instance
