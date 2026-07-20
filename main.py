"""Orquestrador principal do Funda Analyzer.

Fluxo completo: coleta (multi-fonte) -> WOZ -> reforma -> score -> dashboard.

As fontes coletadas vêm de config/search.yaml (campo `sources`). Você pode
sobrescrever pela linha de comando:

    python main.py                          # usa as fontes do search.yaml
    python main.py --sources mock           # só dados de exemplo
    python main.py --sources funda pararius # Funda + Pararius (quando prontos)
"""
from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

from src.config import load_config
from src.enrichment import enrich_with_woz, enrich_renovation, enrich_kadaster, enrich_neighborhood
from src.providers import collect_all
from src.report import build_dashboard
from src.scoring import score_listings
from src.storage import Storage


def run(sources: list[str] | None = None, open_browser: bool = True) -> Path:
    cfg = load_config("config/search.yaml")
    used = sources or cfg.search.sources

    print(f"[1/6] Coletando de todas as fontes: {', '.join(used)}")
    listings = collect_all(cfg, sources=sources)
    print(f"      Total (sem duplicatas): {len(listings)} imóveis.")

    print("[2/6] Consultando WOZ (avaliação fiscal)...")
    scored = enrich_with_woz(listings)

    print("[3/6] Consultando Kadaster (vendas reais)...")
    scored = enrich_kadaster(scored)
    scored = enrich_neighborhood(scored)  # benchmark de €/m² por bairro (PC4)

    print("[4/6] Analisando potencial de reforma (heurística)...")
    scored = enrich_renovation(scored)

    print("[5/6] Calculando scores...")
    scored = score_listings(scored, cfg.scoring)

    print("[6/6] Salvando no banco e gerando dashboard...")
    db = Storage("data/funda.db")
    n = db.save_snapshot(scored)
    csv_path = db.export_latest_csv("output/latest.csv")
    db.close()
    print(f"      {n} imóveis gravados em data/funda.db · CSV: {csv_path}")

    out = build_dashboard(scored, "output/dashboard.html", source=", ".join(used), scoring=cfg.scoring)
    print(f"      Dashboard: {out.resolve()}")

    if open_browser:
        webbrowser.open(out.resolve().as_uri())
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", nargs="+", default=None,
                    choices=["mock", "funda", "pararius"],
                    help="fontes a coletar (padrão: as do search.yaml)")
    ap.add_argument("--no-open", action="store_true", help="não abrir o navegador")
    args = ap.parse_args()
    run(sources=args.sources, open_browser=not args.no_open)
