"""
Busca via Apify Google Maps Scraper (compass/crawler-google-places).
Usado como fallback quando a cota do Google Maps API é excedida
ou quando não há chave do Google Maps configurada.
Custo: $4 / 1.000 lugares.
"""

import requests
from typing import Callable, Optional

_ACTOR_ID = "compass~crawler-google-places"
_SYNC_URL  = f"https://api.apify.com/v2/acts/{_ACTOR_ID}/run-sync-get-dataset-items"


def buscar(
    query_base: str,
    localidade: str,
    limite: int = 60,
    api_key: str = "",
    nicho: str = "",
    subnicho: str = "",
    cidade: str = "",
    estado: str = "",
    progress_callback: Optional[Callable] = None,
    exclude_phones: Optional[set] = None,
    show_phone: bool = True,
    show_rating: bool = True,
) -> list[dict]:
    """
    Busca lugares via Apify Google Maps Scraper.
    Retorna lista no mesmo formato que google_maps.buscar().

    show_phone=False  → omite telefone do resultado (Apify coleta mesmo assim, sem custo extra)
    show_rating=False → omite avaliação (idem)
    """
    if not api_key:
        raise ValueError("Chave de API do Apify não configurada.")

    def log(a, t, msg):
        if progress_callback:
            progress_callback(a, t, msg)

    query = f"{query_base} {subnicho}".strip() if subnicho else query_base
    log(0, limite, f"[Apify] Buscando: {query} em {localidade}…")

    payload = {
        "searchStringsArray":        [query],
        "locationQuery":             localidade,
        "maxCrawledPlacesPerSearch": limite,
        "language":                  "pt",
        "scrapeReviews":             False,
        "scrapeImageUrls":           False,
        "additionalInfo":            False,
    }

    try:
        resp = requests.post(
            _SYNC_URL,
            json=payload,
            params={"token": api_key, "format": "json", "memory": 1024},
            timeout=600,
        )
        resp.raise_for_status()
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else 0
        if status_code == 401:
            raise ValueError("Token Apify inválido. Verifique a chave em Configurações.")
        raise RuntimeError(f"Erro ao chamar Apify: {e}")

    items = resp.json()
    if not isinstance(items, list):
        raise RuntimeError(f"Resposta inesperada do Apify: {str(items)[:200]}")

    exclude_phones = exclude_phones or set()
    resultados = []

    for item in items:
        if len(resultados) >= limite:
            break

        status_func = (
            "CLOSED_PERMANENTLY"  if item.get("permanentlyClosed")
            else "CLOSED_TEMPORARILY" if item.get("temporarilyClosed")
            else "OPERATIONAL"
        )
        tel  = item.get("phone", "") or ""
        teli = item.get("phoneUnformatted", "") or ""

        if exclude_phones and tel and tel in exclude_phones:
            continue

        r = {
            "nome":                   item.get("title", ""),
            "telefone":               tel  if show_phone  else "",
            "telefone_internacional": teli if show_phone  else "",
            "endereco":               item.get("address", ""),
            "site":                   item.get("website") or "",
            "maps_url":               item.get("url", ""),
            "avaliacao":              item.get("totalScore", "")  if show_rating else "",
            "total_avaliacoes":       item.get("reviewsCount", "") if show_rating else "",
            "status_funcionamento":   status_func,
            "nicho_busca":            nicho,
            "subnicho_busca":         subnicho,
            "cidade_busca":           cidade,
            "estado_busca":           estado,
            "fonte":                  "Apify Maps",
        }
        resultados.append(r)
        log(len(resultados), limite, f"[Apify] {len(resultados)}/{limite}")

    log(limite, limite, f"[Apify] Concluído: {len(resultados)} resultados.")
    return resultados
