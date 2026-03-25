# Prospec-o-Ativa

Sistema para montar bases de prospecção ativa de escritórios de advocacia,
com nome, **telefone**, endereço, site e mais.

Exporta para **CSV** e **Excel** prontos para usar no seu CRM ou disparador.

---

## Como funciona

Existem **duas formas** de buscar:

| Método | Fonte | Telefone | Requer |
|--------|-------|----------|--------|
| `maps` | Google Maps | ✅ Alta qualidade | Chave Google API (grátis até ~5k/mês) |
| `cnpj` | Receita Federal via Brasil.io | ✅ Dados oficiais | Token Brasil.io (100% grátis) |

---

## Instalação (1 vez só)

```bash
# 1. Clone o repositório e entre na pasta
cd prospec-o-ativa

# 2. Crie o ambiente virtual
python -m venv venv
source venv/bin/activate      # Linux/Mac
# ou: venv\Scripts\activate   # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as chaves de API
cp .env.example .env
# Edite o arquivo .env com suas chaves (veja instruções abaixo)
```

---

## Configuração das chaves

### Google Maps API (para o comando `maps`)

1. Acesse [console.cloud.google.com](https://console.cloud.google.com/)
2. Crie um projeto
3. Ative a **Places API** em "APIs e Serviços > Biblioteca"
4. Vá em "Credenciais" > "Criar credencial" > "Chave de API"
5. Cole no `.env`:
   ```
   GOOGLE_MAPS_API_KEY=AIzaSy...
   ```

> O Google dá **US$ 200 de crédito gratuito por mês** (~5.000 buscas completas).
> Para uso moderado, é suficiente sem pagar nada.

### Brasil.io Token (para o comando `cnpj`)

1. Crie conta gratuita em [brasil.io](https://brasil.io/)
2. Acesse [brasil.io/auth/tokens-api/](https://brasil.io/auth/tokens-api/)
3. Gere um token e cole no `.env`:
   ```
   BRASILIO_TOKEN=seu_token_aqui
   ```

---

## Uso

### Busca via Google Maps (recomendado para telefone)

```bash
# Busca básica por cidade
python main.py maps --cidade "São Paulo" --estado SP

# Com especialidade
python main.py maps --cidade "Curitiba" --especialidade "trabalhista"
python main.py maps --cidade "Rio de Janeiro" --especialidade "tributário"
python main.py maps --cidade "Belo Horizonte" --especialidade "família"

# Mais resultados (máx 60 por busca)
python main.py maps --cidade "Florianópolis" --limite 60

# Só CSV
python main.py maps --cidade "Porto Alegre" --formato csv

# Salvar em outra pasta
python main.py maps --cidade "Recife" --saida /minha/pasta
```

### Busca via CNPJ / Receita Federal

```bash
# Por estado inteiro
python main.py cnpj --uf SP

# Por município específico (nome em MAIÚSCULAS)
python main.py cnpj --municipio "SAO PAULO" --uf SP
python main.py cnpj --municipio "CURITIBA" --uf PR

# Mais resultados
python main.py cnpj --uf RJ --limite 500

# Só Excel
python main.py cnpj --uf MG --formato excel
```

### Enriquecer base existente com dados de CNPJ

```bash
# Adiciona dados faltantes (e-mail, CEP, CNPJ) a um CSV que você já tem
python main.py enriquecer --arquivo resultados/prospecao_sp.csv
```

---

## O que é exportado

Cada linha da planilha tem:

| Campo | Descrição |
|-------|-----------|
| Nome | Nome do escritório |
| **Telefone** | Número de telefone formatado |
| E-mail | E-mail (quando disponível) |
| Endereço | Endereço completo |
| Município / UF | Cidade e estado |
| Site | Site do escritório |
| Google Maps | Link direto no Maps |
| Avaliação | Nota no Google (1–5) |
| CNPJ | CNPJ quando disponível |
| Fonte | De onde veio o dado |

---

## Dicas de uso

- **Faça buscas por especialidade** para qualificar melhor a lista:
  `trabalhista`, `tributário`, `família`, `imobiliário`, `criminal`, `previdenciário`

- **Combine os dois métodos**: use `maps` para ter telefone e depois `enriquecer` para adicionar CNPJ e e-mail.

- **Para cobrir uma cidade grande**: faça múltiplas buscas com especialidades diferentes, depois junte os arquivos no Excel removendo duplicatas pela coluna "Nome".

- Os arquivos são salvos na pasta `resultados/` com timestamp no nome.
