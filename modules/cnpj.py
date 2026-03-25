"""
Módulo de enriquecimento via CNPJ individual.

Usa a BrasilAPI (100% gratuita, sem autenticação) para buscar dados
completos de um CNPJ específico quando você já tem o número.

Para busca em massa por CNAE, use modules/receita_federal.py.

CNAE de advocacia:
  6911701  Serviços advocatícios
  6911702  Atividades auxiliares da justiça
  6912500  Cartórios
"""

import requests
from rich.console import Console

console = Console()

BRASILAPI_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"


def enriquecer_com_cnpj(cnpj: str) -> dict | None:
    """
    Busca dados completos de um CNPJ via BrasilAPI.
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

        ddd = data.get("ddd_telefone_1", "").strip()
        tel = data.get("telefone", "").strip()
        telefone = f"({ddd}) {tel}" if ddd and tel else tel or ddd

        return {
            "nome": data.get("razao_social", ""),
            "nome_fantasia": data.get("nome_fantasia", ""),
            "cnpj": data.get("cnpj", ""),
            "telefone": telefone,
            "email": data.get("email", ""),
            "endereco": _montar_endereco(data),
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


def _montar_endereco(data: dict) -> str:
    partes = [
        data.get("logradouro", ""),
        data.get("numero", ""),
        data.get("complemento", ""),
        data.get("bairro", ""),
    ]
    return ", ".join(p for p in partes if p)
