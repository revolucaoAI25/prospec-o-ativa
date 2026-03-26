"""Prospec-o-Ativa · Revolução AI"""
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
_code = st.query_params.get("code","")
if _code and "sheets_creds" not in st.session_state:
    cid, cs, ru = _s("GOOGLE_CLIENT_ID"), _s("GOOGLE_CLIENT_SECRET"), _s("APP_URL","http://localhost:8501")
    if cid and cs:
        try:
            from modules.google_sheets import trocar_codigo
            st.session_state["sheets_creds"] = trocar_codigo(cid, cs, ru, _code)
        except Exception as e:
            st.session_state["_oauth_err"] = str(e)
    st.query_params.clear()
    st.rerun()

st.set_page_config(page_title="Prospec-o-Ativa · Revolução AI", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif}
.brand-header{background:linear-gradient(135deg,#0D1F15,#0A0A0F 60%,#061A10);
  border-bottom:1px solid #00D97E30;padding:16px 28px 12px;
  margin:-1rem -1rem 1.5rem;display:flex;align-items:center;gap:12px}
.brand-dot{width:34px;height:34px;background:#00D97E;border-radius:9px;
  display:flex;align-items:center;justify-content:center;
  font-weight:700;color:#0A0A0F;font-size:17px;flex-shrink:0}
.brand-title{font-size:1.2rem;font-weight:700;color:#F0F0F5;line-height:1.2}
.brand-sub{font-size:.72rem;color:#00D97E;font-weight:500;letter-spacing:.08em;text-transform:uppercase}
.stat-card{background:#141418;border:1px solid #1E1E28;border-radius:12px;
  padding:16px 18px;text-align:center;position:relative;overflow:hidden}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;
  background:linear-gradient(90deg,#00D97E,#00A85E)}
.stat-num{font-size:2rem;font-weight:700;color:#00D97E;line-height:1}
.stat-lbl{font-size:.75rem;color:#8888A0;margin-top:5px;text-transform:uppercase;letter-spacing:.06em}
.badge{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;
  border-radius:20px;font-size:.78rem;font-weight:500}
.b-ok{background:#052e16;color:#00D97E;border:1px solid #00D97E40}
.b-warn{background:#2d1b00;color:#FFB800;border:1px solid #FFB80040}
.b-err{background:#2d0a0a;color:#FF4757;border:1px solid #FF475740}
.sec{font-size:.68rem;font-weight:600;color:#00D97E;text-transform:uppercase;
  letter-spacing:.12em;margin:1rem 0 .4rem}
.hr{border:none;border-top:1px solid #1E1E28;margin:.8rem 0}
div[data-testid="stForm"]{background:#141418;border:1px solid #1E1E28;border-radius:14px;padding:22px}
.info-box{background:#0D1F15;border:1px solid #00D97E30;border-radius:10px;
  padding:11px 15px;font-size:.84rem;color:#A0C8B0;margin-bottom:1rem}
.login-card{background:#141418;border:1px solid #1E1E28;border-radius:18px;
  padding:40px 36px;max-width:400px;margin:60px auto 0}
.page-title{font-size:1.4rem;font-weight:700;color:#F0F0F5;margin-bottom:.25rem}
.page-sub{font-size:.85rem;color:#8888A0;margin-bottom:1.5rem}
</style>""", unsafe_allow_html=True)

from modules.google_sheets import COLUNAS_EXPORT
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
    tot=len(rows); tel=sum(1 for r in rows if r.get("telefone") or r.get("telefone2"))
    site=sum(1 for r in rows if r.get("site")); em=sum(1 for r in rows if r.get("email"))
    cs=st.columns(4)
    for col,n,lbl in zip(cs,[tot,tel,site,em],["Total","Com telefone","Com site","Com e-mail"]):
        col.markdown(f'<div class="stat-card"><div class="stat-num">{n}</div><div class="stat-lbl">{lbl}</div></div>',unsafe_allow_html=True)
    st.markdown("")

def _tabela(rows):
    import pandas as pd
    vis=["nome","telefone","email","municipio","uf","endereco","site","avaliacao","cnpj","nicho_busca","subnicho_busca","fonte"]
    lm={c:l for c,l in ALL_COLS}; df=pd.DataFrame(rows)
    cols=[c for c in vis if c in df.columns]
    st.dataframe(df[cols].rename(columns=lm).fillna("").astype(str).replace("nan",""), use_container_width=True, height=380)

def _dl_buttons(rows, prefix, sheets_auth):
    ts=int(time.time()); c1,c2,c3=st.columns(3)
    with c1: st.download_button("⬇️ Excel",_xlsx(rows),f"{prefix}_{ts}.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
    with c2: st.download_button("⬇️ CSV",_csv(rows),f"{prefix}_{ts}.csv","text/csv",use_container_width=True)
    with c3:
        if sheets_auth:
            if st.button("📊 Google Sheets",use_container_width=True): _export_sheets(rows)
        else:
            st.button("📊 Google Sheets",use_container_width=True,disabled=True,help="Conecte sua conta Google em Configurações.")

def _export_sheets(rows):
    from modules.google_sheets import exportar, extrair_sheet_id
    creds=st.session_state.get("sheets_creds"); sid=st.session_state.get("sheets_selected_id","")
    aba=st.session_state.get("sheets_aba","Prospecção"); modo=st.session_state.get("sheets_modo","substituir")
    if not creds or not sid: st.warning("Escolha uma planilha em Configurações."); return
    with st.spinner("Exportando..."): ok,msg=exportar(rows,creds,sid,aba,modo)
    (st.success if ok else st.error)(msg)

# ══════════════════════════════════════════════════════════════
# PÁGINAS
# ══════════════════════════════════════════════════════════════

def pagina_login():
    st.markdown("""<div class="login-card">
    <div style="text-align:center;margin-bottom:28px">
        <div style="width:48px;height:48px;background:#00D97E;border-radius:13px;display:inline-flex;
            align-items:center;justify-content:center;font-weight:700;color:#0A0A0F;font-size:22px">R</div>
        <div style="font-size:1.4rem;font-weight:700;color:#F0F0F5;margin-top:12px">Prospec-o-Ativa</div>
        <div style="font-size:.72rem;color:#00D97E;letter-spacing:.1em;text-transform:uppercase">Revolução AI</div>
    </div></div>""", unsafe_allow_html=True)

    col=st.columns([1,2,1])[1]
    with col:
        with st.form("login"):
            email=st.text_input("E-mail",placeholder="seu@email.com")
            senha=st.text_input("Senha",type="password",placeholder="••••••••")
            btn=st.form_submit_button("Entrar",use_container_width=True,type="primary")
        if btn:
            if not email or not senha:
                st.error("Preencha e-mail e senha.")
            else:
                from modules.auth import login, supabase_configurado
                if not supabase_configurado():
                    st.error("Supabase não configurado. Verifique SUPABASE_URL e SUPABASE_ANON_KEY nos Secrets.")
                else:
                    with st.spinner("Autenticando..."):
                        ok, msg = login(email, senha)
                    if ok:
                        st.session_state["page"] = "busca"
                        st.rerun()
                    else:
                        st.error(msg)


def pagina_busca():
    from modules.nichos import NICHOS, ESTADOS, NOMES_NICHOS, SIGLAS_ESTADOS

    st.markdown('<div class="page-title">🔍 Nova Busca</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Busque leads por nicho e localidade</div>', unsafe_allow_html=True)

    gmaps_key = st.session_state.get("user_gmaps_key") or _s("GOOGLE_MAPS_API_KEY")
    gmaps_ok  = bool(gmaps_key)

    aba_maps, aba_rf = st.tabs(["🗺️  Google Maps  ·  com telefone", "📋  Receita Federal  ·  dados oficiais"])

    with aba_maps:
        if not gmaps_ok:
            st.warning("Chave do Google Maps não configurada. Adicione em Configurações ou nos Secrets.", icon="⚠️")
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
                prog = st.progress(0, text="Iniciando..."); cap = st.empty()
                def _cb(a,t,m): cap.caption(m); prog.progress(min(a/t,1.0),text=m) if t and t>0 else None
                try:
                    res = maps_buscar(query_base=qbase, localidade=localidade, limite=lim,
                                      api_key=gmaps_key, nicho=nicho_lbl, subnicho=sub_final,
                                      cidade=cv, estado=ev, progress_callback=_cb)
                    prog.progress(1.0, text="Concluído!"); cap.empty()
                    st.session_state["maps_res"] = res; st.session_state["maps_prefix"] = slug
                    # Salva no banco
                    from modules.database import salvar_pesquisa, salvar_leads
                    sid = salvar_pesquisa(nicho_lbl, sub_final, cv, ev, localidade, "maps", len(res))
                    if sid: salvar_leads(sid, res)
                except ValueError as e: prog.empty(); cap.empty(); st.error(str(e)); st.session_state["maps_res"]=[]
                except Exception as e: prog.empty(); cap.empty(); st.error(f"Erro: {e}"); st.session_state["maps_res"]=[]

        if st.session_state.get("maps_res"):
            res = st.session_state["maps_res"]
            st.success(f"✅ **{len(res)}** resultados")
            _stats(res); _dl_buttons(res, st.session_state.get("maps_prefix","prospecao"), "sheets_creds" in st.session_state)
            st.markdown("#### Prévia"); _tabela(res)

    with aba_rf:
        st.markdown('<div class="info-box">Dados oficiais da <strong>Receita Federal</strong>. Ideal para volumes maiores com CNPJ e e-mail. <strong>1º uso:</strong> baixa arquivos ~350 MB (fica em cache 30 dias).</div>', unsafe_allow_html=True)
        with st.form("form_rf"):
            c1,c2=st.columns(2)
            with c1: mun_rf=st.text_input("Município (opcional)", placeholder="Ex: São Paulo", label_visibility="collapsed")
            with c2: uf_rf=st.selectbox("Estado *", SIGLAS_ESTADOS, index=SIGLAS_ESTADOS.index("SP"), label_visibility="collapsed")
            lim_rf=st.slider("Máx. resultados",50,2000,300,50)
            btn_rf=st.form_submit_button("🔍 Buscar na Receita Federal", use_container_width=True, type="primary")
        if btn_rf:
            from modules.receita_federal import buscar_por_cnae_rf
            local=mun_rf.strip() or uf_rf; bar=st.progress(0,text="Iniciando...")
            def _cbrf(a,t,m): bar.progress(min(a/t,1.0),text=m) if t and t>0 else None
            try:
                res_rf=buscar_por_cnae_rf(uf=uf_rf,municipio=mun_rf.strip(),limite=lim_rf,callback_progresso=_cbrf)
                bar.progress(1.0,text="Concluído!")
                st.session_state["rf_res"]=res_rf; st.session_state["rf_prefix"]=f"rf_{local.lower().replace(' ','_')}"
                from modules.database import salvar_pesquisa, salvar_leads
                sid=salvar_pesquisa("Advocacia (RF)","",mun_rf.strip(),uf_rf,local,"receita_federal",len(res_rf))
                if sid: salvar_leads(sid,res_rf)
            except Exception as e: st.error(f"Erro: {e}"); st.session_state["rf_res"]=[]
        if st.session_state.get("rf_res"):
            res=st.session_state["rf_res"]
            st.success(f"✅ **{len(res)}** resultados")
            _stats(res); _dl_buttons(res,st.session_state.get("rf_prefix","prospecao_rf"),"sheets_creds" in st.session_state)
            st.markdown("#### Prévia"); _tabela(res)


def pagina_historico():
    from modules.database import listar_pesquisas, buscar_leads_da_pesquisa, deletar_pesquisa

    st.markdown('<div class="page-title">📁 Histórico de Pesquisas</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Todas as suas extrações anteriores com leads salvos</div>', unsafe_allow_html=True)

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
            c1,c2 = st.columns(2)
            with c1: st.download_button("⬇️ Excel",_xlsx(leads),f"{slug}_{ts}.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True,key=f"xl_{p['id']}")
            with c2: st.download_button("⬇️ CSV",_csv(leads),f"{slug}_{ts}.csv","text/csv",use_container_width=True,key=f"csv_{p['id']}")

            import pandas as pd
            vis=["nome","telefone","email","municipio","uf","site","avaliacao","cnpj"]
            lm={c:l for c,l in ALL_COLS}; df=pd.DataFrame(leads)
            st.dataframe(df[[c for c in vis if c in df.columns]].rename(columns=lm).fillna("").astype(str).replace("nan",""), use_container_width=True, height=280)


# ── Configurações ──────────────────────────────────────────────────────────────

def pagina_configuracoes():
    from modules.database import carregar_configuracoes, salvar_configuracoes
    from modules.google_sheets import gerar_url_auth

    st.markdown('<div class="page-title">⚙️ Configurações</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Gerencie suas credenciais e integrações</div>', unsafe_allow_html=True)

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

        # Credenciais OAuth do app
        cid = cfg.get("google_client_id","") or _s("GOOGLE_CLIENT_ID")
        cs  = cfg.get("google_client_secret","") or _s("GOOGLE_CLIENT_SECRET")
        ru  = cfg.get("app_url","") or _s("APP_URL","http://localhost:8501")

        col1, col2 = st.columns(2)
        with col1:
            new_cid = st.text_input("Google Client ID",  value=cid, placeholder="...apps.googleusercontent.com", key="cfg_cid")
        with col2:
            new_cs  = st.text_input("Google Client Secret", value=cs, type="password", placeholder="GOCSPX-...", key="cfg_cs")

        new_ru = st.text_input("URL do app (para redirect OAuth)", value=ru, placeholder="https://seu-app.streamlit.app", key="cfg_ru")

        if st.button("💾 Salvar credenciais Google", key="save_google_creds"):
            ok, msg = salvar_configuracoes({
                "google_client_id": new_cid,
                "google_client_secret": new_cs,
                "app_url": new_ru,
            })
            (st.success if ok else st.error)(msg)

        st.markdown("---")

        if "sheets_creds" in st.session_state:
            st.success("✅ Conta Google conectada!", icon="✅")
            if st.button("🔓 Desconectar conta Google", key="disc_google"):
                st.session_state.pop("sheets_creds", None)
                st.session_state.pop("sheets_lista", None)
                st.session_state.pop("sheets_selected_id", None)
                st.session_state.pop("sheets_selected_name", None)
                st.session_state.pop("sheets_abas", None)
                # Remove also from DB
                salvar_configuracoes({"google_sheets_creds": None})
                st.rerun()
        else:
            if new_cid and new_cs:
                url = gerar_url_auth(new_cid, new_ru)
                st.link_button("🔗 Conectar conta Google", url, use_container_width=True)
            else:
                st.info("Preencha o Client ID e Secret acima para conectar sua conta Google.", icon="ℹ️")

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

    st.markdown('<div class="page-title">👑 Painel Admin</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Gerencie os usuários da plataforma</div>', unsafe_allow_html=True)

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
        st.markdown(
            '<div style="text-align:center;padding:1.2rem 0 0.5rem;">'
            '<span style="font-size:2rem;">⚡</span><br>'
            '<span style="font-size:1.2rem;font-weight:700;color:#00D97E;">Prospec-o-Ativa</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        user = st.session_state.get("user", {})
        st.caption(f"👤 {user.get('email','')}")
        role_badge = "👑 Admin" if user.get("role") == "admin" else "🙂 Usuário"
        st.caption(role_badge)
        st.markdown("---")

        page = st.session_state.get("page", "busca")

        if st.button("🔍 Busca", use_container_width=True, key="nav_busca",
                     type="primary" if page == "busca" else "secondary"):
            st.session_state["page"] = "busca"; st.rerun()

        if st.button("📁 Histórico", use_container_width=True, key="nav_hist",
                     type="primary" if page == "historico" else "secondary"):
            st.session_state["page"] = "historico"; st.rerun()

        if st.button("⚙️ Configurações", use_container_width=True, key="nav_cfg",
                     type="primary" if page == "configuracoes" else "secondary"):
            st.session_state["page"] = "configuracoes"; st.rerun()

        if eh_admin():
            if st.button("👑 Admin", use_container_width=True, key="nav_admin",
                         type="primary" if page == "admin" else "secondary"):
                st.session_state["page"] = "admin"; st.rerun()

        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True, key="nav_logout"):
            logout()
            st.rerun()


def main():
    from modules.auth import usuario_logado, eh_admin, supabase_configurado

    if not supabase_configurado():
        st.error(
            "⚠️ **Supabase não configurado.**\n\n"
            "Adicione `SUPABASE_URL` e `SUPABASE_ANON_KEY` nos segredos do Streamlit "
            "(Settings → Secrets) ou no arquivo `.env`.",
            icon="🔒",
        )
        st.stop()

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
