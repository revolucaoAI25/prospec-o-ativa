"""
Módulo de autenticação via Supabase.

Gerencia login, logout e sessão de usuários.
Supabase cuida do hash de senhas, tokens JWT e refresh automático.
"""

import os
import streamlit as st
from typing import Optional

try:
    from supabase import create_client, Client
    _SUPABASE_OK = True
except ImportError:
    _SUPABASE_OK = False


def _get_secret(key: str) -> str:
    try:
        v = st.secrets.get(key, "")
        if v:
            return str(v).strip()
    except Exception:
        pass
    return os.getenv(key, "").strip()


def supabase_configurado() -> bool:
    return bool(_get_secret("SUPABASE_URL") and _get_secret("SUPABASE_ANON_KEY"))


def _client() -> Optional["Client"]:
    """Retorna cliente Supabase padrão (anon key)."""
    if not _SUPABASE_OK:
        return None
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_ANON_KEY")
    if not url or not key:
        return None
    return create_client(url, key)


def _admin_client() -> Optional["Client"]:
    """Retorna cliente Supabase com service role (para operações de admin)."""
    if not _SUPABASE_OK:
        return None
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)


# ── Autenticação ──────────────────────────────────────────────────────────────

# ── Persistência de sessão via cookie ────────────────────────────────────────
# LEITURA : st.context.cookies — nativo Streamlit ≥1.37, zero componente,
#            zero rerun extra. Lê o cookie do header HTTP da requisição inicial.
# ESCRITA : extra-streamlit-components CookieManager — provadamente funciona.
#            MAS é renderizado SOMENTE quando há algo para escrever/apagar
#            (login / logout / renovação pós-restore). Durante navegação normal
#            o CookieManager NUNCA é renderizado → transições rápidas.
#
# Mecanismo: salvar_sessao_cookie() apenas seta um flag "_pending_rt" em
# session_state. O main() de app.py lê esse flag e renderiza o CookieManager
# uma única vez para efetivar a escrita.

_COOKIE_NAME = "le_rt"


def salvar_sessao_cookie(refresh_token: str):
    """Marca o refresh token como pendente de escrita no cookie.
    A escrita real ocorre em main() via CookieManager (uma vez)."""
    if refresh_token and st.session_state.get("_cookie_set") != refresh_token:
        st.session_state["_pending_rt"] = refresh_token


def limpar_cookie():
    """Marca o cookie para deleção no próximo render de main()."""
    st.session_state["_do_logout_cookie"] = True
    st.session_state.pop("_pending_rt", None)
    st.session_state.pop("_cookie_set", None)


def _carregar_sheets_state(raw):
    """Carrega sheets_creds, sheets_planilhas e auto_export_enabled do campo JSONB."""
    if not raw:
        return
    if isinstance(raw, dict) and "oauth" in raw:
        st.session_state["sheets_creds"]        = raw["oauth"]
        st.session_state["sheets_planilhas"]    = raw.get("planilhas", [])
        st.session_state["auto_export_enabled"] = raw.get("auto_export", False)
    else:
        # Formato antigo (só dict OAuth)
        st.session_state["sheets_creds"]        = raw
        st.session_state["sheets_planilhas"]    = []
        st.session_state["auto_export_enabled"] = False


def restaurar_sessao(refresh_token: str) -> bool:
    """
    Restaura sessão a partir do refresh token fornecido pelo CookieManager.
    O token é lido via JavaScript (document.cookie) — funciona no Community Cloud.
    """
    if "user" in st.session_state:
        return True
    if not refresh_token:
        return False
    sb = _client()
    if not sb:
        return False
    try:
        resp = sb.auth.refresh_session(refresh_token)
        if not resp or not resp.user or not resp.session:
            return False
        user = resp.user
        sess = resp.session
        perfil = sb.table("profiles").select(
            "role, google_maps_api_key, google_sheets_creds"
        ).eq("id", user.id).single().execute()
        dados = perfil.data or {}
        st.session_state["user"] = {
            "id":            user.id,
            "email":         user.email,
            "role":          dados.get("role", "user"),
            "access_token":  sess.access_token,
            "refresh_token": sess.refresh_token,
        }
        if dados.get("google_maps_api_key"):
            st.session_state["user_gmaps_key"] = dados["google_maps_api_key"]
        _carregar_sheets_state(dados.get("google_sheets_creds"))
        salvar_sessao_cookie(sess.refresh_token)
        return True
    except Exception:
        return False


def login(email: str, senha: str) -> tuple[bool, str]:
    """
    Autentica o usuário com email e senha.
    Armazena dados na session_state em caso de sucesso.
    Retorna (sucesso, mensagem).
    """
    sb = _client()
    if not sb:
        return False, "Supabase não configurado. Verifique as variáveis SUPABASE_URL e SUPABASE_ANON_KEY."

    try:
        resp = sb.auth.sign_in_with_password({"email": email.strip(), "password": senha})
        user = resp.user
        sess = resp.session

        # Busca perfil (role)
        perfil = sb.table("profiles").select("role, google_maps_api_key, google_client_id, google_client_secret, google_sheets_creds, app_url").eq("id", user.id).single().execute()
        dados = perfil.data or {}

        st.session_state["user"] = {
            "id":            user.id,
            "email":         user.email,
            "role":          dados.get("role", "user"),
            "access_token":  sess.access_token,
            "refresh_token": sess.refresh_token,
        }
        if dados.get("google_maps_api_key"):
            st.session_state["user_gmaps_key"] = dados["google_maps_api_key"]
        _carregar_sheets_state(dados.get("google_sheets_creds"))
        salvar_sessao_cookie(sess.refresh_token)
        return True, "Login realizado com sucesso."

    except Exception as e:
        msg = str(e)
        if "Invalid login credentials" in msg:
            return False, "E-mail ou senha incorretos."
        if "Email not confirmed" in msg:
            return False, "E-mail não confirmado. Contate o administrador."
        return False, f"Erro ao autenticar: {msg}"


def logout():
    """Remove sessão do state e apaga o cookie."""
    limpar_cookie()
    for k in ["user", "user_gmaps_key", "sheets_creds", "sheets_planilhas",
              "auto_export_enabled", "sheets_lista",
              "maps_res", "rf_res", "page", "_cfg_cache", "_cookie_set",
              "_pesquisas_cache", "_sb_client", "_cm_init_done"]:
        st.session_state.pop(k, None)


def usuario_logado() -> Optional[dict]:
    return st.session_state.get("user")


def eh_admin() -> bool:
    u = usuario_logado()
    return bool(u and u.get("role") == "admin")


# ── Gestão de usuários (somente admin) ───────────────────────────────────────

def listar_usuarios() -> tuple[bool, list, str]:
    """Retorna (sucesso, lista_usuarios, erro)."""
    sb = _admin_client()
    if not sb:
        return False, [], "SUPABASE_SERVICE_ROLE_KEY não configurado."
    try:
        resp = sb.table("user_stats").select("*").order("created_at", desc=True).execute()
        return True, resp.data or [], ""
    except Exception as e:
        return False, [], str(e)


def criar_usuario(email: str, senha: str, role: str = "user") -> tuple[bool, str]:
    """Cria novo usuário. Retorna (sucesso, mensagem)."""
    sb = _admin_client()
    if not sb:
        return False, "SUPABASE_SERVICE_ROLE_KEY não configurado."
    try:
        resp = sb.auth.admin.create_user({
            "email":          email.strip(),
            "password":       senha,
            "email_confirm":  True,
            "user_metadata":  {"role": role},
        })
        user_id = resp.user.id
        # Garante que o perfil exista com o role correto
        sb.table("profiles").upsert({
            "id":    user_id,
            "email": email.strip(),
            "role":  role,
        }).execute()
        return True, f"Usuário **{email}** criado com sucesso."
    except Exception as e:
        msg = str(e)
        if "already been registered" in msg or "already exists" in msg:
            return False, "Este e-mail já está cadastrado."
        return False, f"Erro ao criar usuário: {msg}"


def deletar_usuario(user_id: str) -> tuple[bool, str]:
    """Remove usuário e todos os seus dados."""
    sb = _admin_client()
    if not sb:
        return False, "SUPABASE_SERVICE_ROLE_KEY não configurado."
    try:
        sb.auth.admin.delete_user(user_id)
        return True, "Usuário removido com sucesso."
    except Exception as e:
        return False, f"Erro ao remover usuário: {e}"


def alterar_role(user_id: str, novo_role: str) -> tuple[bool, str]:
    """Altera o papel (role) de um usuário."""
    sb = _admin_client()
    if not sb:
        return False, "SUPABASE_SERVICE_ROLE_KEY não configurado."
    try:
        sb.table("profiles").update({"role": novo_role}).eq("id", user_id).execute()
        return True, "Papel atualizado."
    except Exception as e:
        return False, str(e)


def redefinir_senha(user_id: str, nova_senha: str) -> tuple[bool, str]:
    sb = _admin_client()
    if not sb:
        return False, "SUPABASE_SERVICE_ROLE_KEY não configurado."
    try:
        sb.auth.admin.update_user_by_id(user_id, {"password": nova_senha})
        return True, "Senha redefinida com sucesso."
    except Exception as e:
        return False, str(e)
