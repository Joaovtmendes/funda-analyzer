"""Enriquecimento com preços reais de venda do Kadaster.

Enquanto o WOZ é a avaliação fiscal, o Kadaster tem os PREÇOS DE VENDA REAIS —
por quanto imóveis parecidos foram de fato vendidos. É o dado mais valioso para
julgar se um preço pedido está caro ou barato.

Modos (igual ao WOZ):
  - offline_estimate=True  -> estima a mediana de vendas a partir do imóvel, para
    desenvolver o pipeline sem rede. (padrão agora)
  - offline_estimate=False -> caminho real: consultar os dados do Kadaster/BAG.
    A implementar na fase de testes (alguns produtos do Kadaster são pagos).
"""
from __future__ import annotations

from typing import Optional

from ..models import Listing, ScoredListing


class KadasterClient:
    def __init__(self, offline_estimate: bool = True):
        self.offline_estimate = offline_estimate

    def recent_sales_median(self, listing: Listing) -> Optional[int]:
        """Mediana dos preços de venda recentes de imóveis comparáveis (€)."""
        if self.offline_estimate:
            return self._estimate(listing)
        return self._real_lookup(listing)

    def _real_lookup(self, listing: Listing) -> Optional[int]:
        # TODO(fase de teste): consultar Kadaster/BAG por vendas comparáveis
        # (mesma rua/código postal, tipo e faixa de área). Retornar None se n/d.
        return None

    def _estimate(self, listing: Listing) -> Optional[int]:
        """Simula a mediana de vendas comparáveis como fração do preço pedido.

        Na prática, o pedido costuma ficar perto das vendas reais, às vezes
        acima (imóvel caro) ou abaixo (oportunidade). Geramos essa dispersão
        para o pipeline ter um sinal realista para trabalhar.
        """
        if not listing.price:
            return None
        import random

        rng = random.Random((hash(listing.listing_id) ^ 0x5A5A) & 0xFFFFFFFF)
        factor = rng.uniform(0.88, 1.12)
        return int(listing.price / factor)


def enrich_kadaster(items: list[ScoredListing], client: Optional[KadasterClient] = None) -> list[ScoredListing]:
    client = client or KadasterClient()
    for s in items:
        median = client.recent_sales_median(s.listing)
        s.kadaster_median = median
        if median and s.listing.price:
            pct = s.listing.price / median * 100
            if pct < 97:
                s.notes.append(f"~{100 - pct:.0f}% abaixo de vendas reais")
    return items
