"""Limpeza do banco: remove imóveis de uma fonte (por padrão, 'mock').

Uso:
    python -m scripts.db_clean            # remove as linhas mock
    python -m scripts.db_clean --source funda   # remove outra fonte, se quiser

Depois de limpar, reexporta output/latest.csv só com o que restou.
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path

DB = "data/funda.db"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="mock", help="fonte a remover (padrão: mock)")
    ap.add_argument("--db", default=DB)
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    before = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
    n = conn.execute(
        "SELECT COUNT(*) FROM snapshots WHERE source LIKE ?", (f"%{args.source}%",)
    ).fetchone()[0]
    conn.execute("DELETE FROM snapshots WHERE source LIKE ?", (f"%{args.source}%",))
    conn.commit()
    try:
        conn.execute("VACUUM")
    except sqlite3.OperationalError:
        pass  # VACUUM é opcional
    after = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]

    # reexporta o CSV
    cur = conn.execute("SELECT * FROM latest ORDER BY score DESC")
    cols = [d[0] for d in cur.description]
    Path("output").mkdir(exist_ok=True)
    with open("output/latest.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(cur.fetchall())

    srcs = [s[0] for s in conn.execute("SELECT DISTINCT source FROM snapshots").fetchall()]
    conn.close()
    print(f"Antes: {before} linhas | removidas ({args.source}): {n} | agora: {after}")
    print(f"Fontes restantes: {srcs}")
    print("CSV reexportado: output/latest.csv")


if __name__ == "__main__":
    main()
