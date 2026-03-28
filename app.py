"""Lead Extractor · Revolução AI"""
import os, io, csv, time, json
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

def _s(k, d=""):
    try:
        v = st.secrets.get(k,"")
        if v: return str(v).strip()
    except: pass
    return os.getenv(k,d).strip()

# ── OAuth callback ────────────────────────────────────────────
# Guarda code/state na sessão na primeira vez que aparecem na URL,
# evitando que reruns do CookieManager consumam o código duas vezes.
_code  = st.query_params.get("code","")
_state = st.query_params.get("state","")
if _code and not st.session_state.get("_oauth_code_seen"):
    st.session_state["_oauth_code_seen"] = _code   # marca como visto
    st.session_state["_oauth_state_seen"] = _state  # preserva state junto
    st.query_params.clear()                          # limpa URL imediatamente

if st.session_state.get("_oauth_code_seen") and "sheets_creds" not in st.session_state \
        and not st.session_state.get("_oauth_exchange_done"):
    _code_to_use  = st.session_state.pop("_oauth_code_seen")
    _state_to_use = st.session_state.pop("_oauth_state_seen", "")
    st.session_state["_oauth_exchange_done"] = True  # impede segundo uso

    # 1) Credenciais + code_verifier codificados no state (gerados em gerar_url_auth)
    cid, cs, ru, cv = "", "", "", ""
    if _state_to_use:
        from modules.google_sheets import extrair_credenciais_state
        cid, cs, ru, cv = extrair_credenciais_state(_state_to_use)

    # 2) Fallback: env vars (sem code_verifier — PKCE não funcionará nesse caso)
    if not (cid and cs):
        cid = cid or _s("GOOGLE_CLIENT_ID")
        cs  = cs  or _s("GOOGLE_CLIENT_SECRET")
        ru  = ru  or _s("APP_URL","http://localhost:8501")

    st.session_state["page"] = "configuracoes"

    if cid and cs:
        try:
            from modules.google_sheets import trocar_codigo
            creds = trocar_codigo(cid, cs, ru, _code_to_use, code_verifier=cv)
            st.session_state["sheets_creds"] = creds
            st.session_state.pop("_oauth_exchange_done", None)  # limpa flag após sucesso
            if "user" in st.session_state:
                from modules.database import salvar_configuracoes
                salvar_configuracoes({"google_sheets_creds": creds})
            else:
                st.session_state["_pending_sheets_save"] = True
        except Exception as e:
            err = str(e)
            if "redirect_uri_mismatch" in err:
                err = (f"redirect_uri_mismatch — adicione exatamente '{ru}' em "
                       f"Google Cloud Console → Credenciais → OAuth → URIs de redirecionamento autorizados.")
            st.session_state["_oauth_err"] = err
    else:
        st.session_state["_oauth_err"] = (
            "Credenciais OAuth não encontradas. "
            + (f"State recebido: `{_state_to_use[:80]}`" if _state_to_use else "Nenhum state recebido.")
        )
    st.rerun()

st.set_page_config(page_title="Lead Extractor · Revolução AI", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

/* ═══════════════════════════════════════════════════════════
   BASE & RESET
═══════════════════════════════════════════════════════════ */
*, *::before, *::after { box-sizing: border-box; margin: 0; }
html, body, [class*="css"] {
  font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
  -webkit-font-smoothing: antialiased;
}

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 8px; }
::-webkit-scrollbar-thumb:hover { background: #00D97E35; }

/* ═══════════════════════════════════════════════════════════
   LAYOUT
═══════════════════════════════════════════════════════════ */
.stApp {
  background: #020617 !important;
  background-image: radial-gradient(ellipse 80% 50% at 50% -10%, #0d2b1a18, transparent) !important;
}
[data-testid="stAppViewContainer"] { background: transparent !important; }
.block-container {
  padding: 2rem 2.75rem 5rem !important;
  max-width: 1320px !important;
}

/* ═══════════════════════════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
  background: #040812 !important;
  border-right: 1px solid #0f172a !important;
}
[data-testid="stSidebarContent"] { padding: 0 !important; }
[data-testid="stSidebar"] hr {
  margin: 4px 16px !important;
  border: none !important;
  border-top: 1px solid #0f172a !important;
}

/* Nav buttons */
[data-testid="stSidebar"] [data-testid="stButton"] > button {
  width: 100% !important;
  text-align: left !important;
  justify-content: flex-start !important;
  padding: 9px 14px 9px 16px !important;
  border-radius: 8px !important;
  font-size: 0.84rem !important;
  font-weight: 500 !important;
  transition: all 0.15s ease !important;
  margin: 1px 0 !important;
  border: none !important;
  letter-spacing: 0.003em !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="secondary"] {
  background: transparent !important;
  color: #475569 !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="secondary"]:hover {
  background: #0f172a !important;
  color: #cbd5e1 !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(135deg, #052913 0%, #031b0c 100%) !important;
  color: #00D97E !important;
  border: 1px solid #00D97E20 !important;
  font-weight: 600 !important;
  box-shadow: inset 0 1px 0 #00D97E10 !important;
}

/* ═══════════════════════════════════════════════════════════
   INPUTS & CONTROLS
═══════════════════════════════════════════════════════════ */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
  background: #0a0f1e !important;
  border: 1px solid #1e293b !important;
  border-radius: 8px !important;
  color: #e2e8f0 !important;
  padding: 9px 13px !important;
  font-size: 0.875rem !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  transition: border-color 0.18s, box-shadow 0.18s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
  border-color: #00D97E50 !important;
  box-shadow: 0 0 0 3px #00D97E0e !important;
  outline: none !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stNumberInput"] input::placeholder { color: #334155 !important; }

[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
  background: #0a0f1e !important;
  border: 1px solid #1e293b !important;
  border-radius: 8px !important;
  color: #e2e8f0 !important;
}
[data-testid="stSelectbox"] > div > div:focus-within,
[data-testid="stMultiSelect"] > div > div:focus-within {
  border-color: #00D97E50 !important;
  box-shadow: 0 0 0 3px #00D97E0e !important;
}

/* Dropdown menu */
[data-testid="stSelectboxVirtualDropdown"],
.stSelectbox [data-testid="stMarkdownContainer"],
div[data-baseweb="popover"] ul {
  background: #0d1424 !important;
  border: 1px solid #1e293b !important;
  border-radius: 10px !important;
}

/* ═══════════════════════════════════════════════════════════
   FORMS
═══════════════════════════════════════════════════════════ */
[data-testid="stForm"] {
  background: linear-gradient(160deg, #080d1a 0%, #060a14 100%) !important;
  border: 1px solid #0f1e38 !important;
  border-radius: 14px !important;
  padding: 22px 24px !important;
  box-shadow: 0 4px 24px #00000055, inset 0 1px 0 #ffffff05 !important;
  backdrop-filter: blur(0px) !important;
}

/* ═══════════════════════════════════════════════════════════
   BUTTONS
═══════════════════════════════════════════════════════════ */
[data-testid="stButton"] > button,
[data-testid="stDownloadButton"] > button {
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-size: 0.835rem !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  transition: all 0.17s cubic-bezier(.4,0,.2,1) !important;
  letter-spacing: 0.01em !important;
  padding: 7px 16px !important;
  min-height: unset !important;
  height: auto !important;
}

/* Primary */
[data-testid="stButton"] > button[kind="primary"],
button[kind="primaryFormSubmit"] {
  background: linear-gradient(135deg, #00bf6a 0%, #00a558 100%) !important;
  color: #021408 !important;
  border: none !important;
  font-weight: 700 !important;
  box-shadow: 0 1px 2px #00000030, 0 2px 12px #00bf6a28 !important;
  padding: 8px 20px !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover,
button[kind="primaryFormSubmit"]:hover {
  background: linear-gradient(135deg, #00d47a 0%, #00b862 100%) !important;
  box-shadow: 0 2px 4px #00000030, 0 6px 24px #00D97E38 !important;
  transform: translateY(-1px) !important;
}
[data-testid="stButton"] > button[kind="primary"]:active,
button[kind="primaryFormSubmit"]:active {
  transform: translateY(0) !important;
  box-shadow: 0 1px 4px #00000030 !important;
}

/* Secondary */
[data-testid="stButton"] > button[kind="secondary"] {
  background: #0a0f1e !important;
  border: 1px solid #1e293b !important;
  color: #64748b !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover {
  background: #0d1424 !important;
  border-color: #2d3f5e !important;
  color: #cbd5e1 !important;
}

/* Download */
[data-testid="stDownloadButton"] > button {
  background: #0a0f1e !important;
  border: 1px solid #1e293b !important;
  color: #64748b !important;
}
[data-testid="stDownloadButton"] > button:hover {
  background: #071610 !important;
  border-color: #1a3d28 !important;
  color: #00C472 !important;
}

/* ═══════════════════════════════════════════════════════════
   TABS
═══════════════════════════════════════════════════════════ */
[data-testid="stTabs"] [role="tablist"] {
  background: #060a14 !important;
  border-radius: 10px !important;
  padding: 4px !important;
  border: 1px solid #0f172a !important;
  gap: 2px !important;
}
[data-testid="stTabs"] [role="tab"] {
  border-radius: 7px !important;
  color: #475569 !important;
  font-weight: 500 !important;
  font-size: 0.855rem !important;
  padding: 8px 20px !important;
  transition: all 0.18s !important;
  border: none !important;
  letter-spacing: 0.005em !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  background: linear-gradient(135deg, #082318 0%, #051410 100%) !important;
  color: #00D97E !important;
  font-weight: 700 !important;
  box-shadow: 0 1px 8px #00000035, inset 0 1px 0 #00D97E18 !important;
}
[data-testid="stTabs"] [role="tab"]:hover:not([aria-selected="true"]) {
  background: #0d1424 !important;
  color: #94a3b8 !important;
}

/* ═══════════════════════════════════════════════════════════
   EXPANDERS
═══════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {
  background: #060a14 !important;
  border: 1px solid #0f172a !important;
  border-radius: 12px !important;
  margin-bottom: 8px !important;
  overflow: hidden !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stExpander"]:hover {
  border-color: #1e293b !important;
  box-shadow: 0 2px 16px #00000025 !important;
}
[data-testid="stExpander"] summary {
  padding: 13px 18px !important;
  color: #94a3b8 !important;
  font-weight: 600 !important;
  font-size: 0.875rem !important;
  letter-spacing: 0.005em !important;
}
[data-testid="stExpander"] summary:hover {
  background: #0a0f1e !important;
  color: #e2e8f0 !important;
}
[data-testid="stExpander"] > div > div { padding: 0 18px 16px !important; }

/* ═══════════════════════════════════════════════════════════
   ALERTS
═══════════════════════════════════════════════════════════ */
[data-testid="stAlert"] {
  border-radius: 10px !important;
  border-width: 1px !important;
  font-size: 0.875rem !important;
}
.stSuccess {
  background: linear-gradient(135deg, #04130b 0%, #030e08 100%) !important;
  border-color: #00D97E28 !important;
}
.stInfo {
  background: linear-gradient(135deg, #030b1c 0%, #020814 100%) !important;
  border-color: #3b82f628 !important;
}
.stWarning {
  background: linear-gradient(135deg, #110e02 0%, #0d0a01 100%) !important;
  border-color: #f59e0b28 !important;
}
.stError {
  background: linear-gradient(135deg, #130404 0%, #0f0303 100%) !important;
  border-color: #ef444428 !important;
}

/* ═══════════════════════════════════════════════════════════
   PROGRESS BAR
═══════════════════════════════════════════════════════════ */
[data-testid="stProgress"] { margin: 10px 0 !important; }
[data-testid="stProgress"] > div {
  background: #0f172a !important;
  border-radius: 99px !important;
  height: 5px !important;
}
[data-testid="stProgress"] > div > div {
  background: linear-gradient(90deg, #00bf6a, #00f090) !important;
  border-radius: 99px !important;
  box-shadow: 0 0 8px #00D97E55 !important;
}

/* ═══════════════════════════════════════════════════════════
   DATAFRAME
═══════════════════════════════════════════════════════════ */
.stDataFrame { border-radius: 12px !important; overflow: hidden !important; }
.stDataFrame [data-testid="stDataFrameResizable"] {
  border: 1px solid #0f172a !important;
  border-radius: 12px !important;
}

/* ═══════════════════════════════════════════════════════════
   LABELS & CAPTIONS
═══════════════════════════════════════════════════════════ */
[data-testid="stCaptionContainer"] { color: #334155 !important; font-size: 0.78rem !important; }
[data-testid="stWidgetLabel"] {
  color: #475569 !important;
  font-size: 0.8rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.02em !important;
  text-transform: uppercase !important;
}
[data-testid="stToggle"] { background: transparent !important; padding: 6px 0 !important; }

/* ═══════════════════════════════════════════════════════════
   CUSTOM COMPONENTS
═══════════════════════════════════════════════════════════ */

/* ── Sidebar Brand ─────────────────────────────────────────── */
.brand-header {
  padding: 20px 16px 16px;
  background: linear-gradient(180deg, #060d1a 0%, #030710 100%);
  border-bottom: 1px solid #0f172a;
}
.brand-dot {
  width: 34px; height: 34px;
  background: linear-gradient(135deg, #00D97E 0%, #009955 100%);
  border-radius: 9px;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 800; color: #020e06; font-size: 15px;
  box-shadow: 0 2px 10px #00D97E40, 0 0 0 1px #00D97E20;
  vertical-align: middle; margin-right: 10px; flex-shrink: 0;
}
.brand-title {
  font-size: 0.9rem; font-weight: 700; color: #e2e8f0;
  line-height: 1.2; letter-spacing: -0.02em;
}
.brand-sub {
  font-size: 0.6rem; color: #00D97E; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.16em; margin-top: 2px;
  opacity: 0.85;
}

/* ── User Card ─────────────────────────────────────────────── */
.user-card {
  margin: 8px 10px 4px;
  background: #060a14;
  border: 1px solid #0f172a;
  border-radius: 10px; padding: 10px 13px;
}
.user-email { font-size: 0.76rem; color: #475569; font-weight: 500; word-break: break-all; }
.user-role-badge {
  display: inline-block; margin-top: 5px; padding: 2px 8px;
  border-radius: 99px; font-size: 0.63rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.12em;
}
.role-admin { background: #041b0e; color: #00D97E; border: 1px solid #00D97E22; }
.role-user  { background: #070b18; color: #60a5fa; border: 1px solid #3b82f622; }

/* ── Page Header ───────────────────────────────────────────── */
.page-header {
  margin-bottom: 2rem; padding-bottom: 1.5rem;
  border-bottom: 1px solid #0f172a;
  display: flex; align-items: flex-start; gap: 14px;
}
.page-header-icon {
  width: 44px; height: 44px; border-radius: 11px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  background: linear-gradient(135deg, #0a1628 0%, #07101e 100%);
  border: 1px solid #1e293b;
  box-shadow: inset 0 1px 0 #ffffff06;
}
.page-title {
  font-size: 1.6rem; font-weight: 800; letter-spacing: -0.03em;
  line-height: 1.1;
  background: linear-gradient(135deg, #f1f5f9 30%, #64748b 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text; margin-bottom: 0.3rem;
}
.page-sub {
  font-size: 0.845rem; color: #334155; font-weight: 400; line-height: 1.5;
}

/* ── Stat Cards ────────────────────────────────────────────── */
.stats-row {
  display: grid; grid-template-columns: repeat(4,1fr);
  gap: 12px; margin: 1.25rem 0;
}
.stat-card {
  background: #060a14;
  border: 1px solid #0f172a;
  border-radius: 14px; padding: 18px 20px;
  position: relative; overflow: hidden;
  transition: border-color 0.22s, transform 0.22s, box-shadow 0.22s;
}
.stat-card:hover {
  border-color: #00D97E22;
  transform: translateY(-2px);
  box-shadow: 0 8px 28px #00000045;
}
.stat-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, #00D97E50, transparent 60%);
}
.stat-card::after {
  content: ''; position: absolute;
  top: -30px; right: -30px;
  width: 80px; height: 80px;
  background: radial-gradient(circle, #00D97E08, transparent 70%);
  border-radius: 50%;
}
.stat-num {
  font-size: 2.2rem; font-weight: 800; color: #00D97E;
  line-height: 1; letter-spacing: -0.04em;
}
.stat-lbl {
  font-size: 0.68rem; color: #334155; margin-top: 7px;
  text-transform: uppercase; letter-spacing: 0.12em; font-weight: 600;
}

/* ── Section Label ─────────────────────────────────────────── */
.sec {
  font-size: 0.65rem; font-weight: 700; color: #00D97E;
  text-transform: uppercase; letter-spacing: 0.14em;
  margin: 1rem 0 0.4rem;
  display: flex; align-items: center; gap: 8px;
  opacity: 0.85;
}
.sec::after {
  content: ''; flex: 1; height: 1px;
  background: linear-gradient(90deg, #00D97E18, transparent);
}

/* ── Info Box ──────────────────────────────────────────────── */
.info-box {
  background: #060a14;
  border: 1px solid #0f172a;
  border-left: 2px solid #00D97E60;
  border-radius: 8px; padding: 12px 16px;
  font-size: 0.84rem; color: #475569; line-height: 1.65;
  margin-bottom: 1.25rem;
}
.info-box strong { color: #64748b; font-weight: 600; }

/* ── Divider ───────────────────────────────────────────────── */
.hr { border: none; border-top: 1px solid #0f172a; margin: 1rem 0; }

/* ── Badges ────────────────────────────────────────────────── */
.badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px; border-radius: 99px;
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em;
}
.b-ok   { background: #041b0e; color: #00D97E; border: 1px solid #00D97E22; }
.b-warn { background: #120d01; color: #f59e0b; border: 1px solid #f59e0b22; }
.b-err  { background: #130304; color: #f87171; border: 1px solid #ef444422; }

/* ── Login Form ────────────────────────────────────────────── */
[data-testid="stForm"] { padding: 26px 28px 22px !important; }
.login-head { text-align: center; padding: 0 0 20px; }
.login-title {
  font-size: 1.25rem; font-weight: 800; color: #e2e8f0;
  letter-spacing: -0.025em; margin-top: 14px; line-height: 1.2;
}
.login-sub {
  font-size: 0.62rem; color: #00C472; font-weight: 700;
  letter-spacing: 0.16em; text-transform: uppercase; margin-top: 4px;
  opacity: 0.75;
}

</style>""", unsafe_allow_html=True)

from modules.google_sheets import COLUNAS_EXPORT
from modules.auth import _COOKIE_NAME  # nome do cookie de sessão

def _logo_html(size: int = 40) -> str:
    """Retorna HTML com a logo.
    Usa URL estática (app/static/logo.png) — o browser faz cache da imagem e
    ela NÃO é reenviada via WebSocket a cada render, ao contrário do base64."""
    from pathlib import Path
    p = Path("static/logo.png")
    r = size // 5
    if p.exists():
        return (f'<img src="app/static/logo.png" '
                f'style="width:{size}px;height:{size}px;border-radius:{r}px;'
                f'object-fit:cover;display:inline-block" />')
    r2 = size // 4
    fs = int(size * 0.38)
    return (f'<div style="width:{size}px;height:{size}px;background:#00C472;'
            f'border-radius:{r2}px;display:inline-flex;align-items:center;'
            f'justify-content:center;font-size:{fs}px;font-weight:800;color:#030E06">R</div>')
_EXTRA=[("telefone_internacional","Telefone Intl."),("status_funcionamento","Status"),
        ("porte","Porte"),("data_abertura","Data Abertura")]
ALL_COLS = COLUNAS_EXPORT + [c for c in _EXTRA if c not in COLUNAS_EXPORT]

def _csv(rows):
    b=io.StringIO(); w=csv.writer(b)
    w.writerow([l for _,l in ALL_COLS])
    for r in rows: w.writerow([r.get(c,"") for c,_ in ALL_COLS])
    return b.getvalue().encode("utf-8-sig")

def _xlsx(rows):
    import openpyxl
    from openpyxl.styles import Font,PatternFill,Alignment
    from openpyxl.utils import get_column_letter
    wb=openpyxl.Workbook(); ws=wb.active; ws.title="Prospecção"
    hf=Font(bold=True,color="0A0A0F"); hfill=PatternFill("solid",fgColor="00D97E")
    for ci,(col,lbl) in enumerate(ALL_COLS,1):
        c=ws.cell(row=1,column=ci,value=lbl); c.font=hf; c.fill=hfill
        c.alignment=Alignment(horizontal="center")
    ws.row_dimensions[1].height=22
    fa=PatternFill("solid",fgColor="141418"); fb=PatternFill("solid",fgColor="0D0D12")
    for ri,r in enumerate(rows,2):
        for ci,(col,_) in enumerate(ALL_COLS,1):
            cell=ws.cell(row=ri,column=ci,value=r.get(col,""))
            cell.fill=fa if ri%2==0 else fb
            if col in("site","maps_url") and r.get(col):
                cell.hyperlink=r[col]; cell.font=Font(color="00D97E",underline="single")
    for ci in range(1,len(ALL_COLS)+1):
        mx=max(len(str(ws.cell(row=rr,column=ci).value or"")) for rr in range(1,len(rows)+2))
        ws.column_dimensions[get_column_letter(ci)].width=min(mx+2,50)
    ws.freeze_panes="A2"
    buf=io.BytesIO(); wb.save(buf); return buf.getvalue()

def _stats(rows):
    tot  = len(rows)
    tel  = sum(1 for r in rows if r.get("telefone") or r.get("telefone2"))
    site = sum(1 for r in rows if r.get("site"))
    em   = sum(1 for r in rows if r.get("email"))
    cards = "".join(
        f'<div class="stat-card"><div class="stat-num">{n}</div><div class="stat-lbl">{l}</div></div>'
        for n, l in [(tot,"Total leads"),(tel,"Com telefone"),(site,"Com site"),(em,"Com e-mail")]
    )
    st.markdown(f'<div class="stats-row">{cards}</div>', unsafe_allow_html=True)

def _tabela(rows):
    import pandas as pd
    vis=["nome","telefone","email","municipio","uf","endereco","site","avaliacao","cnpj","nicho_busca","subnicho_busca","fonte"]
    lm={c:l for c,l in ALL_COLS}; df=pd.DataFrame(rows)
    cols=[c for c in vis if c in df.columns]
    st.dataframe(df[cols].rename(columns=lm).fillna("").astype(str).replace("nan",""), use_container_width=True, height=380)

def _export_to_planilha(rows, planilha: dict):
    """Exporta rows para uma planilha configurada."""
    from modules.google_sheets import exportar
    creds = st.session_state.get("sheets_creds")
    if not creds:
        st.error("Conta Google não vinculada. Configure em ⚙️ Configurações.")
        return
    with st.spinner(f"Exportando para {planilha['nome']}…"):
        ok, msg = exportar(rows, creds, planilha["id"], planilha["aba"],
                           planilha.get("modo", "substituir"))
    if ok:
        st.success(msg)
    else:
        st.error(msg)

def _dl_buttons(rows, prefix, sheets_auth):
    ts = int(time.time())

    # Executa exportação pendente FORA do popover (evita contexto fechado)
    _req_id = st.session_state.pop(f"_exp_req_{prefix}", None)
    if _req_id:
        _p = next((p for p in st.session_state.get("sheets_planilhas", []) if p["id"] == _req_id), None)
        if _p:
            _export_to_planilha(rows, _p)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("⬇️ Excel", _xlsx(rows), f"{prefix}_{ts}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    with c2:
        st.download_button("⬇️ CSV", _csv(rows), f"{prefix}_{ts}.csv",
                           "text/csv", use_container_width=True)
    with c3:
        planilhas_cfg = st.session_state.get("sheets_planilhas", [])
        if sheets_auth and planilhas_cfg:
            with st.popover("📊 Google Sheets", use_container_width=True):
                st.markdown("**Exportar para:**")
                for p in planilhas_cfg:
                    badge = " ⭐" if p.get("padrao") else ""
                    lbl = f"{p['nome']}{badge} → {p['aba']} ({p.get('modo','substituir')})"
                    if st.button(lbl, key=f"exp_{p['id'][:8]}_{prefix}", use_container_width=True):
                        # Guarda flag — exportação roda fora do popover no próximo render
                        st.session_state[f"_exp_req_{prefix}"] = p["id"]
                        st.rerun()
        elif sheets_auth:
            st.button("📊 Google Sheets", use_container_width=True, disabled=True,
                      help="Adicione uma planilha em ⚙️ Configurações.")
        else:
            st.button("📊 Google Sheets", use_container_width=True, disabled=True,
                      help="Conecte sua conta Google em ⚙️ Configurações.")

# ══════════════════════════════════════════════════════════════
# PÁGINAS
# ══════════════════════════════════════════════════════════════

def pagina_login():
    # Centralização vertical: espaçador + colunas
    st.markdown("<div style='height:12vh'></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.form("login"):
            st.markdown(
                f'<div class="login-head">'
                f'{_logo_html(52)}'
                f'<div class="login-title">Lead Extractor</div>'
                f'<div class="login-sub">Revolução AI</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            email = st.text_input("E-mail", placeholder="seu@email.com")
            senha = st.text_input("Senha", type="password", placeholder="••••••••")
            btn   = st.form_submit_button("Entrar", use_container_width=True, type="primary")
        if btn:
            if not email or not senha:
                st.error("Preencha e-mail e senha.")
            else:
                from modules.auth import login, supabase_configurado
                if not supabase_configurado():
                    st.error("Supabase não configurado. Verifique SUPABASE_URL e SUPABASE_ANON_KEY nos Secrets.")
                else:
                    with st.spinner(""):
                        ok, msg = login(email, senha)
                    if ok:
                        st.session_state["page"] = "busca"
                        st.rerun()
                    else:
                        st.error(msg)


def pagina_busca():
    from modules.nichos import NICHOS, ESTADOS, NOMES_NICHOS, SIGLAS_ESTADOS

    st.markdown(
        '<div class="page-header">'
        '<div class="page-header-icon">🔍</div>'
        '<div><div class="page-title">Nova Busca</div>'
        '<div class="page-sub">Busque leads por nicho e localidade usando Google Maps ou Receita Federal</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Chave do Google Maps vem EXCLUSIVAMENTE das configurações do usuário (Supabase)
    from modules.database import carregar_configuracoes
    _cfg_busca = carregar_configuracoes()
    gmaps_key = _cfg_busca.get("google_maps_api_key", "") or st.session_state.get("user_gmaps_key", "")
    gmaps_ok  = bool(gmaps_key)

    aba_maps, aba_rf = st.tabs(["🗺️  Google Maps  ·  com telefone", "🏢  Casa dos Dados  ·  CNPJ + filtros avançados"])

    with aba_maps:
        if not gmaps_ok:
            st.warning("Chave do Google Maps não configurada. Acesse **Configurações → Google Maps API** para adicionar.", icon="⚠️")
        st.markdown('<div class="info-box">Melhor fonte para <strong>telefones</strong>. Até ~500 resultados com múltiplas buscas automáticas.</div>', unsafe_allow_html=True)

        col_n, col_s = st.columns(2)
        with col_n:
            st.markdown('<div class="sec">Nicho *</div>', unsafe_allow_html=True)
            nicho_sel = st.selectbox("Nicho", NOMES_NICHOS, label_visibility="collapsed", key="m_nicho")
        nicho_data = NICHOS[nicho_sel]; is_custom = nicho_sel == "Outro / Personalizado"
        with col_s:
            st.markdown('<div class="sec">Subnicho / Especialidade</div>', unsafe_allow_html=True)
            if is_custom:
                query_custom = st.text_input("Termo", placeholder='"pet shop", "clínica veterinária"', label_visibility="collapsed", key="m_qcustom")
                subnicho_sel = ""
            else:
                sub_opts = ["Todos (sem filtro)"] + nicho_data["subnichos"] + ["✏️ Personalizado..."]
                subnicho_sel = st.selectbox("Subnicho", sub_opts, label_visibility="collapsed", key="m_sub")
        sub_custom = ""
        if not is_custom and subnicho_sel == "✏️ Personalizado...":
            sub_custom = st.text_input("Especialidade personalizada", key="m_subcustom")

        st.markdown('<hr class="hr">', unsafe_allow_html=True)
        with st.form("form_maps"):
            st.markdown('<div class="sec">Localidade — cidade e/ou estado</div>', unsafe_allow_html=True)
            cc, ce, cl = st.columns([3,1,2])
            with cc: cidade = st.text_input("Cidade", placeholder="Ex: São Paulo", label_visibility="collapsed")
            with ce:
                eopts = ["—"]+SIGLAS_ESTADOS; edef = eopts.index("SP") if "SP" in eopts else 0
                est_raw = st.selectbox("Estado", eopts, index=edef, label_visibility="collapsed")
                estado = "" if est_raw == "—" else est_raw
            with cl:
                lim = st.slider("Resultados", 20, 500, 60, 20, label_visibility="collapsed")
                st.caption(f"Máx. **{lim}** resultados")
            apenas_novos_maps = st.toggle(
                "🔄 Apenas leads novos (remover repetidos de buscas anteriores)",
                value=True,
                help="Quando ativado, leads com mesmo telefone ou CNPJ de pesquisas anteriores são removidos dos resultados.",
            )
            buscar_btn = st.form_submit_button("🔍 Buscar no Google Maps", disabled=not gmaps_ok, use_container_width=True, type="primary")

        if buscar_btn:
            cv, ev = cidade.strip(), estado.strip()
            if not cv and not ev: st.error("Informe ao menos a cidade ou o estado.")
            elif is_custom and not query_custom.strip(): st.error("Informe o termo personalizado.")
            else:
                from modules.google_maps import buscar as maps_buscar
                qbase = query_custom.strip() if is_custom else nicho_data["query"]
                nicho_lbl = qbase if is_custom else nicho_sel
                sub_final = "" if (is_custom or subnicho_sel=="Todos (sem filtro)") else (sub_custom.strip() if subnicho_sel=="✏️ Personalizado..." else subnicho_sel)
                localidade = f"{cv}, {ESTADOS.get(ev,ev)}" if cv and ev else cv or ESTADOS.get(ev,ev)
                slug = f"{nicho_lbl[:15]}_{localidade[:15]}".lower().replace(" ","_").replace(",","")
                # Carrega identificadores já salvos antes de iniciar a busca
                excl_tels_maps = set()
                if apenas_novos_maps:
                    from modules.database import buscar_identificadores_existentes
                    excl_tels_maps, _ = buscar_identificadores_existentes()
                prog = st.progress(0, text="Iniciando...")
                def _cb(a, t, m):
                    v = min(a / t, 1.0) if t and t > 0 else 0
                    prog.progress(v, text=str(m)[:120])
                try:
                    res = maps_buscar(query_base=qbase, localidade=localidade, limite=lim,
                                      api_key=gmaps_key, nicho=nicho_lbl, subnicho=sub_final,
                                      cidade=cv, estado=ev, progress_callback=_cb,
                                      exclude_phones=excl_tels_maps if apenas_novos_maps else None)
                    prog.progress(1.0, text=f"Concluído! {len(res)} resultados.")
                    prog.empty()
                    st.session_state["maps_res"] = res
                    st.session_state["maps_prefix"] = slug
                except ValueError as e:
                    prog.empty(); st.error(str(e)); st.session_state["maps_res"] = []
                except Exception as e:
                    prog.empty(); st.error(f"Erro: {e}"); st.session_state["maps_res"] = []
                else:
                    try:
                        from modules.database import salvar_pesquisa, salvar_leads
                        sid = salvar_pesquisa(nicho_lbl, sub_final, cv, ev, localidade, "maps", len(res))
                        if sid: salvar_leads(sid, res)
                    except Exception:
                        pass
                    # Seta flag — auto-export roda fora do bloco else/tab abaixo
                    if st.session_state.get("auto_export_enabled"):
                        st.session_state["_auto_exp_maps"] = True

        if st.session_state.get("maps_res"):
            res = st.session_state["maps_res"]
            # Auto-export roda aqui, fora de qualquer contexto de form/tab/popover
            if st.session_state.pop("_auto_exp_maps", False):
                _planilhas = st.session_state.get("sheets_planilhas", [])
                _padrao = next((p for p in _planilhas if p.get("padrao")), None)
                if _padrao and st.session_state.get("sheets_creds"):
                    from modules.google_sheets import exportar
                    with st.spinner(f"Auto-exportando para {_padrao['nome']}…"):
                        _ok, _msg = exportar(res, st.session_state["sheets_creds"],
                                             _padrao["id"], _padrao["aba"],
                                             _padrao.get("modo","substituir"))
                    if _ok:
                        st.success(_msg)
                    else:
                        st.error(_msg)
                elif not st.session_state.get("sheets_creds"):
                    st.warning("Auto-export: conta Google não vinculada.")
                else:
                    st.warning("Auto-export: nenhuma planilha padrão ⭐ definida.")
            st.success(f"✅ **{len(res)}** resultados")
            _stats(res); _dl_buttons(res, st.session_state.get("maps_prefix","prospecao"), "sheets_creds" in st.session_state and bool(st.session_state.get("sheets_planilhas")))
            st.markdown("#### Prévia"); _tabela(res)

    with aba_rf:
        from modules.cnaes import OPCOES_MULTISELECT, CODIGO_PARA_DESC

        cdd_key = _s("CDD_API_KEY")
        if not cdd_key:
            st.warning(
                "Chave da API Casa dos Dados não configurada.  \n"
                "Adicione `CDD_API_KEY` nas **Secrets** do Streamlit Cloud para habilitar esta busca.",
                icon="⚠️",
            )
        else:
            st.markdown('<div class="info-box">Busca direta no cadastro da <strong>Receita Federal</strong> via <strong>Casa dos Dados</strong>. '
                        'Filtros por CNAE, porte, regime tributário e muito mais. Resultados instantâneos.</div>', unsafe_allow_html=True)

            with st.form("form_cdd"):
                # ── CNAEs ──────────────────────────────────────────────────────
                st.markdown("**CNAE(s) — Atividade principal**")
                cnaes_sel = st.multiselect(
                    "Selecione os CNAEs", OPCOES_MULTISELECT,
                    placeholder="Digite para buscar por código ou atividade…",
                    label_visibility="collapsed", key="cdd_cnaes",
                )
                cnae_manual = st.text_input(
                    "Ou adicione código CNAE manualmente (separe por vírgula)",
                    placeholder="Ex: 6911701, 6912500",
                    key="cdd_cnae_manual",
                )

                # ── Localização ───────────────────────────────────────────────
                c1, c2 = st.columns(2)
                with c1:
                    uf_cdd = st.selectbox("Estado *", SIGLAS_ESTADOS, index=SIGLAS_ESTADOS.index("SP"), key="cdd_uf")
                with c2:
                    mun_cdd = st.text_input("Município (opcional)", placeholder="Ex: São Paulo", key="cdd_mun")

                lim_cdd = st.slider("Máx. resultados", 50, 2000, 300, 50, key="cdd_lim")

                # ── Filtros da empresa ─────────────────────────────────────────
                with st.expander("📊 Filtros da empresa"):
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        portes_sel = st.multiselect(
                            "Porte da empresa",
                            options=["01 — Micro Empresa", "03 — Empresa de Pequeno Porte", "05 — Demais"],
                            default=[],
                            key="cdd_porte",
                        )
                        matriz_fil = st.radio(
                            "Matriz / Filial",
                            ["Todos", "Somente Matriz", "Somente Filial"],
                            horizontal=True, key="cdd_matriz",
                        )
                    with fc2:
                        simples_op = st.radio(
                            "Simples Nacional",
                            ["Indiferente", "Apenas optantes", "Excluir optantes"],
                            key="cdd_simples",
                        )
                        mei_op = st.radio(
                            "MEI",
                            ["Indiferente", "Apenas MEI", "Excluir MEI"],
                            key="cdd_mei",
                        )

                    fd1, fd2 = st.columns(2)
                    with fd1:
                        dt_ini = st.date_input("Abertura — de", value=None, key="cdd_dt_ini")
                        cap_min = st.number_input("Capital social mínimo (R$)", min_value=0, value=0, step=1000, key="cdd_cap_min")
                    with fd2:
                        dt_fim = st.date_input("Abertura — até", value=None, key="cdd_dt_fim")
                        cap_max = st.number_input("Capital social máximo (R$)", min_value=0, value=0, step=1000, key="cdd_cap_max")

                # ── Filtros de contato ─────────────────────────────────────────
                with st.expander("📞 Filtros de contato"):
                    ct1, ct2 = st.columns(2)
                    with ct1:
                        com_tel = st.toggle("Apenas com telefone", value=True, key="cdd_com_tel")
                        com_email_cdd = st.toggle("Apenas com e-mail", value=False, key="cdd_com_email")
                    with ct2:
                        tipo_tel = st.radio("Tipo de telefone", ["Todos", "Somente celular", "Somente fixo"], key="cdd_tipo_tel")
                        excl_contab = st.toggle("Excluir e-mails de contabilidade", value=True, key="cdd_excl_contab")

                apenas_novos_cdd = st.toggle(
                    "🔄 Apenas leads novos (remover repetidos de buscas anteriores)",
                    value=True, key="cdd_apenas_novos",
                    help="Remove empresas com CNPJ ou telefone já salvos em buscas anteriores.",
                )

                btn_cdd = st.form_submit_button("🔍 Buscar na Casa dos Dados", use_container_width=True, type="primary")

            if btn_cdd:
                from modules.casa_dos_dados import buscar as cdd_buscar

                # Monta lista de CNAEs
                cnaes_codigos = [op.split(" — ")[0].strip() for op in cnaes_sel]
                if cnae_manual.strip():
                    cnaes_codigos += [c.strip() for c in cnae_manual.split(",") if c.strip()]
                cnaes_codigos = list(dict.fromkeys(cnaes_codigos))  # deduplication mantendo ordem

                if not cnaes_codigos:
                    st.error("Selecione ao menos um CNAE para buscar.")
                else:
                    # Porte
                    porte_codigos = [op.split(" — ")[0].strip() for op in portes_sel] or None

                    # Matriz/filial
                    mf_map = {"Somente Matriz": "MATRIZ", "Somente Filial": "FILIAL"}
                    mf_val = mf_map.get(matriz_fil, "")

                    # Simples
                    simples_optante = True if simples_op == "Apenas optantes" else None
                    excluir_simples = simples_op == "Excluir optantes"

                    # MEI
                    mei_optante = True if mei_op == "Apenas MEI" else None
                    excluir_mei = mei_op == "Excluir MEI"

                    # Tipo de telefone
                    so_cel = tipo_tel == "Somente celular"
                    so_fix = tipo_tel == "Somente fixo"

                    # Datas
                    dt_ini_str = dt_ini.strftime("%Y-%m-%d") if dt_ini else ""
                    dt_fim_str = dt_fim.strftime("%Y-%m-%d") if dt_fim else ""

                    # Capital
                    cap_min_v = int(cap_min) if cap_min else None
                    cap_max_v = int(cap_max) if cap_max else None

                    # Deduplicação
                    excl_tels_cdd, excl_cnpjs_cdd = set(), set()
                    if apenas_novos_cdd:
                        from modules.database import buscar_identificadores_existentes
                        excl_tels_cdd, excl_cnpjs_cdd = buscar_identificadores_existentes()

                    local_cdd = mun_cdd.strip() or uf_cdd
                    nicho_label = CODIGO_PARA_DESC.get(cnaes_codigos[0], cnaes_codigos[0]) if cnaes_codigos else "CDD"

                    bar_cdd = st.progress(0, text="Buscando…")
                    def _cb_cdd(a, t, m):
                        v = min(a / max(t, 1), 1.0)
                        bar_cdd.progress(v, text=str(m)[:120])

                    try:
                        res_cdd = cdd_buscar(
                            api_key=cdd_key,
                            cnaes=cnaes_codigos,
                            uf=uf_cdd,
                            municipio=mun_cdd.strip(),
                            porte=porte_codigos,
                            matriz_filial=mf_val,
                            simples_optante=simples_optante,
                            excluir_simples=excluir_simples,
                            mei_optante=mei_optante,
                            excluir_mei=excluir_mei,
                            com_telefone=com_tel,
                            com_email=com_email_cdd,
                            somente_celular=so_cel,
                            somente_fixo=so_fix,
                            excluir_email_contab=excl_contab,
                            data_abertura_inicio=dt_ini_str,
                            data_abertura_fim=dt_fim_str,
                            capital_min=cap_min_v,
                            capital_max=cap_max_v,
                            limite=lim_cdd,
                            exclude_phones=excl_tels_cdd if apenas_novos_cdd else None,
                            exclude_cnpjs=excl_cnpjs_cdd if apenas_novos_cdd else None,
                            callback=_cb_cdd,
                        )
                        bar_cdd.progress(1.0, text=f"Concluído! {len(res_cdd)} resultados.")
                        bar_cdd.empty()
                        st.session_state["rf_res"] = res_cdd
                        st.session_state["rf_prefix"] = f"cdd_{local_cdd.lower().replace(' ','_')}"
                    except Exception as e:
                        bar_cdd.empty()
                        st.error(f"Erro: {e}")
                        st.session_state["rf_res"] = []
                    else:
                        try:
                            from modules.database import salvar_pesquisa, salvar_leads
                            sid = salvar_pesquisa(nicho_label, ", ".join(cnaes_codigos), mun_cdd.strip(), uf_cdd, local_cdd, "casa_dos_dados", len(res_cdd))
                            if sid: salvar_leads(sid, res_cdd)
                        except Exception:
                            pass
                        if st.session_state.get("auto_export_enabled"):
                            st.session_state["_auto_exp_rf"] = True

        if st.session_state.get("rf_res"):
            res = st.session_state["rf_res"]
            if st.session_state.pop("_auto_exp_rf", False):
                _planilhas = st.session_state.get("sheets_planilhas", [])
                _padrao = next((p for p in _planilhas if p.get("padrao")), None)
                if _padrao and st.session_state.get("sheets_creds"):
                    from modules.google_sheets import exportar
                    with st.spinner(f"Auto-exportando para {_padrao['nome']}…"):
                        _ok, _msg = exportar(res, st.session_state["sheets_creds"],
                                             _padrao["id"], _padrao["aba"],
                                             _padrao.get("modo","substituir"))
                    if _ok:
                        st.success(_msg)
                    else:
                        st.error(_msg)
                elif not st.session_state.get("sheets_creds"):
                    st.warning("Auto-export: conta Google não vinculada.")
                else:
                    st.warning("Auto-export: nenhuma planilha padrão ⭐ definida.")
            st.success(f"✅ **{len(res)}** resultados")
            _stats(res); _dl_buttons(res, st.session_state.get("rf_prefix","prospecao_cdd"), "sheets_creds" in st.session_state and bool(st.session_state.get("sheets_planilhas")))
            st.markdown("#### Prévia"); _tabela(res)


def pagina_historico():
    from modules.database import listar_pesquisas, buscar_leads_da_pesquisa, deletar_pesquisa

    st.markdown(
        '<div class="page-header">'
        '<div class="page-header-icon">📁</div>'
        '<div><div class="page-title">Histórico</div>'
        '<div class="page-sub">Todas as suas extrações anteriores com leads salvos</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    pesquisas = listar_pesquisas()
    if not pesquisas:
        st.info("Nenhuma pesquisa salva ainda. Faça sua primeira busca!", icon="💡")
        return

    for p in pesquisas:
        dt = p.get("created_at","")[:16].replace("T"," ") if p.get("created_at") else "—"
        fonte_icon = "🗺️" if p.get("fonte") == "maps" else "📋"
        nicho = p.get("nicho","—"); sub = p.get("subnicho",""); loc = p.get("localidade","—")
        total = p.get("total_results", 0)
        titulo = f"{fonte_icon} **{nicho}**" + (f" · {sub}" if sub else "") + f" — {loc}"

        with st.expander(f"{titulo}  ·  {total} leads  ·  {dt}"):
            col_a, col_b = st.columns([6,1])
            with col_b:
                if st.button("🗑️ Apagar", key=f"del_{p['id']}"):
                    ok, msg = deletar_pesquisa(p["id"])
                    (st.success if ok else st.error)(msg)
                    if ok: time.sleep(0.5); st.rerun()

            leads = buscar_leads_da_pesquisa(p["id"])
            if not leads:
                st.caption("Nenhum lead salvo para esta pesquisa.")
                continue

            ts = int(time.time())
            slug = f"{nicho[:12]}_{loc[:12]}".lower().replace(" ","_").replace(",","")
            _planilhas_h = st.session_state.get("sheets_planilhas", [])

            # Executa exportação pendente fora do popover
            _hreq = st.session_state.pop(f"_hexp_req_{p['id']}", None)
            if _hreq and leads:
                _hp = next((x for x in _planilhas_h if x["id"] == _hreq), None)
                if _hp:
                    _export_to_planilha(leads, _hp)

            c1, c2, c3 = st.columns(3)
            with c1: st.download_button("⬇️ Excel",_xlsx(leads),f"{slug}_{ts}.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True,key=f"xl_{p['id']}")
            with c2: st.download_button("⬇️ CSV",_csv(leads),f"{slug}_{ts}.csv","text/csv",use_container_width=True,key=f"csv_{p['id']}")
            with c3:
                if "sheets_creds" in st.session_state and _planilhas_h:
                    with st.popover("📊 Google Sheets", use_container_width=True):
                        st.markdown("**Exportar para:**")
                        for _ph in _planilhas_h:
                            _badge = " ⭐" if _ph.get("padrao") else ""
                            _lbl = f"{_ph['nome']}{_badge} → {_ph['aba']} ({_ph.get('modo','substituir')})"
                            if st.button(_lbl, key=f"hexp_{_ph['id'][:8]}_{p['id'][:8]}", use_container_width=True):
                                st.session_state[f"_hexp_req_{p['id']}"] = _ph["id"]
                                st.rerun()
                else:
                    sheets_tip = "Conecte sua conta Google em ⚙️ Configurações." if "sheets_creds" not in st.session_state else "Adicione uma planilha em ⚙️ Configurações."
                    st.button("📊 Google Sheets", disabled=True, use_container_width=True, help=sheets_tip, key=f"hgs_{p['id']}")

            import pandas as pd
            vis=["nome","telefone","email","municipio","uf","site","avaliacao","cnpj"]
            lm={c:l for c,l in ALL_COLS}; df=pd.DataFrame(leads)
            st.dataframe(df[[c for c in vis if c in df.columns]].rename(columns=lm).fillna("").astype(str).replace("nan",""), use_container_width=True, height=280)


# ── Configurações ──────────────────────────────────────────────────────────────

def pagina_configuracoes():
    from modules.database import carregar_configuracoes, salvar_configuracoes
    from modules.google_sheets import gerar_url_auth

    st.markdown(
        '<div class="page-header">'
        '<div class="page-header-icon">⚙️</div>'
        '<div><div class="page-title">Configurações</div>'
        '<div class="page-sub">Gerencie suas credenciais e integrações</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    cfg = carregar_configuracoes()

    # ── Google Maps ─────────────────────────────────────────────────────────────
    with st.expander("🗺️ Google Maps API", expanded=True):
        st.markdown("Insira sua chave de API do Google Maps (Places API).")
        gmk = st.text_input(
            "Chave de API",
            value=cfg.get("google_maps_api_key",""),
            type="password",
            placeholder="AIzaSy...",
            key="cfg_gmaps",
        )
        if st.button("💾 Salvar chave Maps", key="save_gmaps"):
            ok, msg = salvar_configuracoes({"google_maps_api_key": gmk})
            (st.success if ok else st.error)(msg)
            if ok:
                st.session_state["user_gmaps_key"] = gmk

    # ── Google Sheets OAuth ─────────────────────────────────────────────────────
    with st.expander("📊 Google Sheets (OAuth)", expanded=True):
        st.markdown("Conecte sua conta Google para exportar resultados diretamente para planilhas.")

        # Credenciais OAuth vêm sempre das secrets do app (não por usuário)
        cid = _s("GOOGLE_CLIENT_ID")
        cs  = _s("GOOGLE_CLIENT_SECRET")
        ru  = cfg.get("app_url","") or _s("APP_URL","http://localhost:8501")

        if not (cid and cs):
            st.warning(
                "As credenciais Google OAuth não estão configuradas nas secrets do app.\n\n"
                "Adicione `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` e `APP_URL` nas **Secrets** do Streamlit Cloud.",
                icon="⚠️",
            )
        else:
            # Exibe erro de OAuth persistente (não usa pop — sobrevive a reruns)
            if st.session_state.get("_oauth_err"):
                st.error(f"Erro ao conectar conta Google:\n\n`{st.session_state['_oauth_err']}`", icon="❌")
                if st.button("✖ Fechar erro", key="clear_oauth_err"):
                    st.session_state.pop("_oauth_err", None)
                    st.rerun()

            if "sheets_creds" in st.session_state:
                st.success("✅ Conta Google vinculada!", icon="✅")

                from modules.google_sheets import listar_planilhas, listar_abas, extrair_sheet_id

                def _salvar_planilhas():
                    return salvar_configuracoes({"google_sheets_creds": {
                        "oauth":       st.session_state["sheets_creds"],
                        "planilhas":   st.session_state.get("sheets_planilhas", []),
                        "auto_export": st.session_state.get("auto_export_enabled", False),
                    }})

                # ── Auto-export toggle ──────────────────────────────────────────
                auto_val = st.session_state.get("auto_export_enabled", False)
                auto_new = st.toggle(
                    "🔄 Exportar automaticamente após cada busca (planilha padrão ⭐)",
                    value=auto_val, key="cfg_auto_export",
                )
                if auto_new != auto_val:
                    st.session_state["auto_export_enabled"] = auto_new
                    _salvar_planilhas()

                st.markdown("---")
                st.markdown("**📋 Planilhas configuradas**")

                # ── Lista de planilhas cadastradas ──────────────────────────────
                planilhas_cfg = st.session_state.get("sheets_planilhas", [])
                if not planilhas_cfg:
                    st.caption("Nenhuma planilha adicionada ainda.")
                else:
                    for i, p in enumerate(planilhas_cfg):
                        badge = " ⭐" if p.get("padrao") else ""
                        c_info, c_pad, c_del = st.columns([6, 2, 1])
                        with c_info:
                            st.markdown(f"**{p['nome']}{badge}** · `{p['aba']}` · {p.get('modo','substituir')}")
                        with c_pad:
                            if not p.get("padrao"):
                                if st.button("⭐ Padrão", key=f"pad_{i}", use_container_width=True):
                                    for j in range(len(planilhas_cfg)):
                                        planilhas_cfg[j]["padrao"] = (j == i)
                                    st.session_state["sheets_planilhas"] = planilhas_cfg
                                    _salvar_planilhas()
                                    st.rerun()
                        with c_del:
                            if st.button("🗑️", key=f"del_p_{i}", use_container_width=True):
                                planilhas_cfg.pop(i)
                                st.session_state["sheets_planilhas"] = planilhas_cfg
                                _salvar_planilhas()
                                st.rerun()

                # ── Formulário: adicionar planilha ──────────────────────────────
                st.markdown("")
                with st.expander("➕ Adicionar planilha", expanded=False):
                    # Carrega lista do Drive (uma vez por sessão)
                    _lista_err = None
                    if "sheets_lista" not in st.session_state:
                        with st.spinner("Buscando planilhas no Google Drive..."):
                            try:
                                st.session_state["sheets_lista"] = listar_planilhas(st.session_state["sheets_creds"])
                            except Exception as e:
                                st.session_state["sheets_lista"] = []
                                _lista_err = str(e)

                    drive_lista = st.session_state.get("sheets_lista", [])

                    if _lista_err:
                        st.warning(
                            f"Não foi possível listar planilhas do Drive: {_lista_err}\n\n"
                            "Habilite a **Google Drive API** no Cloud Console ou cole a URL abaixo.",
                            icon="⚠️",
                        )

                    # Seleção: Drive ou URL manual
                    _new_id, _new_nome_drive = "", ""
                    if drive_lista:
                        nomes_drive = ["— cole URL manualmente —"] + [p["name"] for p in drive_lista]
                        ids_drive   = [""] + [p["id"] for p in drive_lista]
                        escolha_drive = st.selectbox("Escolher do Google Drive", nomes_drive, key="add_drive_sel")
                        idx_d = nomes_drive.index(escolha_drive)
                        _new_id = ids_drive[idx_d]
                        _new_nome_drive = escolha_drive if _new_id else ""

                    url_add = st.text_input(
                        "URL ou ID da planilha" if not drive_lista else "Ou cole a URL manualmente",
                        placeholder="https://docs.google.com/spreadsheets/d/...",
                        key="add_sheet_url",
                    )
                    if url_add.strip():
                        _new_id = extrair_sheet_id(url_add.strip()) or url_add.strip()
                        _new_nome_drive = ""

                    # Nome de exibição
                    nome_add = st.text_input("Nome de exibição", value=_new_nome_drive,
                                             placeholder="Ex: Advocacia SP", key="add_nome")

                    # Carrega abas se há ID
                    _abas_add = []
                    if _new_id:
                        _cache_key     = f"_abas_add_{_new_id}"
                        _cache_err_key = f"_abas_err_{_new_id}"
                        if _cache_key not in st.session_state:
                            with st.spinner("Carregando abas..."):
                                try:
                                    st.session_state[_cache_key] = listar_abas(
                                        st.session_state["sheets_creds"], _new_id)
                                    st.session_state.pop(_cache_err_key, None)
                                except Exception as e:
                                    st.session_state[_cache_key]     = []
                                    st.session_state[_cache_err_key] = str(e)
                        _abas_add = st.session_state.get(_cache_key, [])

                    _abas_err = st.session_state.get(f"_abas_err_{_new_id}") if _new_id else None
                    if _abas_err:
                        st.warning(
                            "**Não foi possível carregar as abas desta planilha.**\n\n"
                            "A **Google Sheets API** não está habilitada no seu projeto Google Cloud. "
                            "Para ativar: [Google Cloud Console](https://console.cloud.google.com) → "
                            "**APIs e Serviços → Biblioteca** → procure *Google Sheets API* → **Ativar**.\n\n"
                            f"Erro: `{_abas_err}`\n\n"
                            "Enquanto isso, **digite o nome da aba manualmente** abaixo.",
                            icon="⚠️",
                        )
                        if _new_id and st.button("🔄 Tentar novamente", key=f"retry_abas_{_new_id[:8]}"):
                            st.session_state.pop(f"_abas_add_{_new_id}", None)
                            st.session_state.pop(f"_abas_err_{_new_id}", None)
                            st.rerun()

                    if _abas_add:
                        aba_add = st.selectbox("Aba destino", _abas_add, key="add_aba_sel")
                    else:
                        aba_add = st.text_input(
                            "Nome da aba *",
                            placeholder="Ex: Planilha1, Leads, Dados…",
                            key="add_aba_txt",
                            help="Digite o nome exato da aba (verifique no rodapé da planilha no Google Sheets).",
                        )

                    modo_add = st.selectbox("Modo de exportação", ["acrescentar", "substituir"], key="add_modo")
                    padrao_add = st.checkbox("⭐ Definir como planilha padrão (auto-export)", key="add_padrao")

                    if st.button("💾 Adicionar planilha", type="primary", use_container_width=True, key="btn_add_planilha"):
                        if not _new_id:
                            st.error("Selecione uma planilha ou cole a URL.")
                        elif not nome_add.strip():
                            st.error("Informe um nome de exibição.")
                        elif not aba_add.strip():
                            st.error("Informe o nome da aba.")
                        else:
                            nova = {
                                "id":    _new_id,
                                "nome":  nome_add.strip(),
                                "aba":   aba_add.strip(),
                                "modo":  modo_add,
                                "padrao": padrao_add,
                            }
                            lista = st.session_state.get("sheets_planilhas", [])
                            if padrao_add:
                                for existing in lista:
                                    existing["padrao"] = False
                            lista.append(nova)
                            st.session_state["sheets_planilhas"] = lista
                            st.session_state.pop(f"_abas_add_{_new_id}", None)
                            st.session_state.pop(f"_abas_err_{_new_id}", None)
                            ok_save, err_save = _salvar_planilhas()
                            if ok_save:
                                st.toast(f"✅ Planilha **{nova['nome']}** adicionada!")
                            else:
                                st.toast(f"❌ Erro ao salvar: {err_save}", icon="❌")
                            st.rerun()

                st.markdown("")
                if st.button("🔓 Desconectar conta Google", key="disc_google"):
                    for k in ["sheets_creds", "sheets_planilhas", "auto_export_enabled", "sheets_lista"]:
                        st.session_state.pop(k, None)
                    salvar_configuracoes({"google_sheets_creds": None})
                    st.rerun()
            else:
                url = gerar_url_auth(cid, cs, ru)
                st.link_button("🔗 Conectar conta Google", url, use_container_width=True)

    # ── Alterar senha ────────────────────────────────────────────────────────────
    with st.expander("🔑 Alterar senha", expanded=False):
        np1 = st.text_input("Nova senha", type="password", key="cfg_np1")
        np2 = st.text_input("Confirmar nova senha", type="password", key="cfg_np2")
        if st.button("🔐 Alterar senha", key="btn_alterar_senha"):
            if not np1:
                st.warning("Digite a nova senha.")
            elif np1 != np2:
                st.error("As senhas não coincidem.")
            elif len(np1) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            else:
                from modules.auth import redefinir_senha
                uid = st.session_state.get("user",{}).get("id","")
                ok, msg = redefinir_senha(uid, np1)
                (st.success if ok else st.error)(msg)


# ── Admin ──────────────────────────────────────────────────────────────────────

def pagina_admin():
    from modules.auth import (
        listar_usuarios, criar_usuario, deletar_usuario,
        alterar_role, redefinir_senha,
    )

    st.markdown(
        '<div class="page-header">'
        '<div class="page-header-icon">👑</div>'
        '<div><div class="page-title">Painel Admin</div>'
        '<div class="page-sub">Gerencie os usuários da plataforma</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Criar usuário ────────────────────────────────────────────────────────────
    with st.expander("➕ Criar novo usuário", expanded=False):
        c1, c2, c3 = st.columns([3,2,1])
        with c1: new_email = st.text_input("E-mail", key="adm_email", placeholder="usuario@empresa.com")
        with c2: new_senha = st.text_input("Senha inicial", type="password", key="adm_senha", placeholder="Mín. 6 caracteres")
        with c3: new_role  = st.selectbox("Papel", ["user","admin"], key="adm_role")
        if st.button("✅ Criar usuário", key="btn_criar_user"):
            if not new_email or not new_senha:
                st.warning("Preencha e-mail e senha.")
            elif len(new_senha) < 6:
                st.error("Senha deve ter pelo menos 6 caracteres.")
            else:
                ok, msg = criar_usuario(new_email.strip(), new_senha, new_role)
                (st.success if ok else st.error)(msg)
                if ok: time.sleep(0.3); st.rerun()

    st.markdown("---")

    # ── Lista de usuários ────────────────────────────────────────────────────────
    ok, usuarios, err = listar_usuarios()
    if not ok:
        st.error(f"Não foi possível carregar usuários: {err}")
        return
    if not usuarios:
        st.info("Nenhum usuário cadastrado.")
        return

    st.markdown(f"**{len(usuarios)} usuário(s) cadastrado(s)**")

    for u in usuarios:
        uid       = u.get("id","")
        email     = u.get("email","—")
        role      = u.get("role","user")
        created   = (u.get("created_at","") or "")[:10]
        searches  = u.get("total_searches", 0) or 0
        leads_tot = u.get("total_leads", 0) or 0
        last_s    = (u.get("last_search_at","") or "")[:10] or "nunca"
        me        = st.session_state.get("user",{}).get("id","") == uid

        badge = "🟢 admin" if role == "admin" else "⚪ user"
        label = f"{badge}  **{email}**" + ("  *(você)*" if me else "")

        with st.expander(label):
            st.caption(f"ID: `{uid}`  ·  Criado em {created}  ·  {searches} pesquisas  ·  {leads_tot} leads  ·  Última busca: {last_s}")

            col_r, col_p, col_d = st.columns(3)

            with col_r:
                novo_role = st.selectbox(
                    "Papel", ["user","admin"],
                    index=0 if role == "user" else 1,
                    key=f"role_{uid}",
                )
                if st.button("🔄 Alterar papel", key=f"btn_role_{uid}", disabled=me):
                    ok2, msg2 = alterar_role(uid, novo_role)
                    (st.success if ok2 else st.error)(msg2)
                    if ok2: time.sleep(0.3); st.rerun()

            with col_p:
                nova_senha = st.text_input("Nova senha", type="password", key=f"pw_{uid}", placeholder="Mín. 6 caracteres")
                if st.button("🔑 Redefinir senha", key=f"btn_pw_{uid}"):
                    if not nova_senha or len(nova_senha) < 6:
                        st.warning("Mínimo 6 caracteres.")
                    else:
                        ok3, msg3 = redefinir_senha(uid, nova_senha)
                        (st.success if ok3 else st.error)(msg3)

            with col_d:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Remover usuário", key=f"del_u_{uid}", disabled=me, type="secondary"):
                    ok4, msg4 = deletar_usuario(uid)
                    (st.success if ok4 else st.error)(msg4)
                    if ok4: time.sleep(0.3); st.rerun()


# ── Sidebar & roteamento principal ────────────────────────────────────────────

def _sidebar():
    from modules.auth import logout, eh_admin

    with st.sidebar:
        # ── Brand ──────────────────────────────────────────────
        user = st.session_state.get("user", {})
        role = user.get("role", "user")
        logo = _logo_html(30)
        st.markdown(
            f'<div class="brand-header">'
            f'<div style="display:flex;align-items:center;gap:10px">'
            f'{logo}'
            f'<div><div class="brand-title">Lead Extractor</div>'
            f'<div class="brand-sub">Revolução AI</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # ── User card ───────────────────────────────────────────
        role_cls   = "role-admin" if role == "admin" else "role-user"
        role_label = "Admin" if role == "admin" else "Usuário"
        st.markdown(
            f'<div class="user-card">'
            f'<div class="user-email">{user.get("email","")}</div>'
            f'<span class="user-role-badge {role_cls}">{role_label}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

        # ── Nav — sem emojis, texto limpo ────────────────────────
        page = st.session_state.get("page", "busca")
        nav_items = [
            ("busca",         "Busca"),
            ("historico",     "Histórico"),
            ("configuracoes", "Configurações"),
        ]
        if eh_admin():
            nav_items.append(("admin", "Admin"))

        st.markdown('<div style="padding:0 8px">', unsafe_allow_html=True)
        for key, label in nav_items:
            if st.button(label, use_container_width=True, key=f"nav_{key}",
                         type="primary" if page == key else "secondary"):
                st.session_state["page"] = key
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Logout ──────────────────────────────────────────────
        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        st.markdown('<hr style="border-color:#141828;margin:0 8px 12px">', unsafe_allow_html=True)
        st.markdown('<div style="padding:0 8px">', unsafe_allow_html=True)
        if st.button("Sair", use_container_width=True, key="nav_logout", type="secondary"):
            logout()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def main():
    from modules.auth import usuario_logado, eh_admin, supabase_configurado, restaurar_sessao
    import extra_streamlit_components as stx
    from datetime import datetime, timedelta

    if not supabase_configurado():
        st.error(
            "⚠️ **Supabase não configurado.**\n\n"
            "Adicione `SUPABASE_URL` e `SUPABASE_ANON_KEY` nos segredos do Streamlit "
            "(Settings → Secrets) ou no arquivo `.env`.",
            icon="🔒",
        )
        st.stop()

    # ── CookieManager sempre renderizado ─────────────────────────────────────
    # st.context.cookies não funciona no Community Cloud (CDN remove headers HTTP).
    # CookieManager usa JavaScript/WebSocket (document.cookie) — funciona sempre.
    # Só dispara reruns quando o valor do cookie muda — navegação normal é rápida.
    cm = stx.CookieManager(key="__le_cm")

    # ── Restaura sessão do cookie ─────────────────────────────────────────────
    if "user" not in st.session_state:
        if not st.session_state.get("_cm_init_done"):
            # Primeiro render: CookieManager ainda não inicializou (retorna None).
            # Seta flag e para — CookieManager dispara rerun automático (~100-300ms).
            st.session_state["_cm_init_done"] = True
            st.stop()
        rt = cm.get(_COOKIE_NAME)
        if rt:
            restaurar_sessao(rt)

    # ── Persiste sheets_creds no Supabase se veio de redirect OAuth ──────────
    if "user" in st.session_state and st.session_state.pop("_pending_sheets_save", False):
        if st.session_state.get("sheets_creds"):
            from modules.database import salvar_configuracoes
            salvar_configuracoes({"google_sheets_creds": {
                "oauth":      st.session_state["sheets_creds"],
                "planilhas":  st.session_state.get("sheets_planilhas", []),
                "auto_export": st.session_state.get("auto_export_enabled", False),
            }})

    # ── Escreve cookie após login ─────────────────────────────────────────────
    if st.session_state.get("_pending_rt"):
        rt = st.session_state.pop("_pending_rt")
        cm.set(_COOKIE_NAME, rt, expires_at=datetime.now() + timedelta(days=30))

    # ── Apaga cookie no logout ────────────────────────────────────────────────
    if st.session_state.get("_do_logout_cookie"):
        try:
            cm.delete(_COOKIE_NAME)
        except Exception:
            pass
        st.session_state.pop("_do_logout_cookie", None)

    user = usuario_logado()

    if not user:
        pagina_login()
        return

    _sidebar()

    page = st.session_state.get("page", "busca")

    if page == "busca":
        pagina_busca()
    elif page == "historico":
        pagina_historico()
    elif page == "configuracoes":
        pagina_configuracoes()
    elif page == "admin":
        if eh_admin():
            pagina_admin()
        else:
            st.error("Acesso negado.")
    else:
        pagina_busca()


if __name__ == "__main__" or True:
    main()
