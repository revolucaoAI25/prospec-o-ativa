"""
Módulo de busca/enriquecimento via CNPJ.

Oferece duas funcionalidades:
1. buscar_por_cnae() — busca empresas pelo código CNAE usando o dataset
   público do Brasil.io (advogados = CNAE 6911-7/01).
   Requer token do Brasil.io (gratuito, basta criar conta).

2. enriquecer_com_cnpj() — dado um CNPJ, busca dados completos via
   BrasilAPI (100% gratuito, sem autenticação).

CNAE de advocacia:
  6911-7/01  Serviços advocatícios
  6911-7/02  Atividades auxiliares da justiça
  6912-5/00  Cartórios
"""

import os
import time
import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()

BRASILAPI_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
BRASILIO_URL = "https://brasil.io/api/dataset/socios-brasil/empresas/data/"

CNAE_ADVOCACIA = "6911701"  # Remove pontos/barras para a API


def buscar_por_cnae(
    cnae: str = CNAE_ADVOCACIA,
    municipio: str = "",
    uf: str = "",
    limite: int = 100,
    token_brasilio: str = None,
) -> list[dict]:
    """
    Busca empresas pelo código CNAE no dataset do Brasil.io.
    Requer token gratuito em: https://brasil.io/auth/tokens-api/

    Parâmetros:
        cnae       - Código CNAE sem pontuação (padrão: 6911701 = advocacia)
        municipio  - Nome do município em maiúsculas (ex: "SAO PAULO")
        uf         - Sigla do estado (ex: "SP")
        limite     - Máximo de registros a retornar
        token_brasilio - Token da API do Brasil.io
    """
    if token_brasilio is None:
        token_brasilio = os.getenv("BRASILIO_TOKEN", "")

    if not token_brasilio:
        console.print(
            "[yellow]Aviso: BRASILIO_TOKEN não configurado. "
            "Crie uma conta gratuita em https://brasil.io/auth/tokens-api/ "
            "e adicione ao .env[/yellow]"
        )
        return []

    headers = {"Authorization": f"Token {token_brasilio}"}
    resultados = []
    url = BRASILIO_URL
    params = {
        "cnae_fiscal": cnae,
        "situacao_cadastral": "ATIVA",
        "page_size": min(100, limite),
    }
    if municipio:
        params["municipio"] = municipio.upper()
    if uf:
        params["uf"] = uf.upper()

    console.print(f"\n[bold cyan]Buscando CNPJ por CNAE:[/bold cyan] {cnae}")
    if municipio:
        console.print(f"[dim]Município: {municipio} | UF: {uf}[/dim]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Buscando no Brasil.io...", total=None)

        while url and len(resultados) < limite:
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=20)
                resp.raise_for_status()
            except requests.HTTPError as e:
                if resp.status_code == 401:
                    console.print("[red]Token inválido. Verifique BRASILIO_TOKEN no .env[/red]")
                else:
                    console.print(f"[red]Erro na API Brasil.io: {e}[/red]")
                break

            data = resp.json()
            for empresa in data.get("results", []):
                if len(resultados) >= limite:
                    break
                resultados.append({
                    "nome": empresa.get("razao_social", ""),
                    "cnpj": empresa.get("cnpj", ""),
                    "telefone": _formatar_telefone(
                        empresa.get("ddd_telefone_1", ""),
                        empresa.get("telefone_1", "")
                    ),
                    "telefone2": _formatar_telefone(
                        empresa.get("ddd_telefone_2", ""),
                        empresa.get("telefone_2", "")
                    ),
                    "email": empresa.get("correio_eletronico", ""),
                    "endereco": _montar_endereco(empresa),
                    "municipio": empresa.get("municipio", ""),
                    "uf": empresa.get("uf", ""),
                    "cep": empresa.get("cep", ""),
                    "situacao": empresa.get("situacao_cadastral", ""),
                    "porte": empresa.get("porte", ""),
                    "data_abertura": empresa.get("data_inicio_atividade", ""),
                    "fonte": "CNPJ/Brasil.io",
                })

            url = data.get("next")
            params = {}  # próxima página já vem com todos os params na URL
            progress.update(task, description=f"Encontrados {len(resultados)} registros...")
            time.sleep(0.3)

    console.print(f"[bold green]✓[/bold green] {len(resultados)} empresas encontradas via CNPJ.")
    return resultados


def enriquecer_com_cnpj(cnpj: str) -> dict | None:
    """
    Busca dados completos de um CNPJ específico via BrasilAPI.
    Gratuito, sem autenticação necessária.

    Retorna dict com dados da empresa ou None se não encontrado.
    """
    cnpj_limpo = "".join(c for c in cnpj if c.isdigit())
    if len(cnpj_limpo) != 14:
        return None

    try:
        url = BRASILAPI_URL.format(cnpj=cnpj_limpo)
        resp = requests.get(url, timeout=15)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        return {
            "nome": data.get("razao_social", ""),
            "nome_fantasia": data.get("nome_fantasia", ""),
            "cnpj": data.get("cnpj", ""),
            "telefone": data.get("ddd_telefone_1", "") + data.get("telefone", ""),
            "email": data.get("email", ""),
            "endereco": _montar_endereco_brasilapi(data),
            "municipio": data.get("municipio", ""),
            "uf": data.get("uf", ""),
            "cep": data.get("cep", ""),
            "situacao": data.get("descricao_situacao_cadastral", ""),
            "data_abertura": data.get("data_inicio_atividade", ""),
            "porte": data.get("descricao_porte", ""),
            "fonte": "BrasilAPI",
        }
    except requests.RequestException:
        return None


def _formatar_telefone(ddd: str, numero: str) -> str:
    ddd = (ddd or "").strip()
    numero = (numero or "").strip()
    if not numero:
        return ""
    if ddd:
        return f"({ddd}) {numero}"
    return numero


def _montar_endereco(empresa: dict) -> str:
    partes = [
        empresa.get("descricao_tipo_logradouro", ""),
        empresa.get("logradouro", ""),
        empresa.get("numero", ""),
        empresa.get("complemento", ""),
        empresa.get("bairro", ""),
    ]
    return ", ".join(p for p in partes if p)


def _montar_endereco_brasilapi(data: dict) -> str:
    partes = [
        data.get("logradouro", ""),
        data.get("numero", ""),
        data.get("complemento", ""),
        data.get("bairro", ""),
    ]
    return ", ".join(p for p in partes if p)
