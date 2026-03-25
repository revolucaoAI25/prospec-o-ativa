"""
Prospec-o-Ativa — Interface Web
Hospede gratuitamente em: https://share.streamlit.io
"""

import os
import io
import csv
import time
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


# ── Helpers de secrets ───────────────────────────────────────────────────────
def _get_secret(nome: str) -> str:
    """Lê chave: primeiro Streamlit Secrets, depois .env / variável de ambiente."""
    try:
        valor = st.secrets.get(nome, "")
        if valor:
            return str(valor).strip()
    except Exception:
        pass
    return os.getenv(nome, "").strip()


# ── Configuração da página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Prospec-o-Ativa",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stat-box {
        background: #f0f4f8;
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
        border-left: 4px solid #1F4E79;
    }
    .stat-number { font-size: 2rem; font-weight: 700; color: #1F4E79; }
    .stat-label  { font-size: 0.85rem; color: #555; margin-top: 4px; }
    .badge-ok    { background:#d4edda; color:#155724; padding:3px 10px; border-radius:12px; font-size:0.82rem; }
    .badge-warn  { background:#fff3cd; color:#856404; padding:3px 10px; border-radius:12px; font-size:0.82rem; }
    .badge-err   { background:#f8d7da; color:#721c24; padding:3px 10px; border-radius:12px; font-size:0.82rem; }
    div[data-testid="stForm"] { border: 1px solid #dce3ea; border-radius: 10px; padding: 20px; }
</style>
""", unsafe_allow_html=True)


# ── Helpers de exportação em memória ────────────────────────────────────────
from modules.google_sheets import COLUNAS_EXPORT as COLUNAS

# Colunas extras que só existem em alguns resultados
_COLUNAS_EXTRA = [
    ("telefone2",             "Telefone 2"),
    ("telefone_internacional","Telefone Intl."),
    ("status_funcionamento",  "Status"),
    ("porte",                 "Porte"),
    ("data_abertura",         "Data Abertura"),
    ("termo_busca",           "Termo Extra"),
]
TODAS_COLUNAS = COLUNAS + [c for c in _COLUNAS_EXTRA if c not in COLUNAS]


def para_csv_bytes(resultados: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([label for _, label in TODAS_COLUNAS])
    for r in resultados:
        w.writerow([r.get(col, "") for col, _ in TODAS_COLUNAS])
    return buf.getvalue().encode("utf-8-sig")


def para_excel_bytes(resultados: list[dict]) -> bytes:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Prospecção"

    h_font  = Font(bold=True, color="FFFFFF")
    h_fill  = PatternFill("solid", fgColor="1F4E79")
    h_align = Alignment(horizontal="center", vertical="center")

    cabecalho = [label for _, label in TODAS_COLUNAS]
    for ci, label in enumerate(cabecalho, 1):
        cell = ws.cell(row=1, column=ci, value=label)
        cell.font, cell.fill, cell.alignment = h_font, h_fill, h_align
    ws.row_dimensions[1].height = 20

    fill_par   = PatternFill("solid", fgColor="D6E4F0")
    fill_impar = PatternFill("solid", fgColor="FFFFFF")

    for ri, r in enumerate(resultados, 2):
        fill = fill_par if ri % 2 == 0 else fill_impar
        for ci, (col, _) in enumerate(TODAS_COLUNAS, 1):
            cell = ws.cell(row=ri, column=ci, value=r.get(col, ""))
            cell.fill = fill
            if col in ("site", "maps_url") and r.get(col):
                cell.hyperlink = r[col]
                cell.font = Font(color="0563C1", underline="single")

    for ci in range(1, len(cabecalho) + 1):
        max_len = max(
            len(str(ws.cell(row=rr, column=ci).value or ""))
            for rr in range(1, len(resultados) + 2)
        )
        ws.column_dimensions[get_column_letter(ci)].width = min(max_len + 2, 50)

    ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _mostrar_botoes_download(resultados: list[dict], prefixo: str, sheets_ok: bool):
    col1, col2, col3 = st.columns([2, 2, 2])
    ts = int(time.time())
    with col1:
        st.download_button(
            "⬇️ Baixar Excel (.xlsx)",
            data=para_excel_bytes(resultados),
            file_name=f"{prefixo}_{ts}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "⬇️ Baixar CSV",
            data=para_csv_bytes(resultados),
            file_name=f"{prefixo}_{ts}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col3:
        if sheets_ok:
            if st.button("📊 Exportar para Google Sheets", use_container_width=True, type="secondary"):
                _exportar_sheets(resultados)
        else:
            st.button(
                "📊 Google Sheets (não configurado)",
                use_container_width=True,
                disabled=True,
                help="Configure GOOGLE_SERVICE_ACCOUNT e GOOGLE_SHEET_URL nos Secrets para ativar.",
            )


def _exportar_sheets(resultados: list[dict]):
    from modules.google_sheets import exportar
    sa_json   = _get_secret("GOOGLE_SERVICE_ACCOUNT")
    sheet_url = st.session_state.get("sheets_url", _get_secret("GOOGLE_SHEET_URL"))
    aba_nome  = st.session_state.get("sheets_aba", "Prospecção")
    modo      = st.session_state.get("sheets_modo", "substituir")

    with st.spinner("Exportando para Google Sheets..."):
        sucesso, msg = exportar(resultados, sa_json, sheet_url, aba_nome, modo)

    if sucesso:
        st.success(msg)
    else:
        st.error(msg)


def _mostrar_stats(resultados: list[dict]):
    total        = len(resultados)
    com_telefone = sum(1 for r in resultados if r.get("telefone") or r.get("telefone2"))
    com_site     = sum(1 for r in resultados if r.get("site"))
    com_email    = sum(1 for r in resultados if r.get("email"))

    c1, c2, c3, c4 = st.columns(4)
    for col, num, label in [
        (c1, total,        "Total encontrados"),
        (c2, com_telefone, "Com telefone"),
        (c3, com_site,     "Com site"),
        (c4, com_email,    "Com e-mail"),
    ]:
        col.markdown(
            f'<div class="stat-box"><div class="stat-number">{num}</div>'
            f'<div class="stat-label">{label}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown("")


def _mostrar_tabela(resultados: list[dict]):
    import pandas as pd
    cols_vis = ["nome", "telefone", "email", "municipio", "uf",
                "endereco", "site", "avaliacao", "cnpj", "nicho_busca", "subnicho_busca", "fonte"]
    labels = {col: lbl for col, lbl in TODAS_COLUNAS}
    df = pd.DataFrame(resultados)
    cols_ok = [c for c in cols_vis if c in df.columns]
    df_vis = df[cols_ok].rename(columns=labels).fillna("").astype(str).replace("nan", "")
    st.dataframe(df_vis, use_container_width=True, height=420)


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎯 Prospec-o-Ativa")
    st.caption("Prospecção ativa em qualquer nicho")
    st.divider()

    # Status das integrações
    gmaps_ok  = bool(_get_secret("GOOGLE_MAPS_API_KEY"))
    sheets_sa = _get_secret("GOOGLE_SERVICE_ACCOUNT")
    sheets_ok = bool(sheets_sa)

    st.subheader("Integrações")

    if gmaps_ok:
        st.markdown('<span class="badge-ok">✓ Google Maps</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge-err">✗ Google Maps</span>', unsafe_allow_html=True)

    st.markdown("")

    if sheets_ok:
        st.markdown('<span class="badge-ok">✓ Google Sheets</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge-warn">○ Google Sheets (opcional)</span>', unsafe_allow_html=True)

    st.markdown("")
    st.markdown('<span class="badge-ok">✓ Receita Federal</span>', unsafe_allow_html=True)

    # Configuração do Google Sheets
    st.divider()
    with st.expander("⚙️ Configurar Google Sheets"):
        st.markdown("""
Configure a planilha que receberá os resultados automaticamente.
""")
        sheet_url_input = st.text_input(
            "URL da planilha Google",
            value=st.session_state.get("sheets_url", _get_secret("GOOGLE_SHEET_URL") or ""),
            placeholder="https://docs.google.com/spreadsheets/d/...",
            key="sheets_url_input",
        )
        aba_input = st.text_input(
            "Nome da aba",
            value=st.session_state.get("sheets_aba", "Prospecção"),
            key="sheets_aba_input",
        )
        modo_input = st.radio(
            "Ao exportar",
            ["substituir", "acrescentar"],
            format_func=lambda x: "Substituir tudo" if x == "substituir" else "Acrescentar ao final",
            key="sheets_modo_input",
            horizontal=True,
        )
        if st.button("💾 Salvar configuração", use_container_width=True):
            st.session_state["sheets_url"]  = sheet_url_input
            st.session_state["sheets_aba"]  = aba_input
            st.session_state["sheets_modo"] = modo_input
            st.success("Configuração salva!")

        if sheets_ok and sheet_url_input:
            if st.button("🔌 Testar conexão", use_container_width=True):
                from modules.google_sheets import testar_conexao, obter_email_service_account
                ok, msg = testar_conexao(sheets_sa, sheet_url_input)
                if ok:
                    st.success(msg)
                    email_sa = obter_email_service_account(sheets_sa)
                    if email_sa:
                        st.caption(f"Service Account: `{email_sa}`")
                else:
                    st.error(msg)

        with st.expander("Como configurar?"):
            st.markdown("""
**1. Service Account (uma vez):**
- Google Cloud Console → seu projeto → IAM e Admin → Contas de Serviço
- Crie uma conta → gere chave JSON
- Cole o JSON inteiro em Secrets como `GOOGLE_SERVICE_ACCOUNT`

**2. Compartilhe a planilha:**
- Abra sua planilha Google
- Compartilhe com o e-mail do Service Account (com permissão de **Editor**)

**3. Cole a URL acima** e salve.

> Gratuito para uso normal (Google Sheets API).
""")

    with st.expander("Como configurar Google Maps?"):
        st.markdown("""
1. [console.cloud.google.com](https://console.cloud.google.com/)
2. Ative **Places API**
3. Credenciais → Criar Chave de API
4. Adicione em Secrets: `GOOGLE_MAPS_API_KEY`

> Google dá **US$200/mês grátis** (~5.000 buscas).
""")


# ── Conteúdo principal ───────────────────────────────────────────────────────
st.header("🎯 Prospec-o-Ativa")
st.markdown(
    "Monte bases de prospecção com **nome, telefone, e-mail, endereço e site** "
    "de qualquer nicho. Exporte para Excel, CSV ou diretamente para o Google Sheets."
)
st.divider()

aba_maps, aba_rf = st.tabs([
    "🗺️  Google Maps  (recomendado — tem telefone)",
    "📋  Receita Federal  (dados oficiais em massa)",
])


# ══════════════════════════════════════════════════════════════════════════════
# ABA 1 — Google Maps
# ══════════════════════════════════════════════════════════════════════════════
with aba_maps:
    from modules.nichos import NICHOS, ESTADOS, NOMES_NICHOS, SIGLAS_ESTADOS

    if not gmaps_ok:
        st.warning(
            "⚠️ Chave do Google Maps não configurada. Veja as instruções na sidebar.",
            icon="⚠️",
        )

    st.markdown(
        "Busca direto no Google Maps. Melhor fonte para **telefones**. "
        "Retorna até ~500 resultados usando múltiplas buscas automáticas."
    )

    with st.form("form_maps"):

        # ── Linha 1: Nicho + Subnicho ─────────────────────────────────────
        col_nicho, col_sub = st.columns([2, 2])

        with col_nicho:
            nicho_sel = st.selectbox(
                "Nicho *",
                options=NOMES_NICHOS,
                index=0,
                help="Categoria do público-alvo. Campo obrigatório.",
            )

        nicho_data    = NICHOS[nicho_sel]
        is_customizado = nicho_sel == "Outro / Personalizado"
        subnichos_disp = nicho_data["subnichos"]

        with col_sub:
            if is_customizado:
                query_custom = st.text_input(
                    "Termo de busca personalizado *",
                    placeholder='Ex: "clínica veterinária", "pet shop"',
                    help="Será usado diretamente na busca do Google Maps.",
                )
                subnicho_sel = ""
            else:
                opcoes_sub = ["Todos (sem filtro)"] + subnichos_disp + ["Personalizado..."]
                subnicho_sel = st.selectbox(
                    "Subnicho / Especialidade",
                    options=opcoes_sub,
                    help="Refina a busca por especialidade. Opcional.",
                )

        # Se subnicho for "Personalizado..." mostra campo de texto
        subnicho_custom = ""
        if not is_customizado and subnicho_sel == "Personalizado...":
            subnicho_custom = st.text_input(
                "Especialidade personalizada",
                placeholder='Ex: "direito aeronáutico", "cardiologia pediátrica"',
            )

        # ── Linha 2: Localidade ───────────────────────────────────────────
        st.markdown("**Localidade** — preencha ao menos uma das opções:")
        col_cidade, col_estado = st.columns([3, 1])

        with col_cidade:
            cidade = st.text_input(
                "Cidade",
                placeholder="Ex: São Paulo",
                help="Deixe em branco para buscar em todo o estado.",
            )
        with col_estado:
            estado_idx = SIGLAS_ESTADOS.index("SP") if "SP" in SIGLAS_ESTADOS else 0
            estado = st.selectbox(
                "Estado",
                options=["(nenhum)"] + SIGLAS_ESTADOS,
                index=estado_idx + 1,
                help="Selecione o estado. Pode usar só o estado, sem cidade.",
            )
            if estado == "(nenhum)":
                estado = ""

        # ── Limite ────────────────────────────────────────────────────────
        limite = st.slider(
            "Número máximo de resultados",
            min_value=20, max_value=500, value=60, step=20,
            help=(
                "O Google Maps retorna até 60 por busca. Para mais resultados, "
                "o sistema faz múltiplas buscas automáticas (gasta mais crédito da API)."
            ),
        )

        buscar_btn = st.form_submit_button(
            "🔍 Buscar no Google Maps",
            disabled=not gmaps_ok,
            use_container_width=True,
            type="primary",
        )

    # ── Execução da busca ─────────────────────────────────────────────────
    if buscar_btn:
        cidade_v = cidade.strip()
        estado_v = estado.strip()

        # Validações
        if not cidade_v and not estado_v:
            st.error("Informe ao menos a cidade ou o estado.")
        elif is_customizado and not query_custom.strip():
            st.error("Informe o termo de busca personalizado.")
        else:
            from modules.google_maps import buscar

            # Monta query e subnicho finais
            if is_customizado:
                query_base    = query_custom.strip()
                subnicho_final = ""
                nicho_label   = query_custom.strip()
            else:
                query_base    = nicho_data["query"]
                nicho_label   = nicho_sel
                if subnicho_sel == "Personalizado...":
                    subnicho_final = subnicho_custom.strip()
                elif subnicho_sel == "Todos (sem filtro)":
                    subnicho_final = ""
                else:
                    subnicho_final = subnicho_sel

            # Monta localidade
            if cidade_v and estado_v:
                localidade = f"{cidade_v}, {ESTADOS.get(estado_v, estado_v)}"
            elif cidade_v:
                localidade = cidade_v
            else:
                localidade = ESTADOS.get(estado_v, estado_v)

            prefixo = f"{nicho_label[:20].lower().replace(' ', '_')}_{localidade[:20].lower().replace(' ', '_').replace(',', '')}"

            status_txt = st.empty()
            barra = st.progress(0, text="Iniciando busca...")

            def cb_maps(atual, total, msg):
                status_txt.caption(msg)
                if total and total > 0:
                    barra.progress(min(atual / total, 1.0), text=msg)

            try:
                resultados = buscar(
                    query_base=query_base,
                    localidade=localidade,
                    limite=limite,
                    api_key=_get_secret("GOOGLE_MAPS_API_KEY"),
                    nicho=nicho_label,
                    subnicho=subnicho_final,
                    cidade=cidade_v,
                    estado=estado_v,
                    progress_callback=cb_maps,
                )
                barra.progress(1.0, text="Concluído!")
                status_txt.empty()
                st.session_state["maps_res"]     = resultados
                st.session_state["maps_prefixo"] = prefixo
            except ValueError as e:
                barra.empty(); status_txt.empty()
                st.error(str(e))
                st.session_state["maps_res"] = []
            except Exception as e:
                barra.empty(); status_txt.empty()
                st.error(f"Erro inesperado: {e}")
                st.session_state["maps_res"] = []

    if st.session_state.get("maps_res"):
        res = st.session_state["maps_res"]
        st.success(f"✅ {len(res)} resultados encontrados!")
        _mostrar_stats(res)
        _mostrar_botoes_download(res, st.session_state.get("maps_prefixo", "prospecao"), sheets_ok)
        st.markdown("#### Prévia dos resultados")
        _mostrar_tabela(res)


# ══════════════════════════════════════════════════════════════════════════════
# ABA 2 — Receita Federal
# ══════════════════════════════════════════════════════════════════════════════
with aba_rf:
    st.markdown("""
    Busca nos **dados abertos da Receita Federal** — sem conta, sem custo.
    Ideal para volumes maiores e quando precisa do CNPJ e e-mail.
    """)
    st.info(
        "**Primeiro uso:** baixa os arquivos da RF (~350 MB por lote). "
        "Acontece uma vez — fica em cache por 30 dias.",
        icon="ℹ️",
    )

    with st.form("form_rf"):
        col1, col2 = st.columns(2)
        with col1:
            municipio_rf = st.text_input(
                "Município (opcional)",
                placeholder="Ex: São Paulo",
                help="Deixe em branco para buscar em todo o estado.",
            )
        with col2:
            uf_rf = st.selectbox(
                "Estado *",
                options=SIGLAS_ESTADOS,
                index=SIGLAS_ESTADOS.index("SP"),
            )

        limite_rf = st.slider(
            "Número máximo de resultados",
            min_value=50, max_value=2000, value=300, step=50,
        )

        buscar_rf_btn = st.form_submit_button(
            "🔍 Buscar na Receita Federal",
            use_container_width=True,
            type="primary",
        )

    if buscar_rf_btn:
        from modules.receita_federal import buscar_por_cnae_rf

        local = municipio_rf.strip() if municipio_rf.strip() else uf_rf
        barra_rf = st.progress(0, text="Iniciando...")

        def cb_rf(atual, total, msg):
            if total and total > 0:
                barra_rf.progress(min(atual / total, 1.0), text=msg)

        try:
            res_rf = buscar_por_cnae_rf(
                uf=uf_rf,
                municipio=municipio_rf.strip(),
                limite=limite_rf,
                callback_progresso=cb_rf,
            )
            barra_rf.progress(1.0, text="Concluído!")
            st.session_state["rf_res"]     = res_rf
            st.session_state["rf_prefixo"] = f"rf_{local.lower().replace(' ', '_')}"
        except Exception as e:
            st.error(f"Erro: {e}")
            st.session_state["rf_res"] = []

    if st.session_state.get("rf_res"):
        res = st.session_state["rf_res"]
        st.success(f"✅ {len(res)} resultados encontrados!")
        _mostrar_stats(res)
        _mostrar_botoes_download(res, st.session_state.get("rf_prefixo", "prospecao_rf"), sheets_ok)
        st.markdown("#### Prévia dos resultados")
        _mostrar_tabela(res)
