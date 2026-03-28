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
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
  font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: #334155; }

/* ═══════════════════════════════════════════════════════════
   APP SHELL — Background + Ambient Glow
═══════════════════════════════════════════════════════════ */
.stApp {
  background: #020617 !important;
}
[data-testid="stAppViewContainer"] {
  background: transparent !important;
}
/* Ambient green glow top-center */
[data-testid="stAppViewContainer"]::before {
  content: '';
  position: fixed; top: -180px; left: 50%; transform: translateX(-50%);
  width: 700px; height: 400px;
  background: radial-gradient(ellipse, #00D97E06 0%, transparent 70%);
  pointer-events: none; z-index: 0;
}
.block-container {
  padding: 2.25rem 2.75rem 5rem !important;
  max-width: 1340px !important;
  position: relative; z-index: 1;
}

/* ═══════════════════════════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #030918 0%, #020510 100%) !important;
  border-right: 1px solid #0c1425 !important;
  box-shadow: 4px 0 24px #00000030 !important;
}
[data-testid="stSidebarContent"] { padding: 0 !important; }
[data-testid="stSidebar"] hr {
  margin: 4px 14px !important;
  border: none !important;
  border-top: 1px solid #0c1425 !important;
}

/* Sidebar nav buttons */
[data-testid="stSidebar"] [data-testid="stButton"] > button {
  width: 100% !important;
  text-align: left !important;
  justify-content: flex-start !important;
  padding: 10px 14px !important;
  border-radius: 10px !important;
  font-size: 0.84rem !important;
  font-weight: 500 !important;
  transition: all 0.18s cubic-bezier(.4,0,.2,1) !important;
  margin: 1px 0 !important;
  border: none !important;
  letter-spacing: 0.005em !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="secondary"] {
  background: transparent !important;
  color: #475569 !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="secondary"]:hover {
  background: #0a1020 !important;
  color: #e2e8f0 !important;
  transform: translateX(2px) !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(135deg, #062215 0%, #041810 100%) !important;
  color: #00D97E !important;
  border: 1px solid #00D97E18 !important;
  font-weight: 700 !important;
  box-shadow: 0 0 20px #00D97E08 !important;
}

/* ═══════════════════════════════════════════════════════════
   TEXT INPUTS
═══════════════════════════════════════════════════════════ */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {
  background: #070b18 !important;
  border: 1px solid #131c32 !important;
  border-radius: 10px !important;
  color: #e2e8f0 !important;
  padding: 10px 14px !important;
  font-size: 0.875rem !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stDateInput"] input:focus {
  border-color: #00D97E40 !important;
  box-shadow: 0 0 0 3px #00D97E0a, 0 0 16px #00D97E08 !important;
  outline: none !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stNumberInput"] input::placeholder { color: #293548 !important; }

/* Selects / Multiselect */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
  background: #070b18 !important;
  border: 1px solid #131c32 !important;
  border-radius: 10px !important;
  color: #e2e8f0 !important;
}
[data-testid="stSelectbox"] > div > div:focus-within,
[data-testid="stMultiSelect"] > div > div:focus-within {
  border-color: #00D97E40 !important;
  box-shadow: 0 0 0 3px #00D97E0a !important;
}

/* Multiselect tags */
[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
  background: #0a1e14 !important;
  border: 1px solid #00D97E22 !important;
  border-radius: 6px !important;
  color: #00D97E !important;
  font-weight: 600 !important;
  font-size: 0.78rem !important;
}

/* Slider track */
[data-testid="stSlider"] [role="slider"] {
  background: #00D97E !important;
  border: 2px solid #020617 !important;
  box-shadow: 0 0 8px #00D97E40 !important;
}

/* ═══════════════════════════════════════════════════════════
   FORMS
═══════════════════════════════════════════════════════════ */
[data-testid="stForm"] {
  background: linear-gradient(165deg, #070c1c 0%, #050914 50%, #060b18 100%) !important;
  border: 1px solid #0e1830 !important;
  border-radius: 16px !important;
  padding: 24px 26px !important;
  box-shadow: 0 4px 32px #00000050, 0 1px 0 #ffffff04 inset !important;
}

/* ═══════════════════════════════════════════════════════════
   BUTTONS
═══════════════════════════════════════════════════════════ */
[data-testid="stButton"] > button,
[data-testid="stDownloadButton"] > button {
  border-radius: 10px !important;
  font-weight: 600 !important;
  font-size: 0.84rem !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  transition: all 0.2s cubic-bezier(.4,0,.2,1) !important;
  letter-spacing: 0.01em !important;
  padding: 8px 18px !important;
  min-height: unset !important;
  height: auto !important;
}

/* Primary button — gradient with glow */
[data-testid="stButton"] > button[kind="primary"],
button[kind="primaryFormSubmit"] {
  background: linear-gradient(135deg, #00D97E 0%, #00b366 100%) !important;
  color: #012010 !important;
  border: none !important;
  font-weight: 800 !important;
  box-shadow: 0 0 0 1px #00D97E20, 0 2px 8px #00000030, 0 4px 20px #00D97E20 !important;
  padding: 10px 22px !important;
  letter-spacing: 0.02em !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover,
button[kind="primaryFormSubmit"]:hover {
  background: linear-gradient(135deg, #00f08e 0%, #00c874 100%) !important;
  box-shadow: 0 0 0 1px #00D97E30, 0 4px 12px #00000030, 0 8px 32px #00D97E30 !important;
  transform: translateY(-1px) !important;
}
[data-testid="stButton"] > button[kind="primary"]:active,
button[kind="primaryFormSubmit"]:active {
  transform: translateY(0px) scale(0.98) !important;
  box-shadow: 0 0 0 1px #00D97E20, 0 1px 4px #00000030 !important;
}

/* Secondary button */
[data-testid="stButton"] > button[kind="secondary"] {
  background: #070b18 !important;
  border: 1px solid #131c32 !important;
  color: #64748b !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover {
  background: #0a1020 !important;
  border-color: #1e293b !important;
  color: #e2e8f0 !important;
}

/* Download */
[data-testid="stDownloadButton"] > button {
  background: #070b18 !important;
  border: 1px solid #131c32 !important;
  color: #64748b !important;
}
[data-testid="stDownloadButton"] > button:hover {
  background: #081510 !important;
  border-color: #143828 !important;
  color: #00D97E !important;
}

/* ═══════════════════════════════════════════════════════════
   TABS
═══════════════════════════════════════════════════════════ */
[data-testid="stTabs"] [role="tablist"] {
  background: #040810 !important;
  border-radius: 12px !important;
  padding: 5px !important;
  border: 1px solid #0c1425 !important;
  gap: 3px !important;
}
[data-testid="stTabs"] [role="tab"] {
  border-radius: 9px !important;
  color: #3e4c66 !important;
  font-weight: 600 !important;
  font-size: 0.845rem !important;
  padding: 9px 22px !important;
  transition: all 0.2s cubic-bezier(.4,0,.2,1) !important;
  border: none !important;
  letter-spacing: 0.005em !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  background: linear-gradient(135deg, #071e14 0%, #041410 100%) !important;
  color: #00D97E !important;
  font-weight: 700 !important;
  box-shadow: 0 2px 12px #00000040, 0 0 20px #00D97E08 !important;
  border: 1px solid #00D97E15 !important;
}
[data-testid="stTabs"] [role="tab"]:hover:not([aria-selected="true"]) {
  background: #080e1c !important;
  color: #94a3b8 !important;
}

/* ═══════════════════════════════════════════════════════════
   EXPANDERS
═══════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {
  background: #040810 !important;
  border: 1px solid #0c1425 !important;
  border-radius: 14px !important;
  margin-bottom: 10px !important;
  overflow: hidden !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stExpander"]:hover {
  border-color: #162040 !important;
  box-shadow: 0 4px 20px #00000020 !important;
}
[data-testid="stExpander"] summary {
  padding: 14px 20px !important;
  color: #94a3b8 !important;
  font-weight: 600 !important;
  font-size: 0.88rem !important;
  transition: all 0.15s !important;
}
[data-testid="stExpander"] summary:hover {
  background: #080e1c !important;
  color: #e2e8f0 !important;
}
[data-testid="stExpander"] > div > div { padding: 0 20px 18px !important; }

/* ═══════════════════════════════════════════════════════════
   ALERTS — Each with left accent bar
═══════════════════════════════════════════════════════════ */
[data-testid="stAlert"] {
  border-radius: 12px !important;
  border-width: 0 0 0 3px !important;
  font-size: 0.87rem !important;
}
.stSuccess {
  background: linear-gradient(135deg, #03110a 0%, #020c07 100%) !important;
  border-color: #00D97E !important;
}
.stInfo {
  background: linear-gradient(135deg, #020a1c 0%, #020714 100%) !important;
  border-color: #3b82f6 !important;
}
.stWarning {
  background: linear-gradient(135deg, #110d02 0%, #0c0901 100%) !important;
  border-color: #f59e0b !important;
}
.stError {
  background: linear-gradient(135deg, #120303 0%, #0e0202 100%) !important;
  border-color: #ef4444 !important;
}

/* ═══════════════════════════════════════════════════════════
   PROGRESS BAR
═══════════════════════════════════════════════════════════ */
[data-testid="stProgress"] { margin: 12px 0 !important; }
[data-testid="stProgress"] > div {
  background: #0c1425 !important;
  border-radius: 99px !important;
  height: 6px !important;
}
[data-testid="stProgress"] > div > div {
  background: linear-gradient(90deg, #00a85e, #00D97E, #00f090) !important;
  border-radius: 99px !important;
  box-shadow: 0 0 12px #00D97E50, 0 0 4px #00D97E80 !important;
}

/* ═══════════════════════════════════════════════════════════
   DATAFRAME — Dark styled table
═══════════════════════════════════════════════════════════ */
.stDataFrame { border-radius: 14px !important; overflow: hidden !important; }
.stDataFrame [data-testid="stDataFrameResizable"] {
  border: 1px solid #0c1425 !important;
  border-radius: 14px !important;
}

/* ═══════════════════════════════════════════════════════════
   LABELS & CAPTIONS
═══════════════════════════════════════════════════════════ */
[data-testid="stCaptionContainer"] { color: #334155 !important; font-size: 0.76rem !important; }
[data-testid="stWidgetLabel"] {
  color: #64748b !important;
  font-size: 0.76rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.06em !important;
  text-transform: uppercase !important;
}
[data-testid="stToggle"] { background: transparent !important; padding: 6px 0 !important; }

/* Radio buttons styling */
[data-testid="stRadio"] > div > label {
  font-size: 0.85rem !important;
  color: #94a3b8 !important;
}

/* Popover styling */
[data-testid="stPopover"] > div {
  background: #070b18 !important;
  border: 1px solid #131c32 !important;
  border-radius: 14px !important;
  box-shadow: 0 8px 40px #00000060 !important;
}

/* ═══════════════════════════════════════════════════════════
   SIDEBAR BRAND
═══════════════════════════════════════════════════════════ */
.brand-header {
  padding: 22px 18px 18px;
  background: linear-gradient(170deg, #071220 0%, #030918 100%);
  border-bottom: 1px solid #0c1425;
  position: relative;
}
.brand-header::after {
  content: '';
  position: absolute; bottom: -1px; left: 18px; right: 18px;
  height: 1px;
  background: linear-gradient(90deg, #00D97E20, transparent 50%);
}
.brand-dot {
  width: 36px; height: 36px;
  background: linear-gradient(135deg, #00D97E 0%, #009955 100%);
  border-radius: 10px;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 800; color: #020e06; font-size: 15px;
  box-shadow: 0 2px 12px #00D97E45, 0 0 0 2px #00D97E18;
  vertical-align: middle; margin-right: 10px; flex-shrink: 0;
}
.brand-title {
  font-size: 0.95rem; font-weight: 800; color: #f1f5f9;
  line-height: 1.2; letter-spacing: -0.025em;
}
.brand-sub {
  font-size: 0.58rem; font-weight: 700;
  background: linear-gradient(90deg, #00D97E, #34d399);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  text-transform: uppercase; letter-spacing: 0.18em; margin-top: 3px;
}

/* ═══════════════════════════════════════════════════════════
   USER CARD
═══════════════════════════════════════════════════════════ */
.user-card {
  margin: 10px 12px 6px;
  background: linear-gradient(160deg, #070c1c 0%, #050914 100%);
  border: 1px solid #0e1830;
  border-radius: 12px; padding: 12px 14px;
  position: relative;
}
.user-avatar {
  width: 32px; height: 32px; border-radius: 8px;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 800; color: #64748b;
  border: 1px solid #1e293b; flex-shrink: 0;
}
.user-info { flex: 1; min-width: 0; }
.user-email {
  font-size: 0.78rem; color: #94a3b8; font-weight: 600;
  word-break: break-all; line-height: 1.3;
}
.user-role-badge {
  display: inline-flex; align-items: center; gap: 4px;
  margin-top: 6px; padding: 2px 10px;
  border-radius: 99px; font-size: 0.6rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.12em;
}
.role-admin {
  background: linear-gradient(135deg, #052e18 0%, #031f10 100%);
  color: #00D97E;
  border: 1px solid #00D97E22;
  box-shadow: 0 0 8px #00D97E10;
}
.role-user {
  background: linear-gradient(135deg, #0a1230 0%, #070c20 100%);
  color: #60a5fa;
  border: 1px solid #3b82f622;
}

/* ═══════════════════════════════════════════════════════════
   PAGE HEADER
═══════════════════════════════════════════════════════════ */
.page-header {
  margin-bottom: 2rem; padding-bottom: 1.75rem;
  border-bottom: 1px solid #0c1425;
  display: flex; align-items: center; gap: 16px;
  position: relative;
}
.page-header::after {
  content: '';
  position: absolute; bottom: -1px; left: 0; width: 120px; height: 1px;
  background: linear-gradient(90deg, #00D97E30, transparent);
}
.page-header-icon {
  width: 48px; height: 48px; border-radius: 14px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(145deg, #0a1628 0%, #060e1e 100%);
  border: 1px solid #131c32;
  box-shadow: 0 2px 12px #00000030, inset 0 1px 0 #ffffff05;
}
.page-header-icon svg { width: 22px; height: 22px; }
.page-title {
  font-size: 1.65rem; font-weight: 800; letter-spacing: -0.035em;
  line-height: 1.1; color: #f1f5f9; margin-bottom: 0.25rem;
}
.page-sub {
  font-size: 0.84rem; color: #475569; font-weight: 400; line-height: 1.5;
}

/* ═══════════════════════════════════════════════════════════
   STAT CARDS — Individual accent colors
═══════════════════════════════════════════════════════════ */
.stats-row {
  display: grid; grid-template-columns: repeat(4,1fr);
  gap: 14px; margin: 1.5rem 0;
}
.stat-card {
  background: linear-gradient(165deg, #070c1c 0%, #050914 100%);
  border: 1px solid #0e1830;
  border-radius: 16px; padding: 20px 22px;
  position: relative; overflow: hidden;
  transition: border-color 0.25s, transform 0.25s, box-shadow 0.25s;
}
.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 40px #00000040;
}
/* Top accent line — color set by inline style */
.stat-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: var(--accent);
  opacity: 0.5;
}
/* Corner glow */
.stat-card::after {
  content: ''; position: absolute;
  top: -20px; right: -20px;
  width: 70px; height: 70px;
  background: radial-gradient(circle, var(--accent-glow, #00D97E08), transparent 70%);
  border-radius: 50%;
}
.stat-card:hover { border-color: var(--accent-border, #00D97E18); }
.stat-icon {
  width: 40px; height: 40px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 14px;
  background: var(--icon-bg, #041a0e);
  border: 1px solid var(--icon-border, #00D97E18);
}
.stat-icon svg { width: 20px; height: 20px; stroke-width: 2; fill: none; }
.stat-num {
  font-size: 2rem; font-weight: 800; line-height: 1;
  letter-spacing: -0.04em;
  color: var(--accent-text, #00D97E);
}
.stat-lbl {
  font-size: 0.68rem; color: #475569; margin-top: 6px;
  text-transform: uppercase; letter-spacing: 0.12em; font-weight: 700;
}

/* ═══════════════════════════════════════════════════════════
   SECTION LABEL
═══════════════════════════════════════════════════════════ */
.sec {
  font-size: 0.65rem; font-weight: 700; color: #00D97E;
  text-transform: uppercase; letter-spacing: 0.15em;
  margin: 1.1rem 0 0.45rem;
  display: flex; align-items: center; gap: 10px;
}
.sec::after {
  content: ''; flex: 1; height: 1px;
  background: linear-gradient(90deg, #00D97E15, transparent);
}

/* ═══════════════════════════════════════════════════════════
   INFO BOX
═══════════════════════════════════════════════════════════ */
.info-box {
  background: linear-gradient(135deg, #060c18 0%, #040810 100%);
  border: 1px solid #0e1830;
  border-left: 3px solid #00D97E50;
  border-radius: 10px; padding: 14px 18px;
  font-size: 0.84rem; color: #64748b; line-height: 1.7;
  margin-bottom: 1.25rem;
}
.info-box strong { color: #94a3b8; font-weight: 700; }

/* ═══════════════════════════════════════════════════════════
   DIVIDER
═══════════════════════════════════════════════════════════ */
.hr { border: none; border-top: 1px solid #0c1425; margin: 1rem 0; }

/* ═══════════════════════════════════════════════════════════
   BADGES
═══════════════════════════════════════════════════════════ */
.badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px; border-radius: 99px;
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em;
}
.b-ok   { background: #041a0e; color: #00D97E; border: 1px solid #00D97E22; }
.b-warn { background: #120d02; color: #f59e0b; border: 1px solid #f59e0b22; }
.b-err  { background: #130304; color: #f87171; border: 1px solid #ef444422; }

/* ═══════════════════════════════════════════════════════════
   LOGIN PAGE — Premium centered card
═══════════════════════════════════════════════════════════ */
.login-wrapper {
  position: relative;
  max-width: 400px; margin: 0 auto;
}
/* Ambient glow behind login card */
.login-wrapper::before {
  content: '';
  position: absolute; top: -60px; left: 50%; transform: translateX(-50%);
  width: 300px; height: 200px;
  background: radial-gradient(ellipse, #00D97E12, transparent 70%);
  pointer-events: none;
}
[data-testid="stForm"] { padding: 32px 30px 26px !important; }
.login-head { text-align: center; padding: 0 0 24px; }
.login-title {
  font-size: 1.35rem; font-weight: 800; color: #f1f5f9;
  letter-spacing: -0.03em; margin-top: 16px; line-height: 1.2;
}
.login-sub {
  font-size: 0.6rem; font-weight: 700;
  background: linear-gradient(90deg, #00D97E, #34d399);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  letter-spacing: 0.18em; text-transform: uppercase; margin-top: 6px;
}

/* ═══════════════════════════════════════════════════════════
   NAV ICONS — SVG inline in sidebar buttons
═══════════════════════════════════════════════════════════ */
.nav-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; margin-right: 10px; flex-shrink: 0;
  vertical-align: middle;
}
.nav-icon svg {
  width: 18px; height: 18px;
  stroke-width: 1.8; fill: none; stroke: currentColor;
}

/* ═══════════════════════════════════════════════════════════
   RESPONSIVE — Stat cards 2 cols on narrow screens
═══════════════════════════════════════════════════════════ */
@media (max-width: 768px) {
  .stats-row { grid-template-columns: repeat(2,1fr) !important; }
  .block-container { padding: 1.5rem 1.25rem 4rem !important; }
  .page-title { font-size: 1.3rem !important; }
  .page-header-icon { width: 40px; height: 40px; border-radius: 12px; }
  .page-header-icon svg { width: 18px; height: 18px; }
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
    return (f'<div style="width:{size}px;height:{size}px;'
            f'background:linear-gradient(135deg,#00D97E,#009955);'
            f'border-radius:{r2}px;display:inline-flex;align-items:center;'
            f'justify-content:center;font-size:{fs}px;font-weight:800;color:#012010;'
            f'box-shadow:0 2px 12px #00D97E40,0 0 0 2px #00D97E18">R</div>')
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
    _stat_cfg = [
        (tot, "Total leads",
         "#00D97E", "#041a0e", "#00D97E18", "#00D97E08", "#00D97E18",
         '<svg viewBox="0 0 24 24" stroke="#00D97E"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>'),
        (tel, "Com telefone",
         "#3b82f6", "#071530", "#3b82f618", "#3b82f608", "#3b82f618",
         '<svg viewBox="0 0 24 24" stroke="#3b82f6"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>'),
        (site, "Com site",
         "#a855f7", "#120730", "#a855f718", "#a855f708", "#a855f718",
         '<svg viewBox="0 0 24 24" stroke="#a855f7"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>'),
        (em, "Com e-mail",
         "#f59e0b", "#1a1005", "#f59e0b18", "#f59e0b08", "#f59e0b18",
         '<svg viewBox="0 0 24 24" stroke="#f59e0b"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>'),
    ]
    cards = ""
    for n, l, accent, icon_bg, icon_border, glow, border_h, svg in _stat_cfg:
        cards += (
            f'<div class="stat-card" style="--accent:{accent};--accent-glow:{glow};--accent-border:{border_h};--accent-text:{accent};--icon-bg:{icon_bg};--icon-border:{icon_border}">'
            f'<div class="stat-icon">{svg}</div>'
            f'<div class="stat-num">{n}</div>'
            f'<div class="stat-lbl">{l}</div>'
            f'</div>'
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
    # Centralização vertical
    st.markdown("<div style='height:14vh'></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1.2, 1.6, 1.2])
    with col:
        st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
        with st.form("login"):
            st.markdown(
                f'<div class="login-head">'
                f'{_logo_html(56)}'
                f'<div class="login-title">Lead Extractor</div>'
                f'<div class="login-sub">Revolução AI</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            email = st.text_input("E-mail", placeholder="seu@email.com")
            senha = st.text_input("Senha", type="password", placeholder="••••••••")
            st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
            btn   = st.form_submit_button("Entrar", use_container_width=True, type="primary")
        st.markdown('</div>', unsafe_allow_html=True)
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
        '<div class="page-header-icon"><svg viewBox="0 0 24 24" stroke="#00D97E" fill="none" stroke-width="1.8"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></div>'
        '<div><div class="page-title">Nova Busca</div>'
        '<div class="page-sub">Busque leads por nicho e localidade usando Google Maps ou Casa dos Dados</div></div>'
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
        '<div class="page-header-icon"><svg viewBox="0 0 24 24" stroke="#3b82f6" fill="none" stroke-width="1.8"><path d="M3 3v5h5"/><path d="M3.05 13A9 9 0 1 0 6 5.3L3 8"/><path d="M12 7v5l4 2"/></svg></div>'
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
        '<div class="page-header-icon"><svg viewBox="0 0 24 24" stroke="#a855f7" fill="none" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg></div>'
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
        '<div class="page-header-icon"><svg viewBox="0 0 24 24" stroke="#f59e0b" fill="none" stroke-width="1.8"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></div>'
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

_NAV_ICONS = {
    "busca":         '<svg viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.8"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    "historico":     '<svg viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.8"><path d="M3 3v5h5"/><path d="M3.05 13A9 9 0 1 0 6 5.3L3 8"/><path d="M12 7v5l4 2"/></svg>',
    "configuracoes": '<svg viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    "admin":         '<svg viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.8"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "logout":        '<svg viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.8"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',
}

def _sidebar():
    from modules.auth import logout, eh_admin

    with st.sidebar:
        # ── Brand ──────────────────────────────────────────────
        user = st.session_state.get("user", {})
        role = user.get("role", "user")
        logo = _logo_html(32)
        st.markdown(
            f'<div class="brand-header">'
            f'<div style="display:flex;align-items:center;gap:10px">'
            f'{logo}'
            f'<div><div class="brand-title">Lead Extractor</div>'
            f'<div class="brand-sub">Revolução AI</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # ── User card with avatar ──────────────────────────────
        email = user.get("email", "")
        initial = email[0].upper() if email else "U"
        role_cls   = "role-admin" if role == "admin" else "role-user"
        role_label = "Admin" if role == "admin" else "Usuário"
        st.markdown(
            f'<div class="user-card">'
            f'<div style="display:flex;align-items:center;gap:10px">'
            f'<div class="user-avatar">{initial}</div>'
            f'<div class="user-info">'
            f'<div class="user-email">{email}</div>'
            f'<span class="user-role-badge {role_cls}">{role_label}</span>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

        # ── Nav with SVG icons ────────────────────────────────
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
            icon_html = f'<span class="nav-icon">{_NAV_ICONS.get(key,"")}</span>'
            if st.button(f"{label}", use_container_width=True, key=f"nav_{key}",
                         type="primary" if page == key else "secondary"):
                st.session_state["page"] = key
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Logout ──────────────────────────────────────────────
        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        st.markdown('<hr style="border:none;border-top:1px solid #0c1425;margin:0 14px 12px">', unsafe_allow_html=True)
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
