"""
Busca via Apify Google Maps Scraper (compass/crawler-google-places).
Usado como fallback quando a cota do Google Maps API é excedida
ou quando não há chave do Google Maps configurada.
Custo: $4 / 1.000 lugares.
"""

import random
import time
import requests
from typing import Callable, Optional

from .google_maps import _MODIFICADORES_CIDADE, _MODIFICADORES_ESTADO

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


def _montar_variacoes(query_base: str, subnicho: str, cidade: str) -> list[str]:
    """
    Monta variações da busca acrescentando modificadores geográficos ao texto
    (ex: "advogado centro", "advogado zona norte") — a localização em si vai
    à parte, em `locationQuery`. A ordem é embaralhada a cada chamada (exceto
    a variação sem modificador, que sempre roda primeiro) pra que buscas
    repetidas na mesma localidade não fiquem presas às mesmas 2-3 primeiras
    variações quando `limite` é pequeno.
    """
    query = f"{query_base} {subnicho}".strip() if subnicho else query_base
    mods = list(_MODIFICADORES_CIDADE if cidade else _MODIFICADORES_ESTADO)
    resto = mods[1:]
    random.shuffle(resto)
    mods = ([mods[0]] + resto)[:3]
    return [f"{query} {m}".strip() if m else query for m in mods]


def _buscar_uma_localidade(
    query_base: str,
    localidade: str,
    limite: int,
    api_key: str,
    nicho: str,
    subnicho: str,
    cidade: str,
    estado: str,
    log: Callable,
    exclude_phones: set,
    show_phone: bool,
    show_rating: bool,
) -> list[dict]:
    search_strings = _montar_variacoes(query_base, subnicho, cidade)
    cota_por_variacao = max(1, -(-limite // len(search_strings)))
    log(0, limite, f"[Apify] Iniciando busca: {len(search_strings)} variações em {localidade}…")

    payload = {
        "searchStringsArray":        search_strings,
        "locationQuery":             localidade,
        "maxCrawledPlacesPerSearch": cota_por_variacao,
    }

    run_id, dataset_id = _iniciar_run(api_key, payload)
    log(0, limite, "[Apify] Run iniciado. Aguardando resultados…")

    _aguardar_run(api_key, run_id, timeout=600, log_fn=log)
    log(0, limite, "[Apify] Coletando resultados…")

    items = _buscar_items(api_key, dataset_id)

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

    log(len(resultados), limite, f"[Apify] '{localidade}': {len(resultados)} resultados.")
    return resultados


def buscar(
    query_base: str,
    localidade,
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

    `localidade` aceita uma string única ou uma lista de strings — nesse
    caso roda um run do Apify por localidade e mescla os resultados,
    deduplicados por telefone, respeitando `limite` no total.
    """
    if not api_key:
        raise ValueError("Chave de API do Apify não configurada.")

    localidades = localidade if isinstance(localidade, list) else [localidade]
    localidades = [l.strip() for l in localidades if l and l.strip()]
    if not localidades:
        raise ValueError("Informe ao menos uma cidade ou estado.")

    def log(a, t, msg):
        if progress_callback:
            progress_callback(a, t, msg)

    vistos_tel = set(exclude_phones or [])
    resultados: list[dict] = []
    multiplas = len(localidades) > 1

    def _localizar(loc: str) -> tuple[str, str]:
        if not multiplas and (cidade or estado):
            return cidade, estado
        if "," in loc:
            partes = [p.strip() for p in loc.split(",", 1)]
            return partes[0], partes[1]
        return "", loc

    def _buscar_loc(loc: str, cota: int) -> None:
        if cota <= 0:
            return
        _cidade_loc, _estado_loc = _localizar(loc)
        parcial = _buscar_uma_localidade(
            query_base=query_base, localidade=loc, limite=cota, api_key=api_key,
            nicho=nicho, subnicho=subnicho, cidade=_cidade_loc, estado=_estado_loc,
            log=log, exclude_phones=vistos_tel, show_phone=show_phone, show_rating=show_rating,
        )
        for r in parcial:
            tel_d = _apenas_digitos(r.get("telefone", ""))
            if tel_d:
                vistos_tel.add(tel_d)
        resultados.extend(parcial)

    if multiplas:
        # 1ª passada: cota igual pra cada localidade, garante que todas sejam
        # pesquisadas (senão a primeira da lista podia preencher tudo sozinha).
        cota_base = max(1, limite // len(localidades))
        for idx, loc in enumerate(localidades):
            if len(resultados) >= limite:
                break
            log(len(resultados), limite, f"[Apify] [{idx+1}/{len(localidades)}] Buscando em {loc}…")
            _buscar_loc(loc, min(cota_base, limite - len(resultados)))

        # 2ª passada: completa a vaga que sobrou nas mesmas localidades.
        for loc in localidades:
            if len(resultados) >= limite:
                break
            _buscar_loc(loc, limite - len(resultados))
    else:
        _buscar_loc(localidades[0], limite)

    log(len(resultados), limite, f"[Apify] Concluído: {len(resultados)} resultados.")
    return resultados[:limite]
