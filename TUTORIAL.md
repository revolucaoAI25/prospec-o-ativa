# Lead Extractor — Guia Completo da Plataforma
**Revolução AI** · suporte@revolucao-ai.com

---

## Bem-vindo ao Lead Extractor

O Lead Extractor é a sua central de prospecção ativa. Em vez de gastar horas procurando contatos manualmente, você encontra centenas de empresas qualificadas em segundos — com telefone, e-mail, site e muito mais.

A plataforma oferece dois motores de busca complementares e um sistema de automação:

- **Google Maps** — ideal para encontrar negócios locais por nicho e localização, com dados de contato atualizados (telefone, site, avaliações)
- **Busca por CNPJ** — ideal para prospecção B2B estruturada, com dados fiscais completos (sócios, regime tributário, capital social, CNAE)
- **Automações** — buscas programadas que rodam sozinhas nos dias e horários que você definir, exportando os leads direto para o Google Sheets

Use os três recursos juntos para uma estratégia de prospecção completa e contínua.

---

## 1. Configurando sua Conta

Antes de começar a buscar leads, reserve alguns minutos para configurar sua conta. Cada item abaixo desbloqueia uma funcionalidade diferente.

### 1.1 Chave da API do Google Maps

A busca via Google Maps exige uma chave de API própria do Google. Essa chave é o que permite que o sistema consulte dados reais de lugares diretamente no Google.

**Como obter sua chave:**

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Crie um projeto novo (ou use um existente)
3. No menu lateral, vá em **APIs e Serviços → Biblioteca**
4. Pesquise por **"Places API"** (sem o "New") e ative-a
5. Vá em **Credenciais → Criar credencial → Chave de API**
6. Copie a chave gerada

> **Atenção:** Ative a **Places API** (versão clássica), não a "Places API (New)". São produtos diferentes com preços e comportamentos distintos.

**Como configurar no Lead Extractor:**

1. Acesse **Configurações → Google Maps API**
2. Cole a chave no campo correspondente
3. Clique em **Salvar**

**Pool de múltiplas chaves (opcional):**

Você pode cadastrar várias chaves de API do Google Maps. O sistema usa cada uma automaticamente e alterna para a próxima quando o limite mensal de uma delas for atingido. Isso é útil para aumentar o volume de buscas sem custos extras imediatos.

- Acesse **Configurações → Pool de Chaves Maps**
- Adicione cada chave no campo e clique em **Adicionar**
- O sistema mostra o uso atual de cada chave com indicadores 🟢 (livre) / 🟡 (perto do limite) / 🔴 (esgotada)

> **Se o administrador da plataforma já configurou a chave:** o campo de API key não aparecerá para você — a chave já está ativa automaticamente na sua conta.

---

### 1.2 Chave Apify (Fallback Automático para o Google Maps)

O Apify é uma plataforma de extração de dados alternativa ao Google Maps. No Lead Extractor, ela funciona como **fallback automático**: quando a cota da sua chave do Google Maps é esgotada, ou se você não tem chave do Google Maps configurada, o sistema usa o Apify automaticamente para continuar a busca — sem interromper o fluxo e sem aviso ao usuário.

**Custo:** $4 por 1.000 resultados (bem mais barato que o Google Maps quando a cota gratuita acaba).

**Como criar uma conta no Apify:**

1. Acesse [apify.com](https://apify.com) e clique em **Sign Up**
2. Crie uma conta (pode usar Google ou e-mail)
3. O plano gratuito inclui **$5 de crédito por mês** — suficiente para ~1.250 resultados mensais sem pagar nada
4. Para volumes maiores, o plano **Starter** começa em $49/mês

**Como obter sua chave de API:**

1. Faça login em [console.apify.com](https://console.apify.com)
2. No menu lateral esquerdo, clique em **Settings**
3. Vá na aba **Integrations**
4. Copie o **Personal API token** (começa com `apify_api_...`)

**Como configurar no Lead Extractor:**

1. Acesse **Configurações → 🤖 Apify API Key**
2. Cole o token no campo
3. Clique em **Salvar chave Apify**

A partir daí o fallback está ativo. Se quiser usar **somente o Apify** (sem chave do Google Maps), basta não configurar a chave do Google Maps — o sistema detecta automaticamente e usa o Apify desde a primeira busca.

---

### 1.3 Conectar Conta do Google (para exportação automática)



Para exportar resultados diretamente para o Google Sheets de forma automática, você precisa autorizar o Lead Extractor a acessar sua conta Google.

**Como conectar:**

1. Vá em **Configurações → Google Sheets**
2. Clique em **Conectar conta Google**
3. Faça login com sua conta Google na janela que abrir
4. Autorize o acesso às planilhas
5. Pronto — você verá uma mensagem de confirmação

Após conectar, o Lead Extractor pode criar e atualizar planilhas automaticamente na sua conta Google Drive.

> **Nota de privacidade:** A autorização concede acesso apenas às planilhas criadas pelo próprio Lead Extractor. Seus outros arquivos do Google Drive não são acessados.

---

### 1.4 Vincular Planilha Google

Com a conta Google conectada, você pode escolher para qual planilha os leads serão exportados automaticamente.

**Como vincular:**

1. Em **Configurações → Google Sheets**, clique em **Selecionar planilha**
2. Escolha uma planilha existente da lista, ou crie uma nova diretamente pelo Lead Extractor
3. Ative a opção **Exportação automática** para que os resultados de cada busca sejam enviados à planilha assim que concluídos

> **Dica:** Crie planilhas separadas por nicho ou campanha para manter sua prospecção organizada.

---

## 2. Buscando Leads no Google Maps

A busca via Google Maps encontra estabelecimentos reais cadastrados no Google — com nome, endereço, telefone, site e avaliações dos clientes.

### 2.1 Como funciona a busca

1. Acesse a aba **Nova Busca → Google Maps**
2. Preencha os campos de busca
3. Clique em **Buscar**
4. Aguarde os resultados — a barra de progresso indica o andamento

Os resultados aparecem em uma tabela com todos os dados disponíveis. Cada linha é um lead.

---

### 2.2 Campos de busca e filtros

**País**
Selecione o país antes de preencher os outros campos. A seleção do país muda dinamicamente as opções de localização disponíveis (estado e cidade, ou apenas cidade para países fora do Brasil).

**Nicho**
O tipo de negócio que você quer prospectar. Use os nichos pré-cadastrados ou escreva um termo personalizado no campo **Termo de busca customizado**.

> **Dica:** Seja específico. Em vez de "escritório", tente "escritório de advocacia trabalhista" ou "advogado trabalhista". O Google Maps retorna resultados melhores com termos mais precisos.

**Subnicho / Porte**
Refina ainda mais o nicho. Por exemplo: nicho "Advogado", subnicho "Trabalhista" ou "Tributário". Combine com o porte do escritório (pequeno, médio, grande) quando aplicável.

**Estado e Cidade**
- Para o Brasil: selecione o estado primeiro, depois a cidade
- Para outros países: insira o nome da cidade diretamente
- Deixar a cidade em branco busca em todo o estado

**Quantidade máxima de resultados**
Define o teto de leads que a busca vai retornar. O valor padrão é 300. Ajuste conforme sua necessidade — buscas menores são mais rápidas.

> **Importante:** O Google Maps tem um limite técnico de aproximadamente 60 resultados por combinação de busca + localidade. O sistema faz várias buscas automaticamente para contornar isso, mas em nichos muito saturados (ex: "restaurante em São Paulo") o retorno pode ser menor que o esperado.

**Filtros de qualidade**
Após a busca, você pode filtrar os resultados por:

- **Apenas com telefone** — exclui leads sem número de contato
- **Apenas com site** — útil para prospecção digital
- **Apenas novos** — exclui leads que já aparecem no seu histórico (evita duplicatas entre campanhas)

> **Boa prática:** Use o filtro **Apenas novos** quando estiver fazendo buscas recorrentes no mesmo nicho. Isso garante que você sempre prospectará contatos diferentes.

---

### 2.3 Dados disponíveis nos resultados do Maps

| Campo | Descrição |
|---|---|
| Nome | Nome do estabelecimento |
| Telefone | Número de contato principal |
| Site | URL do site (se cadastrado) |
| Endereço | Endereço completo |
| Município / UF | Cidade e estado |
| Avaliação | Nota no Google (1-5) |
| Nº de avaliações | Total de reviews |
| Nicho / Subnicho | Categorias usadas na busca |
| URL Maps | Link direto para o perfil no Google Maps |

---

### 2.4 Limites de uso e custos

**Como o sistema faz as chamadas à API:**

Cada resultado retornado consome chamadas do Google Maps de acordo com o que você ativou:

| Configuração | Chamadas por resultado | Limite gratuito/mês |
|---|---|---|
| Telefone **ativado** | 2 (Text Search + Contact Data) | ~10.000 resultados |
| Telefone **desativado** | 1 (só Text Search) | ~10.000 resultados |

A avaliação (estrelas e nº de reviews) vem embutida na primeira chamada — **sem custo adicional**.

**O que acontece quando a cota acaba:**

Se todas as chaves do Google Maps atingirem o limite mensal e você tiver configurado uma chave Apify, o sistema troca automaticamente para o Apify e continua a busca normalmente. O custo no Apify é **$4 por 1.000 resultados** (valores em dólar, debitados do saldo da sua conta Apify).

Se não houver chave Apify configurada, o sistema exibe um aviso e a busca é interrompida.

**Custo além da cota gratuita do Google Maps:**

| Tipo de chamada | Custo por 1.000 |
|---|---|
| Text Search (busca de texto) | US$ 32 |
| Contact Data (telefone + site) | US$ 17 |
| **Total com telefone ativado** | **US$ 49 / 1.000 resultados** |
| **Total sem telefone** | **US$ 32 / 1.000 resultados** |

> **Dica de economia:** Configure um limite de gastos diários no Google Cloud Console para evitar cobranças inesperadas — acesse **Faturamento → Orçamentos e alertas**. Usar um pool de várias chaves também distribui o consumo e amplia a cota gratuita total.

> **Importante:** Valores e limites são definidos pelo Google e podem mudar. Consulte a [página oficial de preços do Google Maps Platform](https://mapsplatform.google.com/pricing/) para informações atualizadas.

---

## 3. Buscando Leads por CNPJ (Receita Federal)

A busca por CNPJ consulta a base da Receita Federal e retorna dados fiscais completos de empresas brasileiras. É a ferramenta ideal para prospecção B2B estruturada, quando você quer encontrar empresas por segmento, porte ou localização com informações cadastrais verificadas.

### 3.1 Como funciona a busca

1. Acesse a aba **Nova Busca → Busca por CNPJ**
2. Preencha os filtros desejados
3. Defina a quantidade máxima de resultados (mínimo: 1)
4. Clique em **Buscar CNPJs**
5. Aguarde o processamento

> **Créditos:** Esta busca consome créditos da sua conta. Verifique seu saldo antes de iniciar (visível na sidebar). O sistema não inicia a busca se o saldo for insuficiente para o número de resultados solicitado.

---

### 3.2 Campos de busca e filtros

**Estado (UF)**
Filtra empresas ativas em um estado específico. Obrigatório para a maioria das buscas.

**Município**
Refina a busca para uma cidade específica dentro do estado selecionado.

**CNAE (Código de Atividade)**
O CNAE é o código que classifica a atividade econômica de uma empresa. Você pode buscar por código exato ou por descrição.

> **Exemplo:** CNAE 6911-7/01 corresponde a "Serviços advocatícios". Consulte a tabela CNAE da Receita Federal para encontrar o código do nicho que você prospecta.

**Natureza Jurídica**
Filtra pelo tipo de pessoa jurídica: MEI, LTDA, SA, EIRELI, etc.

**Simples Nacional / MEI**
Filtra empresas optantes pelo Simples Nacional ou MEI — útil para identificar empresas de menor porte.

**Quantidade máxima de resultados**
Define o teto de CNPJs retornados. O mínimo é 1. O sistema debita créditos apenas pela quantidade efetivamente encontrada — se a busca retornar 80 empresas e o limite era 100, você pagará por 80.

---

### 3.3 Dados disponíveis nos resultados do CNPJ

| Campo | Descrição |
|---|---|
| Nome / Razão Social | Nome da empresa na Receita Federal |
| CNPJ | CNPJ formatado |
| Telefone / Telefone 2 | Números de contato cadastrados |
| Tipo de Telefone | Comercial, celular, etc. |
| E-mail | E-mail cadastrado na Receita |
| Endereço | Logradouro completo |
| Município / UF | Cidade e estado |
| CEP | Código postal |
| CNAE | Código e descrição da atividade principal |
| Natureza Jurídica | Tipo de empresa |
| Data de Abertura | Data de constituição da empresa |
| Capital Social | Capital registrado |
| Matriz / Filial | Indica se é sede ou filial |
| Simples optante | Sim/Não — optante pelo Simples Nacional |
| MEI optante | Sim/Não — microempreendedor individual |
| Sócio Principal | Nome do sócio majoritário |

---

### 3.4 Sistema de Créditos

O uso da busca por CNPJ consome créditos da sua conta. Cada lead retornado desconta 1 crédito.

**Como funciona:**
- O sistema verifica seu saldo antes de iniciar a busca
- Se o saldo for menor que o número de resultados solicitado, a busca não é iniciada
- Após a busca, apenas os leads efetivamente encontrados são debitados

**Renovação mensal:**
Seus créditos são renovados automaticamente a cada 30 dias, conforme o plano configurado pelo administrador. O saldo é **resetado** para o valor mensal — créditos não utilizados não acumulam para o próximo mês.

**Onde ver seu saldo:**
O saldo de créditos aparece na sidebar lateral, logo abaixo das informações da sua conta. Se a busca via Maps também tiver créditos configurados, os dois saldos aparecem separados.

> **Dica:** Use os filtros com precisão para não desperdiçar créditos em leads que não se encaixam no seu perfil de cliente ideal. Quanto mais específico o filtro, mais qualificada a lista.

---

### 3.5 Enriquecimento com Google Maps

Após uma busca por CNPJ, você pode cruzar automaticamente cada empresa com o Google Maps para complementar os dados com informações de presença digital: avaliação dos clientes, número de avaliações, link do perfil no Maps, site e telefone alternativo.

Os dados da Receita Federal **nunca são sobrescritos** — o enriquecimento apenas preenche campos que estavam vazios ou adiciona um segundo telefone quando o Maps retorna um número diferente do cadastrado.

**Como usar — opção 1: antes da busca (recomendado)**

Ative o toggle **🗺️ Enriquecer com Google Maps** que aparece logo acima do botão de busca. Com essa opção ativada, o enriquecimento roda automaticamente assim que a busca termina — antes de qualquer exportação automática.

**Como usar — opção 2: após a busca**

Se a busca já foi concluída sem o enriquecimento, clique no botão **🗺️ Enriquecer com Google Maps** que aparece acima dos resultados. O processo roda empresa por empresa e atualiza a prévia ao final.

**Campos adicionados pelo enriquecimento**

| Campo | Descrição |
|---|---|
| Avaliação | Nota média no Google (ex: 4.3) |
| Nº Avaliações | Quantidade total de avaliações |
| Google Maps | Link direto para o perfil da empresa no Maps |
| Telefone 2 | Segundo número, se diferente do cadastrado na Receita |
| Site | Site da empresa, se não havia um cadastrado no CNPJ |

**Quando vale a pena usar**

O enriquecimento é especialmente útil quando você quer qualificar a lista antes de prospectar — empresas com muitas avaliações positivas tendem a estar ativas e com movimento. Também ajuda a encontrar o site da empresa quando ele não está no cadastro da Receita Federal.

> **Custo:** O enriquecimento consome créditos Maps (1 por empresa), caso sua conta esteja configurada com créditos Maps. Se você usa chave de API própria, não há custo adicional de créditos na plataforma — apenas o custo da API do Google diretamente.

---

## 4. Exportação de Resultados

Cada busca gera uma lista de leads que pode ser exportada de duas formas: automaticamente para o Google Sheets ou manualmente em Excel.

### 4.1 Exportação Automática (Google Sheets)

Com a exportação automática ativada, cada busca concluída é enviada diretamente à planilha vinculada — sem nenhuma ação manual da sua parte.

**Como ativar:**
1. Configure a conta Google e vincule uma planilha (veja seção 1.2 e 1.3)
2. Em **Configurações**, ative a opção **Exportação automática**

A partir daí, toda busca adiciona os leads automaticamente à planilha, em uma aba separada por data/nicho.

> **Dica:** Crie uma planilha por campanha ou por cliente (se você for uma agência). Isso mantém os dados organizados e facilita o acompanhamento de cada ação de prospecção.

---

### 4.2 Exportação Manual (Excel)

Após qualquer busca, você pode baixar os resultados em Excel clicando no botão **Baixar Excel** na parte superior dos resultados.

O arquivo gerado inclui todas as colunas disponíveis para o tipo de busca realizada (Maps ou CNPJ), com formatação profissional e links clicáveis para sites e perfis no Google Maps.

**Quando usar exportação manual:**
- Quando você quer revisar os leads antes de enviá-los a uma planilha
- Para compartilhar com um time de vendas que não usa o Sheets
- Quando você quer salvar um snapshot específico de uma busca

---

### 4.3 O que está incluído na exportação

A exportação inclui todos os campos disponíveis para o tipo de busca, incluindo:
- Dados de contato (telefone, e-mail, site)
- Dados de localização (endereço, cidade, estado, CEP)
- Dados de contexto (nicho, subnicho/porte, data da busca)
- Dados fiscais completos (apenas na busca por CNPJ)

---

## 5. Histórico de Buscas

O Lead Extractor salva automaticamente todas as suas buscas anteriores na aba **Histórico**.

### 5.1 O que o histórico mostra

Cada busca salva exibe:
- **Tipo de busca** (Google Maps ou CNPJ/Receita Federal)
- **Nicho e localidade** buscados
- **Quantidade de leads** encontrados
- **Data e hora** da busca

Clique em qualquer busca para expandir e ver todos os leads daquela pesquisa novamente, com opção de exportar.

---

### 5.2 Usando o histórico na prática

**Evitar duplicatas:**
O filtro **Apenas novos** nas buscas do Maps cruza automaticamente com seu histórico. Leads que já apareceram em buscas anteriores são filtrados — você sempre recebe contatos frescos.

**Retomar campanhas:**
Se você precisou pausar uma campanha de prospecção, acesse o histórico para lembrar exatamente onde parou — quais nichos, quais cidades, quais resultados já foram trabalhados.

**Auditar resultados:**
Use o histórico para revisar campanhas anteriores e identificar padrões — quais nichos geram mais leads com telefone, quais cidades têm mais empresas do seu perfil ideal.

---

## 6. Automações — Buscas Programadas

A aba **Automações** permite criar buscas que rodam automaticamente nos dias e horários que você definir — sem precisar acessar a plataforma. Os leads são exportados direto para o Google Sheets assim que cada execução termina.

É a forma mais prática de manter uma esteira de prospecção contínua funcionando em segundo plano.

---

### 6.1 Como funciona

Você cria uma automação uma vez. A partir daí, ela:

1. Executa a busca (Maps ou CNPJ) nos dias e horários configurados
2. Aplica todos os filtros que você definiu
3. Deduplica automaticamente — nunca exporta um telefone ou CNPJ que já está no seu histórico
4. Exporta os novos leads para a planilha do Google Sheets vinculada
5. Agenda a próxima execução automaticamente

Se não houver créditos suficientes, a automação registra a tentativa como "Sem créditos" e agenda normalmente para a próxima vez.

---

### 6.2 Criando uma automação

1. Acesse a aba **Automações** na sidebar
2. Clique em **+ Nova Automação**
3. Preencha o formulário:

**Nome** — escolha um nome descritivo (ex: "Advogados SP — diário")

**Tipo de busca** — Google Maps ou CNPJ. Essa escolha não pode ser alterada depois.

**Filtros da busca** — os mesmos filtros disponíveis na busca manual:
- Maps: nicho, subnicho, país, cidade, estado, máximo de resultados
- CNPJ: CNAEs, UF, município, porte, matriz/filial, Simples Nacional, MEI, data de abertura, capital, tipo de telefone, e-mail

**Planilha destino** — selecione a planilha do Google Sheets para onde os leads serão exportados. Você precisa ter uma conta Google conectada e uma planilha vinculada nas Configurações.

**Agenda de execução:**
- *Dias da semana* — marque os dias em que a automação deve rodar (ex: Seg, Qua, Sex)
- *Horários* — selecione um ou mais horários por dia (ex: 08:00 e 14:00). Todos os horários usam o fuso de Brasília (BRT)
- *Data de encerramento* — opcional. Se preenchida, a automação se desativa automaticamente nessa data

4. Clique em **Criar Automação**

A automação entra em fila imediatamente e mostrará a próxima execução prevista no card.

---

### 6.3 Gerenciando automações

Cada automação aparece como um card com as informações principais e cinco botões de ação:

| Botão | O que faz |
|---|---|
| Pausar / Ativar | Suspende ou reativa a automação sem excluí-la |
| Executar agora | Dispara a execução imediatamente, fora do horário programado |
| Editar | Abre o formulário pré-preenchido para alterar qualquer configuração |
| Excluir | Remove a automação permanentemente (pede confirmação) |
| Execuções | Mostra o histórico das últimas execuções com status e quantidade de leads |

**Editando uma automação:**
Clique em **Editar** para abrir o painel com todos os campos pré-preenchidos. Você pode alterar filtros, planilha, dias, horários e data de encerramento. O tipo de busca (Maps ou CNPJ) não pode ser alterado após a criação.

---

### 6.4 Múltiplos horários por dia

Você pode selecionar mais de um horário para a mesma automação. Por exemplo: **08:00 e 18:00** faz a busca duas vezes por dia, sempre exportando apenas leads novos.

> **Dica:** Combine múltiplos horários em dias específicos para intensificar a prospecção em períodos de campanha sem criar várias automações separadas.

---

### 6.5 Deduplicação automática

As automações verificam automaticamente todos os telefones e CNPJs já salvos no seu histórico antes de exportar. Leads duplicados são descartados silenciosamente — sua planilha sempre recebe apenas contatos novos.

Isso vale mesmo que o mesmo contato apareça em buscas manuais anteriores ou em outras automações.

---

### 6.6 Histórico de execuções

Clique em **Execuções** em qualquer card para ver as últimas execuções com:

| Status | Significado |
|---|---|
| ✅ Sucesso | Busca concluída e leads exportados |
| ❌ Erro | Falha na busca (detalhes aparecem na linha) |
| 💳 Sem créditos | Créditos insuficientes no momento da execução |
| 📊 Sem Sheets | Planilha não configurada ou sem autorização |

---

### 6.7 Pré-requisitos para automações funcionarem

Antes de criar automações, certifique-se de que:

- **Para automações Maps:** você tem uma chave de API do Google Maps configurada (ou o administrador configurou a chave da plataforma)
- **Para automações CNPJ:** você tem créditos disponíveis na conta
- **Para exportação:** sua conta Google está conectada e uma planilha está vinculada nas Configurações (seções 1.3 e 1.4)

> **Importante:** As automações rodam em segundo plano no servidor enquanto a plataforma está ativa. Se você pausar uma automação e depois reativá-la, a próxima execução é recalculada automaticamente a partir do momento da reativação.

---

## 7. Boas Práticas para Resultados Melhores

### 7.1 Defina seu ICP antes de buscar

ICP (Ideal Customer Profile) é o perfil do seu cliente ideal. Antes de qualquer busca, responda:

- Qual é o nicho específico? (não apenas "empresas", mas "escritórios de advocacia trabalhista com 2-10 funcionários")
- Qual a localização ideal? (cidade? estado? todo o Brasil?)
- Qual o porte? (MEI, pequena empresa, médio porte?)
- O que precisa ter? (telefone, site, e-mail?)

Com esse perfil definido, seus filtros ficam muito mais precisos — e seus créditos rendem muito mais.

---

### 7.2 Google Maps ou CNPJ? Quando usar cada um

| Situação | Recomendação |
|---|---|
| Prospecção local (bairro, cidade) | Google Maps |
| Precisar de telefone direto | Google Maps |
| Querer ver avaliações e reputação | Google Maps |
| Prospecção B2B por segmento (CNAE) | Busca por CNPJ |
| Precisar de dados fiscais (sócios, capital) | Busca por CNPJ |
| Querer filtrar por MEI ou Simples Nacional | Busca por CNPJ |
| Identificar empresas abertas recentemente | Busca por CNPJ |

> **Estratégia combinada:** Faça uma busca por CNPJ para identificar as empresas do segmento e depois use o Google Maps para enriquecer com telefones e sites atualizados.

---

### 7.3 Organize por campanhas

Antes de exportar, defina uma estrutura de organização:

- Uma planilha por nicho (ex: "Leads — Advocacia SP")
- Uma aba por cidade ou campanha dentro de cada planilha
- Um CRM ou pipeline de vendas alimentado a partir dessas planilhas

O Lead Extractor gera os dados — a organização do processo de vendas é o que transforma leads em clientes.

---

### 7.4 Qualidade antes de quantidade

É melhor ter 50 leads altamente qualificados do que 500 leads genéricos. Use os filtros ao máximo:

- Sempre ative **Apenas com telefone** se sua estratégia é cold call
- Sempre ative **Apenas novos** em campanhas recorrentes
- Refine o nicho com termos específicos antes de ampliar o volume

---

## 8. Dúvidas Frequentes

**Por que minha busca no Maps retornou menos resultados do que o limite configurado?**
O Google Maps limita tecnicamente a cerca de 60 resultados por combinação de busca + localidade. Em cidades grandes ou nichos saturados, o sistema já faz múltiplas buscas automaticamente, mas o total pode ser menor do que o teto configurado. Tente dividir a busca por bairro ou subnicho.

**Meus créditos zeraram no meio da busca — o que acontece?**
A busca não é iniciada se o saldo for insuficiente para o número de resultados solicitado. Se quiser fazer uma busca menor para usar os créditos restantes, ajuste o limite máximo de resultados.

**Por que alguns leads do CNPJ não têm telefone ou e-mail?**
Os dados vêm diretamente do cadastro da Receita Federal. Se a empresa não informou esses dados no momento do registro (ou os dados estão desatualizados), eles não aparecem. Use o Google Maps para complementar nesses casos.

**Posso usar o Lead Extractor no celular?**
Sim, a plataforma é responsiva. A experiência é melhor em telas maiores (desktop ou tablet), especialmente para visualizar tabelas com muitas colunas.

**Minha automação não executou no horário programado — o que pode ter acontecido?**
Verifique se: (1) a automação está ativa (não pausada), (2) o horário configurado usa o fuso de Brasília, (3) os pré-requisitos estão atendidos (chave de API, créditos, conta Google). Se tudo estiver correto, use o botão **Executar agora** para forçar a execução e verificar se aparece algum erro no histórico.

**Posso ter automações Maps e CNPJ rodando ao mesmo tempo?**
Sim. Você pode criar quantas automações quiser, de qualquer tipo, com agendamentos independentes.

**A automação vai exportar leads que eu já tenho na planilha?**
Não. A deduplicação é automática — a automação cruza com todo o histórico de buscas da sua conta antes de exportar. Apenas leads com telefone ou CNPJ ainda não vistos são enviados à planilha.

**O que acontece se minha automação rodar e eu não tiver créditos?**
A execução é registrada com o status "Sem créditos" e nenhum lead é processado. A próxima execução é agendada normalmente — quando seus créditos forem renovados ou você comprar mais, a automação volta a funcionar sozinha.

**Posso alterar os filtros de uma automação que já está rodando?**
Sim. Clique em **Editar** no card da automação, faça as alterações e salve. As mudanças entram em vigor na próxima execução agendada.

**Como entro em contato com o suporte?**
Envie um e-mail para **suporte@revolucao-ai.com**. Inclua uma descrição do problema e, se possível, um print da tela.

---

*Lead Extractor by Revolução AI — Prospecção ativa, resultados reais.*
