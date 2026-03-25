"""
Catálogo de nichos e subnichos para prospecção.

Cada nicho define:
  - query: termo base usado na busca do Google Maps
  - subnichos: lista de especialidades predefinidas
"""

NICHOS: dict[str, dict] = {
    "Advogado / Escritório de Advocacia": {
        "query": "escritório de advocacia",
        "subnichos": [
            "Trabalhista",
            "Tributário",
            "Família e Divórcio",
            "Criminal / Penal",
            "Imobiliário",
            "Previdenciário / INSS",
            "Empresarial / Societário",
            "Cível",
            "Ambiental",
            "Direito Digital",
            "Propriedade Intelectual",
        ],
    },
    "Médico / Clínica Médica": {
        "query": "clínica médica",
        "subnichos": [
            "Cardiologia",
            "Ortopedia e Traumatologia",
            "Dermatologia",
            "Pediatria",
            "Ginecologia e Obstetrícia",
            "Psiquiatria",
            "Neurologia",
            "Oftalmologia",
            "Urologia",
            "Oncologia",
            "Endocrinologia",
            "Gastroenterologia",
        ],
    },
    "Dentista / Clínica Odontológica": {
        "query": "clínica odontológica",
        "subnichos": [
            "Ortodontia",
            "Implantodontia",
            "Periodontia",
            "Endodontia",
            "Odontopediatria",
            "Prótese Dentária",
            "Harmonização Orofacial",
        ],
    },
    "Psicólogo / Clínica de Psicologia": {
        "query": "clínica de psicologia",
        "subnichos": [
            "Psicoterapia Individual",
            "Psicologia Infantil",
            "Terapia de Casal",
            "Psicologia Organizacional",
            "Neuropsicologia",
            "Terapia Cognitivo-Comportamental",
        ],
    },
    "Contador / Escritório Contábil": {
        "query": "escritório de contabilidade",
        "subnichos": [
            "Contabilidade Empresarial",
            "Planejamento Tributário",
            "Auditoria",
            "Departamento Pessoal / RH",
            "Abertura de Empresas",
            "Contabilidade para MEI",
        ],
    },
    "Arquiteto / Escritório de Arquitetura": {
        "query": "escritório de arquitetura",
        "subnichos": [
            "Arquitetura Residencial",
            "Arquitetura Comercial",
            "Design de Interiores",
            "Urbanismo e Paisagismo",
            "Arquitetura Sustentável",
        ],
    },
    "Engenheiro / Escritório de Engenharia": {
        "query": "escritório de engenharia",
        "subnichos": [
            "Engenharia Civil",
            "Engenharia Elétrica",
            "Engenharia Mecânica",
            "Engenharia Ambiental",
            "Engenharia de Segurança do Trabalho",
        ],
    },
    "Nutricionista / Clínica de Nutrição": {
        "query": "clínica de nutrição",
        "subnichos": [
            "Nutrição Esportiva",
            "Nutrição Clínica",
            "Emagrecimento",
            "Nutrição Infantil",
            "Nutrição Oncológica",
        ],
    },
    "Fisioterapeuta / Clínica de Fisioterapia": {
        "query": "clínica de fisioterapia",
        "subnichos": [
            "Fisioterapia Ortopédica",
            "Fisioterapia Neurológica",
            "Pilates Clínico",
            "Fisioterapia Esportiva",
            "RPG / Reeducação Postural",
        ],
    },
    "Corretor / Imobiliária": {
        "query": "imobiliária",
        "subnichos": [
            "Venda de Imóveis Residenciais",
            "Venda de Imóveis Comerciais",
            "Aluguel Residencial",
            "Aluguel Comercial",
            "Lançamentos / Incorporação",
        ],
    },
    "Escola / Curso": {
        "query": "escola",
        "subnichos": [
            "Educação Infantil",
            "Ensino Fundamental",
            "Ensino Médio",
            "Curso de Idiomas",
            "Curso Técnico / Profissionalizante",
            "Curso Preparatório / Pré-vestibular",
        ],
    },
    "Outro / Personalizado": {
        "query": "",
        "subnichos": [],
    },
}

# Mapeamento estado (sigla → nome completo) para buscas por estado
ESTADOS: dict[str, str] = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal",
    "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
    "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco",
    "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima",
    "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}

NOMES_NICHOS = list(NICHOS.keys())
SIGLAS_ESTADOS = list(ESTADOS.keys())
