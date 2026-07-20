"""Heurística de potencial de reforma (Opção C — sem IA de visão).

Estima o esforço de reforma a partir de sinais que já temos, sem olhar as
fotos: ano de construção, label energético e palavras-chave da descrição do
anúncio (em holandês). É grátis, instantâneo e surpreendentemente informativo,
porque anúncios holandeses quase sempre declaram o estado do imóvel no texto.

Mais adiante (Opção A), a visão da Claude entra por cima disto, analisando as
fotos só dos melhores candidatos. As duas convivem: esta heurística preenche o
`RenovationAssessment`, e a visão pode refiná-lo depois.

Interpretação do resultado (`effort`):
    baixo  -> instapklaar, pronto pra morar / reformado
    medio  -> alguns pontos a modernizar
    alto   -> opknapper / kluswoning, reforma pesada
"""
from __future__ import annotations

from ..models import Listing, RenovationAssessment, ScoredListing

# Termos que indicam NECESSIDADE de reforma (pontos positivos de "esforço").
_NEEDS_WORK = {
    "opknapper": 3, "kluswoning": 3, "renovatie nodig": 3, "te renoveren": 2,
    "achterstallig onderhoud": 3, "verouderd": 2, "gedateerd": 2,
    "toe aan renovatie": 2, "doe-het-zelver": 2, "deels verouderd": 1,
}
# Termos que indicam imóvel PRONTO / reformado (reduzem o esforço).
_MOVE_IN = {
    "instapklaar": 3, "gerenoveerd": 2, "gemoderniseerd": 2, "nieuwbouw": 3,
    "nieuwe keuken": 1, "nieuwe badkamer": 1, "luxe afgewerkt": 2,
    "hoogwaardige materialen": 1, "goed onderhouden": 1, "energiezuinig": 1,
}
_BAD_LABELS = {"E", "F", "G"}
_GOOD_LABELS = {"A", "B"}


def assess(listing: Listing) -> RenovationAssessment:
    score = 0  # >0 tende a "alto"; <0 tende a "baixo"
    flags: list[str] = []
    text = (listing.description or "").lower()

    # 1. palavras-chave da descrição
    for term, weight in _NEEDS_WORK.items():
        if term in text:
            score += weight
            flags.append(f"⚠ {term}")
    for term, weight in _MOVE_IN.items():
        if term in text:
            score -= weight
            flags.append(f"✓ {term}")

    # 2. ano de construção
    if listing.year_built:
        if listing.year_built < 1960:
            score += 2
            flags.append(f"construção {listing.year_built}")
        elif listing.year_built > 2010:
            score -= 2

    # 3. label energético
    if listing.energy_label:
        lab = listing.energy_label.upper()
        if lab in _BAD_LABELS:
            score += 2
            flags.append(f"label {lab}")
        elif lab in _GOOD_LABELS:
            score -= 1

    # mapeia o placar para um nível de esforço
    if score >= 3:
        effort = "alto"
    elif score <= -2:
        effort = "baixo"
    else:
        effort = "medio"

    summary = {
        "alto": "Reforma pesada provável — oportunidade de agregar valor (ou custo alto).",
        "medio": "Alguns pontos a modernizar.",
        "baixo": "Pronto pra morar / recém-reformado.",
    }[effort]

    return RenovationAssessment(effort=effort, summary=summary, flags=flags[:4])


def enrich_renovation(items: list[ScoredListing]) -> list[ScoredListing]:
    for s in items:
        s.renovation = assess(s.listing)
    return items
