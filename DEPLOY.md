# Como fazer o deploy (hospedar gratuitamente)

## Streamlit Community Cloud — 100% Gratuito

O Streamlit Community Cloud permite hospedar apps Python de graça,
com URL pública que você pode compartilhar com o time.

---

### Passo a passo

**1. Crie conta no Streamlit Cloud**
- Acesse: https://share.streamlit.io
- Clique em "Sign up" e entre com sua conta do GitHub

**2. Conecte o repositório**
- Clique em **"New app"**
- Selecione o repositório `prospec-o-ativa`
- Branch: `main` (ou a branch atual)
- Main file path: `app.py`
- Clique em **"Deploy!"**

**3. Configure as chaves de API (IMPORTANTE)**

Antes de usar, você precisa adicionar as chaves secretas:

- No painel do app, clique em **"Settings"** (ícone de engrenagem)
- Vá em **"Secrets"**
- Cole o seguinte, preenchendo com suas chaves reais:

```toml
GOOGLE_MAPS_API_KEY = "AIzaSy_SUA_CHAVE_AQUI"
BRASILIO_TOKEN      = "seu_token_brasil_io_aqui"
```

- Clique em **"Save"** — o app reinicia automaticamente

**4. Compartilhe a URL**

Após o deploy, você recebe uma URL no formato:
```
https://seu-usuario-prospec-o-ativa-app-xxxxxx.streamlit.app
```

Compartilhe com o time. Qualquer pessoa com a URL pode usar.

---

### Limites do plano gratuito

| Recurso | Limite |
|---------|--------|
| Apps públicos | Ilimitado |
| Apps privados | 1 |
| Memória RAM | 1 GB |
| CPU | Compartilhada |
| Inatividade (app hiberna) | Após 7 dias sem uso |

Para uso interno da empresa, o plano gratuito é mais que suficiente.

---

### Rodando localmente (para testes)

```bash
# Instale as dependências
pip install -r requirements.txt

# Configure as chaves
cp .env.example .env
# Edite o .env com suas chaves

# Rode o app
streamlit run app.py
```

O app abre automaticamente em http://localhost:8501
