"""
Módulo de busca via Google Maps Places API.

Para superar o limite de 60 resultados por consulta do Google, o módulo
realiza múltiplas buscas com variações de localidade (zonas da cidade,
bairros, etc.) e deduplica os resultados pelo place_id.

Custo estimado (2026):
  - Text Search:   US$ 0,032 por página
  - Place Details: US$ 0,017 por resultado
  - Crédito gratuito do Google: US$ 200/mês (~5.000 buscas completas)
"""

import time
import os
import requests
from typing import Callable

PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL     = "https://maps.googleapis.com/maps/api/place/details/json"

DETAIL_FIELDS = (
    "name,formatted_phone_number,international_phone_number,"
    "formatted_address,website,url,business_status,rating,user_ratings_total"
)

# Modificadores geográficos usados para ampliar resultados além de 60
_MODIFICADORES = [
    "",
    "centro",
    "zona norte",
    "zona sul",
    "zona leste",
    "zona oeste",
    "região metropolitana",
    "bairros",
    "norte",
    "sul",
]


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


def _coletar_place_ids(
    query_base: str,
    api_key: str,
    limite: int,
    log: Callable,
) -> list[str]:
    """
    Coleta place_ids até atingir o limite, usando múltiplas queries se necessário.
    Deduplica automaticamente.
    """
    vistos: set[str] = set()
    place_ids: list[str] = []

    # Quantas queries rodar? Cada query retorna no máx 60.
    # Usamos modificadores geográficos para variar os resultados.
    max_queries = min(len(_MODIFICADORES), -(-limite // 60))  # ceil(limite/60)

    for mod_idx in range(max_queries):
        if len(place_ids) >= limite:
            break

        mod = _MODIFICADORES[mod_idx]
        query = f"{query_base} {mod}".strip() if mod else query_base
        log(0, 0, f"Buscando: {query}")

        page_token = None
        paginas = 0

        while len(place_ids) < limite and paginas < 3:
            try:
                data = _text_search(query, api_key, page_token)
            except requests.HTTPError as e:
                log(0, 0, f"Erro na busca: {e}")
                break

            status = data.get("status")
            if status == "ZERO_RESULTS":
                break
            if status == "REQUEST_DENIED":
                raise ValueError(
                    f"API negou o acesso: {data.get('error_message', '')}.\n"
                    "Verifique se a chave está correta e se a Places API está ativada."
                )
            if status != "OK":
                raise RuntimeError(
                    f"Erro da API: {status} — {data.get('error_message', '')}"
                )

            for place in data.get("results", []):
                pid = place["place_id"]
                if pid not in vistos:
                    vistos.add(pid)
                    place_ids.append(pid)

            page_token = data.get("next_page_token")
            paginas += 1
            if not page_token:
                break
            time.sleep(2)  # Google exige ~2s entre páginas com next_page_token

    return place_ids[:limite]


def buscar(
    query_base: str,
    localidade: str,
    limite: int = 60,
    api_key: str = None,
    nicho: str = "",
    subnicho: str = "",
    cidade: str = "",
    estado: str = "",
    progress_callback: Callable[[int, int, str], None] = None,
    exclude_phones: set = None,
) -> list[dict]:
    """
    Busca estabelecimentos no Google Maps e retorna lista de dicts.

    Parâmetros:
        query_base        - Termo principal (ex: "escritório de advocacia")
        localidade        - Cidade e/ou estado (ex: "São Paulo, SP")
        limite            - Máx de resultados únicos a retornar
        api_key           - Chave da Google Maps API
        nicho/subnicho    - Metadados para incluir nos resultados
        cidade/estado     - Metadados para incluir nos resultados
        progress_callback - função(atual, total, msg) para atualizar UI
        exclude_phones    - Set de telefones já vistos; duplicatas são puladas e
                            a busca continua até completar `limite` ou esgotar resultados
    """
    if api_key is None:
        api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        raise ValueError(
            "Chave da API do Google Maps não encontrada.\n"
            "Configure GOOGLE_MAPS_API_KEY no .env ou nos Secrets do Streamlit."
        )

    exclude_phones = exclude_phones or set()

    def log(atual, total, msg):
        if progress_callback:
            progress_callback(atual, total, msg)
        else:
            print(msg)

    query_completa = f"{query_base} em {localidade}"
    if subnicho:
        query_completa = f"{query_base} {subnicho.lower()} em {localidade}"

    # Se há deduplicação ativa, busca mais place_ids do que o limite pedido
    # para compensar as que serão descartadas por serem duplicatas.
    fetch_limit = limite if not exclude_phones else min(len(_MODIFICADORES) * 60, limite * 3)

    # ── Coleta place_ids ──────────────────────────────────────────────────────
    log(0, limite, f"Coletando resultados para: {query_completa}")
    place_ids = _coletar_place_ids(query_completa, api_key, fetch_limit, log)
    log(0, limite, f"{len(place_ids)} candidatos encontrados. Buscando detalhes...")

    # ── Busca detalhes, pulando duplicatas até completar a cota ───────────────
    resultados = []
    pulados = 0

    for pid in place_ids:
        if len(resultados) >= limite:
            break
        try:
            det = _get_details(pid, api_key)
        except requests.HTTPError:
            continue

        telefone = det.get("formatted_phone_number", "")
        if exclude_phones and telefone and telefone in exclude_phones:
            pulados += 1
            log(len(resultados), limite,
                f"Detalhes: {len(resultados)}/{limite} (pulados {pulados} repetidos)")
            time.sleep(0.1)
            continue

        resultados.append({
            "nome":                    det.get("name", ""),
            "telefone":                telefone,
            "telefone_internacional":  det.get("international_phone_number", ""),
            "endereco":                det.get("formatted_address", ""),
            "site":                    det.get("website", ""),
            "maps_url":                det.get("url", ""),
            "avaliacao":               det.get("rating", ""),
            "total_avaliacoes":        det.get("user_ratings_total", ""),
            "status_funcionamento":    det.get("business_status", ""),
            "nicho_busca":             nicho,
            "subnicho_busca":          subnicho,
            "cidade_busca":            cidade,
            "estado_busca":            estado,
            "fonte":                   "Google Maps",
        })

        log(len(resultados), limite, f"Detalhes: {len(resultados)}/{limite}")
        time.sleep(0.1)

    sufixo = f" ({pulados} repetidos ignorados)" if pulados else ""
    log(limite, limite, f"Concluído: {len(resultados)} resultados{sufixo}.")
    return resultados


# Mantém compatibilidade com código antigo
def buscar_escritorios(
    cidade: str = "",
    estado: str = "",
    termo_extra: str = "",
    limite: int = 60,
    api_key: str = None,
    progress_callback: Callable = None,
) -> list[dict]:
    localidade = f"{cidade}, {estado}" if cidade and estado else cidade or estado
    from modules.nichos import NICHOS
    query = NICHOS.get("Advogado / Escritório de Advocacia", {}).get("query", "escritório de advocacia")
    return buscar(
        query_base=query,
        localidade=localidade,
        limite=limite,
        api_key=api_key,
        subnicho=termo_extra,
        cidade=cidade,
        estado=estado,
        progress_callback=progress_callback,
    )
