"""Re-export search base classes from package __init__."""

from backend.services.search import SearchProvider, SearchManager, SearchResult

__all__ = ["SearchProvider", "SearchManager", "SearchResult"]
