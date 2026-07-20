"""Interface comum a todos os providers de coleta.

A ideia central da arquitetura: o resto do sistema só conhece esta interface.
Trocar scraping por uma API paga no futuro = escrever uma nova subclasse, sem
mudar scoring, storage ou relatório.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import AppConfig
from ..models import Listing


class BaseProvider(ABC):
    def __init__(self, config: AppConfig):
        self.config = config

    @abstractmethod
    def fetch_listings(self) -> list[Listing]:
        """Retorna a lista de imóveis segundo os parâmetros em config.search."""
        raise NotImplementedError
