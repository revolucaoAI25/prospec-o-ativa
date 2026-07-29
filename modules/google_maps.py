"""
Módulo de busca via Google Maps Places API (legada).

Custo por SKU (API Places legada):
  - Text Search:    Pro  — 5.000 gratuitas/mês, depois US$32/1.000
  - Place Details:  Pro  — 5.000 gratuitas/mês, depois US$17/1.000
  - Contact Data:   Enterprise — 1.000 gratuitas/mês (telefone + site)
  - Atmosphere Data: nunca cobrado aqui — rating vem do Text Search (Essentials, grátis)

Estratégia de custo:
  - rating/user_ratings_total são obtidos do Text Search (sem custo Enterprise)
  - Place Details é chamado apenas quando show_phone=True (Contact Data)
  - Com show_phone=False: apenas Text Search → 5.000 gratuitas/mês
  - Com show_phone=True:  Text Search + Details + Contact Data → 1.000 gratuitas/mês
"""

import time
import os
import random
import requests
from typing import Callable, Optional

PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"


class QuotaExceededError(RuntimeError):
    """Raised when the Google Maps API daily quota is exhausted (OVER_QUERY_LIMIT)."""
PLACES_DETAILS_URL     = "https://maps.googleapis.com/maps/api/place/details/json"

# Campos de detalhe — sem rating/user_ratings_total (vêm do Text Search de graça)
DETAIL_FIELDS = (
    "name,formatted_phone_number,international_phone_number,"
    "formatted_address,website,url,business_status"
)


def _apenas_digitos(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())

# Variações usadas quando a busca tem uma CIDADE específica — bairros/zonas
# são um conceito de cidade, então só fazem sentido nesse caso.
_MODIFICADORES_CIDADE = [
    "",
    "centro",
    "zona norte",
    "zona sul",
    "zona leste",
    "zona oeste",
    "região central",
    "região metropolitana",
    "bairros",
    "periferia",
    "centro histórico",
    "arredores",
]

# Variações usadas quando a busca é só por ESTADO (sem cidade) — termos que
# fazem sentido numa escala estadual, não zonas de bairro.
_MODIFICADORES_ESTADO = [
    "",
    "capital",
    "interior",
    "litoral",
    "região metropolitana",
    "norte",
    "sul",
]


def _text_search(query: str, api_key: str, page_token: str = None) -> dict:
    if page_token:
        # Google exige que pagetoken seja enviado sozinho (sem query/language)
        params = {"pagetoken": page_token, "key": api_key}
    else:
        params = {"query": query, "language": "pt-BR", "key": api_key}
    resp = requests.get(PLACES_TEXT_SEARCH_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _get_details(place_id: str, api_key: str) -> dict:
    params = {
        "place_id": place_id,
        "fields":   DETAIL_FIELDS,
        "language": "pt-BR",
        "key":      api_key,
    }
    resp = requests.get(PLACES_DETAILS_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("result", {})


def _coletar_places_uma_query(query: str, api_key: str, log: Callable) -> list[dict]:
    """Coleta candidatos de UMA única query de texto (até 3 páginas / ~60 resultados)."""
    places: list[dict] = []
    page_token = None
    paginas = 0

    while paginas < 3:
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
        if status == "OVER_QUERY_LIMIT":
            raise QuotaExceededError(
                "Cota diária da API Google Maps esgotada."
            )
        if status == "INVALID_REQUEST":
            # Geralmente ocorre quando o page_token ainda não está pronto
            # ou a requisição tem parâmetros inválidos — encerra esta página
            break
        if status != "OK":
            raise RuntimeError(
                f"Erro da API: {status} — {data.get('error_message', '')}"
            )

        for place in data.get("results", []):
            places.append({
                "place_id":            place["place_id"],
                "nome":                place.get("name", ""),
                "endereco":            place.get("formatted_address", ""),
                "avaliacao":           place.get("rating", ""),
                "total_avaliacoes":    place.get("user_ratings_total", ""),
                "status_funcionamento": place.get("business_status", ""),
            })

        page_token = data.get("next_page_token")
        paginas += 1
        if not page_token:
            break
        time.sleep(2)

    return places


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
    """
    Busca numa única localidade (cidade+estado, ou só estado). Uso interno de buscar().

    Cada modificador (variação de bairro/zona/região) é tentado UM DE CADA
    VEZ, resolvendo telefone e checando duplicata do histórico ANTES de
    decidir se precisa do próximo — em vez de coletar de antemão um "pool"
    de candidatos com base numa estimativa de quantos seriam necessários
    (o que fazia buscas recorrentes numa cidade já bastante explorada
    desistirem cedo demais: os primeiros modificadores sorteados traziam
    quase só candidatos já vistos, mas como isso só era descoberto DEPOIS
    de já ter parado de coletar mais, os modificadores seguintes — que
    poderiam ter leads novos de verdade — nunca chegavam a ser tentados).
    Agora só passa pro próximo modificador quando o atual não bastou.
    """
    nicho_query = f"{query_base} {subnicho.lower()}".strip() if subnicho else query_base

    # Zonas de bairro (centro, zona norte...) só existem numa cidade — pra
    # busca por estado inteiro usam-se termos de escala estadual (litoral,
    # interior, capital...), senão vira "centro do estado" sem sentido.
    modificadores = _MODIFICADORES_CIDADE if cidade else _MODIFICADORES_ESTADO

    # Embaralha a ordem (menos o "" sem modificador, que sempre roda primeiro
    # por ser a busca mais confiável). Sem isso, buscas com poucas variações
    # sempre pegavam as mesmas primeiras da lista e nunca chegavam nas
    # últimas — resultado repetitivo em buscas sucessivas na mesma cidade.
    _mods = list(modificadores)
    if _mods and _mods[0] == "":
        _resto = _mods[1:]
        random.shuffle(_resto)
        _mods = [""] + _resto
    else:
        random.shuffle(_mods)

    log(0, limite, f"Coletando resultados para: {nicho_query} em {localidade}")

    resultados: list[dict] = []
    pulados = 0
    vistos_pid: set[str] = set()

    for mod in _mods:
        if len(resultados) >= limite:
            break

        query = f"{nicho_query} em {mod} de {localidade}" if mod else f"{nicho_query} em {localidade}"
        log(len(resultados), limite, f"Buscando: {query}")
        places_mod = _coletar_places_uma_query(query, api_key, log)

        for p in places_mod:
            if len(resultados) >= limite:
                break

            pid = p["place_id"]
            if pid in vistos_pid:
                continue
            vistos_pid.add(pid)

            telefone = ""
            tel_int  = ""
            site     = ""
            endereco = p["endereco"]
            maps_url = f"https://www.google.com/maps/place/?q=place_id:{pid}"

            if show_phone:
                try:
                    det      = _get_details(pid, api_key)
                    telefone = det.get("formatted_phone_number", "")
                    tel_int  = det.get("international_phone_number", "")
                    site     = det.get("website", "")
                    maps_url = det.get("url") or maps_url
                    endereco = det.get("formatted_address") or endereco
                except requests.HTTPError:
                    pass

            if exclude_phones and telefone and _apenas_digitos(telefone) in exclude_phones:
                pulados += 1
                log(len(resultados), limite,
                    f"{'Detalhes' if show_phone else 'Resultados'}: "
                    f"{len(resultados)}/{limite} (pulados {pulados} repetidos)")
                if show_phone:
                    time.sleep(0.1)
                continue

            resultados.append({
                "nome":                   p["nome"],
                "telefone":               telefone,
                "telefone_internacional": tel_int,
                "endereco":               endereco,
                "site":                   site,
                "maps_url":               maps_url,
                "avaliacao":              p["avaliacao"] if show_rating else "",
                "total_avaliacoes":       p["total_avaliacoes"] if show_rating else "",
                "status_funcionamento":   p["status_funcionamento"],
                "nicho_busca":            nicho,
                "subnicho_busca":         subnicho,
                "cidade_busca":           cidade,
                "estado_busca":           estado,
                "fonte":                  "Google Maps",
            })

            log(len(resultados), limite,
                f"{'Detalhes' if show_phone else 'Resultados'}: {len(resultados)}/{limite}")
            if show_phone:
                time.sleep(0.1)

    sufixo = f" ({pulados} repetidos ignorados)" if pulados else ""
    log(len(resultados), limite, f"'{localidade}': {len(resultados)} resultados{sufixo}.")
    return resultados


def buscar(
    query_base: str,
    localidade,
    limite: int = 60,
    api_key: str = None,
    nicho: str = "",
    subnicho: str = "",
    cidade: str = "",
    estado: str = "",
    progress_callback: Callable[[int, int, str], None] = None,
    exclude_phones: set = None,
    show_phone: bool = True,
    show_rating: bool = True,
) -> list[dict]:
    """
    Busca estabelecimentos no Google Maps e retorna lista de dicts.

    `localidade` aceita uma string única ("São Paulo, SP" ou só "SP") OU uma
    lista de strings — nesse caso cada localidade é buscada e os resultados
    são mesclados e deduplicados por telefone entre si, respeitando `limite`
    no total (não por localidade).

    show_phone  — busca telefone e site via Place Details (Contact Data, 1.000 gratuitas/mês)
    show_rating — inclui avaliação nos resultados (vem do Text Search, sempre gratuito)

    Com show_phone=False: apenas Text Search → 5.000 resultados gratuitos/mês.
    Com show_phone=True:  Text Search + Place Details → 1.000 resultados gratuitos/mês.
    """
    if api_key is None:
        api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        raise ValueError(
            "Chave da API do Google Maps não encontrada.\n"
            "Configure GOOGLE_MAPS_API_KEY no .env ou nos Secrets do Streamlit."
        )

    localidades = localidade if isinstance(localidade, list) else [localidade]
    localidades = [l.strip() for l in localidades if l and l.strip()]
    if not localidades:
        raise ValueError("Informe ao menos uma cidade ou estado.")

    def log(atual, total, msg):
        if progress_callback:
            progress_callback(atual, total, msg)
        else:
            print(msg)

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
        # 1ª passada: cota igual pra cada localidade, pra garantir que TODAS
        # sejam pesquisadas — sem isso, a primeira localidade da lista podia
        # sozinha preencher o limite todo e as outras nunca eram buscadas.
        cota_base = max(1, limite // len(localidades))
        for idx, loc in enumerate(localidades):
            if len(resultados) >= limite:
                break
            log(len(resultados), limite, f"[{idx+1}/{len(localidades)}] Buscando em {loc}…")
            _buscar_loc(loc, min(cota_base, limite - len(resultados)))

        # 2ª passada: sobrou vaga (alguma localidade rendeu menos que a cota)?
        # completa nas mesmas localidades, na ordem, até atingir o limite.
        for loc in localidades:
            if len(resultados) >= limite:
                break
            _buscar_loc(loc, limite - len(resultados))
    else:
        _buscar_loc(localidades[0], limite)

    sufixo = f" ({len(localidades)} localidades)" if multiplas else ""
    log(len(resultados), limite, f"Concluído: {len(resultados)} resultados{sufixo}.")
    return resultados[:limite]


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


def enriquecer_com_maps(
    resultados: list[dict],
    api_key: str,
    progress_callback: Callable = None,
    show_phone: bool = True,
    show_rating: bool = True,
) -> list[dict]:
    """
    Enriquece cada empresa com dados do Google Maps.
    show_phone=True  → busca telefone/site via Place Details (Contact Data)
    show_rating=True → inclui avaliação (vem do Text Search, sempre gratuito)
    Não sobrescreve campos já preenchidos pelo CNPJ.
    """
    total = len(resultados)

    def _cb(i, msg):
        if progress_callback:
            progress_callback(i, total, msg)

    for i, r in enumerate(resultados):
        nome      = (r.get("nome") or "").strip()
        municipio = (r.get("municipio") or r.get("cidade_busca") or "").strip()
        uf        = (r.get("uf") or r.get("estado_busca") or "").strip()

        _cb(i, f"[{i+1}/{total}] {nome[:45]}…")

        if not nome:
            continue

        query = f"{nome} {municipio} {uf}".strip()
        try:
            resp = _text_search(query, api_key)
            if resp.get("status") != "OK" or not resp.get("results"):
                continue

            place = resp["results"][0]
            pid   = place.get("place_id", "")

            # Avaliação do Text Search — sem custo Enterprise
            if show_rating:
                if place.get("rating") is not None:
                    r["avaliacao"] = place["rating"]
                if place.get("user_ratings_total") is not None:
                    r["total_avaliacoes"] = place["user_ratings_total"]

            # Maps URL básica (funciona sem Details)
            if pid and not r.get("maps_url"):
                r["maps_url"] = f"https://www.google.com/maps/place/?q=place_id:{pid}"

            # Place Details: apenas se show_phone=True
            if pid and show_phone:
                det = _get_details(pid, api_key)
                if det.get("url"):
                    r["maps_url"] = det["url"]

                tel = det.get("formatted_phone_number") or det.get("international_phone_number") or ""
                if tel:
                    if not r.get("telefone"):
                        r["telefone"] = tel
                    elif _apenas_digitos(r.get("telefone")) != _apenas_digitos(tel) and not r.get("telefone2"):
                        r["telefone2"] = tel

                if det.get("website") and not r.get("site"):
                    r["site"] = det["website"]

        except Exception:
            pass

        time.sleep(0.05)

    _cb(total, "Enriquecimento concluído!")
    return resultados
