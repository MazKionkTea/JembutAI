# AI-Agent - RAG Implementation

Implementasi **RAG (Retrieval-Augmented Generation)** menggunakan **llama.cpp** dan **ChromaDB**.

## 📋 Deskripsi

Proyek ini adalah sistem RAG lengkap dengan komponen:
- **Embedder**: Embedding model menggunakan llama.cpp (nomic-embed-text-v2-moe)
- **Indexer**: Indexing dokumen ke ChromaDB
- **Retriever**: Similarity search untuk retrieval
- **Context Builder**: Formatting context dengan referensi
- **Prompt Builder**: Template prompt dengan system instruction
- **Guardrails**: Input/output validation dan prompt injection detection
- **Threat Detector**: Advanced threat analysis dengan risk scoring

## 📁 Struktur Folder

```
/workspace/
├── rag/                          # Package RAG
│   ├── __init__.py               # Package initialization
│   ├── embedder.py               # Embedding dengan llama.cpp
│   ├── indexer.py                # Indexing ke ChromaDB
│   ├── retriever.py              # Similarity search
│   ├── context_builder.py        # Context formatting
│   ├── prompt_builder.py         # Prompt templating
│   ├── guardrails.py             # Input/output validation
│   ├── threat_detector.py        # Threat analysis
│   └── rag_index.py              # Script CLI untuk indexing
├── documents/                    # Folder untuk dokumen yang akan diindex
├── chroma_db/                    # ChromaDB storage
├── models/                       # Model GGUF
└── README.md                     # Dokumentasi ini
```

## 🚀 Instalasi

### Requirements

```bash
pip install llama-cpp-python chromadb sentence-transformers
```

### Download Model

Download model embedding ke folder `models/`:
```bash
wget https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe-GGUF/resolve/main/nomic-embed-text-v2-moe.Q5_K_M.gguf \
  -O models/nomic-embed-text-v2-moe.Q5_K_M.gguf
```

## 📖 Cara Penggunaan

### 1. Indexing Dokumen

Letakkan file dokumen (.txt, .md, .json, .csv) di folder `documents/`, lalu jalankan:

```bash
cd /workspace
python -m rag.rag_index
```

Atau dari dalam Python:

```python
from rag import Indexer, Embedder

# Inisialisasi
embedder = Embedder(model_path="models/nomic-embed-text-v2-moe.Q5_K_M.gguf")
indexer = Indexer(embedder=embedder)

# Index file
files = ["documents/file1.txt", "documents/file2.md"]
total = indexer.add_from_files(files)
print(f"Indexed {total} chunks")
```

### 2. Query/RAG

```python
from rag import Embedder, Retriever, ContextBuilder, PromptBuilder, Guardrails

# Inisialisasi
embedder = Embedder()
retriever = Retriever()
context_builder = ContextBuilder()
prompt_builder = PromptBuilder()
guardrails = Guardrails()

# Validate input
if not guardrails.validate_question("Pertanyaan Anda?"):
    raise ValueError("Invalid question")

# Retrieve
results = retriever.retrieve("Pertanyaan Anda?", top_k=3)

# Build context
context = context_builder.build(results)

# Build prompt
prompt = prompt_builder.build("Pertanyaan Anda?", context)

# Generate response dengan llama.cpp
# ... (gunakan inference.py atau llama-server)
```

## 🔒 Security Features

### Guardrails
- Input validation (max 1000 chars)
- Output sanitization (max 3000 chars)
- Prompt injection detection (18 patterns)
- Citation validation

### Threat Detector
- Session tracking (max 20 messages)
- Risk scoring (Low/Medium/High)
- Intent detection:
  - Prompt extraction
  - Context extraction
  - Roleplay override
  - Jailbreak attempts
- User blocking mechanism

## 📊 Model Configuration

| Parameter | Value |
|-----------|-------|
| Model | nomic-embed-text-v2-moe.Q5_K_M.gguf |
| Fallback | BAAI/bge-m3 (sentence-transformers) |
| Context Window | 2048 tokens |
| GPU Layers | -1 (all layers) |
| ChromaDB | Persistent (chroma_db/) |

## 📝 Dokumentasi Lengkap

- `rag-roadmap-final.md` - Master documentation dengan detail lengkap
- `rag-roadmap7.md` - Guardrails & security details
- `rag-roadmap6.md` - Prompt engineering
- `rag-roadmap5.md` - Context building
- `rag-roadmap4.md` - Retrieval process

## ⚠️ Catatan Penting

1. **Package Structure**: Module RAG ada di folder `rag/` dengan relative imports
2. **Model Path**: Pastikan model ada di `models/` atau akan fallback ke sentence-transformers
3. **ChromaDB**: Data persistent di `chroma_db/chroma.sqlite3`
4. **Documents**: Letakkan file yang akan diindex di folder `documents/`

## 🛠️ Development

### Menjalankan Tests

```bash
python -c "from rag import Embedder, Indexer, Retriever; print('OK')"
```

### Verbose Mode

Semua module support `verbose=True` untuk debugging:

```python
embedder = Embedder(verbose=True)
indexer = Indexer(verbose=True)
```

## 📄 License

[Your License Here]
