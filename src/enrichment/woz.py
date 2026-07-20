"""Enriquecimento com valor WOZ (avaliação oficial holandesa).

IMPORTANTE sobre WOZ:
  - Os valores WOZ são públicos por endereço em wozwaardeloket.nl, MAS não são
    "open data" e consultas em massa não são permitidas.
  - Por isso consultamos WOZ SOB DEMANDA, apenas para os imóveis que já passaram
    pelo filtro — nunca varrendo tudo. Volume baixo, uso pessoal.

Modos:
  - offline_estimate=True  -> estima o WOZ a partir do próprio imóvel, para
    desenvolver o pipeline sem rede. (padrão agora)
  - offline_estimate=False -> caminho real: geocodifica o endereço no PDOK
    Locatieserver (oficial e aberto) e depois consulta o WOZ. O passo final
    está marcado com TODO para a fase de testes com endereços reais.
"""
from __future__ import annotations

import time
from typing import Optional

import httpx

from ..models import Listing, ScoredListing, WozData

PDOK_SUGGEST = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"


class WozClient:
    def __init__(self, delay_seconds: float = 1.0, offline_estimate: bool = True):
        self.delay_seconds = delay_seconds
        self.offline_estimate = offline_estimate
        self._client = httpx.Client(timeout=15.0)

    def lookup(self, listing: Listing) -> Optional[WozData]:
        if self.offline_estimate:
            return self._estimate(listing)
        try:
            return self._real_lookup(listing)
        except Exception as e:  # noqa: BLE001
            print(f"[woz] falha ao consultar {listing.address}: {e}")
            return None

    # ---- caminho real (a completar na fase de testes) -------------------
    def _real_lookup(self, listing: Listing) -> Optional[WozData]:
        q = f"{listing.address} {listing.postal_code or ''} {listing.city}".strip()
        r = self._client.get(
            PDOK_SUGGEST,
            params={"q": q, "rows": 1, "fl": "id,weergavenaam,nummeraanduiding_id"},
        )
        r.raise_for_status()
        docs = r.json().get("response", {}).get("docs", [])
        if not docs:
            return None
        # TODO(fase de teste): usar o nummeraanduiding_id/BAG para consultar o
        # endpoint interno do wozwaardeloket e extrair o valor mais recente.
        time.sleep(self.delay_seconds)
        return None

    # ---- estimativa offline (desenvolvimento) ---------------------------
    def _estimate(self, listing: Listing) -> Optional[WozData]:
        """Aproxima o WOZ como uma fração do preço pedido.

        Na prática o WOZ costuma ficar ABAIXO do valor de mercado. Simulamos
        isso com um fator para o scoring ter dados realistas para trabalhar.
        """
        if not listing.price:
            return None
        import random

        rng = random.Random(hash(listing.listing_id) & 0xFFFFFFFF)
        factor = rng.uniform(0.82, 1.05)  # alguns acima, maioria abaixo do preço
        return WozData(address=listing.address, woz_value=int(listing.price * factor))


def enrich_with_woz(listings: list[Listing], client: Optional[WozClient] = None) -> list[ScoredListing]:
    client = client or WozClient()
    out: list[ScoredListing] = []
    for lst in listings:
        woz = client.lookup(lst)
        out.append(ScoredListing(listing=lst, woz=woz))
    return out
