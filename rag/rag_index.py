# rag_index.py
"""
Index dokumen ke ChromaDB
"""

import sys
from pathlib import Path

# Tambahkan root workspace ke path
sys.path.insert(0, str(Path(__file__).parent))

# Import langsung dari root (karena file-file RAG ada di root workspace)
from embedder import Embedder
from indexer import Indexer


def index_documents():
    """Index semua dokumen di folder documents/"""
    print("📚 Indexing documents...")
    
    # Cek model embedding
    models_dir = Path(__file__).parent / "models"
    embed_model_path = models_dir / "nomic-embed-text-v2-moe.Q5_K_M.gguf"

    
    # Embedder
    embedder = Embedder(
        model_path=str(embed_model_path) if embed_model_path.exists() else "",
        n_ctx=512,
        n_gpu_layers=0,
        verbose=True
    )
    
    # Indexer
    indexer = Indexer(
        chroma_path="chroma_db",
        collection_name="knowledge",
        embedder=embedder,
        verbose=True
    )
    
    # Cari file di documents/
    docs_dir = Path("documents")
    if not docs_dir.exists():
        print(f"⚠️ Folder {docs_dir} tidak ditemukan")
        return
    
    files = []
    for ext in ['*.txt', '*.md', '*.json', '*.csv']:
        files.extend(docs_dir.glob(ext))
    
    if not files:
        print(f"⚠️ Tidak ada file di {docs_dir}")
        print("   Letakkan file .txt, .md, .json, atau .csv di folder documents/")
        return
    
    print(f"\n📄 Found {len(files)} files:")
    for f in files:
        print(f"   - {f.name}")
    
    # Index
    total = indexer.add_from_files([str(f) for f in files])
    
    print(f"\n✅ Indexed {total} chunks from {len(files)} files")


if __name__ == "__main__":
    index_documents()
