"""
Integração com a API da Casa dos Dados (casadosdados.com.br).

Endpoint: POST https://api.casadosdados.com.br/v5/cnpj/pesquisa
Auth:     header  api-key: <CDD_API_KEY>

Configuração necessária (Streamlit Secrets):
  CDD_API_KEY = "sua_chave_aqui"
"""

from __future__ import annotations

import json
import logging
import requests

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.casadosdados.com.br/v5/cnpj/pesquisa"
_MAX_POR_PAGINA = 1000  # limite máximo aceito pela API por requisição


# ──────────────────────────────────────────────────────────────────────────────
# Função principal
# ──────────────────────────────────────────────────────────────────────────────

def buscar(
    api_key: str,
    cnaes: list[str],
    uf: str | list[str],
    municipio: str | list[str] = "",
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
    cnae_tipo: str = "principal",
    busca_textual: list | None = None,
    situacoes_cadastrais: list | None = None,
    dedup_raiz: bool = False,
    stats: dict | None = None,
) -> list[dict]:
    """
    Busca empresas na API da Casa dos Dados com filtros avançados.

    Parâmetros:
        api_key             — chave de API (CDD_API_KEY)
        cnaes               — lista de códigos CNAE principal (ex: ["6911701"])
        uf                  — sigla do estado (ex: "SP") ou lista de siglas (ex: ["SP","RJ"])
        municipio           — nome do município (ex: "São Paulo") ou lista de nomes — opcional
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
        stats               — dict opcional preenchido in-place com
                              {"total_api": N} (total de empresas que batem
                              com o filtro na Receita Federal, segundo a
                              própria API) — usado pra avisar o usuário
                              quando um filtro já está saturado, sem quebrar
                              quem chama buscar() sem passar esse parâmetro.
    """
    resultados: list[dict] = []
    pagina = 1
    total_api = None  # preenchido após 1ª resposta

    while len(resultados) < limite:
        por_pagina = min(_MAX_POR_PAGINA, limite - len(resultados) + 50)  # pega um pouco a mais para compensar deduplicação
        por_pagina = min(por_pagina, _MAX_POR_PAGINA)

        body = _montar_body(
            cnaes=cnaes,
            cnae_tipo=cnae_tipo,
            busca_textual=busca_textual,
            situacoes_cadastrais=situacoes_cadastrais,
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

        if pagina == 1:
            logger.debug("CDD request body: %s", json.dumps(body, ensure_ascii=False))

        try:
            resp = requests.post(
                _ENDPOINT,
                params={"tipo_resultado": "completo"},
                headers={"Content-Type": "application/json", "api-key": api_key},
                json=body,
                timeout=30,
            )
            if not resp.ok:
                logger.warning("CDD HTTP %s: %s", resp.status_code, resp.text[:500])
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
            if pagina == 1:
                logger.debug("CDD total na API: %s", total_api)

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

    if dedup_raiz:
        seen_raiz: set = set()
        deduped: list[dict] = []
        for r in resultados:
            raiz = (r.get("cnpj") or "")[:8]
            if raiz and raiz in seen_raiz:
                continue
            if raiz:
                seen_raiz.add(raiz)
            deduped.append(r)
        resultados = deduped

    if stats is not None:
        stats["total_api"] = total_api or 0

    return resultados[:limite]


# ──────────────────────────────────────────────────────────────────────────────
# Montagem do body da requisição
# ──────────────────────────────────────────────────────────────────────────────

def _to_list(v) -> list:
    """Normaliza um valor único ou lista para lista, removendo vazios."""
    if v is None:
        return []
    if isinstance(v, list):
        return [x for x in v if x]
    return [v] if v else []


def _montar_body(
    cnaes, uf, municipio, porte, matriz_filial,
    simples_optante, excluir_simples, mei_optante, excluir_mei,
    com_telefone, com_email, somente_celular, somente_fixo, excluir_email_contab,
    data_abertura_inicio, data_abertura_fim,
    capital_min, capital_max,
    limite_pagina, pagina,
    cnae_tipo: str = "principal",
    busca_textual: list | None = None,
    situacoes_cadastrais: list | None = None,
) -> dict:
    body: dict = {
        "situacao_cadastral": situacoes_cadastrais or ["ATIVA"],
        "limite": limite_pagina,
        "pagina": pagina,
    }

    if busca_textual:
        body["busca_textual"] = busca_textual

    if cnaes:
        _cnaes_limpos = [c.replace("-", "").replace("/", "").replace(".", "") for c in cnaes]
        if cnae_tipo in ("principal", "ambos"):
            body["codigo_atividade_principal"] = _cnaes_limpos
        if cnae_tipo in ("secundario", "ambos"):
            body["codigo_atividade_secundaria"] = _cnaes_limpos

    _ufs = _to_list(uf)
    if _ufs:
        body["uf"] = [u.lower() for u in _ufs]

    _municipios = _to_list(municipio)
    if _municipios:
        # API aceita sem acentos em minúsculas
        body["municipio"] = [_normalizar_municipio(m) for m in _municipios]

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

    # Telefones — API v5 retorna em "contato_telefonico": [{ddd, numero, completo, tipo}]
    tels = item.get("contato_telefonico") or []
    tel1 = _fmt_telefone_cdd(tels[0]) if len(tels) > 0 else ""
    tel2 = _fmt_telefone_cdd(tels[1]) if len(tels) > 1 else ""

    # E-mail — API v5 retorna em "contato_email": [{email, valido, dominio}]
    emails = item.get("contato_email") or []
    email = emails[0].get("email", "") if emails else ""

    # CNAE descrição para nicho_busca
    ativ = item.get("atividade_principal") or {}
    if isinstance(ativ, list):
        ativ = ativ[0] if ativ else {}
    nicho = ativ.get("descricao", "") if isinstance(ativ, dict) else ""
    cnae_codigo = ativ.get("codigo", "") if isinstance(ativ, dict) else ""

    porte_obj = item.get("porte_empresa") or {}
    porte_desc = porte_obj.get("descricao", "") if isinstance(porte_obj, dict) else ""

    # Data de abertura — remove a parte de horário
    data_abertura_raw = item.get("data_abertura") or ""
    data_abertura = str(data_abertura_raw)[:10] if data_abertura_raw else ""

    # Sócio principal
    qsa = item.get("quadro_societario") or []
    socio_principal = qsa[0].get("nome", "") if qsa else ""

    # Tipo do primeiro telefone
    tipo_telefone = tels[0].get("tipo", "") if tels else ""

    # Simples / MEI
    simples_obj = item.get("simples") or {}
    mei_obj = item.get("mei") or {}
    simples_optante = "Sim" if simples_obj.get("optante") else "Não"
    mei_optante = "Sim" if mei_obj.get("optante") else "Não"

    # Situação especial (ex: "EM RECUPERACAO JUDICIAL")
    sit_esp = item.get("situacao_especial") or {}
    if isinstance(sit_esp, dict):
        situacao_especial = sit_esp.get("descricao", "") or ""
    else:
        situacao_especial = str(sit_esp) if sit_esp else ""

    return {
        "nome":             nome,
        "cnpj":             item.get("cnpj", ""),
        "telefone":         tel1,
        "telefone2":        tel2,
        "tipo_telefone":    tipo_telefone,
        "email":            email,
        "endereco":         endereco,
        "municipio":        end.get("municipio", ""),
        "uf":               end.get("uf", "").upper(),
        "cep":              end.get("cep", ""),
        "site":             "",
        "maps_url":         "",
        "avaliacao":        "",
        "total_avaliacoes": "",
        "nicho_busca":      nicho,
        "cnae_codigo":      cnae_codigo,
        "subnicho_busca":   porte_desc,
        "matriz_filial":    item.get("matriz_filial", ""),
        "natureza_juridica": item.get("descricao_natureza_juridica", ""),
        "data_abertura":    data_abertura,
        "capital_social":   str(item.get("capital_social", "") or ""),
        "simples_optante":  simples_optante,
        "mei_optante":      mei_optante,
        "situacao_especial": situacao_especial,
        "socio_principal":  socio_principal,
        "cidade_busca":     end.get("municipio", ""),
        "estado_busca":     end.get("uf", "").upper(),
        "fonte":            "Casa dos Dados",
    }


def _fmt_telefone(t) -> str:
    """Formata telefone para exibição.

    Trata todos os formatos que a API CDD v5 pode retornar:
      - dict com chaves ddd/codigo_ddd + numero/telefone/number
      - string já formatada ou só dígitos
    """
    if not t:
        return ""
    if isinstance(t, dict):
        ddd = str(
            t.get("ddd") or t.get("codigo_ddd") or t.get("ddd_numero") or ""
        ).strip()
        num = str(
            t.get("numero") or t.get("telefone") or t.get("number") or t.get("fone") or ""
        ).strip()
        if not ddd and not num:
            return ""
        if ddd and num:
            return f"({ddd}) {num}"
        return ddd or num
    s = str(t).strip()
    return s


def _fmt_telefone_cdd(t: dict) -> str:
    """Formata entrada de contato_telefonico: {ddd, numero, completo, tipo}."""
    if not t or not isinstance(t, dict):
        return ""
    ddd = str(t.get("ddd") or "").strip()
    num = str(t.get("numero") or "").strip()
    if ddd and num:
        return f"({ddd}) {num}"
    completo = str(t.get("completo") or "").strip()
    return completo


def _apenas_digitos(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def remover_duplicados_lote(leads: list[dict], cnpjs_vistos: set, tels_vistos: set) -> list[dict]:
    """
    Remove leads cujo CNPJ ou telefone (1 ou 2) já apareceu antes — seja no
    histórico (sets pré-populados com o que já foi salvo) ou dentro do
    próprio lote sendo processado. Os sets são atualizados por referência,
    então a mesma chamada pode ser reaplicada depois do enriquecimento com
    Google Maps para pegar duplicatas que só ficaram visíveis quando o
    telefone foi preenchido (a CDD não tinha, o Maps completou).
    """
    unicos: list[dict] = []
    for lead in leads:
        cnpj = lead.get("cnpj", "")
        tel1 = _apenas_digitos(lead.get("telefone", ""))
        tel2 = _apenas_digitos(lead.get("telefone2", ""))

        if cnpj and cnpj in cnpjs_vistos:
            continue
        if (tel1 and tel1 in tels_vistos) or (tel2 and tel2 in tels_vistos):
            continue

        if cnpj:
            cnpjs_vistos.add(cnpj)
        if tel1:
            tels_vistos.add(tel1)
        if tel2:
            tels_vistos.add(tel2)
        unicos.append(lead)
    return unicos


def _normalizar_municipio(m: str) -> str:
    """Converte 'São Paulo' → 'sao paulo' (sem acento, minúsculas)."""
    import unicodedata
    s = unicodedata.normalize("NFD", m.strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()
