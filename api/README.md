# API de Provisionamento de Usuários — Lead Extractor

API para criar usuários automaticamente na plataforma Lead Extractor (Revolução AI), pensada para integração com sistemas de venda automática (checkout, LP, automações).

---

## Endpoint

```
POST https://optimistic-fulfillment-production-3cc2.up.railway.app/users
```

## Autenticação

Toda requisição precisa do header:

```
X-API-Key: a3eb9c2ae6e5bc6ff5c9d08d49186073bf44c6b66940deb21077c394784498f4
```

Requisições sem essa chave ou com chave errada retornam `401 Unauthorized`.

## Headers obrigatórios

| Header | Valor |
|---|---|
| `X-API-Key` | `a3eb9c2ae6e5bc6ff5c9d08d49186073bf44c6b66940deb21077c394784498f4` |
| `Content-Type` | `application/json` |

---

## Corpo da requisição (JSON)

| Campo | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `email` | string | ✅ | — | E-mail do novo usuário (login) |
| `password` | string | ✅ | — | Senha (mínimo 6 caracteres) |
| `role` | string | não | `"user"` | `"user"` ou `"admin"` |
| `cdd_credits` | int | não | `0` | Saldo inicial de créditos de busca CNPJ |
| `monthly_cdd_credits` | int | não | `0` | Renovação automática mensal de créditos CNPJ (`0` = sem renovação) |
| `maps_credits_enabled` | bool | não | `false` | `true` = usuário usa chave/créditos Google Maps da plataforma; `false` = usuário precisa cadastrar a própria chave |
| `maps_credits` | int | não | `0` | Saldo inicial de créditos Maps (só relevante se `maps_credits_enabled=true`) |
| `monthly_maps_credits` | int | não | `0` | Renovação mensal de créditos Maps |
| `instagram_visible` | bool | não | `true` | Se a aba de busca Instagram aparece para o usuário |
| `instagram_credits_enabled` | bool | não | `false` | `true` = usuário usa a chave Apify da plataforma |
| `instagram_credits` | int | não | `0` | Saldo inicial de créditos Instagram |
| `monthly_instagram_credits` | int | não | `0` | Renovação mensal de créditos Instagram |
| `disparo_habilitado` | bool | não | `false` | `true` = usuário vê e pode usar a página de Disparos (campanhas WhatsApp). Fica desativado por padrão para todo mundo — libere aqui na criação ou depois manualmente em Admin → usuário → "Habilitar Disparos" |

---

## Exemplo de requisição

```bash
curl -X POST https://optimistic-fulfillment-production-3cc2.up.railway.app/users \
  -H "X-API-Key: a3eb9c2ae6e5bc6ff5c9d08d49186073bf44c6b66940deb21077c394784498f4" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "cliente@empresa.com",
    "password": "SenhaSegura123",
    "cdd_credits": 500,
    "monthly_cdd_credits": 500,
    "maps_credits_enabled": true,
    "maps_credits": 200,
    "monthly_maps_credits": 200,
    "instagram_visible": false
  }'
```

### Exemplo em JavaScript (fetch)

```javascript
const resposta = await fetch("https://optimistic-fulfillment-production-3cc2.up.railway.app/users", {
  method: "POST",
  headers: {
    "X-API-Key": "a3eb9c2ae6e5bc6ff5c9d08d49186073bf44c6b66940deb21077c394784498f4",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    email: "cliente@empresa.com",
    password: "SenhaSegura123",
    cdd_credits: 500,
    monthly_cdd_credits: 500,
    maps_credits_enabled: true,
    maps_credits: 200,
    monthly_maps_credits: 200,
  }),
});

const dados = await resposta.json();
console.log(dados);
```

---

## Resposta de sucesso — `201 Created`

```json
{
  "success": true,
  "user_id": "5f2b1c3a-...-uuid",
  "email": "cliente@empresa.com",
  "message": "Usuário criado com sucesso."
}
```

## Respostas de erro

| Status | Quando acontece | Corpo da resposta |
|---|---|---|
| `401` | API key ausente ou incorreta | `{"detail": "API key inválida ou ausente."}` |
| `409` | E-mail já cadastrado na plataforma | `{"detail": "Este e-mail já está cadastrado."}` |
| `422` | Dados inválidos (e-mail mal formatado, senha curta, campo com tipo errado) | `{"detail": [...detalhes de validação...]}` |
| `500` | Erro interno (Supabase indisponível, etc.) | `{"detail": "Erro ao criar usuário: ..."}` |

---

## Health check

```
GET https://optimistic-fulfillment-production-3cc2.up.railway.app/health
```

Retorna `{"status": "ok"}` — útil para monitorar se o serviço está no ar, não precisa de autenticação.

---

## Notas importantes

- O usuário criado por esta API já pode fazer login imediatamente na plataforma (e-mail já vem confirmado automaticamente).
- Os campos de crédito (`cdd_credits`, `maps_credits`, `instagram_credits`) definem o **saldo inicial**. Os campos `monthly_*` definem quanto esse saldo é **renovado automaticamente todo mês** — se quiser que o cliente só tenha o pacote comprado sem renovação, deixe os campos `monthly_*` como `0`.
- Se `maps_credits_enabled` ou `instagram_credits_enabled` forem `false` (padrão), o usuário precisa cadastrar suas próprias chaves de API (Google Maps / Apify) dentro da plataforma, em Configurações.
- `disparo_habilitado` fica `false` por padrão para todo mundo, inclusive se você não enviar esse campo — a página de Disparos só aparece pra quem for admin ou tiver essa liberação individual ativada.
- A `X-API-Key` dá poder de criar usuários na plataforma — trate como segredo, nunca exponha no front-end da LP (a chamada para esta API deve ser feita pelo backend/servidor da automação de venda, nunca direto do navegador do cliente).

---

# Enriquecimento de Leads (protótipo, admin-only)

Segundo recurso deste mesmo serviço, independente do de criação de usuários. Recebe um lead
(nome/e-mail/telefone) via webhook e tenta descobrir dados comerciais (empresa, CNPJ,
endereço) associados — **não** é busca de dado pessoal (CPF etc.), só identificação de
empresa a partir de e-mail corporativo ou telefone.

## Endpoint

```
POST https://<seu-servico>.up.railway.app/enrich/lead
```

## Autenticação

Header `X-API-Key` com o valor de `ENRICH_API_KEY`.

> **O que é essa chave?** Não é uma chave que você "obtém" em algum lugar — é uma senha que
> **você mesmo inventa** (qualquer string longa e aleatória) e cadastra como variável de
> ambiente `ENRICH_API_KEY` no Railway. Ela só serve pra impedir que qualquer pessoa na
> internet consiga chamar esse endpoint — o mesmo sistema (Make, n8n etc.) que vai disparar
> o webhook precisa mandar esse mesmo valor no header. É o mesmo esquema que já existe pro
> endpoint `/users` (lá é a `SIGNUP_API_KEY`) — só que separada, pra não misturar os dois
> recursos.

## Corpo da requisição (JSON)

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `nome` | string | não | Nome do lead, se disponível (usado na busca) |
| `email` | string | ao menos um entre `email`/`telefone` | E-mail do lead |
| `telefone` | string | ao menos um entre `email`/`telefone` | Telefone do lead (qualquer formato) |
| `webhook_destino` | string (URL) | não | Se informado, o resultado é reenviado via `POST` pra essa URL quando o processamento terminar |

## Resposta — `202 Accepted`

A requisição só registra o pedido e devolve na hora — o processamento roda em background
(pode levar alguns segundos, já que envolve busca na web).

```json
{
  "id": "5f2b1c3a-...-uuid",
  "status": "pendente",
  "message": "Recebido — processando em background..."
}
```

Consulte o resultado depois pelo `id` (direto no Supabase, tabela `lead_enrichments`, ou pelo
painel Enriquecimento dentro do app, aba admin), ou configure `webhook_destino` pra receber o
resultado automaticamente quando terminar. O payload reenviado pro `webhook_destino` tem o
mesmo formato da linha salva: `empresa_nome`, `cnpj`, `municipio`, `uf`, `website`, `cargo`,
`linkedin_url`, `resumo` (contexto comercial curto sobre a empresa), `metodo_encontrado`
(`"ia"` ou `null` se não achou), `status`.

## Exemplo de requisição

```bash
curl -X POST https://<seu-servico>.up.railway.app/enrich/lead \
  -H "X-API-Key: <ENRICH_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Fulano de Tal",
    "email": "fulano@clinicasaude.com.br",
    "telefone": "+55 47 99999-9999",
    "webhook_destino": "https://hook.make.com/xxxxxxxxx"
  }'
```

## Variáveis de ambiente necessárias (além das já usadas por `/users`)

| Variável | Obrigatória | Descrição |
|---|---|---|
| `ENRICH_API_KEY` | ✅ (senão o endpoint retorna `503`) | Senha que você mesmo inventa (ver explicação acima), pro header `X-API-Key` — separada da usada em `/users` |
| `OPENAI_API_KEY` | ✅ (senão o resultado é sempre "não encontrado") | Usada pra busca (`gpt-5-mini` com busca na web, Responses API) |
| `ENRICH_ALERTA_WEBHOOK_URL` | opcional | Se um lead falhar por erro técnico mesmo depois de 3 tentativas (rede, API fora do ar, etc.), manda um aviso curto pra essa URL — separado do `webhook_destino` de cada lead, que também recebe o status `erro` normalmente. Sem essa variável, a falha só fica registrada no histórico (`status: "erro"`) |

## Estratégia do pipeline

Só IA (OpenAI `gpt-5-mini` com busca na web habilitada, Responses API). Havia antes uma
tentativa prévia via e-mail→Casa dos Dados/Google Maps e telefone→Google Maps, mas na
calibragem prática elas praticamente não geravam resultado (a IA já cobre esses mesmos casos,
e melhor — com cargo, LinkedIn e resumo, o que a busca direta não dava) e só adicionavam
custo/latência — por isso foram removidas.

A chamada à IA tenta até 3 vezes em caso de falha técnica (rede, timeout, rate limit) antes de
desistir — nesse caso o lead vira `status: "erro"` (diferente de `"nao_encontrado"`, que é um
resultado negativo válido, não uma falha), o `webhook_destino` do lead (se configurado) recebe
esse status normalmente, e o `ENRICH_ALERTA_WEBHOOK_URL` (se configurado) recebe um aviso
separado. Nenhum lead trava o processamento dos outros — cada requisição roda numa tarefa em
background independente.

## Notas

- Isto é pensado pra ser usado só pelo **admin** — a chave fica só com quem administra a
  plataforma.
- O SQL de `lead_enrichments`, `enrichment_settings` e `enrichment_webhooks` precisa estar
  rodado no Supabase antes de usar este endpoint (ver `supabase_schema.sql`).
- **Painel visual próprio**, separado da interface do app Streamlit principal de propósito:

  ```
  GET https://<seu-servico>.up.railway.app/painel
  ```

  Protegido por **HTTP Basic Auth** (o navegador mostra um prompt de login nativo) — usuário
  pode ser qualquer coisa, a **senha precisa ser o valor de `ENRICH_API_KEY`**. Mostra o
  endpoint de entrada pronto pra copiar, gerencia webhooks de destino salvos, tem um
  formulário "Testar agora" (roda na hora, sem precisar de ferramenta externa), e lista o
  histórico completo — tudo isso rodando dentro deste mesmo serviço, sem precisar importar
  nada do app principal. Configure `ENRICH_API_URL` (a URL pública deste serviço) só pra esse
  endpoint aparecer certinho no exemplo de "como conectar" exibido no painel.
