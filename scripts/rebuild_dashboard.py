"""Reconstrói o dashboard a partir do que JÁ está no banco (sem coletar de novo).

Uso:
    python -m scripts.rebuild_dashboard

Lê a captura mais recente de cada imóvel (view `latest`), recalcula os scores
com os pesos atuais e gera output/dashboard.html com as funções mais novas.
Útil quando você mexeu só no dashboard/scoring e não quer refazer o scraping.
"""
from __future__ import annotations

import sqlite3
import webbrowser
from datetime import date, datetime
from pathlib import Path

from src.config import load_config
from src.enrichment import enrich_neighborhood
from src.models import Listing, ScoredListing, WozData
from src.report import build_dashboard
from src.scoring import score_listings

DB = "data/funda.db"


def _to_scored(row: dict) -> ScoredListing:
    listing = Listing(
        listing_id=row["listing_id"],
        source=row.get("source") or "funda",
        url=row.get("url") or "",
        address=row.get("address") or "?",
        postal_code=row.get("postal_code"),
        city=row.get("city") or "",
        price=row.get("price"),
        area_m2=row.get("area_m2"),
        rooms=row.get("rooms"),
        year_built=row.get("year_built"),
        energy_label=row.get("energy_label"),
    )
    woz = WozData(address=listing.address, woz_value=row["woz_value"]) if row.get("woz_value") else None
    s = ScoredListing(listing=listing, woz=woz)
    s.kadaster_median = row.get("kadaster_median")
    return s


def main() -> None:
    cfg = load_config("config/search.yaml")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM latest")]
    conn.close()

    if not rows:
        print("Banco vazio — rode `python main.py` ao menos uma vez para coletar.")
        return

    scored = [_to_scored(r) for r in rows]
    scored = enrich_neighborhood(scored)           # benchmark por bairro
    scored = score_listings(scored, cfg.scoring)   # recalcula com os pesos atuais
    out = build_dashboard(scored, "output/dashboard.html",
                          source="banco (histórico)", scoring=cfg.scoring)
    print(f"Dashboard reconstruído com {len(scored)} imóveis do banco: {out.resolve()}")
    webbrowser.open(out.resolve().as_uri())


if __name__ == "__main__":
    main()
