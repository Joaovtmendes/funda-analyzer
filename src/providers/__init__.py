from .base import BaseProvider
from .mock import MockProvider
from ..models import Listing

__all__ = ["BaseProvider", "MockProvider", "get_provider", "collect_all"]


def get_provider(name: str, config):
    """Fábrica de providers. Cada fonte respeita o mesmo contrato BaseProvider."""
    name = (name or "mock").lower()
    if name == "mock":
        return MockProvider(config)
    if name == "funda":
        from .funda import FundaScraperProvider  # import tardio: só exige playwright no modo real
        return FundaScraperProvider(config)
    if name == "pararius":
        from .pararius import ParariusProvider
        return ParariusProvider(config)
    raise ValueError(f"Provider desconhecido: {name}")


def _norm(text: str | None) -> str:
    return " ".join((text or "").lower().split())


def _completeness(l: Listing) -> int:
    """Quantos campos úteis o imóvel tem preenchidos (para escolher o melhor na dedup)."""
    fields = (l.price, l.area_m2, l.energy_label, l.year_built, l.description)
    return sum(1 for f in fields if f) + len(l.photos)


def _dedupe(listings: list[Listing]) -> list[Listing]:
    """Junta imóveis iguais que aparecem em fontes diferentes.

    Chave = endereço normalizado + código postal. Quando há duplicata, mantém o
    registro mais completo e registra as duas origens (ex: 'funda+pararius'),
    preenchendo campos que faltarem a partir do outro.
    """
    best: dict[tuple[str, str], Listing] = {}
    for l in listings:
        key = (_norm(l.address), (l.postal_code or "").replace(" ", "").lower())
        if not key[0]:  # sem endereço, não dá pra deduplicar com segurança
            best[(l.listing_id, l.source)] = l
            continue
        if key not in best:
            best[key] = l
        else:
            keep, other = best[key], l
            if _completeness(other) > _completeness(keep):
                keep, other = other, keep
            # registra ambas as origens
            srcs = sorted(set(keep.source.split("+") + other.source.split("+")))
            keep.source = "+".join(srcs)
            # completa campos ausentes com o outro registro
            for f in ("price", "area_m2", "energy_label", "year_built", "description", "postal_code"):
                if not getattr(keep, f) and getattr(other, f):
                    setattr(keep, f, getattr(other, f))
            if not keep.photos and other.photos:
                keep.photos = other.photos
            best[key] = keep
    return list(best.values())


def collect_all(config, sources: list[str] | None = None) -> list[Listing]:
    """Coleta de TODAS as fontes configuradas, junta e remove duplicatas.

    Fontes não implementadas (esqueletos) ou que derem erro são puladas com
    aviso, sem derrubar a coleta das demais.
    """
    sources = sources or config.search.sources or ["mock"]
    collected: list[Listing] = []
    for name in sources:
        try:
            provider = get_provider(name, config)
            items = provider.fetch_listings()
            for it in items:
                it.source = name
            collected.extend(items)
            print(f"      [{name}] {len(items)} imóveis")
        except NotImplementedError:
            print(f"      [{name}] ainda não implementado — pulando (ver ROADMAP.md)")
        except Exception as e:  # noqa: BLE001
            print(f"      [{name}] erro: {e} — pulando")

    merged = _dedupe(collected)
    dups = len(collected) - len(merged)
    if dups > 0:
        print(f"      {dups} duplicata(s) unificada(s) entre fontes")
    return merged
