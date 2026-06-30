"""Retrieval-Augmented Generation system for course documents."""

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
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)
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

    def retrieve(self, query: str, top_k: int = TOP_K_RETRIEVAL) -> str:
        """Retrieve top-k relevant chunks and return as a single context string."""
        results = self.retrieve_with_scores(query, top_k=top_k)
        if not results:
            return ""
        return "\n\n".join(text for text, _ in results)

    def retrieve_with_scores(
        self, query: str, top_k: int = TOP_K_RETRIEVAL
    ) -> list[tuple[str, float]]:
        """Retrieve top-k chunks with similarity scores (distance converted to score)."""
        if not query.strip():
            return []

        if self.collection.count() == 0:
            return []

        query_embedding = self.embedder.encode([query], show_progress_bar=False).tolist()
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, self.collection.count()),
            include=["documents", "distances"],
        )

        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]

        scored: list[tuple[str, float]] = []
        for doc, distance in zip(documents, distances):
            # Cosine distance: lower is better; convert to similarity score
            score = 1.0 - distance
            scored.append((doc, score))
        return scored

    def reset_index(self) -> None:
        """Clear and rebuild the vector index (useful for testing)."""
        self.client.delete_collection(CHROMA_COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._ensure_documents_indexed()
