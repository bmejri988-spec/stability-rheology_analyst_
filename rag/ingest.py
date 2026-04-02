import os
import sys
import json
import hashlib
import uuid
import time
from pathlib import Path
# Add the parent directory to the path so we can import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client.http.exceptions import ResponseHandlingException
from rag.vectorstore import load_vectorstore, get_backend_fingerprint
from rag.pdf_parser import extract_pdf_content
from config import (
    PDF_PATH,
    VECTOR_DB_PATH,
    QDRANT_UPSERT_BATCH_SIZE,
    QDRANT_UPSERT_MAX_RETRIES,
)


MANIFEST_PATH = Path(VECTOR_DB_PATH) / "ingest_manifest.json"


def _file_hash(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}

    try:
        with MANIFEST_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def _discover_pdf_files(pdf_folder: str) -> list[Path]:
    root = Path(pdf_folder)
    if not root.exists():
        return []

    return sorted([p for p in root.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"])


def _chunk_documents(documents):
    section_docs = [d for d in documents if d.metadata.get("content_type") == "section"]
    table_docs = [d for d in documents if d.metadata.get("content_type") == "table"]
    figure_docs = [d for d in documents if d.metadata.get("content_type") == "figure_caption"]

    # Narrative chunks for scientific discussion text.
    section_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    # Smaller chunks for dense tabular content.
    table_splitter = RecursiveCharacterTextSplitter(
        chunk_size=450,
        chunk_overlap=50,
        separators=["\n", " | ", " ", ""],
    )
    # Keep figure captions mostly atomic, split only when unusually long.
    figure_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=30,
        separators=["\n", ". ", " ", ""],
    )

    chunks = []
    if section_docs:
        chunks.extend(section_splitter.split_documents(section_docs))
    if table_docs:
        chunks.extend(table_splitter.split_documents(table_docs))
    if figure_docs:
        chunks.extend(figure_splitter.split_documents(figure_docs))

    for idx, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = idx

    return chunks


def _chunk_ids(source_name: str, chunks: list) -> list[str]:
    ids = []
    for idx, chunk in enumerate(chunks):
        page = chunk.metadata.get("page", "na")
        content_type = chunk.metadata.get("content_type", "section")
        source_chunk_id = f"{source_name}:{page}:{content_type}:{idx}"
        chunk.metadata["source_chunk_id"] = source_chunk_id
        ids.append(str(uuid.uuid5(uuid.NAMESPACE_URL, source_chunk_id)))
    return ids


def _add_documents_with_retries(vectordb, chunks: list, chunk_ids: list[str], source_name: str) -> None:
    if not chunks:
        return

    total = len(chunks)
    for start in range(0, total, QDRANT_UPSERT_BATCH_SIZE):
        end = min(start + QDRANT_UPSERT_BATCH_SIZE, total)
        batch_docs = chunks[start:end]
        batch_ids = chunk_ids[start:end]

        last_error = None
        for attempt in range(1, QDRANT_UPSERT_MAX_RETRIES + 1):
            try:
                vectordb.add_documents(batch_docs, ids=batch_ids)
                last_error = None
                break
            except ResponseHandlingException as exc:
                message = str(exc).lower()
                if "timed out" not in message and "timeout" not in message:
                    raise
                last_error = exc
                sleep_seconds = min(8.0, 0.5 * (2 ** (attempt - 1)))
                print(
                    f"Timeout upserting {source_name} batch {start}-{end - 1} "
                    f"(attempt {attempt}/{QDRANT_UPSERT_MAX_RETRIES}); retrying in {sleep_seconds:.1f}s..."
                )
                time.sleep(sleep_seconds)

        if last_error:
            raise RuntimeError(
                f"Failed to upsert source '{source_name}' batch {start}-{end - 1} after "
                f"{QDRANT_UPSERT_MAX_RETRIES} retries"
            ) from last_error

if __name__ == "__main__":
    print("Scanning PDFs for incremental ingestion...")
    pdf_files = _discover_pdf_files(PDF_PATH)
    print(f"Discovered {len(pdf_files)} PDF files.")

    manifest = _load_manifest()
    backend_fingerprint = get_backend_fingerprint()

    previous_backend = manifest.get("__backend__")
    if previous_backend and previous_backend != backend_fingerprint:
        print("Vector backend target changed; forcing full reindex for the new backend.")
        manifest = {}

    current_sources = {p.name for p in pdf_files}
    previous_sources = {k for k in manifest.keys() if k != "__backend__"}

    vectordb = load_vectorstore()

    try:
        removed_sources = sorted(previous_sources - current_sources)
        if removed_sources:
            print(f"Removing {len(removed_sources)} deleted sources from vectorstore...")
            for source_name in removed_sources:
                vectordb.delete(where={"source": source_name})
                manifest.pop(source_name, None)

        changed = 0
        skipped = 0
        total_chunks = 0

        for pdf_path in pdf_files:
            source_name = pdf_path.name
            file_hash = _file_hash(pdf_path)

            if manifest.get(source_name, {}).get("hash") == file_hash:
                skipped += 1
                continue

            changed += 1
            print(f"Processing: {source_name}")

            docs = extract_pdf_content(str(pdf_path))
            chunks = _chunk_documents(docs)
            chunk_ids = _chunk_ids(source_name, chunks)

            # Replace stale chunks for this source with the fresh chunk set.
            vectordb.delete(where={"source": source_name})
            if chunks:
                _add_documents_with_retries(vectordb, chunks, chunk_ids, source_name)
                total_chunks += len(chunks)

            manifest[source_name] = {
                "hash": file_hash,
                "chunks": len(chunks),
            }

        manifest["__backend__"] = backend_fingerprint
        _save_manifest(manifest)

        print("Incremental ingestion complete.")
        print(f"Updated files: {changed}")
        print(f"Skipped unchanged files: {skipped}")
        print(f"New chunks embedded this run: {total_chunks}")
    finally:
        vectordb.close()