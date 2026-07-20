"""Provider do Pararius (ESQUELETO / roadmap).

O Pararius é o 2º maior portal holandês e às vezes lista imóveis à venda que
não estão no Funda. Como respeita o mesmo contrato BaseProvider, entra no
sistema sem mudar scoring, WOZ ou relatório — basta implementar fetch_listings.

Status: a implementar. A estratégia será semelhante à do Funda (Playwright +
parsing dos cards), ajustada ao HTML do Pararius na fase de testes.
"""
from __future__ import annotations

from ..models import Listing
from .base import BaseProvider

PARARIUS_BASE = "https://www.pararius.nl"


class ParariusProvider(BaseProvider):
    def fetch_listings(self) -> list[Listing]:
        raise NotImplementedError(
            "Provider Pararius ainda não implementado — ver ROADMAP.md. "
            "A arquitetura já o acomoda: basta preencher este método."
        )
