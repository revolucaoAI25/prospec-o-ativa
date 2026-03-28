"""
Catálogo de CNAEs para uso no seletor da busca Casa dos Dados.

Formato de código: 7 dígitos sem pontuação (ex: "6911701")
"""

CNAES: list[dict] = [
    # ── JURÍDICO ──────────────────────────────────────────────────────────────
    {"setor": "Jurídico",       "codigo": "6911701", "descricao": "Advocacia"},
    {"setor": "Jurídico",       "codigo": "6911702", "descricao": "Atividades auxiliares da justiça"},
    {"setor": "Jurídico",       "codigo": "6912500", "descricao": "Cartórios e serviços notariais"},
    {"setor": "Jurídico",       "codigo": "6911703", "descricao": "Agentes de propriedade industrial"},

    # ── CONTABILIDADE / FINANÇAS ───────────────────────────────────────────────
    {"setor": "Contabilidade",  "codigo": "6920601", "descricao": "Atividades de contabilidade"},
    {"setor": "Contabilidade",  "codigo": "6920602", "descricao": "Elaboração de cadastros empresariais"},
    {"setor": "Contabilidade",  "codigo": "6920603", "descricao": "Auditoria e análise de sistemas contábeis"},
    {"setor": "Contabilidade",  "codigo": "6922500", "descricao": "Consultoria e auditoria contábil e tributária"},
    {"setor": "Finanças",       "codigo": "6612601", "descricao": "Corretoras de títulos e valores mobiliários"},
    {"setor": "Finanças",       "codigo": "6613400", "descricao": "Administração de cartões de crédito"},
    {"setor": "Finanças",       "codigo": "6621501", "descricao": "Peritos e avaliadores de seguros"},
    {"setor": "Finanças",       "codigo": "6622300", "descricao": "Corretores e agentes de seguros"},
    {"setor": "Finanças",       "codigo": "6636201", "descricao": "Clubes e fundos de investimento"},
    {"setor": "Finanças",       "codigo": "6499301", "descricao": "Correspondentes bancários"},

    # ── SAÚDE ─────────────────────────────────────────────────────────────────
    {"setor": "Saúde",          "codigo": "8630503", "descricao": "Atividade médica ambulatorial (cirurgias)"},
    {"setor": "Saúde",          "codigo": "8630504", "descricao": "Atividade odontológica"},
    {"setor": "Saúde",          "codigo": "8630506", "descricao": "Serviços de vacinação e imunização"},
    {"setor": "Saúde",          "codigo": "8630507", "descricao": "Atividade de psicologia e psicanálise"},
    {"setor": "Saúde",          "codigo": "8630508", "descricao": "Atividade de fisioterapia"},
    {"setor": "Saúde",          "codigo": "8630509", "descricao": "Atividade de terapia ocupacional"},
    {"setor": "Saúde",          "codigo": "8630511", "descricao": "Atividade de nutricionista"},
    {"setor": "Saúde",          "codigo": "8630512", "descricao": "Assistência ambulatorial não especificada"},
    {"setor": "Saúde",          "codigo": "8640202", "descricao": "Laboratórios clínicos"},
    {"setor": "Saúde",          "codigo": "8650001", "descricao": "Atividades de enfermagem"},
    {"setor": "Saúde",          "codigo": "8650003", "descricao": "Atividades de psicologia"},
    {"setor": "Saúde",          "codigo": "8650004", "descricao": "Atividades de fisioterapia (liberal)"},
    {"setor": "Saúde",          "codigo": "8650006", "descricao": "Atividades de fonoaudiologia"},
    {"setor": "Saúde",          "codigo": "8650099", "descricao": "Outros profissionais de saúde"},
    {"setor": "Saúde",          "codigo": "8690901", "descricao": "Atividades de fisioterapia (clínica)"},
    {"setor": "Saúde",          "codigo": "8690999", "descricao": "Outras atividades de atenção à saúde"},
    {"setor": "Saúde",          "codigo": "4771701", "descricao": "Comércio varejista de farmácias"},
    {"setor": "Saúde",          "codigo": "4771703", "descricao": "Comércio de artigos médicos e ortopédicos"},

    # ── EDUCAÇÃO ──────────────────────────────────────────────────────────────
    {"setor": "Educação",       "codigo": "8511200", "descricao": "Educação infantil — creche"},
    {"setor": "Educação",       "codigo": "8512100", "descricao": "Educação infantil — pré-escola"},
    {"setor": "Educação",       "codigo": "8513900", "descricao": "Ensino fundamental"},
    {"setor": "Educação",       "codigo": "8520100", "descricao": "Ensino médio"},
    {"setor": "Educação",       "codigo": "8531700", "descricao": "Educação superior — graduação"},
    {"setor": "Educação",       "codigo": "8541400", "descricao": "Educação profissional técnica"},
    {"setor": "Educação",       "codigo": "8591100", "descricao": "Ensino de esportes"},
    {"setor": "Educação",       "codigo": "8592901", "descricao": "Ensino de dança"},
    {"setor": "Educação",       "codigo": "8592903", "descricao": "Ensino de música"},
    {"setor": "Educação",       "codigo": "8593700", "descricao": "Ensino de idiomas"},
    {"setor": "Educação",       "codigo": "8599601", "descricao": "Autoescolas (formação de condutores)"},
    {"setor": "Educação",       "codigo": "8599603", "descricao": "Treinamento em informática"},
    {"setor": "Educação",       "codigo": "8599604", "descricao": "Treinamento profissional e gerencial"},
    {"setor": "Educação",       "codigo": "8599605", "descricao": "Cursos preparatórios para concursos"},
    {"setor": "Educação",       "codigo": "8599699", "descricao": "Outras atividades de ensino"},

    # ── TECNOLOGIA / TI ───────────────────────────────────────────────────────
    {"setor": "Tecnologia",     "codigo": "6201501", "descricao": "Desenvolvimento de software customizável"},
    {"setor": "Tecnologia",     "codigo": "6201502", "descricao": "Web design"},
    {"setor": "Tecnologia",     "codigo": "6202300", "descricao": "Desenvolvimento de software (licenciamento)"},
    {"setor": "Tecnologia",     "codigo": "6203100", "descricao": "Desenvolvimento de software não-customizável"},
    {"setor": "Tecnologia",     "codigo": "6209100", "descricao": "Suporte técnico e manutenção de TI"},
    {"setor": "Tecnologia",     "codigo": "6311900", "descricao": "Tratamento de dados e hospedagem"},
    {"setor": "Tecnologia",     "codigo": "6319400", "descricao": "Portais e provedores de conteúdo internet"},
    {"setor": "Tecnologia",     "codigo": "6399200", "descricao": "Outras atividades de tecnologia da informação"},
    {"setor": "Tecnologia",     "codigo": "9511800", "descricao": "Reparação de computadores e equipamentos"},

    # ── CONSTRUÇÃO / ENGENHARIA ───────────────────────────────────────────────
    {"setor": "Construção",     "codigo": "4110700", "descricao": "Incorporação de empreendimentos imobiliários"},
    {"setor": "Construção",     "codigo": "4120400", "descricao": "Construção de edifícios"},
    {"setor": "Construção",     "codigo": "4321500", "descricao": "Instalação e manutenção elétrica"},
    {"setor": "Construção",     "codigo": "4322301", "descricao": "Instalações hidráulicas e sanitárias"},
    {"setor": "Construção",     "codigo": "4322302", "descricao": "Instalação de ar condicionado"},
    {"setor": "Construção",     "codigo": "4329103", "descricao": "Instalação e manutenção de elevadores"},
    {"setor": "Construção",     "codigo": "4330404", "descricao": "Pintura de edifícios"},
    {"setor": "Construção",     "codigo": "4399103", "descricao": "Obras de alvenaria"},
    {"setor": "Construção",     "codigo": "7111100", "descricao": "Serviços de arquitetura"},
    {"setor": "Construção",     "codigo": "7112000", "descricao": "Serviços de engenharia"},
    {"setor": "Construção",     "codigo": "7119701", "descricao": "Cartografia, topografia e geodésia"},
    {"setor": "Construção",     "codigo": "7119704", "descricao": "Serviços de perícia técnica"},

    # ── IMOBILIÁRIO ───────────────────────────────────────────────────────────
    {"setor": "Imobiliário",    "codigo": "6810201", "descricao": "Compra e venda de imóveis próprios"},
    {"setor": "Imobiliário",    "codigo": "6810202", "descricao": "Aluguel de imóveis próprios"},
    {"setor": "Imobiliário",    "codigo": "6821801", "descricao": "Corretagem — compra e venda de imóveis"},
    {"setor": "Imobiliário",    "codigo": "6821802", "descricao": "Corretagem — aluguel de imóveis"},
    {"setor": "Imobiliário",    "codigo": "6822600", "descricao": "Gestão e administração de propriedade imobiliária"},

    # ── MARKETING / PUBLICIDADE ───────────────────────────────────────────────
    {"setor": "Marketing",      "codigo": "7311400", "descricao": "Agências de publicidade"},
    {"setor": "Marketing",      "codigo": "7312200", "descricao": "Agenciamento de espaços para publicidade"},
    {"setor": "Marketing",      "codigo": "7319002", "descricao": "Promoção de vendas"},
    {"setor": "Marketing",      "codigo": "7319003", "descricao": "Marketing direto"},
    {"setor": "Marketing",      "codigo": "7319004", "descricao": "Consultoria em publicidade"},
    {"setor": "Marketing",      "codigo": "7320300", "descricao": "Pesquisas de mercado e opinião pública"},

    # ── ALIMENTAÇÃO ───────────────────────────────────────────────────────────
    {"setor": "Alimentação",    "codigo": "5611201", "descricao": "Restaurantes e similares"},
    {"setor": "Alimentação",    "codigo": "5611203", "descricao": "Lanchonetes, casas de chá e similares"},
    {"setor": "Alimentação",    "codigo": "5611205", "descricao": "Bares e estabelecimentos de bebidas"},
    {"setor": "Alimentação",    "codigo": "5612100", "descricao": "Serviços ambulantes de alimentação"},
    {"setor": "Alimentação",    "codigo": "5620101", "descricao": "Fornecimento de alimentos para empresas"},
    {"setor": "Alimentação",    "codigo": "5620102", "descricao": "Serviços de alimentação para eventos"},
    {"setor": "Alimentação",    "codigo": "1091102", "descricao": "Padarias e confeitarias"},

    # ── BELEZA / ESTÉTICA ─────────────────────────────────────────────────────
    {"setor": "Beleza",         "codigo": "9602501", "descricao": "Cabeleireiros, manicure e pedicure"},
    {"setor": "Beleza",         "codigo": "9602502", "descricao": "Estética e outros tratamentos de beleza"},

    # ── TRANSPORTE / LOGÍSTICA ────────────────────────────────────────────────
    {"setor": "Transporte",     "codigo": "4930201", "descricao": "Frete rodoviário de carga geral"},
    {"setor": "Transporte",     "codigo": "4930202", "descricao": "Frota própria para transporte de carga"},
    {"setor": "Transporte",     "codigo": "4921301", "descricao": "Transporte rodoviário coletivo de passageiros"},
    {"setor": "Transporte",     "codigo": "5231102", "descricao": "Guarda-móveis"},
    {"setor": "Transporte",     "codigo": "5231103", "descricao": "Depósitos de mercadorias para terceiros"},
    {"setor": "Transporte",     "codigo": "5250803", "descricao": "Agenciamento de cargas"},
    {"setor": "Transporte",     "codigo": "5320201", "descricao": "Serviços de malote e encomendas"},
    {"setor": "Transporte",     "codigo": "4921302", "descricao": "Transporte rodoviário intermunicipal"},

    # ── TURISMO / HOSPEDAGEM ──────────────────────────────────────────────────
    {"setor": "Turismo",        "codigo": "5510801", "descricao": "Hotéis"},
    {"setor": "Turismo",        "codigo": "5510802", "descricao": "Apart-hotéis"},
    {"setor": "Turismo",        "codigo": "5510803", "descricao": "Motéis"},
    {"setor": "Turismo",        "codigo": "5590601", "descricao": "Albergues e pousadas"},
    {"setor": "Turismo",        "codigo": "7911200", "descricao": "Agências de viagens"},
    {"setor": "Turismo",        "codigo": "7912100", "descricao": "Operadoras turísticas"},
    {"setor": "Turismo",        "codigo": "7990200", "descricao": "Serviços de reservas e turismo"},

    # ── COMÉRCIO VAREJISTA ────────────────────────────────────────────────────
    {"setor": "Comércio",       "codigo": "4711302", "descricao": "Supermercado e mercadinho"},
    {"setor": "Comércio",       "codigo": "4751200", "descricao": "Equipamentos e suprimentos de informática"},
    {"setor": "Comércio",       "codigo": "4752100", "descricao": "Equipamentos de telefonia e comunicação"},
    {"setor": "Comércio",       "codigo": "4753900", "descricao": "Eletrodomésticos"},
    {"setor": "Comércio",       "codigo": "4761001", "descricao": "Livros, revistas e jornais"},
    {"setor": "Comércio",       "codigo": "4772500", "descricao": "Cosméticos, perfumaria e higiene"},
    {"setor": "Comércio",       "codigo": "4774100", "descricao": "Artigos de óptica"},
    {"setor": "Comércio",       "codigo": "4781400", "descricao": "Vestuário e acessórios"},
    {"setor": "Comércio",       "codigo": "4782201", "descricao": "Calçados"},
    {"setor": "Comércio",       "codigo": "4789004", "descricao": "Pet shop — animais e alimentos"},
    {"setor": "Comércio",       "codigo": "4744005", "descricao": "Materiais de construção"},
    {"setor": "Comércio",       "codigo": "4742300", "descricao": "Material elétrico"},

    # ── VEÍCULOS ──────────────────────────────────────────────────────────────
    {"setor": "Veículos",       "codigo": "4511101", "descricao": "Comércio de veículos novos"},
    {"setor": "Veículos",       "codigo": "4511102", "descricao": "Comércio de automóveis e utilitários novos"},
    {"setor": "Veículos",       "codigo": "4530701", "descricao": "Peças e acessórios para veículos"},
    {"setor": "Veículos",       "codigo": "4541201", "descricao": "Comércio de motocicletas novas"},
    {"setor": "Veículos",       "codigo": "4520001", "descricao": "Manutenção e reparação de automóveis"},
    {"setor": "Veículos",       "codigo": "4520002", "descricao": "Lanternagem e pintura de veículos"},
    {"setor": "Veículos",       "codigo": "4520003", "descricao": "Manutenção de caminhões"},

    # ── SERVIÇOS GERAIS ───────────────────────────────────────────────────────
    {"setor": "Serviços",       "codigo": "8011101", "descricao": "Vigilância e segurança privada"},
    {"setor": "Serviços",       "codigo": "8013901", "descricao": "Instalação de sistemas de segurança"},
    {"setor": "Serviços",       "codigo": "8111700", "descricao": "Serviços combinados para edifícios"},
    {"setor": "Serviços",       "codigo": "8112500", "descricao": "Condomínios prediais"},
    {"setor": "Serviços",       "codigo": "8121400", "descricao": "Limpeza em prédios e domicílios"},
    {"setor": "Serviços",       "codigo": "8122200", "descricao": "Controle de pragas e dedetização"},
    {"setor": "Serviços",       "codigo": "8130300", "descricao": "Atividades paisagísticas e jardinagem"},
    {"setor": "Serviços",       "codigo": "8299701", "descricao": "Cobranças e informações cadastrais"},
    {"setor": "Serviços",       "codigo": "8299706", "descricao": "Tradução e interpretação"},
    {"setor": "Serviços",       "codigo": "8219999", "descricao": "Preparação de documentos e apoio adm."},

    # ── AGROPECUÁRIA ──────────────────────────────────────────────────────────
    {"setor": "Agropecuária",   "codigo": "0111301", "descricao": "Cultivo de trigo"},
    {"setor": "Agropecuária",   "codigo": "0111302", "descricao": "Cultivo de milho"},
    {"setor": "Agropecuária",   "codigo": "0111303", "descricao": "Cultivo de arroz"},
    {"setor": "Agropecuária",   "codigo": "0151201", "descricao": "Criação de bovinos para corte"},
    {"setor": "Agropecuária",   "codigo": "0151202", "descricao": "Criação de bovinos para leite"},
    {"setor": "Agropecuária",   "codigo": "0155501", "descricao": "Criação de suínos"},
    {"setor": "Agropecuária",   "codigo": "0159801", "descricao": "Apicultura"},
    {"setor": "Agropecuária",   "codigo": "0311601", "descricao": "Pesca em água salgada"},
    {"setor": "Agropecuária",   "codigo": "0210101", "descricao": "Cultivo de eucalipto"},

    # ── RECURSOS HUMANOS / CONSULTORIA ────────────────────────────────────────
    {"setor": "RH / Consultoria", "codigo": "7020400", "descricao": "Atividades de consultoria em gestão empresarial"},
    {"setor": "RH / Consultoria", "codigo": "7810800", "descricao": "Seleção e agenciamento de mão-de-obra"},
    {"setor": "RH / Consultoria", "codigo": "7820500", "descricao": "Locação de mão-de-obra temporária"},
    {"setor": "RH / Consultoria", "codigo": "7830200", "descricao": "Fornecimento e gestão de recursos humanos"},
    {"setor": "RH / Consultoria", "codigo": "7490101", "descricao": "Serviços de tradução e interpretação"},
    {"setor": "RH / Consultoria", "codigo": "7490104", "descricao": "Atividades de intermediação e agenciamento"},
]


def buscar_cnaes(termo: str) -> list[dict]:
    """Filtra CNAEs por código ou descrição (case-insensitive)."""
    t = termo.strip().lower()
    if not t:
        return CNAES
    return [
        c for c in CNAES
        if t in c["codigo"].lower() or t in c["descricao"].lower() or t in c["setor"].lower()
    ]


# Opções formatadas para st.multiselect: "6911701 — Advocacia (Jurídico)"
OPCOES_MULTISELECT: list[str] = [
    f"{c['codigo']} — {c['descricao']} [{c['setor']}]"
    for c in CNAES
]

# Mapa código → descrição para lookup rápido
CODIGO_PARA_DESC: dict[str, str] = {c["codigo"]: c["descricao"] for c in CNAES}
