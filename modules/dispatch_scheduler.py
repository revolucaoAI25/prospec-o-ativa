"""
Scheduler de disparo WhatsApp — thread de background que processa a fila de
mensagens pendentes, respeitando o intervalo anti-banimento por instância.

Diferente do AutomationScheduler (modules/scheduler.py), o rate-limit aqui é
por INSTÂNCIA, não por item da fila — por isso o processamento roda inline,
um alvo por instância por tick, nunca em threads paralelas por alvo (evita
corrida onde duas threads liberariam o mesmo envio ao mesmo tempo).

Fase 2: além da fila de envio (acima), um segundo sub-loop bem mais lento
varre campanhas do tipo sheet_watch e importa linhas novas de uma Planilha
Google como novos targets — mesmo processo, sem thread própria (evita a
mesma classe de corrida que o envio já evita rodando inline).
"""

from __future__ import annotations
import logging
import threading
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

TICK_SEGUNDOS = 15
SHEET_WATCH_INTERVALO_SEGUNDOS = 120


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


def _enviar_etapa_evolution(instance: dict, target: dict, step: dict) -> tuple[str, str]:
    """Retorna (evolution_message_id, texto_enviado) — lança em caso de erro."""
    from modules import evolution_api
    texto = _renderizar_mensagem(step["corpo_mensagem"], target.get("lead_snapshot") or {})
    resp = evolution_api.enviar_texto(instance["evolution_instance_name"], target["telefone"], texto)
    return (resp.get("key") or {}).get("id", ""), texto


def _enviar_etapa_oficial(instance: dict, target: dict, step: dict) -> tuple[str, str]:
    """Retorna (message_id, parametros_renderizados_como_texto) — lança em caso de erro."""
    from modules import dispatch_db, whatsapp_oficial
    if not step.get("template_id"):
        raise RuntimeError("Etapa sem template configurado — instância é do canal oficial.")
    template = dispatch_db.obter_template(step["template_id"])
    if not template:
        raise RuntimeError("Template da etapa não encontrado (pode ter sido excluído).")
    if template.get("status_aprovacao") != "aprovado":
        raise RuntimeError(f"Template '{template.get('nome')}' não está aprovado (status: {template.get('status_aprovacao')}).")

    lead_snapshot = target.get("lead_snapshot") or {}
    parametros = [_renderizar_mensagem(p, lead_snapshot) for p in (step.get("parametros_template") or [])]
    resp = whatsapp_oficial.enviar_template(
        instance["token_oficial"], instance["phone_number_id"], target["telefone"],
        template["nome_meta"], template.get("idioma", "pt_BR"), parametros,
    )
    msg_id = (resp.get("messages") or [{}])[0].get("id", "")
    return msg_id, " | ".join(parametros)


def _processar_instancia(instance: dict) -> None:
    from modules import dispatch_db

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
        # Marca concluído direto, sem log de mensagem — nada foi enviado de fato.
        dispatch_db.atualizar_target(target["id"], status="concluido", atualizado_em=datetime.now(timezone.utc).isoformat())
        return

    try:
        if instance.get("canal") == "oficial":
            msg_id, corpo_log = _enviar_etapa_oficial(instance, target, step)
        else:
            msg_id, corpo_log = _enviar_etapa_evolution(instance, target, step)
        dispatch_db.marcar_enviado(target, campaign_id, step, msg_id, corpo_log)
    except Exception as e:
        logger.error("Falha ao enviar mensagem (target=%s): %s", target["id"], e)
        dispatch_db.marcar_falha(target, campaign_id, step, str(e), "")

    dispatch_db.liberar_proximo_envio(
        instance_id,
        campanha.get("intervalo_min_seg", 30),
        campanha.get("intervalo_max_seg", 90),
    )


def _processar_sheet_watcher(campanha: dict) -> None:
    """Lê linhas novas da planilha monitorada por essa campanha e as inscreve
    como targets. `ultima_linha_processada` é um watermark de quantas linhas
    de DADOS (sem contar o cabeçalho) já foram vistas — só otimização pra não
    reler tudo a cada scan; quem garante contra inscrição duplicada é o
    UNIQUE(campaign_id, telefone), igual às outras origens."""
    from modules import dispatch_db
    from modules.automation_db import get_perfil_usuario
    from modules.google_sheets import ler_valores

    watcher = dispatch_db.obter_sheet_watcher(campanha["id"])
    if not watcher:
        return

    perfil = get_perfil_usuario(campanha["user_id"])
    creds_raw = perfil.get("google_sheets_creds")
    if isinstance(creds_raw, dict):
        creds_dict = creds_raw.get("oauth") or creds_raw
    else:
        creds_dict = None
    if not creds_dict:
        logger.warning("Campanha %s (sheet_watch): usuário sem Google Sheets conectado.", campanha["id"])
        return

    try:
        valores = ler_valores(creds_dict, watcher["sheet_id"], watcher["aba_nome"])
    except Exception as e:
        logger.error("Campanha %s (sheet_watch): erro ao ler planilha: %s", campanha["id"], e)
        return

    if not valores:
        return
    cabecalho = valores[0]
    linhas = valores[1:]
    ja_processadas = watcher.get("ultima_linha_processada") or 0
    novas = linhas[ja_processadas:]
    if not novas:
        return

    try:
        idx_tel = cabecalho.index(watcher["coluna_telefone"])
    except ValueError:
        logger.error(
            "Campanha %s (sheet_watch): coluna de telefone '%s' não existe mais no cabeçalho da planilha.",
            campanha["id"], watcher["coluna_telefone"],
        )
        return
    coluna_nome = watcher.get("coluna_nome") or ""
    idx_nome = cabecalho.index(coluna_nome) if coluna_nome and coluna_nome in cabecalho else None

    leads = []
    for linha in novas:
        lead = {cabecalho[i]: (linha[i] if i < len(linha) else "") for i in range(len(cabecalho))}
        lead["telefone"] = linha[idx_tel] if idx_tel < len(linha) else ""
        lead["nome"] = linha[idx_nome] if (idx_nome is not None and idx_nome < len(linha)) else ""
        leads.append(lead)

    resultado = dispatch_db.enroll_targets(campanha["id"], leads)
    dispatch_db.atualizar_sheet_watcher(watcher["id"], ultima_linha_processada=len(linhas))
    logger.info(
        "Campanha %s (sheet_watch): %d linha(s) nova(s) na planilha, %d inscrita(s).",
        campanha["id"], len(novas), resultado.get("inscritos", 0),
    )


def _processar_auto_trigger(campanha: dict) -> None:
    """Busca leads do próprio dono da campanha que batem com o filtro
    (nicho/subnicho/UF) extraídos desde o último scan, e os inscreve.
    Escopo intencional: só leads do próprio admin, nunca de outros usuários
    da plataforma (privacidade/consentimento — decisão tomada no desenho
    original dessa feature)."""
    from modules import dispatch_db

    leads = dispatch_db.buscar_leads_filtro(
        user_id=campanha["user_id"],
        nicho=campanha.get("filtro_nicho") or "",
        subnicho=campanha.get("filtro_subnicho") or "",
        uf=campanha.get("filtro_uf") or "",
        desde=campanha.get("ultimo_trigger_em"),
    )
    agora_iso = datetime.now(timezone.utc).isoformat()
    if not leads:
        dispatch_db.atualizar_campanha(campanha["id"], ultimo_trigger_em=agora_iso)
        return

    resultado = dispatch_db.enroll_targets(campanha["id"], leads)
    dispatch_db.atualizar_campanha(campanha["id"], ultimo_trigger_em=agora_iso)
    logger.info(
        "Campanha %s (auto_trigger): %d lead(s) novo(s) batendo com o filtro, %d inscrito(s).",
        campanha["id"], len(leads), resultado.get("inscritos", 0),
    )


class DispatchScheduler:
    """Thread de background que processa a fila de disparo WhatsApp a cada TICK_SEGUNDOS."""

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._ultimo_watch = 0.0

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
            if time.time() - self._ultimo_watch >= SHEET_WATCH_INTERVALO_SEGUNDOS:
                try:
                    self._tick_sheet_watch()
                except Exception as e:
                    logger.error("DispatchScheduler sheet-watch tick error: %s", e)
                self._ultimo_watch = time.time()
            time.sleep(TICK_SEGUNDOS)

    def _tick(self):
        from modules import dispatch_db
        dispatch_db.requeue_travados()
        for inst in dispatch_db.listar_instancias_conectadas():
            try:
                _processar_instancia(inst)
            except Exception as e:
                logger.error("Erro processando instância %s: %s", inst.get("id"), e)

    def _tick_sheet_watch(self):
        from modules import dispatch_db
        for campanha in dispatch_db.listar_campanhas_sheet_watch_ativas():
            try:
                _processar_sheet_watcher(campanha)
            except Exception as e:
                logger.error("Erro processando sheet_watch da campanha %s: %s", campanha.get("id"), e)
        for campanha in dispatch_db.listar_campanhas_auto_trigger_ativas():
            try:
                _processar_auto_trigger(campanha)
            except Exception as e:
                logger.error("Erro processando auto_trigger da campanha %s: %s", campanha.get("id"), e)


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
