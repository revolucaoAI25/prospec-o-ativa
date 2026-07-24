"""
Normalização de telefone para E.164 — usado pela ferramenta de disparo WhatsApp.

Diferente do `_apenas_digitos()` duplicado em vários módulos (que só remove
caracteres não numéricos), aqui é preciso inferir o DDI e montar o número
completo no formato que a Evolution API exige, ex: 5511999999999.
"""

from __future__ import annotations


def apenas_digitos(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def normalizar_e164(numero: str, ddi_padrao: str = "55") -> str:
    """
    Converte um telefone em formato livre (ex: "(11) 99999-9999",
    "11999999999", "+55 11 99999-9999") para E.164 sem o "+"
    (formato aceito pela Evolution API), assumindo DDI padrão quando ausente.

    Heurística para números brasileiros (ddi_padrao="55"):
      - já tem o DDI (13 dígitos, começa com "55")           → mantém
      - DDD + número, com 9º dígito (11 dígitos)              → adiciona DDI
      - DDD + número, sem 9º dígito, fixo (10 dígitos)        → adiciona DDI
      - menos de 10 dígitos → não dá pra inferir DDD, retorna "" (inválido)
    """
    d = apenas_digitos(numero)
    if not d:
        return ""

    if d.startswith(ddi_padrao) and len(d) in (12, 13):
        return d

    if len(d) in (10, 11):
        return f"{ddi_padrao}{d}"

    # Já tem algum DDI diferente do padrão (14+ dígitos ou 12-13 sem bater
    # com o padrão) — assume que já está completo e devolve como está.
    if len(d) >= 12:
        return d

    return ""


def formatar_exibicao(numero_e164: str) -> str:
    """Formata um E.164 brasileiro para exibição: 5511999999999 → (11) 99999-9999."""
    d = apenas_digitos(numero_e164)
    if d.startswith("55") and len(d) == 13:
        d = d[2:]
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return numero_e164
