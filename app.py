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


def _get_secret(nome: str) -> str:
    """
    Lê uma chave de API buscando em duas fontes, nesta ordem:
    1. Streamlit Secrets (Streamlit Cloud)
    2. Variável de ambiente / arquivo .env (uso local)
    """
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
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Estilos CSS ──────────────────────────────────────────────────────────────
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
    .badge-ok    { background:#d4edda; color:#155724; padding:2px 8px; border-radius:12px; font-size:0.8rem; }
    .badge-warn  { background:#fff3cd; color:#856404; padding:2px 8px; border-radius:12px; font-size:0.8rem; }
    .badge-err   { background:#f8d7da; color:#721c24; padding:2px 8px; border-radius:12px; font-size:0.8rem; }
</style>
""", unsafe_allow_html=True)


# ── Helpers de exportação em memória ────────────────────────────────────────
COLUNAS = [
    ("nome",                    "Nome"),
    ("telefone",                "Telefone"),
    ("telefone2",               "Telefone 2"),
    ("telefone_internacional",  "Telefone Intl."),
    ("email",                   "E-mail"),
    ("endereco",                "Endereço"),
    ("municipio",               "Município"),
    ("uf",                      "UF"),
    ("cep",                     "CEP"),
    ("site",                    "Site"),
    ("maps_url",                "Google Maps"),
    ("avaliacao",               "Avaliação"),
    ("total_avaliacoes",        "Nº Avaliações"),
    ("status_funcionamento",    "Status"),
    ("cnpj",                    "CNPJ"),
    ("porte",                   "Porte"),
    ("data_abertura",           "Data Abertura"),
    ("cidade_busca",            "Cidade Buscada"),
    ("estado_busca",            "Estado Buscado"),
    ("termo_busca",             "Especialidade"),
    ("fonte",                   "Fonte"),
]


def para_csv_bytes(resultados: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([label for _, label in COLUNAS])
    for r in resultados:
        w.writerow([r.get(col, "") for col, _ in COLUNAS])
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

    cabecalho = [label for _, label in COLUNAS]
    for ci, label in enumerate(cabecalho, 1):
        cell = ws.cell(row=1, column=ci, value=label)
        cell.font, cell.fill, cell.alignment = h_font, h_fill, h_align
    ws.row_dimensions[1].height = 20

    fill_par  = PatternFill("solid", fgColor="D6E4F0")
    fill_impar= PatternFill("solid", fgColor="FFFFFF")

    for ri, r in enumerate(resultados, 2):
        fill = fill_par if ri % 2 == 0 else fill_impar
        for ci, (col, _) in enumerate(COLUNAS, 1):
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


def _mostrar_botoes_download(resultados: list[dict], prefixo: str):
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="⬇️ Baixar Excel (.xlsx)",
            data=para_excel_bytes(resultados),
            file_name=f"{prefixo}_{int(time.time())}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            label="⬇️ Baixar CSV",
            data=para_csv_bytes(resultados),
            file_name=f"{prefixo}_{int(time.time())}.csv",
            mime="text/csv",
            use_container_width=True,
        )


def _mostrar_stats(resultados: list[dict]):
    total         = len(resultados)
    com_telefone  = sum(1 for r in resultados if r.get("telefone") or r.get("telefone2"))
    com_site      = sum(1 for r in resultados if r.get("site"))
    com_email     = sum(1 for r in resultados if r.get("email"))

    c1, c2, c3, c4 = st.columns(4)
    for col, num, label in [
        (c1, total,        "Total encontrados"),
        (c2, com_telefone, "Com telefone"),
        (c3, com_site,     "Com site"),
        (c4, com_email,    "Com e-mail"),
    ]:
        col.markdown(
            f'<div class="stat-box">'
            f'<div class="stat-number">{num}</div>'
            f'<div class="stat-label">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown("")


def _mostrar_tabela(resultados: list[dict]):
    colunas_visiveis = [
        "nome", "telefone", "email", "municipio", "uf",
        "endereco", "site", "avaliacao", "cnpj", "fonte",
    ]
    labels = {col: lbl for col, lbl in COLUNAS}
    import pandas as pd
    df = pd.DataFrame(resultados)
    cols_existentes = [c for c in colunas_visiveis if c in df.columns]
    df_vis = df[cols_existentes].rename(columns=labels)
    df_vis = df_vis.fillna("").astype(str).replace("nan", "")
    st.dataframe(df_vis, use_container_width=True, height=400)


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/scales--v1.png", width=64)
    st.title("Prospec-o-Ativa")
    st.caption("Escritórios de advocacia")
    st.divider()

    st.subheader("Status das chaves de API")

    gmaps_ok = bool(_get_secret("GOOGLE_MAPS_API_KEY"))

    if gmaps_ok:
        st.markdown('<span class="badge-ok">✓ Google Maps configurado</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge-err">✗ Google Maps não configurado</span>', unsafe_allow_html=True)

    st.markdown("")
    st.markdown('<span class="badge-ok">✓ Receita Federal — sem conta necessária</span>', unsafe_allow_html=True)

    st.divider()
    with st.expander("Como configurar a chave do Google Maps?"):
        st.markdown("""
**Google Maps API** (para busca Maps):
1. Acesse [console.cloud.google.com](https://console.cloud.google.com/)
2. Crie um projeto > ative **Places API**
3. Credenciais > Criar Chave de API
4. Adicione em `.env` ou nos Secrets do Streamlit

> O Google dá **US$ 200/mês grátis** (~5.000 buscas).

**Receita Federal**: não precisa de nenhuma conta.
Os dados são públicos e baixados direto do governo.
""")


# ── Conteúdo principal ───────────────────────────────────────────────────────
st.header("⚖️ Prospecção de Escritórios de Advocacia")
st.markdown(
    "Monte bases de prospecção com **nome, telefone, e-mail, endereço e site** "
    "de escritórios de advocacia. Exporte para Excel ou CSV com um clique."
)
st.divider()

aba_maps, aba_cnpj = st.tabs([
    "🗺️  Google Maps  (recomendado para telefones)",
    "📋  CNPJ / Receita Federal  (dados oficiais em massa)",
])


# ══════════════════════════════════════════════════════════════════════════════
# ABA 1 — Google Maps
# ══════════════════════════════════════════════════════════════════════════════
with aba_maps:
    if not gmaps_ok:
        st.warning(
            "⚠️ Chave do Google Maps não configurada. "
            "Siga as instruções na sidebar para ativar esta busca.",
            icon="⚠️",
        )

    st.markdown("""
    Busca escritórios diretamente no Google Maps. É a fonte **mais confiável para telefones**.
    Retorna até 60 resultados por busca (por limitação do Google).
    """)

    with st.form("form_maps"):
        col1, col2, col3 = st.columns([3, 1, 2])
        with col1:
            cidade = st.text_input(
                "Cidade *",
                placeholder="Ex: São Paulo",
                help="Nome da cidade que deseja prospectar",
            )
        with col2:
            estado = st.text_input(
                "Estado",
                placeholder="SP",
                max_chars=2,
                help="Sigla do estado (opcional, mas recomendado)",
            ).upper()
        with col3:
            especialidade = st.selectbox(
                "Especialidade",
                options=[
                    "Todos (sem filtro)",
                    "Trabalhista",
                    "Tributário",
                    "Família e Divórcio",
                    "Criminal / Penal",
                    "Imobiliário",
                    "Previdenciário / INSS",
                    "Empresarial / Societário",
                    "Cível",
                    "Ambiental",
                ],
                help="Filtra por área de atuação do escritório",
            )

        limite = st.slider(
            "Número máximo de resultados",
            min_value=10, max_value=60, value=40, step=10,
            help="O Google Maps retorna até 60 resultados por busca",
        )

        buscar_maps = st.form_submit_button(
            "🔍 Buscar no Google Maps",
            disabled=not gmaps_ok,
            use_container_width=True,
            type="primary",
        )

    if buscar_maps:
        if not cidade.strip():
            st.error("Informe o nome da cidade.")
        else:
            from modules.google_maps import buscar_escritorios

            termo = "" if especialidade == "Todos (sem filtro)" else especialidade.lower()

            with st.spinner(f"Buscando escritórios em {cidade}... pode levar 1-2 minutos."):
                try:
                    resultados = buscar_escritorios(
                        cidade=cidade.strip(),
                        estado=estado.strip(),
                        termo_extra=termo,
                        limite=limite,
                        api_key=_get_secret("GOOGLE_MAPS_API_KEY"),
                    )
                    st.session_state["maps_resultados"] = resultados
                    st.session_state["maps_prefixo"] = f"advocacia_{cidade.lower().replace(' ', '_')}"
                except ValueError as e:
                    st.error(str(e))
                    st.session_state["maps_resultados"] = []
                except Exception as e:
                    st.error(f"Erro inesperado: {e}")
                    st.session_state["maps_resultados"] = []

    if "maps_resultados" in st.session_state and st.session_state["maps_resultados"]:
        res = st.session_state["maps_resultados"]
        st.success(f"✅ {len(res)} escritórios encontrados!")
        _mostrar_stats(res)
        _mostrar_botoes_download(res, st.session_state.get("maps_prefixo", "prospecao_maps"))
        st.markdown("#### Prévia dos resultados")
        _mostrar_tabela(res)


# ══════════════════════════════════════════════════════════════════════════════
# ABA 2 — Receita Federal (dados abertos, sem conta)
# ══════════════════════════════════════════════════════════════════════════════
with aba_cnpj:
    st.markdown("""
    Busca nos **dados abertos oficiais da Receita Federal** — sem precisar de
    conta em nenhum serviço. Os arquivos são baixados direto do governo e
    filtrados localmente. Ideal para **volumes maiores** e quando você precisa
    do CNPJ, e-mail e dados cadastrais completos.
    """)

    st.info(
        "**Primeiro uso:** o sistema baixa os arquivos da Receita Federal (~350 MB por lote). "
        "Isso leva alguns minutos mas acontece só uma vez — depois fica em cache por 30 dias.",
        icon="ℹ️",
    )

    with st.form("form_cnpj"):
        col1, col2 = st.columns(2)
        with col1:
            municipio = st.text_input(
                "Município (opcional)",
                placeholder="Ex: São Paulo",
                help="Deixe em branco para buscar em todo o estado.",
            )
        with col2:
            uf_cnpj = st.selectbox(
                "Estado *",
                options=[
                    "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA",
                    "MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN",
                    "RS","RO","RR","SC","SP","SE","TO",
                ],
                index=24,  # SP
                help="Estado onde buscar",
            )

        limite_cnpj = st.slider(
            "Número máximo de resultados",
            min_value=50, max_value=2000, value=300, step=50,
            help="Sem limite real — todos os escritórios ativos do estado estão disponíveis",
        )

        buscar_cnpj = st.form_submit_button(
            "🔍 Buscar na Receita Federal",
            use_container_width=True,
            type="primary",
        )

    if buscar_cnpj:
        from modules.receita_federal import buscar_por_cnae_rf

        local_label = municipio.strip() if municipio.strip() else uf_cnpj

        progresso_placeholder = st.empty()
        barra = st.progress(0, text="Iniciando...")

        def atualizar_progresso(atual, total, msg):
            barra.progress(atual / total, text=msg)

        with st.spinner(f"Buscando escritórios em {local_label} nos dados da Receita Federal..."):
            try:
                resultados_cnpj = buscar_por_cnae_rf(
                    uf=uf_cnpj,
                    municipio=municipio.strip(),
                    limite=limite_cnpj,
                    callback_progresso=atualizar_progresso,
                )
                barra.progress(1.0, text="Concluído!")
                st.session_state["cnpj_resultados"] = resultados_cnpj
                st.session_state["cnpj_prefixo"] = (
                    f"advocacia_rf_{local_label.lower().replace(' ', '_')}"
                )
            except Exception as e:
                st.error(f"Erro ao acessar dados da Receita Federal: {e}")
                st.session_state["cnpj_resultados"] = []

    if "cnpj_resultados" in st.session_state and st.session_state["cnpj_resultados"]:
        res = st.session_state["cnpj_resultados"]
        st.success(f"✅ {len(res)} escritórios encontrados!")
        _mostrar_stats(res)
        _mostrar_botoes_download(res, st.session_state.get("cnpj_prefixo", "prospecao_rf"))
        st.markdown("#### Prévia dos resultados")
        _mostrar_tabela(res)
