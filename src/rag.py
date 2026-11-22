"""Retrieval-Augmented Generation system for course documents."""

import re
import uuid
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from src.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DB_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COURSE_DOCS_DIR,
    EMBEDDING_MODEL,
    TOP_K_RETRIEVAL,
)


def _load_embedder() -> SentenceTransformer:
    """
    Load the embedding model, preferring the local Hugging Face cache.

    Avoids network calls on startup (fixes SSL/proxy/timeout errors in class/demo).
    """
    try:
        return SentenceTransformer(EMBEDDING_MODEL, local_files_only=True)
    except (OSError, ValueError):
        pass

    try:
        return SentenceTransformer(EMBEDDING_MODEL)
    except Exception as exc:
        raise RuntimeError(
            "Failed to load the embedding model. Options:\n"
            "  1. Run with the project venv: .\\venv\\Scripts\\python app.py\n"
            "  2. Download once online: python -c \"from sentence_transformers "
            "import SentenceTransformer; "
            "SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')\"\n"
            "  3. Check your network / VPN / proxy settings for huggingface.co"
        ) from exc


class _KeywordRetriever:
    """Lightweight offline fallback when embedding model is unavailable."""

    def __init__(self, chunks: list[tuple[str, str]]):
        """chunks: list of (text, source filename)"""
        self._chunks = chunks

    def retrieve_with_scores(
        self,
        query: str,
        top_k: int = TOP_K_RETRIEVAL,
        source: str | None = None,
    ) -> list[tuple[str, float]]:
        query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        if not query_tokens:
            return []

        scored: list[tuple[str, float]] = []
        for text, doc_source in self._chunks:
            if source and doc_source != source:
                continue
            text_tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
            overlap = len(query_tokens & text_tokens)
            if overlap:
                scored.append((text, overlap / len(query_tokens)))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


class RAGSystem:
    """Loads course documents, embeds them, and retrieves relevant context."""

    def __init__(
        self,
        course_docs_dir: Path | None = None,
        chroma_db_dir: Path | None = None,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
        ephemeral: bool = False,
    ):
        self.course_docs_dir = Path(course_docs_dir or COURSE_DOCS_DIR)
        self.chroma_db_dir = Path(chroma_db_dir or CHROMA_DB_DIR)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._ephemeral = ephemeral

        self.chroma_db_dir.mkdir(parents=True, exist_ok=True)
        self._keyword_fallback: _KeywordRetriever | None = None
        self.embedder: SentenceTransformer | None = None
        try:
            self.embedder = _load_embedder()
        except RuntimeError:
            docs = self._load_txt_files()
            self._keyword_fallback = _KeywordRetriever(
                [(text, source) for _, text, source in docs]
            )
        collection_name = (
            f"{CHROMA_COLLECTION_NAME}_{uuid.uuid4().hex}"
            if ephemeral
            else CHROMA_COLLECTION_NAME
        )
        if ephemeral:
            self.client = chromadb.EphemeralClient()
        else:
            self.client = chromadb.PersistentClient(path=str(self.chroma_db_dir))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._ensure_documents_indexed()

    def close(self) -> None:
        """Release ChromaDB and model resources (important on Windows in tests)."""
        self.collection = None  # type: ignore[assignment]
        self.client = None  # type: ignore[assignment]
        self.embedder = None  # type: ignore[assignment]

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        if not text.strip():
            return []

        chunks: list[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= text_len:
                break
            start += self.chunk_size - self.chunk_overlap

        return chunks

    def _load_txt_files(self) -> list[tuple[str, str, str]]:
        """Load all .txt files from course_docs. Returns (id, text, source)."""
        documents: list[tuple[str, str, str]] = []
        if not self.course_docs_dir.exists():
            return documents

        for file_path in sorted(self.course_docs_dir.glob("*.txt")):
            text = file_path.read_text(encoding="utf-8")
            for i, chunk in enumerate(self._chunk_text(text)):
                doc_id = f"{file_path.stem}_{i}"
                documents.append((doc_id, chunk, file_path.name))
        return documents

    def _ensure_documents_indexed(self) -> None:
        """Index course documents if the collection is empty."""
        if self.collection.count() > 0:
            return

        documents = self._load_txt_files()
        if not documents:
            return

        if self.embedder is None:
            return

        ids = [doc_id for doc_id, _, _ in documents]
        texts = [text for _, text, _ in documents]
        metadatas = [{"source": source} for _, _, source in documents]
        embeddings = self.embedder.encode(texts, show_progress_bar=False).tolist()

        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def retrieve(
        self,
        query: str,
        top_k: int = TOP_K_RETRIEVAL,
        source: str | None = None,
    ) -> str:
        """Retrieve top-k relevant chunks and return as a single context string."""
        results = self.retrieve_with_scores(query, top_k=top_k, source=source)
        if not results:
            return ""
        return "\n\n".join(text for text, _ in results)

    def retrieve_with_scores(
        self,
        query: str,
        top_k: int = TOP_K_RETRIEVAL,
        source: str | None = None,
    ) -> list[tuple[str, float]]:
        """Retrieve top-k chunks with similarity scores (distance converted to score)."""
        if not query.strip():
            return []

        if self._keyword_fallback is not None:
            return self._keyword_fallback.retrieve_with_scores(
                query, top_k=top_k, source=source
            )

        if self.collection.count() == 0:
            return []

        query_embedding = self.embedder.encode([query], show_progress_bar=False).tolist()
        where_filter = {"source": source} if source else None

        def _query(n_results: int, where: dict | None) -> list[tuple[str, float]]:
            kwargs: dict = {
                "query_embeddings": query_embedding,
                "n_results": n_results,
                "include": ["documents", "distances"],
            }
            if where:
                kwargs["where"] = where
            results = self.collection.query(**kwargs)
            documents = results.get("documents", [[]])[0]
            distances = results.get("distances", [[]])[0]
            scored: list[tuple[str, float]] = []
            for doc, distance in zip(documents, distances):
                scored.append((doc, 1.0 - distance))
            return scored

        n_results = min(top_k, self.collection.count())
        if where_filter:
            scored = _query(n_results, where_filter)
            if scored:
                return scored
        return _query(n_results, None)

    def reset_index(self) -> None:
        """Clear and rebuild the vector index (useful for testing)."""
        self.client.delete_collection(CHROMA_COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._ensure_documents_indexed()
