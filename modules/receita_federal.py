"""
Módulo de busca direta nos dados abertos da Receita Federal.

A Receita Federal disponibiliza os dados completos do CNPJ para download
público e gratuito, sem necessidade de conta ou autenticação.

Fonte oficial: https://dadosabertos.rfb.gov.br/CNPJ/

Os arquivos de Estabelecimentos contêm:
  - CNPJ completo, Razão social / nome fantasia
  - Telefones (DDD + número), E-mail
  - Endereço completo, UF, município, CEP
  - CNAE principal, Situação cadastral

Os arquivos têm ~350 MB cada compactado. O módulo faz download e filtra
em modo streaming, salva cache local e não baixa de novo por 30 dias.

CNAE de advocacia: 6911701
"""

import os
import io
import csv
import json
import zipfile
import hashlib
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Callable

RF_BASE_URL = "https://dadosabertos.rfb.gov.br/CNPJ"
NUM_SHARDS = 10
CNAE_ADVOCACIA = "6911701"
CACHE_DIR = Path(".cache_rf")
CACHE_VALIDADE_DIAS = 30

COLUNAS_ESTAB = [
    "cnpj_basico", "cnpj_ordem", "cnpj_dv", "identificador",
    "nome_fantasia", "situacao_cadastral", "data_situacao",
    "motivo_situacao", "nome_cidade_exterior", "pais", "data_inicio",
    "cnae_principal", "cnae_secundario", "tipo_logradouro", "logradouro",
    "numero", "complemento", "bairro", "cep", "uf", "municipio_cod",
    "ddd1", "telefone1", "ddd2", "telefone2", "ddd_fax", "fax",
    "email", "situacao_especial", "data_situacao_especial",
]

_municipios: dict[str, str] = {}


def _log(msg: str, callback: Callable = None):
    if callback:
        callback(0, 0, msg)
    else:
        print(msg)


def _carregar_municipios(callback: Callable = None) -> dict[str, str]:
    global _municipios
    if _municipios:
        return _municipios

    cache_path = CACHE_DIR / "municipios.json"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        _municipios = json.loads(cache_path.read_text(encoding="utf-8"))
        return _municipios

    _log("Baixando tabela de municípios...", callback)
    try:
        resp = requests.get(f"{RF_BASE_URL}/Municipios.zip", timeout=60, stream=True)
        resp.raise_for_status()
        buf = io.BytesIO(resp.content)
        with zipfile.ZipFile(buf) as zf:
            nome_csv = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
            with zf.open(nome_csv) as f:
                for row in csv.reader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"):
                    if len(row) >= 2:
                        _municipios[row[0].strip()] = row[1].strip().title()
    except Exception as e:
        _log(f"Aviso: não foi possível carregar municípios: {e}", callback)
        _municipios = {}

    if _municipios:
        cache_path.write_text(json.dumps(_municipios, ensure_ascii=False), encoding="utf-8")
    return _municipios


def _cache_path(shard: int, uf: str, cnae: str) -> Path:
    chave = f"estab_{shard}_{uf.upper()}_{cnae}"
    h = hashlib.md5(chave.encode()).hexdigest()[:8]
    return CACHE_DIR / f"{chave}_{h}.json"


def _cache_valido(path: Path) -> bool:
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return datetime.now() - mtime < timedelta(days=CACHE_VALIDADE_DIAS)


def _baixar_e_filtrar_shard(
    shard: int,
    uf: str,
    cnae: str,
    municipio_cod: str = "",
    download_callback: Callable = None,
) -> list[dict]:
    """Baixa um shard em streaming, filtra por UF + CNAE e retorna registros."""

    cache = _cache_path(shard, uf, cnae)
    if _cache_valido(cache):
        return json.loads(cache.read_text(encoding="utf-8"))

    url = f"{RF_BASE_URL}/Estabelecimentos{shard}.zip"

    try:
        resp = requests.get(url, stream=True, timeout=600)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Shard {shard}: erro ao baixar ({e})")
        return []

    tamanho_total = int(resp.headers.get("content-length", 0))
    buf = io.BytesIO()
    baixados = 0

    for chunk in resp.iter_content(chunk_size=1024 * 512):
        buf.write(chunk)
        baixados += len(chunk)
        if download_callback and tamanho_total:
            pct = baixados / tamanho_total
            mb = baixados / 1024 / 1024
            total_mb = tamanho_total / 1024 / 1024
            download_callback(pct, f"Baixando shard {shard}: {mb:.0f} MB / {total_mb:.0f} MB")

    buf.seek(0)
    municipios = _carregar_municipios()
    resultados = []

    with zipfile.ZipFile(buf) as zf:
        nome_csv = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        with zf.open(nome_csv) as f:
            for row in csv.reader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"):
                if len(row) < len(COLUNAS_ESTAB):
                    continue
                rec = dict(zip(COLUNAS_ESTAB, row))

                if rec["uf"].upper() != uf.upper():
                    continue
                if rec["cnae_principal"].strip() != cnae:
                    continue
                if rec["situacao_cadastral"].strip() != "02":
                    continue
                if municipio_cod and rec["municipio_cod"].strip() != municipio_cod:
                    continue

                cnpj = rec["cnpj_basico"] + rec["cnpj_ordem"] + rec["cnpj_dv"]
                nome_mun = municipios.get(rec["municipio_cod"].strip(), rec["municipio_cod"])

                resultados.append({
                    "nome": rec["nome_fantasia"].strip().title() or "",
                    "cnpj": cnpj,
                    "telefone": _fmt_tel(rec["ddd1"], rec["telefone1"]),
                    "telefone2": _fmt_tel(rec["ddd2"], rec["telefone2"]),
                    "email": rec["email"].strip().lower(),
                    "endereco": _fmt_end(rec),
                    "municipio": nome_mun,
                    "uf": rec["uf"].upper(),
                    "cep": rec["cep"].strip(),
                    "data_abertura": rec["data_inicio"].strip(),
                    "fonte": "Receita Federal (dados abertos)",
                })

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(resultados, ensure_ascii=False), encoding="utf-8")
    return resultados


def buscar_por_cnae_rf(
    uf: str,
    municipio: str = "",
    cnae: str = CNAE_ADVOCACIA,
    limite: int = 500,
    callback_progresso: Callable[[int, int, str], None] = None,
) -> list[dict]:
    """
    Busca escritórios de advocacia nos dados abertos da Receita Federal.

    Parâmetros:
        uf                 - Sigla do estado (ex: "SP")
        municipio          - Nome do município (ex: "São Paulo") — opcional
        cnae               - Código CNAE (padrão: 6911701 = advocacia)
        limite             - Número máximo de resultados
        callback_progresso - função(atual, total, mensagem) para atualizar UI

    Retorna lista de dicts com: nome, cnpj, telefone, email, endereço, etc.

    NOTA: O primeiro uso baixa os arquivos da RF (~350 MB por shard).
          Os resultados filtrados ficam em cache por 30 dias.
    """
    uf = uf.upper().strip()
    municipio = municipio.strip()

    def _cb(atual, total, msg):
        if callback_progresso:
            callback_progresso(atual, total, msg)
        else:
            print(msg)

    # Resolve código do município se fornecido
    mun_cod = ""
    if municipio:
        municipios = _carregar_municipios(lambda *_, **__: None)
        municipio_upper = municipio.upper()
        for cod, nome in municipios.items():
            if nome.upper() == municipio_upper:
                mun_cod = cod
                break
        if not mun_cod:
            _cb(0, 0, f"Município '{municipio}' não encontrado — buscando em todo {uf}.")

    todos = []

    for i in range(NUM_SHARDS):
        if len(todos) >= limite:
            break

        cache = _cache_path(i, uf, cnae)
        em_cache = _cache_valido(cache)

        if em_cache:
            msg = f"Shard {i+1}/{NUM_SHARDS}: usando cache local..."
        else:
            msg = f"Shard {i+1}/{NUM_SHARDS}: baixando da Receita Federal..."

        _cb(i, NUM_SHARDS, msg)

        def _dl_cb(pct, msg_dl, _shard=i):
            if callback_progresso:
                callback_progresso(
                    _shard + pct,
                    NUM_SHARDS,
                    msg_dl,
                )

        parcial = _baixar_e_filtrar_shard(
            shard=i,
            uf=uf,
            cnae=cnae,
            municipio_cod=mun_cod,
            download_callback=_dl_cb if not em_cache else None,
        )
        todos.extend(parcial)
        _cb(i + 1, NUM_SHARDS, f"Shard {i+1}/{NUM_SHARDS} ✓ — {len(todos)} encontrados")

    resultado_final = todos[:limite]
    _cb(NUM_SHARDS, NUM_SHARDS, f"Concluído: {len(resultado_final)} escritórios.")
    return resultado_final


def _fmt_tel(ddd: str, numero: str) -> str:
    ddd = (ddd or "").strip()
    numero = (numero or "").strip()
    if not numero:
        return ""
    return f"({ddd}) {numero}" if ddd else numero


def _fmt_end(rec: dict) -> str:
    partes = [
        rec.get("tipo_logradouro", ""), rec.get("logradouro", ""),
        rec.get("numero", ""), rec.get("complemento", ""), rec.get("bairro", ""),
    ]
    return ", ".join(p.strip() for p in partes if p.strip())
