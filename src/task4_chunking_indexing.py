"""
Task 4 — Chunking & Indexing vào Vector Store.

Hướng dẫn:
    1. Đọc toàn bộ markdown files từ data/standardized/
    2. Chọn 1 chunking strategy (giải thích lý do)
    3. Chọn 1 embedding model (giải thích lý do)
    4. Index vào vector store (ChromaDB khuyến cáo — đơn giản, local, không cần Docker)

Chunking options (langchain-text-splitters):
    - RecursiveCharacterTextSplitter: an toàn, phổ biến
    - MarkdownHeaderTextSplitter: tốt cho file có heading
    - SemanticChunker: dùng embedding để tách (nâng cao)

Embedding model options:
    - sentence-transformers/all-MiniLM-L6-v2 (384 dim, nhẹ)
    - BAAI/bge-m3 (1024 dim, multilingual, tốt cho cả tiếng Việt lẫn tiếng Anh)
    - OpenAI text-embedding-3-small (1536 dim, API)

Vector store options:
    - ChromaDB (khuyến cáo: đơn giản, local persistent, không cần Docker)
    - Weaviate (hỗ trợ hybrid search built-in, cần Docker/Cloud)
    - FAISS (chỉ dense search)

Cài đặt:
    pip install langchain-text-splitters chromadb openai

Lưu ý quan trọng: nếu sau này đổi corpus (đổi chủ đề, thêm/bớt tài liệu), phải XÓA
chroma_db/ cũ trước khi reindex — nếu không, chunk cũ và mới sẽ tồn tại lẫn lộn
trong cùng collection, retrieval sẽ trả về kết quả rác từ dữ liệu cũ.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
LEGAL_MANIFEST_PATH = Path(__file__).parent.parent / "data" / "landing" / "legal" / "manifest.json"


# =============================================================================
# CONFIGURATION
# =============================================================================

# Chunking: RecursiveCharacterTextSplitter — an toàn, tôn trọng ranh giới đoạn/câu
# thay vì cắt cứng theo số ký tự (tránh cắt đôi câu quan trọng ở ranh giới chunk).
CHUNK_SIZE = 800        # Đủ lớn để giữ trọn ngữ cảnh 1 điều khoản/mục chính sách,
                         # đủ nhỏ để không làm loãng thông tin khi đưa vào LLM.
CHUNK_OVERLAP = 100      # ~12.5% chunk_size — đảm bảo câu văn ở ranh giới 2 chunk
                         # liên tiếp không bị cắt mất ngữ cảnh phía trước/sau.
CHUNKING_METHOD = "recursive"  # "recursive" | "markdown_header" | "semantic"

# Embedding: OpenAI text-embedding-3-small (API) — dùng chung API key với Task 10,
# không cần tải/chạy model local (~2GB), tốc độ ổn định, hỗ trợ đa ngôn ngữ tốt.
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# Vector store: ChromaDB — local, persistent, không cần Docker, hỗ trợ Cosine
# Similarity Search sẵn cho Task 5.
VECTOR_STORE = "chromadb"  # "chromadb" | "weaviate" | "faiss"
COLLECTION_NAME = "ecommerce_support_docs"


# =============================================================================
# IMPLEMENTATION
# =============================================================================

def _load_customer_role_map() -> dict[str, str]:
    """
    Đọc manifest.json (sinh ra ở Task 1) để lấy customer_role (buyer/seller/both)
    theo tên file gốc. Map key đổi đuôi .pdf/.docx -> .md để khớp với file đã convert.
    """
    if not LEGAL_MANIFEST_PATH.exists():
        return {}
    manifest = json.loads(LEGAL_MANIFEST_PATH.read_text(encoding="utf-8"))
    return {
        f"{Path(filename).stem}.md": meta["customer_role"]
        for filename, meta in manifest.items()
    }


def load_documents() -> list[dict]:
    """
    Đọc toàn bộ markdown files từ data/standardized/.

    Returns:
        List of {'content': str, 'metadata': {'source': str, 'type': str, 'customer_role': str}}
    """
    role_map = _load_customer_role_map()

    documents = []
    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8").strip()
        if not content:
            continue

        doc_type = "legal" if "legal" in md_file.parts else "news"
        # Văn bản pháp lý: lấy customer_role từ manifest Task 1.
        # Bài viết hỗ trợ khách hàng (news): mặc định "buyer" — các chủ đề
        # (theo dõi đơn hàng, đổi phương thức thanh toán...) đều hướng tới người mua.
        customer_role = role_map.get(md_file.name, "buyer" if doc_type == "news" else "both")

        documents.append({
            "content": content,
            "metadata": {
                "source": md_file.name,
                "type": doc_type,
                "customer_role": customer_role,
            },
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """
    Chunk documents theo strategy đã chọn (RecursiveCharacterTextSplitter).

    Returns:
        List of {'content': str, 'metadata': dict} — mỗi item là 1 chunk
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for doc in documents:
        splits = splitter.split_text(doc["content"])
        for i, chunk_text in enumerate(splits):
            chunks.append({
                "content": chunk_text,
                "metadata": {**doc["metadata"], "chunk_index": i},
            })
    return chunks


_openai_client = None  # cache singleton
_EMBED_BATCH_SIZE = 100


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Cần OPENAI_API_KEY trong .env để dùng OpenAI Embeddings API "
                f"(model={EMBEDDING_MODEL})."
            )
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed danh sách text bằng OpenAI Embeddings API (batch để tránh vượt giới hạn request)."""
    if not texts:
        return []
    client = _get_openai_client()
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[i : i + _EMBED_BATCH_SIZE]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        embeddings.extend(item.embedding for item in resp.data)
    return embeddings


def get_collection():
    """Trả về ChromaDB collection đã index ở Task 4 (dùng chung cho Task 5/9)."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Embed toàn bộ chunks bằng OpenAI Embeddings API (EMBEDDING_MODEL).

    Returns:
        Mỗi chunk dict được thêm key 'embedding': list[float]
    """
    texts = [c["content"] for c in chunks]
    embeddings = embed_texts(texts)
    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb
    return chunks


def index_to_vectorstore(chunks: list[dict]):
    """
    Lưu chunks vào ChromaDB (persistent, local, tại CHROMA_DIR).
    """
    collection = get_collection()

    ids = [
        f"{c['metadata']['type']}_{c['metadata']['source']}_chunk_{c['metadata']['chunk_index']}"
        for c in chunks
    ]
    collection.upsert(
        ids=ids,
        documents=[c["content"] for c in chunks],
        embeddings=[c["embedding"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )


def run_pipeline():
    """Chạy toàn bộ pipeline: load → chunk → embed → index."""
    print("=" * 50)
    print("Task 4: Chunking & Indexing")
    print(f"  Chunking: {CHUNKING_METHOD} (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"  Embedding: {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    print(f"  Vector Store: {VECTOR_STORE}")
    print("=" * 50)

    docs = load_documents()
    print(f"\n✓ Loaded {len(docs)} documents")
    if not docs:
        print("⚠ Không có document nào trong data/standardized/ — hãy chạy Task 3 trước.")
        return

    chunks = chunk_documents(docs)
    print(f"✓ Created {len(chunks)} chunks")

    chunks = embed_chunks(chunks)
    print(f"✓ Embedded {len(chunks)} chunks")

    index_to_vectorstore(chunks)
    print(f"✓ Indexed to vector store tại {CHROMA_DIR}")


if __name__ == "__main__":
    run_pipeline()
