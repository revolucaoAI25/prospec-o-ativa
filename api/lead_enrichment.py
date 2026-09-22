"""
Pipeline de enriquecimento de leads por e-mail/telefone — protótipo admin-only.

Módulo AUTOCONTIDO de propósito: este serviço (/api) é deployado separado do
app Streamlit principal (root directory próprio no Railway, requirements.txt
próprio) e não tem acesso a modules/ do app principal.

Estratégia: só IA (OpenAI gpt-5-mini, com a ferramenta de busca na web nativa
da Responses API). Havia antes uma tentativa prévia via e-mail→Casa dos
Dados/Google Maps e telefone→Google Maps, mas na calibragem prática elas
praticamente não geravam resultado (a IA já cobre esses mesmos casos, e
melhor — com cargo, LinkedIn e resumo, o que a busca direta não dava) e só
adicionavam custo de API/latência — por isso foram removidas.

Variáveis de ambiente usadas:
  OPENAI_API_KEY   — obrigatória pra esse recurso funcionar (sem ela, o
                     enriquecimento sempre retorna "não encontrado"). Usa o
                     modelo gpt-5-mini.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# ── Utilitários ──────────────────────────────────────────────────────────

def _apenas_digitos(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def _normalizar_sim_nao(valor) -> Optional[str]:
    """Normaliza a resposta livre da IA pra três valores fixos — protege
    contra variações de grafia (com/sem acento, maiúscula, etc.)."""
    v = (str(valor) if valor is not None else "").strip().lower()
    v = v.replace("ã", "a").replace("á", "a").replace("ç", "c")
    if v in ("sim", "yes", "true"):
        return "sim"
    if v in ("nao", "no", "false"):
        return "nao"
    if v in ("nao_verificado", "nao verificado", "unknown", "indeterminado"):
        return "nao_verificado"
    return None


# DDD → UF, usado só como PISTA regional pra ajudar a busca e, principalmente,
# como checagem cruzada contra o que a IA encontrar (ver enriquecer_via_ia) —
# reduz falso positivo tipo "achei uma empresa em outro estado que não tem
# nada a ver, só porque o nome bateu".
_DDD_UF = {
    "11": "SP", "12": "SP", "13": "SP", "14": "SP", "15": "SP", "16": "SP", "17": "SP", "18": "SP", "19": "SP",
    "21": "RJ", "22": "RJ", "24": "RJ",
    "27": "ES", "28": "ES",
    "31": "MG", "32": "MG", "33": "MG", "34": "MG", "35": "MG", "37": "MG", "38": "MG",
    "41": "PR", "42": "PR", "43": "PR", "44": "PR", "45": "PR", "46": "PR",
    "47": "SC", "48": "SC", "49": "SC",
    "51": "RS", "53": "RS", "54": "RS", "55": "RS",
    "61": "DF", "62": "GO", "64": "GO",
    "63": "TO",
    "65": "MT", "66": "MT",
    "67": "MS",
    "68": "AC",
    "69": "RO",
    "71": "BA", "73": "BA", "74": "BA", "75": "BA", "77": "BA",
    "79": "SE",
    "81": "PE", "87": "PE",
    "82": "AL",
    "83": "PB",
    "84": "RN",
    "85": "CE", "88": "CE",
    "86": "PI", "89": "PI",
    "91": "PA", "93": "PA", "94": "PA",
    "92": "AM", "97": "AM",
    "95": "RR",
    "96": "AP",
    "98": "MA", "99": "MA",
}


def uf_provavel_por_telefone(telefone: str) -> Optional[str]:
    """Estima a UF a partir do DDD de um telefone brasileiro. Retorna None
    se não der pra reconhecer (telefone estrangeiro, incompleto, etc.)."""
    digitos = _apenas_digitos(telefone)
    if digitos.startswith("55") and len(digitos) > 10:
        digitos = digitos[2:]
    if len(digitos) < 10:
        return None
    return _DDD_UF.get(digitos[:2])


# ── Teste em lote — parser do texto colado no painel ────────────────────

# Rótulos aceitos no teste em lote, em formato "* Rótulo\nValor",
# "Rótulo: Valor" (mesma linha), com ou sem marcador de bullet na frente
# (*, -, •, etc.) — tolerante a variações de como o texto foi copiado de
# outro lugar (planilha, export de formulário, etc.). Rótulos que não
# batam com nenhum desses (ex.: "Sua dívida é de:Array") são ignorados.
_BULLET = r"[\*\-•●○▪–—]?"
_CAMPO_PATTERNS = [
    ("email", re.compile(rf"^{_BULLET}\s*e[-\s]?mail\s*[:\-]?\s*(.*)$", re.IGNORECASE)),
    ("nome", re.compile(rf"^{_BULLET}\s*(?:full\s*name|nome\s*completo|nome)\s*[:\-]?\s*(.*)$", re.IGNORECASE)),
    ("telefone", re.compile(rf"^{_BULLET}\s*(?:phone\s*number|phone|telefone|celular|whatsapp)\s*[:\-]?\s*(.*)$", re.IGNORECASE)),
]


def _linha_e_rotulo(linha: str) -> bool:
    return any(patt.match(linha) for _, patt in _CAMPO_PATTERNS)


def _dividir_em_blocos(texto: str) -> list[str]:
    """Separa o texto colado em um bloco por lead. Preferência por
    linha(s) em branco como separador; se um "bloco" (entre linhas em
    branco) tiver MAIS DE UM rótulo de e-mail dentro dele, assume que os
    leads vieram colados sem linha em branco entre eles e subdivide a
    partir de cada novo "e-mail" encontrado."""
    texto = (texto or "").strip()
    if not texto:
        return []
    email_patt = _CAMPO_PATTERNS[0][1]
    blocos = []
    for bruto in re.split(r"\n\s*\n", texto):
        linhas = bruto.splitlines()
        inicios = [i for i, l in enumerate(linhas) if email_patt.match(l.strip())]
        if len(inicios) <= 1:
            blocos.append(bruto)
            continue
        limites = inicios + [len(linhas)]
        for a, b in zip(limites, limites[1:]):
            blocos.append("\n".join(linhas[a:b]))
    return blocos


def parse_leads_em_lote(texto: str) -> list[dict]:
    """Faz o parse de um texto colado com vários leads, um por bloco, no
    formato (aceita variações — ver _CAMPO_PATTERNS acima):

        * Email
        fulano@empresa.com.br
        * Full name
        Fulano de Tal
        * Phone number
        +5511999999999

        * Email
        ...

    Leads sem e-mail e sem telefone (nada pra buscar) são descartados.
    """
    leads = []
    for bloco in _dividir_em_blocos(texto):
        linhas = [l.strip() for l in bloco.splitlines() if l.strip()]
        lead = {"nome": "", "email": "", "telefone": ""}
        i = 0
        while i < len(linhas):
            linha = linhas[i]
            for campo, patt in _CAMPO_PATTERNS:
                m = patt.match(linha)
                if not m:
                    continue
                valor = m.group(1).strip()
                if not valor and i + 1 < len(linhas) and not _linha_e_rotulo(linhas[i + 1]):
                    valor = linhas[i + 1]
                    i += 1
                lead[campo] = valor
                break
            i += 1
        if lead["email"] or lead["telefone"]:
            leads.append(lead)
    return leads


# ── IA (único mecanismo de busca) ───────────────────────────────────────

def enriquecer_via_ia(nome: str, email: str, telefone: str, openai_api_key: str) -> Optional[dict]:
    """Pede pra um modelo OpenAI barato (gpt-5-mini) buscar na internet,
    cruzando nome + e-mail (inclusive a parte antes do @, útil mesmo em
    e-mail pessoal) + telefone, e tentar identificar a empresa/dados
    comerciais associados. Retorna None se não achar nada com confiança
    razoável, mesmo depois de tentar vários ângulos de busca."""
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("pacote 'openai' não instalado — enriquecimento desativado")
        return None

    usuario_email = email.split("@")[0] if email and "@" in email else ""
    uf_hint = uf_provavel_por_telefone(telefone) if telefone else None

    prompt = (
        "Você é um pesquisador tentando identificar a EMPRESA (dado comercial, nunca CPF ou "
        "dado pessoal sensível) onde este lead trabalha, a partir de sinais parciais. Use "
        "busca na web ativamente, em múltiplas frentes, sem desistir numa tentativa só.\n\n"
        "Estratégias (combine várias): (1) domínio do e-mail corporativo — geralmente é o "
        "site da empresa; (2) nome completo + \"LinkedIn\"; (3) texto antes do @ como "
        "username, mesmo em e-mail pessoal; (4) telefone (com/sem +55 e DDD); (5) cruze "
        "pistas entre si.\n\n"
        "JULGAMENTO DE IDENTIDADE — não é a mesma pessoa só porque o nome bate: nomes comuns "
        "pertencem a milhares de pessoas. Só afirme uma empresa com corroboração real ligando "
        "ESTE lead (não um homônimo) a ela: telefone/e-mail aparecendo no mesmo perfil da "
        "empresa, nome raro batendo com perfil verificável, ou domínio corporativo já sendo "
        "a empresa. Sobrenome precisa bater EXATAMENTE (não aceite grafias parecidas mas "
        "diferentes, tipo \"Fisbhen\" vs \"Fischen\"). Sem corroboração real, é extrapolação "
        "— retorne \"não encontrado\".\n\n"
        + (
            f"PISTA REGIONAL: o DDD indica que o lead provavelmente está em {uf_hint}. "
            f"Reforce a busca com isso e, se a empresa encontrada for de outro estado sem "
            f"explicação plausível, trate como sinal de homônimo e reduza a confiança.\n\n"
            if uf_hint else ""
        )
        + "TAREFA PRINCIPAL, resolva isso primeiro e sozinha: decida empresa_nome (ou null), "
        "cargo, cnpj, municipio, uf, website, linkedin_url, confianca (\"alta\"/\"media\"/"
        "\"baixa\") e fonte, usando SÓ os critérios acima. Critério de confiança: \"alta\" = "
        "dois ou mais sinais independentes convergem (ou domínio já é a empresa) sem conflito "
        "regional; \"media\" = um sinal forte específico; \"baixa\" = palpite sem corroboração "
        "real ou com conflito regional não explicado — nesse caso prefira {\"empresa_nome\": "
        "null} a arriscar um palpite errado.\n\n"
        + "SÓ DEPOIS de já ter decidido tudo isso, preencha OPCIONALMENTE (sem fazer buscas "
        "extra dedicadas — só aproveite o que já apareceu nas buscas acima, pra não gastar "
        "mais tempo/custo): outros sócios/fundadores da empresa; data ou ano de fundação; "
        "outros dados comerciais úteis (setor, porte, produtos/serviços principais, clientes "
        "notáveis); e, só se tiver aparecido incidentalmente (não faça busca dedicada pra "
        "isso), indício — nunca detalhe — de processo judicial ligado à empresa ou ao lead, "
        "só marcando \"sim\" se claramente for a mesma empresa/pessoa (mesmo cuidado contra "
        "homônimo de antes). Não achou algum desses quatro itens nas buscas já feitas? Deixe "
        "null/\"nao_verificado\" e siga em frente — NUNCA deixe de responder a tarefa "
        "principal, nem mude empresa_nome ou confianca, por causa desses itens opcionais; "
        "eles não fazem parte do julgamento de identidade.\n\n"
        + "Retorne SOMENTE um JSON (sem markdown) com: empresa_nome, cargo, cnpj, municipio, "
        "uf, website, linkedin_url, confianca, fonte, resumo (2 a 4 frases em português com "
        "contexto comercial da empresa — setor, porte, cidade, e outros dados relevantes que "
        "achar; null se não achar empresa), socios (nomes separados por vírgula; null se não "
        "achar/não se aplicar), fundacao (data ou ano; null se não achar) e processos_jusbrasil "
        "(\"sim\"/\"nao\"/\"nao_verificado\").\n\n"
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
            # reasoning.effort="low" foi testado e piorou resultado (casos fáceis
            # que antes eram achados passaram a dar "não encontrado") — "medium"
            # é o meio-termo.
            reasoning={"effort": "medium"},
            text={"verbosity": "medium"},
            # Teto duro de buscas — sem isso, nada impedia a IA de ficar
            # pesquisando indefinidamente (o que também explica ficar "travado"
            # em processando por muito tempo) nem limitava o custo por lead.
            max_tool_calls=6,
            # Timeout pra essa chamada específica não travar pra sempre —
            # se estourar, cai no except abaixo e o lead termina como "erro"
            # em vez de ficar preso em "processando" indefinidamente.
            timeout=90.0,
        )
        texto = resp.output_text or ""
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if not match:
            return None
        dados = json.loads(match.group(0))
        if not dados.get("empresa_nome"):
            return None
        confianca = (dados.get("confianca") or "").strip().lower()
        if confianca not in ("alta", "media"):
            # Rede de segurança independente do prompt: mesmo que o modelo
            # devolva um palpite de baixa confiança (ou sem confiança
            # informada), tratamos como "não encontrado" em vez de atribuir
            # uma empresa a alguém com base só numa coincidência de nome.
            logger.info(
                "IA achou candidato de confiança insuficiente (%s) — descartando: %s / fonte: %s",
                confianca or "(ausente)", dados.get("empresa_nome"), dados.get("fonte"),
            )
            return None
        empresa_uf = (dados.get("uf") or "").strip().upper()
        if uf_hint and empresa_uf and empresa_uf != uf_hint and confianca != "alta":
            # Checagem programática independente do autojulgamento da IA: se o
            # DDD indica uma região e a empresa encontrada é de outra, só
            # aceitamos quando a própria IA já classificou como "alta" (ela foi
            # instruída a levar esse conflito em conta nesse julgamento) — em
            # "media" o risco de homônimo é grande o bastante pra descartar.
            logger.info(
                "IA achou candidato com conflito regional (DDD indica %s, empresa em %s, confianca=%s) — descartando: %s",
                uf_hint, empresa_uf, confianca, dados.get("empresa_nome"),
            )
            return None
        return dados
    except Exception as e:
        logger.warning("enriquecer_via_ia falhou: %s", e)
        return None


# ── Orquestração ─────────────────────────────────────────────────────────

def enriquecer_lead(nome: str, email: str, telefone: str, openai_api_key: str) -> dict:
    """Roda o enriquecimento (só IA, ver docstring do módulo) e retorna um
    dict estruturado com o resultado."""
    resultado: dict = {
        "status": "nao_encontrado", "metodo_encontrado": None,
        "empresa_nome": None, "cnpj": None, "endereco": None,
        "municipio": None, "uf": None, "website": None, "maps_url": None,
        "avaliacao": None, "total_avaliacoes": None, "erro": None,
        "cargo": None, "linkedin_url": None, "resumo": None,
        "socios": None, "fundacao": None, "processos_jusbrasil": None,
    }

    if not openai_api_key:
        return resultado

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
            "resumo": dados_ia.get("resumo"),
            "socios": dados_ia.get("socios"),
            "fundacao": dados_ia.get("fundacao"),
            "processos_jusbrasil": _normalizar_sim_nao(dados_ia.get("processos_jusbrasil")),
        })

    return resultado
