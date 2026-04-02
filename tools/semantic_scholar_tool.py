import json
import requests
import time
from langchain.tools import tool
from config import (
    SEMANTIC_SCHOLAR_URL,
    SEMANTIC_SCHOLAR_API_KEY,
    SEMANTIC_SCHOLAR_TIMEOUT_SECONDS,
    SEMANTIC_SCHOLAR_LIMIT,
    SEMANTIC_SCHOLAR_RATE_LIMIT_SECONDS,
)
    

def _query_terms(text: str) -> set[str]:
    return {t.lower() for t in text.split() if len(t.strip()) >= 4}


def search_semantic_scholar(query: str, limit: int = 6):
    if not SEMANTIC_SCHOLAR_URL:
        return {"error": "SEMANTIC_SCHOLAR_URL is not configured"}

    if limit <= 0:
        limit = SEMANTIC_SCHOLAR_LIMIT

    headers = {
        "x-api-key": SEMANTIC_SCHOLAR_API_KEY
    }

    params = {
        "query": query,
        "limit": limit,
        "fields": "title,abstract,year,authors,venue,url"
    }

    response = requests.get(
        SEMANTIC_SCHOLAR_URL,
        headers=headers,
        params=params,
        timeout=SEMANTIC_SCHOLAR_TIMEOUT_SECONDS,
    )

    if response.status_code != 200:
        return {"error": response.text}

    data = response.json()

    query_terms = _query_terms(query)
    results = []
    seen_titles = set()

    for paper in data.get("data", []):
        title = (paper.get("title") or "").strip()
        if not title:
            continue
        norm_title = title.lower()
        if norm_title in seen_titles:
            continue

        abstract = paper.get("abstract")
        abstract_text = abstract if isinstance(abstract, str) else ""
        haystack = f"{title} {abstract_text}".lower()

        if query_terms and not any(term in haystack for term in query_terms):
            continue

        seen_titles.add(norm_title)
        results.append({
            "title": title,
            "abstract": paper.get("abstract"),
            "year": paper.get("year"),
            "authors": [a["name"] for a in paper.get("authors", [])],
            "venue": paper.get("venue"),
            "url": paper.get("url")
        })

        if len(results) >= limit:
            break

    # 🔥 IMPORTANT: respect rate limit
    if SEMANTIC_SCHOLAR_RATE_LIMIT_SECONDS > 0:
        time.sleep(SEMANTIC_SCHOLAR_RATE_LIMIT_SECONDS)

    return results

@tool
def semantic_scholar_search(query: str) -> str:
    """Search scientific literature for formulation, rheology, and stability evidence."""
    results = search_semantic_scholar(query, limit=SEMANTIC_SCHOLAR_LIMIT)

    if isinstance(results, dict) and "error" in results:
        return json.dumps(results, ensure_ascii=True)

    payload = {
        "query": query,
        "count": len(results),
        "papers": results,
    }
    return json.dumps(payload, ensure_ascii=True)