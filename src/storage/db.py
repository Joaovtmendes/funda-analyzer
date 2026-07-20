"""Armazenamento em SQLite (banco de arquivo único, sem servidor).

Por que SQLite: já vem no Python, é um único arquivo (data/funda.db) fácil de
mover e abrir em qualquer visualizador de tabela (DB Browser for SQLite, a
extensão SQLite Viewer no VS Code, ou exportando pra CSV/Excel).

Cada execução grava um SNAPSHOT com a data/hora. Guardar o histórico é o que
permite detectar QUEDAS DE PREÇO: o mesmo imóvel capturado em datas diferentes.

Tabelas:
  - snapshots: uma linha por imóvel por execução (histórico completo)
  - latest (view): apenas a captura mais recente de cada imóvel
"""
from __future__ import annotations

import csv
import sqlite3
from datetime import datetime
from pathlib import Path

from ..models import ScoredListing

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at      TEXT NOT NULL,
    listing_id       TEXT NOT NULL,
    source           TEXT,
    url              TEXT,
    address          TEXT,
    postal_code      TEXT,
    city             TEXT,
    price            INTEGER,
    area_m2          INTEGER,
    price_per_m2     REAL,
    rooms            INTEGER,
    year_built       INTEGER,
    energy_label     TEXT,
    woz_value        INTEGER,
    price_vs_woz_pct REAL,
    kadaster_median  INTEGER,
    price_vs_sales_pct REAL,
    reno_effort      TEXT,
    score            REAL
);
CREATE INDEX IF NOT EXISTS idx_listing ON snapshots(listing_id);
CREATE INDEX IF NOT EXISTS idx_captured ON snapshots(captured_at);

-- captura mais recente de cada imóvel
CREATE VIEW IF NOT EXISTS latest AS
SELECT s.* FROM snapshots s
JOIN (SELECT listing_id, MAX(captured_at) AS mx FROM snapshots GROUP BY listing_id) t
  ON s.listing_id = t.listing_id AND s.captured_at = t.mx;
"""

_COLUMNS = [
    "captured_at", "listing_id", "source", "url", "address", "postal_code", "city",
    "price", "area_m2", "price_per_m2", "rooms", "year_built", "energy_label",
    "woz_value", "price_vs_woz_pct", "kadaster_median", "price_vs_sales_pct",
    "reno_effort", "score",
]


class Storage:
    def __init__(self, path: str | Path = "data/funda.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def _row(self, s: ScoredListing, now: str) -> tuple:
        l = s.listing
        return (
            now, l.listing_id, l.source, l.url, l.address, l.postal_code, l.city,
            l.price, l.area_m2, l.price_per_m2, l.rooms, l.year_built, l.energy_label,
            s.woz.woz_value if s.woz else None, s.price_vs_woz_pct,
            s.kadaster_median, s.price_vs_sales_pct,
            s.renovation.effort if s.renovation else None, s.score,
        )

    def save_snapshot(self, items: list[ScoredListing]) -> int:
        now = datetime.utcnow().isoformat(timespec="seconds")
        rows = [self._row(s, now) for s in items]
        placeholders = ",".join(["?"] * len(_COLUMNS))
        self.conn.executemany(
            f"INSERT INTO snapshots ({','.join(_COLUMNS)}) VALUES ({placeholders})", rows
        )
        self.conn.commit()
        return len(rows)

    def price_history(self, listing_id: str) -> list[tuple[str, int]]:
        """Histórico (data, preço) de um imóvel, para detectar quedas."""
        cur = self.conn.execute(
            "SELECT captured_at, price FROM snapshots WHERE listing_id=? ORDER BY captured_at",
            (listing_id,),
        )
        return cur.fetchall()

    def export_latest_csv(self, csv_path: str | Path = "output/latest.csv") -> Path:
        """Exporta a captura mais recente de cada imóvel para CSV (abrir no Excel)."""
        csv_path = Path(csv_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        cur = self.conn.execute("SELECT * FROM latest ORDER BY score DESC")
        cols = [d[0] for d in cur.description]
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(cur.fetchall())
        return csv_path

    def close(self) -> None:
        self.conn.close()
