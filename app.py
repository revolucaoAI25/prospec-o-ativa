"""
Prospec-o-Ativa — Interface Web
Revolução AI · Prospecção ativa em qualquer nicho
"""

import os
import io
import csv
import time
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Secrets ──────────────────────────────────────────────────────────────────
def _s(key: str, default: str = "") -> str:
    try:
        v = st.secrets.get(key, "")
        if v:
            return str(v).strip()
    except Exception:
        pass
    return os.getenv(key, default).strip()

# ── Page config (deve vir antes de qualquer st.*) ─────────────────────────────
st.set_page_config(
    page_title="Prospec-o-Ativa · Revolução AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Google OAuth: detecta callback na URL ────────────────────────────────────
_code = st.query_params.get("code", "")
if _code and "sheets_creds" not in st.session_state:
    client_id     = _s("GOOGLE_CLIENT_ID")
    client_secret = _s("GOOGLE_CLIENT_SECRET")
    redirect_uri  = _s("APP_URL", "http://localhost:8501")
    if client_id and client_secret:
        try:
            from modules.google_sheets import trocar_codigo
            st.session_state["sheets_creds"] = trocar_codigo(
                client_id, client_secret, redirect_uri, _code
            )
        except Exception as e:
            st.session_state["oauth_error"] = str(e)
    st.query_params.clear()
    st.rerun()

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Fonte e base ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Header da marca ── */
.brand-header {
    background: linear-gradient(135deg, #0D1F15 0%, #0A0A0F 60%, #061A10 100%);
    border-bottom: 1px solid #00D97E30;
    padding: 18px 32px 14px;
    margin: -1rem -1rem 1.5rem -1rem;
    display: flex;
    align-items: center;
    gap: 14px;
}
.brand-dot {
    width: 36px; height: 36px;
    background: #00D97E;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; font-weight: 700; color: #0A0A0F;
    flex-shrink: 0;
}
.brand-title { font-size: 1.25rem; font-weight: 700; color: #F0F0F5; line-height: 1.2; }
.brand-sub   { font-size: 0.75rem; color: #00D97E; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; }

/* ── Cards de estatística ── */
.stat-card {
    background: #141418;
    border: 1px solid #1E1E28;
    border-radius: 12px;
    padding: 18px 20px;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.stat-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #00D97E, #00A85E);
}
.stat-num   { font-size: 2.2rem; font-weight: 700; color: #00D97E; line-height: 1; }
.stat-label { font-size: 0.78rem; color: #8888A0; margin-top: 6px; text-transform: uppercase; letter-spacing: 0.06em; }

/* ── Badges ── */
.badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 10px; border-radius: 20px;
    font-size: 0.78rem; font-weight: 500;
}
.badge-ok   { background: #052e16; color: #00D97E; border: 1px solid #00D97E40; }
.badge-warn { background: #2d1b00; color: #FFB800; border: 1px solid #FFB80040; }
.badge-err  { background: #2d0a0a; color: #FF4757; border: 1px solid #FF475740; }

/* ── Seções ── */
.section-title {
    font-size: 0.7rem; font-weight: 600; color: #00D97E;
    text-transform: uppercase; letter-spacing: 0.12em;
    margin: 1.2rem 0 0.5rem;
}
.divider { border: none; border-top: 1px solid #1E1E28; margin: 1rem 0; }

/* ── Formulários ── */
div[data-testid="stForm"] {
    background: #141418;
    border: 1px solid #1E1E28;
    border-radius: 14px;
    padding: 24px;
}

/* ── Tabelas ── */
div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

/* ── Abas ── */
div[data-testid="stTabs"] button[role="tab"] {
    font-weight: 500; font-size: 0.88rem;
}

/* ── Info box ── */
.info-box {
    background: #0D1F15;
    border: 1px solid #00D97E30;
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 0.85rem;
    color: #A0C8B0;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ── Helpers de export ─────────────────────────────────────────────────────────
from modules.google_sheets import COLUNAS_EXPORT

_EXTRA = [
    ("telefone_internacional", "Telefone Intl."),
    ("status_funcionamento",   "Status"),
    ("porte",                  "Porte"),
    ("data_abertura",          "Data Abertura"),
]
TODAS_COLUNAS = COLUNAS_EXPORT + [c for c in _EXTRA if c not in COLUNAS_EXPORT]


def _csv_bytes(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([lbl for _, lbl in TODAS_COLUNAS])
    for r in rows:
        w.writerow([r.get(col, "") for col, _ in TODAS_COLUNAS])
    return buf.getvalue().encode("utf-8-sig")


def _xlsx_bytes(rows):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Prospecção"
    hf = Font(bold=True, color="0A0A0F")
    hfill = PatternFill("solid", fgColor="00D97E")
    for ci, (_, lbl) in enumerate(TODAS_COLUNAS, 1):
        c = ws.cell(row=1, column=ci, value=lbl)
        c.font, c.fill = hf, hfill
        c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 22
    fill_a = PatternFill("solid", fgColor="141418")
    fill_b = PatternFill("solid", fgColor="0A0A0F")
    for ri, r in enumerate(rows, 2):
        for ci, (col, _) in enumerate(TODAS_COLUNAS, 1):
            cell = ws.cell(row=ri, column=ci, value=r.get(col, ""))
            cell.fill = fill_a if ri % 2 == 0 else fill_b
            if col in ("site", "maps_url") and r.get(col):
                cell.hyperlink = r[col]
                cell.font = Font(color="00D97E", underline="single")
    for ci in range(1, len(TODAS_COLUNAS) + 1):
        mx = max(len(str(ws.cell(row=rr, column=ci).value or "")) for rr in range(1, len(rows) + 2))
        ws.column_dimensions[get_column_letter(ci)].width = min(mx + 2, 50)
    ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _stats(rows):
    total  = len(rows)
    tel    = sum(1 for r in rows if r.get("telefone") or r.get("telefone2"))
    site   = sum(1 for r in rows if r.get("site"))
    email  = sum(1 for r in rows if r.get("email"))
    cols   = st.columns(4)
    for col, num, lbl in [(cols[0], total, "Total"), (cols[1], tel, "Com telefone"),
                          (cols[2], site, "Com site"), (cols[3], email, "Com e-mail")]:
        col.markdown(
            f'<div class="stat-card"><div class="stat-num">{num}</div>'
            f'<div class="stat-label">{lbl}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown("")


def _tabela(rows):
    import pandas as pd
    vis = ["nome","telefone","email","municipio","uf","endereco","site",
           "avaliacao","cnpj","nicho_busca","subnicho_busca","fonte"]
    lmap = {col: lbl for col, lbl in TODAS_COLUNAS}
    df = pd.DataFrame(rows)[[c for c in vis if c in pd.DataFrame(rows).columns]]
    st.dataframe(df.rename(columns=lmap).fillna("").astype(str).replace("nan",""),
                 use_container_width=True, height=400)


def _botoes_download(rows, prefix, sheets_auth):
    ts = int(time.time())
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("⬇️ Excel (.xlsx)", _xlsx_bytes(rows),
                           f"{prefix}_{ts}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    with c2:
        st.download_button("⬇️ CSV", _csv_bytes(rows), f"{prefix}_{ts}.csv",
                           "text/csv", use_container_width=True)
    with c3:
        if sheets_auth:
            if st.button("📊 Google Sheets", use_container_width=True, type="secondary"):
                _export_sheets(rows)
        else:
            st.button("📊 Google Sheets", use_container_width=True,
                      disabled=True, help="Conecte sua conta Google na sidebar.")


def _export_sheets(rows):
    from modules.google_sheets import exportar, extrair_sheet_id
    creds     = st.session_state.get("sheets_creds")
    sheet_id  = st.session_state.get("sheets_selected_id", "")
    aba       = st.session_state.get("sheets_aba", "Prospecção")
    modo      = st.session_state.get("sheets_modo", "substituir")
    if not creds or not sheet_id:
        st.warning("Escolha uma planilha na sidebar antes de exportar.")
        return
    with st.spinner("Exportando para Google Sheets..."):
        ok, msg = exportar(rows, creds, sheet_id, aba, modo)
    (st.success if ok else st.error)(msg)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 8px">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
            <div style="width:32px;height:32px;background:#00D97E;border-radius:8px;
                        display:flex;align-items:center;justify-content:center;
                        font-weight:700;color:#0A0A0F;font-size:16px">R</div>
            <div>
                <div style="font-weight:700;font-size:1rem;color:#F0F0F5">Prospec-o-Ativa</div>
                <div style="font-size:0.7rem;color:#00D97E;letter-spacing:.08em;text-transform:uppercase">Revolução AI</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Status integrações
    gmaps_ok  = bool(_s("GOOGLE_MAPS_API_KEY"))
    oauth_cid = _s("GOOGLE_CLIENT_ID")
    oauth_cs  = _s("GOOGLE_CLIENT_SECRET")
    oauth_configured = bool(oauth_cid and oauth_cs)
    sheets_auth = "sheets_creds" in st.session_state

    st.markdown('<div class="section-title">Integrações</div>', unsafe_allow_html=True)
    st.markdown(
        f'<span class="badge {"badge-ok" if gmaps_ok else "badge-err"}">{"✓" if gmaps_ok else "✗"} Google Maps</span>',
        unsafe_allow_html=True)
    st.markdown("")
    if sheets_auth:
        st.markdown('<span class="badge badge-ok">✓ Google Sheets conectado</span>', unsafe_allow_html=True)
        if st.button("↩ Desconectar", use_container_width=True):
            for k in ["sheets_creds","sheets_selected_id","sheets_selected_name","sheets_abas"]:
                st.session_state.pop(k, None)
            st.rerun()
    elif oauth_configured:
        st.markdown('<span class="badge badge-warn">○ Google Sheets</span>', unsafe_allow_html=True)
        redirect = _s("APP_URL", "http://localhost:8501")
        from modules.google_sheets import gerar_url_auth
        auth_url = gerar_url_auth(oauth_cid, oauth_cs, redirect)
        st.link_button("🔗 Conectar com Google", auth_url, use_container_width=True)
    else:
        st.markdown('<span class="badge badge-warn">○ Google Sheets (opcional)</span>', unsafe_allow_html=True)

    st.markdown("")
    st.markdown('<span class="badge badge-ok">✓ Receita Federal</span>', unsafe_allow_html=True)

    # Erro de OAuth
    if "oauth_error" in st.session_state:
        st.error(f"Erro ao autenticar: {st.session_state.pop('oauth_error')}")

    # Configuração do Google Sheets após autenticado
    if sheets_auth:
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Google Sheets</div>', unsafe_allow_html=True)

        if "sheets_selected_id" not in st.session_state:
            if st.button("🔄 Carregar minhas planilhas", use_container_width=True):
                with st.spinner("Carregando..."):
                    try:
                        from modules.google_sheets import listar_planilhas
                        planilhas = listar_planilhas(st.session_state["sheets_creds"])
                        st.session_state["sheets_lista"] = planilhas
                    except Exception as e:
                        st.error(f"Erro: {e}")

        if st.session_state.get("sheets_lista"):
            planilhas = st.session_state["sheets_lista"]
            nomes = [p["name"] for p in planilhas]
            idx = st.selectbox("Planilha", range(len(nomes)), format_func=lambda i: nomes[i])
            planilha_sel = planilhas[idx]

            if st.button("✓ Usar esta planilha", use_container_width=True, type="primary"):
                st.session_state["sheets_selected_id"]   = planilha_sel["id"]
                st.session_state["sheets_selected_name"] = planilha_sel["name"]
                try:
                    from modules.google_sheets import listar_abas
                    st.session_state["sheets_abas"] = listar_abas(
                        st.session_state["sheets_creds"], planilha_sel["id"]
                    )
                except Exception:
                    st.session_state["sheets_abas"] = ["Prospecção"]
                st.rerun()

        if st.session_state.get("sheets_selected_id"):
            nome_planilha = st.session_state.get("sheets_selected_name", "")
            st.success(f"📄 {nome_planilha}")
            abas_disp = st.session_state.get("sheets_abas", ["Prospecção"])
            aba_sel = st.selectbox("Aba", abas_disp + ["+ Nova aba"])
            if aba_sel == "+ Nova aba":
                aba_sel = st.text_input("Nome da nova aba", value="Prospecção")
            st.session_state["sheets_aba"] = aba_sel
            st.session_state["sheets_modo"] = st.radio(
                "Ao exportar",
                ["substituir", "acrescentar"],
                format_func=lambda x: "🔄 Substituir tudo" if x == "substituir" else "➕ Acrescentar",
                horizontal=True,
            )
            if st.button("🔄 Trocar planilha", use_container_width=True):
                for k in ["sheets_selected_id","sheets_selected_name","sheets_abas"]:
                    st.session_state.pop(k, None)
                st.rerun()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    with st.expander("⚙️ Como configurar?"):
        st.markdown("""
**Google Maps API:**
1. [console.cloud.google.com](https://console.cloud.google.com/)
2. Ative **Places API**
3. Credenciais → Criar Chave de API
4. Secrets: `GOOGLE_MAPS_API_KEY`

**Google Sheets (OAuth):**
1. Mesmo projeto → Credenciais
2. Criar → **ID cliente OAuth 2.0** → Aplicativo da Web
3. Adicione a URL do app em *Origens JS* e *URIs de redirecionamento*
4. Secrets:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `APP_URL` = URL do seu app
""")


# ── Header principal ──────────────────────────────────────────────────────────
st.markdown("""
<div class="brand-header">
    <div class="brand-dot">R</div>
    <div>
        <div class="brand-title">Prospec-o-Ativa</div>
        <div class="brand-sub">Revolução AI · Prospecção ativa em qualquer nicho</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Abas ──────────────────────────────────────────────────────────────────────
from modules.nichos import NICHOS, ESTADOS, NOMES_NICHOS, SIGLAS_ESTADOS

aba_maps, aba_rf = st.tabs([
    "🗺️  Google Maps  ·  com telefone",
    "📋  Receita Federal  ·  dados oficiais",
])


# ══════════════════════════════════════════════════════════════════════════════
# ABA 1 — Google Maps
# ══════════════════════════════════════════════════════════════════════════════
with aba_maps:
    if not gmaps_ok:
        st.warning("Chave do Google Maps não configurada. Veja as instruções na sidebar.", icon="⚠️")

    st.markdown(
        '<div class="info-box">Busca direto no Google Maps. '
        'Melhor fonte para <strong>telefones</strong>. '
        'Até ~500 resultados com múltiplas buscas automáticas.</div>',
        unsafe_allow_html=True,
    )

    # ── Nicho + Subnicho (fora do form para ser dinâmico) ─────────────────────
    col_n, col_s = st.columns(2)

    with col_n:
        st.markdown('<div class="section-title">Nicho *</div>', unsafe_allow_html=True)
        nicho_sel = st.selectbox("Nicho", NOMES_NICHOS, label_visibility="collapsed",
                                 key="maps_nicho")

    nicho_data    = NICHOS[nicho_sel]
    is_custom     = nicho_sel == "Outro / Personalizado"

    with col_s:
        st.markdown('<div class="section-title">Subnicho / Especialidade</div>', unsafe_allow_html=True)
        if is_custom:
            query_custom  = st.text_input("Termo de busca", placeholder='Ex: "pet shop", "clínica veterinária"',
                                          label_visibility="collapsed", key="maps_query_custom")
            subnicho_sel  = ""
        else:
            opcoes_sub = ["Todos (sem filtro)"] + nicho_data["subnichos"] + ["✏️ Personalizado..."]
            subnicho_sel = st.selectbox("Subnicho", opcoes_sub, label_visibility="collapsed",
                                        key="maps_subnicho")

    subnicho_custom = ""
    if not is_custom and subnicho_sel == "✏️ Personalizado...":
        subnicho_custom = st.text_input(
            "Especialidade personalizada",
            placeholder="Digite a especialidade desejada",
            key="maps_subnicho_custom",
        )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Localidade + limite (no form para agrupar) ───────────────────────────
    with st.form("form_maps"):
        st.markdown('<div class="section-title">Localidade — preencha cidade e/ou estado</div>',
                    unsafe_allow_html=True)
        col_c, col_e, col_l = st.columns([3, 1, 2])

        with col_c:
            cidade = st.text_input("Cidade", placeholder="Ex: São Paulo",
                                   label_visibility="collapsed", key="maps_cidade")
        with col_e:
            estado_opts = ["—"] + SIGLAS_ESTADOS
            est_default = estado_opts.index("SP") if "SP" in estado_opts else 0
            estado_raw  = st.selectbox("Estado", estado_opts, index=est_default,
                                       label_visibility="collapsed", key="maps_estado")
            estado = "" if estado_raw == "—" else estado_raw

        with col_l:
            limite = st.slider("Resultados", 20, 500, 60, 20,
                               label_visibility="collapsed", key="maps_limite")
            st.caption(f"Máx. **{limite}** resultados")

        buscar_btn = st.form_submit_button(
            "🔍 Buscar no Google Maps",
            disabled=not gmaps_ok,
            use_container_width=True,
            type="primary",
        )

    # ── Execução ──────────────────────────────────────────────────────────────
    if buscar_btn:
        cv, ev = cidade.strip(), estado.strip()
        if not cv and not ev:
            st.error("Informe ao menos a cidade ou o estado.")
        elif is_custom and not query_custom.strip():
            st.error("Informe o termo de busca personalizado.")
        else:
            from modules.google_maps import buscar as maps_buscar

            if is_custom:
                qbase, nicho_lbl = query_custom.strip(), query_custom.strip()
                sub_final = ""
            else:
                qbase, nicho_lbl = nicho_data["query"], nicho_sel
                if subnicho_sel == "✏️ Personalizado...":
                    sub_final = subnicho_custom.strip()
                elif subnicho_sel == "Todos (sem filtro)":
                    sub_final = ""
                else:
                    sub_final = subnicho_sel

            if cv and ev:
                localidade = f"{cv}, {ESTADOS.get(ev, ev)}"
            elif cv:
                localidade = cv
            else:
                localidade = ESTADOS.get(ev, ev)

            slug = f"{nicho_lbl[:15]}_{localidade[:15]}".lower().replace(" ","_").replace(",","")

            prog = st.progress(0, text="Iniciando...")
            cap  = st.empty()

            def _cb(a, t, m):
                cap.caption(m)
                if t and t > 0:
                    prog.progress(min(a / t, 1.0), text=m)

            try:
                res = maps_buscar(
                    query_base=qbase, localidade=localidade, limite=limite,
                    api_key=_s("GOOGLE_MAPS_API_KEY"),
                    nicho=nicho_lbl, subnicho=sub_final,
                    cidade=cv, estado=ev,
                    progress_callback=_cb,
                )
                prog.progress(1.0, text="Concluído!")
                cap.empty()
                st.session_state["maps_res"]    = res
                st.session_state["maps_prefix"] = slug
            except ValueError as e:
                prog.empty(); cap.empty(); st.error(str(e))
                st.session_state["maps_res"] = []
            except Exception as e:
                prog.empty(); cap.empty()
                st.error(f"Erro inesperado: {e}")
                st.session_state["maps_res"] = []

    if st.session_state.get("maps_res"):
        res = st.session_state["maps_res"]
        st.success(f"✅ **{len(res)}** resultados encontrados")
        _stats(res)
        _botoes_download(res, st.session_state.get("maps_prefix", "prospecao"), sheets_auth)
        st.markdown("#### Prévia")
        _tabela(res)


# ══════════════════════════════════════════════════════════════════════════════
# ABA 2 — Receita Federal
# ══════════════════════════════════════════════════════════════════════════════
with aba_rf:
    st.markdown(
        '<div class="info-box">Dados oficiais da <strong>Receita Federal</strong> — sem conta, sem custo. '
        'Ideal para volumes grandes com CNPJ e e-mail. '
        '<strong>Primeiro uso:</strong> faz download dos arquivos (~350 MB); '
        'fica em cache por 30 dias.</div>',
        unsafe_allow_html=True,
    )

    with st.form("form_rf"):
        st.markdown('<div class="section-title">Localidade</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            mun_rf = st.text_input("Município (opcional)", placeholder="Ex: São Paulo",
                                   label_visibility="collapsed")
        with col2:
            uf_rf = st.selectbox("Estado *", SIGLAS_ESTADOS,
                                 index=SIGLAS_ESTADOS.index("SP"),
                                 label_visibility="collapsed")
        lim_rf = st.slider("Máx. resultados", 50, 2000, 300, 50)
        btn_rf = st.form_submit_button("🔍 Buscar na Receita Federal",
                                       use_container_width=True, type="primary")

    if btn_rf:
        from modules.receita_federal import buscar_por_cnae_rf
        local = mun_rf.strip() or uf_rf
        bar   = st.progress(0, text="Iniciando...")

        def _cb_rf(a, t, m):
            if t and t > 0:
                bar.progress(min(a / t, 1.0), text=m)

        try:
            res_rf = buscar_por_cnae_rf(uf=uf_rf, municipio=mun_rf.strip(),
                                         limite=lim_rf, callback_progresso=_cb_rf)
            bar.progress(1.0, text="Concluído!")
            st.session_state["rf_res"]    = res_rf
            st.session_state["rf_prefix"] = f"rf_{local.lower().replace(' ','_')}"
        except Exception as e:
            st.error(f"Erro: {e}")
            st.session_state["rf_res"] = []

    if st.session_state.get("rf_res"):
        res = st.session_state["rf_res"]
        st.success(f"✅ **{len(res)}** resultados encontrados")
        _stats(res)
        _botoes_download(res, st.session_state.get("rf_prefix", "prospecao_rf"), sheets_auth)
        st.markdown("#### Prévia")
        _tabela(res)
