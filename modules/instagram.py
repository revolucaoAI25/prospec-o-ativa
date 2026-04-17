"""
Módulo de extração de leads via Instagram — integração com Apify.

Extrai seguidores de perfis públicos ou comentaristas de publicações,
retornando username + ID numérico (necessário para disparo via API).

Requisito: chave Apify (api.apify.com) configurada pelo admin ou pelo usuário.
"""

from __future__ import annotations
import time
import logging
import requests
from typing import Callable, Optional

logger = logging.getLogger(__name__)

APIFY_BASE                = "https://api.apify.com/v2"
ACTOR_FOLLOWERS_FOLLOWING = "scraping_solutions~instagram-scraper-followers-following-no-cookies"
ACTOR_COMMENTS            = "louisdeconinck~instagram-comments-scraper"

# Timeout máximo (segundos) aguardando o Apify concluir o job
RUN_TIMEOUT = 420


# ── Comunicação com Apify ─────────────────────────────────────────────────────

def _iniciar_run(api_key: str, actor_id: str, input_data: dict) -> tuple[str, str]:
    """Inicia um Apify actor run. Retorna (run_id, dataset_id)."""
    resp = requests.post(
        f"{APIFY_BASE}/acts/{actor_id}/runs",
        params={"token": api_key},
        json=input_data,
        timeout=30,
    )
    if not resp.ok:
        # Inclui o corpo do erro para facilitar diagnóstico
        try:
            detalhe = resp.json().get("error", {}).get("message", resp.text[:300])
        except Exception:
            detalhe = resp.text[:300]
        raise RuntimeError(f"Apify {resp.status_code}: {detalhe}")
    data = resp.json()["data"]
    return data["id"], data["defaultDatasetId"]


def _aguardar_run(api_key: str, run_id: str, callback: Optional[Callable] = None) -> None:
    """Aguarda o run terminar, lançando exceção se falhar."""
    deadline = time.time() + RUN_TIMEOUT
    tentativa = 0
    while time.time() < deadline:
        time.sleep(min(8 + tentativa * 2, 20))
        tentativa += 1
        resp = requests.get(
            f"{APIFY_BASE}/actor-runs/{run_id}",
            params={"token": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        status = resp.json()["data"]["status"]
        if callback:
            callback(0, 1, f"Apify: {status.lower()}… ({tentativa * 10}s)")
        if status == "SUCCEEDED":
            return
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise RuntimeError(f"Apify encerrou com status: {status}")
    raise TimeoutError(f"Apify não respondeu em {RUN_TIMEOUT}s. Tente com menos resultados.")


def _obter_items(api_key: str, dataset_id: str, limite: int) -> list[dict]:
    """Baixa itens do dataset resultante."""
    resp = requests.get(
        f"{APIFY_BASE}/datasets/{dataset_id}/items",
        params={"token": api_key, "format": "json", "limit": limite},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json() or []


# ── Normalização de resultados ────────────────────────────────────────────────

def _normalizar_perfil(item: dict, tipo: str) -> Optional[dict]:
    """
    Converte um item Apify para o dict padrão da plataforma.
    Retorna None se não houver username nem ID.
    """
    # IDs e usernames têm nomes diferentes por actor
    insta_id = str(
        item.get("id") or item.get("pk") or
        item.get("ownerUserId") or item.get("owner_id") or ""
    ).strip()
    username = str(
        item.get("username") or item.get("ownerUsername") or
        item.get("owner_username") or ""
    ).strip().lstrip("@")

    if not username and not insta_id:
        return None

    nome_exibicao = f"@{username}" if username else insta_id
    nome_completo = str(item.get("full_name") or item.get("ownerFullName") or "").strip()
    bio       = str(item.get("biography") or item.get("bio") or "").strip()
    website   = str(item.get("external_url") or item.get("externalUrl") or item.get("website") or "").strip()
    email     = str(item.get("public_email") or item.get("publicEmail") or item.get("email") or "").strip()
    followers = int(item.get("followers_count") or item.get("followersCount") or 0)
    is_biz    = bool(item.get("is_business_account") or item.get("isBusinessAccount") or False)
    comentario = str(item.get("text") or "") if tipo == "comentaristas" else ""

    return {
        "instagram_id":    insta_id,
        "username":        f"@{username}" if username else "",
        "nome":            nome_exibicao,
        "nome_completo":   nome_completo,
        "bio":             bio[:500],
        "site":            website,
        "email":           email,
        "followers_count": followers,
        "is_business":     is_biz,
        "comentario":      comentario[:300],
        "maps_url":        f"https://www.instagram.com/{username}/" if username else "",
        "nicho_busca":     "Instagram",
        "subnicho_busca":  {"seguidores": "Seguidor", "seguindo": "Following"}.get(tipo, "Comentarista"),
        "cidade_busca":    "",
        "estado_busca":    "",
        "fonte":           "instagram",
    }


# ── Função pública ────────────────────────────────────────────────────────────

def buscar(
    apify_api_key: str,
    tipo: str,
    alvo: str,
    limite: int = 200,
    progress_callback: Optional[Callable] = None,
    exclude_ids: Optional[set] = None,
) -> list[dict]:
    """
    Extrai seguidores de um perfil ou comentaristas de uma publicação.

    tipo: "seguidores" | "comentaristas"
    alvo: username (sem @) OU URL da publicação do Instagram
    limite: máximo de resultados retornados
    progress_callback: callable(atual, total, mensagem)
    exclude_ids: set de instagram_id já vistos (deduplicação)

    Retorna lista de dicts no formato padrão da plataforma.
    """
    if not apify_api_key:
        raise ValueError("Chave Apify não configurada. Acesse Configurações → Instagram.")

    alvo = alvo.strip().lstrip("@")

    def _cb(a, t, msg):
        if progress_callback:
            progress_callback(a, t, msg)

    _cb(0, 1, "Preparando extração…")

    if tipo in ("seguidores", "seguindo"):
        # Extrai username puro a partir de URL ou handle
        if alvo.startswith("http"):
            username = alvo.rstrip("/").split("/")[-1]
        else:
            username = alvo.lstrip("@")
        actor_id   = ACTOR_FOLLOWERS_FOLLOWING
        input_data = {
            "Account":      [username],
            "resultsLimit": limite,
            "dataToScrape": "Followers" if tipo == "seguidores" else "Following",
        }
    elif tipo == "comentaristas":
        url = (alvo if alvo.startswith("http")
               else f"https://www.instagram.com/p/{alvo}/")
        actor_id   = ACTOR_COMMENTS
        input_data = {
            "urls":        [url],
            "maxComments": limite * 3,
        }
    else:
        raise ValueError(f"Tipo inválido: {tipo!r}. Use 'seguidores', 'seguindo' ou 'comentaristas'.")

    _cb(0, 1, "Iniciando job no Apify…")
    run_id, dataset_id = _iniciar_run(apify_api_key, actor_id, input_data)
    logger.info("Instagram buscar: run_id=%s actor=%s tipo=%s alvo=%s", run_id, actor_id, tipo, alvo)

    _aguardar_run(apify_api_key, run_id, callback=progress_callback)

    _cb(0, 1, "Baixando resultados…")
    raw_items = _obter_items(apify_api_key, dataset_id, limite * 3)
    logger.info("Instagram: %d itens brutos recebidos", len(raw_items))

    # Normalizar, dedup por instagram_id/username e respeitar limite
    vistos:  set[str] = set(exclude_ids or [])
    ignorados = 0
    resultados: list[dict] = []

    for item in raw_items:
        if len(resultados) >= limite:
            break
        r = _normalizar_perfil(item, tipo)
        if not r:
            continue
        # Chave de dedup: prefere ID numérico, usa username como fallback
        dedup_key = r["instagram_id"] or r["username"]
        if dedup_key and dedup_key in vistos:
            ignorados += 1
            continue
        if dedup_key:
            vistos.add(dedup_key)
        resultados.append(r)

    if ignorados:
        logger.info("Instagram: %d duplicatas ignoradas", ignorados)
        _cb(1, 1, f"{len(resultados)} novos leads ({ignorados} duplicatas ignoradas)")
    else:
        _cb(1, 1, f"{len(resultados)} leads extraídos")

    return resultados
