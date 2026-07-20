"""Copia o dashboard mais recente para docs/index.html (pasta do GitHub Pages).

Fluxo típico:
    python -m scripts.rebuild_dashboard   # (opcional) regenera com dados do banco
    python -m scripts.publish             # copia para docs/index.html
    git add docs && git commit -m "atualiza dashboard" && git push

O GitHub Pages serve a pasta docs/ — então o site público reflete o que estiver
em docs/index.html.
"""
from __future__ import annotations

import shutil
from pathlib import Path


def main() -> None:
    src = Path("output/dashboard.html")
    if not src.exists():
        print("Não achei output/dashboard.html — rode `python main.py` ou "
              "`python -m scripts.rebuild_dashboard` antes.")
        return
    docs = Path("docs")
    docs.mkdir(exist_ok=True)
    shutil.copy(src, docs / "index.html")
    print(f"OK: dashboard copiado para docs/index.html ({src.stat().st_size // 1024} KB).")
    print("Agora publique:")
    print('  git add docs && git commit -m "atualiza dashboard" && git push')


if __name__ == "__main__":
    main()
