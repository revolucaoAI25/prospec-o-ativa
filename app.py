"""Lead Extractor · Revolução AI"""
import os, io, csv, time, json, logging
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

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
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,opsz,wght@0,14..32,300;0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700;0,14..32,800&display=swap');


/* ═══════════════════════════════════════════════════════════
   DESIGN TOKENS
═══════════════════════════════════════════════════════════ */
:root {
  --bg-deep:     #03040a;
  --bg-base:     #050710;
  --surface:     rgba(255, 255, 255, 0.035);
  --surface-2:   rgba(255, 255, 255, 0.06);
  --border:      rgba(255, 255, 255, 0.08);
  --border-muted:rgba(255, 255, 255, 0.04);
  --text-1: #f1f5f9;
  --text-2: #94a3b8;
  --text-3: #4b5a72;
  --accent:      #00D97E;
  --accent-dim:  rgba(0, 217, 126, 0.15);
  --accent-glow: rgba(0, 217, 126, 0.22);
  --ease: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out: cubic-bezier(0.0, 0.0, 0.2, 1);
  --radius-sm: 10px;
  --radius-md: 16px;
  --radius-lg: 22px;
}

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
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.18); }

/* ═══════════════════════════════════════════════════════════
   APP SHELL — Atmospheric dark background with color blobs
═══════════════════════════════════════════════════════════ */
.stApp {
  background-color: var(--bg-deep) !important;
  /* Atmospheric ambient blobs — each radial-gradient is a floating color orb */
  background-image:
    radial-gradient(ellipse 55vw 45vh at 12% 18%,  rgba(0, 217, 126, 0.055) 0%, transparent 65%),
    radial-gradient(ellipse 50vw 50vh at 88% 78%,  rgba(59, 130, 246, 0.045) 0%, transparent 65%),
    radial-gradient(ellipse 40vw 55vh at 60% 35%,  rgba(139, 92, 246, 0.03)  0%, transparent 65%),
    radial-gradient(ellipse 70vw 30vh at 50% 100%, rgba(0, 217, 126, 0.025)  0%, transparent 70%) !important;
}
[data-testid="stAppViewContainer"] { background: transparent !important; }
.block-container {
  padding: 2.5rem 3rem 6rem !important;
  max-width: 1360px !important;
  position: relative;
}

/* ═══════════════════════════════════════════════════════════
   SIDEBAR — Frosted glass panel
═══════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
  background: rgba(3, 5, 14, 0.85) !important;
  backdrop-filter: blur(24px) saturate(160%) !important;
  -webkit-backdrop-filter: blur(24px) saturate(160%) !important;
  border-right: 1px solid var(--border) !important;
  box-shadow: 8px 0 40px rgba(0,0,0,0.5) !important;
}
[data-testid="stSidebarContent"] { padding: 0 !important; }
[data-testid="stSidebar"] hr {
  margin: 4px 14px !important;
  border: none !important;
  border-top: 1px solid var(--border-muted) !important;
}

/* Sidebar nav buttons */
[data-testid="stSidebar"] [data-testid="stButton"] > button {
  width: 100% !important;
  text-align: left !important;
  justify-content: flex-start !important;
  padding: 10px 14px !important;
  border-radius: var(--radius-sm) !important;
  font-size: 0.845rem !important;
  font-weight: 500 !important;
  transition: background 0.18s var(--ease), color 0.18s var(--ease), transform 0.18s var(--ease) !important;
  margin: 1px 0 !important;
  border: none !important;
  letter-spacing: 0.01em !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="secondary"] {
  background: transparent !important;
  color: var(--text-3) !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="secondary"]:hover {
  background: var(--surface-2) !important;
  color: var(--text-1) !important;
  transform: translateX(3px) !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"] {
  background: var(--accent-dim) !important;
  color: var(--accent) !important;
  border: 1px solid rgba(0,217,126,0.2) !important;
  font-weight: 700 !important;
  box-shadow: 0 0 24px rgba(0,217,126,0.08), inset 0 1px 0 rgba(255,255,255,0.06) !important;
}

/* ═══════════════════════════════════════════════════════════
   TEXT INPUTS — Dark recessed look with hairline border
═══════════════════════════════════════════════════════════ */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {
  background: rgba(0, 0, 0, 0.35) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text-1) !important;
  padding: 10px 14px !important;
  font-size: 0.875rem !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  transition: border-color 0.2s var(--ease), box-shadow 0.2s var(--ease) !important;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.4) !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stDateInput"] input:focus {
  border-color: rgba(0,217,126,0.4) !important;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.4), 0 0 0 3px rgba(0,217,126,0.08), 0 0 20px rgba(0,217,126,0.06) !important;
  outline: none !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stNumberInput"] input::placeholder { color: var(--text-3) !important; opacity: 0.7 !important; }

/* Selects / Multiselect */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
  background: rgba(0, 0, 0, 0.35) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text-1) !important;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.3) !important;
}
[data-testid="stSelectbox"] > div > div:focus-within,
[data-testid="stMultiSelect"] > div > div:focus-within {
  border-color: rgba(0,217,126,0.4) !important;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.3), 0 0 0 3px rgba(0,217,126,0.08) !important;
}

/* Multiselect tags */
[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
  background: rgba(0, 217, 126, 0.1) !important;
  border: 1px solid rgba(0, 217, 126, 0.22) !important;
  border-radius: 6px !important;
  color: var(--accent) !important;
  font-weight: 600 !important;
  font-size: 0.78rem !important;
}

/* Slider thumb */
[data-testid="stSlider"] [role="slider"] {
  background: var(--accent) !important;
  border: 2px solid var(--bg-deep) !important;
  box-shadow: 0 0 10px var(--accent-glow) !important;
}

/* ═══════════════════════════════════════════════════════════
   FORMS — True glassmorphism floating panels
═══════════════════════════════════════════════════════════ */
[data-testid="stForm"] {
  background: var(--surface) !important;
  backdrop-filter: blur(32px) saturate(160%) !important;
  -webkit-backdrop-filter: blur(32px) saturate(160%) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  padding: 28px 30px !important;
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.03) inset,
    0 1px 0 rgba(255,255,255,0.07) inset,
    0 8px 40px rgba(0,0,0,0.6),
    0 2px 8px rgba(0,0,0,0.3) !important;
}

/* ═══════════════════════════════════════════════════════════
   BUTTONS
═══════════════════════════════════════════════════════════ */
[data-testid="stButton"] > button,
[data-testid="stDownloadButton"] > button {
  border-radius: var(--radius-sm) !important;
  font-weight: 600 !important;
  font-size: 0.84rem !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  transition: all 0.22s var(--ease) !important;
  letter-spacing: 0.015em !important;
  padding: 8px 18px !important;
  min-height: unset !important;
  height: auto !important;
  cursor: pointer !important;
}

/* Primary — solid green with strong halo glow */
[data-testid="stButton"] > button[kind="primary"],
button[kind="primaryFormSubmit"] {
  background: linear-gradient(160deg, #00E88A 0%, #00C472 50%, #00A85E 100%) !important;
  color: #01180c !important;
  border: 1px solid rgba(0,217,126,0.3) !important;
  font-weight: 800 !important;
  letter-spacing: 0.02em !important;
  padding: 10px 24px !important;
  box-shadow:
    0 1px 0 rgba(255,255,255,0.25) inset,
    0 2px 4px rgba(0,0,0,0.4),
    0 4px 16px rgba(0,217,126,0.25),
    0 8px 40px rgba(0,217,126,0.15) !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover,
button[kind="primaryFormSubmit"]:hover {
  background: linear-gradient(160deg, #00F593 0%, #00D97E 50%, #00BF6A 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow:
    0 1px 0 rgba(255,255,255,0.3) inset,
    0 4px 8px rgba(0,0,0,0.4),
    0 8px 24px rgba(0,217,126,0.35),
    0 16px 60px rgba(0,217,126,0.2) !important;
}
[data-testid="stButton"] > button[kind="primary"]:active,
button[kind="primaryFormSubmit"]:active {
  transform: translateY(0) scale(0.97) !important;
  box-shadow:
    0 1px 0 rgba(255,255,255,0.2) inset,
    0 1px 4px rgba(0,0,0,0.4),
    0 2px 8px rgba(0,217,126,0.2) !important;
}

/* Secondary — glass surface */
[data-testid="stButton"] > button[kind="secondary"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-3) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.05) !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover {
  background: var(--surface-2) !important;
  border-color: rgba(255,255,255,0.14) !important;
  color: var(--text-1) !important;
}

/* Download */
[data-testid="stDownloadButton"] > button {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-3) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.05) !important;
}
[data-testid="stDownloadButton"] > button:hover {
  background: rgba(0,217,126,0.08) !important;
  border-color: rgba(0,217,126,0.25) !important;
  color: var(--accent) !important;
}

/* ═══════════════════════════════════════════════════════════
   TABS — Glass pill container
═══════════════════════════════════════════════════════════ */
[data-testid="stTabs"] [role="tablist"] {
  background: rgba(0,0,0,0.3) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  border-radius: var(--radius-md) !important;
  padding: 5px !important;
  border: 1px solid var(--border) !important;
  gap: 3px !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.04) !important;
}
[data-testid="stTabs"] [role="tab"] {
  border-radius: 12px !important;
  color: var(--text-3) !important;
  font-weight: 600 !important;
  font-size: 0.845rem !important;
  padding: 9px 22px !important;
  transition: all 0.22s var(--ease) !important;
  border: none !important;
  letter-spacing: 0.01em !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  background: var(--accent-dim) !important;
  color: var(--accent) !important;
  font-weight: 700 !important;
  border: 1px solid rgba(0,217,126,0.2) !important;
  box-shadow:
    0 2px 12px rgba(0,0,0,0.4),
    0 0 24px rgba(0,217,126,0.1),
    inset 0 1px 0 rgba(255,255,255,0.08) !important;
}
[data-testid="stTabs"] [role="tab"]:hover:not([aria-selected="true"]) {
  background: var(--surface) !important;
  color: var(--text-2) !important;
}

/* ═══════════════════════════════════════════════════════════
   EXPANDERS — Minimal glass with top-edge shimmer
═══════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {
  background: var(--surface) !important;
  backdrop-filter: blur(16px) !important;
  -webkit-backdrop-filter: blur(16px) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  margin-bottom: 10px !important;
  overflow: hidden !important;
  transition: border-color 0.22s var(--ease), box-shadow 0.22s var(--ease) !important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.06),
    0 2px 12px rgba(0,0,0,0.3) !important;
}
[data-testid="stExpander"]:hover {
  border-color: rgba(255,255,255,0.14) !important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 4px 24px rgba(0,0,0,0.4) !important;
}
[data-testid="stExpander"] summary {
  padding: 15px 20px !important;
  color: var(--text-2) !important;
  font-weight: 600 !important;
  font-size: 0.875rem !important;
  transition: color 0.15s, background 0.15s !important;
}
[data-testid="stExpander"] summary:hover {
  background: var(--surface-2) !important;
  color: var(--text-1) !important;
}
[data-testid="stExpander"] > div > div { padding: 2px 20px 20px !important; }

/* ═══════════════════════════════════════════════════════════
   ALERTS — Glass with colored left accent bar
═══════════════════════════════════════════════════════════ */
[data-testid="stAlert"] {
  background: var(--surface) !important;
  backdrop-filter: blur(16px) !important;
  -webkit-backdrop-filter: blur(16px) !important;
  border-radius: var(--radius-sm) !important;
  border: 1px solid var(--border) !important;
  border-left-width: 3px !important;
  font-size: 0.87rem !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.05), 0 2px 12px rgba(0,0,0,0.3) !important;
}
.stSuccess { border-left-color: #00D97E !important; }
.stInfo    { border-left-color: #3b82f6 !important; }
.stWarning { border-left-color: #f59e0b !important; }
.stError   { border-left-color: #ef4444 !important; }

/* ═══════════════════════════════════════════════════════════
   PROGRESS BAR — Glowing green track
═══════════════════════════════════════════════════════════ */
[data-testid="stProgress"] { margin: 14px 0 !important; }
[data-testid="stProgress"] > div {
  background: rgba(255,255,255,0.06) !important;
  border-radius: 99px !important;
  height: 5px !important;
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.4) !important;
}
[data-testid="stProgress"] > div > div {
  background: linear-gradient(90deg, #00a85e 0%, #00D97E 60%, #5effa8 100%) !important;
  border-radius: 99px !important;
  box-shadow: 0 0 16px rgba(0,217,126,0.6), 0 0 4px rgba(0,217,126,0.9) !important;
}

/* ═══════════════════════════════════════════════════════════
   DATAFRAME
═══════════════════════════════════════════════════════════ */
.stDataFrame { border-radius: var(--radius-md) !important; overflow: hidden !important; }
.stDataFrame [data-testid="stDataFrameResizable"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
}

/* ═══════════════════════════════════════════════════════════
   LABELS & CAPTIONS
═══════════════════════════════════════════════════════════ */
[data-testid="stCaptionContainer"] { color: var(--text-3) !important; font-size: 0.76rem !important; }
[data-testid="stWidgetLabel"] {
  color: var(--text-3) !important;
  font-size: 0.73rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.07em !important;
  text-transform: uppercase !important;
}
[data-testid="stToggle"] { background: transparent !important; padding: 6px 0 !important; }
[data-testid="stRadio"] > div > label {
  font-size: 0.85rem !important;
  color: var(--text-2) !important;
}

/* Popover */
[data-testid="stPopover"] > div {
  background: rgba(6, 8, 20, 0.9) !important;
  backdrop-filter: blur(24px) !important;
  -webkit-backdrop-filter: blur(24px) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  box-shadow: 0 8px 40px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.06) !important;
}

/* ═══════════════════════════════════════════════════════════
   SIDEBAR BRAND — No flat rectangle; just atmosphere
═══════════════════════════════════════════════════════════ */
.brand-header {
  padding: 24px 18px 20px;
  position: relative;
  /* Subtle green aurora at top of brand area */
  background: radial-gradient(ellipse 150% 120% at 40% -30%, rgba(0,217,126,0.07) 0%, transparent 70%) !important;
  border-bottom: 1px solid var(--border-muted);
}
.brand-header::after {
  content: '';
  position: absolute; bottom: -1px; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0,217,126,0.15), transparent);
}
.brand-dot {
  width: 36px; height: 36px;
  background: linear-gradient(145deg, #00E88A 0%, #00C472 100%);
  border-radius: 11px;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 800; color: #01180c; font-size: 15px;
  /* Double ring: accent glow + hairline white */
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.15),
    0 2px 8px rgba(0,0,0,0.5),
    0 0 24px rgba(0,217,126,0.4);
  vertical-align: middle; margin-right: 10px; flex-shrink: 0;
}
.brand-title {
  font-size: 0.95rem; font-weight: 800; color: var(--text-1);
  line-height: 1.2; letter-spacing: -0.025em;
}
.brand-sub {
  font-size: 0.58rem; font-weight: 700;
  background: linear-gradient(90deg, #00D97E 0%, #5effa8 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  text-transform: uppercase; letter-spacing: 0.2em; margin-top: 3px;
}

/* ═══════════════════════════════════════════════════════════
   USER CARD — Glass inset panel
═══════════════════════════════════════════════════════════ */
.user-card {
  margin: 10px 12px 6px;
  background: rgba(0,0,0,0.2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
}
.user-avatar {
  width: 32px; height: 32px; border-radius: 8px;
  background: var(--surface-2);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 800; color: var(--text-2);
  border: 1px solid var(--border); flex-shrink: 0;
}
.user-info { flex: 1; min-width: 0; }
.user-email {
  font-size: 0.78rem; color: var(--text-2); font-weight: 500;
  word-break: break-all; line-height: 1.3;
}
.user-role-badge {
  display: inline-flex; align-items: center; gap: 4px;
  margin-top: 6px; padding: 2px 10px;
  border-radius: 99px; font-size: 0.6rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.12em;
}
.role-admin {
  background: rgba(0,217,126,0.1);
  color: var(--accent);
  border: 1px solid rgba(0,217,126,0.2);
}
.role-user {
  background: rgba(59,130,246,0.1);
  color: #60a5fa;
  border: 1px solid rgba(59,130,246,0.2);
}

/* ═══════════════════════════════════════════════════════════
   PAGE HEADER — Minimal, content-forward
═══════════════════════════════════════════════════════════ */
.page-header {
  margin-bottom: 2.25rem; padding-bottom: 2rem;
  border-bottom: 1px solid var(--border-muted);
  display: flex; align-items: center; gap: 18px;
  position: relative;
}
.page-header::after {
  content: '';
  position: absolute; bottom: -1px; left: 0; width: 200px; height: 1px;
  background: linear-gradient(90deg, rgba(0,217,126,0.25), transparent);
}
.page-header-icon {
  width: 50px; height: 50px; border-radius: 15px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 4px 16px rgba(0,0,0,0.3);
}
.page-header-icon svg { width: 23px; height: 23px; }
.page-title {
  font-size: 1.75rem; font-weight: 800; letter-spacing: -0.04em;
  line-height: 1.1; color: var(--text-1); margin-bottom: 0.3rem;
}
.page-sub {
  font-size: 0.855rem; color: var(--text-3); font-weight: 400; line-height: 1.55;
}

/* ═══════════════════════════════════════════════════════════
   STAT CARDS — Glass with colored ambient light
═══════════════════════════════════════════════════════════ */
.stats-row {
  display: grid; grid-template-columns: repeat(4,1fr);
  gap: 16px; margin: 1.75rem 0;
}
.stat-card {
  background: var(--surface);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border);
  border-radius: var(--radius-md); padding: 22px 22px 20px;
  position: relative; overflow: hidden;
  transition: transform 0.28s var(--ease), box-shadow 0.28s var(--ease), border-color 0.28s var(--ease);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.07),
    0 2px 16px rgba(0,0,0,0.3);
}
.stat-card:hover {
  transform: translateY(-4px);
  border-color: var(--accent-border, rgba(255,255,255,0.12));
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.1),
    0 16px 48px rgba(0,0,0,0.45),
    0 0 60px var(--accent-glow, rgba(0,217,126,0.06));
}
/* Top shimmer line */
.stat-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent 0%, var(--accent) 50%, transparent 100%);
  opacity: 0.4;
}
/* Ambient radial glow from color */
.stat-card::after {
  content: ''; position: absolute;
  top: -40px; right: -40px;
  width: 120px; height: 120px;
  background: radial-gradient(circle, var(--accent-glow, rgba(0,217,126,0.08)), transparent 70%);
  border-radius: 50%;
  pointer-events: none;
}
.stat-icon {
  width: 42px; height: 42px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 16px;
  background: var(--icon-bg, rgba(0,217,126,0.08));
  border: 1px solid var(--icon-border, rgba(0,217,126,0.15));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
}
.stat-icon svg { width: 20px; height: 20px; stroke-width: 1.8; fill: none; }
.stat-num {
  font-size: 2.1rem; font-weight: 800; line-height: 1;
  letter-spacing: -0.04em;
  color: var(--accent-text, var(--accent));
}
.stat-lbl {
  font-size: 0.67rem; color: var(--text-3); margin-top: 7px;
  text-transform: uppercase; letter-spacing: 0.13em; font-weight: 700;
}

/* ═══════════════════════════════════════════════════════════
   SECTION LABEL — Minimal rule with glow dot
═══════════════════════════════════════════════════════════ */
.sec {
  font-size: 0.65rem; font-weight: 700; color: var(--accent);
  text-transform: uppercase; letter-spacing: 0.16em;
  margin: 1.25rem 0 0.5rem;
  display: flex; align-items: center; gap: 10px;
  opacity: 0.9;
}
.sec::after {
  content: ''; flex: 1; height: 1px;
  background: linear-gradient(90deg, rgba(0,217,126,0.12), transparent);
}

/* ═══════════════════════════════════════════════════════════
   INFO BOX — Glass with accent edge
═══════════════════════════════════════════════════════════ */
.info-box {
  background: var(--surface);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--border);
  border-left: 2px solid rgba(0,217,126,0.5);
  border-radius: var(--radius-sm);
  padding: 14px 18px;
  font-size: 0.855rem; color: var(--text-3); line-height: 1.7;
  margin-bottom: 1.5rem;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
}
.info-box strong { color: var(--text-2); font-weight: 600; }

/* ═══════════════════════════════════════════════════════════
   DIVIDER
═══════════════════════════════════════════════════════════ */
.hr { border: none; border-top: 1px solid var(--border-muted); margin: 1.25rem 0; }

/* ═══════════════════════════════════════════════════════════
   BADGES — Pill glass
═══════════════════════════════════════════════════════════ */
.badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px; border-radius: 99px;
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em;
}
.b-ok   { background: rgba(0,217,126,0.1); color: var(--accent); border: 1px solid rgba(0,217,126,0.2); }
.b-warn { background: rgba(245,158,11,0.1); color: #f59e0b; border: 1px solid rgba(245,158,11,0.2); }
.b-err  { background: rgba(239,68,68,0.1); color: #f87171; border: 1px solid rgba(239,68,68,0.2); }

/* ═══════════════════════════════════════════════════════════
   LOGIN PAGE — Cinematic glass card
═══════════════════════════════════════════════════════════ */
.login-wrapper {
  position: relative; max-width: 400px; margin: 0 auto;
}
.login-wrapper::before {
  content: '';
  position: absolute; top: -80px; left: 50%; transform: translateX(-50%);
  width: 360px; height: 260px;
  background: radial-gradient(ellipse, rgba(0,217,126,0.1), transparent 65%);
  pointer-events: none;
}
[data-testid="stForm"] { padding: 34px 32px 28px !important; }
.login-head { text-align: center; padding: 0 0 26px; }
.login-title {
  font-size: 1.4rem; font-weight: 800; color: var(--text-1);
  letter-spacing: -0.035em; margin-top: 18px; line-height: 1.2;
}
.login-sub {
  font-size: 0.6rem; font-weight: 700;
  background: linear-gradient(90deg, #00D97E 0%, #5effa8 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  letter-spacing: 0.2em; text-transform: uppercase; margin-top: 7px;
}

/* ═══════════════════════════════════════════════════════════
   NAV ICON helper class
═══════════════════════════════════════════════════════════ */
.nav-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; margin-right: 10px; flex-shrink: 0;
  vertical-align: middle;
}
.nav-icon svg { width: 18px; height: 18px; stroke-width: 1.8; fill: none; stroke: currentColor; }

/* ═══════════════════════════════════════════════════════════
   RESPONSIVE
═══════════════════════════════════════════════════════════ */
@media (max-width: 768px) {
  .stats-row { grid-template-columns: repeat(2,1fr) !important; }
  .block-container { padding: 1.5rem 1.25rem 4rem !important; }
  .page-title { font-size: 1.35rem !important; }
  .page-header-icon { width: 42px; height: 42px; }
  .page-header-icon svg { width: 20px; height: 20px; }
}

/* ═══════════════════════════════════════════════════════════
   OCULTAR BRANDING STREAMLIT
   Esconde apenas o menu (⋮) e o footer, sem remover o header
   para não quebrar o botão de reabrir a sidebar.
═══════════════════════════════════════════════════════════ */
#MainMenu { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
footer { visibility: hidden !important; height: 0 !important; }
[data-testid="stDecoration"] { display: none !important; }

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
_EXTRA=[("telefone_internacional","Telefone Intl."),("status_funcionamento","Status"),("porte","Porte")]
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
    vis=[
        "nome","telefone","telefone2","tipo_telefone","email",
        "municipio","uf","endereco","cep",
        "cnpj","nicho_busca","cnae_codigo","subnicho_busca","matriz_filial",
        "natureza_juridica","data_abertura","capital_social",
        "simples_optante","mei_optante","situacao_especial","socio_principal",
        "site","avaliacao","total_avaliacoes","maps_url",
    ]
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
    try:
        with st.spinner(f"Exportando para {planilha['nome']}…"):
            ok, msg = exportar(rows, creds, planilha["id"], planilha["aba"],
                               planilha.get("modo", "substituir"))
        if ok:
            st.success(msg)
        else:
            st.error(msg)
    except Exception as e:
        logger.exception("Erro ao exportar para planilha '%s'", planilha.get("nome", ""))
        st.error("Não foi possível exportar para o Google Sheets. Tente novamente ou reconecte sua conta Google em Configurações.")

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
                           use_container_width=True, key=f"dl_xlsx_{prefix}")
    with c2:
        st.download_button("⬇️ CSV", _csv(rows), f"{prefix}_{ts}.csv",
                           "text/csv", use_container_width=True, key=f"dl_csv_{prefix}")
    with c3:
        try:
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
                          help="Adicione uma planilha em ⚙️ Configurações.", key=f"dl_sheets_nop_{prefix}")
            else:
                st.button("📊 Google Sheets", use_container_width=True, disabled=True,
                          help="Conecte sua conta Google em ⚙️ Configurações.", key=f"dl_sheets_dis_{prefix}")
        except Exception:
            logger.exception("Erro ao renderizar botão Google Sheets (prefix=%s)", prefix)
            st.button("📊 Google Sheets", use_container_width=True, disabled=True,
                      help="Erro ao carregar opções do Google Sheets.", key=f"dl_sheets_err_{prefix}")

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
        '<div class="page-sub">Busque leads por nicho e localidade via Google Maps ou CNPJ com filtros avançados</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Chave do Google Maps — usa chave admin (ou pool) se maps_credits_enabled
    from modules.database import carregar_configuracoes
    _cfg_busca = carregar_configuracoes()
    _maps_credits_enabled = st.session_state.get("maps_credits_enabled", False)
    if _maps_credits_enabled:
        gmaps_key = st.session_state.get("maps_api_key_admin", "")
        if not gmaps_key:
            # Verifica se há pool configurado (para gmaps_ok)
            from modules.auth import obter_pool_maps_usuario_admin
            _pool_adm_check = obter_pool_maps_usuario_admin(
                st.session_state.get("user", {}).get("id", "")
            )
            if _pool_adm_check:
                gmaps_key = _pool_adm_check[0].get("key", "")
    else:
        gmaps_key = _cfg_busca.get("google_maps_api_key", "") or st.session_state.get("user_gmaps_key", "")
        if not gmaps_key:
            from modules.database import obter_pool_maps_usuario
            _pool_usr_check = obter_pool_maps_usuario()
            if _pool_usr_check:
                gmaps_key = _pool_usr_check[0].get("key", "")
    gmaps_ok        = bool(gmaps_key)
    _apify_maps_key = st.session_state.get("apify_api_key_user", "")
    maps_ok         = gmaps_ok or bool(_apify_maps_key)

    _insta_visible = st.session_state.get("instagram_visible", True)
    _tab_labels = ["🗺️  Google Maps  ·  com telefone", "🏢  CNPJ + filtros avançados"]
    if _insta_visible:
        _tab_labels.append("📸  Instagram")
    _tabs = st.tabs(_tab_labels)
    aba_maps = _tabs[0]
    aba_rf   = _tabs[1]
    aba_insta = _tabs[2] if _insta_visible else None

    with aba_maps:
        if not maps_ok:
            if _maps_credits_enabled:
                st.warning("Chave do Google Maps não configurada pelo administrador.", icon="⚠️")
            else:
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

        # País — FORA do form para ser reativo (muda sem precisar submeter)
        _pais_opts = [
            "Brasil", "Estados Unidos", "Portugal", "Argentina", "México",
            "Colômbia", "Chile", "Peru", "Espanha", "Reino Unido",
            "França", "Alemanha", "Itália", "Canadá", "Austrália",
            "Japão", "Outro…",
        ]
        _pc0, _pc1, _pc2 = st.columns([2, 5, 3])
        with _pc0:
            pais_sel = st.selectbox("País", _pais_opts, index=0, label_visibility="collapsed", key="maps_pais")
        is_brasil = pais_sel == "Brasil"

        with st.form("form_maps"):
            st.markdown('<div class="sec">Localidade</div>', unsafe_allow_html=True)

            cc, ce, cl = st.columns([3, 1, 2])
            with cc:
                if pais_sel == "Outro…":
                    cidade = st.text_input("País / Cidade", placeholder="Ex: Dubai, Singapura…", label_visibility="collapsed")
                elif is_brasil:
                    cidade = st.text_input("Cidade", placeholder="Ex: São Paulo", label_visibility="collapsed")
                else:
                    cidade = st.text_input("Cidade / Região (opcional)", placeholder="Ex: Miami, Los Angeles…", label_visibility="collapsed")
            with ce:
                if is_brasil:
                    eopts = ["—"] + SIGLAS_ESTADOS
                    edef = eopts.index("SP") if "SP" in eopts else 0
                    est_raw = st.selectbox("Estado", eopts, index=edef, label_visibility="collapsed")
                    estado = "" if est_raw == "—" else est_raw
                else:
                    estado = ""
            with cl:
                lim = st.slider("Resultados", 20, 500, 60, 20, label_visibility="collapsed")
                st.caption(f"Máx. **{lim}** resultados")
            apenas_novos_maps = st.toggle(
                "🔄 Apenas leads novos (remover repetidos de buscas anteriores)",
                value=True,
                help="Quando ativado, leads com mesmo telefone ou CNPJ de pesquisas anteriores são removidos dos resultados.",
            )
            _tc1, _tc2 = st.columns(2)
            with _tc1:
                show_phone_maps = st.toggle(
                    "📞 Exibir telefone e site",
                    value=True, key="maps_show_phone",
                    help="Busca telefone e site via Place Details. Consome Contact Data (1.000 gratuitas/mês por chave).",
                )
            with _tc2:
                show_rating_maps = st.toggle(
                    "⭐ Exibir avaliações",
                    value=True, key="maps_show_rating",
                    help="Inclui avaliação e nº de reviews. Vem do Text Search — sem custo adicional.",
                )
            buscar_btn = st.form_submit_button("🔍 Buscar no Google Maps", disabled=not maps_ok, use_container_width=True, type="primary")

        if buscar_btn:
            cv, ev = cidade.strip(), estado.strip()
            pais_final = "" if pais_sel in ("Brasil", "Outro…") else pais_sel
            _maps_err = None
            if is_brasil and not cv and not ev:
                _maps_err = "Informe ao menos a cidade ou o estado."
            elif not is_brasil and not cv:
                _maps_err = "Informe o país ou cidade."
            elif is_custom and not query_custom.strip():
                _maps_err = "Informe o termo personalizado."
            elif _maps_credits_enabled:
                from modules.database import obter_creditos_maps
                _saldo_maps = obter_creditos_maps()
                if _saldo_maps < lim:
                    _maps_err = (
                        f"Créditos Maps insuficientes. Você tem **{_saldo_maps}** créditos "
                        f"e a busca requer **{lim}**. Solicite mais créditos ao administrador."
                    )

            if _maps_err:
                st.error(_maps_err)
            else:
                qbase = query_custom.strip() if is_custom else nicho_data["query"]
                nicho_lbl = qbase if is_custom else nicho_sel
                sub_final = "" if (is_custom or subnicho_sel=="Todos (sem filtro)") else (sub_custom.strip() if subnicho_sel=="✏️ Personalizado..." else subnicho_sel)
                if is_brasil:
                    localidade = f"{cv}, {ESTADOS.get(ev,ev)}" if cv and ev else cv or ESTADOS.get(ev, ev)
                else:
                    localidade = f"{cv}, {pais_final}" if cv and pais_final else cv or pais_final
                slug = f"{nicho_lbl[:15]}_{localidade[:15]}".lower().replace(" ","_").replace(",","")
                excl_tels_maps = set()
                if apenas_novos_maps:
                    from modules.database import buscar_identificadores_existentes
                    excl_tels_maps, _ = buscar_identificadores_existentes()
                prog = st.progress(0, text="Iniciando...")
                def _cb(a, t, m):
                    v = min(a / t, 1.0) if t and t > 0 else 0
                    prog.progress(v, text=str(m)[:120])
                # ── Seleção de chave via pool (se configurado) ────────────────
                _pool_ativo   = []
                _pool_key_idx = -1
                _chave_busca  = gmaps_key
                if gmaps_ok:
                    from modules.database import obter_pool_maps_usuario, selecionar_chave_maps
                    _pool_ativo = obter_pool_maps_usuario()
                    if _pool_ativo:
                        _c, _pool_key_idx, _pool_ativo = selecionar_chave_maps(_pool_ativo)
                        if _c:
                            _chave_busca = _c
                        elif not _chave_busca:
                            if _apify_maps_key:
                                _chave_busca = ""  # força fallback Apify
                            else:
                                prog.empty()
                                st.error("Todas as chaves Maps atingiram o limite mensal. Adicione novas chaves ou configure uma chave Apify como fallback.")
                                st.stop()

                _used_apify = False
                _excl = excl_tels_maps if apenas_novos_maps else None
                try:
                    if _chave_busca:
                        from modules.google_maps import buscar as maps_buscar, QuotaExceededError
                        try:
                            res = maps_buscar(query_base=qbase, localidade=localidade, limite=lim,
                                              api_key=_chave_busca, nicho=nicho_lbl, subnicho=sub_final,
                                              cidade=cv, estado=ev, progress_callback=_cb,
                                              exclude_phones=_excl,
                                              show_phone=show_phone_maps, show_rating=show_rating_maps)
                        except QuotaExceededError:
                            if not _apify_maps_key:
                                raise RuntimeError("Cota Google Maps esgotada e nenhuma chave Apify configurada como fallback.")
                            prog.progress(0, text="Cota Google Maps esgotada. Usando Apify como fallback…")
                            _used_apify = True
                            from modules.apify_maps import buscar as apify_buscar
                            res = apify_buscar(query_base=qbase, localidade=localidade, limite=lim,
                                               api_key=_apify_maps_key, nicho=nicho_lbl, subnicho=sub_final,
                                               cidade=cv, estado=ev, progress_callback=_cb,
                                               exclude_phones=_excl,
                                               show_phone=show_phone_maps, show_rating=show_rating_maps)
                    else:
                        # Apify-only (sem chave Google Maps)
                        _used_apify = True
                        from modules.apify_maps import buscar as apify_buscar
                        res = apify_buscar(query_base=qbase, localidade=localidade, limite=lim,
                                           api_key=_apify_maps_key, nicho=nicho_lbl, subnicho=sub_final,
                                           cidade=cv, estado=ev, progress_callback=_cb,
                                           exclude_phones=_excl,
                                           show_phone=show_phone_maps, show_rating=show_rating_maps)
                    prog.progress(1.0, text=f"Concluído! {len(res)} resultados.")
                    prog.empty()
                    st.session_state["maps_res"] = res
                    st.session_state["maps_prefix"] = slug
                except ValueError as e:
                    prog.empty(); st.error(str(e)); st.session_state["maps_res"] = []
                except Exception as e:
                    logger.exception("Erro na busca Google Maps")
                    prog.empty(); st.error("Ocorreu um erro inesperado na busca. Tente novamente."); st.session_state["maps_res"] = []
                else:
                    # Registra uso no pool (somente se usou Google Maps)
                    if not _used_apify and _pool_ativo and _pool_key_idx >= 0:
                        from modules.database import registrar_uso_maps, salvar_pool_maps_usuario
                        salvar_pool_maps_usuario(
                            registrar_uso_maps(_pool_ativo, _pool_key_idx, len(res))
                        )
                    try:
                        from modules.database import salvar_pesquisa, salvar_leads, debitar_creditos_maps
                        sid = salvar_pesquisa(nicho_lbl, sub_final, cv, ev, localidade, "maps", len(res))
                        if sid: salvar_leads(sid, res)
                        if _maps_credits_enabled:
                            debitar_creditos_maps(len(res))
                    except Exception:
                        pass
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
                    st.warning("Exportação automática não realizada: conta Google não vinculada.")
                else:
                    st.warning("Exportação automática não realizada: nenhuma planilha principal configurada.")
            st.success(f"✅ **{len(res)}** resultados")
            _stats(res); _dl_buttons(res, st.session_state.get("maps_prefix","prospecao"), "sheets_creds" in st.session_state and bool(st.session_state.get("sheets_planilhas")))
            st.markdown("#### Prévia"); _tabela(res)

    with aba_rf:
        from modules.cnaes import OPCOES_MULTISELECT, CODIGO_PARA_DESC

        cdd_key = _s("CDD_API_KEY")
        if not cdd_key:
            st.warning(
                "Busca por CNPJ não configurada.  \n"
                "Adicione `CDD_API_KEY` nas **Secrets** do Streamlit Cloud para habilitar esta busca.",
                icon="⚠️",
            )
        else:
            st.markdown('<div class="info-box">Busca direta no cadastro da <strong>Receita Federal</strong>. '
                        'Filtros por CNAE, porte, regime tributário e muito mais. Resultados instantâneos.</div>', unsafe_allow_html=True)

            with st.form("form_cdd"):
                # ── CNAEs ──────────────────────────────────────────────────────
                st.markdown("**CNAE(s)**")
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
                cnae_tipo_cdd = st.radio(
                    "Considerar CNAE como",
                    ["Primário", "Secundário", "Primário ou Secundário"],
                    horizontal=True, key="cdd_cnae_tipo",
                )

                # ── Recuperação Judicial ───────────────────────────────────────
                rj_cdd = st.checkbox(
                    "🏛️ Apenas empresas em Recuperação Judicial",
                    key="cdd_rj",
                    help="Filtra pela razão social contendo 'RECUPERACAO JUDICIAL'. CNAE torna-se opcional.",
                )

                # ── Localização ───────────────────────────────────────────────
                c1, c2 = st.columns(2)
                with c1:
                    uf_cdd = st.selectbox("Estado *", SIGLAS_ESTADOS, index=SIGLAS_ESTADOS.index("SP"), key="cdd_uf")
                with c2:
                    mun_cdd = st.text_input("Município (opcional)", placeholder="Ex: São Paulo", key="cdd_mun")

                lim_cdd = st.slider("Máx. resultados", 1, 2000, 300, 50, key="cdd_lim")

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

                if gmaps_ok:
                    _enr_label = "🗺️ Enriquecer com Google Maps (avaliação, telefone extra, site)"
                    if _maps_credits_enabled:
                        _enr_label += "  — 1 crédito Maps por empresa"
                    enriquecer_maps_cdd = st.toggle(
                        _enr_label, value=False, key="cdd_enriquecer_maps",
                        help="Após buscar, complementa cada empresa com dados do Google Maps.",
                    )
                else:
                    enriquecer_maps_cdd = False

                btn_cdd = st.form_submit_button("🔍 Buscar empresas por CNPJ", use_container_width=True, type="primary")

            if btn_cdd:
                from modules.casa_dos_dados import buscar as cdd_buscar

                # Monta lista de CNAEs
                cnaes_codigos = [op.split(" — ")[0].strip() for op in cnaes_sel]
                if cnae_manual.strip():
                    cnaes_codigos += [c.strip() for c in cnae_manual.split(",") if c.strip()]
                cnaes_codigos = list(dict.fromkeys(cnaes_codigos))  # deduplication mantendo ordem

                # Busca textual: modo Recuperação Judicial
                _busca_textual_cdd = None
                _situacoes_cdd = None
                if rj_cdd:
                    _busca_textual_cdd = [{"texto": ["RECUPERACAO JUDICIAL"], "tipo_busca": "radical", "razao_social": True}]
                    # Inclui SUSPENSA e INAPTA: empresas em RJ frequentemente perdem
                    # o status ATIVA por atraso em obrigações fiscais
                    _situacoes_cdd = ["ATIVA", "SUSPENSA", "INAPTA"]

                if not cnaes_codigos and not rj_cdd:
                    st.error("Selecione ao menos um CNAE para buscar.")
                else:
                    from modules.database import obter_creditos
                    _saldo_cdd = obter_creditos()
                    if _saldo_cdd < lim_cdd:
                        st.error(
                            f"Créditos insuficientes. Você tem **{_saldo_cdd}** créditos "
                            f"e a busca requer **{lim_cdd}**. "
                            f"Reduza o limite de resultados ou solicite mais créditos ao administrador."
                        )
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

                        _cnae_tipo_map = {"Primário": "principal", "Secundário": "secundario", "Primário ou Secundário": "ambos"}
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
                                cnae_tipo=_cnae_tipo_map.get(cnae_tipo_cdd, "principal"),
                                busca_textual=_busca_textual_cdd,
                                situacoes_cadastrais=_situacoes_cdd,
                            )
                            bar_cdd.progress(1.0, text=f"Concluído! {len(res_cdd)} resultados.")
                            bar_cdd.empty()
                            if enriquecer_maps_cdd and res_cdd:
                                _bar_enr2 = st.progress(0, text="Enriquecendo com Google Maps…")
                                def _cb_enr2(a, t, m): _bar_enr2.progress(min(a / max(t, 1), 1.0), text=str(m)[:100])
                                from modules.google_maps import enriquecer_com_maps
                                enriquecer_com_maps(res_cdd, gmaps_key, _cb_enr2)
                                _bar_enr2.empty()
                                st.session_state["_rf_enriched"] = True
                                if _maps_credits_enabled:
                                    from modules.database import debitar_creditos_maps
                                    debitar_creditos_maps(len(res_cdd))
                            else:
                                st.session_state.pop("_rf_enriched", None)
                            st.session_state["rf_res"] = res_cdd
                            st.session_state["rf_prefix"] = f"cdd_{local_cdd.lower().replace(' ','_')}"
                        except Exception as e:
                            logger.exception("Erro na busca CNPJ")
                            bar_cdd.empty()
                            st.error("Ocorreu um erro inesperado na busca. Tente novamente.")
                            st.session_state["rf_res"] = []
                        else:
                            try:
                                from modules.database import salvar_pesquisa, salvar_leads, debitar_creditos
                                sid = salvar_pesquisa(nicho_label, ", ".join(cnaes_codigos), mun_cdd.strip(), uf_cdd, local_cdd, "receita_federal", len(res_cdd))
                                if sid: salvar_leads(sid, res_cdd)
                                debitar_creditos(len(res_cdd))
                            except Exception:
                                pass
                            if st.session_state.get("auto_export_enabled"):
                                st.session_state["_auto_exp_rf"] = True

        if st.session_state.get("rf_res") is not None and not st.session_state.get("rf_res"):
            st.info("Nenhuma empresa encontrada com os filtros aplicados. Tente ampliar os critérios de busca.")
        if st.session_state.get("rf_res"):
            res = st.session_state["rf_res"]
            if st.session_state.pop("_auto_exp_rf", False):
                _planilhas = st.session_state.get("sheets_planilhas", [])
                _padrao = next((p for p in _planilhas if p.get("padrao")), None)
                if _padrao and st.session_state.get("sheets_creds"):
                    from modules.google_sheets import exportar
                    try:
                        with st.spinner(f"Auto-exportando para {_padrao['nome']}…"):
                            _ok, _msg = exportar(res, st.session_state["sheets_creds"],
                                                 _padrao["id"], _padrao["aba"],
                                                 _padrao.get("modo","substituir"))
                        if _ok:
                            st.success(_msg)
                        else:
                            st.error(_msg)
                    except Exception as _ae:
                        logger.exception("Falha no auto-export CNPJ para Sheets")
                        st.error("Exportação automática falhou. Seus resultados foram salvos — use o botão de download para baixar manualmente.")
                elif not st.session_state.get("sheets_creds"):
                    st.warning("Exportação automática não realizada: conta Google não vinculada.")
                else:
                    st.warning("Exportação automática não realizada: nenhuma planilha principal configurada.")
            st.success(f"✅ **{len(res)}** resultados")
            _stats(res)
            if gmaps_ok and not st.session_state.get("_rf_enriched"):
                _n_enr = len(res)
                if _maps_credits_enabled:
                    from modules.database import obter_creditos_maps
                    _ec1, _ec2 = st.columns([5, 2])
                    with _ec1:
                        _btn_enr = st.button(
                            f"🗺️ Enriquecer com Google Maps  —  {_n_enr} créditos Maps",
                            key="btn_enrich_rf", use_container_width=True,
                        )
                    with _ec2:
                        st.caption(f"Saldo Maps: {obter_creditos_maps()}")
                else:
                    _btn_enr = st.button(
                        "🗺️ Enriquecer com Google Maps",
                        key="btn_enrich_rf", use_container_width=True,
                    )
                if _btn_enr:
                    _cred_ok = True
                    if _maps_credits_enabled:
                        from modules.database import obter_creditos_maps
                        _saldo_m = obter_creditos_maps()
                        if _saldo_m < _n_enr:
                            st.error(f"Créditos Maps insuficientes ({_saldo_m} disponíveis, {_n_enr} necessários).")
                            _cred_ok = False
                    if _cred_ok:
                        _bar_enr = st.progress(0, text="Iniciando enriquecimento…")
                        def _cb_enr(a, t, m): _bar_enr.progress(min(a / max(t, 1), 1.0), text=str(m)[:100])
                        from modules.google_maps import enriquecer_com_maps
                        try:
                            enriquecer_com_maps(res, gmaps_key, _cb_enr)
                            st.session_state["rf_res"] = res
                            st.session_state["_rf_enriched"] = True
                            if _maps_credits_enabled:
                                from modules.database import debitar_creditos_maps
                                debitar_creditos_maps(_n_enr)
                            _bar_enr.empty()
                            st.rerun()
                        except Exception as _enr_e:
                            _bar_enr.empty()
                            st.error(f"Erro no enriquecimento: {_enr_e}")
            _dl_buttons(res, st.session_state.get("rf_prefix","prospecao_cdd"), "sheets_creds" in st.session_state and bool(st.session_state.get("sheets_planilhas")))
            st.markdown("#### Prévia"); _tabela(res)


    if aba_insta is not None:
     with aba_insta:
        _insta_credits_en = st.session_state.get("instagram_credits_enabled", False)
        _apify_key_user   = st.session_state.get("apify_api_key_user", "")
        _apify_key_admin  = st.session_state.get("apify_api_key_admin", "")

        # Seleciona chave a usar: usuário > admin > env
        if _apify_key_user:
            _apify_key = _apify_key_user
            _usar_creditos_insta = False
        elif _apify_key_admin:
            _apify_key = _apify_key_admin
            _usar_creditos_insta = _insta_credits_en
        else:
            _apify_key = _s("APIFY_API_KEY")
            _usar_creditos_insta = _insta_credits_en

        if not _apify_key:
            st.warning(
                "Busca via Instagram não configurada.  \n"
                "O administrador precisa configurar a chave Apify para habilitar esta busca.",
                icon="⚠️",
            )
        else:
            # Exibe erro persistente de extração anterior
            if st.session_state.get("_insta_error"):
                st.error(st.session_state.pop("_insta_error"))
            st.markdown(
                '<div class="info-box">Extrai <strong>seguidores</strong> de perfis públicos ou '
                '<strong>comentaristas</strong> de publicações. '
                'Retorna username e ID numérico (para disparo via DM automatizado).</div>',
                unsafe_allow_html=True,
            )

            # Tipo fora do form para atualizar labels dinamicamente
            _insta_tipo = st.radio(
                "Tipo de extração",
                ["👥 Seguidores do perfil", "➡️ Quem o perfil segue (Following)"],
                horizontal=True, key="insta_tipo",
            )
            _tipo_val = "seguidores" if "Seguidores" in _insta_tipo else "seguindo"

            with st.form("form_instagram"):
                _alvo = st.text_input(
                    "Username do perfil",
                    placeholder="Ex: neymarjr (sem @)",
                    key="insta_alvo",
                )

                _lim_min   = 100 if _tipo_val in ("seguidores", "seguindo") else 10
                _lim_insta = st.slider("Máx. resultados", _lim_min, 1000, max(200, _lim_min), 10, key="insta_lim")
                _apenas_novos_insta = st.toggle(
                    "🔄 Apenas leads novos (remover duplicatas de buscas anteriores)",
                    value=True, key="insta_apenas_novos",
                    help="Remove perfis com Instagram ID já salvos em buscas anteriores.",
                )
                btn_insta = st.form_submit_button("📸 Extrair do Instagram", use_container_width=True, type="primary")

            if btn_insta:
                if not _alvo.strip():
                    st.error("Informe o username ou URL do alvo.")
                else:
                    _insta_ok = True
                    if _usar_creditos_insta:
                        from modules.database import obter_creditos_instagram
                        _saldo_insta = obter_creditos_instagram()
                        if _saldo_insta < _lim_insta:
                            st.error(
                                f"Créditos insuficientes. Você tem **{_saldo_insta}** créditos Instagram "
                                f"e a busca requer **{_lim_insta}**. "
                                "Reduza o limite ou solicite mais créditos ao administrador."
                            )
                            _insta_ok = False

                    if _insta_ok:
                        _excl_insta: set = set()
                        if _apenas_novos_insta:
                            from modules.database import buscar_instagram_ids_existentes
                            _excl_insta = buscar_instagram_ids_existentes()

                        bar_insta = st.progress(0, text="Iniciando extração…")

                        def _cb_insta(a, t, msg):
                            v = min(a / max(t, 1), 1.0)
                            bar_insta.progress(v, text=str(msg)[:120])

                        try:
                            from modules.instagram import buscar as insta_buscar
                            res_insta = insta_buscar(
                                apify_api_key=_apify_key,
                                tipo=_tipo_val,
                                alvo=_alvo.strip(),
                                limite=_lim_insta,
                                progress_callback=_cb_insta,
                                exclude_ids=_excl_insta if _apenas_novos_insta else None,
                            )
                            bar_insta.progress(1.0, text=f"Concluído! {len(res_insta)} resultados.")
                            bar_insta.empty()
                            if not res_insta:
                                st.session_state["_insta_error"] = "Nenhum resultado encontrado. Verifique o username/URL e tente novamente."
                                st.rerun()
                            st.session_state["insta_res"] = res_insta
                            _alvo_slug = _alvo.strip().replace("/", "_").replace("@", "")[:20]
                            st.session_state["insta_prefix"] = f"instagram_{_tipo_val}_{_alvo_slug}"
                        except Exception as e:
                            logger.exception("Erro na extração Instagram")
                            bar_insta.empty()
                            st.session_state["_insta_error"] = "Não foi possível concluir a extração. Tente novamente."
                            st.session_state["insta_res"] = []
                            st.toast("Extração finalizada com erro.", icon="🚨")
                            st.rerun()
                        else:
                            try:
                                from modules.database import (
                                    salvar_pesquisa, salvar_leads, debitar_creditos_instagram,
                                )
                                sid = salvar_pesquisa(
                                    "Instagram", _tipo_val, "", "", _alvo.strip(),
                                    "instagram", len(res_insta),
                                )
                                if sid:
                                    salvar_leads(sid, res_insta)
                                if _usar_creditos_insta:
                                    debitar_creditos_instagram(len(res_insta))
                            except Exception:
                                pass
                            if st.session_state.get("auto_export_enabled"):
                                st.session_state["_auto_exp_insta"] = True

        if st.session_state.get("insta_res"):
            res = st.session_state["insta_res"]
            if st.session_state.pop("_auto_exp_insta", False):
                _planilhas = st.session_state.get("sheets_planilhas", [])
                _padrao = next((p for p in _planilhas if p.get("padrao")), None)
                if _padrao and st.session_state.get("sheets_creds"):
                    from modules.google_sheets import exportar
                    with st.spinner(f"Auto-exportando para {_padrao['nome']}…"):
                        _ok, _msg = exportar(
                            res, st.session_state["sheets_creds"],
                            _padrao["id"], _padrao["aba"], _padrao.get("modo", "substituir"),
                        )
                    if _ok:
                        st.success(_msg)
                    else:
                        st.error(_msg)
                elif not st.session_state.get("sheets_creds"):
                    st.warning("Exportação automática não realizada: conta Google não vinculada.")
                else:
                    st.warning("Exportação automática não realizada: nenhuma planilha principal configurada.")
            st.success(f"✅ **{len(res)}** resultados")
            _stats(res)
            _dl_buttons(
                res,
                st.session_state.get("insta_prefix", "instagram"),
                "sheets_creds" in st.session_state and bool(st.session_state.get("sheets_planilhas")),
            )
            st.markdown("#### Prévia")
            import pandas as pd_ig
            _insta_vis = [
                "nome", "instagram_id", "nome_completo", "email", "site",
                "bio", "followers_count", "is_business", "comentario", "fonte",
            ]
            _lm_insta = {
                "nome":            "Username / @handle",
                "instagram_id":    "Instagram ID",
                "nome_completo":   "Nome Completo",
                "email":           "E-mail",
                "site":            "Site",
                "bio":             "Bio",
                "followers_count": "Seguidores",
                "is_business":     "Conta Business",
                "comentario":      "Comentário",
                "fonte":           "Fonte",
            }
            _df_insta = pd_ig.DataFrame(res)
            _insta_cols = [c for c in _insta_vis if c in _df_insta.columns]
            st.dataframe(
                _df_insta[_insta_cols].rename(columns=_lm_insta).fillna("").astype(str).replace("nan", ""),
                use_container_width=True, height=380,
            )


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


# ── Automações ─────────────────────────────────────────────────────────────────

_DIAS_PT  = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb"}
_DIAS_OPT = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]  # índice == valor

def _card_automacao(auto: dict) -> None:
    from modules.automation_db import atualizar_automacao, deletar_automacao, obter_ultimas_execucoes
    from modules.scheduler import calcular_proxima_execucao, formatar_proxima_execucao, formatar_dias, formatar_horarios

    aid  = auto["id"]
    nome = auto.get("nome", "Sem nome")
    tipo = auto.get("tipo", "maps")
    ativa = bool(auto.get("ativa", True))
    dias  = auto.get("dias_semana") or [1,2,3,4,5]
    hora  = (auto.get("horario") or "08:00")
    prox  = auto.get("proxima_execucao")
    data_fim = (auto.get("filtros") or {}).get("data_fim", "")

    tipo_badge = ("🗺️ Maps" if tipo == "maps" else "🏢 CNPJ")
    status_cor  = "#00D97E" if ativa else "#4b5a72"
    status_txt  = "Ativa" if ativa else "Pausada"

    with st.container():
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.035);border:1px solid rgba(255,255,255,0.07);'
            f'border-radius:14px;padding:16px 20px;margin-bottom:12px">'
            f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
            f'<span style="font-weight:700;font-size:15px;color:#f1f5f9">{nome}</span>'
            f'<span style="background:rgba(0,217,126,0.12);color:#00D97E;font-size:11px;'
            f'padding:2px 8px;border-radius:99px;font-weight:600">{tipo_badge}</span>'
            f'<span style="background:rgba(255,255,255,0.06);color:{status_cor};font-size:11px;'
            f'padding:2px 8px;border-radius:99px">{status_txt}</span>'
            f'</div>'
            f'<div style="margin-top:8px;font-size:12px;color:#94a3b8;display:flex;gap:20px;flex-wrap:wrap">'
            f'<span>🗓️ {formatar_dias(dias)} às {formatar_horarios(hora)}</span>'
            f'<span>⏭️ {formatar_proxima_execucao(prox)}</span>'
            + (f'<span>🔚 Encerra em {data_fim[8:10]}/{data_fim[5:7]}/{data_fim[:4]}</span>' if data_fim else '')
            + f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        col_tog, col_run, col_ed, col_del, col_exp = st.columns([2, 2, 2, 2, 2])
        with col_tog:
            label_tog = "⏸️ Pausar" if ativa else "▶️ Ativar"
            if st.button(label_tog, key=f"tog_{aid}", use_container_width=True):
                nova_ativa = not ativa
                atualizar_automacao(aid, ativa=nova_ativa)
                if nova_ativa:
                    nova_prox = calcular_proxima_execucao(dias, hora)
                    if nova_prox:
                        atualizar_automacao(aid, proxima_execucao=nova_prox)
                st.rerun()
        with col_run:
            if st.button("▶️ Executar agora", key=f"run_{aid}", use_container_width=True):
                from modules.scheduler import executar_automacao as _exec_auto, _reservar_automacao
                _reservar_automacao(auto)  # evita duplo disparo com o scheduler
                with st.spinner("Executando…"):
                    try:
                        _exec_auto(auto)
                        st.success("Execução concluída.")
                    except Exception as _exc:
                        logger.exception("Erro ao executar automação manualmente")
                        st.error("Não foi possível executar a automação. Tente novamente.")
                st.rerun()
        with col_ed:
            _edit_key = f"_edit_aberto_{aid}"
            label_ed = "✏️ Fechar edição" if st.session_state.get(_edit_key) else "✏️ Editar"
            if st.button(label_ed, key=f"ed_btn_{aid}", use_container_width=True):
                st.session_state[_edit_key] = not st.session_state.get(_edit_key, False)
                st.rerun()
        with col_del:
            if st.button("🗑️ Excluir", key=f"del_{aid}", use_container_width=True):
                st.session_state[f"_conf_del_{aid}"] = True
                st.rerun()
        with col_exp:
            if st.button("📋 Execuções", key=f"exp_{aid}", use_container_width=True):
                chave = f"_runs_aberto_{aid}"
                st.session_state[chave] = not st.session_state.get(chave, False)
                st.rerun()

        # Confirmação de exclusão
        if st.session_state.get(f"_conf_del_{aid}"):
            st.warning(f"Tem certeza que deseja excluir **{nome}**? Esta ação não pode ser desfeita.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Sim, excluir", key=f"conf_del_ok_{aid}", type="primary"):
                    deletar_automacao(aid)
                    st.session_state.pop(f"_conf_del_{aid}", None)
                    st.rerun()
            with c2:
                if st.button("Cancelar", key=f"conf_del_no_{aid}"):
                    st.session_state.pop(f"_conf_del_{aid}", None)
                    st.rerun()

        # Histórico de execuções
        if st.session_state.get(f"_runs_aberto_{aid}"):
            runs = obter_ultimas_execucoes(aid, limit=5)
            if not runs:
                st.info("Nenhuma execução registrada ainda.")
            else:
                STATUS_ICON = {
                    "success":      "✅ Sucesso",
                    "error":        "❌ Erro",
                    "sem_creditos": "💳 Sem créditos",
                    "sem_sheets":   "📊 Sem Sheets",
                    "running":      "⏳ Rodando",
                }
                for r in runs:
                    s = r.get("status", "—")
                    lbl = STATUS_ICON.get(s, s)
                    leads = r.get("leads_encontrados", 0)
                    ts = (r.get("concluida_em") or r.get("iniciada_em") or "")[:16].replace("T", " ")
                    erro = r.get("erro") or ""
                    st.markdown(
                        f'<div style="font-size:12px;padding:6px 12px;margin-bottom:4px;'
                        f'background:rgba(255,255,255,0.03);border-radius:8px;color:#94a3b8">'
                        f'{ts} &nbsp;·&nbsp; {lbl} &nbsp;·&nbsp; {leads} leads'
                        + (f' &nbsp;·&nbsp; <span style="color:#ef4444">{erro[:80]}</span>' if erro else "")
                        + "</div>",
                        unsafe_allow_html=True,
                    )

        # ── Painel de edição ──────────────────────────────────────────────────
        if st.session_state.get(f"_edit_aberto_{aid}"):
            from modules.nichos import NICHOS, ESTADOS, NOMES_NICHOS, SIGLAS_ESTADOS
            from modules.cnaes import OPCOES_MULTISELECT as _CNAES_OPTS
            from datetime import datetime as _dt_parse, date as _date_cls
            filtros_e = auto.get("filtros") or {}
            _SLOTS_E = [f"{_h:02d}:{_m:02d}" for _h in range(24) for _m in (0, 30)]
            planilhas_cfg_e = st.session_state.get("sheets_planilhas", [])
            sheets_ok_e = bool(st.session_state.get("sheets_creds") and planilhas_cfg_e)

            st.markdown("---")
            st.markdown("**✏️ Editar automação**")

            # País selector (Maps) — fora do form para ser reativo
            _pais_opts_e = [
                "Brasil", "Estados Unidos", "Portugal", "Argentina", "México",
                "Colômbia", "Chile", "Peru", "Espanha", "Reino Unido",
                "França", "Alemanha", "Itália", "Canadá", "Austrália", "Japão", "Outro…",
            ]
            if tipo == "maps":
                _pais_stored = filtros_e.get("pais", "Brasil")
                _pais_idx_e  = _pais_opts_e.index(_pais_stored) if _pais_stored in _pais_opts_e else 0
                pais_ed     = st.selectbox("País", _pais_opts_e, index=_pais_idx_e, key=f"ed_{aid}_pais")
                is_brasil_ed = pais_ed == "Brasil"
            else:
                pais_ed      = "Brasil"
                is_brasil_ed = True

            with st.form(key=f"form_edit_{aid}"):
                nome_ed = st.text_input("Nome da automação *", value=nome, key=f"ed_{aid}_nome")
                st.caption(f"Tipo: **{'Google Maps' if tipo == 'maps' else 'CNPJ / Receita Federal'}** (não pode ser alterado após a criação)")

                if tipo == "maps":
                    st.markdown("**Busca no Maps**")
                    _nicho_stored = filtros_e.get("nicho", "")
                    _nicho_idx_e  = NOMES_NICHOS.index(_nicho_stored) if _nicho_stored in NOMES_NICHOS else 0
                    em1, em2 = st.columns([3, 3])
                    with em1:
                        nicho_key_ed = st.selectbox("Nicho *", NOMES_NICHOS,
                                                     index=_nicho_idx_e, key=f"ed_{aid}_nicho")
                        _is_custom_e = nicho_key_ed == "Outro / Personalizado"
                        _subs_e      = NICHOS.get(nicho_key_ed, {}).get("subnichos", [])
                        _sub_stored  = filtros_e.get("subnicho", "")
                        _sub_idx_e   = (_subs_e.index(_sub_stored) + 1) if _sub_stored in _subs_e else 0
                        sub_ed = st.selectbox("Subnicho", ["—"] + _subs_e, index=_sub_idx_e, key=f"ed_{aid}_sub") if _subs_e else None
                    with em2:
                        query_ed = st.text_input("Busca personalizada" if _is_custom_e else "Busca (opcional)",
                                                  value=filtros_e.get("query_base", ""), key=f"ed_{aid}_query")
                    ec1, ec2, ec3 = st.columns([3, 2, 2])
                    with ec1:
                        _lbl_cidade = "País / Cidade" if pais_ed == "Outro…" else ("Cidade" if is_brasil_ed else "Cidade / Região (opcional)")
                        cidade_ed = st.text_input(_lbl_cidade, value=filtros_e.get("cidade", ""), key=f"ed_{aid}_cidade")
                    with ec2:
                        if is_brasil_ed:
                            _est_stored = filtros_e.get("estado", "")
                            _est_idx_e  = (SIGLAS_ESTADOS.index(_est_stored) + 1) if _est_stored in SIGLAS_ESTADOS else 0
                            estado_ed_raw = st.selectbox("Estado", ["—"] + SIGLAS_ESTADOS, index=_est_idx_e, key=f"ed_{aid}_estado")
                            estado_ed = "" if estado_ed_raw == "—" else estado_ed_raw
                        else:
                            st.text_input("Estado", value="", disabled=True, key=f"ed_{aid}_estado_dis")
                            estado_ed = ""
                    with ec3:
                        lim_ed_m = st.number_input("Máx. resultados", 10, 500, int(filtros_e.get("limite", 50)), 10, key=f"ed_{aid}_lim_m")

                else:  # cnpj
                    st.markdown("**Busca por CNPJ**")
                    _cnaes_stored   = filtros_e.get("cnaes") or []
                    _cnaes_default_e = [op for op in _CNAES_OPTS if op.split(" — ")[0].strip() in _cnaes_stored]
                    cnaes_ed = st.multiselect("CNAE(s) *", _CNAES_OPTS, default=_cnaes_default_e,
                                              placeholder="Digite para buscar…", key=f"ed_{aid}_cnaes")
                    cnae_manual_ed = st.text_input("Ou adicione código manualmente (separado por vírgula)",
                                                    placeholder="6911701, 6912500", key=f"ed_{aid}_cnae_manual")
                    _cnae_tipo_opts_e = ["Primário", "Secundário", "Primário ou Secundário"]
                    _cnae_tipo_map_e  = {"principal": 0, "secundario": 1, "ambos": 2}
                    _cnae_tipo_stored_e = filtros_e.get("cnae_tipo", "principal")
                    cnae_tipo_ed = st.radio(
                        "Considerar CNAE como", _cnae_tipo_opts_e,
                        index=_cnae_tipo_map_e.get(_cnae_tipo_stored_e, 0),
                        horizontal=True, key=f"ed_{aid}_cnae_tipo",
                    )
                    rj_ed = st.checkbox(
                        "🏛️ Apenas empresas em Recuperação Judicial",
                        value=filtros_e.get("recuperacao_judicial", False),
                        key=f"ed_{aid}_rj",
                        help="Filtra pela razão social contendo 'RECUPERACAO JUDICIAL'. CNAE torna-se opcional.",
                    )
                    fca, fcb, fcc = st.columns([2, 2, 2])
                    with fca:
                        _uf_stored = filtros_e.get("uf", "SP")
                        _uf_idx_e  = SIGLAS_ESTADOS.index(_uf_stored) if _uf_stored in SIGLAS_ESTADOS else 0
                        uf_ed = st.selectbox("Estado *", SIGLAS_ESTADOS, index=_uf_idx_e, key=f"ed_{aid}_uf")
                    with fcb:
                        mun_ed = st.text_input("Município (opcional)", value=filtros_e.get("municipio", ""), key=f"ed_{aid}_mun")
                    with fcc:
                        lim_ed_c = st.number_input("Máx. resultados", 1, 2000, int(filtros_e.get("limite", 100)), 50, key=f"ed_{aid}_lim_c")

                    _PORTE_OPTS_E = ["01 — Micro Empresa", "03 — Empresa de Pequeno Porte", "05 — Demais"]
                    with st.expander("📊 Filtros da empresa"):
                        _porte_stored   = filtros_e.get("porte") or []
                        _porte_default_e = [op for op in _PORTE_OPTS_E if op.split(" — ")[0].strip() in _porte_stored]
                        gc1, gc2 = st.columns(2)
                        with gc1:
                            portes_ed = st.multiselect("Porte da empresa", _PORTE_OPTS_E, default=_porte_default_e, key=f"ed_{aid}_porte")
                            _mf_idx   = {"MATRIZ": 1, "FILIAL": 2}.get(filtros_e.get("matriz_filial", ""), 0)
                            matriz_ed = st.radio("Matriz / Filial", ["Todos", "Somente Matriz", "Somente Filial"],
                                                  index=_mf_idx, horizontal=True, key=f"ed_{aid}_matriz")
                        with gc2:
                            _simp_idx  = 1 if filtros_e.get("simples_optante") is True else (2 if filtros_e.get("excluir_simples") else 0)
                            simples_ed = st.radio("Simples Nacional", ["Indiferente", "Apenas optantes", "Excluir optantes"],
                                                   index=_simp_idx, key=f"ed_{aid}_simples")
                            _mei_idx   = 1 if filtros_e.get("mei_optante") is True else (2 if filtros_e.get("excluir_mei") else 0)
                            mei_ed     = st.radio("MEI", ["Indiferente", "Apenas MEI", "Excluir MEI"],
                                                   index=_mei_idx, key=f"ed_{aid}_mei")
                        gd1, gd2 = st.columns(2)
                        _dti_s = filtros_e.get("data_abertura_inicio", "")
                        _dtf_s = filtros_e.get("data_abertura_fim", "")
                        with gd1:
                            dt_ini_ed  = st.date_input("Abertura — de",
                                                        value=(_dt_parse.strptime(_dti_s, "%Y-%m-%d").date() if _dti_s else None),
                                                        key=f"ed_{aid}_dt_ini")
                            cap_min_ed = st.number_input("Capital mínimo (R$)", 0,
                                                          value=int(filtros_e.get("capital_min") or 0),
                                                          step=1000, key=f"ed_{aid}_cap_min")
                        with gd2:
                            dt_fim_ed  = st.date_input("Abertura — até",
                                                        value=(_dt_parse.strptime(_dtf_s, "%Y-%m-%d").date() if _dtf_s else None),
                                                        key=f"ed_{aid}_dt_fim")
                            cap_max_ed = st.number_input("Capital máximo (R$)", 0,
                                                          value=int(filtros_e.get("capital_max") or 0),
                                                          step=1000, key=f"ed_{aid}_cap_max")

                    with st.expander("📞 Filtros de contato"):
                        _tel_idx   = 1 if filtros_e.get("somente_celular") else (2 if filtros_e.get("somente_fixo") else 0)
                        gt1, gt2   = st.columns(2)
                        with gt1:
                            tipo_tel_ed  = st.radio("Tipo de telefone", ["Todos", "Somente celular", "Somente fixo"],
                                                      index=_tel_idx, horizontal=True, key=f"ed_{aid}_tipo_tel")
                            com_email_ed = st.checkbox("Exigir e-mail",
                                                        value=bool(filtros_e.get("com_email", False)),
                                                        key=f"ed_{aid}_com_email")
                        with gt2:
                            excl_contab_ed = st.checkbox("Excluir e-mails contábeis",
                                                          value=bool(filtros_e.get("excluir_email_contab", True)),
                                                          key=f"ed_{aid}_excl_contab")

                # ── Planilha destino ──
                st.markdown("**Exportação → Google Sheets**")
                if not sheets_ok_e:
                    st.warning("Planilha não configurada. Acesse ⚙️ Configurações.", icon="📊")
                    sheet_id_ed  = auto.get("sheet_id", "")
                    sheet_aba_ed = auto.get("sheet_aba", "Leads")
                else:
                    _pln_nomes_e  = [f"{p['nome']} → {p['aba']}" for p in planilhas_cfg_e]
                    _cur_sheet_id = auto.get("sheet_id", "")
                    _cur_idx_e    = next((i for i, p in enumerate(planilhas_cfg_e) if p["id"] == _cur_sheet_id), 0)
                    plan_idx_e    = st.selectbox("Planilha destino", range(len(_pln_nomes_e)),
                                                  format_func=lambda i: _pln_nomes_e[i],
                                                  index=_cur_idx_e, key=f"ed_{aid}_plan")
                    plan_sel_e    = planilhas_cfg_e[plan_idx_e]
                    sheet_id_ed   = plan_sel_e["id"]
                    sheet_aba_ed  = plan_sel_e["aba"]

                # ── Agenda ──
                st.markdown("**Agenda de execução** (fuso: Brasília / BRT)")
                _ag1e, _ag2e = st.columns([3, 4])
                with _ag1e:
                    dias_ed = st.multiselect("Dias da semana", options=list(range(7)), default=dias,
                                              format_func=lambda d: _DIAS_PT[d], key=f"ed_{aid}_dias")
                with _ag2e:
                    _hora_default_e = [h.strip() for h in hora.split(",") if h.strip()]
                    horarios_ed = st.multiselect("Horários", options=_SLOTS_E,
                                                  default=[h for h in _hora_default_e if h in _SLOTS_E],
                                                  key=f"ed_{aid}_horarios")
                _data_fim_stored_e = filtros_e.get("data_fim", "")
                _data_fim_default_e = (_dt_parse.strptime(_data_fim_stored_e, "%Y-%m-%d").date()
                                        if _data_fim_stored_e else None)
                data_fim_ed = st.date_input("Data de encerramento (opcional)",
                                             value=_data_fim_default_e, key=f"ed_{aid}_data_fim")

                col_sv, col_cancel = st.columns([4, 1])
                with col_sv:
                    submitted_ed = st.form_submit_button("💾 Salvar alterações", type="primary", use_container_width=True)
                with col_cancel:
                    cancel_ed = st.form_submit_button("Cancelar", use_container_width=True)

            if cancel_ed:
                st.session_state.pop(f"_edit_aberto_{aid}", None)
                st.rerun()

            if submitted_ed:
                _erros_ed = []
                if not nome_ed.strip():
                    _erros_ed.append("Informe um nome.")
                if not dias_ed:
                    _erros_ed.append("Selecione ao menos um dia.")
                if not horarios_ed:
                    _erros_ed.append("Selecione ao menos um horário.")

                if tipo == "maps":
                    _pais_final_ed = "" if pais_ed in ("Brasil", "Outro…") else pais_ed
                    if is_brasil_ed:
                        _est_nome_ed = ESTADOS.get(estado_ed, estado_ed) if estado_ed else ""
                        _loc_ed = (f"{cidade_ed}, {_est_nome_ed}" if cidade_ed and _est_nome_ed
                                   else cidade_ed or _est_nome_ed)
                    else:
                        _loc_ed = (f"{cidade_ed}, {_pais_final_ed}" if cidade_ed and _pais_final_ed
                                   else cidade_ed or _pais_final_ed)
                    if not _loc_ed:
                        _erros_ed.append("Informe ao menos a cidade ou o estado.")
                    _sub_val_ed = sub_ed if isinstance(sub_ed, str) and sub_ed != "—" else ""
                    novos_filtros_ed = {
                        "query_base": query_ed if _is_custom_e else query_ed,
                        "localidade": _loc_ed,
                        "nicho":      nicho_key_ed if not _is_custom_e else query_ed,
                        "subnicho":   _sub_val_ed,
                        "cidade":     cidade_ed,
                        "estado":     estado_ed,
                        "pais":       pais_ed,
                        "limite":     int(lim_ed_m),
                    }
                else:
                    _cnaes_cod_ed = [op.split(" — ")[0].strip() for op in cnaes_ed]
                    if cnae_manual_ed.strip():
                        _cnaes_cod_ed += [c.strip() for c in cnae_manual_ed.split(",") if c.strip()]
                    _cnaes_cod_ed = list(dict.fromkeys(_cnaes_cod_ed))
                    if not _cnaes_cod_ed and not rj_ed:
                        _erros_ed.append("Selecione ao menos um CNAE.")
                    _mfmap_ed = {"Somente Matriz": "MATRIZ", "Somente Filial": "FILIAL"}
                    _cnae_tipo_val_ed = {"Primário": "principal", "Secundário": "secundario", "Primário ou Secundário": "ambos"}.get(cnae_tipo_ed, "principal")
                    novos_filtros_ed = {
                        "cnaes":              _cnaes_cod_ed,
                        "cnae_tipo":          _cnae_tipo_val_ed,
                        "recuperacao_judicial": rj_ed,
                        "uf":                 uf_ed,
                        "municipio":          mun_ed.strip(),
                        "limite":             int(lim_ed_c),
                        "porte":              [op.split(" — ")[0].strip() for op in portes_ed] or None,
                        "matriz_filial":      _mfmap_ed.get(matriz_ed, ""),
                        "simples_optante":    True if simples_ed == "Apenas optantes" else None,
                        "excluir_simples":    simples_ed == "Excluir optantes",
                        "mei_optante":        True if mei_ed == "Apenas MEI" else None,
                        "excluir_mei":        mei_ed == "Excluir MEI",
                        "com_telefone":       True,
                        "com_email":          com_email_ed,
                        "somente_celular":    tipo_tel_ed == "Somente celular",
                        "somente_fixo":       tipo_tel_ed == "Somente fixo",
                        "excluir_email_contab": excl_contab_ed,
                        "data_abertura_inicio": dt_ini_ed.strftime("%Y-%m-%d") if dt_ini_ed else "",
                        "data_abertura_fim":    dt_fim_ed.strftime("%Y-%m-%d") if dt_fim_ed else "",
                        "capital_min":        int(cap_min_ed) if cap_min_ed else None,
                        "capital_max":        int(cap_max_ed) if cap_max_ed else None,
                    }

                if data_fim_ed:
                    novos_filtros_ed["data_fim"] = data_fim_ed.strftime("%Y-%m-%d")

                if _erros_ed:
                    for _e in _erros_ed:
                        st.error(_e)
                else:
                    _horario_str_ed = ",".join(sorted(horarios_ed))
                    _proxima_ed = calcular_proxima_execucao(dias_ed, _horario_str_ed)
                    _ok_ed = atualizar_automacao(
                        aid,
                        nome=nome_ed.strip(),
                        filtros=novos_filtros_ed,
                        sheet_id=sheet_id_ed or None,
                        sheet_aba=sheet_aba_ed or "Leads",
                        dias_semana=dias_ed,
                        horario=_horario_str_ed,
                        proxima_execucao=_proxima_ed,
                    )
                    if _ok_ed:
                        st.success("✅ Automação atualizada!")
                        st.session_state.pop(f"_edit_aberto_{aid}", None)
                        time.sleep(0.4)
                        st.rerun()
                    else:
                        st.error("Não foi possível salvar as alterações. Tente novamente.")


def pagina_automacoes():
    from modules.automation_db import listar_automacoes_usuario, criar_automacao
    from modules.scheduler import calcular_proxima_execucao, ensure_started
    from modules.nichos import NICHOS, ESTADOS, NOMES_NICHOS, SIGLAS_ESTADOS

    user_id = st.session_state.get("user", {}).get("id")

    # Garante que o scheduler está rodando
    ensure_started()

    st.markdown(
        '<div class="page-header">'
        '<div class="page-header-icon"><svg viewBox="0 0 24 24" stroke="#f59e0b" fill="none" stroke-width="1.8">'
        '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div>'
        '<div><div class="page-title">Automações</div>'
        '<div class="page-sub">Buscas programadas que rodam automaticamente e exportam para o Google Sheets</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    autos = listar_automacoes_usuario(user_id)

    col_info, col_btn = st.columns([3, 1])
    with col_info:
        ativas = sum(1 for a in autos if a.get("ativa"))
        if autos:
            st.markdown(
                f'<div style="font-size:13px;color:#94a3b8;margin-top:4px">'
                f'{len(autos)} automação(ões) · {ativas} ativa(s)</div>',
                unsafe_allow_html=True,
            )
    with col_btn:
        if st.button("+ Nova Automação", type="primary", use_container_width=True, key="btn_nova_auto"):
            st.session_state["_auto_form_aberto"] = not st.session_state.get("_auto_form_aberto", False)
            st.rerun()

    # ── Formulário de criação ─────────────────────────────────────────────────
    if st.session_state.get("_auto_form_aberto"):
        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        with st.container():
            st.markdown(
                '<div style="background:rgba(0,217,126,0.05);border:1px solid rgba(0,217,126,0.2);'
                'border-radius:16px;padding:20px 24px">',
                unsafe_allow_html=True,
            )
            st.markdown("#### Nova Automação")

            # Tipo — FORA do form para ser reativo
            tipo_sel = st.radio(
                "Tipo de busca",
                ["Google Maps", "CNPJ / Receita Federal"],
                horizontal=True,
                key="_new_auto_tipo",
            )
            tipo_val = "maps" if tipo_sel == "Google Maps" else "cnpj"

            # País (Maps) — FORA do form para ser reativo
            _pais_opts_a = [
                "Brasil", "Estados Unidos", "Portugal", "Argentina", "México",
                "Colômbia", "Chile", "Peru", "Espanha", "Reino Unido",
                "França", "Alemanha", "Itália", "Canadá", "Austrália",
                "Japão", "Outro…",
            ]
            if tipo_val == "maps":
                _pa0, _pa1 = st.columns([2, 5])
                with _pa0:
                    pais_auto = st.selectbox("País", _pais_opts_a, index=0, key="an_pais")
                is_brasil_auto = pais_auto == "Brasil"
            else:
                pais_auto = "Brasil"
                is_brasil_auto = True

            planilhas_cfg = st.session_state.get("sheets_planilhas", [])
            sheets_ok = bool(st.session_state.get("sheets_creds") and planilhas_cfg)

            with st.form("form_nova_automacao", clear_on_submit=True):
                # ── Nome ──────────────────────────────────────────────────────
                nome_auto = st.text_input("Nome da automação *", placeholder="Ex: Advogados SP — diário")

                # ── Filtros condicionais por tipo ─────────────────────────────
                if tipo_val == "maps":
                    st.markdown("**Busca Google Maps**")
                    c1, c2 = st.columns(2)
                    with c1:
                        nicho_auto = st.selectbox("Nicho *", NOMES_NICHOS, key="an_nicho")
                    nicho_d = NICHOS[nicho_auto]; is_custom_a = nicho_auto == "Outro / Personalizado"
                    with c2:
                        if is_custom_a:
                            query_auto = st.text_input("Termo personalizado *", key="an_qcustom")
                            sub_auto   = ""
                        else:
                            sub_opts_a = ["Todos (sem filtro)"] + nicho_d["subnichos"]
                            sub_auto   = st.selectbox("Subnicho", sub_opts_a, key="an_sub")
                            query_auto = nicho_d["query"]
                            if sub_auto == "Todos (sem filtro)":
                                sub_auto = ""

                    ca, cb, cc = st.columns([3, 2, 2])
                    with ca:
                        if pais_auto == "Outro…":
                            cidade_auto = st.text_input("País / Cidade", placeholder="Ex: Dubai, Singapura…", key="an_cidade")
                        elif is_brasil_auto:
                            cidade_auto = st.text_input("Cidade", placeholder="Ex: São Paulo", key="an_cidade")
                        else:
                            cidade_auto = st.text_input("Cidade / Região (opcional)", placeholder="Ex: Miami…", key="an_cidade")
                    with cb:
                        if is_brasil_auto:
                            estado_auto_raw = st.selectbox("Estado", ["—"] + SIGLAS_ESTADOS, key="an_estado")
                            estado_auto = "" if estado_auto_raw == "—" else estado_auto_raw
                        else:
                            st.text_input("Estado", value="", disabled=True, key="an_estado_dis")
                            estado_auto = ""
                    with cc:
                        lim_auto_m = st.number_input("Máx. resultados", 10, 500, 50, 10, key="an_lim_m")

                    # Montar localidade
                    pais_final_auto = "" if pais_auto in ("Brasil", "Outro…") else pais_auto
                    if is_brasil_auto:
                        _est_nome = ESTADOS.get(estado_auto, estado_auto) if estado_auto else ""
                        localidade_auto = (
                            f"{cidade_auto}, {_est_nome}" if cidade_auto and _est_nome
                            else cidade_auto or _est_nome
                        )
                    else:
                        localidade_auto = (
                            f"{cidade_auto}, {pais_final_auto}" if cidade_auto and pais_final_auto
                            else cidade_auto or pais_final_auto
                        )
                    filtros_auto: dict = {
                        "query_base":  query_auto,
                        "localidade":  localidade_auto,
                        "nicho":       nicho_auto if not is_custom_a else query_auto,
                        "subnicho":    sub_auto,
                        "cidade":      cidade_auto,
                        "estado":      estado_auto,
                        "pais":        pais_auto,
                        "limite":      int(lim_auto_m),
                        "show_phone":  st.toggle("📞 Buscar telefone e site", value=True, key="an_show_phone",
                                                  help="Chama Place Details (Contact Data). Com False: 5× mais buscas gratuitas/mês."),
                        "show_rating": st.toggle("⭐ Incluir avaliações", value=True, key="an_show_rating",
                                                  help="Vem do Text Search — sem custo adicional."),
                    }

                else:  # cnpj
                    st.markdown("**Busca por CNPJ**")
                    from modules.cnaes import OPCOES_MULTISELECT
                    cnaes_a = st.multiselect(
                        "CNAE(s) *", OPCOES_MULTISELECT,
                        placeholder="Digite para buscar…", key="an_cnaes",
                    )
                    cnae_manual_a = st.text_input(
                        "Ou adicione código manualmente (separado por vírgula)",
                        placeholder="6911701, 6912500", key="an_cnae_manual",
                    )
                    cnae_tipo_a = st.radio(
                        "Considerar CNAE como",
                        ["Primário", "Secundário", "Primário ou Secundário"],
                        horizontal=True, key="an_cnae_tipo",
                    )
                    rj_a = st.checkbox(
                        "🏛️ Apenas empresas em Recuperação Judicial",
                        key="an_rj",
                        help="Filtra pela razão social contendo 'RECUPERACAO JUDICIAL'. CNAE torna-se opcional.",
                    )
                    ca, cb, cc = st.columns([2, 2, 2])
                    with ca:
                        uf_a = st.selectbox("Estado *", SIGLAS_ESTADOS, index=SIGLAS_ESTADOS.index("SP"), key="an_uf")
                    with cb:
                        mun_a = st.text_input("Município (opcional)", key="an_mun")
                    with cc:
                        lim_auto_c = st.number_input("Máx. resultados", 1, 2000, 100, 50, key="an_lim_c")

                    with st.expander("📊 Filtros da empresa"):
                        fc1, fc2 = st.columns(2)
                        with fc1:
                            portes_a = st.multiselect(
                                "Porte da empresa",
                                ["01 — Micro Empresa", "03 — Empresa de Pequeno Porte", "05 — Demais"],
                                key="an_porte",
                            )
                            matriz_a = st.radio(
                                "Matriz / Filial",
                                ["Todos", "Somente Matriz", "Somente Filial"],
                                horizontal=True, key="an_matriz",
                            )
                        with fc2:
                            simples_a = st.radio(
                                "Simples Nacional",
                                ["Indiferente", "Apenas optantes", "Excluir optantes"],
                                key="an_simples",
                            )
                            mei_a = st.radio(
                                "MEI",
                                ["Indiferente", "Apenas MEI", "Excluir MEI"],
                                key="an_mei",
                            )
                        fd1, fd2 = st.columns(2)
                        with fd1:
                            dt_ini_a = st.date_input("Abertura — de", value=None, key="an_dt_ini")
                            cap_min_a = st.number_input("Capital mínimo (R$)", min_value=0, value=0, step=1000, key="an_cap_min")
                        with fd2:
                            dt_fim_a = st.date_input("Abertura — até", value=None, key="an_dt_fim")
                            cap_max_a = st.number_input("Capital máximo (R$)", min_value=0, value=0, step=1000, key="an_cap_max")

                    with st.expander("📞 Filtros de contato"):
                        fct1, fct2 = st.columns(2)
                        with fct1:
                            tipo_tel_a = st.radio(
                                "Tipo de telefone",
                                ["Todos", "Somente celular", "Somente fixo"],
                                horizontal=True, key="an_tipo_tel",
                            )
                            com_email_a = st.checkbox("Exigir e-mail", value=False, key="an_com_email")
                        with fct2:
                            excl_contab_a = st.checkbox("Excluir e-mails contábeis", value=True, key="an_excl_contab")

                    cnaes_codigos_a = [op.split(" — ")[0].strip() for op in cnaes_a]
                    if cnae_manual_a.strip():
                        cnaes_codigos_a += [c.strip() for c in cnae_manual_a.split(",") if c.strip()]
                    cnaes_codigos_a = list(dict.fromkeys(cnaes_codigos_a))

                    mf_map_a = {"Somente Matriz": "MATRIZ", "Somente Filial": "FILIAL"}
                    _cnae_tipo_val_a = {"Primário": "principal", "Secundário": "secundario", "Primário ou Secundário": "ambos"}.get(cnae_tipo_a, "principal")
                    filtros_auto = {
                        "cnaes":              cnaes_codigos_a,
                        "cnae_tipo":          _cnae_tipo_val_a,
                        "recuperacao_judicial": rj_a,
                        "uf":                 uf_a,
                        "municipio":          mun_a.strip(),
                        "limite":             int(lim_auto_c),
                        "porte":              [op.split(" — ")[0].strip() for op in portes_a] or None,
                        "matriz_filial":      mf_map_a.get(matriz_a, ""),
                        "simples_optante":    True if simples_a == "Apenas optantes" else None,
                        "excluir_simples":    simples_a == "Excluir optantes",
                        "mei_optante":        True if mei_a == "Apenas MEI" else None,
                        "excluir_mei":        mei_a == "Excluir MEI",
                        "com_telefone":       True,
                        "com_email":          com_email_a,
                        "somente_celular":    tipo_tel_a == "Somente celular",
                        "somente_fixo":       tipo_tel_a == "Somente fixo",
                        "excluir_email_contab": excl_contab_a,
                        "data_abertura_inicio": dt_ini_a.strftime("%Y-%m-%d") if dt_ini_a else "",
                        "data_abertura_fim":    dt_fim_a.strftime("%Y-%m-%d") if dt_fim_a else "",
                        "capital_min":        int(cap_min_a) if cap_min_a else None,
                        "capital_max":        int(cap_max_a) if cap_max_a else None,
                    }

                # ── Planilha destino ──────────────────────────────────────────
                st.markdown("**Exportação → Google Sheets**")
                if not sheets_ok:
                    st.warning("Conecte sua conta Google e configure uma planilha em ⚙️ Configurações para ativar a exportação automática.", icon="📊")
                    sheet_id_sel  = ""
                    sheet_aba_sel = "Leads"
                else:
                    plan_nomes = [f"{p['nome']} → {p['aba']}" for p in planilhas_cfg]
                    plan_idx   = st.selectbox("Planilha destino", range(len(plan_nomes)),
                                              format_func=lambda i: plan_nomes[i], key="an_plan")
                    plan_sel   = planilhas_cfg[plan_idx]
                    sheet_id_sel  = plan_sel["id"]
                    sheet_aba_sel = plan_sel["aba"]

                # ── Agenda ───────────────────────────────────────────────────
                st.markdown("**Agenda de execução** (fuso: Brasília / BRT)")
                _ag1, _ag2 = st.columns([3, 4])
                with _ag1:
                    dias_sel = st.multiselect(
                        "Dias da semana",
                        options=list(range(7)),
                        default=[1, 2, 3, 4, 5],
                        format_func=lambda d: _DIAS_PT[d],
                        key="an_dias",
                    )
                with _ag2:
                    _SLOTS = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
                    horarios_sel = st.multiselect(
                        "Horários (pode escolher mais de um)",
                        options=_SLOTS,
                        default=["08:00"],
                        key="an_horarios",
                    )
                data_fim_sel = st.date_input(
                    "Data de encerramento (opcional — deixe em branco para rodar indefinidamente)",
                    value=None,
                    key="an_data_fim",
                )

                # ── Submit ───────────────────────────────────────────────────
                submitted = st.form_submit_button("✅ Criar Automação", type="primary", use_container_width=True)

            if submitted:
                erros = []
                if not nome_auto.strip():
                    erros.append("Informe um nome para a automação.")
                if tipo_val == "maps" and not localidade_auto:
                    erros.append("Informe ao menos a cidade ou o estado.")
                if tipo_val == "cnpj" and not filtros_auto.get("cnaes") and not filtros_auto.get("recuperacao_judicial"):
                    erros.append("Selecione ao menos um CNAE.")
                if not dias_sel:
                    erros.append("Selecione ao menos um dia da semana.")
                if not horarios_sel:
                    erros.append("Selecione ao menos um horário de execução.")

                if erros:
                    for e in erros:
                        st.error(e)
                else:
                    horario_str = ",".join(sorted(horarios_sel))
                    if data_fim_sel:
                        filtros_auto["data_fim"] = data_fim_sel.strftime("%Y-%m-%d")
                    proxima = calcular_proxima_execucao(dias_sel, horario_str)
                    novo_id = criar_automacao(
                        user_id=user_id,
                        nome=nome_auto.strip(),
                        tipo=tipo_val,
                        filtros=filtros_auto,
                        sheet_id=sheet_id_sel,
                        sheet_aba=sheet_aba_sel,
                        dias_semana=dias_sel,
                        horario=horario_str,
                        proxima_execucao=proxima,
                    )
                    if novo_id:
                        prox_fmt = proxima.strftime('%d/%m às %H:%M') if proxima else '—'
                        st.success(f"✅ Automação **{nome_auto}** criada! Próxima execução: {prox_fmt}.")
                        st.session_state["_auto_form_aberto"] = False
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Não foi possível salvar a automação. Tente novamente.")

            st.markdown('</div>', unsafe_allow_html=True)

    # ── Lista de automações ───────────────────────────────────────────────────
    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    if not autos:
        st.markdown(
            '<div style="text-align:center;padding:48px 24px;color:#4b5a72;font-size:14px">'
            '⚡ Nenhuma automação criada ainda.<br>'
            '<span style="font-size:12px">Clique em "+ Nova Automação" para agendar sua primeira busca automática.</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        for auto in autos:
            _card_automacao(auto)


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
        if st.session_state.get("maps_credits_enabled"):
            st.info("As chaves do Google Maps são gerenciadas pelo administrador nesta conta.", icon="ℹ️")
        else:
            st.markdown("Configure uma ou mais chaves de API do Google Maps. O sistema usa rodízio automático quando uma chave atinge o limite mensal.")
            from modules.database import obter_pool_maps_usuario, salvar_pool_maps_usuario, selecionar_chave_maps
            _cfg_pool = obter_pool_maps_usuario()
            if _cfg_pool:
                for _pi, _pe in enumerate(_cfg_pool):
                    _pc1, _pc2, _pc3 = st.columns([3, 3, 1])
                    with _pc1:
                        st.caption(_pe.get("nickname") or f"Chave {_pi+1}")
                    with _pc2:
                        _puse = int(_pe.get("usage", 0))
                        _plim = int(_pe.get("limit", 900))
                        _pmon = _pe.get("month", "—")
                        _ppct = min(_puse / max(_plim, 1), 1.0)
                        _pcor = "🔴" if _ppct >= 1.0 else ("🟡" if _ppct >= 0.8 else "🟢")
                        st.caption(f"{_pcor} {_pmon}: **{_puse}/{_plim}**")
                    with _pc3:
                        if st.button("🗑️", key=f"del_cfg_mk_{_pi}", help="Remover"):
                            _np = [k for j, k in enumerate(_cfg_pool) if j != _pi]
                            if salvar_pool_maps_usuario(_np):
                                st.rerun()
            with st.form("add_cfg_mk"):
                _fc1, _fc2, _fc3 = st.columns([2, 4, 2])
                with _fc1:
                    _fn = st.text_input("Apelido", placeholder="Chave 1", key="cfg_mk_nick")
                with _fc2:
                    _fk = st.text_input("Chave API", placeholder="AIzaSy...", type="password", key="cfg_mk_val")
                with _fc3:
                    _fl = st.number_input("Limite/mês", min_value=100, value=900, step=100, key="cfg_mk_lim")
                if st.form_submit_button("➕ Adicionar chave", use_container_width=True):
                    if _fk:
                        _np = list(_cfg_pool) + [{
                            "key": _fk, "nickname": _fn or f"Chave {len(_cfg_pool)+1}",
                            "usage": 0, "month": "", "limit": int(_fl),
                        }]
                        if salvar_pool_maps_usuario(_np):
                            st.success("Chave adicionada!")
                            st.rerun()
            # Chave única (compatibilidade)
            with st.expander("Ou use chave única (modo legado)"):
                gmk = st.text_input("Chave única", value=cfg.get("google_maps_api_key",""),
                                    type="password", placeholder="AIzaSy...", key="cfg_gmaps")
                if st.button("💾 Salvar chave única", key="save_gmaps"):
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
                st.error("Não foi possível conectar sua conta Google. Verifique as permissões e tente novamente.", icon="❌")
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

    # ── Apify API Key ─────────────────────────────────────────────────────────────
    with st.expander("🤖 Apify API Key", expanded=False):
        _apify_desc = "Usada como **fallback automático** na busca Google Maps quando a cota é esgotada ($4/1.000 resultados)."
        if st.session_state.get("instagram_credits_enabled"):
            _apify_desc += "  \nTambém usada na busca Instagram para não deduzir créditos da plataforma."
        st.markdown(_apify_desc)
        _apify_cur = st.session_state.get("apify_api_key_user", "")
        apify_inp = st.text_input(
            "Apify API Key",
            value=_apify_cur,
            type="password",
            placeholder="apify_api_...",
            key="cfg_apify_key",
        )
        if st.button("💾 Salvar chave Apify", key="save_apify"):
            from modules.database import salvar_configuracoes
            ok_ap, msg_ap = salvar_configuracoes({"apify_api_key": apify_inp.strip()})
            if ok_ap:
                st.session_state["apify_api_key_user"] = apify_inp.strip()
                st.success("Chave Apify salva com sucesso.")
            else:
                st.error(msg_ap)

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
        alterar_role, redefinir_senha, ajustar_creditos_admin, configurar_creditos_admin,
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
        logger.error("Erro ao carregar usuários: %s", err)
        st.error("Não foi possível carregar a lista de usuários.")
        return
    if not usuarios:
        st.info("Nenhum usuário cadastrado.")
        return

    st.markdown(f"**{len(usuarios)} usuário(s) cadastrado(s)**")

    for u in usuarios:
        uid          = u.get("id","")
        email        = u.get("email","—")
        role         = u.get("role","user")
        cdd_bal      = int(u.get("cdd_credits", 0) or 0)
        maps_bal     = int(u.get("maps_credits", 0) or 0)
        maps_en      = bool(u.get("maps_credits_enabled", False))
        maps_adm_key = u.get("maps_api_key_admin") or ""
        monthly_cdd  = int(u.get("monthly_cdd_credits", 0) or 0)
        monthly_maps = int(u.get("monthly_maps_credits", 0) or 0)
        created      = (u.get("created_at","") or "")[:10]
        searches     = u.get("total_searches", 0) or 0
        leads_tot    = u.get("total_leads", 0) or 0
        last_s       = (u.get("last_search_at","") or "")[:10] or "nunca"
        me           = st.session_state.get("user",{}).get("id","") == uid

        badge = "🟢 admin" if role == "admin" else "⚪ user"
        maps_tag = "  ·  🗺️ Maps ativo" if maps_en else ""
        label = f"{badge}  **{email}**  ·  🪙 CNPJ: {cdd_bal}{maps_tag}" + ("  *(você)*" if me else "")

        with st.expander(label):
            st.caption(f"ID: `{uid}`  ·  Criado em {created}  ·  {searches} pesquisas  ·  {leads_tot} leads  ·  Última busca: {last_s}")

            col_r, col_p, col_d = st.columns(3)
            with col_r:
                novo_role = st.selectbox("Papel", ["user","admin"], index=0 if role=="user" else 1, key=f"role_{uid}")
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

            st.markdown("---")

            # ── Créditos CNPJ ──────────────────────────────────────
            st.markdown(f"**🪙 Créditos CNPJ** — saldo atual: **{cdd_bal}**  ·  Mensal: **{monthly_cdd}**/mês")
            ca1, ca2, ca3, ca4 = st.columns([2,1,1,2])
            with ca1:
                delta_cdd = st.number_input("Qtd CNPJ", min_value=1, value=100, step=50, key=f"cdd_delta_{uid}", label_visibility="collapsed")
            with ca2:
                if st.button("➕", key=f"cdd_add_{uid}", use_container_width=True, help="Adicionar créditos CNPJ"):
                    ok5, msg5 = ajustar_creditos_admin(uid, int(delta_cdd), "cdd")
                    (st.success if ok5 else st.error)(msg5)
                    if ok5: time.sleep(0.3); st.rerun()
            with ca3:
                if st.button("➖", key=f"cdd_sub_{uid}", use_container_width=True, help="Subtrair créditos CNPJ"):
                    ok6, msg6 = ajustar_creditos_admin(uid, -int(delta_cdd), "cdd")
                    (st.success if ok6 else st.error)(msg6)
                    if ok6: time.sleep(0.3); st.rerun()
            with ca4:
                new_monthly_cdd = st.number_input("Mensal CNPJ", min_value=0, value=monthly_cdd, step=50, key=f"cdd_mon_{uid}", label_visibility="collapsed")
                if st.button("💾 Salvar mensal CNPJ", key=f"cdd_mon_save_{uid}", use_container_width=True):
                    ok7, msg7 = configurar_creditos_admin(uid, monthly_cdd_credits=int(new_monthly_cdd))
                    (st.success if ok7 else st.error)(msg7)
                    if ok7: time.sleep(0.3); st.rerun()

            # ── Créditos Maps ───────────────────────────────────────
            st.markdown("**🗺️ Créditos Maps**")
            maps_toggle = st.toggle("Habilitar créditos Maps (oculta chave própria do usuário)", value=maps_en, key=f"maps_en_{uid}")
            if maps_toggle != maps_en:
                ok8, msg8 = configurar_creditos_admin(uid, maps_credits_enabled=maps_toggle)
                (st.success if ok8 else st.error)(msg8)
                if ok8: time.sleep(0.3); st.rerun()

            if maps_toggle:
                # ── Pool de chaves Maps ──────────────────────────────────
                from modules.auth import obter_pool_maps_usuario_admin
                _upool = obter_pool_maps_usuario_admin(uid)
                st.markdown("**Chaves de API Maps** (rodízio automático por mês)")
                if _upool:
                    for _ki, _ke in enumerate(_upool):
                        _kc1, _kc2, _kc3 = st.columns([3, 3, 1])
                        with _kc1:
                            st.caption(_ke.get("nickname") or f"Chave {_ki+1}")
                        with _kc2:
                            _kuse = int(_ke.get("usage", 0))
                            _klim = int(_ke.get("limit", 900))
                            _kmon = _ke.get("month", "—")
                            _kpct = min(_kuse / max(_klim, 1), 1.0)
                            _cor  = "🔴" if _kpct >= 1.0 else ("🟡" if _kpct >= 0.8 else "🟢")
                            st.caption(f"{_cor} {_kmon}: **{_kuse}/{_klim}**")
                        with _kc3:
                            if st.button("🗑️", key=f"del_mk_{uid}_{_ki}", help="Remover chave"):
                                _np = [k for j, k in enumerate(_upool) if j != _ki]
                                _ok_p, _msg_p = configurar_creditos_admin(uid, maps_keys_pool=_np)
                                (st.success if _ok_p else st.error)(_msg_p)
                                if _ok_p: time.sleep(0.3); st.rerun()
                else:
                    st.caption("Nenhuma chave configurada.")
                with st.form(f"add_mk_{uid}"):
                    _ac1, _ac2, _ac3 = st.columns([2, 4, 2])
                    with _ac1:
                        _new_nick = st.text_input("Apelido", placeholder="Chave 1", key=f"mk_nick_{uid}")
                    with _ac2:
                        _new_kval = st.text_input("Chave API", placeholder="AIzaSy...", type="password", key=f"mk_val_{uid}")
                    with _ac3:
                        _new_klim = st.number_input("Limite/mês", min_value=100, value=900, step=100, key=f"mk_lim_{uid}")
                    if st.form_submit_button("➕ Adicionar chave", use_container_width=True):
                        if _new_kval:
                            _np = list(_upool) + [{
                                "key": _new_kval,
                                "nickname": _new_nick or f"Chave {len(_upool)+1}",
                                "usage": 0, "month": "", "limit": int(_new_klim),
                            }]
                            _ok_p, _msg_p = configurar_creditos_admin(uid, maps_keys_pool=_np)
                            (st.success if _ok_p else st.error)(_msg_p)
                            if _ok_p: time.sleep(0.3); st.rerun()

                st.markdown(f"Saldo Maps atual: **{maps_bal}**  ·  Mensal: **{monthly_maps}**/mês")
                cm1, cm2, cm3, cm4 = st.columns([2,1,1,2])
                with cm1:
                    delta_maps = st.number_input("Qtd Maps", min_value=1, value=100, step=50, key=f"maps_delta_{uid}", label_visibility="collapsed")
                with cm2:
                    if st.button("➕", key=f"maps_add_{uid}", use_container_width=True, help="Adicionar créditos Maps"):
                        ok10, msg10 = ajustar_creditos_admin(uid, int(delta_maps), "maps")
                        (st.success if ok10 else st.error)(msg10)
                        if ok10: time.sleep(0.3); st.rerun()
                with cm3:
                    if st.button("➖", key=f"maps_sub_{uid}", use_container_width=True, help="Subtrair créditos Maps"):
                        ok11, msg11 = ajustar_creditos_admin(uid, -int(delta_maps), "maps")
                        (st.success if ok11 else st.error)(msg11)
                        if ok11: time.sleep(0.3); st.rerun()
                with cm4:
                    new_monthly_maps = st.number_input("Mensal Maps", min_value=0, value=monthly_maps, step=50, key=f"maps_mon_{uid}", label_visibility="collapsed")
                    if st.button("💾 Salvar mensal Maps", key=f"maps_mon_save_{uid}", use_container_width=True):
                        ok12, msg12 = configurar_creditos_admin(uid, monthly_maps_credits=int(new_monthly_maps))
                        (st.success if ok12 else st.error)(msg12)
                        if ok12: time.sleep(0.3); st.rerun()

            # ── Instagram — visibilidade e créditos ────────────────────
            insta_visible = bool(u.get("instagram_visible", True))
            insta_vis_toggle = st.toggle(
                "Exibir aba Instagram para este usuário",
                value=insta_visible, key=f"insta_vis_{uid}",
            )
            if insta_vis_toggle != insta_visible:
                ok_iv, msg_iv = configurar_creditos_admin(uid, instagram_visible=insta_vis_toggle)
                (st.success if ok_iv else st.error)(msg_iv)
                if ok_iv: time.sleep(0.3); st.rerun()

            insta_en     = bool(u.get("instagram_credits_enabled", False))
            insta_bal    = int(u.get("instagram_credits", 0) or 0)
            monthly_insta = int(u.get("monthly_instagram_credits", 0) or 0)
            apify_adm_key = u.get("apify_api_key_admin") or ""

            st.markdown("**📸 Créditos Instagram**")
            insta_toggle = st.toggle(
                "Habilitar créditos Instagram (usa chave Apify da plataforma)",
                value=insta_en, key=f"insta_en_{uid}",
            )
            if insta_toggle != insta_en:
                ok_it, msg_it = configurar_creditos_admin(uid, instagram_credits_enabled=insta_toggle)
                (st.success if ok_it else st.error)(msg_it)
                if ok_it: time.sleep(0.3); st.rerun()

            if insta_toggle:
                new_apify_key = st.text_input(
                    "Chave Apify (admin)", value=apify_adm_key, type="password",
                    key=f"apify_key_{uid}", placeholder="apify_api_...",
                )
                if st.button("💾 Salvar chave Apify", key=f"apify_key_save_{uid}"):
                    ok_ak, msg_ak = configurar_creditos_admin(uid, apify_api_key_admin=new_apify_key)
                    (st.success if ok_ak else st.error)(msg_ak)
                    if ok_ak: time.sleep(0.3); st.rerun()

                st.markdown(f"Saldo Instagram atual: **{insta_bal}**  ·  Mensal: **{monthly_insta}**/mês")
                ci1, ci2, ci3, ci4 = st.columns([2, 1, 1, 2])
                with ci1:
                    delta_insta = st.number_input("Qtd Instagram", min_value=1, value=100, step=50,
                                                  key=f"insta_delta_{uid}", label_visibility="collapsed")
                with ci2:
                    if st.button("➕", key=f"insta_add_{uid}", use_container_width=True, help="Adicionar créditos Instagram"):
                        ok13, msg13 = ajustar_creditos_admin(uid, int(delta_insta), "instagram")
                        (st.success if ok13 else st.error)(msg13)
                        if ok13: time.sleep(0.3); st.rerun()
                with ci3:
                    if st.button("➖", key=f"insta_sub_{uid}", use_container_width=True, help="Subtrair créditos Instagram"):
                        ok14, msg14 = ajustar_creditos_admin(uid, -int(delta_insta), "instagram")
                        (st.success if ok14 else st.error)(msg14)
                        if ok14: time.sleep(0.3); st.rerun()
                with ci4:
                    new_monthly_insta = st.number_input("Mensal Instagram", min_value=0, value=monthly_insta,
                                                        step=50, key=f"insta_mon_{uid}", label_visibility="collapsed")
                    if st.button("💾 Salvar mensal Instagram", key=f"insta_mon_save_{uid}", use_container_width=True):
                        ok15, msg15 = configurar_creditos_admin(uid, monthly_instagram_credits=int(new_monthly_insta))
                        (st.success if ok15 else st.error)(msg15)
                        if ok15: time.sleep(0.3); st.rerun()


# ── Sidebar & roteamento principal ────────────────────────────────────────────

_NAV_ICONS = {
    "busca":         '<svg viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.8"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    "historico":     '<svg viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.8"><path d="M3 3v5h5"/><path d="M3.05 13A9 9 0 1 0 6 5.3L3 8"/><path d="M12 7v5l4 2"/></svg>',
    "automacoes":    '<svg viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
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

        # ── Créditos ──────────────────────────────────────────
        from modules.database import obter_perfil_creditos
        _pc = obter_perfil_creditos()
        _cdd_bal   = int(_pc.get("cdd_credits", 0))
        _maps_bal  = int(_pc.get("maps_credits", 0))
        _maps_en   = bool(_pc.get("maps_credits_enabled", False))
        _insta_bal = int(_pc.get("instagram_credits", 0))
        _insta_en  = bool(_pc.get("instagram_credits_enabled", False))
        def _cor(v): return "#00D97E" if v > 50 else "#f59e0b" if v > 0 else "#ef4444"
        _lines = f'CNPJ: <span style="color:{_cor(_cdd_bal)};font-weight:700">{_cdd_bal}</span>'
        if _maps_en:
            _lines += f' &nbsp;&nbsp; Maps: <span style="color:{_cor(_maps_bal)};font-weight:700">{_maps_bal}</span>'
        if _insta_en:
            _lines += f' &nbsp;&nbsp; Insta: <span style="color:{_cor(_insta_bal)};font-weight:700">{_insta_bal}</span>'
        st.markdown(
            f'<div style="margin:6px 4px 10px;padding:8px 12px;'
            f'background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);'
            f'border-radius:8px;font-size:12px;color:#94a3b8">'
            f'Créditos — {_lines}</div>',
            unsafe_allow_html=True,
        )

        # ── Nav with SVG icons ────────────────────────────────
        page = st.session_state.get("page", "busca")
        nav_items = [
            ("busca",         "Busca"),
            ("historico",     "Histórico"),
            ("automacoes",    "Automações"),
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
        # Logout pendente: deleta o cookie ANTES de tentar restaurar sessão
        if st.session_state.get("_do_logout_cookie"):
            try:
                cm.delete(_COOKIE_NAME)
            except Exception:
                pass
            st.session_state.pop("_do_logout_cookie", None)
        else:
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

    # (_do_logout_cookie é tratado antes da restauração de sessão — ver acima)

    user = usuario_logado()

    if not user:
        pagina_login()
        return

    # Renovação mensal de créditos — roda uma vez por sessão
    if not st.session_state.get("_credits_renewed"):
        st.session_state["_credits_renewed"] = True
        from modules.database import renovar_creditos_se_necessario
        renovar_creditos_se_necessario()

    # Scheduler de automações — inicia uma vez por processo (singleton global)
    try:
        from modules.scheduler import ensure_started as _sched_start
        _sched_start()
    except Exception:
        pass

    _sidebar()

    page = st.session_state.get("page", "busca")

    if page == "busca":
        pagina_busca()
    elif page == "historico":
        pagina_historico()
    elif page == "automacoes":
        pagina_automacoes()
    elif page == "configuracoes":
        pagina_configuracoes()
    elif page == "admin":
        if eh_admin():
            pagina_admin()
        else:
            st.error("Acesso não autorizado.")
    else:
        pagina_busca()


if __name__ == "__main__" or True:
    main()
