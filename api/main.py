"""
API de provisionamento de usuários — Lead Extractor by Revolução AI.

Serviço HTTP independente do app Streamlit principal, usado por sistemas
externos (landing pages, checkouts, automações de venda) para criar
usuários programaticamente após uma compra.

Compartilha o mesmo projeto Supabase do app Streamlit — um usuário criado
por aqui já consegue logar normalmente na plataforma.

Variáveis de ambiente necessárias:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
  SIGNUP_API_KEY   — chave secreta que o sistema externo envia no header X-API-Key
"""

import os
from datetime import date
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field
from supabase import create_client, Client

app = FastAPI(title="Lead Extractor — API de Provisionamento de Usuários")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
SIGNUP_API_KEY = os.environ["SIGNUP_API_KEY"]

_sb: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


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


@app.get("/health")
def health():
    return {"status": "ok"}
