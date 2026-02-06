"""Plugin registry for ticket sources, using Python entry points."""

from __future__ import annotations

import importlib.metadata
import logging

from levelup.tickets.base import TicketSource
from levelup.tickets.manual import ManualTicketSource

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "levelup.ticket_sources"


class TicketSourceRegistry:
    """Registry that discovers and manages ticket sources."""

    def __init__(self) -> None:
        self._sources: dict[str, type[TicketSource]] = {}
        # Always register the built-in manual source
        self._sources["manual"] = ManualTicketSource

    def discover_plugins(self) -> None:
        """Discover ticket source plugins via entry points."""
        try:
            eps = importlib.metadata.entry_points()
            group = eps.get(ENTRY_POINT_GROUP, []) if isinstance(eps, dict) else eps.select(group=ENTRY_POINT_GROUP)
            for ep in group:
                try:
                    cls = ep.load()
                    if isinstance(cls, type) and issubclass(cls, TicketSource):
                        self._sources[ep.name] = cls
                        logger.info("Discovered ticket source plugin: %s", ep.name)
                except Exception as e:
                    logger.warning("Failed to load ticket source plugin %s: %s", ep.name, e)
        except Exception as e:
            logger.warning("Failed to discover ticket source plugins: %s", e)

    def get(self, name: str) -> TicketSource:
        """Get a ticket source instance by name."""
        if name not in self._sources:
            available = ", ".join(self._sources.keys())
            raise KeyError(f"Unknown ticket source: {name}. Available: {available}")
        return self._sources[name]()

    @property
    def available_sources(self) -> list[str]:
        return list(self._sources.keys())
