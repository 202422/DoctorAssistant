"""Cardiovascular Knowledge Base using FAISS."""

from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import get_embeddings  # ✅ Centralized config


# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # project root
DATA_DIR = BASE_DIR / "data" / "knowledge_bases"
VECTORSTORE_DIR = DATA_DIR / "vectorstores" / "cardiovascular"
PDF_PATH = DATA_DIR / "Heart Disease Diagnosis and Therapy.pdf"


def create_vectorstore() -> FAISS:
    """Create and save FAISS vectorstore from PDF."""
    
    # 1. Load PDF
    print(f"📄 Loading PDF: {PDF_PATH}")
    loader = PyPDFLoader(str(PDF_PATH))
    documents = loader.load()
    print(f"   Loaded {len(documents)} pages")
    
    # 2. Split into chunks
    print("✂️  Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_documents(documents)
    print(f"   Created {len(chunks)} chunks")
    
    # 3. Create embeddings and vectorstore
    print("🧠 Creating embeddings...")
    embeddings = get_embeddings()  # ✅ From config
    vectorstore = FAISS.from_documents(chunks, embeddings)
    
    # 4. Save locally
    print(f"💾 Saving vectorstore to: {VECTORSTORE_DIR}")
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(VECTORSTORE_DIR))
    
    print("✅ Vectorstore created successfully!")
    return vectorstore


def load_vectorstore() -> FAISS:
    """Load existing FAISS vectorstore."""
    
    embeddings = get_embeddings()  # ✅ From config
    vectorstore = FAISS.load_local(
        str(VECTORSTORE_DIR), 
        embeddings,
        allow_dangerous_deserialization=True
    )
    return vectorstore


def get_retriever(k: int = 4):
    """Get retriever - creates vectorstore if it doesn't exist."""
    
    if not VECTORSTORE_DIR.exists():
        print("⚠️  Vectorstore not found. Creating...")
        vectorstore = create_vectorstore()
    else:
        print("📂 Loading existing vectorstore...")
        vectorstore = load_vectorstore()
    
    return vectorstore.as_retriever(search_kwargs={"k": k})


# Quick test
if __name__ == "__main__":
    retriever = get_retriever()
    
    # Test query
    query = "What are the symptoms of heart failure?"
    docs = retriever.invoke(query)
    
    print(f"\n🔍 Query: {query}\n")
    for i, doc in enumerate(docs, 1):
        print(f"--- Result {i} ---")
        print(doc.page_content[:300] + "...")
        print()