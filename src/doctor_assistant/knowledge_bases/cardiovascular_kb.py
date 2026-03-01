"""
Cardiovascular Knowledge Base Module for Doctor Assistant Multi-Agent System.

Provides RAG (Retrieval-Augmented Generation) capabilities for the
CardiovascularDiagnosis agent using FAISS vector similarity search.

Source: "Heart Disease Diagnosis and Therapy" PDF
Vector Store: FAISS (Facebook AI Similarity Search)
"""

from functools import lru_cache
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import get_embeddings


# =============================================================================
# PATH CONFIGURATION
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # Project root
DATA_DIR = BASE_DIR / "data" / "knowledge_bases"
VECTORSTORE_DIR = DATA_DIR / "vectorstores" / "cardiovascular"
PDF_PATH = DATA_DIR / "Heart Disease Diagnosis and Therapy.pdf"


# =============================================================================
# VECTORSTORE CREATION
# =============================================================================

def create_vectorstore() -> FAISS:
    """
    Create FAISS vectorstore from the cardiology PDF.
    
    Pipeline:
    1. Load PDF pages as documents
    2. Split into overlapping chunks for better context
    3. Generate embeddings using HuggingFace model
    4. Build FAISS index and save to disk
    
    Returns:
        FAISS vectorstore ready for similarity search.
    """
    # Step 1: Load PDF document
    print(f"📄 Loading PDF: {PDF_PATH}")
    loader = PyPDFLoader(str(PDF_PATH))
    documents = loader.load()
    print(f"   Loaded {len(documents)} pages")

    # Step 2: Split into chunks with overlap for context continuity
    print("✂️  Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,      # Characters per chunk
        chunk_overlap=200,    # Overlap to preserve context across chunks
        separators=["\n\n", "\n", ". ", " ", ""]  # Split priority order
    )
    chunks = splitter.split_documents(documents)
    print(f"   Created {len(chunks)} chunks")

    # Step 3: Generate embeddings and build FAISS index
    print("🧠 Creating embeddings...")
    embeddings = get_embeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)

    # Step 4: Persist to disk for reuse
    print(f"💾 Saving vectorstore to: {VECTORSTORE_DIR}")
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(VECTORSTORE_DIR))

    print("✅ Vectorstore created successfully!")
    return vectorstore


# =============================================================================
# VECTORSTORE LOADING
# =============================================================================

def load_vectorstore() -> FAISS:
    """
    Load existing FAISS vectorstore from disk.
    
    Note: allow_dangerous_deserialization=True is required for FAISS
    pickle loading. Only use with trusted local files.
    
    Returns:
        FAISS vectorstore loaded from VECTORSTORE_DIR.
    """
    embeddings = get_embeddings()
    return FAISS.load_local(
        str(VECTORSTORE_DIR),
        embeddings,
        allow_dangerous_deserialization=True,  # Required for pickle loading
    )


@lru_cache(maxsize=1)
def get_vectorstore() -> FAISS:
    """
    Get vectorstore with singleton caching.
    
    Creates vectorstore if it doesn't exist, otherwise loads from disk.
    Cached to avoid reloading on every agent invocation.
    
    Returns:
        Cached FAISS vectorstore instance.
    """
    if not VECTORSTORE_DIR.exists():
        print("⚠️  Vectorstore not found. Creating...")
        return create_vectorstore()
    print("📂 Loading existing vectorstore...")
    return load_vectorstore()


# =============================================================================
# RETRIEVER INTERFACE
# =============================================================================

def get_retriever(k: int = 4):
    """
    Get a retriever for the CardiovascularDiagnosis agent.
    
    Used by the agent to fetch relevant medical context
    before generating diagnosis responses.
    
    Args:
        k: Number of similar documents to retrieve (default: 4).
    
    Returns:
        LangChain retriever configured for top-k similarity search.
    """
    return get_vectorstore().as_retriever(search_kwargs={"k": k})


# =============================================================================
# MODULE TEST (run directly to verify RAG pipeline)
# =============================================================================

if __name__ == "__main__":
    # Initialize retriever
    retriever = get_retriever()

    # Test query
    query = "What are the symptoms of heart failure?"
    docs = retriever.invoke(query)

    # Display results
    print(f"\n🔍 Query: {query}\n")
    for i, doc in enumerate(docs, 1):
        print(f"--- Result {i} ---")
        print(doc.page_content[:300] + "...")
        print()