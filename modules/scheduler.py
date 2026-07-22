"""
Scheduler de automações — thread de background que executa buscas programadas.

Usa um singleton global iniciado uma única vez quando o app sobe.
Não depende de st.session_state — opera exclusivamente via service role do Supabase.
"""

from __future__ import annotations
import os
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Timezone de Brasília
try:
    from zoneinfo import ZoneInfo
    BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")
except Exception:
    import datetime as _dt
    BRAZIL_TZ = timezone(timedelta(hours=-3))  # fallback UTC-3


# ── Cálculo de próxima execução ───────────────────────────────────────────────

def calcular_proxima_execucao(
    dias_semana: list[int],
    horario: str,
) -> Optional[datetime]:
    """
    Calcula o próximo datetime (com timezone de Brasília) em que a automação deve rodar.

    dias_semana: lista de ints onde 0=Dom, 1=Seg, 2=Ter, 3=Qua, 4=Qui, 5=Sex, 6=Sáb
    horario: string "HH:MM" ou múltiplos separados por vírgula "08:00,14:00,20:00"

    Retorna o mais próximo datetime com timezone (America/Sao_Paulo) ou None.
    """
    if not dias_semana or not horario:
        return None

    horarios = [h.strip() for h in horario.split(",") if h.strip()]
    agora = datetime.now(BRAZIL_TZ)
    melhor: Optional[datetime] = None

    for h_str in horarios:
        try:
            h, m = map(int, h_str.split(":")[:2])
        except (ValueError, AttributeError):
            continue

        for delta in range(8):  # hoje + até 7 dias à frente
            data_cand = (agora + timedelta(days=delta)).date()
            # Python weekday: 0=Seg...6=Dom → nossa conv: 0=Dom,1=Seg...6=Sáb
            python_wd = data_cand.weekday()
            nosso_wd  = (python_wd + 1) % 7

            if nosso_wd not in dias_semana:
                continue

            dt_cand = datetime(
                data_cand.year, data_cand.month, data_cand.day,
                h, m, 0, tzinfo=BRAZIL_TZ,
            )
            if dt_cand > agora:
                if melhor is None or dt_cand < melhor:
                    melhor = dt_cand
                break  # próximo horário

    return melhor


def formatar_horarios(horario: str) -> str:
    """'08:00,14:00,20:00' → '08:00, 14:00 e 20:00'"""
    times = [h.strip() for h in (horario or "").split(",") if h.strip()]
    if not times:
        return "—"
    if len(times) == 1:
        return times[0]
    return ", ".join(times[:-1]) + f" e {times[-1]}"


def formatar_proxima_execucao(proxima_iso: Optional[str]) -> str:
    """Formata proxima_execucao para exibição amigável em PT-BR."""
    if not proxima_iso:
        return "Não agendada"
    try:
        dt = datetime.fromisoformat(proxima_iso.replace("Z", "+00:00"))
        dt_br = dt.astimezone(BRAZIL_TZ)
        agora = datetime.now(BRAZIL_TZ)
        diff = dt_br - agora
        total_min = int(diff.total_seconds() / 60)

        if total_min < 1:
            return "Agora"
        if total_min < 60:
            return f"Em {total_min} min"
        if total_min < 1440:
            horas = total_min // 60
            return f"Em {horas}h"
        if total_min < 2880:
            return f"Amanhã às {dt_br.strftime('%H:%M')}"
        dias = total_min // 1440
        return f"Em {dias} dias às {dt_br.strftime('%H:%M')}"
    except Exception:
        return proxima_iso[:16] if proxima_iso else "—"


def formatar_dias(dias_semana: list[int]) -> str:
    """Converte lista de dias para string legível."""
    NOMES = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb"}
    if not dias_semana:
        return "Nenhum dia"
    if sorted(dias_semana) == [1, 2, 3, 4, 5]:
        return "Seg–Sex"
    if sorted(dias_semana) == [0, 6]:
        return "Sáb e Dom"
    if sorted(dias_semana) == [0, 1, 2, 3, 4, 5, 6]:
        return "Todos os dias"
    return ", ".join(NOMES.get(d, str(d)) for d in sorted(dias_semana))


# ── Execução de automação ─────────────────────────────────────────────────────

def _get_cdd_key() -> str:
    key = os.getenv("CDD_API_KEY", "")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("CDD_API_KEY", "")
        except Exception:
            pass
    return key


def executar_automacao(auto: dict) -> None:
    """
    Executa uma automação: busca leads e exporta para o Google Sheets configurado.
    Chamada pelo scheduler em background thread — sem session_state.
    """
    from modules.automation_db import (
        get_perfil_usuario, get_telefones_usuario, get_cnpjs_usuario,
        salvar_pesquisa_scheduler, salvar_leads_scheduler,
        debit_credits_scheduler, registrar_execucao, atualizar_automacao,
    )
    from modules.google_sheets import exportar as sheets_exportar

    auto_id = auto["id"]
    user_id = auto["user_id"]
    tipo    = auto["tipo"]
    filtros = auto.get("filtros") or {}

    logger.info("Executando automação %s (user=%s tipo=%s)", auto_id, user_id, tipo)

    # 0. Verificar data de encerramento
    data_fim_str = filtros.get("data_fim", "")
    if data_fim_str:
        try:
            from datetime import date as _date
            data_fim = datetime.strptime(data_fim_str, "%Y-%m-%d").date()
            hoje = datetime.now(BRAZIL_TZ).date()
            if hoje > data_fim:
                logger.info("Automação %s encerrada: data_fim %s atingida", auto_id, data_fim_str)
                from modules.automation_db import atualizar_automacao as _upd
                _upd(auto_id, ativa=False)
                return
        except Exception:
            pass

    # 1. Perfil do usuário
    perfil = get_perfil_usuario(user_id)
    if not perfil:
        registrar_execucao(auto_id, user_id, "error", erro="Perfil não encontrado")
        _reagendar(auto)
        return

    # 2. Verificar créditos CNPJ
    limite = int(filtros.get("limite", 50))
    if tipo == "cnpj":
        saldo = int(perfil.get("cdd_credits", 0))
        if saldo < 1:
            logger.info("Automação %s pausada: sem créditos CDD", auto_id)
            registrar_execucao(auto_id, user_id, "sem_creditos")
            _reagendar(auto)
            return
        # Busca até o mínimo entre limite e saldo
        limite = min(limite, saldo)

    # 3. API Keys
    _apify_key_sched = perfil.get("apify_api_key", "")
    if tipo == "maps":
        # Tenta pool primeiro, cai na chave única se não houver pool
        from modules.database import selecionar_chave_maps, registrar_uso_maps, salvar_pool_maps_usuario
        _pool_sched = perfil.get("maps_keys_pool") or []
        _pool_idx   = -1
        api_key     = ""
        if _pool_sched:
            api_key, _pool_idx, _pool_sched = selecionar_chave_maps(_pool_sched)
        if not api_key:
            if perfil.get("maps_credits_enabled"):
                api_key = perfil.get("maps_api_key_admin", "")
            else:
                api_key = perfil.get("google_maps_api_key", "")
        if not api_key and not _apify_key_sched:
            registrar_execucao(auto_id, user_id, "error", erro="Chave Google Maps não configurada")
            _reagendar(auto)
            return
    else:
        api_key = _get_cdd_key()
        if not api_key:
            registrar_execucao(auto_id, user_id, "error", erro="CDD_API_KEY não configurada")
            _reagendar(auto)
            return

    # 4. Deduplicação — sempre ativada em automações
    excl_tels = get_telefones_usuario(user_id)
    excl_cnpjs = get_cnpjs_usuario(user_id)

    # 5. Executar busca
    resultados = []
    _sched_used_apify = False
    try:
        if tipo == "maps":
            _maps_kwargs = dict(
                query_base=filtros.get("query_base", ""),
                localidade=filtros.get("localidade", ""),
                limite=limite,
                nicho=filtros.get("nicho", ""),
                subnicho=filtros.get("subnicho", ""),
                cidade=filtros.get("cidade", ""),
                estado=filtros.get("estado", ""),
                progress_callback=None,
                exclude_phones=excl_tels,
                show_phone=filtros.get("show_phone", True),
                show_rating=filtros.get("show_rating", True),
            )
            if api_key:
                from modules.google_maps import buscar as maps_buscar, QuotaExceededError
                try:
                    resultados = maps_buscar(api_key=api_key, **_maps_kwargs)
                except QuotaExceededError:
                    if not _apify_key_sched:
                        raise
                    logger.info("Automação %s: cota Google Maps esgotada, usando Apify", auto_id)
                    _sched_used_apify = True
                    from modules.apify_maps import buscar as apify_buscar
                    resultados = apify_buscar(api_key=_apify_key_sched, **_maps_kwargs)
            else:
                _sched_used_apify = True
                from modules.apify_maps import buscar as apify_buscar
                resultados = apify_buscar(api_key=_apify_key_sched, **_maps_kwargs)
            # Atualiza contador do pool (somente se usou Google Maps)
            if not _sched_used_apify and _pool_sched and _pool_idx >= 0:
                from modules.database import salvar_pool_maps_por_user_id
                salvar_pool_maps_por_user_id(
                    user_id,
                    registrar_uso_maps(_pool_sched, _pool_idx, len(resultados)),
                )
        else:  # cnpj
            from modules.casa_dos_dados import buscar as cdd_buscar
            _busca_txt = None
            _sits_cdd = None
            _rj_auto = bool(filtros.get("recuperacao_judicial"))
            if _rj_auto:
                # tipo_busca "radical" não funciona na API da CDD (sempre
                # retorna 0) — "exata" funciona como busca por substring.
                _busca_txt = [{
                    "texto": ["recuperacao judicial"], "tipo_busca": "exata",
                    "razao_social": True, "nome_fantasia": True,
                }]
                _sits_cdd = ["ATIVA", "SUSPENSA", "INAPTA"]
            resultados = cdd_buscar(
                api_key=api_key,
                cnaes=filtros.get("cnaes", []),
                uf=filtros.get("uf", ""),
                municipio=filtros.get("municipio", ""),
                porte=filtros.get("porte") or None,
                matriz_filial=filtros.get("matriz_filial", ""),
                simples_optante=filtros.get("simples_optante"),
                excluir_simples=filtros.get("excluir_simples", False),
                mei_optante=filtros.get("mei_optante"),
                excluir_mei=filtros.get("excluir_mei", False),
                com_telefone=filtros.get("com_telefone", True),
                com_email=filtros.get("com_email", False),
                somente_celular=filtros.get("somente_celular", False),
                somente_fixo=filtros.get("somente_fixo", False),
                excluir_email_contab=True,
                limite=limite,
                exclude_phones=excl_tels,
                exclude_cnpjs=excl_cnpjs,
                cnae_tipo=filtros.get("cnae_tipo", "principal"),
                busca_textual=_busca_txt,
                situacoes_cadastrais=_sits_cdd,
                dedup_raiz=_rj_auto,
            )
    except Exception as e:
        logger.error("Erro na busca da automação %s: %s", auto_id, e)
        registrar_execucao(auto_id, user_id, "error", erro=str(e)[:500])
        _reagendar(auto)
        return

    total = len(resultados)
    logger.info("Automação %s encontrou %d leads", auto_id, total)

    # 6. Salvar no histórico
    fonte = "maps" if tipo == "maps" else "receita_federal"
    search_id = salvar_pesquisa_scheduler(
        user_id=user_id,
        nicho=filtros.get("nicho", "") or filtros.get("cnaes", [""])[0],
        subnicho=filtros.get("subnicho", ""),
        cidade=filtros.get("cidade", ""),
        estado=filtros.get("estado", "") or filtros.get("uf", ""),
        localidade=filtros.get("localidade", "") or filtros.get("municipio", ""),
        fonte=fonte,
        total=total,
    )
    if search_id and resultados:
        salvar_leads_scheduler(search_id, user_id, resultados)

    # 7. Debitar créditos CNPJ
    if tipo == "cnpj" and total > 0:
        debit_credits_scheduler(user_id, total, "cdd")
    elif tipo == "maps" and perfil.get("maps_credits_enabled") and total > 0 and not _sched_used_apify:
        # Só cobra créditos Maps da plataforma se o Google Maps foi de fato
        # usado — quando cai no fallback Apify (chave pessoal do usuário),
        # o custo é dele, não da plataforma.
        debit_credits_scheduler(user_id, total, "maps")

    # 8. Exportar para Google Sheets
    sheets_status = "success"
    if auto.get("sheet_id") and resultados:
        creds_raw = perfil.get("google_sheets_creds")
        if isinstance(creds_raw, dict):
            creds_dict = creds_raw.get("oauth") or creds_raw
        else:
            creds_dict = None

        if creds_dict:
            try:
                ok, msg = sheets_exportar(
                    resultados=resultados,
                    creds_dict=creds_dict,
                    sheet_id=auto["sheet_id"],
                    aba_nome=auto.get("sheet_aba", "Leads"),
                    modo="acrescentar",
                )
                if not ok:
                    logger.warning("Sheets export falhou na automação %s: %s", auto_id, msg)
            except Exception as e:
                logger.error("Sheets export erro na automação %s: %s", auto_id, e)
        else:
            sheets_status = "sem_sheets"

    # 9. Registrar log da execução
    registrar_execucao(auto_id, user_id, sheets_status, leads=total)

    # 10. Reagendar
    _reagendar(auto)


def _reservar_automacao(auto: dict) -> None:
    """
    Move proxima_execucao para longe no futuro (sentinel) antes de executar.
    Impede que o scheduler ou o botão manual disparem a mesma automação duas vezes.
    _reagendar() ao final da execução substitui esse valor pelo próximo horário real.
    """
    from modules.automation_db import atualizar_automacao
    sentinel = datetime.now(timezone.utc) + timedelta(hours=24)
    atualizar_automacao(auto["id"], proxima_execucao=sentinel)


def _reagendar(auto: dict) -> None:
    """Calcula e salva a próxima execução da automação."""
    from modules.automation_db import atualizar_automacao
    proxima = calcular_proxima_execucao(
        dias_semana=auto.get("dias_semana", [1, 2, 3, 4, 5]),
        horario=auto.get("horario", "08:00"),
    )
    campos: dict = {
        "ultima_execucao": datetime.now(timezone.utc),
    }
    if proxima:
        campos["proxima_execucao"] = proxima
    atualizar_automacao(auto["id"], **campos)


# ── Singleton do scheduler ────────────────────────────────────────────────────

class AutomationScheduler:
    """Thread de background que verifica e executa automações vencidas a cada minuto."""

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="AutomationScheduler",
        )
        self._thread.start()
        logger.info("AutomationScheduler iniciado")

    def _loop(self):
        # Aguarda 30s no startup para o app terminar de carregar
        time.sleep(30)
        while self._running:
            try:
                self._tick()
            except Exception as e:
                logger.error("Scheduler tick error: %s", e)
            time.sleep(60)

    def _tick(self):
        from modules.automation_db import obter_automacoes_vencidas, atualizar_automacao
        vencidas = obter_automacoes_vencidas()
        if not vencidas:
            return
        logger.info("Scheduler: %d automação(ões) vencida(s)", len(vencidas))
        for auto in vencidas:
            # "Reserva" a automação atualizando proxima_execucao para o futuro
            # antes de executar — evita duplo disparo (scheduler + botão manual)
            _reservar_automacao(auto)
            t = threading.Thread(
                target=self._executar_com_guard,
                args=(auto,),
                daemon=True,
            )
            t.start()

    def _executar_com_guard(self, auto: dict):
        try:
            executar_automacao(auto)
        except Exception as e:
            logger.error("Erro na automação %s: %s", auto.get("id"), e)
            try:
                from modules.automation_db import registrar_execucao
                registrar_execucao(auto["id"], auto["user_id"], "error", erro=str(e)[:500])
                _reagendar(auto)
            except Exception:
                pass


# Singleton global
_instance: Optional[AutomationScheduler] = None
_lock = threading.Lock()


def ensure_started() -> AutomationScheduler:
    """Garante que o scheduler esteja rodando. Idempotente — pode ser chamado várias vezes."""
    global _instance
    if _instance is not None:
        return _instance
    with _lock:
        if _instance is None:
            _instance = AutomationScheduler()
            _instance.start()
    return _instance
