"""
Busca via Apify Google Maps Scraper (compass/crawler-google-places).
Usado como fallback quando a cota do Google Maps API é excedida
ou quando não há chave do Google Maps configurada.
Custo: $4 / 1.000 lugares.
"""

import time
import requests
from typing import Callable, Optional

_ACTOR_ID = "compass~crawler-google-places"
_BASE      = "https://api.apify.com/v2"


def _apenas_digitos(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def _iniciar_run(token: str, payload: dict) -> tuple[str, str]:
    """Inicia o run e retorna (run_id, dataset_id)."""
    resp = requests.post(
        f"{_BASE}/acts/{_ACTOR_ID}/runs",
        json=payload,
        params={"token": token},
        timeout=60,
    )
    if not resp.ok:
        body = resp.text[:300]
        if resp.status_code == 401:
            raise ValueError("Token Apify inválido. Verifique a chave em Configurações.")
        raise RuntimeError(f"Apify retornou {resp.status_code}: {body}")
    data = resp.json()["data"]
    return data["id"], data["defaultDatasetId"]


def _aguardar_run(token: str, run_id: str, timeout: int, log_fn: Callable) -> None:
    """Polling até o run terminar ou timeout."""
    url = f"{_BASE}/actor-runs/{run_id}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(url, params={"token": token}, timeout=30)
        resp.raise_for_status()
        status = resp.json()["data"]["status"]
        if status == "SUCCEEDED":
            return
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise RuntimeError(f"Run Apify encerrado com status: {status}")
        log_fn(0, 1, f"[Apify] Aguardando… ({status})")
        time.sleep(5)
    raise RuntimeError("Timeout aguardando resultado do Apify (>10 min).")


def _buscar_items(token: str, dataset_id: str) -> list[dict]:
    resp = requests.get(
        f"{_BASE}/datasets/{dataset_id}/items",
        params={"token": token, "format": "json", "clean": "true"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


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
    """
    if not api_key:
        raise ValueError("Chave de API do Apify não configurada.")

    def log(a, t, msg):
        if progress_callback:
            progress_callback(a, t, msg)

    query = f"{query_base} {subnicho}".strip() if subnicho else query_base
    log(0, limite, f"[Apify] Iniciando busca: {query} em {localidade}…")

    payload = {
        "searchStringsArray":        [query],
        "locationQuery":             localidade,
        "maxCrawledPlacesPerSearch": limite,
    }

    run_id, dataset_id = _iniciar_run(api_key, payload)
    log(0, limite, "[Apify] Run iniciado. Aguardando resultados…")

    _aguardar_run(api_key, run_id, timeout=600, log_fn=log)
    log(0, limite, "[Apify] Coletando resultados…")

    items = _buscar_items(api_key, dataset_id)

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

        if exclude_phones and tel and _apenas_digitos(tel) in exclude_phones:
            continue

        resultados.append({
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
        })
        log(len(resultados), limite, f"[Apify] {len(resultados)}/{limite}")

    log(limite, limite, f"[Apify] Concluído: {len(resultados)} resultados.")
    return resultados
