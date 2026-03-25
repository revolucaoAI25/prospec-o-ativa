"""
Módulo de busca via Google Maps Places API.

Utiliza a API legada de Places (Text Search + Details) para buscar
escritórios de advocacia com nome, telefone, endereço e site.

Custo estimado (março 2026):
  - Text Search:   US$ 0,032 por requisição
  - Place Details: US$ 0,017 por requisição
  - Google oferece US$ 200/mês de crédito gratuito (~5.000 buscas)
"""

import time
import os
import requests
from typing import Callable

PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

DETAIL_FIELDS = (
    "name,"
    "formatted_phone_number,"
    "international_phone_number,"
    "formatted_address,"
    "website,"
    "url,"
    "business_status,"
    "rating,"
    "user_ratings_total"
)


def _text_search(query: str, api_key: str, page_token: str = None) -> dict:
    params = {"query": query, "language": "pt-BR", "key": api_key}
    if page_token:
        params["pagetoken"] = page_token
    resp = requests.get(PLACES_TEXT_SEARCH_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _get_details(place_id: str, api_key: str) -> dict:
    params = {
        "place_id": place_id,
        "fields": DETAIL_FIELDS,
        "language": "pt-BR",
        "key": api_key,
    }
    resp = requests.get(PLACES_DETAILS_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("result", {})


def buscar_escritorios(
    cidade: str,
    estado: str = "",
    termo_extra: str = "",
    limite: int = 60,
    api_key: str = None,
    progress_callback: Callable[[int, int, str], None] = None,
) -> list[dict]:
    """
    Busca escritórios de advocacia no Google Maps.

    Parâmetros:
        cidade           - Nome da cidade (ex: "São Paulo")
        estado           - Sigla do estado (ex: "SP")
        termo_extra      - Especialidade (ex: "trabalhista")
        limite           - Máximo de resultados (máx 60 por busca)
        api_key          - Chave da Google Maps API
        progress_callback - função(atual, total, mensagem) para atualizar UI

    Retorna lista de dicts com: nome, telefone, endereco, site, maps_url, etc.
    """
    if api_key is None:
        api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")

    if not api_key:
        raise ValueError(
            "Chave da API do Google Maps não encontrada.\n"
            "Configure GOOGLE_MAPS_API_KEY no arquivo .env ou nos Secrets do Streamlit."
        )

    localidade = f"{cidade}, {estado}" if estado else cidade
    query = f"escritório de advocacia {termo_extra} em {localidade}".strip()

    def _log(msg: str):
        if progress_callback:
            progress_callback(0, 0, msg)
        else:
            print(msg)

    _log(f"Buscando: {query}")

    # ── Coleta place_ids (até 3 páginas × 20 resultados) ─────────────────────
    place_ids = []
    page_token = None

    while len(place_ids) < limite:
        data = _text_search(query, api_key, page_token)
        status = data.get("status")

        if status == "ZERO_RESULTS":
            _log("Nenhum resultado encontrado.")
            break
        if status == "REQUEST_DENIED":
            raise ValueError(
                f"API negou o acesso: {data.get('error_message', '')}. "
                "Verifique se a chave está correta e se a Places API está ativada."
            )
        if status not in ("OK",):
            raise RuntimeError(f"Erro da API Google Maps: {status} — {data.get('error_message', '')}")

        for place in data.get("results", []):
            if len(place_ids) >= limite:
                break
            place_ids.append(place["place_id"])

        page_token = data.get("next_page_token")
        if not page_token:
            break

        time.sleep(2)  # Google exige ~2s entre páginas com page_token

    _log(f"{len(place_ids)} lugares encontrados. Buscando detalhes...")

    # ── Busca detalhes de cada lugar ──────────────────────────────────────────
    resultados = []
    total = len(place_ids)

    for i, pid in enumerate(place_ids):
        try:
            det = _get_details(pid, api_key)
        except requests.HTTPError:
            continue

        resultados.append({
            "nome": det.get("name", ""),
            "telefone": det.get("formatted_phone_number", ""),
            "telefone_internacional": det.get("international_phone_number", ""),
            "endereco": det.get("formatted_address", ""),
            "site": det.get("website", ""),
            "maps_url": det.get("url", ""),
            "avaliacao": det.get("rating", ""),
            "total_avaliacoes": det.get("user_ratings_total", ""),
            "status_funcionamento": det.get("business_status", ""),
            "cidade_busca": cidade,
            "estado_busca": estado,
            "termo_busca": termo_extra,
            "fonte": "Google Maps",
        })

        if progress_callback:
            progress_callback(i + 1, total, f"Buscando detalhes... {i + 1}/{total}")

        time.sleep(0.1)

    _log(f"Concluído: {len(resultados)} resultados.")
    return resultados
