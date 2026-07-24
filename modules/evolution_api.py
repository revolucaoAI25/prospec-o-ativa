"""
Wrapper fino para a Evolution API (gateway WhatsApp não-oficial, self-hosted).

Docs: https://docs.evolutionfoundation.com.br
Auth: header `apikey` (chave global da instância do servidor).

Configuração necessária (Streamlit Secrets / env):
  EVOLUTION_API_URL = "https://sua-evolution-api.up.railway.app"
  EVOLUTION_API_KEY = "sua_chave_global_aqui"
"""

from __future__ import annotations

import os
import requests

try:
    import streamlit as st
except ImportError:
    st = None


def _s(key: str) -> str:
    if st is not None:
        try:
            v = st.secrets.get(key, "")
            if v:
                return str(v).strip()
        except Exception:
            pass
    return os.getenv(key, "").strip()


def _base_url() -> str:
    return _s("EVOLUTION_API_URL").rstrip("/")


def _headers() -> dict:
    return {"apikey": _s("EVOLUTION_API_KEY"), "Content-Type": "application/json"}


def configurado() -> bool:
    return bool(_s("EVOLUTION_API_URL") and _s("EVOLUTION_API_KEY"))


def criar_instancia(nome_instancia: str) -> dict:
    """Cria uma nova instância WhatsApp. Retorna o payload da API (inclui QR code se disponível na criação)."""
    resp = requests.post(
        f"{_base_url()}/instance/create",
        headers=_headers(),
        json={
            "instanceName": nome_instancia,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def obter_qrcode(nome_instancia: str) -> dict:
    """Busca um QR code novo para pareamento (a instância deve existir e estar desconectada)."""
    resp = requests.get(
        f"{_base_url()}/instance/connect/{nome_instancia}",
        headers=_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def status_conexao(nome_instancia: str) -> str:
    """Retorna o estado da conexão: 'open' (conectado), 'connecting', 'close' (desconectado)."""
    estado, _ = status_e_numero(nome_instancia)
    return estado


def status_e_numero(nome_instancia: str) -> tuple[str, str]:
    """
    Retorna (estado, numero_conectado).

    `connectionState` é o endpoint oficial, mas tem um bug conhecido na
    Evolution API onde fica preso em "connecting" mesmo já pareado
    (github.com/EvolutionAPI/evolution-api/issues/1512). Por isso também
    consulta `fetchInstances`, que reflete o estado real mais rápido e,
    de quebra, traz o número do WhatsApp conectado.
    """
    estado_cs = ""
    try:
        resp = requests.get(
            f"{_base_url()}/instance/connectionState/{nome_instancia}",
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        estado_cs = (resp.json().get("instance") or {}).get("state", "") or ""
    except Exception:
        pass

    estado_fi, numero = "", ""
    try:
        resp2 = requests.get(
            f"{_base_url()}/instance/fetchInstances",
            headers=_headers(),
            params={"instanceName": nome_instancia},
            timeout=15,
        )
        resp2.raise_for_status()
        itens = resp2.json()
        item = itens[0] if isinstance(itens, list) and itens else {}
        inst = item.get("instance", item) if isinstance(item, dict) else {}
        estado_fi = inst.get("connectionStatus") or inst.get("state") or ""
        numero = inst.get("number") or (inst.get("ownerJid") or "").split("@")[0]
    except Exception:
        pass

    estado = "open" if "open" in (estado_cs, estado_fi) else (estado_cs or estado_fi or "close")
    return estado, numero


def desconectar_instancia(nome_instancia: str) -> None:
    resp = requests.delete(
        f"{_base_url()}/instance/logout/{nome_instancia}",
        headers=_headers(),
        timeout=15,
    )
    resp.raise_for_status()


def excluir_instancia(nome_instancia: str) -> None:
    resp = requests.delete(
        f"{_base_url()}/instance/delete/{nome_instancia}",
        headers=_headers(),
        timeout=15,
    )
    resp.raise_for_status()


def enviar_texto(nome_instancia: str, numero_e164: str, texto: str) -> dict:
    """
    Envia uma mensagem de texto. numero_e164 sem "+" (ex: 5511999999999).
    Retorna o payload da API — o campo key.id é o ID da mensagem, usado
    depois para correlacionar com webhooks de status de entrega.
    """
    resp = requests.post(
        f"{_base_url()}/message/sendText/{nome_instancia}",
        headers=_headers(),
        json={
            "number": numero_e164,
            "text": texto,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
