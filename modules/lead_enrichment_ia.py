"""
Enriquecimento de leads (nome/e-mail/telefone → dados comerciais da empresa)
via IA, com busca na web — feature opcional do app principal, habilitada
por usuário pelo admin (ver profiles.enriquecimento_ia_habilitado).

Módulo AUTOCONTIDO de propósito: a lógica de busca via IA já existe, calibrada
com bastante iteração real, no protótipo separado em api/lead_enrichment.py —
mas aquele serviço é um deploy Railway independente (próprio requirements.txt,
sem acesso a modules/ do app principal) e o app principal não importa de lá,
pra manter os dois deploys realmente independentes (mesma decisão de
arquitetura usada no resto do projeto). Por isso essa lógica é reimplementada
aqui, de propósito — mudanças calibradas num lugar (prompt, critérios de
confiança, etc.) devem ser espelhadas manualmente no outro se fizer sentido,
mas os dois módulos nunca se importam.

Diferença chave em relação ao protótipo em api/: lá a chave OpenAI vem de uma
variável de ambiente única (admin-only); aqui cada usuário cadastra a própria
chave em Configurações (profiles.openai_api_key) — o custo de IA é do próprio
usuário, não da plataforma.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Callable, Optional

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
    if v in ("nao_encontrado", "nao encontrado", "nao_verificado", "nao verificado", "unknown", "indeterminado"):
        return "nao_encontrado"
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


# ── Texto colado com vários leads — parser tolerante a formato ─────────────

# Rótulos aceitos no formato "* Rótulo\nValor", "Rótulo: Valor" (mesma
# linha), com ou sem marcador de bullet na frente (*, -, •, etc.) —
# tolerante a variações de como o texto foi copiado de outro lugar
# (planilha, CRM, export de formulário). Rótulos que não batam com nenhum
# desses são ignorados.
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


def _linha_e_csv(linha: str) -> Optional[dict]:
    """Fallback simples: uma linha "Nome, Email, Telefone" (vírgula, ponto
    e vírgula ou tab), sem rótulos — pra quem cola direto de uma planilha
    sem os marcadores "* Rótulo"."""
    partes = re.split(r"[;,\t]", linha)
    partes = [p.strip() for p in partes if p.strip()]
    if len(partes) < 2:
        return None
    lead = {"nome": "", "email": "", "telefone": ""}
    for p in partes:
        if "@" in p and not lead["email"]:
            lead["email"] = p
        elif re.search(r"\d{8,}", _apenas_digitos(p)) and not lead["telefone"]:
            lead["telefone"] = p
        elif not lead["nome"]:
            lead["nome"] = p
    return lead if (lead["email"] or lead["telefone"]) else None


def parse_leads_colados(texto: str) -> list[dict]:
    """Faz o parse de um texto colado com vários leads. Aceita dois
    formatos, tentados nessa ordem:

    1) Bloco por lead, rótulo + valor (aceita variações — ver
       _CAMPO_PATTERNS acima):

        * Email
        fulano@empresa.com.br
        * Full name
        Fulano de Tal
        * Phone number
        +5511999999999

    2) Uma linha por lead, campos separados por vírgula/ponto e vírgula/tab
       (sem rótulos), ex.: "Fulano de Tal, fulano@empresa.com.br, 11999999999"

    Leads sem e-mail e sem telefone (nada pra buscar) são descartados.
    """
    leads = []
    for bloco in _dividir_em_blocos(texto):
        linhas = [l.strip() for l in bloco.splitlines() if l.strip()]
        if not linhas:
            continue
        if _linha_e_rotulo(linhas[0]):
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
        else:
            # bloco sem rótulo — tenta cada linha como um CSV solto
            for linha in linhas:
                lead = _linha_e_csv(linha)
                if lead:
                    leads.append(lead)
    return leads


# ── Nível de raciocínio — configurável por quem usa ─────────────────────

# Fonte única pra essas opções — o app importa isso pra montar o seletor,
# então o texto explicativo mostrado pro usuário e o que de fato é enviado
# pra API ficam sempre em sincronia.
NIVEIS_RACIOCINIO = {
    "rapido": {
        "label": "Rápido e econômico",
        "descricao": (
            "Busca mais direta, menos aprofundada. Mais barato e mais rápido, mas em casos "
            "mais difíceis (pouca informação disponível) pode não achar o que buscaria com "
            "mais tempo — em testes reais, esse nível deixou passar alguns casos que o "
            "\"equilibrado\" achava."
        ),
        "reasoning_effort": "low", "verbosity": "low", "max_tool_calls": 6,
    },
    "equilibrado": {
        "label": "Equilibrado (recomendado)",
        "descricao": "Bom equilíbrio entre profundidade de busca e custo — é o nível já calibrado e testado com casos reais.",
        "reasoning_effort": "medium", "verbosity": "low", "max_tool_calls": 9,
    },
    "profundo": {
        "label": "Mais profundo e detalhado",
        "descricao": "Pesquisa mais a fundo, com mais tentativas, e escreve resumos mais completos — mais lento e mais caro por lead.",
        "reasoning_effort": "high", "verbosity": "medium", "max_tool_calls": 12,
    },
}
NIVEL_PADRAO = "equilibrado"


# ── IA (único mecanismo de busca) ───────────────────────────────────────

def enriquecer_via_ia(
    nome: str, email: str, telefone: str, openai_api_key: str,
    *,
    nivel_raciocinio: str = NIVEL_PADRAO,
    buscar_socios: bool = True,
    buscar_fundacao: bool = True,
    buscar_processos: bool = True,
    campos_customizados: Optional[list[str]] = None,
) -> Optional[dict]:
    """Pede pra um modelo OpenAI barato (gpt-5-mini) buscar na internet,
    cruzando nome + e-mail (inclusive a parte antes do @, útil mesmo em
    e-mail pessoal) + telefone, e tentar identificar a empresa/dados
    comerciais associados. Retorna None se não achar nada com confiança
    razoável, mesmo depois de tentar vários ângulos de busca. Levanta
    exceção se a chamada à IA falhar tecnicamente após as tentativas (ver
    abaixo) — isso é distinto de "não encontrado".

    buscar_socios/buscar_fundacao/buscar_processos desligam a busca (não só
    a exibição) daquele item — a IA nem é instruída a procurar, economiza
    tempo/custo. campos_customizados é uma lista livre de outras coisas pra
    tentar descobrir, definidas por quem está usando (ex.: "número de
    funcionários", "faturamento estimado")."""
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("pacote 'openai' não instalado — enriquecimento desativado")
        return None

    nivel = NIVEIS_RACIOCINIO.get(nivel_raciocinio, NIVEIS_RACIOCINIO[NIVEL_PADRAO])
    campos_customizados = [c.strip() for c in (campos_customizados or []) if c.strip()]

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
    )

    # Itens extras (rodam DEPOIS da identificação, nunca influenciam ela) —
    # montados dinamicamente: só entram no prompt (e custam busca/tempo) os
    # que quem está usando realmente pediu.
    extras_pedidos = []
    if buscar_socios:
        extras_pedidos.append("outros sócios/fundadores da empresa")
    if buscar_fundacao:
        extras_pedidos.append("data ou ano de fundação")
    extras_pedidos.append(
        "outros dados comerciais úteis (setor, porte, produtos/serviços principais, clientes notáveis)"
    )
    if buscar_processos:
        extras_pedidos.append(
            "com uma busca dedicada (ex.: nome da empresa ou do lead + \"jusbrasil\" ou + "
            "\"processo\"), indício — nunca detalhe — de processo judicial ligado à empresa ou "
            "ao lead, só marcando \"sim\" se claramente for a mesma empresa/pessoa (mesmo "
            "cuidado contra homônimo de antes)"
        )
    if campos_customizados:
        lista_campos = "; ".join(f"\"{c}\"" for c in campos_customizados)
        extras_pedidos.append(
            f"e também, especificamente, estes itens pedidos por quem está usando essa busca: "
            f"{lista_campos} — pesquise objetivamente sobre cada um"
        )

    prompt += (
        "SÓ DEPOIS de já ter decidido tudo isso, faça mais algumas buscas (vale a pena buscar "
        "de verdade, isso é informação que interessa — não é só aproveitar o que já apareceu "
        "por acaso) pra tentar descobrir: " + "; ".join(extras_pedidos) + ". Não achou algum "
        "desses itens depois de tentar? Deixe null/\"nao_encontrado\" e siga em frente — mas "
        "NUNCA deixe de responder a tarefa principal, nem mude empresa_nome ou confianca, por "
        "causa desses itens extras; eles não fazem parte do julgamento de identidade, só vêm "
        "depois dele já estar decidido.\n\n"
    )

    campos_desc = [
        "empresa_nome", "cargo", "cnpj", "municipio", "uf", "website", "linkedin_url",
        "confianca (\"alta\"/\"media\"/\"baixa\")",
        "fonte (frase curta e específica da corroboração usada)",
        "resumo (2 a 4 frases em português com contexto comercial da empresa — setor, porte, "
        "cidade, e outros dados relevantes que achar; null se não achar empresa)",
    ]
    if buscar_socios:
        campos_desc.append("socios (nomes separados por vírgula; null se não achar/não se aplicar)")
    if buscar_fundacao:
        campos_desc.append("fundacao (data ou ano; null se não achar)")
    if buscar_processos:
        campos_desc.append("processos_jusbrasil (\"sim\"/\"nao\"/\"nao_encontrado\")")
    if campos_customizados:
        campos_desc.append(
            "extras (objeto JSON com uma chave EXATAMENTE igual a cada um dos itens "
            "pedidos acima — " + ", ".join(f"\"{c}\"" for c in campos_customizados) + " — "
            "com o que encontrar sobre aquilo, em texto curto, ou null se não achar)"
        )

    prompt += (
        "Retorne SOMENTE um JSON (sem markdown) com: " + ", ".join(campos_desc) + ".\n\n"
        f"Nome completo do lead: {nome or '(não informado)'}\n"
        f"E-mail completo: {email or '(não informado)'}"
        + (f" (texto antes do @: \"{usuario_email}\")" if usuario_email else "")
        + f"\nTelefone: {telefone or '(não informado)'}"
    )

    client = OpenAI(api_key=openai_api_key)

    # A CHAMADA em si (rede/API) tenta até 3 vezes — falha transitória
    # (rate limit, timeout, hiccup de rede) não deveria virar "não
    # encontrado" pro lead, é um problema técnico diferente. Depois de
    # esgotar as tentativas, propaga a exceção pra quem chamou tratar como
    # erro técnico (enriquecer_lead distingue isso de "não achou nada").
    resp = None
    ultimo_erro: Optional[Exception] = None
    for tentativa in range(1, 4):
        try:
            resp = client.responses.create(
                model="gpt-5-mini",
                tools=[{"type": "web_search"}],
                input=prompt,
                reasoning={"effort": nivel["reasoning_effort"]},
                text={"verbosity": nivel["verbosity"]},
                max_tool_calls=nivel["max_tool_calls"],
                timeout=240.0,
            )
            break
        except Exception as e:
            ultimo_erro = e
            logger.warning("enriquecer_via_ia: tentativa %d/3 falhou: %s", tentativa, e)
    if resp is None:
        raise RuntimeError(f"busca via IA falhou após 3 tentativas: {ultimo_erro}") from ultimo_erro

    try:
        texto = resp.output_text or ""
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if not match:
            return None
        dados = json.loads(match.group(0))
        if not dados.get("empresa_nome"):
            return None
        confianca = (dados.get("confianca") or "").strip().lower()
        if confianca not in ("alta", "media"):
            logger.info(
                "IA achou candidato de confiança insuficiente (%s) — descartando: %s / fonte: %s",
                confianca or "(ausente)", dados.get("empresa_nome"), dados.get("fonte"),
            )
            return None
        empresa_uf = (dados.get("uf") or "").strip().upper()
        if uf_hint and empresa_uf and empresa_uf != uf_hint and confianca != "alta":
            logger.info(
                "IA achou candidato com conflito regional (DDD indica %s, empresa em %s, confianca=%s) — descartando: %s",
                uf_hint, empresa_uf, confianca, dados.get("empresa_nome"),
            )
            return None
        return dados
    except Exception as e:
        logger.warning("enriquecer_via_ia: erro ao processar resposta da IA: %s", e)
        return None


# ── Orquestração ─────────────────────────────────────────────────────────

def enriquecer_lead(
    nome: str, email: str, telefone: str, openai_api_key: str,
    *,
    nivel_raciocinio: str = NIVEL_PADRAO,
    buscar_socios: bool = True,
    buscar_fundacao: bool = True,
    buscar_processos: bool = True,
    campos_customizados: Optional[list[str]] = None,
) -> dict:
    """Roda o enriquecimento (só IA) pra um lead e retorna um dict
    estruturado com o resultado. status: "concluido" | "nao_encontrado" |
    "erro" (falha técnica, distinto de "não achou nada")."""
    resultado: dict = {
        "status": "nao_encontrado", "metodo_encontrado": None,
        "empresa_nome": None, "cnpj": None,
        "municipio": None, "uf": None, "website": None,
        "cargo": None, "linkedin_url": None, "resumo": None,
        "socios": None, "fundacao": None, "processos_jusbrasil": None,
        "extras": None, "erro": None,
    }

    if not openai_api_key:
        resultado["status"] = "erro"
        resultado["erro"] = "Chave da OpenAI não configurada — cadastre em Configurações."
        return resultado

    try:
        dados_ia = enriquecer_via_ia(
            nome, email, telefone, openai_api_key,
            nivel_raciocinio=nivel_raciocinio,
            buscar_socios=buscar_socios, buscar_fundacao=buscar_fundacao,
            buscar_processos=buscar_processos, campos_customizados=campos_customizados,
        )
    except Exception as e:
        logger.warning("enriquecer_lead: busca via IA falhou definitivamente: %s", e)
        resultado["status"] = "erro"
        resultado["erro"] = str(e)[:500]
        return resultado

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
            "socios": dados_ia.get("socios") if buscar_socios else None,
            "fundacao": dados_ia.get("fundacao") if buscar_fundacao else None,
            "processos_jusbrasil": (
                _normalizar_sim_nao(dados_ia.get("processos_jusbrasil")) if buscar_processos else None
            ),
            "extras": dados_ia.get("extras") if campos_customizados else None,
        })

    return resultado


def enriquecer_leads_em_lote(
    leads: list[dict],
    openai_api_key: str,
    callback: Optional[Callable[[int, int, str], None]] = None,
    **opcoes,
) -> list[dict]:
    """Roda enriquecer_lead pra cada item de `leads` (cada um com
    nome/email/telefone), na ordem, chamando callback(atual, total,
    mensagem) a cada lead concluído — mesmo contrato de progresso já usado
    pelas buscas de CNPJ/Maps do app (ver modules/casa_dos_dados.py).
    `**opcoes` é repassado direto pra enriquecer_lead (nivel_raciocinio,
    buscar_socios, buscar_fundacao, buscar_processos, campos_customizados).
    Retorna uma lista de dicts: os campos originais do lead + os campos de
    enriquecer_lead()."""
    total = len(leads)
    resultados = []
    for i, lead in enumerate(leads, start=1):
        nome = (lead.get("nome") or "").strip()
        email = (lead.get("email") or "").strip()
        telefone = (lead.get("telefone") or "").strip()
        r = enriquecer_lead(nome, email, telefone, openai_api_key, **opcoes)
        resultados.append({
            "nome_lead": nome, "email": email, "telefone": telefone,
            **r,
        })
        if callback:
            rotulo = r.get("empresa_nome") or nome or email or telefone or "lead"
            callback(i, total, f"{rotulo} — {r['status']}")
    return resultados
