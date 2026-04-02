from pathlib import Path

from langchain_openai import AzureOpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from openai import NotFoundError
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
from config import (
    VECTOR_DB_PATH,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    EMBEDDING_DEPLOYMENT_NAME,
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    QDRANT_TIMEOUT_SECONDS,
)


def get_backend_fingerprint() -> str:
    if QDRANT_URL:
        return f"qdrant:{QDRANT_URL}:{QDRANT_COLLECTION}"

    local_path = str(Path(VECTOR_DB_PATH) / "qdrant")
    return f"qdrant-local:{local_path}:{QDRANT_COLLECTION}"


class VectorStoreAdapter:
    """Adapter preserving the existing vectorstore call surface across backends."""

    def __init__(self, client: QdrantClient, store: QdrantVectorStore, collection_name: str):
        self._client = client
        self._store = store
        self._collection_name = collection_name

    def similarity_search_with_score(self, *args, **kwargs):
        return self._store.similarity_search_with_score(*args, **kwargs)

    def max_marginal_relevance_search(self, *args, **kwargs):
        return self._store.max_marginal_relevance_search(*args, **kwargs)

    def add_documents(self, *args, **kwargs):
        return self._store.add_documents(*args, **kwargs)

    def as_retriever(self, *args, **kwargs):
        return self._store.as_retriever(*args, **kwargs)

    def delete(self, where: dict | None = None, ids: list[str] | None = None):
        if ids:
            return self._store.delete(ids=ids)

        if where and "source" in where:
            source_name = where["source"]
            source_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.source",
                        match=models.MatchValue(value=source_name),
                    )
                ]
            )
            try:
                self._client.delete(
                    collection_name=self._collection_name,
                    points_selector=models.FilterSelector(filter=source_filter),
                    wait=True,
                )
            except UnexpectedResponse as exc:
                raw = str(exc)
                if getattr(exc, "status_code", None) == 400 and "index required" in raw.lower():
                    _ensure_payload_indexes(self._client, self._collection_name)
                    self._client.delete(
                        collection_name=self._collection_name,
                        points_selector=models.FilterSelector(filter=source_filter),
                        wait=True,
                    )
                else:
                    raise
            return

        raise ValueError("Unsupported delete call. Provide ids or where={'source': ...}.")

    def close(self):
        self._client.close()


def _build_embeddings_client() -> AzureOpenAIEmbeddings:
    if not AZURE_OPENAI_API_KEY:
        raise ValueError("AZURE_OPENAI_API_KEY is missing in environment variables.")
    if not EMBEDDING_DEPLOYMENT_NAME:
        raise ValueError("EMBEDDING_DEPLOYMENT_NAME is missing in environment variables.")
    if not AZURE_OPENAI_ENDPOINT:
        raise ValueError("Azure OpenAI endpoint is missing. Set AZURE_OPENAI_ENDPOINT.")

    return AzureOpenAIEmbeddings(
        azure_deployment=EMBEDDING_DEPLOYMENT_NAME,
        model=EMBEDDING_DEPLOYMENT_NAME,
        api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version="2024-12-01-preview",
    )


def _build_qdrant_client() -> QdrantClient:
    if QDRANT_URL:
        return QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=QDRANT_TIMEOUT_SECONDS,
        )

    local_path = str(Path(VECTOR_DB_PATH) / "qdrant")
    return QdrantClient(path=local_path, timeout=QDRANT_TIMEOUT_SECONDS)


def _ensure_collection(client: QdrantClient, collection_name: str, embeddings: AzureOpenAIEmbeddings):
    if not client.collection_exists(collection_name):
        vector_size = len(embeddings.embed_query("healthcheck"))
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )

    _ensure_payload_indexes(client, collection_name)


def _ensure_payload_indexes(client: QdrantClient, collection_name: str):
    # Required for filtered delete/query operations in environments enforcing payload indexes.
    required_indexes = {
        "metadata.source": models.PayloadSchemaType.KEYWORD,
    }

    for field_name, schema in required_indexes.items():
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=schema,
                wait=True,
            )
        except Exception as exc:
            message = str(exc).lower()
            if "already exists" in message or "conflict" in message:
                continue
            raise RuntimeError(f"Failed to ensure Qdrant payload index for '{field_name}': {exc}") from exc


def _build_vector_store() -> VectorStoreAdapter:
    embeddings = _build_embeddings_client()

    # Fail fast with a clear message if endpoint/deployment is invalid.
    try:
        embeddings.embed_query("healthcheck")
    except NotFoundError as exc:
        raise RuntimeError(
            "Embedding deployment or endpoint was not found. Verify EMBEDDING_DEPLOYMENT_NAME and AZURE_OPENAI_ENDPOINT. "
            "Use the resource root endpoint (e.g., https://<resource>.cognitiveservices.azure.com), not /openai/v1."
        ) from exc

    client = _build_qdrant_client()
    _ensure_collection(client, QDRANT_COLLECTION, embeddings)

    store = QdrantVectorStore(
        client=client,
        collection_name=QDRANT_COLLECTION,
        embedding=embeddings,
    )
    return VectorStoreAdapter(client=client, store=store, collection_name=QDRANT_COLLECTION)


def create_vector_db(documents):
    vectordb = _build_vector_store()
    if documents:
        vectordb.add_documents(documents)
    return vectordb


def load_vectorstore():
    return _build_vector_store()