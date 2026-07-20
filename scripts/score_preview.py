"""Passo 4: coletar -> enriquecer com WOZ -> pontuar -> mostrar ranking.

Uso:
    python -m scripts.score_preview

Ainda usa dados de exemplo e WOZ estimado (offline). Serve para ver o motor
de score rankeando os imóveis por potencial de compra.
"""
from __future__ import annotations

from rich.console import Console
from rich.table import Table

from src.config import load_config
from src.enrichment import enrich_with_woz
from src.providers import get_provider
from src.scoring import score_listings


def main() -> None:
    cfg = load_config("config/search.yaml")

    listings = get_provider("mock", cfg).fetch_listings()   # 1. coleta
    scored = enrich_with_woz(listings)                       # 2. WOZ
    scored = score_listings(scored, cfg.scoring)             # 3. score + ordena

    console = Console()
    table = Table(title=f"Ranking por potencial de compra ({len(scored)})")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Score", justify="right", style="bold green")
    table.add_column("Endereço", style="cyan")
    table.add_column("Preço €", justify="right")
    table.add_column("€/m²", justify="right")
    table.add_column("WOZ €", justify="right")
    table.add_column("Preço/WOZ", justify="right")
    table.add_column("Destaques")

    for i, s in enumerate(scored, 1):
        l = s.listing
        table.add_row(
            str(i),
            f"{s.score:.0f}",
            l.address,
            f"{l.price:,}" if l.price else "-",
            f"{l.price_per_m2:,.0f}" if l.price_per_m2 else "-",
            f"{s.woz.woz_value:,}" if s.woz and s.woz.woz_value else "-",
            f"{s.price_vs_woz_pct:.0f}%" if s.price_vs_woz_pct else "-",
            "; ".join(s.notes[:2]),
        )

    console.print(table)


if __name__ == "__main__":
    main()
