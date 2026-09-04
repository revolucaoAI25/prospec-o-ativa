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
                salvar_configuracoes({"google_sheets_creds": {
                    "oauth":       creds,
                    "planilhas":   st.session_state.get("sheets_planilhas", []),
                    "auto_export": st.session_state.get("auto_export_enabled", False),
                }})
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
/* Hover do item ativo do menu — precisa de regra própria, senão herda o
   fundo verde sólido do botão primário genérico (usado nos CTAs de busca)
   e o texto (verde) fica ilegível sobre fundo também verde. */
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"]:hover {
  background: rgba(0, 217, 126, 0.22) !important;
  color: var(--accent) !important;
  border-color: rgba(0,217,126,0.32) !important;
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

/* Confirmação de ação destrutiva — botão "Sim, excluir/remover/desconectar"
   dentro de um st.container(key="danger_...") recebe cor de alerta em vez
   do verde padrão de botão primário. */
[class*="st-key-danger_"] [data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(160deg, #f87171 0%, #ef4444 50%, #dc2626 100%) !important;
  color: #2a0505 !important;
  border: 1px solid rgba(239,68,68,0.35) !important;
  box-shadow:
    0 1px 0 rgba(255,255,255,0.2) inset,
    0 2px 4px rgba(0,0,0,0.4),
    0 4px 16px rgba(239,68,68,0.25) !important;
}
[class*="st-key-danger_"] [data-testid="stButton"] > button[kind="primary"]:hover {
  background: linear-gradient(160deg, #fca5a5 0%, #f87171 50%, #ef4444 100%) !important;
  box-shadow:
    0 1px 0 rgba(255,255,255,0.25) inset,
    0 4px 8px rgba(0,0,0,0.4),
    0 8px 24px rgba(239,68,68,0.35) !important;
}

/* Card verde de formulários "+ Nova X" — st.container(key="form_card_...")
   envolve de fato os elementos filhos (diferente de abrir/fechar uma <div>
   crua em st.markdown()s separados, que não agrupa nada e sobra uma faixa
   verde vazia — bug corrigido aqui). */
[class*="st-key-form_card_"] {
  background: rgba(0, 217, 126, 0.05) !important;
  border: 1px solid rgba(0, 217, 126, 0.2) !important;
  border-radius: 16px !important;
  padding: 20px 24px !important;
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
   EMPTY STATE — "nada por aqui ainda"
═══════════════════════════════════════════════════════════ */
.empty-state {
  text-align: center; padding: 48px 24px;
  color: var(--text-3); font-size: 0.875rem;
}
.empty-state .empty-hint {
  font-size: 0.75rem; color: var(--text-3); opacity: 0.85;
  display: block; margin-top: 4px;
}

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
   METRICS — st.metric cards (ex: Relatórios de campanhas)
═══════════════════════════════════════════════════════════ */
[data-testid="stMetric"] {
  background: var(--surface) !important;
  backdrop-filter: blur(16px) !important;
  -webkit-backdrop-filter: blur(16px) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  padding: 16px 18px !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.06), 0 2px 12px rgba(0,0,0,0.3) !important;
}
[data-testid="stMetricLabel"] {
  color: var(--text-3) !important;
  font-size: 0.68rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.1em !important;
}
[data-testid="stMetricValue"] {
  color: var(--text-1) !important;
  font-size: 1.6rem !important;
  font-weight: 800 !important;
  letter-spacing: -0.03em !important;
}

/* ═══════════════════════════════════════════════════════════
   FILE UPLOADER — glass drop zone
═══════════════════════════════════════════════════════════ */
[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"] {
  background: var(--surface) !important;
  border: 1.5px dashed var(--border) !important;
  border-radius: var(--radius-md) !important;
  transition: border-color 0.22s var(--ease), background 0.22s var(--ease) !important;
}
[data-testid="stFileUploader"] section:hover,
[data-testid="stFileUploaderDropzone"]:hover {
  border-color: rgba(0,217,126,0.35) !important;
  background: var(--surface-2) !important;
}
[data-testid="stFileUploader"] small { color: var(--text-3) !important; }

/* ═══════════════════════════════════════════════════════════
   IMAGENS — ex: QR code de pareamento, emolduradas como card
═══════════════════════════════════════════════════════════ */
[data-testid="stImage"] img {
  border-radius: var(--radius-md) !important;
  border: 1px solid var(--border) !important;
  box-shadow: 0 4px 24px rgba(0,0,0,0.4) !important;
}

/* ═══════════════════════════════════════════════════════════
   TÍTULOS DE SEÇÃO em markdown (ex: "### Campanhas")
═══════════════════════════════════════════════════════════ */
.block-container h3 {
  font-size: 1.05rem !important; font-weight: 800 !important;
  color: var(--text-1) !important; letter-spacing: -0.02em !important;
  margin: 1.75rem 0 0.9rem !important;
}
.block-container h4 {
  font-size: 0.92rem !important; font-weight: 700 !important;
  color: var(--text-2) !important; letter-spacing: -0.01em !important;
  margin: 1.25rem 0 0.6rem !important;
}

/* ═══════════════════════════════════════════════════════════
   LINKS
═══════════════════════════════════════════════════════════ */
.block-container a { color: var(--accent) !important; text-decoration: none !important; }
.block-container a:hover { text-decoration: underline !important; }

/* ═══════════════════════════════════════════════════════════
   SPINNER
═══════════════════════════════════════════════════════════ */
[data-testid="stSpinner"] > div { border-top-color: var(--accent) !important; }

/* ═══════════════════════════════════════════════════════════
   ACESSIBILIDADE — anel de foco visível pra navegação por teclado
═══════════════════════════════════════════════════════════ */
[data-testid="stButton"] > button:focus-visible,
[data-testid="stDownloadButton"] > button:focus-visible {
  outline: 2px solid rgba(0,217,126,0.6) !important;
  outline-offset: 2px !important;
}

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
@media (max-width: 480px) {
  .stats-row { grid-template-columns: 1fr !important; }
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

    # Executa exportação pendente FORA do popover (evita contexto fechado).
    # Usa o ÍNDICE na lista (não o "id" da planilha) porque duas configurações
    # podem apontar pra mesma planilha do Google em abas diferentes — nesse
    # caso o "id" se repete e não identifica sozinho qual entrada foi clicada.
    _req_idx = st.session_state.pop(f"_exp_req_{prefix}", None)
    if _req_idx is not None:
        _pl = st.session_state.get("sheets_planilhas", [])
        if 0 <= _req_idx < len(_pl):
            _export_to_planilha(rows, _pl[_req_idx])

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
                    for _pi, p in enumerate(planilhas_cfg):
                        badge = " ⭐" if p.get("padrao") else ""
                        lbl = f"{p['nome']}{badge} → {p['aba']} ({p.get('modo','substituir')})"
                        if st.button(lbl, key=f"exp_{_pi}_{prefix}", use_container_width=True):
                            # Guarda o índice — exportação roda fora do popover no próximo render
                            st.session_state[f"_exp_req_{prefix}"] = _pi
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
    _conta_teste          = bool(st.session_state.get("conta_teste", False))
    _maps_credits_enabled = st.session_state.get("maps_credits_enabled", False)
    if _conta_teste:
        # Conta de teste: chave fixa da plataforma, nunca a do cliente/admin —
        # compartilhada entre todas as contas de teste. Prioriza o pool
        # configurado em Admin (com rodízio/limite rastreado); a variável de
        # ambiente MAPS_API_KEY_TESTE é só o fallback pra quem não quis
        # configurar o pool.
        from modules.auth import obter_pool_maps_teste
        _pool_teste_check = obter_pool_maps_teste()
        gmaps_key = (_pool_teste_check[0].get("key", "") if _pool_teste_check else "") or _s("MAPS_API_KEY_TESTE")
    elif _maps_credits_enabled:
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
    _apify_plat_ok  = bool(st.session_state.get("apify_keys_pool"))
    maps_ok         = gmaps_ok or bool(_apify_maps_key) or _apify_plat_ok

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
                    cidade = st.text_input("Cidade", placeholder="Ex: São Paulo, Campinas, Santos…", label_visibility="collapsed",
                                            help="Pode informar mais de uma cidade separando por vírgula. Nesse caso, escolha só um estado.")
                else:
                    cidade = st.text_input("Cidade / Região (opcional)", placeholder="Ex: Miami, Los Angeles…", label_visibility="collapsed")
            with ce:
                if is_brasil:
                    estados_sel = st.multiselect(
                        "Estado", SIGLAS_ESTADOS, default=["SP"], label_visibility="collapsed",
                        help="Selecione vários estados só quando o campo Cidade estiver vazio (busca ampla, sem cidade específica).",
                    )
                else:
                    estados_sel = []
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
            cidades_lista = [c.strip() for c in cidade.split(",") if c.strip()]
            pais_final = "" if pais_sel in ("Brasil", "Outro…") else pais_sel
            _maps_err = None
            if is_brasil and not cidades_lista and not estados_sel:
                _maps_err = "Informe ao menos uma cidade ou um estado."
            elif is_brasil and cidades_lista and len(estados_sel) > 1:
                _maps_err = (
                    "Você pode selecionar **vários estados sem informar cidade** (busca ampla), "
                    "ou informar **cidade(s) dentro de um único estado** — mas não as duas coisas juntas. "
                    "Remova a cidade ou deixe selecionado apenas um estado."
                )
            elif not is_brasil and not cidades_lista:
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
                    if cidades_lista:
                        _estado_nome = ESTADOS.get(estados_sel[0], estados_sel[0]) if estados_sel else ""
                        localidade = [f"{c}, {_estado_nome}" if _estado_nome else c for c in cidades_lista]
                    else:
                        localidade = [ESTADOS.get(e, e) for e in estados_sel]
                    cv = ", ".join(cidades_lista)
                    ev = ", ".join(estados_sel)
                else:
                    localidade = [f"{c}, {pais_final}" if pais_final else c for c in cidades_lista] if cidades_lista else ([pais_final] if pais_final else [])
                    cv = ", ".join(cidades_lista)
                    ev = ""
                localidade_str = "; ".join(localidade)
                slug = f"{nicho_lbl[:15]}_{localidade_str[:15]}".lower().replace(" ","_").replace(",","")
                excl_tels_maps = set()
                if apenas_novos_maps:
                    from modules.database import buscar_identificadores_existentes
                    excl_tels_maps, _ = buscar_identificadores_existentes()
                prog = st.progress(0, text="Iniciando...")
                def _cb(a, t, m):
                    v = min(a / t, 1.0) if t and t > 0 else 0
                    prog.progress(v, text=str(m)[:120])
                # ── Seleção de chave via pool (se configurado) ────────────────
                from modules.database import carregar_configuracoes as _carregar_cfg_maps
                _pausar_ao_esgotar = bool(_carregar_cfg_maps().get("maps_pausar_ao_esgotar", False))

                from modules.database import obter_pool_maps_usuario, selecionar_chave_maps
                _pool_ativo   = []
                _pool_key_idx = -1
                _chave_busca  = gmaps_key
                if gmaps_ok:
                    if _conta_teste:
                        from modules.auth import obter_pool_maps_teste
                        _pool_ativo = obter_pool_maps_teste()
                    else:
                        _pool_ativo = obter_pool_maps_usuario()
                    if _pool_ativo:
                        _c, _pool_key_idx, _pool_ativo = selecionar_chave_maps(_pool_ativo)
                        if _c:
                            _chave_busca = _c
                        elif not _chave_busca:
                            _chave_busca = ""

                # ── Seleção de chave Apify: pessoal (grátis) > pool do admin ──────
                from modules.database import obter_pool_apify_usuario, selecionar_chave_apify
                _apify_key_resolvido = _apify_maps_key
                _apify_platform_used = False
                _apify_pool_ativo    = []
                _apify_pool_idx      = -1
                if not _apify_key_resolvido:
                    _apify_pool_ativo = obter_pool_apify_usuario()
                    if _apify_pool_ativo:
                        _ac, _apify_pool_idx, _apify_pool_ativo, _ = selecionar_chave_apify(_apify_pool_ativo)
                        if _ac:
                            _apify_key_resolvido = _ac
                            # Só cobra créditos da plataforma se a conta for
                            # gerenciada por ela — se o pool foi o próprio
                            # usuário quem configurou, o uso é dele, de graça.
                            _apify_platform_used = _maps_credits_enabled

                # ── Decisão pausar/continuar: só entra em jogo quando NEM Maps
                # NEM Apify têm chave dentro do limite normal — trocar de recurso
                # (Maps → Apify, ou entre chaves do mesmo pool) dentro dos limites
                # configurados é rodízio normal e não passa por aqui.
                if not _chave_busca and not _apify_key_resolvido:
                    if not _pausar_ao_esgotar:
                        # "Continuar buscando": prefere Apify (mais barato) além do
                        # limite; se não tiver Apify, continua pelo próprio Maps
                        # além do limite (o único recurso que sobrou).
                        if _apify_pool_ativo:
                            _ac, _apify_pool_idx, _apify_pool_ativo, _ = selecionar_chave_apify(_apify_pool_ativo, permitir_overflow=True)
                            if _ac:
                                _apify_key_resolvido = _ac
                                _apify_platform_used = _maps_credits_enabled
                        if not _apify_key_resolvido and _pool_ativo:
                            _c2, _pool_key_idx, _pool_ativo = selecionar_chave_maps(_pool_ativo, permitir_overflow=True)
                            if _c2:
                                _chave_busca = _c2

                    if not _chave_busca and not _apify_key_resolvido:
                        prog.empty()
                        if _pausar_ao_esgotar:
                            st.error(
                                "Todas as chaves Maps e Apify configuradas atingiram o limite mensal. Você "
                                "optou por pausar a busca nesse caso — mude isso em Configurações se quiser "
                                "continuar além da cota."
                            )
                        else:
                            st.error("Nenhuma chave Google Maps ou Apify configurada — não há como buscar.")
                        st.stop()

                _used_apify = False
                _excl = excl_tels_maps if apenas_novos_maps else None
                _maps_stats: dict = {}
                try:
                    if _chave_busca:
                        from modules.google_maps import buscar as maps_buscar, QuotaExceededError
                        try:
                            res = maps_buscar(query_base=qbase, localidade=localidade, limite=lim,
                                              api_key=_chave_busca, nicho=nicho_lbl, subnicho=sub_final,
                                              cidade=cv, estado=ev, progress_callback=_cb,
                                              exclude_phones=_excl,
                                              show_phone=show_phone_maps, show_rating=show_rating_maps,
                                              stats=_maps_stats)
                        except QuotaExceededError:
                            # Chegar aqui já É o sinal de esgotamento em tempo real —
                            # se ainda não tem Apify resolvido e a preferência é
                            # continuar, tenta de novo permitindo passar do limite.
                            if not _apify_key_resolvido and not _pausar_ao_esgotar and _apify_pool_ativo:
                                _ac, _apify_pool_idx, _apify_pool_ativo, _ = selecionar_chave_apify(_apify_pool_ativo, permitir_overflow=True)
                                if _ac:
                                    _apify_key_resolvido = _ac
                                    _apify_platform_used = _maps_credits_enabled
                            if not _apify_key_resolvido:
                                if _pausar_ao_esgotar:
                                    raise RuntimeError("Cota Google Maps esgotada. Você optou por pausar nesse caso em vez de usar Apify — mude isso em Configurações se quiser.")
                                raise RuntimeError("Cota Google Maps esgotada e nenhuma chave Apify configurada como fallback.")
                            prog.progress(0, text="Cota Google Maps esgotada. Usando Apify como fallback…")
                            _used_apify = True
                            from modules.apify_maps import buscar as apify_buscar
                            res = apify_buscar(query_base=qbase, localidade=localidade, limite=lim,
                                               api_key=_apify_key_resolvido, nicho=nicho_lbl, subnicho=sub_final,
                                               cidade=cv, estado=ev, progress_callback=_cb,
                                               exclude_phones=_excl,
                                               show_phone=show_phone_maps, show_rating=show_rating_maps)
                    else:
                        # Apify-only (sem chave Google Maps)
                        _used_apify = True
                        from modules.apify_maps import buscar as apify_buscar
                        res = apify_buscar(query_base=qbase, localidade=localidade, limite=lim,
                                           api_key=_apify_key_resolvido, nicho=nicho_lbl, subnicho=sub_final,
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
                    # Registra uso no pool Maps (somente se usou Google Maps) —
                    # inclui o contador oculto de chamadas de Text Search, além
                    # do contador visível (leads retornados).
                    if not _used_apify and _pool_ativo and _pool_key_idx >= 0:
                        from modules.database import registrar_uso_maps
                        _novo_pool_maps = registrar_uso_maps(_pool_ativo, _pool_key_idx, len(res), _maps_stats.get("text_search_calls", 0))
                        if _conta_teste:
                            from modules.auth import salvar_pool_maps_teste
                            salvar_pool_maps_teste(_novo_pool_maps)
                        else:
                            from modules.database import salvar_pool_maps_usuario
                            salvar_pool_maps_usuario(_novo_pool_maps)
                    # Registra uso no pool Apify sempre que uma chave do pool foi usada
                    # (independente de ser cobrado ou não — o contador é o que faz o
                    # rodízio funcionar corretamente pro dono das chaves).
                    if _used_apify and _apify_pool_idx >= 0:
                        from modules.database import registrar_uso_apify, salvar_pool_apify_usuario
                        salvar_pool_apify_usuario(
                            registrar_uso_apify(_apify_pool_ativo, _apify_pool_idx, len(res))
                        )
                    try:
                        from modules.database import salvar_pesquisa, salvar_leads, debitar_creditos_maps
                        sid = salvar_pesquisa(nicho_lbl, sub_final, cv, ev, localidade_str, "maps", len(res))
                        if sid: salvar_leads(sid, res)
                        # Só debita créditos da plataforma se a busca de fato usou
                        # um recurso da plataforma — Google Maps API, ou o fallback
                        # Apify com chave do pool/admin. Quando o fallback usa a
                        # chave PESSOAL do usuário, o custo é dele, não da plataforma.
                        if _maps_credits_enabled and (not _used_apify or _apify_platform_used):
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
                    uf_cdd_sel = st.multiselect("Estado *", SIGLAS_ESTADOS, default=["SP"], key="cdd_uf",
                                                 help="Pode selecionar mais de um estado.")
                with c2:
                    mun_cdd = st.text_input("Município (opcional)", placeholder="Ex: São Paulo, Campinas…", key="cdd_mun",
                                             help="Pode informar mais de um município separando por vírgula.")

                lim_cdd = st.slider("Máx. resultados", 1, 2000, 300, 50, key="cdd_lim")

                # ── Filtros da empresa ─────────────────────────────────────────
                with st.expander("📊 Filtros da empresa"):
                    st.caption("Porte, matriz/filial e regime tributário")
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

                    st.caption("Data de abertura e capital social")
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
                    _maps_credito_txt = "  — 1 crédito Maps por empresa verificada" if _maps_credits_enabled else ""
                    maps_modo_cdd = st.radio(
                        f"🗺️ Google Maps{_maps_credito_txt}",
                        [
                            "Não usar",
                            "Enriquecer (avaliação, telefone extra, site)",
                            "Filtrar (manter só quem tem perfil no Maps)",
                            "Filtrar e enriquecer",
                        ],
                        index=0, key="cdd_maps_modo",
                        help=(
                            "Enriquecer complementa cada empresa com dados do Google Maps. "
                            "Filtrar remove da lista quem não tem perfil no Google Maps (ou tem "
                            "menos avaliações que o mínimo abaixo) — útil pra identificar quem "
                            "de fato investe em presença online."
                        ),
                    )
                    _filtrar_maps_cdd  = maps_modo_cdd in ("Filtrar (manter só quem tem perfil no Maps)", "Filtrar e enriquecer")
                    enriquecer_maps_cdd = maps_modo_cdd in ("Enriquecer (avaliação, telefone extra, site)", "Filtrar e enriquecer")
                    # Sempre visível (não só quando "Filtrar" está selecionado) — um
                    # widget dentro de st.form só reaparece/some no próximo envio,
                    # não na hora que o radio acima muda. Deixar sempre visível com
                    # essa nota evita esse atraso e resolve mais simples.
                    min_avaliacoes_cdd = st.number_input(
                        "Mínimo de avaliações no Google Maps (só usado se 'Filtrar' estiver selecionado acima)",
                        min_value=0, value=0, step=1, key="cdd_min_avaliacoes",
                        help="0 = só exige ter perfil no Google Maps, sem mínimo de avaliações.",
                    )
                else:
                    _filtrar_maps_cdd   = False
                    enriquecer_maps_cdd = False
                    min_avaliacoes_cdd  = 0

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
                    # Objeto único com tipo_busca "exata" = busca por substring.
                    # Múltiplos objetos no array são AND — manter apenas um.
                    _busca_textual_cdd = [
                        {"texto": ["recuperacao judicial"], "tipo_busca": "exata", "razao_social": True, "nome_fantasia": True},
                    ]
                    # Inclui SUSPENSA e INAPTA: empresas em RJ frequentemente perdem
                    # o status ATIVA por atraso em obrigações fiscais
                    _situacoes_cdd = ["ATIVA", "SUSPENSA", "INAPTA"]

                mun_lista = [m.strip() for m in mun_cdd.split(",") if m.strip()]

                if not cnaes_codigos and not rj_cdd:
                    st.error("Selecione ao menos um CNAE para buscar.")
                elif not uf_cdd_sel:
                    st.error("Selecione ao menos um estado.")
                elif dt_ini and dt_fim and dt_ini > dt_fim:
                    st.error(
                        f"A data **'Abertura — de'** ({dt_ini.strftime('%d/%m/%Y')}) está depois da "
                        f"**'Abertura — até'** ({dt_fim.strftime('%d/%m/%Y')}) — inverta as datas. "
                        "Com elas assim nenhuma empresa pode atender ao filtro."
                    )
                else:
                    from modules.database import obter_creditos
                    _saldo_cdd = obter_creditos()
                    if _saldo_cdd <= 0:
                        st.error("Você não tem créditos CNPJ disponíveis. Solicite mais ao administrador.")
                    else:
                        if _saldo_cdd < lim_cdd:
                            st.info(
                                f"Você tem **{_saldo_cdd}** créditos — a busca vai considerar esse teto em "
                                f"vez dos {lim_cdd} solicitados. Você só é cobrado pelos resultados que "
                                f"realmente vierem (podendo ser menos que isso), nunca pelo valor pedido."
                            )
                            lim_cdd = _saldo_cdd
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

                        local_cdd = ", ".join(mun_lista) if mun_lista else ", ".join(uf_cdd_sel)
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
                                uf=uf_cdd_sel,
                                municipio=mun_lista,
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
                                dedup_raiz=bool(rj_cdd),
                            )
                            bar_cdd.progress(1.0, text=f"Concluído! {len(res_cdd)} resultados.")
                            bar_cdd.empty()
                            logger.info(
                                "Busca CNPJ (user=%s): %d resultado(s) da API. cnaes=%s cnae_tipo=%s "
                                "uf=%s municipio=%s mei=%s simples=%s data=%s..%s capital=%s..%s",
                                st.session_state.get("user", {}).get("id", ""), len(res_cdd),
                                cnaes_codigos, _cnae_tipo_map.get(cnae_tipo_cdd, "principal"),
                                uf_cdd_sel, mun_lista, mei_optante, simples_optante,
                                dt_ini_str, dt_fim_str, cap_min_v, cap_max_v,
                            )

                            # Sets de deduplicação — reaproveita o que já foi buscado do
                            # histórico (se "apenas leads novos" estiver ativo) e vai sendo
                            # atualizado à medida que os leads do próprio lote são processados.
                            _dedup_cnpjs = set(excl_cnpjs_cdd) if apenas_novos_cdd else set()
                            _dedup_tels  = set(excl_tels_cdd) if apenas_novos_cdd else set()
                            from modules.casa_dos_dados import remover_duplicados_lote
                            # Remove duplicados ANTES de enriquecer — evita gastar créditos
                            # Maps enriquecendo um lead que já é duplicado (do histórico ou
                            # de outro lead dentro do mesmo lote).
                            _n_antes_dedup = len(res_cdd)
                            res_cdd = remover_duplicados_lote(res_cdd, _dedup_cnpjs, _dedup_tels)
                            if _n_antes_dedup != len(res_cdd):
                                logger.info("Busca CNPJ: dedup removeu %d de %d (sobraram %d)", _n_antes_dedup - len(res_cdd), _n_antes_dedup, len(res_cdd))

                            if (enriquecer_maps_cdd or _filtrar_maps_cdd) and res_cdd:
                                # Mesma lógica de seleção/rotação/pausa da busca direta do
                                # Google Maps: usa o pool do usuário com limite (visível +
                                # teto oculto de Text Search) e só passa do limite quando a
                                # preferência "Ao esgotar o limite das chaves de API" estiver
                                # configurada pra continuar buscando. Sem isso, o enriquecimento
                                # rodava sem registrar uso nenhum na maioria dos casos — uma
                                # brecha real de cota que passava despercebida.
                                from modules.database import (
                                    carregar_configuracoes as _carregar_cfg_enr,
                                    obter_pool_maps_usuario, selecionar_chave_maps,
                                )
                                _pausar_ao_esgotar_enr = bool(_carregar_cfg_enr().get("maps_pausar_ao_esgotar", False))
                                if _conta_teste:
                                    from modules.auth import obter_pool_maps_teste
                                    _enr_pool = obter_pool_maps_teste()
                                else:
                                    _enr_pool = obter_pool_maps_usuario()
                                _enr_pool_idx  = -1
                                _enr_key       = gmaps_key
                                _enr_bloqueado = False
                                if _enr_pool:
                                    _c, _enr_pool_idx, _enr_pool = selecionar_chave_maps(_enr_pool)
                                    if _c:
                                        _enr_key = _c
                                    elif _pausar_ao_esgotar_enr:
                                        _enr_bloqueado = True
                                    else:
                                        _c2, _enr_pool_idx, _enr_pool = selecionar_chave_maps(_enr_pool, permitir_overflow=True)
                                        if _c2:
                                            _enr_key = _c2

                                if _enr_bloqueado:
                                    st.error(
                                        "Todas as chaves Google Maps atingiram o limite mensal. Você "
                                        "optou por pausar a busca nesse caso — mude isso em Configurações "
                                        "se quiser continuar além da cota. Os leads de CNPJ já buscados "
                                        "foram mantidos, só a etapa do Maps não rodou."
                                    )
                                    st.session_state.pop("_rf_enriched", None)
                                elif not _enr_key:
                                    st.error("Nenhuma chave Google Maps configurada.")
                                    st.session_state.pop("_rf_enriched", None)
                                else:
                                    _label_maps_step = "Filtrando" if (_filtrar_maps_cdd and not enriquecer_maps_cdd) else "Enriquecendo"
                                    _bar_enr2 = st.progress(0, text=f"{_label_maps_step} com Google Maps…")
                                    def _cb_enr2(a, t, m): _bar_enr2.progress(min(a / max(t, 1), 1.0), text=str(m)[:100])
                                    from modules.google_maps import enriquecer_com_maps, QuotaExceededError
                                    _enr_stats: dict = {}
                                    # Créditos e uso são cobrados por empresa VERIFICADA, não por
                                    # quem sobra depois do filtro — a chamada ao Maps já foi feita
                                    # mesmo pra quem acaba sendo removida da lista.
                                    _n_verificados = len(res_cdd)
                                    try:
                                        res_cdd = enriquecer_com_maps(
                                            res_cdd, _enr_key, _cb_enr2, stats=_enr_stats,
                                            show_phone=enriquecer_maps_cdd,
                                            filtrar=_filtrar_maps_cdd, min_avaliacoes=int(min_avaliacoes_cdd),
                                        )
                                    except QuotaExceededError:
                                        st.warning(
                                            "Cota Google Maps esgotada no meio do processo — parte das "
                                            "empresas pode não ter sido verificada. Os leads de CNPJ já "
                                            "buscados foram mantidos normalmente."
                                        )
                                    finally:
                                        _bar_enr2.empty()
                                    st.session_state["_rf_enriched"] = True
                                    if _enr_pool_idx >= 0:
                                        from modules.database import registrar_uso_maps
                                        _novo_enr_pool = registrar_uso_maps(
                                            _enr_pool, _enr_pool_idx,
                                            _enr_stats.get("contact_data_calls", _n_verificados if enriquecer_maps_cdd else 0),
                                            _enr_stats.get("text_search_calls", 0),
                                        )
                                        if _conta_teste:
                                            from modules.auth import salvar_pool_maps_teste
                                            salvar_pool_maps_teste(_novo_enr_pool)
                                        else:
                                            from modules.database import salvar_pool_maps_por_user_id
                                            salvar_pool_maps_por_user_id(
                                                st.session_state.get("user", {}).get("id", ""), _novo_enr_pool,
                                            )
                                    if _maps_credits_enabled:
                                        from modules.database import debitar_creditos_maps
                                        debitar_creditos_maps(_n_verificados)
                                    if _filtrar_maps_cdd:
                                        st.info(f"Filtro do Google Maps: {len(res_cdd)} de {_n_verificados} empresas tinham perfil (mín. {int(min_avaliacoes_cdd)} avaliações).")
                                        logger.info(
                                            "Busca CNPJ (user=%s): filtro Google Maps manteve %d de %d empresas (mín. %d avaliações)",
                                            st.session_state.get("user", {}).get("id", ""),
                                            len(res_cdd), _n_verificados, int(min_avaliacoes_cdd),
                                        )
                                    # Remove duplicados que só ficaram visíveis DEPOIS do
                                    # enriquecimento (o Maps pode preencher um telefone que bate
                                    # com outro lead já salvo ou já presente neste lote). Usa sets
                                    # NOVOS (só com o histórico) — reaproveitar os sets da passada
                                    # anterior faria cada lead "bater" com o próprio CNPJ/telefone
                                    # que ele mesmo registrou ali, zerando o resultado inteiro.
                                    _dedup_cnpjs = set(excl_cnpjs_cdd) if apenas_novos_cdd else set()
                                    _dedup_tels  = set(excl_tels_cdd) if apenas_novos_cdd else set()
                                    res_cdd = remover_duplicados_lote(res_cdd, _dedup_cnpjs, _dedup_tels)
                            else:
                                st.session_state.pop("_rf_enriched", None)
                            st.session_state["rf_res"] = res_cdd
                            st.session_state["rf_prefix"] = f"cdd_{local_cdd.lower().replace(' ','_')}"
                            st.session_state["_last_rj_mode"] = rj_cdd
                        except Exception as e:
                            logger.exception("Erro na busca CNPJ")
                            bar_cdd.empty()
                            st.error("Ocorreu um erro inesperado na busca. Tente novamente.")
                            st.session_state["rf_res"] = []
                            st.session_state["_last_rj_mode"] = rj_cdd
                        else:
                            try:
                                from modules.database import salvar_pesquisa, salvar_leads, debitar_creditos
                                sid = salvar_pesquisa(nicho_label, ", ".join(cnaes_codigos), ", ".join(mun_lista), ", ".join(uf_cdd_sel), local_cdd, "receita_federal", len(res_cdd))
                                if sid: salvar_leads(sid, res_cdd)
                                debitar_creditos(len(res_cdd))
                            except Exception:
                                pass
                            if st.session_state.get("auto_export_enabled"):
                                st.session_state["_auto_exp_rf"] = True

        if st.session_state.get("rf_res") is not None and not st.session_state.get("rf_res"):
            _msg_vazio = "Nenhuma empresa encontrada com os filtros aplicados."
            if st.session_state.get("_last_rj_mode"):
                _msg_vazio += " No modo Recuperação Judicial, verifique se o filtro **Apenas com telefone** está desmarcado nos filtros da empresa."
            st.info(_msg_vazio)
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
            if st.session_state.get("_rf_filtro_maps_msg"):
                st.info(st.session_state.pop("_rf_filtro_maps_msg"))
            _stats(res)
            if gmaps_ok and not st.session_state.get("_rf_enriched"):
                _n_enr = len(res)
                _maps_credito_txt2 = "  — 1 crédito Maps por empresa verificada" if _maps_credits_enabled else ""
                maps_modo_rf = st.radio(
                    f"🗺️ Google Maps{_maps_credito_txt2}",
                    [
                        "Enriquecer (avaliação, telefone extra, site)",
                        "Filtrar (manter só quem tem perfil no Maps)",
                        "Filtrar e enriquecer",
                    ],
                    index=0, key="rf_maps_modo", horizontal=True,
                )
                _filtrar_rf   = maps_modo_rf in ("Filtrar (manter só quem tem perfil no Maps)", "Filtrar e enriquecer")
                _enriquecer_rf = maps_modo_rf in ("Enriquecer (avaliação, telefone extra, site)", "Filtrar e enriquecer")
                _min_aval_rf = 0
                if _filtrar_rf:
                    _min_aval_rf = st.number_input(
                        "Mínimo de avaliações no Google Maps", min_value=0, value=0, step=1,
                        key="rf_min_avaliacoes",
                        help="0 = só exige ter perfil no Google Maps, sem mínimo de avaliações.",
                    )
                if _maps_credits_enabled:
                    from modules.database import obter_creditos_maps
                    _ec1, _ec2 = st.columns([5, 2])
                    with _ec1:
                        _btn_enr = st.button(
                            f"🗺️ Rodar Google Maps  —  {_n_enr} créditos Maps",
                            key="btn_enrich_rf", use_container_width=True,
                        )
                    with _ec2:
                        st.caption(f"Saldo Maps: {obter_creditos_maps()}")
                else:
                    _btn_enr = st.button(
                        "🗺️ Rodar Google Maps",
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
                        # Mesma lógica de seleção/rotação/pausa da busca direta do Google
                        # Maps (ver bloco de busca CNPJ acima) — esse botão de enriquecimento
                        # manual usava a chave direta sem registrar uso nenhum.
                        from modules.database import (
                            carregar_configuracoes as _carregar_cfg_enr2,
                            obter_pool_maps_usuario, selecionar_chave_maps,
                        )
                        _pausar_ao_esgotar_enr2 = bool(_carregar_cfg_enr2().get("maps_pausar_ao_esgotar", False))
                        if _conta_teste:
                            from modules.auth import obter_pool_maps_teste
                            _enr2_pool = obter_pool_maps_teste()
                        else:
                            _enr2_pool = obter_pool_maps_usuario()
                        _enr2_pool_idx  = -1
                        _enr2_key       = gmaps_key
                        _enr2_bloqueado = False
                        if _enr2_pool:
                            _c, _enr2_pool_idx, _enr2_pool = selecionar_chave_maps(_enr2_pool)
                            if _c:
                                _enr2_key = _c
                            elif _pausar_ao_esgotar_enr2:
                                _enr2_bloqueado = True
                            else:
                                _c2, _enr2_pool_idx, _enr2_pool = selecionar_chave_maps(_enr2_pool, permitir_overflow=True)
                                if _c2:
                                    _enr2_key = _c2

                        if _enr2_bloqueado:
                            _bar_enr.empty()
                            st.error(
                                "Todas as chaves Google Maps atingiram o limite mensal. Você "
                                "optou por pausar a busca nesse caso — mude isso em Configurações "
                                "se quiser continuar além da cota."
                            )
                        elif not _enr2_key:
                            _bar_enr.empty()
                            st.error("Nenhuma chave Google Maps configurada para enriquecimento.")
                        else:
                            from modules.google_maps import enriquecer_com_maps, QuotaExceededError
                            _enr2_stats: dict = {}
                            _enr2_erro = None
                            try:
                                res = enriquecer_com_maps(
                                    res, _enr2_key, _cb_enr, stats=_enr2_stats,
                                    show_phone=_enriquecer_rf,
                                    filtrar=_filtrar_rf, min_avaliacoes=int(_min_aval_rf),
                                )
                            except QuotaExceededError:
                                _enr2_erro = "quota"
                            except Exception as _enr_e:
                                _enr2_erro = str(_enr_e)
                            _bar_enr.empty()

                            if _enr2_pool_idx >= 0:
                                from modules.database import registrar_uso_maps
                                _novo_enr2_pool = registrar_uso_maps(
                                    _enr2_pool, _enr2_pool_idx,
                                    _enr2_stats.get("contact_data_calls", _n_enr if _enriquecer_rf else 0),
                                    _enr2_stats.get("text_search_calls", 0),
                                )
                                if _conta_teste:
                                    from modules.auth import salvar_pool_maps_teste
                                    salvar_pool_maps_teste(_novo_enr2_pool)
                                else:
                                    from modules.database import salvar_pool_maps_por_user_id
                                    salvar_pool_maps_por_user_id(
                                        st.session_state.get("user", {}).get("id", ""), _novo_enr2_pool,
                                    )

                            if _enr2_erro and _enr2_erro != "quota":
                                st.error(f"Erro no enriquecimento: {_enr2_erro}")
                            else:
                                st.session_state["rf_res"] = res
                                st.session_state["_rf_enriched"] = True
                                if _maps_credits_enabled:
                                    from modules.database import debitar_creditos_maps
                                    debitar_creditos_maps(_n_enr)
                                if _enr2_erro == "quota":
                                    st.warning(
                                        "Cota Google Maps esgotada no meio do processo — parte das "
                                        "empresas pode não ter sido verificada. O que já foi processado "
                                        "foi mantido."
                                    )
                                if _filtrar_rf:
                                    st.session_state["_rf_filtro_maps_msg"] = f"Filtro do Google Maps: {len(res)} de {_n_enr} empresas tinham perfil (mín. {int(_min_aval_rf)} avaliações)."
                                    logger.info(
                                        "Enriquecimento manual (user=%s): filtro Google Maps manteve %d de %d empresas (mín. %d avaliações)",
                                        st.session_state.get("user", {}).get("id", ""),
                                        len(res), _n_enr, int(_min_aval_rf),
                                    )
                                st.rerun()
            _dl_buttons(res, st.session_state.get("rf_prefix","prospecao_cdd"), "sheets_creds" in st.session_state and bool(st.session_state.get("sheets_planilhas")))
            st.markdown("#### Prévia"); _tabela(res)


    if aba_insta is not None:
     with aba_insta:
        _insta_credits_en = st.session_state.get("instagram_credits_enabled", False)
        _apify_key_user   = st.session_state.get("apify_api_key_user", "")

        # Seleciona chave a usar: usuário (grátis) > pool do admin (rodízio por
        # mês; se todas estourarem o limite, continua na última) > env (deploy)
        _apify_pool_ativo = []
        _apify_pool_idx   = -1
        if _apify_key_user:
            _apify_key = _apify_key_user
            _usar_creditos_insta = False
        else:
            from modules.database import obter_pool_apify_usuario, selecionar_chave_apify
            _apify_pool_ativo = obter_pool_apify_usuario()
            _apify_key = ""
            if _apify_pool_ativo:
                _apify_key, _apify_pool_idx, _apify_pool_ativo, _apify_esgotado_insta = selecionar_chave_apify(_apify_pool_ativo)
                if not _apify_key and _apify_esgotado_insta:
                    # Mesma preferência geral de pausar/continuar ao esgotar as
                    # chaves — aqui só existe Apify (Instagram não usa Maps).
                    from modules.database import carregar_configuracoes as _carregar_cfg_insta
                    if not bool(_carregar_cfg_insta().get("maps_pausar_ao_esgotar", False)):
                        _apify_key, _apify_pool_idx, _apify_pool_ativo, _ = selecionar_chave_apify(_apify_pool_ativo, permitir_overflow=True)
            if not _apify_key:
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
                                if _apify_pool_idx >= 0:
                                    from modules.database import registrar_uso_apify, salvar_pool_apify_usuario
                                    salvar_pool_apify_usuario(
                                        registrar_uso_apify(_apify_pool_ativo, _apify_pool_idx, len(res_insta))
                                    )
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
        st.markdown(
            '<div class="empty-state">💡 Nenhuma pesquisa salva ainda.'
            '<span class="empty-hint">Vá em "Busca" no menu lateral e faça sua primeira extração de leads.</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Filtros e ordenação ─────────────────────────────────────────────────
    def _estados_de(p: dict) -> list[str]:
        return [e.strip() for e in (p.get("estado", "") or "").split(",") if e.strip()]

    _FONTE_LBL = {"maps": "Google Maps", "receita_federal": "CNPJ", "instagram": "Instagram"}
    fc1, fc2, fc3, fc4 = st.columns([3, 2, 2, 2])
    with fc1:
        hist_busca = st.text_input(
            "Buscar", placeholder="🔍 Nicho, subnicho ou localidade…",
            key="hist_busca", label_visibility="collapsed",
        )
    with fc2:
        _fontes_disp = sorted({p.get("fonte", "") for p in pesquisas if p.get("fonte")})
        hist_fonte = st.multiselect(
            "Fonte", _fontes_disp, format_func=lambda f: _FONTE_LBL.get(f, f),
            key="hist_fonte", placeholder="Todas as fontes", label_visibility="collapsed",
        )
    with fc3:
        _estados_disp = sorted({e for p in pesquisas for e in _estados_de(p)})
        hist_estado = st.multiselect(
            "Estado", _estados_disp, key="hist_estado", placeholder="Todos os estados",
            label_visibility="collapsed",
        )
    with fc4:
        hist_ordenar = st.selectbox(
            "Ordenar por", ["Mais recente", "Mais antigo", "Mais leads", "Menos leads"],
            key="hist_ordenar", label_visibility="collapsed",
        )
    st.markdown('<hr class="hr">', unsafe_allow_html=True)

    pesquisas_filtradas = pesquisas
    if hist_busca.strip():
        _q = hist_busca.strip().lower()
        pesquisas_filtradas = [
            p for p in pesquisas_filtradas
            if _q in (p.get("nicho", "") or "").lower()
            or _q in (p.get("subnicho", "") or "").lower()
            or _q in (p.get("localidade", "") or "").lower()
        ]
    if hist_fonte:
        pesquisas_filtradas = [p for p in pesquisas_filtradas if p.get("fonte") in hist_fonte]
    if hist_estado:
        pesquisas_filtradas = [p for p in pesquisas_filtradas if any(e in hist_estado for e in _estados_de(p))]

    _sort_key = {
        "Mais recente": (lambda p: p.get("created_at", ""), True),
        "Mais antigo":  (lambda p: p.get("created_at", ""), False),
        "Mais leads":   (lambda p: p.get("total_results", 0), True),
        "Menos leads":  (lambda p: p.get("total_results", 0), False),
    }[hist_ordenar]
    pesquisas_filtradas = sorted(pesquisas_filtradas, key=_sort_key[0], reverse=_sort_key[1])

    if len(pesquisas_filtradas) != len(pesquisas):
        st.caption(f"{len(pesquisas_filtradas)} de {len(pesquisas)} pesquisas")

    if not pesquisas_filtradas:
        st.markdown(
            '<div class="empty-state">🔍 Nenhuma pesquisa encontrada com esses filtros.</div>',
            unsafe_allow_html=True,
        )
        return

    for p in pesquisas_filtradas:
        dt = p.get("created_at","")[:16].replace("T"," ") if p.get("created_at") else "—"
        fonte_icon = "🗺️" if p.get("fonte") == "maps" else "📋"
        nicho = p.get("nicho","—"); sub = p.get("subnicho",""); loc = p.get("localidade","—")
        total = p.get("total_results", 0)
        titulo = f"{fonte_icon} **{nicho}**" + (f" · {sub}" if sub else "") + f" — {loc}"

        with st.expander(f"{titulo}  ·  {total} leads  ·  {dt}"):
            col_a, col_b = st.columns([6,1])
            with col_b:
                if st.button("🗑️ Apagar", key=f"del_{p['id']}"):
                    st.session_state[f"_conf_del_pesq_{p['id']}"] = True
                    st.rerun()

            if st.session_state.get(f"_conf_del_pesq_{p['id']}"):
                st.warning("Tem certeza que deseja apagar esta pesquisa e todos os leads salvos nela? Esta ação não pode ser desfeita.")
                cc1, cc2 = st.columns(2)
                with cc1, st.container(key=f"danger_del_pesq_{p['id']}"):
                    if st.button("✅ Sim, apagar", key=f"conf_del_pesq_ok_{p['id']}", type="primary"):
                        ok, msg = deletar_pesquisa(p["id"])
                        st.session_state.pop(f"_conf_del_pesq_{p['id']}", None)
                        (st.success if ok else st.error)(msg)
                        if ok: time.sleep(0.5); st.rerun()
                with cc2:
                    if st.button("Cancelar", key=f"conf_del_pesq_no_{p['id']}"):
                        st.session_state.pop(f"_conf_del_pesq_{p['id']}", None)
                        st.rerun()

            leads = buscar_leads_da_pesquisa(p["id"])
            if not leads:
                st.caption("Nenhum lead salvo para esta pesquisa.")
                continue

            ts = int(time.time())
            slug = f"{nicho[:12]}_{loc[:12]}".lower().replace(" ","_").replace(",","")
            _planilhas_h = st.session_state.get("sheets_planilhas", [])

            # Executa exportação pendente fora do popover. Usa o ÍNDICE na
            # lista (não o "id" da planilha) porque duas configurações podem
            # apontar pra mesma planilha do Google em abas diferentes — nesse
            # caso o "id" se repete e não identifica sozinho qual entrada foi
            # clicada (sempre resolvia pra primeira da lista).
            _hreq = st.session_state.pop(f"_hexp_req_{p['id']}", None)
            if _hreq is not None and leads and 0 <= _hreq < len(_planilhas_h):
                _export_to_planilha(leads, _planilhas_h[_hreq])

            c1, c2, c3 = st.columns(3)
            with c1: st.download_button("⬇️ Excel",_xlsx(leads),f"{slug}_{ts}.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True,key=f"xl_{p['id']}")
            with c2: st.download_button("⬇️ CSV",_csv(leads),f"{slug}_{ts}.csv","text/csv",use_container_width=True,key=f"csv_{p['id']}")
            with c3:
                if "sheets_creds" in st.session_state and _planilhas_h:
                    with st.popover("📊 Google Sheets", use_container_width=True):
                        st.markdown("**Exportar para:**")
                        for _pi, _ph in enumerate(_planilhas_h):
                            _badge = " ⭐" if _ph.get("padrao") else ""
                            _lbl = f"{_ph['nome']}{_badge} → {_ph['aba']} ({_ph.get('modo','substituir')})"
                            if st.button(_lbl, key=f"hexp_{_pi}_{_ph['id']}_{p['id']}", use_container_width=True):
                                st.session_state[f"_hexp_req_{p['id']}"] = _pi
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
    status_cls = "b-ok" if ativa else "b-warn"
    status_txt = "Ativa" if ativa else "Pausada"

    dispatch_camp_id = auto.get("dispatch_campaign_id")
    disparo_badge_html = ""
    disparo_stats_html = ""
    if dispatch_camp_id:
        from modules import dispatch_db as _ddb_card
        _stats_disp = _ddb_card.stats_campanha(dispatch_camp_id)
        disparo_badge_html = '<span class="badge b-ok">📣 Disparo vinculado</span>'
        disparo_stats_html = (
            f'<span>📇 {_stats_disp["total"]} inscritos · ⏳ {_stats_disp["pendente"]} pendentes · '
            f'✅ {_stats_disp["concluido"]} concluídos · ❌ {_stats_disp["falhou"]} falharam '
            f'(gerencie a cadência em Disparos)</span>'
        )

    with st.container():
        st.markdown(
            f'<div style="background:var(--surface);border:1px solid var(--border);'
            f'border-radius:var(--radius-md);padding:16px 20px;margin-bottom:12px">'
            f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
            f'<span style="font-weight:700;font-size:15px;color:var(--text-1)">{nome}</span>'
            f'<span class="badge b-ok">{tipo_badge}</span>'
            f'<span class="badge {status_cls}">{status_txt}</span>'
            + disparo_badge_html +
            f'</div>'
            f'<div style="margin-top:8px;font-size:12px;color:var(--text-2);display:flex;gap:20px;flex-wrap:wrap">'
            f'<span>🗓️ {formatar_dias(dias)} às {formatar_horarios(hora)}</span>'
            f'<span>⏭️ {formatar_proxima_execucao(prox)}</span>'
            + (f'<span>🔚 Encerra em {data_fim[8:10]}/{data_fim[5:7]}/{data_fim[:4]}</span>' if data_fim else '')
            + f'</div>'
            + (f'<div style="margin-top:6px;font-size:12px;color:var(--text-2);display:flex;gap:20px;flex-wrap:wrap">{disparo_stats_html}</div>' if disparo_stats_html else '')
            + f'</div>',
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
            with c1, st.container(key=f"danger_del_auto_{aid}"):
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
                        f'background:var(--surface);border-radius:var(--radius-sm);color:var(--text-2)">'
                        f'{ts} &nbsp;·&nbsp; {lbl} &nbsp;·&nbsp; {leads} leads'
                        + (f' &nbsp;·&nbsp; <span style="color:#f87171">{erro[:80]}</span>' if erro else "")
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

            st.markdown('<hr class="hr">', unsafe_allow_html=True)
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
                    st.markdown('<div class="sec">Busca no Maps</div>', unsafe_allow_html=True)
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
                        cidade_ed = st.text_input(_lbl_cidade, value=filtros_e.get("cidade", ""), key=f"ed_{aid}_cidade",
                                                   help="Pode informar mais de uma cidade separando por vírgula (nesse caso, escolha só um estado)." if is_brasil_ed else None)
                    with ec2:
                        if is_brasil_ed:
                            _est_stored_raw = filtros_e.get("estado", "")
                            _est_stored_list = [e.strip() for e in _est_stored_raw.split(",") if e.strip()] if isinstance(_est_stored_raw, str) else (_est_stored_raw or [])
                            _est_stored_list = [e for e in _est_stored_list if e in SIGLAS_ESTADOS]
                            estados_ed_sel = st.multiselect("Estado", SIGLAS_ESTADOS, default=_est_stored_list, key=f"ed_{aid}_estado")
                        else:
                            st.text_input("Estado", value="", disabled=True, key=f"ed_{aid}_estado_dis")
                            estados_ed_sel = []
                    with ec3:
                        lim_ed_m = st.number_input("Máx. resultados", 10, 500, int(filtros_e.get("limite", 50)), 10, key=f"ed_{aid}_lim_m")

                else:  # cnpj
                    st.markdown('<div class="sec">Busca por CNPJ</div>', unsafe_allow_html=True)
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
                        # filtros_e["uf"] pode ser string (automações antigas, valor
                        # único) ou lista (automações criadas após múltiplos estados)
                        _uf_stored_raw = filtros_e.get("uf", "SP")
                        _uf_stored_list = _uf_stored_raw if isinstance(_uf_stored_raw, list) else ([_uf_stored_raw] if _uf_stored_raw else [])
                        _uf_stored_list = [u for u in _uf_stored_list if u in SIGLAS_ESTADOS] or ["SP"]
                        uf_ed_sel = st.multiselect("Estado *", SIGLAS_ESTADOS, default=_uf_stored_list, key=f"ed_{aid}_uf")
                    with fcb:
                        _mun_stored_raw = filtros_e.get("municipio", "")
                        _mun_stored_str = ", ".join(_mun_stored_raw) if isinstance(_mun_stored_raw, list) else (_mun_stored_raw or "")
                        mun_ed = st.text_input("Município (opcional)", value=_mun_stored_str, key=f"ed_{aid}_mun",
                                                help="Pode informar mais de um separando por vírgula.")
                    with fcc:
                        lim_ed_c = st.number_input("Máx. resultados", 1, 2000, int(filtros_e.get("limite", 100)), 50, key=f"ed_{aid}_lim_c")

                    _PORTE_OPTS_E = ["01 — Micro Empresa", "03 — Empresa de Pequeno Porte", "05 — Demais"]
                    with st.expander("📊 Filtros da empresa"):
                        _porte_stored   = filtros_e.get("porte") or []
                        _porte_default_e = [op for op in _PORTE_OPTS_E if op.split(" — ")[0].strip() in _porte_stored]
                        st.caption("Porte, matriz/filial e regime tributário")
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
                        st.caption("Data de abertura e capital social")
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
                st.markdown('<div class="sec">Exportação → Google Sheets</div>', unsafe_allow_html=True)
                if not sheets_ok_e:
                    st.warning("Planilha não configurada. Acesse ⚙️ Configurações.", icon="📊")
                    sheet_id_ed  = auto.get("sheet_id", "")
                    sheet_aba_ed = auto.get("sheet_aba", "Leads")
                else:
                    _pln_nomes_e  = [f"{p['nome']} → {p['aba']}" for p in planilhas_cfg_e]
                    _cur_sheet_id  = auto.get("sheet_id", "")
                    _cur_sheet_aba = auto.get("sheet_aba", "")
                    # Casa por id + aba — o mesmo id de planilha pode aparecer em
                    # várias entradas (abas diferentes da mesma planilha); só o id
                    # não identifica qual delas estava selecionada.
                    _cur_idx_e = next(
                        (i for i, p in enumerate(planilhas_cfg_e) if p["id"] == _cur_sheet_id and p["aba"] == _cur_sheet_aba),
                        next((i for i, p in enumerate(planilhas_cfg_e) if p["id"] == _cur_sheet_id), 0),
                    )
                    plan_idx_e    = st.selectbox("Planilha destino", range(len(_pln_nomes_e)),
                                                  format_func=lambda i: _pln_nomes_e[i],
                                                  index=_cur_idx_e, key=f"ed_{aid}_plan")
                    plan_sel_e    = planilhas_cfg_e[plan_idx_e]
                    sheet_id_ed   = plan_sel_e["id"]
                    sheet_aba_ed  = plan_sel_e["aba"]

                # ── Agenda ──
                st.markdown('<div class="sec">Agenda de execução (fuso: Brasília / BRT)</div>', unsafe_allow_html=True)
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
                    _cidades_ed_lista = [c.strip() for c in cidade_ed.split(",") if c.strip()]
                    if is_brasil_ed:
                        if _cidades_ed_lista:
                            _est_nome_ed = ESTADOS.get(estados_ed_sel[0], estados_ed_sel[0]) if estados_ed_sel else ""
                            _loc_ed = [f"{c}, {_est_nome_ed}" if _est_nome_ed else c for c in _cidades_ed_lista]
                        else:
                            _loc_ed = [ESTADOS.get(e, e) for e in estados_ed_sel]
                    else:
                        _loc_ed = (
                            [f"{c}, {_pais_final_ed}" if _pais_final_ed else c for c in _cidades_ed_lista]
                            if _cidades_ed_lista else ([_pais_final_ed] if _pais_final_ed else [])
                        )
                    if not _loc_ed:
                        _erros_ed.append("Informe ao menos a cidade ou o estado.")
                    if _cidades_ed_lista and len(estados_ed_sel) > 1:
                        _erros_ed.append(
                            "Você pode selecionar vários estados sem informar cidade (busca ampla), "
                            "ou informar cidade(s) dentro de um único estado — mas não as duas coisas juntas."
                        )
                    _sub_val_ed = sub_ed if isinstance(sub_ed, str) and sub_ed != "—" else ""
                    novos_filtros_ed = {
                        "query_base": query_ed if _is_custom_e else query_ed,
                        "localidade": _loc_ed,
                        "nicho":      nicho_key_ed if not _is_custom_e else query_ed,
                        "subnicho":   _sub_val_ed,
                        "cidade":     ", ".join(_cidades_ed_lista),
                        "estado":     ", ".join(estados_ed_sel),
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
                    if not uf_ed_sel:
                        _erros_ed.append("Selecione ao menos um estado.")
                    if dt_ini_ed and dt_fim_ed and dt_ini_ed > dt_fim_ed:
                        _erros_ed.append(
                            f"A data 'Abertura — de' ({dt_ini_ed.strftime('%d/%m/%Y')}) está depois da "
                            f"'Abertura — até' ({dt_fim_ed.strftime('%d/%m/%Y')}) — inverta as datas."
                        )
                    _mfmap_ed = {"Somente Matriz": "MATRIZ", "Somente Filial": "FILIAL"}
                    _cnae_tipo_val_ed = {"Primário": "principal", "Secundário": "secundario", "Primário ou Secundário": "ambos"}.get(cnae_tipo_ed, "principal")
                    novos_filtros_ed = {
                        "cnaes":              _cnaes_cod_ed,
                        "cnae_tipo":          _cnae_tipo_val_ed,
                        "recuperacao_judicial": rj_ed,
                        "uf":                 uf_ed_sel,
                        "municipio":          [m.strip() for m in mun_ed.split(",") if m.strip()],
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
    from modules.auth import eh_admin

    user_id = st.session_state.get("user", {}).get("id")
    _admin = eh_admin()

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

    if _admin:
        col_info, col_btn, col_btn_disp = st.columns([2, 1.4, 1.4])
    else:
        col_info, col_btn = st.columns([3, 1])
        col_btn_disp = None
    with col_info:
        ativas = sum(1 for a in autos if a.get("ativa"))
        if autos:
            st.markdown(
                f'<div style="font-size:13px;color:#94a3b8;margin-top:4px">'
                f'{len(autos)} automação(ões) · {ativas} ativa(s)</div>',
                unsafe_allow_html=True,
            )
    with col_btn:
        if st.button("+ Nova Automação de Extração", type="primary", use_container_width=True, key="btn_nova_auto"):
            st.session_state["_auto_form_aberto"] = not st.session_state.get("_auto_form_aberto", False)
            st.rerun()
    if col_btn_disp is not None:
        with col_btn_disp:
            if st.button("+ Nova Automação de Disparo", type="primary", use_container_width=True, key="btn_nova_auto_disparo_top"):
                st.session_state["_auto_disp_form_aberto"] = not st.session_state.get("_auto_disp_form_aberto", False)
                st.rerun()

    # ── Formulário de criação ─────────────────────────────────────────────────
    if st.session_state.get("_auto_form_aberto"):
        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        with st.container(key="form_card_nova_automacao"):
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

            # Disparo WhatsApp vinculado (admin, opcional) — FORA do form:
            # o construtor de cadência precisa de botões de adicionar/remover
            # etapa, e st.form só permite st.form_submit_button.
            disparo_auto_ativo = False
            disparo_auto_inst_id = None
            disparo_auto_int_min, disparo_auto_int_max = 30, 90
            if _admin:
                from modules import dispatch_db as _ddb_a
                st.markdown('<div class="sec">📣 Disparo WhatsApp (opcional)</div>', unsafe_allow_html=True)
                disparo_auto_ativo = st.checkbox(
                    "Disparar automaticamente para quem for extraído", key="_auto_disparo_ativo",
                )
                if disparo_auto_ativo:
                    _instancias_a = _ddb_a.listar_instancias(user_id)
                    if not _instancias_a:
                        st.warning("Conecte uma instância WhatsApp em Disparos → Instâncias antes de ativar isso.")
                    else:
                        _inst_por_nome_a = {i["nome"]: i for i in _instancias_a}
                        _inst_sel_a = st.selectbox("Instância WhatsApp", list(_inst_por_nome_a.keys()), key="_auto_disparo_inst")
                        _inst_selecionada_a = _inst_por_nome_a.get(_inst_sel_a) or {}
                        disparo_auto_inst_id = _inst_selecionada_a.get("id")

                        _dac1, _dac2 = st.columns(2)
                        with _dac1:
                            disparo_auto_int_min = st.number_input("Intervalo mínimo (s)", min_value=5, value=30, step=5, key="_auto_disparo_int_min")
                        with _dac2:
                            disparo_auto_int_max = st.number_input("Intervalo máximo (s)", min_value=5, value=90, step=5, key="_auto_disparo_int_max")
                        _ui_cadence_step_builder(
                            "_auto_disparo_steps", "_auto_disparo_step", user_id, _inst_selecionada_a,
                            ["nome", "telefone", "telefone2", "email", "endereco", "municipio", "uf", "cep", "site", "nicho", "subnicho"],
                        )
                        st.markdown('<hr class="hr">', unsafe_allow_html=True)

            with st.form("form_nova_automacao", clear_on_submit=True):
                # ── Nome ──────────────────────────────────────────────────────
                nome_auto = st.text_input("Nome da automação *", placeholder="Ex: Advogados SP — diário")

                # ── Filtros condicionais por tipo ─────────────────────────────
                if tipo_val == "maps":
                    st.markdown('<div class="sec">Busca Google Maps</div>', unsafe_allow_html=True)
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
                            cidade_auto = st.text_input("Cidade", placeholder="Ex: São Paulo, Campinas…", key="an_cidade",
                                                         help="Pode informar mais de uma cidade separando por vírgula (nesse caso, escolha só um estado).")
                        else:
                            cidade_auto = st.text_input("Cidade / Região (opcional)", placeholder="Ex: Miami…", key="an_cidade")
                    with cb:
                        if is_brasil_auto:
                            estados_auto_sel = st.multiselect("Estado", SIGLAS_ESTADOS, default=["SP"], key="an_estado",
                                                               help="Selecione vários estados só quando Cidade estiver vazio.")
                        else:
                            st.text_input("Estado", value="", disabled=True, key="an_estado_dis")
                            estados_auto_sel = []
                    with cc:
                        lim_auto_m = st.number_input("Máx. resultados", 10, 500, 50, 10, key="an_lim_m")

                    # Montar localidade(s)
                    pais_final_auto = "" if pais_auto in ("Brasil", "Outro…") else pais_auto
                    _cidades_auto_lista = [c.strip() for c in cidade_auto.split(",") if c.strip()]
                    if is_brasil_auto:
                        if _cidades_auto_lista:
                            _est_nome = ESTADOS.get(estados_auto_sel[0], estados_auto_sel[0]) if estados_auto_sel else ""
                            localidade_auto = [f"{c}, {_est_nome}" if _est_nome else c for c in _cidades_auto_lista]
                        else:
                            localidade_auto = [ESTADOS.get(e, e) for e in estados_auto_sel]
                    else:
                        localidade_auto = (
                            [f"{c}, {pais_final_auto}" if pais_final_auto else c for c in _cidades_auto_lista]
                            if _cidades_auto_lista else ([pais_final_auto] if pais_final_auto else [])
                        )
                    filtros_auto: dict = {
                        "query_base":  query_auto,
                        "localidade":  localidade_auto,
                        "nicho":       nicho_auto if not is_custom_a else query_auto,
                        "subnicho":    sub_auto,
                        "cidade":      ", ".join(_cidades_auto_lista),
                        "estado":      ", ".join(estados_auto_sel),
                        "pais":        pais_auto,
                        "limite":      int(lim_auto_m),
                        "show_phone":  st.toggle("📞 Buscar telefone e site", value=True, key="an_show_phone",
                                                  help="Chama Place Details (Contact Data). Com False: 5× mais buscas gratuitas/mês."),
                        "show_rating": st.toggle("⭐ Incluir avaliações", value=True, key="an_show_rating",
                                                  help="Vem do Text Search — sem custo adicional."),
                    }

                else:  # cnpj
                    st.markdown('<div class="sec">Busca por CNPJ</div>', unsafe_allow_html=True)
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
                        uf_a_sel = st.multiselect("Estado *", SIGLAS_ESTADOS, default=["SP"], key="an_uf")
                    with cb:
                        mun_a = st.text_input("Município (opcional)", key="an_mun",
                                               help="Pode informar mais de um separando por vírgula.")
                    with cc:
                        lim_auto_c = st.number_input("Máx. resultados", 1, 2000, 100, 50, key="an_lim_c")

                    with st.expander("📊 Filtros da empresa"):
                        st.caption("Porte, matriz/filial e regime tributário")
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
                        st.caption("Data de abertura e capital social")
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
                        "uf":                 uf_a_sel,
                        "municipio":          [m.strip() for m in mun_a.split(",") if m.strip()],
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
                st.markdown('<div class="sec">Exportação → Google Sheets</div>', unsafe_allow_html=True)
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
                st.markdown('<div class="sec">Agenda de execução (fuso: Brasília / BRT)</div>', unsafe_allow_html=True)
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
                if tipo_val == "maps" and _cidades_auto_lista and len(estados_auto_sel) > 1:
                    erros.append(
                        "Você pode selecionar vários estados sem informar cidade (busca ampla), "
                        "ou informar cidade(s) dentro de um único estado — mas não as duas coisas juntas."
                    )
                if tipo_val == "cnpj" and not filtros_auto.get("cnaes") and not filtros_auto.get("recuperacao_judicial"):
                    erros.append("Selecione ao menos um CNAE.")
                if tipo_val == "cnpj" and not filtros_auto.get("uf"):
                    erros.append("Selecione ao menos um estado.")
                if tipo_val == "cnpj" and dt_ini_a and dt_fim_a and dt_ini_a > dt_fim_a:
                    erros.append(
                        f"A data 'Abertura — de' ({dt_ini_a.strftime('%d/%m/%Y')}) está depois da "
                        f"'Abertura — até' ({dt_fim_a.strftime('%d/%m/%Y')}) — inverta as datas."
                    )
                if not dias_sel:
                    erros.append("Selecione ao menos um dia da semana.")
                if not horarios_sel:
                    erros.append("Selecione ao menos um horário de execução.")
                if disparo_auto_ativo:
                    if not disparo_auto_inst_id:
                        erros.append("Selecione uma instância WhatsApp para o disparo (ou desative a opção).")
                    _auto_disparo_steps_val = st.session_state.get("_auto_disparo_steps", [])
                    if not _auto_disparo_steps_val or not _auto_disparo_steps_val[0]["corpo_mensagem"].strip():
                        erros.append("Preencha a mensagem da primeira etapa do disparo (ou desative a opção).")
                    elif not all(s["corpo_mensagem"].strip() for s in _auto_disparo_steps_val):
                        erros.append("Todas as etapas do disparo precisam ter uma mensagem.")

                if erros:
                    for e in erros:
                        st.error(e)
                else:
                    horario_str = ",".join(sorted(horarios_sel))
                    if data_fim_sel:
                        filtros_auto["data_fim"] = data_fim_sel.strftime("%Y-%m-%d")
                    proxima = calcular_proxima_execucao(dias_sel, horario_str)

                    dispatch_campaign_id_novo = None
                    if disparo_auto_ativo and disparo_auto_inst_id:
                        from modules import dispatch_db as _ddb_b
                        dispatch_campaign_id_novo = _ddb_b.criar_campanha(
                            user_id=user_id, nome=f"[Automação] {nome_auto.strip()}",
                            instance_id=disparo_auto_inst_id, tipo_origem="automacao_busca",
                            intervalo_min_seg=int(disparo_auto_int_min), intervalo_max_seg=int(disparo_auto_int_max),
                        )
                        if dispatch_campaign_id_novo:
                            for i, s in enumerate(st.session_state["_auto_disparo_steps"], start=1):
                                _ddb_b.criar_etapa(
                                    dispatch_campaign_id_novo, i, s["atraso_horas"], s["corpo_mensagem"],
                                    template_id=s.get("template_id"), parametros_template=s.get("parametros_template"),
                                )
                            _ddb_b.atualizar_campanha(dispatch_campaign_id_novo, status="ativa")
                        else:
                            st.warning("Não foi possível criar a campanha de disparo — a automação foi criada sem ela.")

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
                        dispatch_campaign_id=dispatch_campaign_id_novo,
                    )
                    if novo_id:
                        prox_fmt = proxima.strftime('%d/%m às %H:%M') if proxima else '—'
                        msg_ok = f"✅ Automação **{nome_auto}** criada! Próxima execução: {prox_fmt}."
                        if dispatch_campaign_id_novo:
                            msg_ok += " Disparo WhatsApp vinculado e ativo."
                        st.success(msg_ok)
                        st.session_state["_auto_form_aberto"] = False
                        st.session_state["_auto_disparo_ativo"] = False
                        st.session_state["_auto_disparo_steps"] = [{"atraso_horas": 0.0, "corpo_mensagem": ""}]
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Não foi possível salvar a automação. Tente novamente.")

    # ── Lista de automações ───────────────────────────────────────────────────
    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    if not autos:
        st.markdown(
            '<div class="empty-state">⚡ Nenhuma automação criada ainda.'
            '<span class="empty-hint">Clique em "+ Nova Automação" para agendar sua primeira busca automática.</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        for auto in autos:
            _card_automacao(auto)

    # ── Automações de disparo (WhatsApp) — admin ──────────────────────────────
    if _admin:
        from modules import dispatch_db as _ddb_disp_auto

        st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
        st.markdown('<hr class="hr">', unsafe_allow_html=True)
        st.markdown("### Automações de disparo (WhatsApp)")
        st.caption("Campanhas que rodam sozinhas: disparam sempre que um lead seu bater com um filtro, ou quando uma planilha monitorada ganhar linhas novas.")

        if st.session_state.get("_auto_disp_form_aberto"):
            st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
            with st.container(key="form_card_nova_auto_disparo"):
                st.markdown("#### Nova Automação de Disparo")
                nome_ad = st.text_input("Nome", key="ad_nome", placeholder="Ex: Recuperação judicial SP")
                _instancias_ad = _ddb_disp_auto.listar_instancias(user_id)
                if not _instancias_ad:
                    st.warning("Conecte uma instância WhatsApp em Disparos → Instâncias antes de criar isso.")
                else:
                    _inst_por_nome_ad = {i["nome"]: i for i in _instancias_ad}
                    inst_sel_ad = st.selectbox("Instância WhatsApp", list(_inst_por_nome_ad.keys()), key="ad_inst")
                    _inst_selecionada_ad = _inst_por_nome_ad.get(inst_sel_ad) or {}
                    inst_id_ad = _inst_selecionada_ad.get("id")

                    gatilho_ad = st.radio("Gatilho", ["Filtro específico", "Monitorar Planilha Google"], key="ad_gatilho")

                    filtro_nicho_ad = filtro_subnicho_ad = filtro_uf_ad = ""
                    sheet_watch_cfg_ad = None
                    leads_iniciais_ad = []
                    variaveis_ad = ["nome", "telefone"]

                    if gatilho_ad == "Filtro específico":
                        fc1, fc2, fc3 = st.columns(3)
                        with fc1:
                            filtro_nicho_ad = st.text_input("Nicho", key="ad_filtro_nicho", placeholder="Ex: advogado")
                        with fc2:
                            filtro_subnicho_ad = st.text_input("Subnicho (opcional)", key="ad_filtro_subnicho")
                        with fc3:
                            filtro_uf_ad = st.selectbox("UF (opcional)", [""] + SIGLAS_ESTADOS, key="ad_filtro_uf")
                        st.caption(
                            "Dispara pra leads que **você** já extraiu (ou vier a extrair) batendo com esse "
                            "filtro. Não considera extrações de outros usuários da plataforma."
                        )
                        variaveis_ad = [
                            "nome", "telefone", "telefone2", "email", "endereco", "municipio",
                            "uf", "cep", "site", "maps_url", "avaliacao", "total_avaliacoes",
                            "cnpj", "nicho", "subnicho", "fonte",
                        ]
                    else:
                        sheet_watch_cfg_ad, leads_iniciais_ad, variaveis_ad = _ui_planilha_watch("ad_sw")

                    dac1, dac2 = st.columns(2)
                    with dac1:
                        int_min_ad = st.number_input("Intervalo mínimo (s)", min_value=5, value=30, step=5, key="ad_int_min")
                    with dac2:
                        int_max_ad = st.number_input("Intervalo máximo (s)", min_value=5, value=90, step=5, key="ad_int_max")
                    _ui_cadence_step_builder("_ad_steps", "ad_step", user_id, _inst_selecionada_ad, variaveis_ad)

                    st.markdown('<hr class="hr">', unsafe_allow_html=True)
                    if st.button("✅ Criar Automação de Disparo", type="primary", key="ad_criar", use_container_width=True):
                        _steps_ad = st.session_state["_ad_steps"]
                        _erros_ad = []
                        if not nome_ad.strip():
                            _erros_ad.append("Dê um nome.")
                        if not inst_id_ad:
                            _erros_ad.append("Selecione uma instância.")
                        if gatilho_ad == "Filtro específico" and not filtro_nicho_ad.strip() and not filtro_subnicho_ad.strip() and not filtro_uf_ad:
                            _erros_ad.append("Preencha ao menos um critério de filtro (nicho, subnicho ou UF).")
                        if gatilho_ad == "Monitorar Planilha Google" and not sheet_watch_cfg_ad:
                            _erros_ad.append("Selecione a planilha, a aba e as colunas de telefone.")
                        if not _steps_ad[0]["corpo_mensagem"].strip():
                            _erros_ad.append("Preencha a mensagem da primeira etapa.")
                        elif not all(s["corpo_mensagem"].strip() for s in _steps_ad):
                            _erros_ad.append("Todas as etapas precisam ter uma mensagem.")

                        if _erros_ad:
                            for e in _erros_ad:
                                st.error(e)
                        else:
                            tipo_origem_ad = "auto_trigger" if gatilho_ad == "Filtro específico" else "sheet_watch"
                            camp_id_ad = _ddb_disp_auto.criar_campanha(
                                user_id=user_id, nome=nome_ad.strip(), instance_id=inst_id_ad,
                                tipo_origem=tipo_origem_ad,
                                filtro_nicho=filtro_nicho_ad.strip(), filtro_subnicho=filtro_subnicho_ad.strip(),
                                filtro_uf=filtro_uf_ad,
                                intervalo_min_seg=int(int_min_ad), intervalo_max_seg=int(int_max_ad),
                            )
                            if not camp_id_ad:
                                st.error("Erro ao criar a automação de disparo.")
                            else:
                                for i, s in enumerate(_steps_ad, start=1):
                                    _ddb_disp_auto.criar_etapa(
                                        camp_id_ad, i, s["atraso_horas"], s["corpo_mensagem"],
                                        template_id=s.get("template_id"), parametros_template=s.get("parametros_template"),
                                    )
                                if tipo_origem_ad == "sheet_watch":
                                    _ddb_disp_auto.criar_sheet_watcher(
                                        camp_id_ad, sheet_watch_cfg_ad["sheet_id"], sheet_watch_cfg_ad["aba_nome"],
                                        sheet_watch_cfg_ad["coluna_telefone"], sheet_watch_cfg_ad["coluna_nome"],
                                        ultima_linha_processada=sheet_watch_cfg_ad["linhas_existentes"],
                                    )
                                resultado_ad = {"inscritos": 0, "invalidos": 0, "duplicados": 0, "opt_out": 0}
                                if leads_iniciais_ad:
                                    resultado_ad = _ddb_disp_auto.enroll_targets(camp_id_ad, leads_iniciais_ad)
                                _ddb_disp_auto.atualizar_campanha(camp_id_ad, status="ativa")
                                st.session_state["_auto_disp_form_aberto"] = False
                                st.session_state["_ad_steps"] = [{"atraso_horas": 0.0, "corpo_mensagem": ""}]
                                st.success(
                                    f"Automação de disparo **{nome_ad}** criada e ativa! "
                                    f"{resultado_ad['inscritos']} contato(s) já inscritos. Acompanhe em Disparos → Relatórios."
                                )
                                time.sleep(0.5)
                                st.rerun()

        _camps_disparo_auto = [
            c for c in _ddb_disp_auto.listar_campanhas(user_id)
            if c.get("tipo_origem") in ("auto_trigger", "sheet_watch")
        ]
        if _camps_disparo_auto:
            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
            for camp_ad in _camps_disparo_auto:
                _stats_ad = _ddb_disp_auto.stats_campanha(camp_ad["id"])
                _gatilho_lbl = "🎯 Gatilho por filtro" if camp_ad["tipo_origem"] == "auto_trigger" else "📊 Monitorando planilha"
                with st.expander(f"{camp_ad['nome']} — {camp_ad.get('status','').upper()} · {_gatilho_lbl}"):
                    st.markdown(
                        f"📇 {_stats_ad['total']} inscritos · ⏳ {_stats_ad['pendente']} pendentes · "
                        f"✅ {_stats_ad['concluido']} concluídos · ❌ {_stats_ad['falhou']} falharam"
                    )
                    bcad1, bcad2 = st.columns(2)
                    with bcad1:
                        if camp_ad.get("status") == "ativa":
                            if st.button("⏸️ Pausar", key=f"ad_pause_{camp_ad['id']}", use_container_width=True):
                                _ddb_disp_auto.atualizar_campanha(camp_ad["id"], status="pausada")
                                st.rerun()
                        else:
                            if st.button("▶️ Ativar", key=f"ad_activate_{camp_ad['id']}", use_container_width=True):
                                _ddb_disp_auto.atualizar_campanha(camp_ad["id"], status="ativa")
                                st.rerun()
                    with bcad2:
                        if st.button("🗑️ Excluir", key=f"ad_del_{camp_ad['id']}", use_container_width=True):
                            _ddb_disp_auto.deletar_campanha(camp_ad["id"])
                            st.rerun()


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
    _conta_teste_cfg = bool(st.session_state.get("conta_teste", False))

    # ── Google Maps ─────────────────────────────────────────────────────────────
    with st.expander("🗺️ Google Maps API", expanded=True):
        if _conta_teste_cfg:
            st.info("Esta é uma conta de teste — usa a chave Google Maps da plataforma, sem custo pra você.", icon="🧪")
        elif st.session_state.get("maps_credits_enabled"):
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
                        _pcls = "b-err" if _ppct >= 1.0 else ("b-warn" if _ppct >= 0.8 else "b-ok")
                        st.markdown(f'<span class="badge {_pcls}">{_pmon}: {_puse}/{_plim}</span>', unsafe_allow_html=True)
                    with _pc3:
                        if st.button("🗑️", key=f"del_cfg_mk_{_pi}", help="Remover"):
                            st.session_state["_conf_del_cfg_mk_idx"] = _pi
                            st.rerun()

                _del_idx = st.session_state.get("_conf_del_cfg_mk_idx")
                if _del_idx is not None and _del_idx < len(_cfg_pool):
                    _del_nome = _cfg_pool[_del_idx].get("nickname") or f"Chave {_del_idx+1}"
                    st.warning(f"Remover a chave **{_del_nome}** do pool?")
                    _dmc1, _dmc2 = st.columns(2)
                    with _dmc1, st.container(key="danger_del_cfg_mk"):
                        if st.button("✅ Sim, remover", key="conf_del_cfg_mk_ok", type="primary"):
                            _np = [k for j, k in enumerate(_cfg_pool) if j != _del_idx]
                            st.session_state.pop("_conf_del_cfg_mk_idx", None)
                            if salvar_pool_maps_usuario(_np):
                                st.rerun()
                    with _dmc2:
                        if st.button("Cancelar", key="conf_del_cfg_mk_no"):
                            st.session_state.pop("_conf_del_cfg_mk_idx", None)
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

    # ── Comportamento geral ao esgotar limites (Maps e/ou Apify) ────────────────────
    with st.expander("⚙️ Ao esgotar o limite das chaves de API", expanded=False):
        st.markdown(
            "Vale pra Google Maps e Apify juntos — sempre que a busca esgotar a chave "
            "que está usando no momento, o que fazer a seguir:"
        )
        _pausar_atual = bool(cfg.get("maps_pausar_ao_esgotar", False))
        _opcao_esgotar = st.radio(
            "Comportamento ao esgotar",
            ["Continuar buscando (pode gerar cobrança de outra API)", "Pausar a busca"],
            index=1 if _pausar_atual else 0,
            key="cfg_maps_pausar", label_visibility="collapsed",
        )
        _novo_pausar = _opcao_esgotar.startswith("Pausar")
        if _novo_pausar != _pausar_atual:
            ok_pz, msg_pz = salvar_configuracoes({"maps_pausar_ao_esgotar": _novo_pausar})
            (st.success if ok_pz else st.error)(msg_pz)
            if ok_pz:
                time.sleep(0.3)
                st.rerun()
        st.caption(
            "Se você só tem chave de um dos dois configurada e ela esgotar, a busca sempre "
            "para (não tem pra onde continuar). Isso só muda o comportamento quando há uma "
            "segunda chave disponível pra continuar buscando."
        )

    # ── Apify API Key ─────────────────────────────────────────────────────────────
    with st.expander("🤖 Apify API Key", expanded=False):
        if _conta_teste_cfg:
            st.info("Esta é uma conta de teste — usa a chave Apify da plataforma, sem custo pra você.", icon="🧪")
        else:
            _apify_desc = "Usada como **fallback automático** na busca Google Maps (quando a cota é esgotada, $4/1.000 resultados) e na busca Instagram."
            st.markdown(_apify_desc)
            st.markdown("Configure uma ou mais chaves Apify. O sistema usa rodízio automático quando uma chave atinge o limite mensal.")
            from modules.database import obter_pool_apify_usuario, salvar_pool_apify_usuario
            _cfg_apool = obter_pool_apify_usuario()
            if _cfg_apool:
                for _api, _ape in enumerate(_cfg_apool):
                    _apc1, _apc2, _apc3 = st.columns([3, 3, 1])
                    with _apc1:
                        st.caption(_ape.get("nickname") or f"Chave {_api+1}")
                    with _apc2:
                        _apuse = int(_ape.get("usage", 0))
                        _aplim = int(_ape.get("limit", 900))
                        _apmon = _ape.get("month", "—")
                        _appct = min(_apuse / max(_aplim, 1), 1.0)
                        _apcls = "b-err" if _appct >= 1.0 else ("b-warn" if _appct >= 0.8 else "b-ok")
                        st.markdown(f'<span class="badge {_apcls}">{_apmon}: {_apuse}/{_aplim}</span>', unsafe_allow_html=True)
                    with _apc3:
                        if st.button("🗑️", key=f"del_cfg_ak_{_api}", help="Remover"):
                            st.session_state["_conf_del_cfg_ak_idx"] = _api
                            st.rerun()

                _del_aidx = st.session_state.get("_conf_del_cfg_ak_idx")
                if _del_aidx is not None and _del_aidx < len(_cfg_apool):
                    _del_anome = _cfg_apool[_del_aidx].get("nickname") or f"Chave {_del_aidx+1}"
                    st.warning(f"Remover a chave **{_del_anome}** do pool?")
                    _dac1, _dac2 = st.columns(2)
                    with _dac1, st.container(key="danger_del_cfg_ak"):
                        if st.button("✅ Sim, remover", key="conf_del_cfg_ak_ok", type="primary"):
                            _nap = [k for j, k in enumerate(_cfg_apool) if j != _del_aidx]
                            st.session_state.pop("_conf_del_cfg_ak_idx", None)
                            if salvar_pool_apify_usuario(_nap):
                                st.rerun()
                    with _dac2:
                        if st.button("Cancelar", key="conf_del_cfg_ak_no"):
                            st.session_state.pop("_conf_del_cfg_ak_idx", None)
                            st.rerun()
            with st.form("add_cfg_ak"):
                _afc1, _afc2, _afc3 = st.columns([2, 4, 2])
                with _afc1:
                    _afn = st.text_input("Apelido", placeholder="Chave 1", key="cfg_ak_nick")
                with _afc2:
                    _afk = st.text_input("Chave API", placeholder="apify_api_...", type="password", key="cfg_ak_val")
                with _afc3:
                    _afl = st.number_input("Limite/mês", min_value=100, value=1000, step=100, key="cfg_ak_lim")
                if st.form_submit_button("➕ Adicionar chave", use_container_width=True):
                    if _afk:
                        _nap = list(_cfg_apool) + [{
                            "key": _afk, "nickname": _afn or f"Chave {len(_cfg_apool)+1}",
                            "usage": 0, "month": "", "limit": int(_afl),
                        }]
                        if salvar_pool_apify_usuario(_nap):
                            st.success("Chave adicionada!")
                            st.rerun()
            # Chave única (compatibilidade)
            with st.expander("Ou use chave única (modo legado)"):
                _apify_cur = st.session_state.get("apify_api_key_user", "")
                apify_inp = st.text_input(
                    "Apify API Key",
                    value=_apify_cur,
                    type="password",
                    placeholder="apify_api_...",
                    key="cfg_apify_key",
                )
                if st.button("💾 Salvar chave única", key="save_apify"):
                    from modules.database import salvar_configuracoes
                    ok_ap, msg_ap = salvar_configuracoes({"apify_api_key": apify_inp.strip()})
                    if ok_ap:
                        st.session_state["apify_api_key_user"] = apify_inp.strip()
                        st.success("Chave Apify salva com sucesso.")
                    else:
                        st.error(msg_ap)

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

                st.markdown('<hr class="hr">', unsafe_allow_html=True)
                st.markdown('<div class="sec">📋 Planilhas configuradas</div>', unsafe_allow_html=True)

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
                _bc1, _bc2 = st.columns(2)
                with _bc1:
                    if st.button("🔄 Renovar conexão", key="renew_google", use_container_width=True, help="Renova o token Google sem apagar suas planilhas"):
                        _pl = st.session_state.get("sheets_planilhas", [])
                        _ae = st.session_state.get("auto_export_enabled", False)
                        for k in ["sheets_creds", "sheets_lista"]:
                            st.session_state.pop(k, None)
                        salvar_configuracoes({"google_sheets_creds": {"oauth": None, "planilhas": _pl, "auto_export": _ae}})
                        st.rerun()
                with _bc2:
                    if st.button("🔓 Desconectar", key="disc_google", use_container_width=True, help="Remove a conta Google e todas as planilhas configuradas"):
                        st.session_state["_conf_disc_google"] = True
                        st.rerun()

                if st.session_state.get("_conf_disc_google"):
                    st.warning("Tem certeza? Isso remove a conta Google conectada e **todas** as planilhas configuradas.")
                    dc1, dc2 = st.columns(2)
                    with dc1, st.container(key="danger_disc_google"):
                        if st.button("✅ Sim, desconectar", key="conf_disc_google_ok", type="primary"):
                            for k in ["sheets_creds", "sheets_planilhas", "auto_export_enabled", "sheets_lista"]:
                                st.session_state.pop(k, None)
                            salvar_configuracoes({"google_sheets_creds": None})
                            st.session_state.pop("_conf_disc_google", None)
                            st.rerun()
                    with dc2:
                        if st.button("Cancelar", key="conf_disc_google_no"):
                            st.session_state.pop("_conf_disc_google", None)
                            st.rerun()
            else:
                _planilhas_salvas = st.session_state.get("sheets_planilhas", [])
                if _planilhas_salvas:
                    st.info(f"Suas {len(_planilhas_salvas)} planilha(s) configurada(s) serão restauradas automaticamente após reconectar.", icon="ℹ️")
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
        with c3: new_role_ui = st.selectbox("Papel", ["user","admin","🧪 teste"], key="adm_role")

        _eh_teste_novo = (new_role_ui == "🧪 teste")
        _teste_cdd, _teste_maps, _teste_dias = 100, 100, 7
        _teste_disparo, _teste_insta = False, True
        if _eh_teste_novo:
            st.markdown('<div class="sec">🧪 Configuração da conta de teste</div>', unsafe_allow_html=True)
            tc1, tc2, tc3 = st.columns(3)
            with tc1:
                _teste_cdd = st.number_input("Créditos CNPJ iniciais", min_value=0, value=100, step=50, key="adm_teste_cdd")
            with tc2:
                _teste_maps = st.number_input("Créditos Maps iniciais", min_value=0, value=100, step=50, key="adm_teste_maps")
            with tc3:
                _teste_dias = st.number_input("Validade (dias)", min_value=1, value=7, step=1, key="adm_teste_dias")
            td1, td2 = st.columns(2)
            with td1:
                _teste_disparo = st.toggle("Habilitar Disparos (WhatsApp)", value=False, key="adm_teste_disparo")
            with td2:
                _teste_insta = st.toggle("Exibir aba Instagram", value=True, key="adm_teste_insta")
            st.caption(
                "Usa a chave Google Maps compartilhada de contas de teste (configure em "
                "🧪 Chave Maps — Contas de Teste, mais abaixo) e a chave CNPJ da plataforma — "
                "não pode configurar chaves próprias."
            )

        if st.button("✅ Criar usuário", key="btn_criar_user"):
            if not new_email or not new_senha:
                st.warning("Preencha e-mail e senha.")
            elif len(new_senha) < 6:
                st.error("Senha deve ter pelo menos 6 caracteres.")
            else:
                _extra = None
                if _eh_teste_novo:
                    from datetime import datetime, timedelta, timezone
                    _extra = {
                        "conta_teste":          True,
                        "teste_expira_em":      (datetime.now(timezone.utc) + timedelta(days=int(_teste_dias))).isoformat(),
                        "cdd_credits":          int(_teste_cdd),
                        "maps_credits":         int(_teste_maps),
                        "maps_credits_enabled": True,
                        "disparo_habilitado":   bool(_teste_disparo),
                        "instagram_visible":    bool(_teste_insta),
                    }
                _role_final = "admin" if new_role_ui == "admin" else "user"
                ok, msg = criar_usuario(new_email.strip(), new_senha, _role_final, extra=_extra)
                (st.success if ok else st.error)(msg)
                if ok: time.sleep(0.3); st.rerun()

    # ── Chave Maps compartilhada entre contas de teste ────────────────────────────
    with st.expander("🧪 Chave Maps — Contas de Teste", expanded=False):
        st.markdown(
            "Chave (ou pool de chaves) do Google Maps usada por **todas** as contas de teste — "
            "elas não configuram chave própria. Configure aqui, ou defina a variável de ambiente "
            "`MAPS_API_KEY_TESTE` (Secrets do Streamlit / variável no Railway) como alternativa fixa. "
            "Se as duas existirem, essa aqui (pool com rodízio e limite) tem prioridade."
        )
        from modules.auth import obter_pool_maps_teste, salvar_pool_maps_teste
        _tpool = obter_pool_maps_teste()
        if _tpool:
            for _ti, _te in enumerate(_tpool):
                _tc1, _tc2, _tc3 = st.columns([3, 3, 1])
                with _tc1:
                    st.caption(_te.get("nickname") or f"Chave {_ti+1}")
                with _tc2:
                    _tuse = int(_te.get("usage", 0))
                    _tlim = int(_te.get("limit", 900))
                    _tmon = _te.get("month", "—")
                    _tpct = min(_tuse / max(_tlim, 1), 1.0)
                    _tcls = "b-err" if _tpct >= 1.0 else ("b-warn" if _tpct >= 0.8 else "b-ok")
                    st.markdown(f'<span class="badge {_tcls}">{_tmon}: {_tuse}/{_tlim}</span>', unsafe_allow_html=True)
                with _tc3:
                    if st.button("🗑️", key=f"del_tk_{_ti}", help="Remover"):
                        st.session_state["_conf_del_tk_idx"] = _ti
                        st.rerun()

            _del_tidx = st.session_state.get("_conf_del_tk_idx")
            if _del_tidx is not None and _del_tidx < len(_tpool):
                _del_tnome = _tpool[_del_tidx].get("nickname") or f"Chave {_del_tidx+1}"
                st.warning(f"Remover a chave **{_del_tnome}** do pool de teste?")
                _dtc1, _dtc2 = st.columns(2)
                with _dtc1, st.container(key="danger_del_tk"):
                    if st.button("✅ Sim, remover", key="conf_del_tk_ok", type="primary"):
                        _ntp = [k for j, k in enumerate(_tpool) if j != _del_tidx]
                        st.session_state.pop("_conf_del_tk_idx", None)
                        if salvar_pool_maps_teste(_ntp):
                            st.rerun()
                with _dtc2:
                    if st.button("Cancelar", key="conf_del_tk_no"):
                        st.session_state.pop("_conf_del_tk_idx", None)
                        st.rerun()
        else:
            st.caption("Nenhuma chave configurada — contas de teste cairão na variável `MAPS_API_KEY_TESTE`, se existir.")
        with st.form("add_tk"):
            _ttc1, _ttc2, _ttc3 = st.columns([2, 4, 2])
            with _ttc1:
                _ttn = st.text_input("Apelido", placeholder="Chave Teste", key="tk_nick")
            with _ttc2:
                _ttk = st.text_input("Chave API", placeholder="AIzaSy...", type="password", key="tk_val")
            with _ttc3:
                _ttl = st.number_input("Limite/mês", min_value=100, value=900, step=100, key="tk_lim")
            if st.form_submit_button("➕ Adicionar chave", use_container_width=True):
                if _ttk:
                    _ntp = list(_tpool) + [{
                        "key": _ttk, "nickname": _ttn or f"Chave {len(_tpool)+1}",
                        "usage": 0, "month": "", "limit": int(_ttl),
                    }]
                    if salvar_pool_maps_teste(_ntp):
                        st.success("Chave adicionada!")
                        st.rerun()

    st.markdown('<hr class="hr">', unsafe_allow_html=True)

    # ── Lista de usuários ────────────────────────────────────────────────────────
    ok, usuarios, err = listar_usuarios()
    if not ok:
        logger.error("Erro ao carregar usuários: %s", err)
        st.error("Não foi possível carregar a lista de usuários.")
        return
    if not usuarios:
        st.markdown('<div class="empty-state">👤 Nenhum usuário cadastrado.</div>', unsafe_allow_html=True)
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
        conta_teste_u = bool(u.get("conta_teste", False))
        teste_exp_u   = u.get("teste_expira_em") or ""

        badge = "🟢 admin" if role == "admin" else "⚪ user"
        if conta_teste_u:
            from datetime import datetime, timezone
            _teste_expirada_u = False
            _dias_rest_u = None
            if teste_exp_u:
                try:
                    _exp_dt_u = datetime.fromisoformat(str(teste_exp_u).replace("Z", "+00:00"))
                    _dias_rest_u = (_exp_dt_u - datetime.now(timezone.utc)).days
                    _teste_expirada_u = _dias_rest_u < 0
                except Exception:
                    pass
            badge = "🔴 teste expirada" if _teste_expirada_u else f"🧪 teste ({_dias_rest_u}d restantes)" if _dias_rest_u is not None else "🧪 teste"
        maps_tag = "  ·  🗺️ Maps ativo" if maps_en else ""
        label = f"{badge}  **{email}**  ·  🪙 CNPJ: {cdd_bal}{maps_tag}" + ("  *(você)*" if me else "")

        with st.expander(label):
            st.caption(f"ID: `{uid}`  ·  Criado em {created}  ·  {searches} pesquisas  ·  {leads_tot} leads  ·  Última busca: {last_s}")

            if conta_teste_u:
                st.markdown('<div class="sec">🧪 Conta de Teste</div>', unsafe_allow_html=True)
                _exp_txt_u = str(teste_exp_u)[:10] if teste_exp_u else "—"
                if _teste_expirada_u:
                    st.error(f"Expirou em {_exp_txt_u} — usuário está bloqueado.")
                else:
                    st.caption(f"Válida até **{_exp_txt_u}** ({_dias_rest_u} dia(s) restantes).")
                te1, te2, te3 = st.columns([2, 1, 1])
                with te1:
                    from datetime import date as _date_cls
                    _data_atual_u = _date_cls.fromisoformat(_exp_txt_u) if teste_exp_u else _date_cls.today()
                    _nova_data_u = st.date_input("Nova data de validade", value=_data_atual_u, key=f"teste_exp_{uid}")
                with te2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 Salvar validade", key=f"teste_exp_save_{uid}", use_container_width=True):
                        from datetime import datetime as _dt_cls, timezone as _tz
                        _nova_exp_iso = _dt_cls.combine(_nova_data_u, _dt_cls.max.time(), tzinfo=_tz.utc).isoformat()
                        ok_te, msg_te = configurar_creditos_admin(uid, teste_expira_em=_nova_exp_iso)
                        (st.success if ok_te else st.error)(msg_te)
                        if ok_te: time.sleep(0.3); st.rerun()
                with te3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🔓 Tornar permanente", key=f"teste_conv_{uid}", use_container_width=True, help="Remove a marca de conta de teste — vira conta normal, mantém créditos e configurações atuais."):
                        ok_tc, msg_tc = configurar_creditos_admin(uid, conta_teste=False)
                        (st.success if ok_tc else st.error)(msg_tc)
                        if ok_tc: time.sleep(0.3); st.rerun()
                st.markdown('<hr class="hr">', unsafe_allow_html=True)

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
                    st.session_state[f"_conf_del_u_{uid}"] = True
                    st.rerun()

            if st.session_state.get(f"_conf_del_u_{uid}"):
                st.warning(f"Tem certeza que deseja remover **{email}** e todos os dados dele (pesquisas, leads, automações)? Esta ação não pode ser desfeita.")
                uc1, uc2 = st.columns(2)
                with uc1, st.container(key=f"danger_del_u_{uid}"):
                    if st.button("✅ Sim, remover", key=f"conf_del_u_ok_{uid}", type="primary"):
                        ok4, msg4 = deletar_usuario(uid)
                        st.session_state.pop(f"_conf_del_u_{uid}", None)
                        (st.success if ok4 else st.error)(msg4)
                        if ok4: time.sleep(0.3); st.rerun()
                with uc2:
                    if st.button("Cancelar", key=f"conf_del_u_no_{uid}"):
                        st.session_state.pop(f"_conf_del_u_{uid}", None)
                        st.rerun()

            st.markdown('<hr class="hr">', unsafe_allow_html=True)

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
            st.markdown('<div class="sec">🗺️ Créditos Maps</div>', unsafe_allow_html=True)
            maps_toggle = st.toggle("Habilitar créditos Maps (oculta chave própria do usuário)", value=maps_en, key=f"maps_en_{uid}")
            if maps_toggle != maps_en:
                ok8, msg8 = configurar_creditos_admin(uid, maps_credits_enabled=maps_toggle)
                (st.success if ok8 else st.error)(msg8)
                if ok8: time.sleep(0.3); st.rerun()

            if maps_toggle:
                if conta_teste_u:
                    st.caption(
                        "Conta de teste — usa a chave Maps compartilhada de contas de teste "
                        "(veja 🧪 Chave Maps — Contas de Teste, no topo desta página), não um pool próprio."
                    )
                else:
                    # ── Pool de chaves Maps ──────────────────────────────────
                    from modules.auth import obter_pool_maps_usuario_admin
                    _upool = obter_pool_maps_usuario_admin(uid)
                    st.markdown('<div class="sec">Chaves de API Maps (rodízio automático por mês)</div>', unsafe_allow_html=True)
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
                                _kcls = "b-err" if _kpct >= 1.0 else ("b-warn" if _kpct >= 0.8 else "b-ok")
                                st.markdown(f'<span class="badge {_kcls}">{_kmon}: {_kuse}/{_klim}</span>', unsafe_allow_html=True)
                            with _kc3:
                                if st.button("🗑️", key=f"del_mk_{uid}_{_ki}", help="Remover chave"):
                                    st.session_state[f"_conf_del_mk_idx_{uid}"] = _ki
                                    st.rerun()

                        _del_kidx = st.session_state.get(f"_conf_del_mk_idx_{uid}")
                        if _del_kidx is not None and _del_kidx < len(_upool):
                            _del_knome = _upool[_del_kidx].get("nickname") or f"Chave {_del_kidx+1}"
                            st.warning(f"Remover a chave **{_del_knome}** do pool deste usuário?")
                            _dkc1, _dkc2 = st.columns(2)
                            with _dkc1, st.container(key=f"danger_del_mk_{uid}"):
                                if st.button("✅ Sim, remover", key=f"conf_del_mk_ok_{uid}", type="primary"):
                                    _np = [k for j, k in enumerate(_upool) if j != _del_kidx]
                                    st.session_state.pop(f"_conf_del_mk_idx_{uid}", None)
                                    _ok_p, _msg_p = configurar_creditos_admin(uid, maps_keys_pool=_np)
                                    (st.success if _ok_p else st.error)(_msg_p)
                                    if _ok_p: time.sleep(0.3); st.rerun()
                            with _dkc2:
                                if st.button("Cancelar", key=f"conf_del_mk_no_{uid}"):
                                    st.session_state.pop(f"_conf_del_mk_idx_{uid}", None)
                                    st.rerun()
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

            # ── Chaves de API Apify — sempre visível, igual ao Maps ─────
            # Usada tanto no fallback da busca Google Maps (após esgotar o pool
            # de Maps) quanto na busca Instagram, sempre que o usuário não
            # tiver chave própria. Rodízio mensal por chave — se todas
            # estourarem o limite, a busca continua na última em vez de travar.
            st.markdown('<div class="sec">🤖 Chaves de API Apify (rodízio automático por mês — fallback Maps + busca Instagram)</div>', unsafe_allow_html=True)
            from modules.auth import obter_pool_apify_usuario_admin
            _apool = obter_pool_apify_usuario_admin(uid)
            if _apool:
                for _ai, _ae in enumerate(_apool):
                    _apc1, _apc2, _apc3 = st.columns([3, 3, 1])
                    with _apc1:
                        st.caption(_ae.get("nickname") or f"Chave {_ai+1}")
                    with _apc2:
                        _ause = int(_ae.get("usage", 0))
                        _alim = int(_ae.get("limit", 900))
                        _amon = _ae.get("month", "—")
                        _apct = min(_ause / max(_alim, 1), 1.0)
                        _acls = "b-err" if _apct >= 1.0 else ("b-warn" if _apct >= 0.8 else "b-ok")
                        st.markdown(f'<span class="badge {_acls}">{_amon}: {_ause}/{_alim}</span>', unsafe_allow_html=True)
                    with _apc3:
                        if st.button("🗑️", key=f"del_ak_{uid}_{_ai}", help="Remover chave"):
                            st.session_state[f"_conf_del_ak_idx_{uid}"] = _ai
                            st.rerun()

                _del_aaidx = st.session_state.get(f"_conf_del_ak_idx_{uid}")
                if _del_aaidx is not None and _del_aaidx < len(_apool):
                    _del_aanome = _apool[_del_aaidx].get("nickname") or f"Chave {_del_aaidx+1}"
                    st.warning(f"Remover a chave **{_del_aanome}** do pool deste usuário?")
                    _dakc1, _dakc2 = st.columns(2)
                    with _dakc1, st.container(key=f"danger_del_ak_{uid}"):
                        if st.button("✅ Sim, remover", key=f"conf_del_ak_ok_{uid}", type="primary"):
                            _nap = [k for j, k in enumerate(_apool) if j != _del_aaidx]
                            st.session_state.pop(f"_conf_del_ak_idx_{uid}", None)
                            _ok_ap, _msg_ap = configurar_creditos_admin(uid, apify_keys_pool=_nap)
                            (st.success if _ok_ap else st.error)(_msg_ap)
                            if _ok_ap: time.sleep(0.3); st.rerun()
                    with _dakc2:
                        if st.button("Cancelar", key=f"conf_del_ak_no_{uid}"):
                            st.session_state.pop(f"_conf_del_ak_idx_{uid}", None)
                            st.rerun()
            else:
                st.caption("Nenhuma chave no pool configurada.")
            with st.form(f"add_ak_{uid}"):
                _aac1, _aac2, _aac3 = st.columns([2, 4, 2])
                with _aac1:
                    _new_anick = st.text_input("Apelido", placeholder="Chave 1", key=f"ak_nick_{uid}")
                with _aac2:
                    _new_akval = st.text_input("Chave API", placeholder="apify_api_...", type="password", key=f"ak_val_{uid}")
                with _aac3:
                    _new_aklim = st.number_input("Limite/mês", min_value=100, value=900, step=100, key=f"ak_lim_{uid}")
                if st.form_submit_button("➕ Adicionar chave", use_container_width=True):
                    if _new_akval:
                        _nap = list(_apool) + [{
                            "key": _new_akval,
                            "nickname": _new_anick or f"Chave {len(_apool)+1}",
                            "usage": 0, "month": "", "limit": int(_new_aklim),
                        }]
                        _ok_ap, _msg_ap = configurar_creditos_admin(uid, apify_keys_pool=_nap)
                        (st.success if _ok_ap else st.error)(_msg_ap)
                        if _ok_ap: time.sleep(0.3); st.rerun()

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

            # ── Disparos — liberação individual (desativado por padrão) ─
            disparo_hab = bool(u.get("disparo_habilitado", False))
            disparo_hab_toggle = st.toggle(
                "Habilitar Disparos (WhatsApp) para este usuário",
                value=disparo_hab, key=f"disparo_hab_{uid}",
            )
            if disparo_hab_toggle != disparo_hab:
                ok_dh, msg_dh = configurar_creditos_admin(uid, disparo_habilitado=disparo_hab_toggle)
                (st.success if ok_dh else st.error)(msg_dh)
                if ok_dh: time.sleep(0.3); st.rerun()

            insta_en     = bool(u.get("instagram_credits_enabled", False))
            insta_bal    = int(u.get("instagram_credits", 0) or 0)
            monthly_insta = int(u.get("monthly_instagram_credits", 0) or 0)

            st.markdown('<div class="sec">📸 Créditos Instagram</div>', unsafe_allow_html=True)
            insta_toggle = st.toggle(
                "Habilitar créditos Instagram (usa chave Apify da plataforma acima)",
                value=insta_en, key=f"insta_en_{uid}",
            )
            if insta_toggle != insta_en:
                ok_it, msg_it = configurar_creditos_admin(uid, instagram_credits_enabled=insta_toggle)
                (st.success if ok_it else st.error)(msg_it)
                if ok_it: time.sleep(0.3); st.rerun()

            if insta_toggle:
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


# ── Disparo WhatsApp (admin-only) ───────────────────────────────────────────

_ORIGEM_CAMPANHA_LBL = {
    "busca_existente": "📋 Busca existente",
    "upload":          "📤 Upload de planilha",
    "manual":          "✍️ Números manuais",
    "auto_trigger":    "🎯 Gatilho por filtro",
    "sheet_watch":     "📊 Monitorando planilha",
    "automacao_busca": "🔗 Vinculada à automação",
    "planilha_google": "📄 Planilha Google (pontual)",
}

_CANDIDATOS_COL_NOME = ["nome", "name", "empresa", "razao", "razão", "contato"]
_CANDIDATOS_COL_TEL = ["telefone", "phone", "celular", "whatsapp", "fone", "numero", "número"]

_STATUS_TEMPLATE_LBL = {
    "rascunho": ("b-warn", "Rascunho"),
    "pendente": ("b-warn", "Pendente (Meta)"),
    "aprovado": ("b-ok",   "Aprovado"),
    "rejeitado": ("b-err", "Rejeitado"),
}


def _extrair_partes_template(componentes: list) -> tuple[str, str, str]:
    """(cabeçalho, corpo, rodapé) a partir do JSONB `componentes` no formato
    da Meta — fonte única de verdade pro conteúdo do template, evita perder
    cabeçalho/rodapé ao reenviar um rascunho salvo antes pra aprovação."""
    cabecalho = corpo = rodape = ""
    for c in componentes or []:
        tipo = (c.get("type") or "").upper()
        if tipo == "HEADER":
            cabecalho = c.get("text", "") or ""
        elif tipo == "BODY":
            corpo = c.get("text", "") or ""
        elif tipo == "FOOTER":
            rodape = c.get("text", "") or ""
    return cabecalho, corpo, rodape


def _detectar_col(colunas: list, candidatos: list[str], padrao_idx: int) -> int:
    for i, c in enumerate(colunas):
        cl = str(c).strip().lower()
        if any(k in cl for k in candidatos):
            return i
    return padrao_idx


def _ui_planilha_watch(key_prefix: str):
    """
    UI compartilhada pra escolher planilha/aba/colunas do Google Sheets a
    monitorar (usada tanto em Disparos → Campanhas quanto em Automações →
    Automação de disparo — um único lugar evita a lógica divergir entre
    as duas telas).

    Retorna (sheet_watch_cfg, leads_iniciais, variaveis_disp).
    sheet_watch_cfg é None se a seleção ainda não está completa.
    """
    from modules import google_sheets
    vazio = (None, [], ["nome", "telefone"])
    creds_sheet = st.session_state.get("sheets_creds")
    if not creds_sheet:
        st.info("Conecte sua conta Google em ⚙️ Configurações antes de monitorar uma planilha.", icon="ℹ️")
        return vazio
    try:
        planilhas_drive = google_sheets.listar_planilhas(creds_sheet)
    except Exception as e:
        st.error(f"Erro ao listar planilhas: {e}")
        return vazio
    if not planilhas_drive:
        st.caption("Nenhuma planilha encontrada na sua conta Google.")
        return vazio

    sheet_opts = {p["name"]: p["id"] for p in planilhas_drive}
    sheet_sel_nome = st.selectbox("Planilha", list(sheet_opts.keys()), key=f"{key_prefix}_sheet")
    sheet_id_sel = sheet_opts.get(sheet_sel_nome)
    try:
        abas_disp = google_sheets.listar_abas(creds_sheet, sheet_id_sel) if sheet_id_sel else []
    except Exception as e:
        st.error(f"Erro ao listar abas: {e}")
        return vazio
    if not abas_disp:
        return vazio

    aba_sel = st.selectbox("Aba", abas_disp, key=f"{key_prefix}_aba")
    try:
        valores_sheet = google_sheets.ler_valores(creds_sheet, sheet_id_sel, aba_sel)
    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        return vazio
    if not valores_sheet:
        st.caption("A aba está vazia (ou só tem cabeçalho).")
        return vazio

    cabecalho_sheet = [str(c) for c in valores_sheet[0]]
    linhas_sheet = valores_sheet[1:]
    idx_nome_sw = _detectar_col(cabecalho_sheet, _CANDIDATOS_COL_NOME, 0)
    idx_tel_sw = _detectar_col(cabecalho_sheet, _CANDIDATOS_COL_TEL, min(1, len(cabecalho_sheet) - 1))
    scc1, scc2 = st.columns(2)
    with scc1:
        col_nome_sw = st.selectbox("Coluna do nome", cabecalho_sheet, index=idx_nome_sw, key=f"{key_prefix}_col_nome")
    with scc2:
        col_tel_sw = st.selectbox("Coluna do telefone", cabecalho_sheet, index=idx_tel_sw, key=f"{key_prefix}_col_tel")

    modo_sw = st.radio(
        "A partir de quando disparar",
        [
            "Desde o início — dispara pro que já está na planilha e continua monitorando",
            "Só a partir de agora — ignora o que já está, dispara só pro que for adicionado depois",
        ],
        key=f"{key_prefix}_modo",
    )
    st.caption(f"{len(linhas_sheet)} linha(s) de dados na planilha agora. A planilha continua sendo monitorada enquanto a campanha estiver ativa.")

    cfg = {
        "sheet_id": sheet_id_sel, "aba_nome": aba_sel,
        "coluna_telefone": col_tel_sw, "coluna_nome": col_nome_sw,
        "linhas_existentes": len(linhas_sheet),
        "modo": "inicio" if modo_sw.startswith("Desde o início") else "novos",
    }
    variaveis_disp = sorted({"nome", "telefone"} | set(cabecalho_sheet))

    leads_iniciais = []
    if cfg["modo"] == "inicio":
        idx_t = cabecalho_sheet.index(col_tel_sw)
        idx_n = cabecalho_sheet.index(col_nome_sw)
        for linha in linhas_sheet:
            lead = {cabecalho_sheet[i]: (linha[i] if i < len(linha) else "") for i in range(len(cabecalho_sheet))}
            lead["telefone"] = linha[idx_t] if idx_t < len(linha) else ""
            lead["nome"] = linha[idx_n] if idx_n < len(linha) else ""
            leads_iniciais.append(lead)

    return cfg, leads_iniciais, variaveis_disp


def _ui_planilha_selecionar(key_prefix: str):
    """
    UI pra escolher uma planilha Google e disparar (uma vez só) pra todo
    mundo que estiver nela agora — sem continuar monitorando (isso é feito
    em Automações → Automação de disparo). Retorna (leads, variaveis_disp).
    """
    from modules import google_sheets
    vazio = ([], ["nome", "telefone"])
    creds_sheet = st.session_state.get("sheets_creds")
    if not creds_sheet:
        st.info("Conecte sua conta Google em ⚙️ Configurações antes de selecionar uma planilha.", icon="ℹ️")
        return vazio
    try:
        planilhas_drive = google_sheets.listar_planilhas(creds_sheet)
    except Exception as e:
        st.error(f"Erro ao listar planilhas: {e}")
        return vazio
    if not planilhas_drive:
        st.caption("Nenhuma planilha encontrada na sua conta Google.")
        return vazio

    sheet_opts = {p["name"]: p["id"] for p in planilhas_drive}
    sheet_sel_nome = st.selectbox("Planilha", list(sheet_opts.keys()), key=f"{key_prefix}_sheet")
    sheet_id_sel = sheet_opts.get(sheet_sel_nome)
    try:
        abas_disp = google_sheets.listar_abas(creds_sheet, sheet_id_sel) if sheet_id_sel else []
    except Exception as e:
        st.error(f"Erro ao listar abas: {e}")
        return vazio
    if not abas_disp:
        return vazio

    aba_sel = st.selectbox("Aba", abas_disp, key=f"{key_prefix}_aba")
    try:
        valores_sheet = google_sheets.ler_valores(creds_sheet, sheet_id_sel, aba_sel)
    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        return vazio
    if not valores_sheet:
        st.caption("A aba está vazia (ou só tem cabeçalho).")
        return vazio

    cabecalho_sheet = [str(c) for c in valores_sheet[0]]
    linhas_sheet = valores_sheet[1:]
    idx_nome_sw = _detectar_col(cabecalho_sheet, _CANDIDATOS_COL_NOME, 0)
    idx_tel_sw = _detectar_col(cabecalho_sheet, _CANDIDATOS_COL_TEL, min(1, len(cabecalho_sheet) - 1))
    scc1, scc2 = st.columns(2)
    with scc1:
        col_nome_sw = st.selectbox("Coluna do nome", cabecalho_sheet, index=idx_nome_sw, key=f"{key_prefix}_col_nome")
    with scc2:
        col_tel_sw = st.selectbox("Coluna do telefone", cabecalho_sheet, index=idx_tel_sw, key=f"{key_prefix}_col_tel")
    st.caption(f"{len(linhas_sheet)} linha(s) na planilha agora — todas serão consideradas (dá pra excluir individualmente na pré-visualização abaixo).")

    idx_t = cabecalho_sheet.index(col_tel_sw)
    idx_n = cabecalho_sheet.index(col_nome_sw)
    leads = []
    for linha in linhas_sheet:
        lead = {cabecalho_sheet[i]: (linha[i] if i < len(linha) else "") for i in range(len(cabecalho_sheet))}
        lead["telefone"] = linha[idx_t] if idx_t < len(linha) else ""
        lead["nome"] = linha[idx_n] if idx_n < len(linha) else ""
        leads.append(lead)
    variaveis_disp = sorted({"nome", "telefone"} | set(cabecalho_sheet))
    return leads, variaveis_disp


def _poll_conexao_disparo(inst_id: str, evolution_name: str, segundos: int = 40) -> bool:
    """Fica checando a conexão ativamente por até `segundos` (a cada 2.5s),
    em vez de depender do usuário clicar em "Verificar conexão" toda hora.
    Retorna True se conectou dentro do prazo."""
    from modules import dispatch_db, evolution_api
    deadline = time.time() + segundos
    while time.time() < deadline:
        try:
            estado, numero = evolution_api.status_e_numero(evolution_name)
        except Exception:
            estado, numero = "", ""
        if estado == "open":
            campos = {"status": "conectado"}
            if numero:
                campos["numero_conectado"] = numero
            dispatch_db.atualizar_instancia(inst_id, **campos)
            return True
        time.sleep(2.5)
    return False


def _tab_disparo_instancias(user_id: str):
    from modules import dispatch_db, evolution_api

    st.markdown("Conecte um número de WhatsApp para usar nas campanhas.")

    _conectando = st.session_state.get("_disparo_conectando")
    if _conectando:
        inst = dispatch_db.obter_instancia(_conectando)
        if inst:
            st.markdown(f"**Pareando: {inst['nome']}**")
            qr_b64 = st.session_state.get("_disparo_qr_b64", "")
            if qr_b64:
                st.image(f"data:image/png;base64,{qr_b64}", width=280, caption="Escaneie com o WhatsApp do número que vai disparar")
            else:
                st.info("QR code não veio na resposta da API — clique em Gerar novo QR.")
            qc1, qc2, qc3 = st.columns(3)
            with qc1:
                if st.button("🔄 Verificar conexão", key="disparo_check_conn", use_container_width=True):
                    try:
                        estado, numero = evolution_api.status_e_numero(inst["evolution_instance_name"])
                        if estado == "open":
                            campos = {"status": "conectado"}
                            if numero:
                                campos["numero_conectado"] = numero
                            dispatch_db.atualizar_instancia(inst["id"], **campos)
                            st.session_state.pop("_disparo_conectando", None)
                            st.session_state.pop("_disparo_qr_b64", None)
                            st.success("Conectado!")
                        else:
                            st.warning(f"Ainda não conectado (estado: {estado}).")
                    except Exception as e:
                        st.error(f"Erro ao verificar: {e}")
                    st.rerun()
            with qc2:
                if st.button("🔁 Gerar novo QR", key="disparo_new_qr", use_container_width=True):
                    try:
                        qr = evolution_api.obter_qrcode(inst["evolution_instance_name"])
                        novo_b64 = (qr.get("base64") or "").split(",")[-1] if qr.get("base64") else ""
                        st.session_state["_disparo_qr_b64"] = novo_b64
                    except Exception as e:
                        st.error(f"Erro ao gerar QR: {e}")
                        st.rerun()
                    with st.spinner("Aguardando leitura do QR code…"):
                        conectou = _poll_conexao_disparo(inst["id"], inst["evolution_instance_name"])
                    if conectou:
                        st.session_state.pop("_disparo_conectando", None)
                        st.session_state.pop("_disparo_qr_b64", None)
                        st.success("Conectado!")
                    st.rerun()
            with qc3:
                if st.button("✖ Cancelar", key="disparo_cancel_conn", use_container_width=True):
                    st.session_state.pop("_disparo_conectando", None)
                    st.session_state.pop("_disparo_qr_b64", None)
                    st.rerun()
            st.markdown('<hr class="hr">', unsafe_allow_html=True)

    canal_novo = st.radio(
        "Tipo de conexão",
        ["WhatsApp não-oficial (QR Code)", "API Oficial (WhatsApp Business)"],
        key="disparo_canal_novo", horizontal=True,
    )

    if canal_novo == "WhatsApp não-oficial (QR Code)":
        with st.expander("➕ Conectar novo número", expanded=not _conectando):
            novo_nome = st.text_input("Nome (só pra identificar internamente)", key="disparo_novo_nome", placeholder="Ex: WhatsApp Comercial")
            if st.button("Criar e mostrar QR", key="disparo_criar_instancia", disabled=not evolution_api.configurado()):
                if not novo_nome.strip():
                    st.warning("Dê um nome pra instância.")
                else:
                    import re as _re, time as _time
                    slug = _re.sub(r"[^a-z0-9]+", "_", novo_nome.strip().lower()).strip("_")
                    evolution_name = f"{slug}_{int(_time.time())}"
                    try:
                        resp = evolution_api.criar_instancia(evolution_name)
                        inst_id = dispatch_db.criar_instancia(user_id, novo_nome.strip(), evolution_name)
                        qr_data = (resp.get("qrcode") or {})
                        b64 = (qr_data.get("base64") or "").split(",")[-1] if qr_data.get("base64") else ""
                        if not b64:
                            # Alguns setups não retornam o QR na criação — busca em seguida
                            try:
                                qr2 = evolution_api.obter_qrcode(evolution_name)
                                b64 = (qr2.get("base64") or "").split(",")[-1] if qr2.get("base64") else ""
                            except Exception:
                                pass
                        st.session_state["_disparo_conectando"] = inst_id
                        st.session_state["_disparo_qr_b64"] = b64
                        with st.spinner("QR gerado. Aguardando leitura…"):
                            conectou = _poll_conexao_disparo(inst_id, evolution_name)
                        if conectou:
                            st.session_state.pop("_disparo_conectando", None)
                            st.session_state.pop("_disparo_qr_b64", None)
                            st.success("Conectado!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao criar instância na Evolution API: {e}")

    else:  # API Oficial
        st.markdown('<div class="sec">API Oficial (WhatsApp Business)</div>', unsafe_allow_html=True)
        st.caption(
            "O canal oficial exige aprovação da Meta e é configurado pela nossa equipe — "
            "você só precisa solicitar a conexão abaixo."
        )
        _solic_usuario = dispatch_db.listar_solicitacoes_oficial_usuario(user_id)
        _solic_pendente = next((s for s in _solic_usuario if s.get("status") != "concluido"), None)
        if _solic_pendente:
            _status_lbl = {"pendente": "aguardando análise", "em_andamento": "em andamento"}.get(
                _solic_pendente["status"], _solic_pendente["status"]
            )
            st.info(f"Você já tem uma solicitação em aberto ({_status_lbl}). Em breve você receberá as instruções.", icon="⏳")
        else:
            _email_of = (st.session_state.get("user", {}) or {}).get("email", "")
            with st.form("form_solicitar_oficial"):
                st.caption(f"Conta: **{_email_of}** — já sabemos quem é você, só falta o número.")
                telefone_contato_of = st.text_input("Número de telefone a conectar", key="of_telefone", placeholder="(11) 99999-9999")
                pedir_of = st.form_submit_button("📨 Solicitar conexão oficial", type="primary", use_container_width=True)
            if pedir_of:
                if not telefone_contato_of.strip():
                    st.warning("Informe o número de telefone.")
                else:
                    req_id = dispatch_db.criar_solicitacao_oficial(
                        user_id, _email_of, telefone_contato_of.strip(),
                    )
                    if req_id:
                        from modules import notificacoes
                        notificacoes.notificar_pedido_conexao_oficial({
                            "tipo": "pedido_conexao_oficial",
                            "request_id": req_id,
                            "user_id": user_id,
                            "email": _email_of,
                            "telefone_contato": telefone_contato_of.strip(),
                        })
                        st.success("Solicitação enviada! Em breve você receberá as instruções pra conectar.")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Não foi possível registrar a solicitação. Tente novamente.")

    st.markdown("### Instâncias conectadas")
    instancias = dispatch_db.listar_instancias(user_id)
    if not instancias:
        st.caption("Nenhuma instância cadastrada ainda.")
        return

    for inst in instancias:
        eh_oficial = inst.get("canal") == "oficial"
        c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
        with c1:
            st.markdown(f"**{inst['nome']}**")
            _canal_lbl = "🟦 Oficial" if eh_oficial else "🟩 Não-oficial"
            _sub = inst.get("numero_conectado") or inst.get("evolution_instance_name", "")
            st.caption(f"{_canal_lbl} · {_sub}" if _sub else _canal_lbl)
        with c2:
            status = inst.get("status", "desconectado")
            badge_cls, badge_lbl = {
                "conectado":    ("b-ok",   "Conectado"),
                "conectando":   ("b-warn", "Conectando"),
                "desconectado": ("b-err",  "Desconectado"),
            }.get(status, ("b-err", status))
            st.markdown(f'<span class="badge {badge_cls}">{badge_lbl}</span>', unsafe_allow_html=True)
        with c3:
            if not eh_oficial and st.button("🔄 Status", key=f"disparo_refresh_{inst['id']}", use_container_width=True):
                try:
                    estado, numero = evolution_api.status_e_numero(inst["evolution_instance_name"])
                    novo_status = "conectado" if estado == "open" else ("conectando" if estado == "connecting" else "desconectado")
                    campos = {"status": novo_status}
                    if numero:
                        campos["numero_conectado"] = numero
                    dispatch_db.atualizar_instancia(inst["id"], **campos)
                except Exception as e:
                    st.error(f"Erro: {e}")
                st.rerun()
        with c4:
            if st.button("🗑️ Remover", key=f"disparo_del_inst_{inst['id']}", use_container_width=True):
                if not eh_oficial:
                    try:
                        evolution_api.excluir_instancia(inst["evolution_instance_name"])
                    except Exception:
                        pass
                dispatch_db.deletar_instancia(inst["id"])
                st.rerun()


def _ui_cadence_step_builder(steps_key: str, key_prefix: str, user_id: str, inst_selecionada: dict, variaveis_disp: list) -> None:
    """
    Construtor de cadência compartilhado entre Disparos → Campanhas e as
    duas telas de Automações — evita a mesma lógica (com o branch canal
    oficial vs. não-oficial) divergindo entre os três lugares. Edita
    st.session_state[steps_key] (lista de dicts) in-place.
    """
    from modules import dispatch_db

    if steps_key not in st.session_state:
        st.session_state[steps_key] = [{"atraso_horas": 0.0, "corpo_mensagem": ""}]

    inst_eh_oficial = (inst_selecionada or {}).get("canal") == "oficial"
    templates_aprovados = []
    if inst_eh_oficial:
        templates_aprovados = [
            t for t in dispatch_db.listar_templates(user_id)
            if t.get("status_aprovacao") == "aprovado" and t.get("instance_id") == inst_selecionada.get("id")
        ]
        if not templates_aprovados:
            st.warning(
                "Essa instância é do canal oficial e não tem nenhum template aprovado ainda — "
                "crie e aguarde a aprovação na aba **Templates** (em Disparos) antes de montar a cadência.",
            )
    else:
        st.caption("Variáveis disponíveis: " + ", ".join(f"{{{{{v}}}}}" for v in variaveis_disp))

    for i, step in enumerate(st.session_state[steps_key]):
        sc1, sc2, sc3 = st.columns([2, 6, 1])
        with sc1:
            step["atraso_horas"] = st.number_input(
                "Atraso (h)" if i == 0 else f"Atraso etapa {i+1} (h)",
                min_value=0.0, value=float(step["atraso_horas"]), step=1.0,
                key=f"{key_prefix}_atraso_{i}",
                help="Horas após a inscrição (etapa 1) ou após a etapa anterior ser enviada.",
            )
        with sc2:
            if inst_eh_oficial:
                if templates_aprovados:
                    _tpl_opts_step = {t["nome"]: t for t in templates_aprovados}
                    _tpl_nome_atual = next(
                        (n for n, t in _tpl_opts_step.items() if t["id"] == step.get("template_id")),
                        list(_tpl_opts_step.keys())[0],
                    )
                    _tpl_sel_step = st.selectbox(
                        "Template" if i == 0 else f"Template etapa {i+1}",
                        list(_tpl_opts_step.keys()),
                        index=list(_tpl_opts_step.keys()).index(_tpl_nome_atual),
                        key=f"{key_prefix}_tpl_{i}",
                    )
                    _tpl_obj_step = _tpl_opts_step[_tpl_sel_step]
                    step["template_id"] = _tpl_obj_step["id"]
                    _cab_step, _corpo_step, _rod_step = _extrair_partes_template(_tpl_obj_step.get("componentes") or [])
                    st.caption(f"Prévia: {_corpo_step}")
                    _n_vars_step = len(_tpl_obj_step.get("variaveis") or [])
                    _params_atuais = step.get("parametros_template") or []
                    _novos_params = []
                    for vi in range(_n_vars_step):
                        _val_atual = _params_atuais[vi] if vi < len(_params_atuais) else ""
                        _novos_params.append(st.text_input(
                            f"Variável {{{{{vi + 1}}}}}", value=_val_atual,
                            key=f"{key_prefix}_tplvar_{i}_{vi}",
                            placeholder="Ex: {{nome}} ou texto fixo",
                        ))
                    step["parametros_template"] = _novos_params
                    step["corpo_mensagem"] = _corpo_step
                else:
                    st.caption("— sem template aprovado —")
            else:
                step["corpo_mensagem"] = st.text_area(
                    "Mensagem" if i == 0 else f"Mensagem etapa {i+1}",
                    value=step["corpo_mensagem"], key=f"{key_prefix}_corpo_{i}", height=80,
                    placeholder="Use {{nome}}, {{telefone}} etc. — veja as variáveis disponíveis acima.",
                )
        with sc3:
            st.markdown("<br>", unsafe_allow_html=True)
            if len(st.session_state[steps_key]) > 1 and st.button("🗑️", key=f"{key_prefix}_del_{i}"):
                st.session_state[steps_key].pop(i)
                st.rerun()

    if st.button("➕ Adicionar etapa à cadência", key=f"{key_prefix}_add_step"):
        st.session_state[steps_key].append({"atraso_horas": 24.0, "corpo_mensagem": ""})
        st.rerun()


def _tab_disparo_campanhas(user_id: str):
    from modules import dispatch_db
    from modules.database import listar_pesquisas, buscar_leads_da_pesquisa

    instancias = dispatch_db.listar_instancias(user_id)
    if not instancias:
        st.info("Conecte uma instância WhatsApp na aba **Instâncias** antes de criar uma campanha.", icon="ℹ️")
        return

    if "_disparo_steps" not in st.session_state:
        st.session_state["_disparo_steps"] = [{"atraso_horas": 0.0, "corpo_mensagem": ""}]

    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.markdown("### Campanhas")
    with col_btn:
        if st.button("+ Nova campanha", type="primary", use_container_width=True, key="btn_nova_campanha"):
            st.session_state["_camp_form_aberto"] = not st.session_state.get("_camp_form_aberto", False)
            st.rerun()

    if st.session_state.get("_camp_form_aberto"):
        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        with st.container(key="form_card_nova_campanha"):
            st.markdown("#### Nova campanha")

            nome_camp = st.text_input("Nome da campanha", key="disparo_camp_nome")
            inst_por_nome = {i["nome"]: i for i in instancias}
            inst_opts = {nome: inst["id"] for nome, inst in inst_por_nome.items()}
            inst_sel = st.selectbox("Instância WhatsApp", list(inst_opts.keys()), key="disparo_camp_inst")
            inst_selecionada = inst_por_nome.get(inst_sel) or {}

            origem = st.radio(
                "Origem dos contatos",
                [
                    "Busca existente (Histórico)", "Upload de planilha",
                    "Digitar números manualmente", "Selecionar planilha Google",
                ],
                key="disparo_camp_origem",
            )

            leads_prontos: list[dict] = []
            origem_search_id = None
            preview_key = "geral"
            variaveis_disp = ["nome", "telefone"]

            if origem == "Busca existente (Histórico)":
                pesquisas = listar_pesquisas()
                if not pesquisas:
                    st.caption("Nenhuma pesquisa salva no Histórico ainda.")
                else:
                    opts = {f"{p['nicho']} · {p['localidade']} ({p['total_results']} leads)": p["id"] for p in pesquisas}
                    sel = st.selectbox("Pesquisa", list(opts.keys()), key="disparo_camp_busca")
                    origem_search_id = opts.get(sel)
                    if origem_search_id:
                        leads_prontos = buscar_leads_da_pesquisa(origem_search_id)
                    preview_key = f"busca_{origem_search_id}"
                    variaveis_disp = [
                        "nome", "telefone", "telefone2", "email", "endereco", "municipio",
                        "uf", "cep", "site", "maps_url", "avaliacao", "total_avaliacoes",
                        "cnpj", "nicho", "subnicho", "fonte",
                    ]

            elif origem == "Upload de planilha":
                arquivo = st.file_uploader("Planilha (CSV ou Excel)", type=["csv", "xlsx"], key="disparo_camp_upload")
                if arquivo is not None:
                    import pandas as pd
                    try:
                        df_up = pd.read_csv(arquivo) if arquivo.name.endswith(".csv") else pd.read_excel(arquivo)
                    except Exception as e:
                        st.error(f"Erro ao ler o arquivo: {e}")
                        df_up = None
                    if df_up is not None and not df_up.empty:
                        cols = list(df_up.columns)
                        idx_nome = _detectar_col(cols, _CANDIDATOS_COL_NOME, 0)
                        idx_tel = _detectar_col(cols, _CANDIDATOS_COL_TEL, min(1, len(cols) - 1))
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            col_nome = st.selectbox("Coluna do nome", cols, index=idx_nome, key="disparo_up_col_nome")
                        with cc2:
                            col_tel = st.selectbox("Coluna do telefone", cols, index=idx_tel, key="disparo_up_col_tel")
                        st.caption(f"{len(df_up)} linhas na planilha. Colunas detectadas automaticamente — confira antes de continuar.")
                        leads_prontos = []
                        for _, r in df_up.iterrows():
                            lead = {str(c): str(r.get(c, "") or "") for c in cols}
                            lead["nome"] = str(r.get(col_nome, "") or "")
                            lead["telefone"] = str(r.get(col_tel, "") or "")
                            leads_prontos.append(lead)
                        variaveis_disp = sorted({"nome", "telefone"} | {str(c) for c in cols})
                        preview_key = f"upload_{arquivo.name}_{arquivo.size}"

            elif origem == "Digitar números manualmente":
                manual_nome = st.text_input(
                    "Nome (opcional, vale pra todos os números abaixo)",
                    key="disparo_camp_manual_nome", placeholder="Ex: Lead",
                )
                manual_txt = st.text_area(
                    "Números — um por linha ou separados por vírgula, sem formatação (ex: 5511999999999)",
                    key="disparo_camp_manual", height=120,
                    placeholder="5511999999999\n5511988888888",
                )
                if manual_txt.strip():
                    import re as _re_manual
                    numeros = [n.strip() for n in _re_manual.split(r"[,;\n]+", manual_txt) if n.strip()]
                    leads_prontos = [{"nome": manual_nome.strip(), "telefone": n} for n in numeros]
                    st.caption(f"{len(leads_prontos)} número(s) detectado(s).")
                    preview_key = f"manual_{len(numeros)}"

            else:  # Selecionar planilha Google
                leads_prontos, variaveis_disp = _ui_planilha_selecionar("disparo_sw")
                if leads_prontos:
                    preview_key = f"sheetsel_{st.session_state.get('disparo_sw_sheet','')}_{st.session_state.get('disparo_sw_aba','')}"

            # ── Pré-visualizar e excluir leads antes de ativar (todas as origens) ──
            if leads_prontos:
                st.markdown('<div class="sec">Pré-visualizar e excluir leads (opcional)</div>', unsafe_allow_html=True)
                if len(leads_prontos) > 2000:
                    st.caption(
                        f"{len(leads_prontos)} leads — lista grande demais pra excluir individualmente aqui "
                        "(limite de 2.000), todos serão inscritos."
                    )
                else:
                    import pandas as pd
                    df_prev = pd.DataFrame([
                        {"Incluir": True, "Nome": l.get("nome", ""), "Telefone": l.get("telefone", "")}
                        for l in leads_prontos
                    ])
                    df_edit = st.data_editor(
                        df_prev,
                        key=f"disparo_preview_{preview_key}",
                        column_config={"Incluir": st.column_config.CheckboxColumn("Incluir", default=True)},
                        disabled=["Nome", "Telefone"],
                        hide_index=True, use_container_width=True,
                        height=min(320, 46 + 35 * len(leads_prontos)),
                    )
                    _excluidos_idx = set(df_edit.index[~df_edit["Incluir"]].tolist())
                    if _excluidos_idx:
                        leads_prontos = [l for i, l in enumerate(leads_prontos) if i not in _excluidos_idx]
                    st.caption(f"{len(leads_prontos)} de {len(df_prev)} serão inscritos.")

            st.markdown('<div class="sec">Ritmo de disparo (intervalo aleatório entre mensagens, anti-banimento)</div>', unsafe_allow_html=True)
            rc1, rc2 = st.columns(2)
            with rc1:
                intervalo_min = st.number_input("Mínimo (segundos)", min_value=5, value=30, step=5, key="disparo_int_min")
            with rc2:
                intervalo_max = st.number_input("Máximo (segundos)", min_value=5, value=90, step=5, key="disparo_int_max")

            st.markdown('<div class="sec">Cadência de mensagens</div>', unsafe_allow_html=True)
            _ui_cadence_step_builder("_disparo_steps", "disparo_step", user_id, inst_selecionada, variaveis_disp)

            st.markdown('<hr class="hr">', unsafe_allow_html=True)
            if st.button("✅ Criar campanha", type="primary", key="disparo_criar_campanha", use_container_width=True):
                steps = st.session_state["_disparo_steps"]
                if not nome_camp.strip():
                    st.warning("Dê um nome pra campanha.")
                elif not steps[0]["corpo_mensagem"].strip():
                    st.warning("Preencha ao menos a mensagem da primeira etapa.")
                elif not all(s["corpo_mensagem"].strip() for s in steps):
                    st.warning("Todas as etapas da cadência precisam ter uma mensagem — preencha ou remova as vazias.")
                elif origem == "Busca existente (Histórico)" and not origem_search_id:
                    st.warning("Selecione uma pesquisa.")
                elif origem == "Upload de planilha" and not leads_prontos:
                    st.warning("Suba uma planilha com nome e telefone.")
                elif origem == "Digitar números manualmente" and not leads_prontos:
                    st.warning("Digite ao menos um número.")
                elif origem == "Selecionar planilha Google" and not leads_prontos:
                    st.warning("Selecione a planilha, a aba e as colunas de telefone.")
                else:
                    tipo_origem = {
                        "Busca existente (Histórico)": "busca_existente",
                        "Upload de planilha": "upload",
                        "Digitar números manualmente": "manual",
                        "Selecionar planilha Google": "planilha_google",
                    }[origem]
                    camp_id = dispatch_db.criar_campanha(
                        user_id=user_id, nome=nome_camp.strip(),
                        instance_id=inst_opts[inst_sel], tipo_origem=tipo_origem,
                        origem_search_id=origem_search_id,
                        intervalo_min_seg=int(intervalo_min), intervalo_max_seg=int(intervalo_max),
                    )
                    if not camp_id:
                        st.error("Erro ao criar a campanha.")
                    else:
                        for i, s in enumerate(steps, start=1):
                            dispatch_db.criar_etapa(
                                camp_id, i, s["atraso_horas"], s["corpo_mensagem"],
                                template_id=s.get("template_id"),
                                parametros_template=s.get("parametros_template"),
                            )

                        if leads_prontos:
                            resultado_enroll = dispatch_db.enroll_targets(camp_id, leads_prontos)
                        else:
                            resultado_enroll = {"inscritos": 0, "invalidos": 0, "duplicados": 0, "opt_out": 0}
                        dispatch_db.atualizar_campanha(camp_id, status="ativa")
                        st.session_state["_disparo_steps"] = [{"atraso_horas": 0.0, "corpo_mensagem": ""}]
                        st.session_state["_camp_form_aberto"] = False
                        msg = f"Campanha criada e ativada com {resultado_enroll['inscritos']} contato(s) inscrito(s)!"
                        _extras = []
                        if resultado_enroll["invalidos"]:
                            _extras.append(f"{resultado_enroll['invalidos']} com telefone inválido")
                        if resultado_enroll["duplicados"]:
                            _extras.append(f"{resultado_enroll['duplicados']} duplicado(s)")
                        if resultado_enroll["opt_out"]:
                            _extras.append(f"{resultado_enroll['opt_out']} em opt-out")
                        if _extras:
                            msg += " (" + ", ".join(_extras) + " ignorado(s))"
                        st.success(msg)
                        time.sleep(0.5)
                        st.rerun()

    campanhas = dispatch_db.listar_campanhas(user_id)
    if not campanhas:
        st.caption("Nenhuma campanha criada ainda.")
        return

    inst_by_id = {i["id"]: i["nome"] for i in instancias}
    for camp in campanhas:
        stats = dispatch_db.stats_campanha(camp["id"])
        origem_lbl = _ORIGEM_CAMPANHA_LBL.get(camp.get("tipo_origem"), "")
        with st.expander(f"{camp['nome']} — {camp.get('status','').upper()} · {inst_by_id.get(camp.get('instance_id'), '—')} · {origem_lbl}"):
            if camp.get("tipo_origem") == "automacao_busca":
                from modules.automation_db import obter_automacao_por_campanha
                _auto_vinc = obter_automacao_por_campanha(camp["id"])
                if _auto_vinc:
                    st.caption(f"🔗 Vinculada à automação de busca: **{_auto_vinc['nome']}**")
            st.markdown(
                f"📇 {stats['total']} inscritos · ⏳ {stats['pendente']} pendentes · "
                f"✅ {stats['concluido']} concluídos · ❌ {stats['falhou']} falharam"
            )
            etapas = dispatch_db.listar_etapas(camp["id"])
            for e in etapas:
                st.caption(f"Etapa {e['ordem']} (+{e['atraso_horas']}h): {e['corpo_mensagem'][:80]}")
            bc1, bc2, bc3 = st.columns(3)
            with bc1:
                if camp.get("status") == "ativa":
                    if st.button("⏸️ Pausar", key=f"disparo_pause_{camp['id']}", use_container_width=True):
                        dispatch_db.atualizar_campanha(camp["id"], status="pausada")
                        st.rerun()
                else:
                    if st.button("▶️ Ativar", key=f"disparo_activate_{camp['id']}", use_container_width=True):
                        dispatch_db.atualizar_campanha(camp["id"], status="ativa")
                        st.rerun()
            with bc3:
                if st.button("🗑️ Excluir", key=f"disparo_del_camp_{camp['id']}", use_container_width=True):
                    dispatch_db.deletar_campanha(camp["id"])
                    st.rerun()


def _tab_disparo_relatorios(user_id: str):
    from modules import dispatch_db

    campanhas = dispatch_db.listar_campanhas(user_id)
    if not campanhas:
        st.caption("Nenhuma campanha ainda.")
        return

    opts = {
        f"{c['nome']} — {_ORIGEM_CAMPANHA_LBL.get(c.get('tipo_origem'), '')} ({c.get('status','').upper()})": c["id"]
        for c in campanhas
    }
    sel = st.selectbox("Campanha", list(opts.keys()), key="disparo_rel_camp")
    camp_id = opts.get(sel)
    if not camp_id:
        return

    _camp_sel = next((c for c in campanhas if c["id"] == camp_id), None)
    if _camp_sel and _camp_sel.get("tipo_origem") == "automacao_busca":
        from modules.automation_db import obter_automacao_por_campanha
        _auto_vinc_rel = obter_automacao_por_campanha(camp_id)
        if _auto_vinc_rel:
            st.caption(f"🔗 Vinculada à automação de busca: **{_auto_vinc_rel['nome']}**")

    stats = dispatch_db.stats_campanha(camp_id)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Inscritos", stats["total"])
    m2.metric("Pendentes", stats["pendente"])
    m3.metric("Concluídos", stats["concluido"])
    m4.metric("Falharam", stats["falhou"])

    targets = dispatch_db.listar_targets_campanha(camp_id)
    if targets:
        import pandas as pd
        df_t = pd.DataFrame(targets)[["nome", "telefone", "status", "proxima_etapa_em", "atualizado_em"]].copy()
        for _col in ("proxima_etapa_em", "atualizado_em"):
            df_t[_col] = pd.to_datetime(df_t[_col], errors="coerce", utc=True) \
                .dt.tz_convert("America/Sao_Paulo").dt.strftime("%d/%m/%Y %H:%M").fillna("—")
        df_t = df_t.rename(columns={
            "nome": "Nome", "telefone": "Telefone", "status": "Status",
            "proxima_etapa_em": "Próxima etapa", "atualizado_em": "Atualizado em",
        })
        st.dataframe(df_t, use_container_width=True, height=320)


def _tab_disparo_templates(user_id: str):
    from modules import dispatch_db, whatsapp_oficial

    instancias_oficiais = [i for i in dispatch_db.listar_instancias(user_id) if i.get("canal") == "oficial"]
    if not instancias_oficiais:
        st.info("Conecte uma instância do canal oficial (aba Instâncias) pra gerenciar templates.", icon="ℹ️")
        return

    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.caption("Templates precisam ser aprovados pela Meta antes de entrar numa campanha do canal oficial.")
    with col_btn:
        if st.button("+ Novo template", type="primary", use_container_width=True, key="btn_novo_template"):
            st.session_state["_tpl_form_aberto"] = not st.session_state.get("_tpl_form_aberto", False)
            st.rerun()

    if st.session_state.get("_tpl_form_aberto"):
        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        with st.container(key="form_card_novo_template"):
            st.markdown("#### Novo template")
            _inst_opts_tpl = {i["nome"]: i["id"] for i in instancias_oficiais}
            inst_sel_tpl = st.selectbox("Instância oficial", list(_inst_opts_tpl.keys()), key="tpl_inst")
            inst_id_tpl = _inst_opts_tpl.get(inst_sel_tpl)

            nome_tpl = st.text_input("Nome interno", key="tpl_nome", placeholder="Ex: Confirmação de agendamento")
            nc1, nc2, nc3 = st.columns(3)
            with nc1:
                nome_meta_tpl = st.text_input(
                    "Nome técnico (Meta)", key="tpl_nome_meta", placeholder="confirmacao_agendamento",
                    help="Minúsculo, só letras/números/underscore — como a Meta identifica o template.",
                )
            with nc2:
                categoria_tpl = st.selectbox("Categoria", ["UTILITY", "MARKETING", "AUTHENTICATION"], key="tpl_categoria")
            with nc3:
                idioma_tpl = st.selectbox("Idioma", ["pt_BR", "en_US", "es_ES"], key="tpl_idioma")
            cabecalho_tpl = st.text_input("Cabeçalho (opcional)", key="tpl_cabecalho")
            corpo_tpl = st.text_area(
                "Corpo *", key="tpl_corpo", height=120,
                placeholder="Olá {{1}}, seu pedido {{2}} foi confirmado!",
                help="Use {{1}}, {{2}}... pras variáveis — na hora de disparar, cada uma é mapeada pra um campo do lead.",
            )
            rodape_tpl = st.text_input("Rodapé (opcional)", key="tpl_rodape")

            st.markdown('<hr class="hr">', unsafe_allow_html=True)
            bc1, bc2 = st.columns(2)
            with bc1:
                salvar_rascunho = st.button("💾 Salvar rascunho", key="tpl_salvar_rascunho", use_container_width=True)
            with bc2:
                enviar_aprovacao = st.button("📤 Salvar e enviar pra aprovação", type="primary", key="tpl_enviar", use_container_width=True)

            if salvar_rascunho or enviar_aprovacao:
                import re as _re_tpl
                _nome_meta_norm = _re_tpl.sub(r"[^a-z0-9_]+", "_", nome_meta_tpl.strip().lower()).strip("_")
                if not nome_tpl.strip():
                    st.warning("Dê um nome interno pro template.")
                elif not corpo_tpl.strip():
                    st.warning("Preencha o corpo da mensagem.")
                elif enviar_aprovacao and not _nome_meta_norm:
                    st.warning("Preencha o nome técnico (Meta) pra enviar pra aprovação.")
                else:
                    _numeros_var = sorted(set(int(n) for n in _re_tpl.findall(r"\{\{(\d+)\}\}", corpo_tpl)))
                    tpl_id = dispatch_db.criar_template(
                        user_id=user_id, instance_id=inst_id_tpl, nome=nome_tpl.strip(),
                        categoria=categoria_tpl, corpo=corpo_tpl.strip(), nome_meta=_nome_meta_norm,
                        idioma=idioma_tpl, cabecalho=cabecalho_tpl.strip(), rodape=rodape_tpl.strip(),
                        variaveis=[f"var{n}" for n in _numeros_var],
                    )
                    if not tpl_id:
                        st.error("Erro ao salvar o template.")
                    elif salvar_rascunho:
                        st.success(f"Template **{nome_tpl}** salvo como rascunho.")
                        st.session_state["_tpl_form_aberto"] = False
                        time.sleep(0.4)
                        st.rerun()
                    else:  # enviar_aprovacao
                        inst_tpl = dispatch_db.obter_instancia(inst_id_tpl)
                        try:
                            resp_meta = whatsapp_oficial.criar_template(
                                token=inst_tpl["token_oficial"], waba_id=inst_tpl.get("waba_id") or "",
                                nome_meta=_nome_meta_norm, categoria=categoria_tpl, idioma=idioma_tpl,
                                corpo=corpo_tpl.strip(), cabecalho=cabecalho_tpl.strip(), rodape=rodape_tpl.strip(),
                            )
                            dispatch_db.atualizar_template(tpl_id, status_aprovacao="pendente", meta_template_id=resp_meta.get("id", ""))
                            st.success("Template salvo e enviado pra aprovação da Meta! Status: pendente.")
                            st.session_state["_tpl_form_aberto"] = False
                            time.sleep(0.4)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Template salvo como rascunho, mas o envio pra Meta falhou: {e}")

    st.markdown("### Seus templates")
    templates = dispatch_db.listar_templates(user_id)
    if not templates:
        st.caption("Nenhum template criado ainda.")
        return

    for tpl in templates:
        status = tpl.get("status_aprovacao", "rascunho")
        badge_cls, badge_lbl = _STATUS_TEMPLATE_LBL.get(status, ("b-err", status))
        with st.expander(f"{tpl['nome']} — {badge_lbl}"):
            st.markdown(f'<span class="badge {badge_cls}">{badge_lbl}</span>', unsafe_allow_html=True)
            st.caption(
                f"Categoria: {tpl.get('categoria','—')} · Idioma: {tpl.get('idioma','—')} · "
                f"Nome técnico: `{tpl.get('nome_meta') or '—'}`"
            )
            _cab_tpl, _corpo_tpl, _rod_tpl = _extrair_partes_template(tpl.get("componentes") or [])
            if _cab_tpl:
                st.caption(f"**Cabeçalho:** {_cab_tpl}")
            st.text(_corpo_tpl or tpl.get("corpo", ""))
            if _rod_tpl:
                st.caption(f"**Rodapé:** {_rod_tpl}")

            bc1, bc2, bc3 = st.columns(3)
            with bc1:
                if tpl.get("meta_template_id"):
                    if st.button("🔄 Atualizar status", key=f"tpl_refresh_{tpl['id']}", use_container_width=True):
                        inst_tpl2 = dispatch_db.obter_instancia(tpl["instance_id"]) if tpl.get("instance_id") else None
                        if not inst_tpl2:
                            st.error("Instância vinculada não encontrada.")
                        else:
                            try:
                                resp_status = whatsapp_oficial.obter_template(inst_tpl2["token_oficial"], tpl["meta_template_id"])
                                novo_status_meta = resp_status.get("status", "")
                                _map_status = {"APPROVED": "aprovado", "PENDING": "pendente", "REJECTED": "rejeitado"}
                                dispatch_db.atualizar_template(
                                    tpl["id"], status_aprovacao=_map_status.get(novo_status_meta, status),
                                )
                                st.success(f"Status atualizado: {novo_status_meta}")
                            except Exception as e:
                                st.error(f"Erro ao consultar status: {e}")
                            st.rerun()
                elif st.button("📤 Enviar pra aprovação", key=f"tpl_send_{tpl['id']}", use_container_width=True):
                    inst_tpl3 = dispatch_db.obter_instancia(tpl["instance_id"]) if tpl.get("instance_id") else None
                    if not inst_tpl3:
                        st.error("Instância vinculada não encontrada.")
                    elif not tpl.get("nome_meta"):
                        st.error("Esse template não tem nome técnico — exclua e crie de novo preenchendo esse campo.")
                    else:
                        try:
                            resp_meta2 = whatsapp_oficial.criar_template(
                                token=inst_tpl3["token_oficial"], waba_id=inst_tpl3.get("waba_id") or "",
                                nome_meta=tpl["nome_meta"], categoria=tpl.get("categoria", "UTILITY"),
                                idioma=tpl.get("idioma", "pt_BR"), corpo=_corpo_tpl, cabecalho=_cab_tpl, rodape=_rod_tpl,
                            )
                            dispatch_db.atualizar_template(
                                tpl["id"], status_aprovacao="pendente", meta_template_id=resp_meta2.get("id", ""),
                            )
                            st.success("Enviado pra aprovação!")
                        except Exception as e:
                            st.error(f"Erro ao enviar: {e}")
                        st.rerun()
            with bc3:
                if st.button("🗑️ Excluir", key=f"tpl_del_{tpl['id']}", use_container_width=True):
                    dispatch_db.deletar_template(tpl["id"])
                    st.rerun()


def _tab_disparo_pedidos_oficial():
    from modules import dispatch_db

    st.markdown(
        "Painel do admin pra provisionar o canal oficial de cada cliente — token, "
        "**Phone Number ID** e **WABA ID** vêm do seu painel DatafyAPI."
    )

    solicitacoes = dispatch_db.listar_solicitacoes_oficial()
    pendentes = [s for s in solicitacoes if s.get("status") != "concluido"]
    concluidas = [s for s in solicitacoes if s.get("status") == "concluido"]

    st.markdown(f"### Pendentes ({len(pendentes)})")
    if not pendentes:
        st.caption("Nenhuma solicitação pendente.")
    for s in pendentes:
        sid = s["id"]
        titulo = f"{s.get('nome_desejado') or 'Cliente sem e-mail'} — {s.get('telefone_contato') or '—'} · {s.get('status','').upper()}"
        with st.expander(titulo):
            st.caption(f"Solicitado em {(s.get('criado_em') or '')[:16].replace('T',' ')} · user_id: `{s['user_id']}`")

            with st.form(f"form_provisionar_{sid}"):
                nome_inst_of = st.text_input(
                    "Nome da instância", value=f"WhatsApp Oficial — {s.get('telefone_contato') or ''}".strip(" —"),
                    key=f"prov_nome_{sid}",
                )
                token_of = st.text_input("Token (DatafyAPI)", key=f"prov_token_{sid}", type="password")
                fc1, fc2 = st.columns(2)
                with fc1:
                    phone_id_of = st.text_input("Phone Number ID", key=f"prov_phone_{sid}")
                with fc2:
                    waba_id_of = st.text_input("WABA ID", key=f"prov_waba_{sid}")
                numero_of = st.text_input("Número conectado (opcional, só exibição)", key=f"prov_numero_{sid}", placeholder="(11) 99999-9999")
                provisionar = st.form_submit_button("✅ Provisionar e concluir", type="primary", use_container_width=True)

            if provisionar:
                if not token_of.strip() or not phone_id_of.strip():
                    st.warning("Preencha ao menos o token e o Phone Number ID.")
                else:
                    inst_id = dispatch_db.criar_instancia_oficial(
                        s["user_id"], nome_inst_of.strip(), token_of.strip(),
                        phone_id_of.strip(), waba_id_of.strip(), numero_of.strip(),
                    )
                    if inst_id:
                        dispatch_db.atualizar_solicitacao_oficial(sid, status="concluido", instance_id=inst_id)
                        st.success("Canal oficial provisionado!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Erro ao criar a instância.")

            bc1, bc2 = st.columns(2)
            with bc1:
                if s.get("status") == "pendente" and st.button("🔧 Marcar em andamento", key=f"prov_andamento_{sid}", use_container_width=True):
                    dispatch_db.atualizar_solicitacao_oficial(sid, status="em_andamento")
                    st.rerun()
            with bc2:
                if st.button("🗑️ Descartar pedido", key=f"prov_del_{sid}", use_container_width=True):
                    dispatch_db.deletar_solicitacao_oficial(sid)
                    st.rerun()

    if concluidas:
        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        st.markdown(f"### Concluídas ({len(concluidas)})")
        for s in concluidas:
            st.caption(f"✅ {s.get('nome_desejado') or 'Sem nome'} — {s.get('telefone_contato') or '—'} (user_id: `{s['user_id']}`)")


def pagina_disparo():
    from modules import evolution_api
    from modules.auth import eh_admin

    user_id = st.session_state.get("user", {}).get("id")
    _admin_disparo = eh_admin()

    st.markdown(
        '<div class="page-header">'
        '<div class="page-header-icon"><svg viewBox="0 0 24 24" stroke="#00D97E" fill="none" stroke-width="1.8"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg></div>'
        '<div><div class="page-title">Disparos</div>'
        '<div class="page-sub">Campanhas de WhatsApp — conecte um número (não-oficial ou API oficial), monte a cadência e dispare</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if not evolution_api.configurado():
        st.warning(
            "Evolution API (canal não-oficial) não configurada. Adicione **EVOLUTION_API_URL** e "
            "**EVOLUTION_API_KEY** nas Secrets do Streamlit / variáveis de ambiente — não afeta o canal oficial.",
            icon="⚠️",
        )

    _nomes_abas = ["📱 Instâncias", "📣 Campanhas", "📝 Templates", "📊 Relatórios"]
    if _admin_disparo:
        _nomes_abas.append("🔧 Pedidos (Oficial)")
    _abas = st.tabs(_nomes_abas)
    with _abas[0]:
        _tab_disparo_instancias(user_id)
    with _abas[1]:
        _tab_disparo_campanhas(user_id)
    with _abas[2]:
        _tab_disparo_templates(user_id)
    with _abas[3]:
        _tab_disparo_relatorios(user_id)
    if _admin_disparo:
        with _abas[4]:
            _tab_disparo_pedidos_oficial()


# ── Sidebar & roteamento principal ────────────────────────────────────────────

_NAV_ICONS = {
    "busca":         '<svg viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.8"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    "historico":     '<svg viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.8"><path d="M3 3v5h5"/><path d="M3.05 13A9 9 0 1 0 6 5.3L3 8"/><path d="M12 7v5l4 2"/></svg>',
    "automacoes":    '<svg viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "configuracoes": '<svg viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    "admin":         '<svg viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.8"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "disparo":       '<svg viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.8"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>',
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
        ]
        if eh_admin() or st.session_state.get("disparo_habilitado"):
            nav_items.append(("disparo", "Disparos"))
        nav_items.append(("configuracoes", "Configurações"))
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
    from modules.auth import usuario_logado, eh_admin, supabase_configurado, restaurar_sessao, sessao_teste_expirada, logout
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

    # Conta de teste expirada — checa a cada render, não só no login, pra
    # bloquear mesmo quem já estava com a aba aberta quando o prazo bateu.
    if sessao_teste_expirada():
        _exp_txt = str(st.session_state.get("teste_expira_em") or "")[:10]
        logout()
        st.error(f"Sua conta de teste expirou em {_exp_txt}. Fale com o administrador pra renovar.", icon="🧪")
        time.sleep(2)
        st.rerun()

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

    # Scheduler de disparo WhatsApp — idem, singleton separado
    try:
        from modules.dispatch_scheduler import ensure_started as _dispatch_sched_start
        _dispatch_sched_start()
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
    elif page == "disparo":
        if eh_admin() or st.session_state.get("disparo_habilitado"):
            pagina_disparo()
        else:
            st.error("Acesso não autorizado.")
    else:
        pagina_busca()


if __name__ == "__main__" or True:
    main()
