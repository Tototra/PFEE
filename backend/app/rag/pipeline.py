"""Pipeline RAG (Retrieval-Augmented Generation) — Couche C3.

Indexe les documents métier (notices, comptes rendus, bonnes pratiques CVC)
dans ChromaDB et fournit un service de recherche sémantique.

Modèle d'embedding : BAAI/bge-m3 (multilingue FR/EN, performant, 1024d).

Pipeline d'ingestion :
  1. Lecture PDF / texte
  2. Chunking sémantique (LlamaIndex SentenceSplitter)
  3. Génération embeddings
  4. Stockage ChromaDB

Pipeline de retrieval :
  1. Embedding de la query
  2. Recherche top-k dans ChromaDB
  3. Re-ranking optionnel (cross-encoder en V2)
  4. Retour des chunks + scores + sources
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RagDocument:
    """Document à indexer."""

    content: str
    metadata: dict[str, Any]
    doc_id: str | None = None


@dataclass
class RagResult:
    """Résultat de recherche RAG."""

    content: str
    metadata: dict[str, Any]
    score: float
    source: str


class RagPipeline:
    """Pipeline RAG basé sur ChromaDB + sentence-transformers.

    Note : LlamaIndex est utilisé séparément pour l'orchestration LLM.
    Ici on garde une couche bas-niveau directe sur ChromaDB pour la
    flexibilité (multi-collection, filtres metadata, etc.).
    """

    COLLECTION_NAME = "coachia_knowledge"

    def __init__(self, persist_dir: str | None = None) -> None:
        self.persist_dir = Path(persist_dir or settings.chroma_persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None
        self._embedder: Any = None

    @property
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    @property
    def collection(self) -> chromadb.Collection:
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def _get_embedder(self) -> Any:
        """Lazy-load du modèle d'embedding (coûteux à charger)."""
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer

            logger.info("rag.embedder.load", model=settings.embedding_model)
            self._embedder = SentenceTransformer(settings.embedding_model)
        return self._embedder

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Génère les embeddings pour une liste de textes."""
        embedder = self._get_embedder()
        vectors = embedder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return vectors.tolist()

    # ─── Ingestion ────────────────────────────────────────────────────────────

    def chunk_text(self, text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
        """Chunking simple par fenêtre glissante.

        Pour la V2, utiliser SemanticSplitter ou SentenceSplitter de LlamaIndex.
        """
        chunk_size = chunk_size or settings.rag_chunk_size
        overlap = overlap or settings.rag_chunk_overlap
        words = text.split()
        chunks: list[str] = []
        i = 0
        step = max(1, chunk_size - overlap)
        while i < len(words):
            chunks.append(" ".join(words[i : i + chunk_size]))
            i += step
        return chunks

    def ingest_documents(self, documents: list[RagDocument]) -> int:
        """Indexe une liste de documents (avec chunking automatique)."""
        all_chunks: list[str] = []
        all_metadatas: list[dict] = []
        all_ids: list[str] = []

        for doc in documents:
            chunks = self.chunk_text(doc.content)
            base_id = doc.doc_id or doc.metadata.get("source", "doc")
            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_metadatas.append({**doc.metadata, "chunk_index": i})
                all_ids.append(f"{base_id}::chunk{i}")

        if not all_chunks:
            return 0

        logger.info("rag.ingest", documents=len(documents), chunks=len(all_chunks))
        embeddings = self.embed(all_chunks)
        self.collection.upsert(
            ids=all_ids,
            documents=all_chunks,
            embeddings=embeddings,
            metadatas=all_metadatas,
        )
        return len(all_chunks)

    def ingest_pdf(self, pdf_path: str | Path, source: str | None = None) -> int:
        """Indexe un PDF (utilise pypdf pour extraction)."""
        from pypdf import PdfReader

        path = Path(pdf_path)
        reader = PdfReader(str(path))
        full_text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        doc = RagDocument(
            content=full_text,
            metadata={
                "source": source or path.name,
                "type": "pdf",
                "pages": len(reader.pages),
            },
            doc_id=path.stem,
        )
        return self.ingest_documents([doc])

    # ─── Retrieval ────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int | None = None,
        filter_metadata: dict | None = None,
    ) -> list[RagResult]:
        """Recherche sémantique avec filtre metadata optionnel."""
        top_k = top_k or settings.rag_top_k
        query_embedding = self.embed([query])[0]
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata,
        )
        results: list[RagResult] = []
        if not result["documents"]:
            return results
        for doc, meta, dist in zip(
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
            strict=True,
        ):
            results.append(
                RagResult(
                    content=doc,
                    metadata=meta or {},
                    score=1.0 - dist,  # cosine distance → similarité
                    source=(meta or {}).get("source", "unknown"),
                )
            )
        return results

    def stats(self) -> dict[str, Any]:
        """Statistiques de la collection."""
        return {
            "collection": self.COLLECTION_NAME,
            "count": self.collection.count(),
            "persist_dir": str(self.persist_dir),
            "embedding_model": settings.embedding_model,
        }
