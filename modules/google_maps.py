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
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()

PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

# Campos buscados nos detalhes — só pague pelo que usa
DETAIL_FIELDS = (
    "name,"
    "formatted_phone_number,"
    "international_phone_number,"
    "formatted_address,"
    "website,"
    "url,"
    "business_status,"
    "rating,"
    "user_ratings_total,"
    "opening_hours"
)


def _text_search(query: str, api_key: str, page_token: str = None) -> dict:
    params = {
        "query": query,
        "language": "pt-BR",
        "key": api_key,
    }
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
    data = resp.json()
    return data.get("result", {})


def buscar_escritorios(
    cidade: str,
    estado: str = "",
    termo_extra: str = "",
    limite: int = 60,
    api_key: str = None,
) -> list[dict]:
    """
    Busca escritórios de advocacia no Google Maps e retorna lista de dicionários.

    Parâmetros:
        cidade      - Nome da cidade (ex: "São Paulo")
        estado      - Sigla do estado (ex: "SP") — opcional
        termo_extra - Especialidade adicional (ex: "trabalhista", "tributário")
        limite      - Número máximo de resultados (máx 60 por busca)
        api_key     - Chave da Google Maps API (usa GOOGLE_MAPS_API_KEY do .env se omitido)

    Retorna lista de dicts com: nome, telefone, telefone_internacional,
    endereco, site, maps_url, avaliacao, total_avaliacoes, status
    """
    if api_key is None:
        api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")

    if not api_key:
        raise ValueError(
            "Chave da API do Google Maps não encontrada.\n"
            "Configure GOOGLE_MAPS_API_KEY no arquivo .env ou passe api_key=..."
        )

    localidade = cidade
    if estado:
        localidade = f"{cidade}, {estado}"

    base_query = f"escritório de advocacia {termo_extra} em {localidade}".strip()

    console.print(f"\n[bold cyan]Buscando:[/bold cyan] {base_query}")
    console.print(f"[dim]Limite: {limite} resultados[/dim]\n")

    place_ids = []
    page_token = None

    # Coleta place_ids (cada página retorna até 20)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Buscando páginas de resultados...", total=None)
        while len(place_ids) < limite:
            try:
                data = _text_search(base_query, api_key, page_token)
            except requests.HTTPError as e:
                console.print(f"[red]Erro na busca: {e}[/red]")
                break

            status = data.get("status")
            if status == "ZERO_RESULTS":
                console.print("[yellow]Nenhum resultado encontrado para essa busca.[/yellow]")
                break
            if status not in ("OK", "ZERO_RESULTS"):
                console.print(f"[red]Erro da API: {status} — {data.get('error_message', '')}[/red]")
                break

            for place in data.get("results", []):
                if len(place_ids) >= limite:
                    break
                place_ids.append(place["place_id"])

            page_token = data.get("next_page_token")
            if not page_token:
                break

            # Google exige ~2s entre páginas com next_page_token
            time.sleep(2)
            progress.update(task, description=f"Encontrados {len(place_ids)} lugares...")

    console.print(f"[green]✓[/green] {len(place_ids)} lugares encontrados. Buscando detalhes...")

    resultados = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Buscando detalhes...", total=len(place_ids))
        for i, pid in enumerate(place_ids):
            try:
                det = _get_details(pid, api_key)
            except requests.HTTPError as e:
                console.print(f"[yellow]Aviso: erro ao buscar detalhes de {pid}: {e}[/yellow]")
                progress.advance(task)
                continue

            resultado = {
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
            }
            resultados.append(resultado)
            progress.advance(task)

            # Evita rate limit
            time.sleep(0.1)

    com_telefone = sum(1 for r in resultados if r["telefone"])
    console.print(
        f"\n[bold green]✓ Concluído![/bold green] "
        f"{len(resultados)} resultados, "
        f"[cyan]{com_telefone}[/cyan] com telefone."
    )
    return resultados
