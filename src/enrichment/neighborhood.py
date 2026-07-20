"""Benchmark de preço/m² por bairro (código postal PC4).

Compara o €/m² de cada imóvel com a mediana do seu bairro — os 4 primeiros
dígitos do código postal holandês (ex.: "1018 RN" -> "1018"). É um sinal de
valuation forte e GRÁTIS: sai dos próprios dados coletados, sem depender de WOZ
ou Kadaster. "20% mais barato que a vizinhança" é muito mais acionável do que
"mais barato que a cidade".

Só considera um bairro com amostra suficiente (min_samples); abaixo disso, o
imóvel fica sem mediana de bairro (o score cai de volta para a mediana geral).
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Optional

from ..models import ScoredListing


def _pc4(postal: Optional[str]) -> Optional[str]:
    if not postal:
        return None
    digits = postal.replace(" ", "")[:4]
    return digits if digits.isdigit() else None


def enrich_neighborhood(items: list[ScoredListing], min_samples: int = 3) -> list[ScoredListing]:
    groups: dict[str, list[float]] = defaultdict(list)
    for s in items:
        ppm2 = s.listing.price_per_m2
        pc4 = _pc4(s.listing.postal_code)
        if ppm2 and pc4:
            groups[pc4].append(ppm2)

    medians = {k: statistics.median(v) for k, v in groups.items() if len(v) >= min_samples}

    for s in items:
        pc4 = _pc4(s.listing.postal_code)
        s.neighborhood = pc4
        s.neighborhood_ppm2_median = medians.get(pc4)
    return items
