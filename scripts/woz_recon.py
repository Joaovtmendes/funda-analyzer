"""Recon do WOZ — v5: captura de rede com anti-detecção + busca manual.

O wozwaardeloket devolve 403 pra navegador automatizado "cru". Aqui aplicamos o
mesmo tratamento do Funda: User-Agent realista, idioma holandês e redução da
assinatura de automação. Você busca o endereço na janela; o script grava as
chamadas XHR/JSON por trás e imprime ao apertar [Enter].

Uso:
    python -m scripts.woz_recon

Dados públicos, baixo volume.
"""
from __future__ import annotations

from pathlib import Path

CAPTURED = []
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
STEALTH = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['nl-NL','nl','en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
window.chrome = { runtime: {} };
"""


def main() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("Playwright não instalado. Rode: pip install playwright && playwright install chromium")

    def on_response(resp):
        try:
            req = resp.request
            ct = resp.headers.get("content-type", "")
            if req.resource_type in ("xhr", "fetch") or "json" in ct:
                try:
                    body = resp.text()[:1800]
                except Exception:
                    body = "<sem corpo>"
                CAPTURED.append((req.method, resp.url, resp.status, ct, body))
        except Exception:
            pass

    profile = Path("data/pw_profile_woz"); profile.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            locale="nl-NL",
            user_agent=UA,
            viewport={"width": 1366, "height": 900},
            extra_http_headers={"Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8"},
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx.add_init_script(STEALTH)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.on("response", on_response)
        page.goto("https://www.wozwaardeloket.nl/", wait_until="domcontentloaded", timeout=60000)

        print("\n>>> Na janela do navegador:")
        print("    1. Digite um endereço no campo de busca (ex: Cornelis Vermuydenstraat 92 Amsterdam)")
        print("    2. Clique na sugestão; espere o VALOR WOZ aparecer na tela")
        input("    3. Então volte aqui e aperte [Enter] para capturar...")

        ctx.close()

    def score(item):
        u = item[1].lower()
        return sum(k in u for k in ("woz", "waarde", "lookup", "suggest", "api"))

    CAPTURED.sort(key=score, reverse=True)
    print(f"\n===== {len(CAPTURED)} requisições XHR/JSON capturadas =====")
    for method, url, status, ct, body in CAPTURED:
        print(f"\n[{method} {status}] {url}")
        print(f"  content-type: {ct}")
        print(f"  corpo: {body}")


if __name__ == "__main__":
    main()
