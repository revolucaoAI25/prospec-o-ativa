"""
Notificações administrativas via webhook (Make.com/Integromat).

Configuração necessária (Streamlit Secrets / env):
  OFICIAL_REQUEST_WEBHOOK_URL = "https://hook.us1.make.com/..."
"""

from __future__ import annotations

import os
import logging
import requests

logger = logging.getLogger(__name__)

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


def notificar_pedido_conexao_oficial(payload: dict) -> bool:
    """Dispara o webhook de novo pedido de conexão do canal oficial. Falha
    silenciosamente (só loga) — nunca deve impedir o cliente de registrar o
    pedido, mesmo se a notificação falhar."""
    url = _s("OFICIAL_REQUEST_WEBHOOK_URL")
    if not url:
        logger.warning("OFICIAL_REQUEST_WEBHOOK_URL não configurada — pedido registrado sem notificação.")
        return False
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error("notificar_pedido_conexao_oficial: %s", e)
        return False
