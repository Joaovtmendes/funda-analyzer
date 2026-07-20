"""Provider de scraping do Funda.nl via Playwright.

Baseado na estrutura REAL da página (capturada pelo recon):
  - Cada imóvel tem uma âncora de endereço: [data-testid="listingDetailsAddress"]
  - O card é o ancestral <div class="@container ...">
  - Preço aparece como "€ 525.000 k.k."
  - Uma <ul> lista área ("65 m²"), quartos ("2") e label energético ("A+")
  - Paginação por ?page=N

Anti-DataDome: reusa o PERFIL PERSISTENTE data/pw_profile (o mesmo do recon), de
modo que o cookie do DataDome já resolvido continue valendo. Reduz também a
assinatura de automação.

Uso pessoal e baixo volume: mantenha max_results moderado e os delays generosos.
Só coleta a página de busca (nível de lista). Ano de construção e descrição
completa ficam na página de detalhe — enriquecimento futuro (ver ROADMAP.md).
"""
from __future__ import annotations

import random
import re
import time
from pathlib import Path

from ..models import Listing
from .base import BaseProvider

FUNDA_BASE = "https://www.funda.nl"
ADDRESS_SEL = "[data-testid='listingDetailsAddress']"
PROFILE_DIR = "data/pw_profile"

_STEALTH = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['nl-NL','nl','en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
window.chrome = { runtime: {} };
"""


class FundaScraperProvider(BaseProvider):
    def _base_url(self) -> str:
        s = self.config.search
        url = f'{FUNDA_BASE}/zoeken/{s.listing_type}?selected_area=["{s.city}"]'
        if s.price_min or s.price_max:
            url += f'&price="{s.price_min or 0}-{s.price_max or ""}"'
        return url

    def _sleep(self) -> None:
        sc = self.config.scraper
        time.sleep(random.uniform(sc.min_delay_seconds, sc.max_delay_seconds))

    # JS que extrai TODOS os cards de uma página numa passada só (rápido e estável)
    _EXTRACT_JS = """
    () => {
      const anchors = document.querySelectorAll("[data-testid='listingDetailsAddress']");
      return Array.from(anchors).map(a => {
        // sobe até o menor ancestral que contém o preço (= o card)
        let el = a, card = null;
        for (let i = 0; i < 8 && el; i++) {
          el = el.parentElement;
          if (el && el.innerText && el.innerText.indexOf('€') !== -1) { card = el; break; }
        }
        const scope = card || a;
        const spans = Array.from(scope.querySelectorAll('ul li span')).map(s => (s.innerText || '').trim());
        const img = scope.querySelector('img');
        return {
          href: a.getAttribute('href') || '',
          addr: a.innerText || '',
          text: scope.innerText || '',
          spans: spans,
          img: img ? img.getAttribute('src') : null
        };
      });
    }
    """

    def fetch_listings(self) -> list[Listing]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Playwright não instalado. Rode: pip install playwright && playwright install chromium"
            ) from exc

        Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)
        base = self._base_url()
        want = self.config.search.max_results     # None = sem limite (cidade toda)
        unlimited = want is None
        max_pages = 300 if unlimited else 50      # trava de segurança
        collected: list[Listing] = []

        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=PROFILE_DIR,
                headless=self.config.scraper.headless,
                locale="nl-NL",
                user_agent=self.config.scraper.user_agent,
                viewport={"width": 1440, "height": 950},
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx.add_init_script(_STEALTH)
            # bloqueia imagens/mídia/fontes: mais leve, evita crash e é educado com o site
            ctx.route("**/*", lambda route: (
                route.abort() if route.request.resource_type in ("image", "media", "font")
                else route.continue_()
            ))
            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            page_num = 1
            while unlimited or len(collected) < want:
                url = base if page_num == 1 else f"{base}&page={page_num}"
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_selector(ADDRESS_SEL, timeout=15000)
                except Exception:
                    if page_num == 1:
                        raise RuntimeError(
                            "Não encontrei imóveis — provavelmente o DataDome bloqueou. "
                            "Rode `python -m scripts.funda_recon` (janela visível) para revalidar "
                            "o perfil, ou defina scraper.headless: false no search.yaml."
                        )
                    break  # falha em página seguinte: fica com o que já coletamos

                raw = page.evaluate(self._EXTRACT_JS)
                page_items = [self._parse_card(r) for r in raw]
                page_items = [x for x in page_items if x]
                if not page_items:
                    break
                collected.extend(page_items)
                print(f"      [funda] página {page_num}: {len(page_items)} imóveis (total {len(collected)})")
                page_num += 1
                if page_num > max_pages:  # trava de segurança
                    break
                self._sleep()

            ctx.close()

        # Sem filtros de área/quartos/label na coleta: guardamos TUDO no banco
        # para a análise histórica. Esses filtros agora vivem no dashboard.
        return collected if unlimited else collected[:want]

    def _parse_card(self, r: dict) -> Listing | None:
        """Transforma o dict extraído pelo JS num objeto Listing."""
        href = r.get("href") or ""
        if "/detail/" not in href:
            return None
        url = href if href.startswith("http") else FUNDA_BASE + href
        listing_id = url.rstrip("/").split("/")[-1]

        # endereço: "Rua 92\n1018 RN Amsterdam"
        lines = [l.strip() for l in (r.get("addr") or "").split("\n") if l.strip()]
        street = lines[0] if lines else "?"
        postal = city = None
        if len(lines) > 1:
            m = re.match(r"([0-9]{4}\s?[A-Z]{2})\s+(.*)", lines[1])
            if m:
                postal, city = m.group(1), m.group(2).strip()
            else:
                city = lines[1]

        text = r.get("text") or ""
        price = None
        pm = re.search(r"€\s*([\d.]+)", text)
        if pm:
            price = int(pm.group(1).replace(".", ""))

        # área / quartos / label a partir dos spans da <ul>
        area = rooms = label = None
        for t in r.get("spans") or []:
            t = t.strip()
            if "m²" in t and area is None:
                digits = re.sub(r"\D", "", t)
                area = int(digits) if digits else None
            elif re.fullmatch(r"[A-G]\+*", t):
                label = t
            elif re.fullmatch(r"\d+", t) and rooms is None:
                rooms = int(t)
        if area is None:  # fallback: pega do texto do card
            am = re.search(r"([\d.]+)\s*m²", text)
            if am:
                area = int(am.group(1).replace(".", ""))

        photos = [r["img"]] if r.get("img") else []

        return Listing(
            listing_id=listing_id,
            source="funda",
            url=url,
            address=street,
            postal_code=postal,
            city=city or self.config.search.city.title(),
            price=price,
            area_m2=area,
            rooms=rooms,
            energy_label=label,
            photos=photos,
        )

