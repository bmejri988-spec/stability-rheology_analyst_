import argparse
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
import chromadb


def _build_qdrant_client(
    qdrant_url: str | None,
    qdrant_api_key: str | None,
    qdrant_local_path: str | None,
    timeout_seconds: float,
    check_compatibility: bool,
):
    if qdrant_url:
        return QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            timeout=timeout_seconds,
            check_compatibility=check_compatibility,
        )

    if qdrant_local_path:
        return QdrantClient(path=qdrant_local_path, timeout=timeout_seconds)

    raise ValueError("Provide either --qdrant-url (cloud) or --qdrant-local-path (local embedded)")


def _iter_collection_rows(collection, batch_size: int):
    offset = 0
    while True:
        batch = collection.get(
            include=["embeddings", "metadatas", "documents"],
            limit=batch_size,
            offset=offset,
        )

        ids = batch.get("ids")
        embeddings = batch.get("embeddings")
        metadatas = batch.get("metadatas")
        documents = batch.get("documents")

        if ids is None:
            ids = []
        if embeddings is None:
            embeddings = []
        if metadatas is None:
            metadatas = []
        if documents is None:
            documents = []

        if not ids:
            break

        for idx, item_id in enumerate(ids):
            embedding = embeddings[idx] if idx < len(embeddings) else None
            metadata = metadatas[idx] if idx < len(metadatas) else {}
            document = documents[idx] if idx < len(documents) else ""
            if embedding is None:
                continue
            # Chroma may return numpy arrays; Qdrant expects JSON-serializable float list.
            if hasattr(embedding, "tolist"):
                embedding = embedding.tolist()
            else:
                embedding = list(embedding)

            yield item_id, embedding, (metadata if metadata is not None else {}), (document if document is not None else "")

        if len(ids) < batch_size:
            break

        offset += batch_size


def _ensure_qdrant_collection(client: QdrantClient, collection_name: str, vector_size: int):
    if client.collection_exists(collection_name):
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
    )


def _to_qdrant_point_id(source_id: str):
    """Convert source IDs into Qdrant-compatible point IDs.

    Qdrant accepts either unsigned integers or UUIDs for point IDs.
    """
    value = str(source_id)

    if value.isdigit():
        return int(value)

    try:
        return str(uuid.UUID(value))
    except ValueError:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, value))


def migrate_collection(
    chroma_client,
    qdrant_client: QdrantClient,
    source_collection_name: str,
    target_collection_name: str,
    batch_size: int,
):
    collection = chroma_client.get_collection(name=source_collection_name)

    iterator = _iter_collection_rows(collection, batch_size=batch_size)
    first = next(iterator, None)
    if first is None:
        print(f"Collection '{source_collection_name}' is empty. Nothing to migrate.")
        return 0

    first_id, first_embedding, first_metadata, first_document = first
    _ensure_qdrant_collection(qdrant_client, target_collection_name, len(first_embedding))

    migrated = 0
    points = []

    def flush():
        nonlocal points
        if not points:
            return
        qdrant_client.upsert(collection_name=target_collection_name, points=points, wait=True)
        points = []

    def build_payload(metadata: dict, document: str, source_id: str):
        return {
            "metadata": metadata,
            "page_content": document,
            "source_id": source_id,
            "source_collection": source_collection_name,
        }

    points.append(
        models.PointStruct(
            id=_to_qdrant_point_id(str(first_id)),
            vector=first_embedding,
            payload=build_payload(first_metadata, first_document, str(first_id)),
        )
    )
    migrated += 1

    for item_id, embedding, metadata, document in iterator:
        points.append(
            models.PointStruct(
                id=_to_qdrant_point_id(str(item_id)),
                vector=embedding,
                payload=build_payload(metadata, document, str(item_id)),
            )
        )
        migrated += 1

        if len(points) >= batch_size:
            flush()

    flush()
    return migrated


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="One-time migration from Chroma persistent storage to Qdrant")
    parser.add_argument("--chroma-path", default="rag/vectorstore", help="Path to Chroma persistent directory")
    parser.add_argument("--chroma-collection", default=None, help="Specific Chroma collection to migrate")
    parser.add_argument(
        "--qdrant-url",
        default=os.getenv("QDRANT_URL"),
        help="Qdrant Cloud/remote REST URL (defaults to QDRANT_URL from .env)",
    )
    parser.add_argument(
        "--qdrant-api-key",
        default=os.getenv("QDRANT_API_KEY"),
        help="Qdrant API key for cloud (defaults to QDRANT_API_KEY from .env)",
    )
    parser.add_argument("--qdrant-local-path", default=None, help="Local Qdrant path (if not using cloud)")
    parser.add_argument(
        "--qdrant-collection",
        default=os.getenv("QDRANT_COLLECTION", "rheology_docs"),
        help="Target Qdrant collection name",
    )
    parser.add_argument("--batch-size", type=int, default=256, help="Batch size for reads/upserts")
    parser.add_argument("--timeout", type=float, default=30.0, help="Qdrant request timeout in seconds")
    parser.add_argument(
        "--skip-compatibility-check",
        action="store_true",
        help="Skip client/server version compatibility check",
    )
    args = parser.parse_args()

    chroma_path = Path(args.chroma_path)
    if not chroma_path.exists():
        raise FileNotFoundError(f"Chroma path not found: {chroma_path}")

    chroma_client = chromadb.PersistentClient(path=str(chroma_path))

    if args.chroma_collection:
        source_collections = [args.chroma_collection]
    else:
        source_collections = [c.name for c in chroma_client.list_collections()]

    if not source_collections:
        print("No Chroma collections found.")
        return

    qdrant_client = _build_qdrant_client(
        qdrant_url=args.qdrant_url,
        qdrant_api_key=args.qdrant_api_key,
        qdrant_local_path=args.qdrant_local_path,
        timeout_seconds=args.timeout,
        check_compatibility=not args.skip_compatibility_check,
    )

    total = 0
    for source_collection in source_collections:
        print(f"Migrating collection '{source_collection}' -> '{args.qdrant_collection}'")
        try:
            migrated = migrate_collection(
                chroma_client=chroma_client,
                qdrant_client=qdrant_client,
                source_collection_name=source_collection,
                target_collection_name=args.qdrant_collection,
                batch_size=args.batch_size,
            )
        except UnexpectedResponse as exc:
            if getattr(exc, "status_code", None) == 404:
                raise RuntimeError(
                    "Qdrant returned 404. Your QDRANT_URL points to the wrong host/path for data operations. "
                    "Use the project-specific Cluster REST URL from Qdrant Cloud Connect (not https://api.cloud.qdrant.io)."
                ) from exc
            raise
        except ResponseHandlingException as exc:
            raise RuntimeError(
                "Failed to connect to Qdrant. This is usually due to an incorrect endpoint or network timeout. "
                "Use your project-specific Qdrant data endpoint (not the control-plane endpoint https://api.cloud.qdrant.io), "
                "or provide --timeout 120 and --skip-compatibility-check."
            ) from exc
        print(f"Migrated {migrated} vectors from '{source_collection}'")
        total += migrated

    print(f"Done. Total migrated vectors: {total}")


if __name__ == "__main__":
    main()
