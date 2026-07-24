"""
Wrapper fino para o canal oficial do WhatsApp (WhatsApp Business Cloud API)
via DatafyAPI (https://datafyapi.com.br) — que espelha a Cloud API da Meta:
só mudam a URL base e o token, os campos e o formato são os mesmos da
documentação oficial da Meta.

Cada instância oficial tem suas PRÓPRIAS credenciais (token, phone_number_id,
waba_id), diferente da Evolution API (que usa uma chave global do servidor)
— por isso as funções aqui recebem `token`/`phone_number_id`/`waba_id`
explicitamente em vez de lerem de secrets globais.

Configuração necessária (Streamlit Secrets / env) — só a URL base, que é
compartilhada entre todos os clientes:
  DATAFY_API_BASE_URL = "https://cloud.datafyapi.com.br/v1"  (padrão se omitido)
"""

from __future__ import annotations

import os
import requests

try:
    import streamlit as st
except ImportError:
    st = None

_BASE_PADRAO = "https://cloud.datafyapi.com.br/v1"


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
    return (_s("DATAFY_API_BASE_URL") or _BASE_PADRAO).rstrip("/")


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def enviar_texto(token: str, phone_number_id: str, numero_e164: str, texto: str) -> dict:
    """Envia texto livre — só funciona dentro da janela de 24h após o cliente
    ter mandado mensagem primeiro. Pra iniciar contato, use enviar_template()."""
    resp = requests.post(
        f"{_base_url()}/{phone_number_id}/messages",
        headers=_headers(token),
        json={
            "messaging_product": "whatsapp",
            "to": numero_e164,
            "type": "text",
            "text": {"body": texto},
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def enviar_template(
    token: str, phone_number_id: str, numero_e164: str,
    nome_template: str, idioma: str, parametros_corpo: list[str] | None = None,
) -> dict:
    """
    Envia uma mensagem de template aprovado — é o único jeito de iniciar
    contato com um cliente que nunca falou com o número antes (a Meta não
    permite texto livre fora da janela de 24h de atendimento).

    `parametros_corpo` preenche as variáveis posicionais {{1}}, {{2}}... do
    corpo do template, na ordem.
    """
    components = []
    if parametros_corpo:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": str(p)} for p in parametros_corpo],
        })
    resp = requests.post(
        f"{_base_url()}/{phone_number_id}/messages",
        headers=_headers(token),
        json={
            "messaging_product": "whatsapp",
            "to": numero_e164,
            "type": "template",
            "template": {
                "name": nome_template,
                "language": {"code": idioma},
                **({"components": components} if components else {}),
            },
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def listar_templates(token: str, waba_id: str) -> list[dict]:
    """Lista os templates cadastrados na conta (com status de aprovação)."""
    resp = requests.get(
        f"{_base_url()}/{waba_id}/message_templates",
        headers=_headers(token),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def criar_template(
    token: str, waba_id: str, nome_meta: str, categoria: str, idioma: str,
    corpo: str, cabecalho: str = "", rodape: str = "",
) -> dict:
    """
    Envia um template pra aprovação da Meta. `nome_meta` deve ser único,
    minúsculo e com underscore (ex: "confirmacao_pedido"). Retorna o
    template criado com status PENDING — a aprovação demora minutos a
    algumas horas e precisa ser conferida depois via obter_template().
    """
    components = [{"type": "BODY", "text": corpo}]
    if cabecalho:
        components.insert(0, {"type": "HEADER", "format": "TEXT", "text": cabecalho})
    if rodape:
        components.append({"type": "FOOTER", "text": rodape})
    resp = requests.post(
        f"{_base_url()}/{waba_id}/message_templates",
        headers=_headers(token),
        json={
            "name": nome_meta,
            "category": categoria,
            "language": idioma,
            "components": components,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def obter_template(token: str, meta_template_id: str) -> dict:
    """Consulta o status atual (PENDING/APPROVED/REJECTED) de um template pelo ID retornado na criação."""
    resp = requests.get(
        f"{_base_url()}/{meta_template_id}",
        headers=_headers(token),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
