"""
API de provisionamento de usuários — Lead Extractor by Revolução AI.

Serviço HTTP independente do app Streamlit principal, usado por sistemas
externos (landing pages, checkouts, automações de venda) para criar
usuários programaticamente após uma compra.

Compartilha o mesmo projeto Supabase do app Streamlit — um usuário criado
por aqui já consegue logar normalmente na plataforma.

Também expõe um segundo recurso, independente do primeiro: um protótipo de
enriquecimento de leads por e-mail/telefone (ver lead_enrichment.py),
admin-only, acionado via webhook — com um painel visual próprio em
GET /painel (HTML, protegido por HTTP Basic Auth com ENRICH_API_KEY como
senha), separado da interface do app Streamlit principal de propósito.

Variáveis de ambiente necessárias:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
  SIGNUP_API_KEY   — chave secreta que o sistema externo envia no header X-API-Key (endpoint /users)
  ENRICH_API_KEY   — chave secreta separada para o endpoint /enrich/lead e pro painel /painel
                     (você mesmo inventa um valor — é só uma senha pra proteger esses recursos,
                     igual a SIGNUP_API_KEY). No painel, o usuário do login HTTP Basic pode ser
                     qualquer coisa — só a senha precisa bater com essa chave.
  CDD_API_KEY      — mesma chave da Casa dos Dados já usada no app principal (copie o mesmo
                     valor pra cá — é uma variável de ambiente só, nunca fica no Supabase)
  OPENAI_API_KEY   — opcional, habilita o fallback de IA (gpt-5-mini) quando e-mail/telefone
                     não encontram nada
  ENRICH_ADMIN_EMAIL — opcional. A chave do Google Maps NÃO precisa de variável de ambiente
                     própria — é lida direto do Supabase, da conta do admin já configurada no
                     app principal. Se houver mais de um usuário admin, informe aqui qual
                     e-mail usar; se deixar em branco, usa o primeiro admin encontrado.
  MAPS_API_KEY_ENRICH — opcional. Só defina isso se quiser uma chave Maps SEPARADA/isolada só
                     pra esse protótipo, em vez de reaproveitar a do admin — tem prioridade
                     sobre a busca automática acima quando definida.
  ENRICH_API_URL   — opcional. URL pública deste próprio serviço (ex:
                     https://seu-servico.up.railway.app) — usada só pra exibir o endpoint
                     completo no painel /painel. Sem ela, o painel mostra um placeholder.
"""

import logging
import os
import secrets as _secrets_mod
from datetime import date, datetime, timezone
from typing import Optional
from urllib.parse import quote as _url_quote

import requests
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, EmailStr, Field
from supabase import create_client, Client

import lead_enrichment
import panel_html

logger = logging.getLogger(__name__)

app = FastAPI(title="Lead Extractor — API de Provisionamento de Usuários")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
SIGNUP_API_KEY = os.environ["SIGNUP_API_KEY"]

# Recurso de enriquecimento — variáveis opcionais (o endpoint fica desativado,
# com erro claro, se ENRICH_API_KEY não estiver configurada; CDD/Maps/IA
# individualmente ausentes só desativam aquele passo específico do pipeline).
ENRICH_API_KEY       = os.getenv("ENRICH_API_KEY", "")
ENRICH_CDD_API_KEY   = os.getenv("CDD_API_KEY", "")
ENRICH_MAPS_API_KEY_OVERRIDE = os.getenv("MAPS_API_KEY_ENRICH", "")
ENRICH_OPENAI_KEY    = os.getenv("OPENAI_API_KEY", "")
ENRICH_ADMIN_EMAIL   = os.getenv("ENRICH_ADMIN_EMAIL", "")
ENRICH_API_URL       = os.getenv("ENRICH_API_URL", "")

_sb: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

_painel_auth = HTTPBasic()


def _verificar_painel_auth(credentials: HTTPBasicCredentials = Depends(_painel_auth)) -> None:
    if not ENRICH_API_KEY:
        raise HTTPException(status_code=503, detail="Painel não configurado (ENRICH_API_KEY ausente).")
    # Usuário do login HTTP Basic pode ser qualquer coisa — só a senha
    # precisa bater com ENRICH_API_KEY. Comparação em tempo constante,
    # mesma prática usada em qualquer checagem de segredo.
    if not _secrets_mod.compare_digest(credentials.password, ENRICH_API_KEY):
        raise HTTPException(
            status_code=401, detail="Credenciais inválidas.",
            headers={"WWW-Authenticate": "Basic"},
        )


class CriarUsuarioRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = Field(default="user", pattern="^(user|admin)$")

    # Créditos de busca CNPJ (Casa dos Dados)
    cdd_credits: int = Field(default=0, ge=0, description="Saldo inicial de créditos CNPJ")
    monthly_cdd_credits: int = Field(default=0, ge=0, description="Renovação mensal automática (0 = sem renovação)")

    # Créditos de busca Google Maps — usando chave/pool da plataforma
    maps_credits_enabled: bool = Field(default=False, description="Se True, usuário usa créditos/chave da plataforma em vez de cadastrar chave própria")
    maps_credits: int = Field(default=0, ge=0)
    monthly_maps_credits: int = Field(default=0, ge=0)

    # Instagram (via Apify)
    instagram_visible: bool = Field(default=True, description="Se a aba Instagram aparece para o usuário")
    instagram_credits_enabled: bool = Field(default=False, description="Se True, usuário usa a chave Apify da plataforma")
    instagram_credits: int = Field(default=0, ge=0)
    monthly_instagram_credits: int = Field(default=0, ge=0)

    # Disparos (WhatsApp)
    disparo_habilitado: bool = Field(default=False, description="Se True, o usuário vê e pode usar a página de Disparos WhatsApp. Desativado por padrão — libere manualmente pelo Admin ou aqui na criação.")


class CriarUsuarioResponse(BaseModel):
    success: bool
    user_id: str
    email: str
    message: str


def _verificar_api_key(x_api_key: Optional[str]) -> None:
    if not x_api_key or x_api_key != SIGNUP_API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida ou ausente.")


@app.post("/users", status_code=201, response_model=CriarUsuarioResponse)
def criar_usuario(payload: CriarUsuarioRequest, x_api_key: Optional[str] = Header(default=None)):
    _verificar_api_key(x_api_key)

    try:
        resp = _sb.auth.admin.create_user({
            "email":         payload.email,
            "password":      payload.password,
            "email_confirm": True,
            "user_metadata": {"role": payload.role},
        })
    except Exception as e:
        msg = str(e)
        if "already been registered" in msg or "already exists" in msg:
            raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado.")
        raise HTTPException(status_code=500, detail=f"Erro ao criar usuário: {msg}")

    user_id = resp.user.id

    profile = {
        "id":                         user_id,
        "email":                      payload.email,
        "role":                       payload.role,
        "cdd_credits":                payload.cdd_credits,
        "monthly_cdd_credits":        payload.monthly_cdd_credits,
        "maps_credits_enabled":       payload.maps_credits_enabled,
        "maps_credits":               payload.maps_credits,
        "monthly_maps_credits":       payload.monthly_maps_credits,
        "instagram_visible":          payload.instagram_visible,
        "instagram_credits_enabled":  payload.instagram_credits_enabled,
        "instagram_credits":          payload.instagram_credits,
        "monthly_instagram_credits":  payload.monthly_instagram_credits,
        "disparo_habilitado":         payload.disparo_habilitado,
        "credits_renewed_at":         date.today().isoformat(),
    }

    try:
        _sb.table("profiles").upsert(profile).execute()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Usuário foi criado (id={user_id}) mas houve falha ao configurar o perfil: {e}",
        )

    return CriarUsuarioResponse(
        success=True,
        user_id=user_id,
        email=payload.email,
        message="Usuário criado com sucesso.",
    )


# ── Enriquecimento de leads (protótipo, admin-only, acionado via webhook) ──

class EnriquecerLeadRequest(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    webhook_destino: Optional[str] = Field(
        default=None,
        description="URL opcional pra onde o resultado é reenviado via POST quando o processamento terminar.",
    )


class EnriquecerLeadResponse(BaseModel):
    id: str
    status: str
    message: str


def _verificar_enrich_api_key(x_api_key: Optional[str]) -> None:
    if not ENRICH_API_KEY:
        raise HTTPException(status_code=503, detail="Recurso de enriquecimento não configurado (ENRICH_API_KEY ausente).")
    if not x_api_key or x_api_key != ENRICH_API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida ou ausente.")


def _processar_enriquecimento(enrichment_id: str, nome: str, email: str, telefone: str, webhook_destino: Optional[str]) -> None:
    """Roda em background — chamado depois da resposta HTTP já ter sido enviada."""
    try:
        _sb.table("lead_enrichments").update({"status": "processando"}).eq("id", enrichment_id).execute()

        maps_key = ENRICH_MAPS_API_KEY_OVERRIDE or lead_enrichment.obter_maps_key_admin(_sb, ENRICH_ADMIN_EMAIL)

        resultado = lead_enrichment.enriquecer_lead(
            nome=nome, email=email, telefone=telefone,
            cdd_api_key=ENRICH_CDD_API_KEY, maps_api_key=maps_key,
            openai_api_key=ENRICH_OPENAI_KEY, sb=_sb,
        )

        atualizacao = {
            "status":             resultado["status"],
            "metodo_encontrado":  resultado["metodo_encontrado"],
            "empresa_nome":       resultado["empresa_nome"],
            "cnpj":               resultado["cnpj"],
            "endereco":           resultado["endereco"],
            "municipio":          resultado["municipio"],
            "uf":                 resultado["uf"],
            "website":            resultado["website"],
            "maps_url":           resultado["maps_url"],
            "avaliacao":          resultado["avaliacao"],
            "total_avaliacoes":   resultado["total_avaliacoes"],
            "dados_brutos":       resultado,
            "erro":               resultado.get("erro"),
            "concluido_em":       datetime.now(timezone.utc).isoformat(),
        }
        _sb.table("lead_enrichments").update(atualizacao).eq("id", enrichment_id).execute()

        if webhook_destino:
            _enviar_webhook_destino(enrichment_id, webhook_destino, {
                "id": enrichment_id, "nome_lead": nome, "email": email, "telefone": telefone,
                **{k: v for k, v in resultado.items()},
            })
    except Exception as e:
        logger.exception("Erro ao processar enriquecimento %s", enrichment_id)
        try:
            _sb.table("lead_enrichments").update({
                "status": "erro", "erro": str(e)[:500],
                "concluido_em": datetime.now(timezone.utc).isoformat(),
            }).eq("id", enrichment_id).execute()
        except Exception:
            pass


def _enviar_webhook_destino(enrichment_id: str, url: str, payload: dict) -> None:
    try:
        resp = requests.post(url, json=payload, timeout=15)
        ok = resp.ok
    except Exception as e:
        logger.warning("Falha ao reenviar webhook de destino (enrichment=%s): %s", enrichment_id, e)
        ok = False
    if ok:
        try:
            _sb.table("lead_enrichments").update({"webhook_destino_enviado": True}).eq("id", enrichment_id).execute()
        except Exception:
            pass


@app.post("/enrich/lead", status_code=202, response_model=EnriquecerLeadResponse)
def criar_enriquecimento_lead(
    payload: EnriquecerLeadRequest,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(default=None),
):
    _verificar_enrich_api_key(x_api_key)

    if not payload.email and not payload.telefone:
        raise HTTPException(status_code=400, detail="Informe ao menos email ou telefone.")

    try:
        resp = _sb.table("lead_enrichments").insert({
            "nome_lead": payload.nome, "email": payload.email, "telefone": payload.telefone,
            "status": "pendente", "webhook_destino": payload.webhook_destino,
            "origem_payload": payload.model_dump(),
        }).execute()
        enrichment_id = resp.data[0]["id"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao registrar requisição: {e}")

    background_tasks.add_task(
        _processar_enriquecimento, enrichment_id,
        payload.nome or "", payload.email or "", payload.telefone or "",
        payload.webhook_destino,
    )

    return EnriquecerLeadResponse(
        id=enrichment_id, status="pendente",
        message="Recebido — processando em background. Consulte o resultado pelo id, ou configure webhook_destino pra receber quando terminar.",
    )


# ── Painel visual (HTML, admin-only via HTTP Basic Auth) ───────────────────
# Rota separada de propósito — não faz parte da interface do app Streamlit
# principal, é uma tela à parte só pra esse protótipo.

def _carregar_dados_painel() -> tuple[list[dict], list[dict]]:
    try:
        webhooks = (_sb.table("enrichment_webhooks").select("*").order("criado_em").execute().data or [])
    except Exception as e:
        logger.warning("Falha ao listar webhooks: %s", e)
        webhooks = []
    try:
        historico = (_sb.table("lead_enrichments").select("*").order("criado_em", desc=True).limit(50).execute().data or [])
    except Exception as e:
        logger.warning("Falha ao listar histórico: %s", e)
        historico = []
    return webhooks, historico


@app.get("/painel", response_class=HTMLResponse)
def painel(msg: str = "", tipo: str = "ok", _auth: None = Depends(_verificar_painel_auth)):
    webhooks, historico = _carregar_dados_painel()
    return panel_html.render_painel(
        endpoint_url=ENRICH_API_URL, enrich_key=ENRICH_API_KEY,
        webhooks=webhooks, historico=historico,
        mensagem=msg, mensagem_tipo=tipo,
    )


@app.post("/painel/testar")
def painel_testar(
    nome: str = Form(""), email: str = Form(""), telefone: str = Form(""),
    webhook_destino: str = Form(""),
    _auth: None = Depends(_verificar_painel_auth),
):
    if not email.strip() and not telefone.strip():
        return RedirectResponse("/painel?tipo=err&msg=Informe+e-mail+ou+telefone.", status_code=303)

    maps_key = ENRICH_MAPS_API_KEY_OVERRIDE or lead_enrichment.obter_maps_key_admin(_sb, ENRICH_ADMIN_EMAIL)
    try:
        resultado = lead_enrichment.enriquecer_lead(
            nome=nome.strip(), email=email.strip(), telefone=telefone.strip(),
            cdd_api_key=ENRICH_CDD_API_KEY, maps_api_key=maps_key,
            openai_api_key=ENRICH_OPENAI_KEY, sb=_sb,
        )
        _sb.table("lead_enrichments").insert({
            "nome_lead": nome or None, "email": email or None, "telefone": telefone or None,
            "webhook_destino": webhook_destino or None,
            "origem_payload": {"nome": nome, "email": email, "telefone": telefone, "via": "painel"},
            "status": resultado["status"], "metodo_encontrado": resultado["metodo_encontrado"],
            "empresa_nome": resultado["empresa_nome"], "cnpj": resultado["cnpj"],
            "endereco": resultado["endereco"], "municipio": resultado["municipio"], "uf": resultado["uf"],
            "website": resultado["website"], "maps_url": resultado["maps_url"],
            "avaliacao": resultado["avaliacao"], "total_avaliacoes": resultado["total_avaliacoes"],
            "dados_brutos": resultado, "concluido_em": datetime.now(timezone.utc).isoformat(),
        }).execute()
        if webhook_destino:
            _enviar_webhook_destino("painel", webhook_destino, {"nome_lead": nome, "email": email, "telefone": telefone, **resultado})
        msg = f"Concluído — {resultado['empresa_nome'] or 'nada encontrado'} ({resultado['status']})"
        return RedirectResponse(f"/painel?msg={_url_quote(msg)}", status_code=303)
    except Exception as e:
        logger.exception("Erro no teste manual do painel")
        return RedirectResponse(f"/painel?tipo=err&msg={_url_quote('Erro: ' + str(e)[:200])}", status_code=303)


@app.post("/painel/webhooks")
def painel_criar_webhook(nome: str = Form(...), url: str = Form(...), _auth: None = Depends(_verificar_painel_auth)):
    try:
        _sb.table("enrichment_webhooks").insert({"nome": nome.strip(), "url": url.strip()}).execute()
        return RedirectResponse("/painel?msg=Webhook+salvo.", status_code=303)
    except Exception as e:
        logger.exception("Erro ao salvar webhook")
        return RedirectResponse(f"/painel?tipo=err&msg={_url_quote('Erro ao salvar: ' + str(e)[:200])}", status_code=303)


@app.post("/painel/webhooks/{webhook_id}/deletar")
def painel_deletar_webhook(webhook_id: str, _auth: None = Depends(_verificar_painel_auth)):
    try:
        _sb.table("enrichment_webhooks").delete().eq("id", webhook_id).execute()
        return RedirectResponse("/painel?msg=Webhook+removido.", status_code=303)
    except Exception as e:
        logger.exception("Erro ao remover webhook")
        return RedirectResponse(f"/painel?tipo=err&msg={_url_quote('Erro ao remover: ' + str(e)[:200])}", status_code=303)


@app.get("/health")
def health():
    return {"status": "ok"}
