import os
from dotenv import load_dotenv

load_dotenv()

# Azure OpenAI
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
CHAT_DEPLOYMENT_NAME = os.getenv("CHAT_DEPLOYMENT_NAME")
EMBEDDING_DEPLOYMENT_NAME = os.getenv("EMBEDDING_DEPLOYMENT_NAME")

# Qdrant
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "rheology_docs")
QDRANT_TIMEOUT_SECONDS = float(os.getenv("QDRANT_TIMEOUT_SECONDS", "120"))
QDRANT_UPSERT_BATCH_SIZE = int(os.getenv("QDRANT_UPSERT_BATCH_SIZE", "32"))
QDRANT_UPSERT_MAX_RETRIES = int(os.getenv("QDRANT_UPSERT_MAX_RETRIES", "4"))

# SerpAPI
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# Semantic Scholar
# Prefer upper-case env names; keep legacy camel-case aliases for backward compatibility.
SEMANTIC_SCHOLAR_URL = os.getenv("SEMANTIC_SCHOLAR_URL") or os.getenv("SemanticScholar_URL")
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY") or os.getenv("SemanticScholar_API_KEY")
SEMANTIC_SCHOLAR_TIMEOUT_SECONDS = int(os.getenv("SEMANTIC_SCHOLAR_TIMEOUT_SECONDS", "20"))
SEMANTIC_SCHOLAR_LIMIT = int(os.getenv("SEMANTIC_SCHOLAR_LIMIT", "6"))
SEMANTIC_SCHOLAR_RATE_LIMIT_SECONDS = float(os.getenv("SEMANTIC_SCHOLAR_RATE_LIMIT_SECONDS", "1.0"))

# PubChem
PUBCHEM_TIMEOUT_SECONDS = int(os.getenv("PUBCHEM_TIMEOUT_SECONDS", "20"))

# Firecrawl
FIRECRAWL_URL = os.getenv("FIRECRAWL_URL") or os.getenv("firecrawl_url", "https://api.firecrawl.dev/v2/agent")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY") or os.getenv("firecrawl_api_key")
FIRECRAWL_MODEL = os.getenv("FIRECRAWL_MODEL", "spark-1-mini")
FIRECRAWL_TIMEOUT_SECONDS = int(os.getenv("FIRECRAWL_TIMEOUT_SECONDS", "45"))

# RAG retrieval quality gates (agent/runtime tunable without code edits)
RAG_MIN_STRONG_EVIDENCE = int(os.getenv("RAG_MIN_STRONG_EVIDENCE", "2"))
RAG_MIN_ACCEPTABLE_SCORE = float(os.getenv("RAG_MIN_ACCEPTABLE_SCORE", "0.18"))
RAG_MIN_ACCEPTABLE_LEXICAL = float(os.getenv("RAG_MIN_ACCEPTABLE_LEXICAL", "0.08"))
ASSESSMENT_ENFORCE_TOOL_COVERAGE_RETRY = os.getenv("ASSESSMENT_ENFORCE_TOOL_COVERAGE_RETRY", "false").lower() == "true"

PDF_PATH = "data/pdf"
VECTOR_DB_PATH = "rag/vectorstore"