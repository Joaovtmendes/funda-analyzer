"""Carregamento e validação da configuração (config/search.yaml)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class SearchConfig(BaseModel):
    city: str = "amsterdam"
    listing_type: str = "koop"
    sources: list[str] = Field(default_factory=lambda: ["mock"])  # fontes a coletar
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    min_area_m2: Optional[int] = None
    min_rooms: Optional[int] = None
    energy_labels: list[str] = Field(default_factory=list)
    max_results: Optional[int] = 40   # vazio (null) = sem limite: pega a cidade toda


class ScraperConfig(BaseModel):
    headless: bool = True
    min_delay_seconds: float = 3
    max_delay_seconds: float = 7
    user_agent: str = "Mozilla/5.0"


class ScoringConfig(BaseModel):
    weight_price_vs_woz: float = 0.30
    weight_price_vs_sales: float = 0.25   # vendas reais do Kadaster (sinal forte)
    weight_price_per_m2: float = 0.25
    weight_days_on_market: float = 0.12
    weight_energy_label: float = 0.08


class AppConfig(BaseModel):
    search: SearchConfig = Field(default_factory=SearchConfig)
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)


def load_config(path: str | Path) -> AppConfig:
    path = Path(path)
    if not path.exists():
        return AppConfig()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return AppConfig(**data)
