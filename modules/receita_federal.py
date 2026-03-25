"""
Módulo de busca direta nos dados abertos da Receita Federal.

A Receita Federal disponibiliza os dados completos do CNPJ para download
público e gratuito, sem necessidade de conta ou autenticação.

Fonte oficial: https://dadosabertos.rfb.gov.br/CNPJ/

Os arquivos de Estabelecimentos contêm:
  - CNPJ completo
  - Razão social / nome fantasia
  - Telefones (DDD + número)
  - E-mail
  - Endereço completo
  - UF, município, CEP
  - CNAE principal
  - Situação cadastral

Os arquivos têm ~350 MB cada compactado. O módulo faz download e filtra
em modo streaming (sem guardar o arquivo completo em memória), salva um
cache local e não precisa baixar de novo enquanto o cache for recente.

CNAE de advocacia: 6911701
"""

import os
import io
import csv
import json
import zipfile
import hashlib
import requests
import time
from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, TextColumn,
    BarColumn, DownloadColumn, TransferSpeedColumn,
)

console = Console()

# ── Configuração ─────────────────────────────────────────────────────────────

RF_BASE_URL = "https://dadosabertos.rfb.gov.br/CNPJ"
NUM_SHARDS = 10          # arquivos Estabelecimentos0.zip … Estabelecimentos9.zip
CNAE_ADVOCACIA = "6911701"
CACHE_DIR = Path(".cache_rf")
CACHE_VALIDADE_DIAS = 30  # reusa o cache por 30 dias

# Colunas dos arquivos de Estabelecimentos (ordem oficial da RF)
COLUNAS_ESTAB = [
    "cnpj_basico",        # 8 dígitos
    "cnpj_ordem",         # 4 dígitos
    "cnpj_dv",            # 2 dígitos
    "identificador",      # 1=Matriz, 2=Filial
    "nome_fantasia",
    "situacao_cadastral", # 01=Nula, 02=Ativa, 03=Suspensa, 04=Inapta, 08=Baixada
    "data_situacao",
    "motivo_situacao",
    "nome_cidade_exterior",
    "pais",
    "data_inicio",
    "cnae_principal",
    "cnae_secundario",
    "tipo_logradouro",
    "logradouro",
    "numero",
    "complemento",
    "bairro",
    "cep",
    "uf",
    "municipio_cod",      # código IBGE (resolvido depois)
    "ddd1",
    "telefone1",
    "ddd2",
    "telefone2",
    "ddd_fax",
    "fax",
    "email",
    "situacao_especial",
    "data_situacao_especial",
]

# Mapa de municípios RF (código → nome)
_municipios: dict[str, str] = {}


def _carregar_municipios() -> dict[str, str]:
    """Baixa e parseia o arquivo de municípios da RF (pequeno, ~1 MB)."""
    global _municipios
    if _municipios:
        return _municipios

    cache_path = CACHE_DIR / "municipios.json"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        _municipios = json.loads(cache_path.read_text(encoding="utf-8"))
        return _municipios

    console.print("[dim]Baixando tabela de municípios da Receita Federal...[/dim]")
    try:
        resp = requests.get(f"{RF_BASE_URL}/Municipios.zip", timeout=60, stream=True)
        resp.raise_for_status()
        buf = io.BytesIO(resp.content)
        with zipfile.ZipFile(buf) as zf:
            nome_csv = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
            with zf.open(nome_csv) as f:
                reader = csv.reader(
                    io.TextIOWrapper(f, encoding="latin-1"),
                    delimiter=";",
                )
                for row in reader:
                    if len(row) >= 2:
                        _municipios[row[0].strip()] = row[1].strip().title()
    except Exception as e:
        console.print(f"[yellow]Aviso: não foi possível carregar municípios: {e}[/yellow]")
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
    progress=None,
    task_id=None,
) -> list[dict]:
    """Baixa um shard em streaming, filtra por UF + CNAE e retorna registros."""

    cache = _cache_path(shard, uf, cnae)
    if _cache_valido(cache):
        dados = json.loads(cache.read_text(encoding="utf-8"))
        if progress and task_id is not None:
            progress.advance(task_id)
        return dados

    url = f"{RF_BASE_URL}/Estabelecimentos{shard}.zip"

    try:
        resp = requests.get(url, stream=True, timeout=300)
        resp.raise_for_status()
    except requests.RequestException as e:
        console.print(f"[yellow]Shard {shard}: erro ao baixar ({e})[/yellow]")
        return []

    tamanho_total = int(resp.headers.get("content-length", 0))
    buf = io.BytesIO()
    baixados = 0

    for chunk in resp.iter_content(chunk_size=1024 * 512):  # 512 KB por chunk
        buf.write(chunk)
        baixados += len(chunk)
        if progress and task_id is not None and tamanho_total:
            progress.update(task_id, completed=baixados, total=tamanho_total)

    buf.seek(0)
    resultados = []
    municipios = _carregar_municipios()

    with zipfile.ZipFile(buf) as zf:
        nome_csv = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        with zf.open(nome_csv) as f:
            reader = csv.reader(
                io.TextIOWrapper(f, encoding="latin-1"),
                delimiter=";",
            )
            for row in reader:
                if len(row) < len(COLUNAS_ESTAB):
                    continue
                rec = dict(zip(COLUNAS_ESTAB, row))

                # Filtros
                if rec["uf"].upper() != uf.upper():
                    continue
                if rec["cnae_principal"].strip() != cnae:
                    continue
                if rec["situacao_cadastral"].strip() != "02":  # 02 = Ativa
                    continue
                if municipio_cod and rec["municipio_cod"].strip() != municipio_cod:
                    continue

                cnpj = rec["cnpj_basico"] + rec["cnpj_ordem"] + rec["cnpj_dv"]
                tel1 = _fmt_tel(rec["ddd1"], rec["telefone1"])
                tel2 = _fmt_tel(rec["ddd2"], rec["telefone2"])
                nome_mun = municipios.get(rec["municipio_cod"].strip(), rec["municipio_cod"])

                resultados.append({
                    "nome": rec["nome_fantasia"].strip().title() or "",
                    "cnpj": cnpj,
                    "telefone": tel1,
                    "telefone2": tel2,
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

    if progress and task_id is not None:
        progress.advance(task_id)

    return resultados


def buscar_por_cnae_rf(
    uf: str,
    municipio: str = "",
    cnae: str = CNAE_ADVOCACIA,
    limite: int = 500,
    callback_progresso=None,
) -> list[dict]:
    """
    Busca escritórios de advocacia nos dados abertos da Receita Federal.

    Parâmetros:
        uf         - Sigla do estado (ex: "SP")
        municipio  - Nome do município (ex: "São Paulo") — opcional
        cnae       - Código CNAE (padrão: 6911701 = advocacia)
        limite     - Número máximo de resultados
        callback_progresso - função(atual, total, mensagem) para UI externas

    Retorna lista de dicts com: nome, cnpj, telefone, email, endereço, etc.

    NOTA: O primeiro uso baixa os arquivos da RF (~350 MB por shard).
          Os resultados filtrados ficam em cache por 30 dias.
    """
    uf = uf.upper().strip()
    municipio = municipio.strip()

    # Resolve código do município se fornecido
    mun_cod = ""
    if municipio:
        municipios = _carregar_municipios()
        municipio_upper = municipio.upper()
        for cod, nome in municipios.items():
            if nome.upper() == municipio_upper:
                mun_cod = cod
                break
        if not mun_cod:
            console.print(
                f"[yellow]Município '{municipio}' não encontrado na tabela RF. "
                f"Buscando em todo o estado {uf}.[/yellow]"
            )

    console.print(
        f"\n[bold cyan]Buscando na Receita Federal:[/bold cyan] "
        f"CNAE {cnae} | UF: {uf}"
        + (f" | Município: {municipio}" if municipio else "")
    )
    console.print(
        "[dim]Os arquivos serão baixados uma vez e ficam em cache por 30 dias.[/dim]\n"
    )

    todos = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        console=console,
        transient=False,
    ) as progress:
        tasks = []
        for i in range(NUM_SHARDS):
            t = progress.add_task(f"Shard {i}", total=None, start=False)
            tasks.append(t)

        for i in range(NUM_SHARDS):
            if len(todos) >= limite:
                break

            cache = _cache_path(i, uf, cnae)
            if _cache_valido(cache):
                descricao = f"Shard {i} (cache local)"
            else:
                descricao = f"Shard {i} — baixando da Receita Federal..."

            progress.start_task(tasks[i])
            progress.update(tasks[i], description=descricao)

            parcial = _baixar_e_filtrar_shard(
                shard=i,
                uf=uf,
                cnae=cnae,
                municipio_cod=mun_cod,
                progress=progress,
                task_id=tasks[i],
            )
            todos.extend(parcial)

            if callback_progresso:
                callback_progresso(
                    i + 1,
                    NUM_SHARDS,
                    f"Shard {i+1}/10 — {len(todos)} encontrados até agora",
                )

            progress.update(
                tasks[i],
                description=f"Shard {i} ✓ ({len(parcial)} registros)",
                completed=1,
                total=1,
            )

    resultado_final = todos[:limite]
    com_tel = sum(1 for r in resultado_final if r.get("telefone"))

    console.print(
        f"\n[bold green]✓ Concluído![/bold green] "
        f"{len(resultado_final)} escritórios encontrados "
        f"([cyan]{com_tel}[/cyan] com telefone)."
    )
    return resultado_final


def _fmt_tel(ddd: str, numero: str) -> str:
    ddd = (ddd or "").strip()
    numero = (numero or "").strip()
    if not numero:
        return ""
    if ddd:
        return f"({ddd}) {numero}"
    return numero


def _fmt_end(rec: dict) -> str:
    partes = [
        rec.get("tipo_logradouro", ""),
        rec.get("logradouro", ""),
        rec.get("numero", ""),
        rec.get("complemento", ""),
        rec.get("bairro", ""),
    ]
    return ", ".join(p.strip() for p in partes if p.strip())
