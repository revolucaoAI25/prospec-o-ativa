"""
Integração com a API da Casa dos Dados (casadosdados.com.br).

Endpoint: POST https://api.casadosdados.com.br/v5/cnpj/pesquisa
Auth:     header  api-key: <CDD_API_KEY>

Configuração necessária (Streamlit Secrets):
  CDD_API_KEY = "sua_chave_aqui"
"""

from __future__ import annotations

import requests

_ENDPOINT = "https://api.casadosdados.com.br/v5/cnpj/pesquisa"
_MAX_POR_PAGINA = 1000  # limite máximo aceito pela API por requisição


# ──────────────────────────────────────────────────────────────────────────────
# Função principal
# ──────────────────────────────────────────────────────────────────────────────

def buscar(
    api_key: str,
    cnaes: list[str],
    uf: str,
    municipio: str = "",
    porte: list[str] | None = None,
    matriz_filial: str = "",
    simples_optante: bool | None = None,
    excluir_simples: bool = False,
    mei_optante: bool | None = None,
    excluir_mei: bool = False,
    com_telefone: bool = True,
    com_email: bool = False,
    somente_celular: bool = False,
    somente_fixo: bool = False,
    excluir_email_contab: bool = True,
    data_abertura_inicio: str = "",
    data_abertura_fim: str = "",
    capital_min: int | None = None,
    capital_max: int | None = None,
    limite: int = 300,
    exclude_phones: set | None = None,
    exclude_cnpjs: set | None = None,
    callback=None,
) -> list[dict]:
    """
    Busca empresas na API da Casa dos Dados com filtros avançados.

    Parâmetros:
        api_key             — chave de API (CDD_API_KEY)
        cnaes               — lista de códigos CNAE principal (ex: ["6911701"])
        uf                  — sigla do estado (ex: "SP")
        municipio           — nome do município (ex: "São Paulo") — opcional
        porte               — códigos de porte: "01"=Micro, "03"=EPP, "05"=Demais
        matriz_filial       — "MATRIZ", "FILIAL" ou "" (todos)
        simples_optante     — True=apenas Simples Nacional, False=excluir
        excluir_simples     — True=excluir optantes do Simples
        mei_optante         — True=apenas MEI, None=indif
        excluir_mei         — True=excluir MEI
        com_telefone        — apenas empresas com telefone
        com_email           — apenas empresas com e-mail
        somente_celular     — apenas celular
        somente_fixo        — apenas telefone fixo
        excluir_email_contab — remove e-mails de contabilidade
        data_abertura_inicio — "YYYY-MM-DD"
        data_abertura_fim    — "YYYY-MM-DD"
        capital_min/max     — faixa de capital social
        limite              — máx. resultados desejados
        exclude_phones      — set de telefones já salvos (deduplicação)
        exclude_cnpjs       — set de CNPJs já salvos (deduplicação)
        callback            — fn(atual, total, msg) para barra de progresso
    """
    resultados: list[dict] = []
    pagina = 1
    total_api = None  # preenchido após 1ª resposta

    while len(resultados) < limite:
        por_pagina = min(_MAX_POR_PAGINA, limite - len(resultados) + 50)  # pega um pouco a mais para compensar deduplicação
        por_pagina = min(por_pagina, _MAX_POR_PAGINA)

        body = _montar_body(
            cnaes=cnaes,
            uf=uf,
            municipio=municipio,
            porte=porte,
            matriz_filial=matriz_filial,
            simples_optante=simples_optante,
            excluir_simples=excluir_simples,
            mei_optante=mei_optante,
            excluir_mei=excluir_mei,
            com_telefone=com_telefone,
            com_email=com_email,
            somente_celular=somente_celular,
            somente_fixo=somente_fixo,
            excluir_email_contab=excluir_email_contab,
            data_abertura_inicio=data_abertura_inicio,
            data_abertura_fim=data_abertura_fim,
            capital_min=capital_min,
            capital_max=capital_max,
            limite_pagina=por_pagina,
            pagina=pagina,
        )

        try:
            resp = requests.post(
                _ENDPOINT,
                params={"tipo_resultado": "completo"},
                headers={"Content-Type": "application/json", "api-key": api_key},
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "?"
            msg = ""
            try:
                msg = e.response.json().get("message", "") or e.response.text[:200]
            except Exception:
                pass
            raise RuntimeError(f"Erro HTTP {status} na API Casa dos Dados: {msg}") from e
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Erro de conexão com Casa dos Dados: {e}") from e

        itens = data.get("cnpjs", [])
        if total_api is None:
            total_api = data.get("total", 0)

        if not itens:
            break

        for item in itens:
            lead = _mapear_lead(item)

            # Deduplicação
            cnpj = lead.get("cnpj", "")
            if exclude_cnpjs and cnpj and cnpj in exclude_cnpjs:
                continue
            tel1 = lead.get("telefone", "")
            tel2 = lead.get("telefone2", "")
            if exclude_phones:
                digits1 = _apenas_digitos(tel1)
                digits2 = _apenas_digitos(tel2)
                if (digits1 and digits1 in exclude_phones) or (digits2 and digits2 in exclude_phones):
                    continue

            resultados.append(lead)
            if len(resultados) >= limite:
                break

        if callback:
            callback(len(resultados), limite, f"Página {pagina} — {len(resultados)}/{limite} leads…")

        # Verifica se há mais páginas
        obtidos_ate_agora = pagina * por_pagina
        if len(itens) < por_pagina or (total_api and obtidos_ate_agora >= total_api):
            break

        pagina += 1

    return resultados[:limite]


# ──────────────────────────────────────────────────────────────────────────────
# Montagem do body da requisição
# ──────────────────────────────────────────────────────────────────────────────

def _montar_body(
    cnaes, uf, municipio, porte, matriz_filial,
    simples_optante, excluir_simples, mei_optante, excluir_mei,
    com_telefone, com_email, somente_celular, somente_fixo, excluir_email_contab,
    data_abertura_inicio, data_abertura_fim,
    capital_min, capital_max,
    limite_pagina, pagina,
) -> dict:
    body: dict = {
        "situacao_cadastral": ["ATIVA"],
        "limite": limite_pagina,
        "pagina": pagina,
    }

    if cnaes:
        body["codigo_atividade_principal"] = [c.replace("-", "").replace("/", "").replace(".", "") for c in cnaes]

    if uf:
        body["uf"] = [uf.lower()]

    if municipio:
        # API aceita sem acentos em minúsculas
        body["municipio"] = [_normalizar_municipio(municipio)]

    if porte:
        body["porte_empresa"] = {"codigos": porte}

    if matriz_filial in ("MATRIZ", "FILIAL"):
        body["matriz_filial"] = matriz_filial

    # Simples Nacional
    simples_obj: dict = {}
    if simples_optante is True:
        simples_obj["optante"] = True
    if excluir_simples:
        simples_obj["excluir_optante"] = True
    if simples_obj:
        body["simples"] = simples_obj

    # MEI
    mei_obj: dict = {}
    if mei_optante is True:
        mei_obj["optante"] = True
    if excluir_mei:
        mei_obj["excluir_optante"] = True
    if mei_obj:
        body["mei"] = mei_obj

    # Filtros extras
    mais: dict = {}
    if com_telefone:
        mais["com_telefone"] = True
    if com_email:
        mais["com_email"] = True
    if somente_celular:
        mais["somente_celular"] = True
    elif somente_fixo:
        mais["somente_fixo"] = True
    if excluir_email_contab:
        mais["excluir_email_contab"] = True
    if mais:
        body["mais_filtros"] = mais

    # Datas
    data_obj: dict = {}
    if data_abertura_inicio:
        data_obj["inicio"] = data_abertura_inicio
    if data_abertura_fim:
        data_obj["fim"] = data_abertura_fim
    if data_obj:
        body["data_abertura"] = data_obj

    # Capital social
    capital_obj: dict = {}
    if capital_min is not None:
        capital_obj["minimo"] = capital_min
    if capital_max is not None:
        capital_obj["maximo"] = capital_max
    if capital_obj:
        body["capital_social"] = capital_obj

    return body


# ──────────────────────────────────────────────────────────────────────────────
# Mapeamento de campos
# ──────────────────────────────────────────────────────────────────────────────

def _mapear_lead(item: dict) -> dict:
    # Nome: preferir razão social, fallback nome fantasia
    nome = (item.get("razao_social") or item.get("nome_fantasia") or "").strip()

    # Endereço
    end = item.get("endereco") or {}
    partes_end = [
        end.get("tipo_logradouro", ""),
        end.get("logradouro", ""),
        end.get("numero", ""),
        end.get("complemento", ""),
        end.get("bairro", ""),
    ]
    endereco = " ".join(p for p in partes_end if p).strip(", ")

    # Telefones — a API pode retornar lista ou campo único
    telefones = item.get("telefone") or item.get("telefones") or []
    if isinstance(telefones, str):
        telefones = [telefones]
    tel1 = _fmt_telefone(telefones[0]) if len(telefones) > 0 else ""
    tel2 = _fmt_telefone(telefones[1]) if len(telefones) > 1 else ""

    # E-mail
    email = item.get("email") or ""
    if isinstance(email, list):
        email = email[0] if email else ""

    # CNAE descrição para nicho_busca
    ativ = item.get("atividade_principal") or {}
    if isinstance(ativ, list):
        ativ = ativ[0] if ativ else {}
    nicho = ativ.get("descricao", "") if isinstance(ativ, dict) else ""

    porte_obj = item.get("porte_empresa") or {}
    porte_desc = porte_obj.get("descricao", "") if isinstance(porte_obj, dict) else ""

    return {
        "nome":           nome,
        "cnpj":           item.get("cnpj", ""),
        "telefone":       tel1,
        "telefone2":      tel2,
        "email":          email,
        "endereco":       endereco,
        "municipio":      end.get("municipio", ""),
        "uf":             end.get("uf", "").upper(),
        "cep":            end.get("cep", ""),
        "site":           "",
        "maps_url":       "",
        "avaliacao":      "",
        "total_avaliacoes": "",
        "nicho_busca":    nicho,
        "subnicho_busca": porte_desc,
        "cidade_busca":   end.get("municipio", ""),
        "estado_busca":   end.get("uf", "").upper(),
        "fonte":          "Casa dos Dados",
    }


def _fmt_telefone(t) -> str:
    """Formata telefone para exibição."""
    if not t:
        return ""
    if isinstance(t, dict):
        ddd = t.get("ddd", "") or t.get("codigo_ddd", "")
        num = t.get("numero", "") or t.get("telefone", "")
        return f"({ddd}) {num}".strip() if ddd else str(num)
    return str(t).strip()


def _apenas_digitos(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def _normalizar_municipio(m: str) -> str:
    """Converte 'São Paulo' → 'sao paulo' (sem acento, minúsculas)."""
    import unicodedata
    s = unicodedata.normalize("NFD", m.strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()
