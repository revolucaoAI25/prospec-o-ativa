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
- A `X-API-Key` dá poder de criar usuários na plataforma — trate como segredo, nunca exponha no front-end da LP (a chamada para esta API deve ser feita pelo backend/servidor da automação de venda, nunca direto do navegador do cliente).
