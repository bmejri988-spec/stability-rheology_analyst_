from langchain.tools import tool
from rag.vectorstore import load_vectorstore
import atexit
import re
from config import (
    RAG_MIN_STRONG_EVIDENCE,
    RAG_MIN_ACCEPTABLE_SCORE,
    RAG_MIN_ACCEPTABLE_LEXICAL,
)

_VDB = None


def _vectordb():
    global _VDB
    if _VDB is None:
        _VDB = load_vectorstore()
        atexit.register(_VDB.close)
    return _VDB


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_]+", text.lower()))


def _dense_candidates(query: str):
    vdb = _vectordb()
    dense = vdb.similarity_search_with_score(query, k=10)
    mmr = vdb.max_marginal_relevance_search(query, k=8, fetch_k=24)
    return dense, mmr


def _hybrid_rank(query: str):
    dense, mmr = _dense_candidates(query)
    query_tokens = _tokenize(query)

    candidates = {}

    for rank, (doc, score) in enumerate(dense, start=1):
        key = (
            doc.metadata.get("source", "unknown"),
            doc.metadata.get("page", -1),
            hash(doc.page_content),
        )
        candidates[key] = {
            "doc": doc,
            "dense_rank": rank,
            "dense_score": float(score),
            "mmr_bonus": 0.0,
        }

    for rank, doc in enumerate(mmr, start=1):
        key = (
            doc.metadata.get("source", "unknown"),
            doc.metadata.get("page", -1),
            hash(doc.page_content),
        )
        if key not in candidates:
            candidates[key] = {
                "doc": doc,
                "dense_rank": 999,
                "dense_score": 99.0,
                "mmr_bonus": 0.15,
            }
        else:
            candidates[key]["mmr_bonus"] = max(candidates[key]["mmr_bonus"], 0.15)

    ranked = []
    for item in candidates.values():
        doc = item["doc"]
        text_tokens = _tokenize(doc.page_content)
        overlap = len(query_tokens & text_tokens)
        lexical_score = overlap / max(1, len(query_tokens))

        content_type = doc.metadata.get("content_type", "section")
        type_boost = 0.08 if content_type in {"table", "figure_caption"} else 0.0

        dense_rank_score = 1.0 / item["dense_rank"]
        final_score = (0.60 * dense_rank_score) + (0.30 * lexical_score) + item["mmr_bonus"] + type_boost

        ranked.append((final_score, doc, lexical_score, content_type))

    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[:6]


def _normalize_formula_text(text: str) -> str:
    normalized = text

    # Repair common PDF/OCR flattening artifact for WLF equation denominator.
    wlf_pattern = re.compile(
        r"log\s*a[_ ]?t\s*\(\s*t\s*,\s*t[o0]\s*\)\s*=\s*-\s*c1\s*\(\s*t\s*-\s*t[o0]\s*\)\s*/\s*c2\s*\+\s*t\s*-\s*t[o0]",
        re.IGNORECASE,
    )
    if wlf_pattern.search(normalized):
        normalized = wlf_pattern.sub(
            "log aT(T,To)= - c1(T-To)/(c2 + T - To)",
            normalized,
        )

    return normalized


def _deduplicate_by_source_page(ranked_items):
    deduped = {}
    for item in ranked_items:
        score, doc, lexical_score, content_type = item
        key = (
            doc.metadata.get("source", "unknown"),
            doc.metadata.get("page", "?"),
        )

        if key not in deduped or score > deduped[key][0]:
            deduped[key] = item

    unique_items = list(deduped.values())
    unique_items.sort(key=lambda x: x[0], reverse=True)
    return unique_items[:6]


def _has_minimum_evidence(ranked_items) -> tuple[bool, str]:
    strong_items = [
        item
        for item in ranked_items
        if item[0] >= RAG_MIN_ACCEPTABLE_SCORE and item[2] >= RAG_MIN_ACCEPTABLE_LEXICAL
    ]

    if len(strong_items) >= RAG_MIN_STRONG_EVIDENCE:
        return True, ""

    if not ranked_items:
        return False, "No relevant evidence was retrieved."

    top_score, _, top_lexical, _ = ranked_items[0]
    return (
        False,
        (
            "Evidence quality is insufficient for a high-confidence answer. "
            f"Top score={top_score:.3f}, top lexical overlap={top_lexical:.3f}. "
            "Ask a narrower query or add more domain PDFs."
        ),
    )


def _format_evidence_block(ranked_items):
    lines = []
    for idx, (score, doc, lexical_score, content_type) in enumerate(ranked_items, start=1):
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "?")
        section = doc.metadata.get("section", "n/a")
        chunk_id = doc.metadata.get("chunk_id", "n/a")
        snippet = doc.page_content.strip().replace("\n", " ")
        snippet = _normalize_formula_text(snippet)
        if len(snippet) > 700:
            snippet = snippet[:700] + " ..."

        lines.append(
            f"[Evidence {idx}] score={score:.3f}, lexical={lexical_score:.3f}, type={content_type}, source={source}, page={page}, section={section}, chunk_id={chunk_id}\n{snippet}"
        )

    return "\n\n".join(lines)

@tool
def search_formulation_docs(query: str) -> str:
    """
    Retrieve, rank, and return evidence from the PDF RAG knowledge base with citations.
    """
    ranked_items = _hybrid_rank(query)
    if not ranked_items:
        return "No relevant evidence found in the formulation knowledge base."

    ranked_items = _deduplicate_by_source_page(ranked_items)
    has_enough, note = _has_minimum_evidence(ranked_items)

    if not has_enough:
        return (
            "[RAG_QUALITY_GATE]\n"
            f"{note}\n\n"
            "Top retrieved evidence (for transparency):\n\n"
            f"{_format_evidence_block(ranked_items[:3])}"
        )

    return _format_evidence_block(ranked_items)