"""Motor de score de 'potencial de compra' (0-100).

O score combina quatro sinais, cada um normalizado para 0-100 e ponderado
pelos pesos em config.scoring:

  1. Preço vs WOZ     -> quanto mais barato que a avaliação oficial, melhor.
  2. Preço/m²         -> vs a mediana da amostra coletada.
  3. Tempo no mercado -> imóveis parados tendem a ter margem de negociação.
  4. Energy label     -> eficiência energética (A melhor, G pior).

Tudo é transparente: cada componente fica salvo no ScoredListing para o
relatório mostrar o "porquê" de cada nota.
"""
from __future__ import annotations

import statistics
from datetime import date

from ..config import ScoringConfig
from ..models import ScoredListing

_ENERGY_RANK = {"A": 100, "B": 83, "C": 66, "D": 50, "E": 33, "F": 16, "G": 0}


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def score_listings(items: list[ScoredListing], cfg: ScoringConfig) -> list[ScoredListing]:
    # mediana da amostra para a normalização de preço/m²
    ppm2 = [s.listing.price_per_m2 for s in items if s.listing.price_per_m2]
    median_ppm2 = statistics.median(ppm2) if ppm2 else None
    today = date.today()

    for s in items:
        lst = s.listing

        # 1. Preço vs WOZ: 100 se o preço é <=80% do WOZ; 0 se >=120%.
        if s.price_vs_woz_pct is not None:
            pct = s.price_vs_woz_pct
            s.score_price_vs_woz = _clamp((120 - pct) / (120 - 80) * 100)
            if pct < 100:
                s.notes.append(f"Preço {100 - pct:.0f}% abaixo do WOZ")
        else:
            s.score_price_vs_woz = 50.0
            s.notes.append("Sem dado WOZ")

        # 1b. Preço vs vendas reais (Kadaster): mesma escala do WOZ.
        if s.price_vs_sales_pct is not None:
            pct = s.price_vs_sales_pct
            s.score_price_vs_sales = _clamp((120 - pct) / (120 - 80) * 100)
        else:
            s.score_price_vs_sales = 50.0  # neutro quando não há dado do Kadaster

        # 2. Preço/m² vs BAIRRO (PC4) quando houver amostra; senão vs mediana geral.
        ref_ppm2 = s.neighborhood_ppm2_median or median_ppm2
        if ref_ppm2 and lst.price_per_m2:
            ratio = lst.price_per_m2 / ref_ppm2
            s.score_price_per_m2 = _clamp((1.25 - ratio) / (1.25 - 0.75) * 100)
            npct = s.ppm2_vs_neighborhood_pct
            if npct is not None and npct < 92:
                s.notes.append(f"€/m² {100 - npct:.0f}% abaixo do bairro")
        else:
            s.score_price_per_m2 = 50.0

        # 3. Tempo no mercado: 0 dias -> 0; 180+ dias -> 100.
        if lst.listed_date:
            days = (today - lst.listed_date).days
            s.score_days_on_market = _clamp(days / 180 * 100)
            if days > 90:
                s.notes.append(f"{days} dias no mercado")
        else:
            s.score_days_on_market = 0.0

        # 4. Energy label
        if lst.energy_label:
            s.score_energy_label = float(_ENERGY_RANK.get(lst.energy_label.upper(), 50))
        else:
            s.score_energy_label = 50.0

        # combinação ponderada -> nota final
        s.score = round(
            s.score_price_vs_woz * cfg.weight_price_vs_woz
            + s.score_price_vs_sales * cfg.weight_price_vs_sales
            + s.score_price_per_m2 * cfg.weight_price_per_m2
            + s.score_days_on_market * cfg.weight_days_on_market
            + s.score_energy_label * cfg.weight_energy_label,
            1,
        )

    items.sort(key=lambda s: s.score, reverse=True)
    return items
