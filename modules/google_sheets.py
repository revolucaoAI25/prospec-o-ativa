"""
Módulo de integração com Google Sheets via OAuth2.

O usuário autentica com a própria conta Google, escolhe a planilha
desejada de uma lista e exporta sem precisar de Service Account.

Configuração necessária (Streamlit Secrets):
  GOOGLE_CLIENT_ID     = "..."
  GOOGLE_CLIENT_SECRET = "..."
  APP_URL              = "https://seu-app.streamlit.app"

No Google Cloud Console:
  1. Credenciais → Criar → ID do cliente OAuth 2.0 → Aplicativo da Web
  2. Origens JavaScript autorizadas: adicionar a URL do app
  3. URIs de redirecionamento autorizados: adicionar a URL do app
"""

import json
from typing import Optional

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    import gspread
    _OAUTH_OK = True
except ImportError:
    _OAUTH_OK = False

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Colunas exportadas para o Google Sheets
COLUNAS_EXPORT = [
    ("nome",             "Nome"),
    ("telefone",         "Telefone"),
    ("telefone2",        "Telefone 2"),
    ("email",            "E-mail"),
    ("endereco",         "Endereço"),
    ("municipio",        "Município"),
    ("uf",               "UF"),
    ("cep",              "CEP"),
    ("site",             "Site"),
    ("maps_url",         "Google Maps"),
    ("avaliacao",        "Avaliação"),
    ("total_avaliacoes", "Nº Avaliações"),
    ("cnpj",             "CNPJ"),
    ("nicho_busca",      "Nicho"),
    ("subnicho_busca",   "Subnicho"),
    ("cidade_busca",     "Cidade Buscada"),
    ("estado_busca",     "Estado Buscado"),
    ("fonte",            "Fonte"),
]


def oauth_disponivel() -> bool:
    return _OAUTH_OK


def _criar_flow(client_id: str, client_secret: str, redirect_uri: str) -> "Flow":
    config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }
    return Flow.from_client_config(config, scopes=SCOPES, redirect_uri=redirect_uri)


def gerar_url_auth(client_id: str, client_secret: str, redirect_uri: str) -> str:
    """Gera a URL de autorização com PKCE. Codifica credenciais + code_verifier no state."""
    import base64, json, os, hashlib

    # Gera PKCE manualmente para controlar o code_verifier
    code_verifier  = base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip("=")

    state = base64.urlsafe_b64encode(json.dumps({
        "cid": client_id,
        "cs":  client_secret,
        "ru":  redirect_uri,
        "cv":  code_verifier,
    }).encode()).decode().rstrip("=")

    flow = _criar_flow(client_id, client_secret, redirect_uri)
    url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
        state=state,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    return url


def extrair_credenciais_state(state: str) -> tuple[str, str, str, str]:
    """Decodifica client_id, client_secret, redirect_uri e code_verifier do state OAuth."""
    import base64, json
    try:
        padded = state + "=" * (-len(state) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        return data.get("cid",""), data.get("cs",""), data.get("ru",""), data.get("cv","")
    except Exception:
        return "", "", "", ""


def trocar_codigo(client_id: str, client_secret: str, redirect_uri: str,
                  code: str, code_verifier: str = "") -> dict:
    """Troca o código de autorização por credenciais OAuth."""
    flow = _criar_flow(client_id, client_secret, redirect_uri)
    fetch_kwargs: dict = {"code": code}
    if code_verifier:
        fetch_kwargs["code_verifier"] = code_verifier
    flow.fetch_token(**fetch_kwargs)
    creds = flow.credentials
    return {
        "token":         creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri":     creds.token_uri,
        "client_id":     creds.client_id,
        "client_secret": creds.client_secret,
        "scopes":        list(creds.scopes or []),
    }


def _creds_from_dict(d: dict) -> "Credentials":
    creds = Credentials(
        token=d["token"],
        refresh_token=d.get("refresh_token"),
        token_uri=d.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=d["client_id"],
        client_secret=d["client_secret"],
        scopes=d.get("scopes"),
    )
    # Sempre renova token — o campo expiry não é salvo no nosso dict,
    # então creds.expired é sempre False mesmo com token vencido (1h).
    if creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            pass  # usa token existente; gspread retenta no 401
    return creds


def listar_planilhas(creds_dict: dict) -> list[dict]:
    """
    Retorna lista de planilhas do usuário como [{"id": ..., "name": ...}].
    """
    creds = _creds_from_dict(creds_dict)
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    result = service.files().list(
        q="mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
        pageSize=50,
        fields="files(id, name)",
        orderBy="modifiedTime desc",
    ).execute()
    return result.get("files", [])


def listar_abas(creds_dict: dict, sheet_id: str) -> list[str]:
    """Retorna nomes das abas de uma planilha."""
    creds = _creds_from_dict(creds_dict)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    return [ws.title for ws in sh.worksheets()]


def exportar(
    resultados: list[dict],
    creds_dict: dict,
    sheet_id: str,
    aba_nome: str = "Planilha1",
    modo: str = "substituir",
) -> tuple[bool, str]:
    """
    Exporta resultados para o Google Sheets usando credenciais OAuth.

    Parâmetros:
        resultados - lista de dicts com os dados
        creds_dict - credenciais serializadas (de trocar_codigo)
        sheet_id   - ID da planilha (extraído da URL)
        aba_nome   - nome da aba onde escrever
        modo       - "substituir" ou "acrescentar"
    """
    if not resultados:
        return False, "Nenhum resultado para exportar."

    try:
        creds = _creds_from_dict(creds_dict)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
    except Exception as e:
        return False, f"Erro ao conectar com a planilha: {e}"

    # Não cria aba silenciosamente — retorna erro claro com abas disponíveis
    try:
        ws = sh.worksheet(aba_nome)
    except Exception:
        disponiveis = [w.title for w in sh.worksheets()]
        return False, (
            f"Aba **'{aba_nome}'** não encontrada. "
            f"Abas disponíveis: {', '.join(disponiveis) or '(nenhuma)'}. "
            "Corrija em ⚙️ Configurações."
        )

    cabecalho = [lbl for _, lbl in COLUNAS_EXPORT]
    linhas = [[str(r.get(col, "") or "") for col, _ in COLUNAS_EXPORT] for r in resultados]

    try:
        if modo == "substituir":
            ws.clear()
            ws.update([cabecalho] + linhas)
        else:
            existentes = ws.get_all_values()
            if not existentes:
                ws.update([cabecalho] + linhas)
            else:
                ws.append_rows(linhas)

        # Verificação: lê de volta para confirmar que os dados foram escritos
        check = ws.get("A1")
        if not check:
            return False, (
                f"Escrita falhou silenciosamente — ws.update() não deu erro "
                f"mas a planilha está vazia. sheet_id={sheet_id[:12]}… aba={aba_nome}"
            )

        return True, f"✅ {len(linhas)} registros exportados para **{aba_nome}**"
    except Exception as e:
        return False, f"Erro ao escrever na planilha: {e}"


def extrair_sheet_id(url_ou_id: str) -> Optional[str]:
    """Extrai o ID de uma URL do Google Sheets ou retorna o próprio ID."""
    if "spreadsheets/d/" in url_ou_id:
        try:
            return url_ou_id.split("spreadsheets/d/")[1].split("/")[0]
        except Exception:
            return None
    if len(url_ou_id) > 20 and "/" not in url_ou_id:
        return url_ou_id
    return None
