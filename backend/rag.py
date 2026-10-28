import os
import pymupdf as fitz
import docx
import chromadb
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

_embedding_model = None
_chroma_client = None

CHROMA_PATH = "vector_store"


def get_embedding_model():
    """Loads the embedding model once and reuses it (it's slow to load)."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _chroma_client


def extract_text(file_path: str) -> str:
    """Module 2: extract raw text from PDF, DOCX, or TXT."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        text = ""
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
        doc.close()
        return text

    elif ext == ".docx":
        d = docx.Document(file_path)
        return "\n".join(p.text for p in d.paragraphs)

    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    else:
        raise ValueError(f"Unsupported file type: {ext}")


def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """Module 2: split long text into overlapping chunks for embedding."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_text(text)


def process_document(interview_id: int, file_path: str, doc_type: str) -> int:
    """
    Module 2/3: full pipeline for one file.
    doc_type should be 'jd' or 'syllabus'.
    Returns number of chunks stored.
    """
    text = extract_text(file_path)
    if not text.strip():
        return 0

    chunks = chunk_text(text)
    model = get_embedding_model()
    embeddings = model.encode(chunks).tolist()

    client = get_chroma_client()
    collection = client.get_or_create_collection(name=f"interview_{interview_id}")

    ids = [f"{doc_type}_{i}" for i in range(len(chunks))]
    metadatas = [{"doc_type": doc_type, "chunk_index": i} for i in range(len(chunks))]

    collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
    return len(chunks)


def query_knowledge_base(interview_id: int, query_text: str, n_results: int = 5) -> list[str]:
    """
    Module 4 will use this: given a topic/question prompt, retrieve the most
    relevant chunks from this interview's JD/syllabus knowledge base.
    """
    client = get_chroma_client()
    try:
        collection = client.get_collection(name=f"interview_{interview_id}")
    except Exception:
        return []

    model = get_embedding_model()
    query_embedding = model.encode([query_text]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=n_results)
    return results.get("documents", [[]])[0]