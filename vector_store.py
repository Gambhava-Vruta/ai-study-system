"""
vector_store.py — ChromaDB Vector Store Manager

Wraps ChromaDB operations for document storage and similarity search.
"""

from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from embeddings import get_embeddings


class VectorStoreManager:
    """
    Manages a ChromaDB vector store for document embeddings.

    Usage:
        manager = VectorStoreManager()
        manager.add_documents(docs, filename="notes.pdf")
        results = manager.similarity_search("What is AI?", k=3)
    """

    def __init__(self, embedding_model=None, chunk_size=400, chunk_overlap=40):
        """
        Initialize the vector store manager.

        Args:
            embedding_model: Custom embedding model. Uses default if None.
            chunk_size: Size of each text chunk for splitting.
            chunk_overlap: Overlap between consecutive chunks.
        """
        self.embeddings = embedding_model or get_embeddings()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.vector_db = None
        self.uploaded_docs = []

    def add_documents(self, docs: list, filename: str = "") -> dict:
        """
        Split documents into chunks and add them to the vector store.

        Args:
            docs: List of LangChain Document objects.
            filename: Name of the source file (for tracking).

        Returns:
            dict with keys: 'pages' (int), 'chunks' (int), 'filename' (str).
        """
        if not docs:
            return {"pages": 0, "chunks": 0, "filename": filename}

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        chunks = splitter.split_documents(docs)

        if self.vector_db is None:
            self.vector_db = Chroma.from_documents(chunks, self.embeddings)
        else:
            self.vector_db.add_documents(chunks)

        if filename and filename not in self.uploaded_docs:
            self.uploaded_docs.append(filename)

        return {"pages": len(docs), "chunks": len(chunks), "filename": filename}

    def similarity_search(self, query: str, k: int = 3) -> list:
        """
        Perform a similarity search against the vector store.

        Args:
            query: Search query string.
            k: Number of results to return.

        Returns:
            List of Document objects most similar to the query.
        """
        if self.vector_db is None:
            return []
        return self.vector_db.similarity_search(query, k=k)

    def get_context(self, query: str, k: int = 2, max_chars: int = 400) -> str:
        """
        Get concatenated text context from similarity search results.

        Args:
            query: Search query string.
            k: Number of documents to retrieve.
            max_chars: Max characters per document chunk.

        Returns:
            Joined text string from top-k similar documents.
        """
        docs = self.similarity_search(query, k=k)
        return "\n\n".join([d.page_content[:max_chars] for d in docs])

    def clear(self):
        """Clear all documents and reset the vector store."""
        self.vector_db = None
        self.uploaded_docs = []

    @property
    def is_loaded(self) -> bool:
        """Check if any documents have been loaded."""
        return self.vector_db is not None
