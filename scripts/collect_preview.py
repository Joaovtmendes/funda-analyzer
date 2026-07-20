"""Passo 3: coletar imóveis e mostrar na tela.

Uso:
    python -m scripts.collect_preview

Ainda usa o provider de exemplo (mock). Serve para ver o pipeline de coleta
funcionando antes de ligar o scraping real do Funda.
"""
from __future__ import annotations

from rich.console import Console
from rich.table import Table

from src.config import load_config
from src.providers import get_provider


def main() -> None:
    cfg = load_config("config/search.yaml")
    provider = get_provider("mock", cfg)  # troque para "funda" quando o scraper estiver pronto
    listings = provider.fetch_listings()

    console = Console()
    table = Table(title=f"Imóveis coletados ({len(listings)})")
    table.add_column("Endereço", style="cyan")
    table.add_column("Preço €", justify="right")
    table.add_column("m²", justify="right")
    table.add_column("€/m²", justify="right")
    table.add_column("Label")
    table.add_column("Anunciado")

    for l in listings:
        table.add_row(
            l.address,
            f"{l.price:,}" if l.price else "-",
            str(l.area_m2 or "-"),
            f"{l.price_per_m2:,.0f}" if l.price_per_m2 else "-",
            l.energy_label or "-",
            l.listed_date.isoformat() if l.listed_date else "-",
        )

    console.print(table)


if __name__ == "__main__":
    main()
