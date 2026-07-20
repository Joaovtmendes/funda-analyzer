"""Modelos de dados centrais do sistema (Pydantic).

Toda a informação que flui pelo pipeline usa estes modelos, o que garante
validação automática e um contrato claro entre os módulos (coleta -> WOZ ->
scoring -> relatório).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class Listing(BaseModel):
    """Um imóvel coletado de uma fonte (Funda ou dados de exemplo)."""

    listing_id: str = Field(..., description="ID único no site de origem")
    source: str = Field("mock", description="Portal de origem (funda, pararius, mock...)")
    url: str
    address: str
    postal_code: Optional[str] = None
    city: str
    price: Optional[int] = Field(None, description="Preço pedido em EUR")
    area_m2: Optional[int] = Field(None, description="Área habitável em m²")
    plot_m2: Optional[int] = Field(None, description="Área do terreno em m²")
    rooms: Optional[int] = None
    bedrooms: Optional[int] = None
    year_built: Optional[int] = None
    energy_label: Optional[str] = None
    description: Optional[str] = Field(None, description="Texto do anúncio (usado na heurística de reforma)")
    photos: list[str] = Field(default_factory=list, description="URLs das fotos do anúncio (usadas na visão da Claude)")
    listed_date: Optional[date] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def price_per_m2(self) -> Optional[float]:
        if self.price and self.area_m2:
            return round(self.price / self.area_m2, 2)
        return None


class WozData(BaseModel):
    """Valor WOZ (avaliação oficial) de um endereço."""

    address: str
    woz_value: Optional[int] = Field(None, description="Valor WOZ mais recente em EUR")
    reference_date: Optional[date] = None
    source: str = "wozwaardeloket"


class RenovationAssessment(BaseModel):
    """Avaliação de potencial de reforma a partir das fotos do anúncio."""

    effort: Optional[str] = Field(None, description="baixo | medio | alto")
    summary: Optional[str] = None
    flags: list[str] = Field(default_factory=list)  # ex: "cozinha datada", "banheiro reformado"


class ScoredListing(BaseModel):
    """Imóvel enriquecido com WOZ, reforma e o score de potencial calculado."""

    listing: Listing
    woz: Optional[WozData] = None
    renovation: Optional[RenovationAssessment] = None
    kadaster_median: Optional[int] = Field(None, description="Mediana de vendas reais comparáveis (Kadaster), EUR")
    neighborhood: Optional[str] = Field(None, description="Bairro = 4 primeiros dígitos do código postal (PC4)")
    neighborhood_ppm2_median: Optional[float] = Field(None, description="Mediana de €/m² do bairro")
    score: float = Field(0.0, description="Potencial de compra, 0-100")
    # componentes do score para transparência no relatório
    score_price_vs_woz: float = 0.0
    score_price_vs_sales: float = 0.0
    score_price_per_m2: float = 0.0
    score_days_on_market: float = 0.0
    score_energy_label: float = 0.0
    notes: list[str] = Field(default_factory=list)

    @property
    def price_vs_woz_pct(self) -> Optional[float]:
        """Percentual do preço em relação ao WOZ. <100% = abaixo do WOZ."""
        if self.woz and self.woz.woz_value and self.listing.price:
            return round(self.listing.price / self.woz.woz_value * 100, 1)
        return None

    @property
    def price_vs_sales_pct(self) -> Optional[float]:
        """Percentual do preço vs vendas reais comparáveis. <100% = abaixo do mercado."""
        if self.kadaster_median and self.listing.price:
            return round(self.listing.price / self.kadaster_median * 100, 1)
        return None

    @property
    def ppm2_vs_neighborhood_pct(self) -> Optional[float]:
        """€/m² do imóvel vs mediana do bairro. <100% = mais barato que a vizinhança."""
        if self.neighborhood_ppm2_median and self.listing.price_per_m2:
            return round(self.listing.price_per_m2 / self.neighborhood_ppm2_median * 100, 1)
        return None
