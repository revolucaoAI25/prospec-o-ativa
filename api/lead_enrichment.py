"""
Pipeline de enriquecimento de leads por e-mail/telefone — protótipo admin-only.

Módulo AUTOCONTIDO de propósito: este serviço (/api) é deployado separado do
app Streamlit principal (root directory próprio no Railway, requirements.txt
próprio) e não tem acesso a modules/ do app principal. Por isso a lógica de
chamada à Casa dos Dados e ao Google Maps é reimplementada aqui de forma
mínima, em vez de importada — mantém os dois serviços com deploys realmente
independentes (mesma decisão de arquitetura já usada no resto do projeto).

Estratégia (do mais barato/confiável pro mais caro/incerto):
  1. E-mail corporativo → domínio → nome provável da empresa → busca textual
     na Casa dos Dados (razão social / nome fantasia) + confirmação cruzada
     via Google Maps (campo "website" batendo com o domínio do e-mail).
  2. Telefone → tenta o número como texto direto numa Text Search do Maps
     (não é um recurso documentado oficialmente — o Google às vezes indexa
     o telefone na ficha do lugar — mas custa só uma chamada extra, vale a
     tentativa antes de desistir).
  3. IA (OpenAI gpt-5-mini, com a ferramenta de busca na web nativa da
     Responses API) como último recurso, só quando os dois anteriores não
     acharem nada.

Variáveis de ambiente usadas:
  CDD_API_KEY      — mesma chave já usada pelo app principal (Casa dos Dados).
                     Só existe como variável de ambiente lá também — nunca
                     fica guardada no Supabase, por isso precisa ser
                     configurada aqui de novo (copiar o mesmo valor).
  OPENAI_API_KEY   — pro fallback de IA (opcional — se ausente, esse passo é
                     simplesmente pulado). Usa o modelo gpt-5-mini.
  (a chave do Google Maps NÃO é uma variável de ambiente — é lida
  diretamente do Supabase, da conta do admin já configurada no app
  principal — ver obter_maps_key_admin() abaixo)
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Optional

import requests

logger = logging.getLogger(__name__)

CDD_ENDPOINT = "https://api.casadosdados.com.br/v5/cnpj/pesquisa"
PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

# Teto de segurança pra chave Maps dedicada desse protótipo — mesmo espírito
# do teto oculto usado no app principal (margem abaixo da cota grátis real
# do Google), só que aqui é um contador único e simples (ferramenta de baixo
# volume, admin-only, não precisa da complexidade de pool/rodízio do app
# principal).
MAPS_LIMITE_MENSAL = 900

# Provedores de e-mail gratuitos/genéricos — não dá pra triangular empresa
# a partir do domínio nesses casos.
DOMINIOS_GRATUITOS = {
    "gmail.com", "hotmail.com", "outlook.com", "live.com", "yahoo.com",
    "yahoo.com.br", "icloud.com", "me.com", "aol.com", "bol.com.br",
    "uol.com.br", "ig.com.br", "terra.com.br", "r7.com", "globo.com",
    "globomail.com", "oi.com.br", "protonmail.com", "gmx.com", "zipmail.com.br",
    "msn.com", "hotmail.com.br", "outlook.com.br",
}


# ── Utilitários ──────────────────────────────────────────────────────────

def _apenas_digitos(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def extrair_dominio_empresa(email: str) -> Optional[str]:
    """Retorna o domínio do e-mail se for corporativo, ou None se for
    provedor gratuito/genérico (ou se o e-mail for inválido)."""
    if not email or "@" not in email:
        return None
    dominio = email.strip().lower().split("@")[-1]
    if not dominio or dominio in DOMINIOS_GRATUITOS:
        return None
    return dominio


def nome_provavel_da_empresa(dominio: str) -> str:
    """'clinicasaude.com.br' → 'clinicasaude' (nome mais provável pra buscar)."""
    base = dominio.split(".")[0]
    return re.sub(r"[-_]+", " ", base).strip()


# Rótulos aceitos no formato "* Rótulo\nValor" colado no teste em lote —
# qualquer rótulo que não bata com um desses (ex.: "Sua dívida é de:Array",
# vindo de export de formulário) é simplesmente ignorado.
_ROTULOS_EMAIL = ("email", "e-mail")
_ROTULOS_NOME = ("full name", "nome completo", "nome")
_ROTULOS_TELEFONE = ("phone number", "phone", "telefone", "celular")


def parse_leads_em_lote(texto: str) -> list[dict]:
    """Faz o parse de um texto colado no formato:

        * Email
        fulano@empresa.com.br
        * Full name
        Fulano de Tal
        * Phone number
        +5511999999999

        * Email
        ...

    Blocos separados por linha(s) em branco = um lead cada. Dentro do
    bloco, uma linha "* Rótulo" é seguida pela linha de valor — rótulos
    que não sejam email/nome/telefone (e rótulos sem valor na linha
    seguinte, ex. de exports de formulário malformados) são ignorados.
    Leads sem e-mail e sem telefone (nada pra buscar) são descartados.
    """
    blocos = re.split(r"\n\s*\n", (texto or "").strip())
    leads = []
    for bloco in blocos:
        linhas = [l.strip() for l in bloco.splitlines() if l.strip()]
        lead = {"nome": "", "email": "", "telefone": ""}
        i = 0
        while i < len(linhas):
            linha = linhas[i]
            if not linha.startswith("*"):
                i += 1
                continue
            rotulo = linha.lstrip("*").strip().rstrip(":").lower()
            tem_valor = i + 1 < len(linhas) and not linhas[i + 1].startswith("*")
            valor = linhas[i + 1] if tem_valor else ""
            i += 2 if tem_valor else 1
            if rotulo in _ROTULOS_EMAIL:
                lead["email"] = valor
            elif rotulo in _ROTULOS_NOME:
                lead["nome"] = valor
            elif rotulo in _ROTULOS_TELEFONE:
                lead["telefone"] = valor
        if lead["email"] or lead["telefone"]:
            leads.append(lead)
    return leads


# ── Casa dos Dados ───────────────────────────────────────────────────────

def cdd_busca_por_nome(nome: str, api_key: str) -> list[dict]:
    """Busca textual na razão social/nome fantasia — mesmo endpoint e
    mecanismo já usado no app principal pro filtro de Recuperação Judicial,
    só que reimplementado aqui de forma mínima (sem os outros ~20 filtros
    que o app principal suporta, que não fazem sentido pra esse caso)."""
    body = {
        "situacao_cadastral": ["ATIVA"],
        "limite": 5,
        "pagina": 1,
        "busca_textual": [{
            "texto": [nome], "tipo_busca": "contem",
            "razao_social": True, "nome_fantasia": True,
        }],
    }
    try:
        resp = requests.post(
            CDD_ENDPOINT, json=body,
            headers={"api-key": api_key, "Content-Type": "application/json"},
            timeout=20,
        )
        resp.raise_for_status()
        itens = resp.json().get("cnpjs", [])
    except Exception as e:
        logger.warning("cdd_busca_por_nome falhou: %s", e)
        return []

    resultados = []
    for item in itens:
        end = item.get("endereco") or {}
        ativ = item.get("atividade_principal") or {}
        if isinstance(ativ, list):
            ativ = ativ[0] if ativ else {}
        resultados.append({
            "nome": (item.get("razao_social") or item.get("nome_fantasia") or "").strip(),
            "cnpj": item.get("cnpj", ""),
            "municipio": end.get("municipio", ""),
            "uf": (end.get("uf") or "").upper(),
            "endereco": " ".join(p for p in [
                end.get("tipo_logradouro", ""), end.get("logradouro", ""),
                end.get("numero", ""), end.get("bairro", ""),
            ] if p).strip(", "),
            "cnae_descricao": ativ.get("descricao", "") if isinstance(ativ, dict) else "",
        })
    return resultados


# ── Google Maps (chave já configurada na conta do admin + teto de segurança) ─

def obter_maps_key_admin(sb, admin_email: str = "") -> str:
    """
    Busca a chave do Google Maps direto do Supabase, na conta do próprio
    admin — a mesma já configurada em Configurações no app principal, sem
    precisar cadastrar uma chave nova/duplicada só pra esse protótipo.
    Tenta, nessa ordem: pool próprio (maps_keys_pool[0]) → chave única
    (google_maps_api_key) → chave de conta gerenciada (maps_api_key_admin,
    caso a própria conta do admin esteja marcada como "créditos Maps
    gerenciados" — incomum, mas cobre esse caso também). Se admin_email não
    for informado, usa o primeiro perfil com role='admin' encontrado.

    Atenção: como é a MESMA chave usada no app principal, o uso feito por
    aqui soma na cota real do Google, mas o contador de uso mostrado no
    Admin do app principal não sabe dessas chamadas (foram feitas por um
    serviço separado) — o teto MAPS_LIMITE_MENSAL abaixo é a proteção
    própria deste protótipo, independente da que já existe no app principal.
    """
    try:
        query = sb.table("profiles").select(
            "email, maps_keys_pool, google_maps_api_key, maps_api_key_admin, role"
        )
        query = query.eq("email", admin_email) if admin_email else query.eq("role", "admin")
        resp = query.limit(1).execute()
        rows = resp.data or []
        if not rows:
            return ""
        perfil = rows[0]
        pool = perfil.get("maps_keys_pool") or []
        if pool and pool[0].get("key"):
            return pool[0]["key"]
        if perfil.get("google_maps_api_key"):
            return perfil["google_maps_api_key"]
        return perfil.get("maps_api_key_admin") or ""
    except Exception as e:
        logger.warning("obter_maps_key_admin falhou: %s", e)
        return ""


def _maps_uso_liberado(sb) -> bool:
    """Checa (e reseta se virou o mês) o contador de uso da chave dedicada
    desse protótipo. True = pode usar, False = estourou o teto do mês."""
    mes = date.today().strftime("%Y-%m")
    try:
        resp = sb.table("enrichment_settings").select("maps_usage, maps_usage_month").eq("id", 1).single().execute()
        row = resp.data or {}
    except Exception:
        return True  # sem conseguir checar, não bloqueia — é só uma margem de segurança
    if row.get("maps_usage_month") != mes:
        try:
            sb.table("enrichment_settings").update({"maps_usage": 0, "maps_usage_month": mes}).eq("id", 1).execute()
        except Exception:
            pass
        return True
    return int(row.get("maps_usage", 0)) < MAPS_LIMITE_MENSAL


def _maps_registrar_uso(sb, chamadas: int = 1) -> None:
    mes = date.today().strftime("%Y-%m")
    try:
        resp = sb.table("enrichment_settings").select("maps_usage, maps_usage_month").eq("id", 1).single().execute()
        row = resp.data or {}
        atual = int(row.get("maps_usage", 0)) if row.get("maps_usage_month") == mes else 0
        sb.table("enrichment_settings").update({
            "maps_usage": atual + chamadas, "maps_usage_month": mes,
        }).eq("id", 1).execute()
    except Exception as e:
        logger.warning("_maps_registrar_uso falhou: %s", e)


def maps_text_search(query: str, api_key: str) -> Optional[dict]:
    try:
        resp = requests.get(
            PLACES_TEXT_SEARCH_URL,
            params={"query": query, "language": "pt-BR", "key": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("maps_text_search falhou: %s", e)
        return None
    if data.get("status") != "OK" or not data.get("results"):
        return None
    return data["results"][0]


def maps_place_details(place_id: str, api_key: str) -> dict:
    try:
        resp = requests.get(
            PLACES_DETAILS_URL,
            params={
                "place_id": place_id,
                "fields": "name,formatted_phone_number,international_phone_number,formatted_address,website,url",
                "language": "pt-BR", "key": api_key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("result", {})
    except Exception as e:
        logger.warning("maps_place_details falhou: %s", e)
        return {}


# ── IA (fallback final) ──────────────────────────────────────────────────

def enriquecer_via_ia(nome: str, email: str, telefone: str, openai_api_key: str) -> Optional[dict]:
    """Último recurso: pede pra um modelo OpenAI barato (gpt-5-mini) buscar
    na internet, cruzando nome + e-mail (inclusive a parte antes do @, útil
    mesmo em e-mail pessoal) + telefone, e tentar identificar a empresa/
    dados comerciais associados. Retorna None se não achar nada com
    confiança razoável, mesmo depois de tentar vários ângulos de busca."""
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("pacote 'openai' não instalado — pulando fallback de IA")
        return None

    usuario_email = email.split("@")[0] if email and "@" in email else ""

    prompt = (
        "Você é um pesquisador tentando identificar a EMPRESA (dado comercial, "
        "não pessoal — nunca CPF ou dado sensível) onde este lead trabalha ou "
        "está associado, a partir de sinais parciais e muitas vezes incompletos. "
        "Use a busca na web de forma ATIVA e em MÚLTIPLAS frentes — não desista "
        "numa única tentativa de busca.\n\n"
        "Estratégias a tentar, combinando os dados disponíveis (tente várias, "
        "não só a primeira que der certo):\n"
        "1. Se o e-mail tem domínio corporativo (não é gmail/hotmail/yahoo/"
        "outlook/icloud/bol/uol/terra e afins), pesquise o domínio direto — "
        "geralmente É o site da empresa.\n"
        "2. Pesquise o NOME COMPLETO do lead junto com \"LinkedIn\" — perfis "
        "profissionais costumam listar a empresa atual e o cargo.\n"
        "3. Mesmo em e-mail pessoal, o texto antes do @ (ex.: \"joao.silva83\") "
        "às vezes é um username reaproveitado em outras redes/plataformas — "
        "vale pesquisar esse texto combinado com o nome.\n"
        "4. Pesquise o telefone (com e sem o \"+55\" e o DDD, e também só os "
        "últimos dígitos) — números de WhatsApp Business e cadastros públicos "
        "às vezes aparecem indexados em páginas de empresas ou diretórios.\n"
        "5. Combine sinais entre si (nome + cidade que aparecer numa busca "
        "anterior, nome + telefone, username do e-mail + telefone, etc.) — "
        "cada busca pode revelar uma pista pra próxima.\n\n"
        "Retorne SOMENTE um JSON (sem markdown, sem texto fora do JSON) com as "
        "chaves: empresa_nome, cargo (se descobrir o cargo/função do lead na "
        "empresa), cnpj (se encontrar), municipio, uf, website, linkedin_url "
        "(se achar o perfil), confianca (\"alta\"/\"media\"/\"baixa\"), e fonte "
        "(frase curta explicando de onde veio — ex.: \"perfil do LinkedIn "
        "encontrado buscando o nome completo\"). Só retorne "
        "{\"empresa_nome\": null} se genuinamente não achar NADA depois de "
        "tentar abordagens diferentes — não desista numa busca só.\n\n"
        f"Nome completo do lead: {nome or '(não informado)'}\n"
        f"E-mail completo: {email or '(não informado)'}"
        + (f" (texto antes do @: \"{usuario_email}\")" if usuario_email else "")
        + f"\nTelefone: {telefone or '(não informado)'}"
    )

    try:
        client = OpenAI(api_key=openai_api_key)
        resp = client.responses.create(
            model="gpt-5-mini",
            tools=[{"type": "web_search"}],
            input=prompt,
        )
        texto = resp.output_text or ""
        import json
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if not match:
            return None
        dados = json.loads(match.group(0))
        if not dados.get("empresa_nome"):
            return None
        return dados
    except Exception as e:
        logger.warning("enriquecer_via_ia falhou: %s", e)
        return None


# ── Orquestração ─────────────────────────────────────────────────────────

def enriquecer_lead(
    nome: str, email: str, telefone: str,
    cdd_api_key: str, maps_api_key: str, openai_api_key: str,
    sb,
) -> dict:
    """
    Roda o pipeline completo e retorna um dict estruturado com o resultado.
    Tenta e-mail primeiro (mais confiável), depois telefone, depois IA.
    """
    resultado: dict = {
        "status": "nao_encontrado", "metodo_encontrado": None,
        "empresa_nome": None, "cnpj": None, "endereco": None,
        "municipio": None, "uf": None, "website": None, "maps_url": None,
        "avaliacao": None, "total_avaliacoes": None, "erro": None,
        "cargo": None, "linkedin_url": None,
    }

    maps_disponivel = bool(maps_api_key) and _maps_uso_liberado(sb)

    # 1) E-mail corporativo → nome provável → CDD + confirmação via Maps
    dominio = extrair_dominio_empresa(email)
    if dominio:
        candidato = nome_provavel_da_empresa(dominio)
        candidatos_cdd = cdd_busca_por_nome(candidato, cdd_api_key) if cdd_api_key else []

        candidato_maps = None
        if maps_disponivel:
            place = maps_text_search(candidato, maps_api_key)
            _maps_registrar_uso(sb, 1)
            if place and place.get("place_id"):
                det = maps_place_details(place["place_id"], maps_api_key)
                _maps_registrar_uso(sb, 1)
                website = (det.get("website") or "").lower()
                if website and dominio in website:
                    candidato_maps = {
                        "nome": det.get("name") or place.get("name", ""),
                        "endereco": det.get("formatted_address", ""),
                        "website": det.get("website", ""),
                        "maps_url": det.get("url", ""),
                        "avaliacao": place.get("rating"),
                        "total_avaliacoes": place.get("user_ratings_total"),
                    }

        # Prioriza CNPJ confirmado pela Casa dos Dados; usa Maps como
        # confirmação cruzada e fonte extra (endereço/site/avaliação).
        if candidatos_cdd:
            melhor = candidatos_cdd[0]
            resultado.update({
                "status": "concluido", "metodo_encontrado": "email",
                "empresa_nome": melhor["nome"], "cnpj": melhor["cnpj"],
                "endereco": melhor["endereco"], "municipio": melhor["municipio"],
                "uf": melhor["uf"],
            })
            if candidato_maps:
                resultado["website"] = candidato_maps["website"]
                resultado["maps_url"] = candidato_maps["maps_url"]
                resultado["avaliacao"] = candidato_maps["avaliacao"]
                resultado["total_avaliacoes"] = candidato_maps["total_avaliacoes"]
            return resultado
        if candidato_maps:
            resultado.update({
                "status": "concluido", "metodo_encontrado": "email",
                "empresa_nome": candidato_maps["nome"],
                "endereco": candidato_maps["endereco"],
                "website": candidato_maps["website"],
                "maps_url": candidato_maps["maps_url"],
                "avaliacao": candidato_maps["avaliacao"],
                "total_avaliacoes": candidato_maps["total_avaliacoes"],
            })
            return resultado

    # 2) Telefone — tenta o número puro como texto no Maps (não documentado
    #    oficialmente, mas barato de tentar)
    if telefone and maps_disponivel:
        digitos = _apenas_digitos(telefone)
        if digitos:
            place = maps_text_search(digitos, maps_api_key)
            _maps_registrar_uso(sb, 1)
            if place and place.get("place_id"):
                det = maps_place_details(place["place_id"], maps_api_key)
                _maps_registrar_uso(sb, 1)
                resultado.update({
                    "status": "concluido", "metodo_encontrado": "telefone",
                    "empresa_nome": det.get("name") or place.get("name", ""),
                    "endereco": det.get("formatted_address", ""),
                    "website": det.get("website", ""),
                    "maps_url": det.get("url", ""),
                    "avaliacao": place.get("rating"),
                    "total_avaliacoes": place.get("user_ratings_total"),
                })
                return resultado

    # 3) IA — último recurso
    if openai_api_key:
        dados_ia = enriquecer_via_ia(nome, email, telefone, openai_api_key)
        if dados_ia:
            resultado.update({
                "status": "concluido", "metodo_encontrado": "ia",
                "empresa_nome": dados_ia.get("empresa_nome"),
                "cnpj": dados_ia.get("cnpj"),
                "municipio": dados_ia.get("municipio"),
                "uf": dados_ia.get("uf"),
                "website": dados_ia.get("website"),
                "cargo": dados_ia.get("cargo"),
                "linkedin_url": dados_ia.get("linkedin_url"),
            })
            return resultado

    return resultado
