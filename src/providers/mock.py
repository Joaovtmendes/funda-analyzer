"""Provider de dados de exemplo.

Permite desenvolver e testar todo o pipeline (WOZ, scoring, dashboard) sem
depender do scraping funcionar. Os dados imitam a estrutura real do Funda,
com dispersão realista de preço/m² para o score ter o que comparar.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from ..models import Listing
from .base import BaseProvider

_STREETS = [
    "Prinsengracht", "Keizersgracht", "Jordaan", "De Pijp", "Vondelstraat",
    "Overtoom", "Javastraat", "Bilderdijkstraat", "Ceintuurbaan", "Weesperzijde",
]
_LABELS = ["A", "A", "B", "B", "C", "C", "D"]

# Descrições de exemplo com termos reais de anúncios holandeses, para a
# heurística de reforma ter o que analisar.
_DESCRIPTIONS = [
    "Instapklare woning, volledig gerenoveerd in 2021 met nieuwe keuken en badkamer.",
    "Opknapper met veel potentie. Achterstallig onderhoud, te renoveren naar eigen smaak.",
    "Gemoderniseerd appartement, luxe afgewerkt en energiezuinig.",
    "Karakteristieke woning, deels verouderd. Keuken en badkamer toe aan renovatie.",
    "Goed onderhouden, netjes bewoonbaar. Enkele kleine klussen mogelijk.",
    "Kluswoning voor de doe-het-zelver. Volledige renovatie nodig.",
    "Nieuwbouw, oplevering afgewerkt met hoogwaardige materialen.",
]


class MockProvider(BaseProvider):
    def fetch_listings(self) -> list[Listing]:
        rng = random.Random(42)  # semente fixa = resultados reproduzíveis
        n = min(self.config.search.max_results or 25, 25)
        listings: list[Listing] = []
        for i in range(n):
            area = rng.randint(45, 160)
            price_m2 = rng.randint(4500, 9000)      # varia por imóvel
            price = int(round(area * price_m2, -3))
            listed = date.today() - timedelta(days=rng.randint(2, 220))
            street = rng.choice(_STREETS)
            num = rng.randint(1, 300)
            listings.append(
                Listing(
                    listing_id=f"mock-{i:03d}",
                    url=f"https://www.funda.nl/koop/amsterdam/mock-{i:03d}/",
                    address=f"{street} {num}",
                    postal_code=f"10{rng.randint(10, 99)} AB",
                    city="Amsterdam",
                    price=price,
                    area_m2=area,
                    rooms=rng.randint(2, 6),
                    bedrooms=rng.randint(1, 4),
                    year_built=rng.randint(1900, 2022),
                    energy_label=rng.choice(_LABELS),
                    description=rng.choice(_DESCRIPTIONS),
                    listed_date=listed,
                )
            )
        return listings
