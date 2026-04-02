from langchain_community.utilities import SerpAPIWrapper
from langchain.tools import tool
from config import SERPAPI_API_KEY

_SEARCH = None


def _search_client():
    global _SEARCH
    if _SEARCH is None:
        if not SERPAPI_API_KEY:
            raise ValueError("SERPAPI_API_KEY is not configured")
        _SEARCH = SerpAPIWrapper(serpapi_api_key=SERPAPI_API_KEY)
    return _SEARCH


@tool
def web_search(query: str) -> str:
    """Search the web for cosmetic formulation information."""
    try:
        return _search_client().run(query)
    except Exception as exc:
        return f"Error: web_search failed: {exc}"