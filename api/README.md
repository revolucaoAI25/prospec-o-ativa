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

Header `X-API-Key` com o valor de `ENRICH_API_KEY` (chave **separada** da usada em `/users`).

## Corpo da requisição (JSON)

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `nome` | string | não | Nome do lead, se disponível (usado só no fallback de IA) |
| `email` | string | ao menos um entre `email`/`telefone` | E-mail do lead |
| `telefone` | string | ao menos um entre `email`/`telefone` | Telefone do lead (qualquer formato) |
| `webhook_destino` | string (URL) | não | Se informado, o resultado é reenviado via `POST` pra essa URL quando o processamento terminar |

## Resposta — `202 Accepted`

A requisição só registra o pedido e devolve na hora — o processamento roda em background
(pode levar alguns segundos, principalmente se cair no fallback de IA).

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
mesmo formato da linha salva: `empresa_nome`, `cnpj`, `endereco`, `municipio`, `uf`, `website`,
`maps_url`, `avaliacao`, `total_avaliacoes`, `metodo_encontrado` (`"email"`/`"telefone"`/`"ia"`
— indica qual etapa do pipeline achou o resultado), `status`.

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
| `ENRICH_API_KEY` | ✅ (senão o endpoint retorna `503`) | Chave secreta pro header `X-API-Key`, separada da usada em `/users` |
| `CDD_API_KEY` | recomendada | Mesma chave da Casa dos Dados já usada no app principal — sem ela, o passo de busca por e-mail pula direto pra confirmação só via Maps |
| `MAPS_API_KEY_ENRICH` | recomendada | Chave do Google Maps **dedicada** a este protótipo (não reaproveita as chaves/pool do app principal, pra não disputar cota com os clientes). Tem um teto de segurança de 900 usos/mês, contado à parte |
| `ANTHROPIC_API_KEY` | opcional | Habilita o fallback de IA (Claude Haiku + busca na web) quando e-mail e telefone não encontram nada. Sem ela, esse passo é simplesmente pulado |

## Estratégia do pipeline (nessa ordem, para no primeiro que achar)

1. **E-mail** — se for corporativo (não gmail/hotmail/etc.), extrai o domínio, busca o nome
   provável da empresa na Casa dos Dados (razão social/nome fantasia) e confirma cruzando com
   o Google Maps (campo `website` do lugar batendo com o domínio do e-mail).
2. **Telefone** — tenta o número como texto direto numa busca do Google Maps (não é um
   recurso oficialmente documentado, mas custa pouco tentar).
3. **IA** — Claude (modelo barato) com busca na web habilitada, só como último recurso.

## Notas

- Assim como `/users`, isto é pensado pra ser chamado só pelo **admin** — a chave fica só com
  quem administra a plataforma, e o painel de visualização dentro do app já é admin-only.
- O SQL de `lead_enrichments` e `enrichment_settings` precisa estar rodado no Supabase antes
  de usar este endpoint (ver `supabase_schema.sql`).
