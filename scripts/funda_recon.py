"""Reconhecimento da página do Funda — v2 (com anti-detecção + captura manual).

Mudanças em relação à v1:
  - Perfil de navegador PERSISTENTE (data/pw_profile): os cookies do DataDome
    ficam salvos, então depois de passar a verificação uma vez, as próximas
    execuções tendem a entrar direto.
  - Reduz a "assinatura de automação" (navigator.webdriver, flag do Chrome).
  - CAPTURA MANUAL: o script espera você resolver o desafio (se aparecer) e a
    lista de imóveis carregar. Só quando você apertar [Enter] ele captura.
  - Captura também __NEXT_DATA__ (o Funda é um app React/Next e costuma embutir
    os dados dos imóveis nesse script) além de JSON-LD.

Uso:
    python -m scripts.funda_recon

Uso pessoal, baixo volume. Se aparecer captcha, resolva na janela.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.config import load_config

CANDIDATE_SELECTORS = [
    "[data-test-id='search-result-item']",
    "[data-testid='search-result-item']",
    "[data-test-id='listing-card']",
    "[class*='search-result']",
    "[class*='SearchResult']",
    "[class*='ListingCard']",
    "[class*='listing']",
    "a[href*='/detail/koop/']",
    "a[href*='/koop/']",
    "article",
]

_STEALTH = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['nl-NL','nl','en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
window.chrome = { runtime: {} };
"""


def build_search_url(cfg) -> str:
    s = cfg.search
    base = "https://www.funda.nl/zoeken"
    url = f'{base}/{s.listing_type}?selected_area=["{s.city}"]'
    if s.price_min or s.price_max:
        url += f'&price="{s.price_min or 0}-{s.price_max or ""}"'
    return url


def _dump_json_scripts(page, out: Path) -> tuple[int, bool]:
    # JSON-LD
    jsonld = []
    for b in page.query_selector_all("script[type='application/ld+json']"):
        try:
            jsonld.append(json.loads(b.inner_text()))
        except Exception:
            pass
    (out / "funda_jsonld.json").write_text(json.dumps(jsonld, ensure_ascii=False, indent=2), encoding="utf-8")

    # __NEXT_DATA__ (dados do app React/Next)
    has_next = False
    nxt = page.query_selector("script#__NEXT_DATA__")
    if nxt:
        try:
            data = json.loads(nxt.inner_text())
            (out / "funda_next_data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            has_next = True
        except Exception:
            pass
    return len(jsonld), has_next


def main() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("Playwright não instalado. Rode: pip install playwright && playwright install chromium")

    cfg = load_config("config/search.yaml")
    url = build_search_url(cfg)
    out = Path("output"); out.mkdir(parents=True, exist_ok=True)
    profile = Path("data/pw_profile"); profile.mkdir(parents=True, exist_ok=True)

    print(f"Abrindo: {url}")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            locale="nl-NL",
            user_agent=cfg.scraper.user_agent,
            viewport={"width": 1440, "height": 950},
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx.add_init_script(_STEALTH)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        print("\n>>> Na janela do navegador:")
        print("    1. Se aparecer verificação/captcha do DataDome, resolva.")
        print("    2. Espere a LISTA DE IMÓVEIS aparecer.")
        input("    3. Então volte aqui e aperte [Enter] para capturar...")

        title = page.title()
        html = page.content()
        (out / "funda_page.html").write_text(html, encoding="utf-8")
        try:
            page.screenshot(path=str(out / "funda_page.png"), full_page=True)
        except Exception:
            page.screenshot(path=str(out / "funda_page.png"))
        n_jsonld, has_next = _dump_json_scripts(page, out)

        low = html.lower()
        datadome = any(t in low for t in ["datadome", "captcha", "verify you are human", "je bent bijna op de pagina"])
        print("\n===== DIAGNÓSTICO =====")
        print(f"Título da página : {title!r}")
        print(f"Tamanho do HTML  : {len(html):,} chars")
        print(f"Blocos JSON-LD   : {n_jsonld}")
        print(f"__NEXT_DATA__    : {'encontrado ✓' if has_next else 'não'}")
        print(f"Ainda parece bloqueio? {'SIM ⚠' if datadome else 'não 🎉'}")
        print("\nElementos por seletor candidato:")
        for sel in CANDIDATE_SELECTORS:
            try:
                n = len(page.query_selector_all(sel))
            except Exception:
                n = -1
            print(f"  {n:>4}  {sel}")
        print("\nSalvos em output/: funda_page.html, funda_jsonld.json, funda_next_data.json (se houver), funda_page.png")
        print("Me mande o diagnóstico acima.")

        input("\n[Enter] para fechar o navegador...")
        ctx.close()


if __name__ == "__main__":
    main()
