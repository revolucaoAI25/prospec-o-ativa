#!/usr/bin/env python3
"""
Prospec-o-Ativa — Sistema de prospecção de escritórios de advocacia.

Uso rápido:
    python main.py maps --cidade "São Paulo" --estado SP
    python main.py maps --cidade "Curitiba" --limite 100 --especialidade "trabalhista"
    python main.py cnpj --municipio "SAO PAULO" --uf SP
    python main.py cnpj --uf RJ --limite 200
"""

import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# Carrega variáveis do .env automaticamente
load_dotenv()

console = Console()


def cmd_maps(args):
    """Busca via Google Maps Places API."""
    from modules.google_maps import buscar_escritorios
    from modules.export import exportar_csv, exportar_excel, mostrar_preview

    resultados = buscar_escritorios(
        cidade=args.cidade,
        estado=args.estado or "",
        termo_extra=args.especialidade or "",
        limite=args.limite,
    )

    if not resultados:
        console.print("[yellow]Nenhum resultado encontrado.[/yellow]")
        return

    mostrar_preview(resultados)

    cidade_slug = args.cidade
    if args.formato == "excel" or args.formato == "ambos":
        exportar_excel(resultados, cidade=cidade_slug, diretorio=args.saida)
    if args.formato == "csv" or args.formato == "ambos":
        exportar_csv(resultados, cidade=cidade_slug, diretorio=args.saida)


def cmd_cnpj(args):
    """Busca via CNPJ/Brasil.io por CNAE de advocacia."""
    from modules.cnpj import buscar_por_cnae
    from modules.export import exportar_csv, exportar_excel, mostrar_preview

    resultados = buscar_por_cnae(
        municipio=args.municipio or "",
        uf=args.uf or "",
        limite=args.limite,
    )

    if not resultados:
        console.print("[yellow]Nenhum resultado. Verifique o token Brasil.io no .env[/yellow]")
        return

    mostrar_preview(resultados)

    cidade_slug = args.municipio or args.uf or "brasil"
    if args.formato == "excel" or args.formato == "ambos":
        exportar_excel(resultados, cidade=cidade_slug, diretorio=args.saida)
    if args.formato == "csv" or args.formato == "ambos":
        exportar_csv(resultados, cidade=cidade_slug, diretorio=args.saida)


def cmd_enriquecer(args):
    """Enriquece um CSV existente com dados de CNPJ via BrasilAPI."""
    import csv
    from modules.cnpj import enriquecer_com_cnpj
    from modules.export import exportar_csv, exportar_excel
    from rich.progress import track

    if not Path(args.arquivo).exists():
        console.print(f"[red]Arquivo não encontrado: {args.arquivo}[/red]")
        sys.exit(1)

    with open(args.arquivo, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        linhas = list(reader)

    console.print(f"[cyan]Enriquecendo {len(linhas)} registros com BrasilAPI...[/cyan]")
    enriquecidos = []

    for linha in track(linhas, description="Consultando CNPJs..."):
        cnpj = linha.get("CNPJ", linha.get("cnpj", ""))
        if cnpj:
            dados = enriquecer_com_cnpj(cnpj)
            if dados:
                linha.update({k: v for k, v in dados.items() if not linha.get(k)})
        enriquecidos.append(linha)

    # Exporta resultado
    if args.formato in ("excel", "ambos"):
        exportar_excel(enriquecidos, cidade="enriquecido", diretorio=args.saida)
    if args.formato in ("csv", "ambos"):
        exportar_csv(enriquecidos, cidade="enriquecido", diretorio=args.saida)


def main():
    banner = Panel(
        "[bold blue]Prospec-o-Ativa[/bold blue]\n"
        "[dim]Sistema de prospecção de escritórios de advocacia[/dim]",
        expand=False,
    )
    console.print(banner)

    parser = argparse.ArgumentParser(
        description="Prospecção ativa de escritórios de advocacia",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main.py maps --cidade "São Paulo" --estado SP
  python main.py maps --cidade "Belo Horizonte" --limite 100 --especialidade "tributário"
  python main.py cnpj --municipio "CURITIBA" --uf PR
  python main.py cnpj --uf SP --limite 500 --formato excel
  python main.py enriquecer --arquivo resultados/prospecao_sp.csv
        """,
    )

    subparsers = parser.add_subparsers(dest="comando", required=True)

    # ── Subcomando: maps ────────────────────────────────────────────────────
    maps_parser = subparsers.add_parser(
        "maps",
        help="Busca via Google Maps Places API (recomendado para telefones)",
    )
    maps_parser.add_argument(
        "--cidade", "-c", required=True,
        help='Nome da cidade. Ex: "São Paulo"',
    )
    maps_parser.add_argument(
        "--estado", "-e", default="",
        help='Sigla do estado. Ex: SP',
    )
    maps_parser.add_argument(
        "--especialidade", "-s", default="",
        help='Especialidade do escritório. Ex: "trabalhista", "tributário", "família"',
    )
    maps_parser.add_argument(
        "--limite", "-l", type=int, default=60,
        help="Número máximo de resultados (padrão: 60, máx: 60 por busca)",
    )
    maps_parser.add_argument(
        "--formato", "-f", default="ambos",
        choices=["csv", "excel", "ambos"],
        help="Formato de exportação (padrão: ambos)",
    )
    maps_parser.add_argument(
        "--saida", "-o", default="resultados",
        help='Diretório de saída (padrão: "resultados")',
    )
    maps_parser.set_defaults(func=cmd_maps)

    # ── Subcomando: cnpj ────────────────────────────────────────────────────
    cnpj_parser = subparsers.add_parser(
        "cnpj",
        help="Busca via CNPJ/Brasil.io por CNAE de advocacia (dados da Receita Federal)",
    )
    cnpj_parser.add_argument(
        "--municipio", "-m", default="",
        help='Nome do município em MAIÚSCULAS. Ex: "SAO PAULO"',
    )
    cnpj_parser.add_argument(
        "--uf", "-u", default="",
        help="Sigla do estado. Ex: SP",
    )
    cnpj_parser.add_argument(
        "--limite", "-l", type=int, default=100,
        help="Número máximo de resultados (padrão: 100)",
    )
    cnpj_parser.add_argument(
        "--formato", "-f", default="ambos",
        choices=["csv", "excel", "ambos"],
        help="Formato de exportação (padrão: ambos)",
    )
    cnpj_parser.add_argument(
        "--saida", "-o", default="resultados",
        help='Diretório de saída (padrão: "resultados")',
    )
    cnpj_parser.set_defaults(func=cmd_cnpj)

    # ── Subcomando: enriquecer ──────────────────────────────────────────────
    enr_parser = subparsers.add_parser(
        "enriquecer",
        help="Enriquece CSV existente com dados de CNPJ via BrasilAPI (gratuito)",
    )
    enr_parser.add_argument(
        "--arquivo", "-a", required=True,
        help="Caminho do CSV a enriquecer",
    )
    enr_parser.add_argument(
        "--formato", "-f", default="ambos",
        choices=["csv", "excel", "ambos"],
        help="Formato de exportação (padrão: ambos)",
    )
    enr_parser.add_argument(
        "--saida", "-o", default="resultados",
        help='Diretório de saída (padrão: "resultados")',
    )
    enr_parser.set_defaults(func=cmd_enriquecer)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
