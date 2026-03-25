"""
Módulo de exportação para Google Sheets via Service Account.

Como configurar (uma única vez):
  1. No Google Cloud Console, crie um Service Account no mesmo projeto da Maps API
  2. Gere uma chave JSON para o Service Account
  3. Copie o conteúdo JSON inteiro e cole em Streamlit Secrets como GOOGLE_SERVICE_ACCOUNT
  4. Compartilhe sua planilha Google com o e-mail do Service Account (com permissão de editor)
  5. Configure a URL da planilha e o nome da aba nas configurações do app

O Service Account funciona como um "robô" que escreve na sua planilha sem
precisar de login interativo — ideal para automações.
"""

import json
from typing import Optional

try:
    import gspread
    from google.oauth2.service_account import Credentials
    _GSPREAD_OK = True
except ImportError:
    _GSPREAD_OK = False

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

COLUNAS_EXPORT = [
    ("nome",                   "Nome"),
    ("telefone",               "Telefone"),
    ("telefone2",              "Telefone 2"),
    ("email",                  "E-mail"),
    ("endereco",               "Endereço"),
    ("municipio",              "Município"),
    ("uf",                     "UF"),
    ("cep",                    "CEP"),
    ("site",                   "Site"),
    ("maps_url",               "Google Maps"),
    ("avaliacao",              "Avaliação"),
    ("total_avaliacoes",       "Nº Avaliações"),
    ("cnpj",                   "CNPJ"),
    ("nicho_busca",            "Nicho"),
    ("subnicho_busca",         "Subnicho"),
    ("cidade_busca",           "Cidade Buscada"),
    ("estado_busca",           "Estado Buscado"),
    ("fonte",                  "Fonte"),
]


def gspread_disponivel() -> bool:
    return _GSPREAD_OK


def _conectar(service_account_json: str) -> "gspread.Client":
    if not _GSPREAD_OK:
        raise ImportError("gspread não instalado. Execute: pip install gspread google-auth")
    info = json.loads(service_account_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def testar_conexao(service_account_json: str, sheet_url: str) -> tuple[bool, str]:
    """
    Testa se o Service Account consegue acessar a planilha.
    Retorna (sucesso, mensagem).
    """
    try:
        client = _conectar(service_account_json)
        sheet = client.open_by_url(sheet_url)
        return True, f"✅ Conectado: '{sheet.title}'"
    except json.JSONDecodeError:
        return False, "❌ JSON do Service Account inválido. Verifique o conteúdo em Secrets."
    except Exception as e:
        msg = str(e)
        if "PERMISSION_DENIED" in msg or "403" in msg:
            return False, "❌ Sem permissão. Compartilhe a planilha com o e-mail do Service Account."
        if "404" in msg or "not found" in msg.lower():
            return False, "❌ Planilha não encontrada. Verifique a URL."
        return False, f"❌ Erro: {msg}"


def exportar(
    resultados: list[dict],
    service_account_json: str,
    sheet_url: str,
    aba_nome: str = "Prospecção",
    modo: str = "substituir",
) -> tuple[bool, str]:
    """
    Exporta resultados para o Google Sheets.

    Parâmetros:
        resultados          - Lista de dicts com os dados
        service_account_json - JSON do Service Account (string)
        sheet_url           - URL completa da planilha Google
        aba_nome            - Nome da aba onde escrever
        modo                - "substituir" (apaga e reescreve) ou "acrescentar"

    Retorna (sucesso, mensagem).
    """
    if not resultados:
        return False, "Nenhum resultado para exportar."

    try:
        client = _conectar(service_account_json)
        sheet = client.open_by_url(sheet_url)
    except Exception as e:
        return False, f"Erro ao conectar: {e}"

    # Abre ou cria a aba
    try:
        ws = sheet.worksheet(aba_nome)
    except Exception:
        ws = sheet.add_worksheet(title=aba_nome, rows=len(resultados) + 10, cols=len(COLUNAS_EXPORT) + 2)

    cabecalho = [label for _, label in COLUNAS_EXPORT]
    linhas_novas = [[str(r.get(col, "") or "") for col, _ in COLUNAS_EXPORT] for r in resultados]

    try:
        if modo == "substituir":
            ws.clear()
            ws.update([cabecalho] + linhas_novas)
            # Formata cabeçalho em negrito
            try:
                ws.format("1:1", {"textFormat": {"bold": True}})
            except Exception:
                pass
        else:  # acrescentar
            existentes = ws.get_all_values()
            if not existentes:
                ws.update([cabecalho] + linhas_novas)
            else:
                ws.append_rows(linhas_novas)

        total = len(linhas_novas)
        return True, f"✅ {total} registros exportados para '{aba_nome}' em '{sheet.title}'"

    except Exception as e:
        return False, f"Erro ao escrever na planilha: {e}"


def obter_email_service_account(service_account_json: str) -> Optional[str]:
    """Extrai o e-mail do Service Account do JSON para exibir ao usuário."""
    try:
        info = json.loads(service_account_json)
        return info.get("client_email", "")
    except Exception:
        return None
