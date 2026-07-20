"""Análise de reforma pelas fotos usando a visão da Claude (Opção A).

Roda POR CIMA da heurística e SÓ nos melhores imóveis do ranking, para manter o
custo baixo. Para cada imóvel, baixa algumas fotos, envia à API da Anthropic e
recebe uma avaliação estruturada (esforço de reforma + observações por cômodo),
que refina o `RenovationAssessment` preenchido pela heurística.

Pré-requisitos:
  - `pip install anthropic`
  - variável de ambiente ANTHROPIC_API_KEY com sua chave (sk-ant-...)

Uso típico (via main.py): analisa só os top-N depois do score.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Optional

import httpx

from ..models import Listing, RenovationAssessment, ScoredListing

# Modelo com visão. Sonnet equilibra qualidade e custo; troque por
# "claude-haiku-4-5-20251001" para ficar ainda mais barato.
DEFAULT_MODEL = "claude-sonnet-5"
MAX_IMAGES_PER_LISTING = 4  # limita o custo por imóvel

_PROMPT = """Você é um avaliador imobiliário. Analise as fotos deste imóvel à venda na Holanda e avalie o potencial/necessidade de REFORMA.

Responda APENAS com um JSON válido, sem texto ao redor, neste formato:
{
  "effort": "baixo | medio | alto",
  "summary": "uma frase objetiva em português",
  "flags": ["observações curtas, ex: 'cozinha datada anos 80', 'banheiro reformado', 'piso a trocar']"
}

Critério de 'effort':
- baixo: pronto pra morar, reformado/moderno
- medio: alguns pontos a modernizar
- alto: reforma pesada (cozinha e banheiro antigos, estrutura/acabamento comprometidos)"""


class VisionRenovationClient:
    def __init__(self, model: str = DEFAULT_MODEL, max_images: int = MAX_IMAGES_PER_LISTING):
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Instale a SDK: pip install anthropic") from exc
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("Defina a variável ANTHROPIC_API_KEY com sua chave.")
        self._client = Anthropic()
        self.model = model
        self.max_images = max_images
        self._http = httpx.Client(timeout=30.0, follow_redirects=True)

    def _download(self, url: str) -> Optional[tuple[str, str]]:
        """Baixa a imagem e devolve (media_type, base64). None se falhar."""
        try:
            r = self._http.get(url)
            r.raise_for_status()
            media = r.headers.get("content-type", "image/jpeg").split(";")[0]
            if not media.startswith("image/"):
                media = "image/jpeg"
            return media, base64.standard_b64encode(r.content).decode()
        except Exception as e:  # noqa: BLE001
            print(f"[vision] falha ao baixar {url}: {e}")
            return None

    def analyze(self, listing: Listing) -> Optional[RenovationAssessment]:
        if not listing.photos:
            return None
        content = []
        for url in listing.photos[: self.max_images]:
            img = self._download(url)
            if img:
                media, b64 = img
                content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": media, "data": b64},
                })
        if not content:
            return None
        content.append({"type": "text", "text": _PROMPT})

        try:
            msg = self._client.messages.create(
                model=self.model,
                max_tokens=400,
                messages=[{"role": "user", "content": content}],
            )
            text = msg.content[0].text.strip()
            data = _extract_json(text)
            return RenovationAssessment(
                effort=data.get("effort"),
                summary="🔍 " + (data.get("summary") or ""),  # marca que veio da visão
                flags=data.get("flags", [])[:4],
            )
        except Exception as e:  # noqa: BLE001
            print(f"[vision] falha ao analisar {listing.address}: {e}")
            return None


def _extract_json(text: str) -> dict:
    """Extrai o primeiro objeto JSON de um texto (robusto a cercas de código)."""
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    return {}


def enrich_vision(items: list[ScoredListing], top_n: int = 10,
                  client: Optional[VisionRenovationClient] = None) -> list[ScoredListing]:
    """Aplica a visão da Claude só nos `top_n` primeiros (já ordenados por score)."""
    client = client or VisionRenovationClient()
    for s in items[:top_n]:
        result = client.analyze(s.listing)
        if result:
            s.renovation = result  # refina a avaliação heurística com a visão
    return items
