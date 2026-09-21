"""
Renderização HTML do painel admin de enriquecimento — módulo puro (só monta
strings HTML a partir dos dados que recebe, sem saber nada de Supabase/config/
autenticação). Fica separado de main.py só pra não poluir o arquivo de rotas
com um bloco grande de HTML/CSS.

Interface intencionalmente simples (forms HTML puros, reload de página a
cada ação) — é um painel interno pra um único admin testar e acompanhar o
protótipo, não precisa de JS/framework.
"""

from __future__ import annotations

import html as _html


def _esc(v) -> str:
    return _html.escape(str(v)) if v is not None else ""


_CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body {
    margin: 0; padding: 0; background: #0a0e17; color: #e6e9ef;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.wrap { max-width: 880px; margin: 0 auto; padding: 32px 20px 80px; }
.header { display: flex; align-items: center; gap: 14px; margin-bottom: 28px; }
.header .icon {
    width: 40px; height: 40px; border-radius: 10px; background: #12335c;
    display: flex; align-items: center; justify-content: center; color: #38bdf8; font-size: 20px;
}
.header h1 { font-size: 20px; margin: 0; }
.header p { margin: 2px 0 0; color: #8b93a7; font-size: 13px; }
.card {
    background: #10151f; border: 1px solid #1c2333; border-radius: 12px;
    padding: 20px 22px; margin-bottom: 18px;
}
.card h2 { font-size: 15px; margin: 0 0 12px; color: #cbd3e1; }
.card h2 small { color: #6b7385; font-weight: 400; font-size: 12px; }
code, pre {
    background: #050810; border: 1px solid #1c2333; border-radius: 8px;
    color: #7ee787; font-size: 12.5px; font-family: ui-monospace, "SF Mono", Consolas, monospace;
}
code { padding: 2px 6px; }
pre { padding: 14px 16px; overflow-x: auto; white-space: pre-wrap; word-break: break-word; }
.grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
.grid3 { display: grid; grid-template-columns: 1fr 3fr; gap: 10px; }
label { display: block; font-size: 12px; color: #8b93a7; margin-bottom: 4px; }
input[type=text], input[type=url], select {
    width: 100%; background: #0a0e17; border: 1px solid #262e42; border-radius: 8px;
    color: #e6e9ef; padding: 9px 11px; font-size: 13px; margin-bottom: 12px;
}
button {
    background: #16a34a; color: #052e16; border: none; border-radius: 8px;
    padding: 10px 18px; font-size: 13.5px; font-weight: 600; cursor: pointer;
}
button.secondary { background: #1c2333; color: #cbd3e1; }
button.danger { background: #3a1220; color: #fca5a5; padding: 6px 10px; font-size: 12px; }
.msg { padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-bottom: 16px; }
.msg.ok { background: #052e16; color: #7ee787; border: 1px solid #16a34a44; }
.msg.err { background: #3a1220; color: #fca5a5; border: 1px solid #ef444444; }
.row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #1c2333; font-size: 13px; }
.row:last-child { border-bottom: none; }
.badge { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 11px; font-weight: 600; }
.b-ok { background: #052e16; color: #7ee787; }
.b-warn { background: #3a2a05; color: #fbbf24; }
.b-err { background: #3a1220; color: #fca5a5; }
.entry { border-bottom: 1px solid #1c2333; padding: 12px 0; }
.entry:last-child { border-bottom: none; }
.entry .titulo { font-weight: 600; font-size: 13.5px; }
.entry .meta { color: #6b7385; font-size: 11.5px; margin-top: 2px; }
.entry .detail { font-size: 12.5px; color: #b6bccb; margin-top: 6px; }
.empty { color: #6b7385; font-size: 13px; padding: 10px 0; }
"""


def render_login_placeholder() -> str:
    # Nunca deveria renderizar — HTTPBasic barra antes. Só por segurança.
    return "<h1>Não autorizado</h1>"


def render_painel(
    *,
    endpoint_url: str,
    enrich_key: str,
    webhooks: list[dict],
    historico: list[dict],
    mensagem: str = "",
    mensagem_tipo: str = "ok",
) -> str:
    msg_html = ""
    if mensagem:
        msg_html = f'<div class="msg {_esc(mensagem_tipo)}">{_esc(mensagem)}</div>'

    webhooks_rows = "".join(
        f'<div class="row"><span>{_esc(w["nome"])} — <code>{_esc(w["url"])}</code></span>'
        f'<form method="post" action="/painel/webhooks/{_esc(w["id"])}/deletar" style="margin:0">'
        f'<button class="danger" type="submit">remover</button></form></div>'
        for w in webhooks
    ) or '<div class="empty">Nenhum webhook salvo ainda.</div>'

    webhook_options = "".join(
        f'<option value="{_esc(w["url"])}">{_esc(w["nome"])} — {_esc(w["url"])}</option>'
        for w in webhooks
    )

    status_badge = {
        "pendente": ("b-warn", "⏳ Pendente"),
        "processando": ("b-warn", "⏳ Processando"),
        "concluido": ("b-ok", "✅ Concluído"),
        "nao_encontrado": ("b-err", "❌ Não encontrado"),
        "erro": ("b-err", "❌ Erro"),
    }
    metodo_lbl = {"email": "📧 e-mail", "telefone": "📞 telefone", "ia": "🤖 IA"}

    historico_rows = ""
    for r in historico:
        cls, lbl = status_badge.get(r.get("status", ""), ("b-err", r.get("status", "—")))
        titulo = r.get("empresa_nome") or r.get("nome_lead") or r.get("email") or r.get("telefone") or "—"
        ts = (r.get("criado_em") or "")[:16].replace("T", " ")
        metodo = metodo_lbl.get(r.get("metodo_encontrado"), "")
        detalhe_partes = []
        if r.get("cnpj"):
            detalhe_partes.append(f"CNPJ {_esc(r['cnpj'])}")
        if r.get("municipio"):
            detalhe_partes.append(_esc(r["municipio"]) + (f"/{_esc(r['uf'])}" if r.get("uf") else ""))
        if r.get("website"):
            detalhe_partes.append(_esc(r["website"]))
        if r.get("erro"):
            detalhe_partes.append(f"erro: {_esc(r['erro'])}")
        detalhe = " · ".join(detalhe_partes)
        historico_rows += (
            '<div class="entry">'
            f'<div class="titulo">{_esc(titulo)} '
            f'<span class="badge {cls}">{lbl}</span>'
            + (f' <span class="badge b-ok">{_esc(metodo)}</span>' if metodo else "")
            + f'</div><div class="meta">{_esc(ts)}'
            + (f' &middot; entrada: {_esc(r.get("email") or r.get("telefone") or "—")}' if r.get("email") or r.get("telefone") else "")
            + "</div>"
            + (f'<div class="detail">{detalhe}</div>' if detalhe else "")
            + "</div>"
        )
    historico_html = historico_rows or '<div class="empty">Nenhum enriquecimento registrado ainda.</div>'

    endpoint_completo = f"{endpoint_url.rstrip('/')}/enrich/lead" if endpoint_url else "https://<este-servico>/enrich/lead"

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Enriquecimento de Leads</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div class="icon">🔎</div>
    <div>
      <h1>Enriquecimento de Leads</h1>
      <p>Protótipo admin-only — descobre dados comerciais (empresa, CNPJ) a partir de e-mail ou telefone</p>
    </div>
  </div>

  {msg_html}

  <div class="card">
    <h2>📡 Como conectar <small>webhook de entrada, pra usar no Make/n8n/Zapier</small></h2>
    <pre>POST {_esc(endpoint_completo)}
Header:  X-API-Key: {_esc(enrich_key or "<sua ENRICH_API_KEY>")}
Header:  Content-Type: application/json

Body (JSON):
{{
  "nome": "Fulano de Tal",
  "email": "fulano@empresa.com.br",
  "telefone": "+55 47 99999-9999",
  "webhook_destino": "https://hook.make.com/xxxxx"   // opcional
}}</pre>
    <p style="color:#8b93a7;font-size:12.5px">
      <code>webhook_destino</code> é opcional — se informado, o resultado é reenviado automaticamente
      pra essa URL quando o processamento terminar. Sem isso, consulte pelo histórico abaixo.
    </p>
  </div>

  <div class="card">
    <h2>🔗 Webhooks de destino salvos</h2>
    {webhooks_rows}
    <form method="post" action="/painel/webhooks" style="margin-top:14px">
      <div class="grid3">
        <div><label>Nome</label><input type="text" name="nome" placeholder="Ex: Make — CRM" required></div>
        <div><label>URL</label><input type="url" name="url" placeholder="https://hook.make.com/..." required></div>
      </div>
      <button type="submit">➕ Salvar webhook</button>
    </form>
  </div>

  <div class="card">
    <h2>🧪 Testar agora</h2>
    <form method="post" action="/painel/testar">
      <div class="grid">
        <div><label>Nome (opcional)</label><input type="text" name="nome"></div>
        <div><label>E-mail</label><input type="text" name="email"></div>
        <div><label>Telefone</label><input type="text" name="telefone"></div>
      </div>
      <label>Reenviar resultado pra (opcional)</label>
      <select name="webhook_destino">
        <option value="">(nenhum)</option>
        {webhook_options}
      </select>
      <button type="submit">🚀 Enriquecer</button>
    </form>
    <p style="color:#6b7385;font-size:12px;margin-top:10px">
      Roda na hora (síncrono) — pode levar alguns segundos, principalmente se cair no fallback de IA.
    </p>
  </div>

  <div class="card">
    <h2>📜 Histórico <small>últimos {len(historico)}</small></h2>
    {historico_html}
  </div>
</div>
</body>
</html>"""
