# Arsitektur & Workflow Sistem AI Agent dengan RAG

## 1. Overview Arsitektur

Proyek ini adalah sistem **AI Agent** yang mengintegrasikan kemampuan **RAG (Retrieval-Augmented Generation)** dengan arsitektur modular berbasis komponen agent (Planner, Memory, Executor).

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                │
│                    (web/app.py - Flask/FastAPI)                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                           MAIN ORCHESTRATOR                             │
│                         (main.py - Entry Point)                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                            AGENT LAYER                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │   Planner    │  │    Memory    │  │   Executor   │  │   Context   │ │
│  │ (planner.py) │  │ (memory.py)  │  │(executor.py) │  │ (context.py)│ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘ │
│                              ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      Agent Core (agent.py)                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                          RAG PIPELINE                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  ┌────────────┐  │
│  │  Indexer    │  │   Embedder   │  │   Retriever   │  │  Guardrails│  │
│  │(indexer.py) │  │(embedder.py) │  │ (retriever.py)│  │(guardrails)│  │
│  └─────────────┘  └──────────────┘  └───────────────┘  └────────────┘  │
│                                                                          │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────────────────────┐  │
│  │Context Builder│  │ Prompt Builder│  │     Threat Detector         │  │
│  │(context_bld.py│  │(prompt_bld.py)│  │   (threat_detector.py)      │  │
│  └───────────────┘  └───────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                          LLM LAYER                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │    Loader    │  │  Inference   │  │    Prompt    │                  │
│  │ (loader.py)  │  │(inference.py)│  │ (prompt.py)  │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                        MCP LAYER (Model Context Protocol)               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  API Server      │  │ Filesystem Server│  │   SQLite Server      │  │
│  │ (api_server.py)  │  │(filesystem_srv.py│  │  (sqlite_server.py)  │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
│                              ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    MCP Launcher (launcher.py)                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         TOOLS LAYER                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │    Files     │  │    Shell     │  │   SQLite     │                  │
│  │ (files.py)   │  │ (shell.py)   │  │ (sqlite.py)  │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      DATA & STORAGE LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  ChromaDB    │  │   SQLite DB  │  │    Cache     │  │  Documents │  │
│  │(chroma_db/)  │  │(database/)   │  │   (cache/)   │  │(documents/)│  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │    Models    │  │     Doc      │  │    Logs      │                  │
│  │  (models/)   │  │   (doc/)     │  │   (logs/)    │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Komponen Utama

### 2.1 Agent Layer (`/agent`)

| File | Fungsi | Deskripsi |
|------|--------|-----------|
| `agent.py` | Core Agent | Mengkoordinasikan Planner, Memory, dan Executor untuk menyelesaikan tugas kompleks |
| `planner.py` | Task Planner | Memecah tujuan user menjadi langkah-langkah terstruktur |
| `memory.py` | Memory Management | Menyimpan konteks percakapan, history, dan knowledge jangka pendek/panjang |
| `executor.py` | Task Executor | Menjalankan tool/action berdasarkan rencana dari planner |
| `context.py` | Context Manager | Mengelola konteks aktif selama sesi interaksi |

### 2.2 RAG Pipeline (`/rag`)

| File | Fungsi | Deskripsi |
|------|--------|-----------|
| `indexer.py` | Document Indexing | Mengelola proses indexing dokumen ke ChromaDB |
| `embedder.py` | Text Embedding | Membuat vector embedding dari teks menggunakan model GGUF/HuggingFace |
| `retriever.py` | Similarity Search | Mencari dokumen relevan berdasarkan query embedding |
| `context_builder.py` | Context Assembly | Menyusun konteks dari hasil retrieval untuk prompt |
| `prompt_builder.py` | Prompt Construction | Membangun prompt template dengan konteks dan instruksi |
| `guardrails.py` | Safety Filter | Filter output untuk memastikan keamanan dan kesesuaian |
| `threat_detector.py` | Threat Detection | Mendeteksi prompt injection, jailbreak attempts, dan ancaman lainnya |
| `rag_index.py` | RAG Index Manager | Wrapper untuk operasi index ChromaDB |
| `__init__.py` | Package Init | Inisialisasi package rag |

### 2.3 LLM Layer (`/llm`)

| File | Fungsi | Deskripsi |
|------|--------|-----------|
| `loader.py` | Model Loader | Memuat model GGUF ke llama-cpp-python |
| `inference.py` | Model Inference | Menjalankan inferensi model untuk menghasilkan teks |
| `prompt.py` | Prompt Templates | Template prompt untuk berbagai use case |

### 2.4 MCP Layer (`/mcp`)

| File | Fungsi | Deskripsi |
|------|--------|-----------|
| `launcher.py` | MCP Launcher | Meluncurkan MCP servers |
| `api_server.py` | MCP API Server | Server MCP untuk akses API eksternal |
| `filesystem_server.py` | MCP Filesystem | Server MCP untuk operasi filesystem |
| `sqlite_server.py` | MCP SQLite | Server MCP untuk query database SQLite |
| `MCP-roadmap.md` | MCP Documentation | Dokumentasi implementasi MCP |

### 2.5 Tools Layer (`/tools`)

| File | Fungsi | Deskripsi |
|------|--------|-----------|
| `files.py` | File Operations | Tool untuk membaca/menulis file |
| `shell.py` | Shell Commands | Tool untuk menjalankan command shell |
| `sqlite.py` | Database Queries | Tool untuk query database SQLite |

### 2.6 Configuration (`/configurasi`)

| File | Fungsi | Deskripsi |
|------|--------|-----------|
| `config.py` | Configuration | Konfigurasi global aplikasi (paths, model settings, dll) |
| `server.py` | Server Config | Konfigurasi server (host, port, SSL, dll) |

### 2.7 Web Interface (`/web`)

| File/Folder | Fungsi | Deskripsi |
|-------------|--------|-----------|
| `app.py` | Web Application | Flask/FastAPI application untuk UI web |
| `templates/index.html` | Frontend HTML | Template halaman utama |
| `static/css/style.css` | Styling | CSS untuk tampilan |
| `static/js/app.js` | Frontend Logic | JavaScript untuk interaksi user |

### 2.8 Data Storage

| Folder/File | Fungsi | Deskripsi |
|-------------|--------|-----------|
| `chroma_db/chroma.sqlite3` | Vector Database | Penyimpanan embeddings untuk RAG |
| `database/assistant.db` | SQLite Database | Database untuk metadata, history, konfigurasi |
| `documents/` | Document Store | Folder untuk dokumen sumber yang akan di-index |
| `models/` | Model Storage | Folder untuk menyimpan model GGUF |
| `cache/` | Cache Storage | Cache untuk response, embeddings, atau hasil intermediate |
| `doc/` | Documentation | Dokumentasi tambahan |
| `logs/log.txt` | Logging | Log file untuk debugging dan monitoring |

---

## 3. Workflow Detail

### 3.1 Workflow Indexing (Offline Process)

```
┌─────────────────────────────────────────────────────────────────┐
│                    INDEXING WORKFLOW                            │
└─────────────────────────────────────────────────────────────────┘

Step 1: Document Loading
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  documents/  │ ──→ │  loader.py   │ ──→ │  Raw Text    │
│  (.md, .txt) │     │  (llm/)      │     │  Content     │
└──────────────┘     └──────────────┘     └──────────────┘

Step 2: Text Preprocessing & Chunking
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Raw Text    │ ──→ │  indexer.py  │ ──→ │   Chunks     │
│  Content     │     │  (rag/)      │     │  (512-1024)  │
└──────────────┘     └──────────────┘     └──────────────┘

Step 3: Embedding Generation
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Chunks     │ ──→ │  embedder.py │ ──→ │   Vectors    │
│  (Text)      │     │  (rag/)      │     │  (768-dim)   │
└──────────────┘     └──────────────┘     └──────────────┘
                          ↓
                   ┌──────────────┐
                   │  BGE-M3      │
                   │  GGUF Model  │
                   │  (models/)   │
                   └──────────────┘

Step 4: Vector Storage
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Vectors    │ ──→ │  rag_index.py│ ──→ │  ChromaDB    │
│  + Metadata  │     │  (rag/)      │     │  (chroma_db/)│
└──────────────┘     └──────────────┘     └──────────────┘

Step 5: Metadata Indexing (Optional)
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Metadata    │ ──→ │  indexer.py  │ ──→ │  assistant.db│
│  (source,    │     │  (rag/)      │     │  (database/) │
│   timestamp) │     └──────────────┘     └──────────────┘
└──────────────┘
```

**Command Execution:**
```bash
# Contoh script untuk menjalankan indexing
python -m rag.indexer --docs-dir ./documents --output-dir ./chroma_db
```

---

### 3.2 Workflow Querying (Online Process)

```
┌─────────────────────────────────────────────────────────────────┐
│                     QUERY WORKFLOW                              │
└─────────────────────────────────────────────────────────────────┘

Step 1: User Input & Validation
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│     User     │ ──→ │  web/app.py  │ ──→ │  main.py     │
│   Question   │     │  (Frontend)  │     │  (Orchestr.) │
└──────────────┘     └──────────────┘     └──────────────┘
                          ↓
                   ┌──────────────┐
                   │ threat_      │
                   │ detector.py  │ ←── Security Check
                   │ (rag/)       │
                   └──────────────┘

Step 2: Query Embedding
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Question   │ ──→ │  embedder.py │ ──→ │   Query      │
│   (Text)     │     │  (rag/)      │     │   Vector     │
└──────────────┘     └──────────────┘     └──────────────┘

Step 3: Similarity Search & Retrieval
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Query       │ ──→ │  retriever.py│ ──→ │  Top-K       │
│  Vector      │     │  (rag/)      │     │  Chunks      │
└──────────────┘     └──────────────┘     └──────────────┘
                          ↓
                   ┌──────────────┐
                   │  ChromaDB    │
                   │  (chroma_db/)│
                   └──────────────┘

Step 4: Context Building
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Top-K       │ ──→ │  context_    │ ──→ │  Structured  │
│  Chunks      │     │  builder.py  │     │  Context     │
└──────────────┘     │  (rag/)      │     └──────────────┘
                     └──────────────┘

Step 5: Agent Processing
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Structured  │ ──→ │   agent.py   │ ──→ │    Task      │
│  Context     │     │  (agent/)    │     │   Planning   │
└──────────────┘     └──────────────┘     └──────────────┘
                          ↓
              ┌───────────┼───────────┐
              ↓           ↓           ↓
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │ planner  │ │ memory   │ │ executor │
       │  .py     │ │  .py     │ │  .py     │
       └──────────┘ └──────────┘ └──────────┘

Step 6: Prompt Building
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Context +   │ ──→ │  prompt_     │ ──→ │  Final       │
│  Question +  │     │  builder.py  │     │  Prompt      │
│  Instructions│     │  (rag/)      │     │  Template    │
└──────────────┘     └──────────────┘     └──────────────┘

Step 7: LLM Inference
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Final       │ ──→ │  inference.py│ ──→ │  Raw         │
│  Prompt      │     │  (llm/)      │     │  Response    │
└──────────────┘     └──────────────┘     └──────────────┘
                          ↓
                   ┌──────────────┐
                   │  llama.cpp   │
                   │  GGUF Model  │
                   │  (models/)   │
                   └──────────────┘

Step 8: Guardrails & Output Filtering
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Raw         │ ──→ │  guardrails. │ ──→ │   Filtered   │
│  Response    │     │  py (rag/)   │     │   Response   │
└──────────────┘     └──────────────┘     └──────────────┘

Step 9: Tool Execution (If Needed)
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Requires   │ ──→ │  executor.py │ ──→ │    Tools     │
│   Tool Call  │     │  (agent/)    │     │  (/tools/)   │
└──────────────┘     └──────────────┘     └──────────────┘
                          ↓
              ┌───────────┼───────────┐
              ↓           ↓           ↓
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │ files.py │ │ shell.py │ │ sqlite.py│
       └──────────┘ └──────────┘ └──────────┘

Step 10: Response Delivery
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Filtered    │ ──→ │  web/app.py  │ ──→ │     User     │
│  Response    │     │  (Frontend)  │     │   Receives   │
└──────────────┘     └──────────────┘     └──────────────┘

Step 11: Memory Update
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Q&A Pair    │ ──→ │  memory.py   │ ──→ │  assistant.db│
│  + Context   │     │  (agent/)    │     │  (database/) │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

### 3.3 Workflow MCP Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP WORKFLOW                                 │
└─────────────────────────────────────────────────────────────────┘

Step 1: MCP Server Initialization
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   main.py    │ ──→ │  launcher.py │ ──→ │ MCP Servers  │
│  (Startup)   │     │  (mcp/)      │     │  Spawned     │
└──────────────┘     └──────────────┘     └──────────────┘
                          ↓
              ┌───────────┼───────────┐
              ↓           ↓           ↓
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │   API    │ │Filesystem│ │  SQLite  │
       │  Server  │ │  Server  │ │  Server  │
       └──────────┘ └──────────┘ └──────────┘

Step 2: Tool Request from Agent
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   executor   │ ──→ │   MCP        │ ──→ │   Target     │
│   (agent/)   │     │   Protocol   │     │   Server     │
└──────────────┘     └──────────────┘     └──────────────┘

Step 3: Tool Execution & Response
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Target     │ ──→ │   MCP        │ ──→ │   executor   │
│   Server     │     │   Response   │     │   (agent/)   │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## 4. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA FLOW                                │
└─────────────────────────────────────────────────────────────────┘

                    DOCUMENTS
                       │
                       ↓
        ┌──────────────────────────────┐
        │      INDEXING PIPELINE       │
        │  (loader → indexer → embedder│
        │       → rag_index → chroma)  │
        └──────────────────────────────┘
                       │
                       ↓
                 ┌──────────┐
                 │ ChromaDB │
                 └──────────┘
                       │
                       │
                    USER QUERY
                       │
                       ↓
        ┌──────────────────────────────┐
        │       QUERY PIPELINE         │
        │  (embedder → retriever →     │
        │   context_builder →          │
        │   prompt_builder)            │
        └──────────────────────────────┘
                       │
                       ↓
                 ┌──────────┐
                 │  Agent   │
                 │ (planner │
                 │  memory  │
                 │ executor)│
                 └──────────┘
                       │
                       ├──────────────┐
                       │              │
                       ↓              ↓
                ┌──────────┐   ┌──────────┐
                │   LLM    │   │  Tools   │
                │(inference│   │(via MCP) │
                └──────────┘   └──────────┘
                       │              │
                       │              │
                       ↓              ↓
                ┌──────────┐   ┌──────────┐
                │Guardrails│   │  Files/  │
                └──────────┘   │  Shell/  │
                       │      │  SQLite  │
                       │      └──────────┘
                       │              │
                       └──────┬───────┘
                              │
                              ↓
                       ┌──────────┐
                       │ Response │
                       │   to     │
                       │   User   │
                       └──────────┘
                              │
                              ↓
                       ┌──────────┐
                       │  Memory  │
                       │  Update  │
                       └──────────┘
```

---

## 5. Sequence Diagram (Query Flow)

```
User → Web App → Main → Agent → RAG → LLM → Tools → Database

1. User mengirim pertanyaan melalui web interface
2. Web app (app.py) menerima request dan forward ke main.py
3. Main orchestrates memanggil agent.py
4. Agent memanggil threat_detector.py untuk validasi keamanan
5. Agent memanggil embedder.py untuk membuat query embedding
6. Agent memanggil retriever.py untuk mencari dokumen relevan dari ChromaDB
7. Agent memanggil context_builder.py untuk menyusun konteks
8. Agent memanggil prompt_builder.py untuk membuat prompt final
9. Agent memanggil inference.py untuk generate response dari LLM
10. Agent memanggil guardrails.py untuk filter output
11. Jika perlu tool call, executor.py memanggil tools via MCP
12. Response dikirim kembali ke user melalui web app
13. Memory disimpan ke database untuk konteks masa depan
```

---

## 6. Konfigurasi & Environment

### 6.1 Struktur Konfigurasi (`configurasi/config.py`)

```python
# Path Configuration
BASE_DIR = "/path/to/project"
DOCUMENTS_DIR = f"{BASE_DIR}/documents"
MODELS_DIR = f"{BASE_DIR}/models"
CHROMA_DB_PATH = f"{BASE_DIR}/chroma_db"
DATABASE_PATH = f"{BASE_DIR}/database/assistant.db"
CACHE_DIR = f"{BASE_DIR}/cache"
LOGS_DIR = f"{BASE_DIR}/logs"

# Model Configuration
EMBEDDING_MODEL = "bge-m3.gguf"
LLM_MODEL = "mistral-7b-instruct-v0.3.Q4_K_M.gguf"
EMBEDDING_DIMENSION = 1024
CONTEXT_WINDOW = 4096
MAX_TOKENS = 512

# RAG Configuration
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
TOP_K_RETRIEVAL = 5
SIMILARITY_THRESHOLD = 0.7

# Server Configuration
HOST = "0.0.0.0"
PORT = 8000
DEBUG = False

# MCP Configuration
MCP_ENABLED = True
MCP_SERVERS = ["filesystem", "sqlite", "api"]
```

### 6.2 Requirements (`requirements.txt`)

```
# Vector Database
chromadb>=0.4.0

# LLM Inference
llama-cpp-python>=0.2.0

# Embedding
sentence-transformers>=2.2.0

# Web Framework
flask>=2.3.0  # atau fastapi>=0.100.0

# MCP
mcp>=1.0.0

# Utilities
python-dotenv>=1.0.0
pydantic>=2.0.0
numpy>=1.24.0
```

---

## 7. Security & Guardrails

### 7.1 Threat Detection Layers

```
Layer 1: Input Validation (threat_detector.py)
  - Detect prompt injection patterns
  - Block jailbreak attempts
  - Validate input length and format

Layer 2: Content Filtering (guardrails.py)
  - Filter harmful content in output
  - Ensure compliance with policies
  - Remove sensitive information

Layer 3: Rate Limiting (server.py)
  - Limit requests per user/session
  - Prevent abuse and DoS attacks

Layer 4: Access Control (configurasi/server.py)
  - Authentication for API endpoints
  - Authorization for tool access
```

---

## 8. Monitoring & Logging

### 8.1 Log Structure (`logs/log.txt`)

```
[TIMESTAMP] [LEVEL] [MODULE] MESSAGE
Example:
[2025-03-19 10:30:45] [INFO] [retriever] Retrieved 5 chunks with avg similarity 0.85
[2025-03-19 10:30:46] [WARNING] [threat_detector] Potential prompt injection detected
[2025-03-19 10:30:47] [ERROR] [inference] Model loading failed: out of memory
```

### 8.2 Metrics to Track

- Response time per query
- Retrieval accuracy (similarity scores)
- Token usage (input/output)
- Error rates per module
- Tool call frequency
- User session duration

---

## 9. Scalability Considerations

### 9.1 Horizontal Scaling

- **Multiple LLM Workers**: Deploy multiple inference instances behind load balancer
- **Distributed ChromaDB**: Use ChromaDB cluster for high availability
- **Caching Layer**: Implement Redis/Memcached untuk cache embeddings dan responses

### 9.2 Vertical Scaling

- **GPU Acceleration**: Offload inference ke GPU untuk performa lebih baik
- **Batch Processing**: Process multiple queries dalam batch untuk efisiensi
- **Model Quantization**: Gunakan model GGUF dengan quantization optimal (Q4_K_M, Q5_K_M)

---

## 10. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYMENT                        │
└─────────────────────────────────────────────────────────────────┘

                    ┌──────────────┐
                    │  Load        │
                    │  Balancer    │
                    │  (Nginx)     │
                    └──────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ↓               ↓               ↓
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │  Web App 1  │ │  Web App 2  │ │  Web App 3  │
   │  (Flask)    │ │  (Flask)    │ │  (Flask)    │
   └─────────────┘ └─────────────┘ └─────────────┘
          │               │               │
          └───────────────┼───────────────┘
                          │
                          ↓
                   ┌─────────────┐
                   │   Message   │
                   │    Queue    │
                   │   (Redis)   │
                   └─────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ↓               ↓               ↓
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │  Worker 1   │ │  Worker 2   │ │  Worker 3   │
   │  (Agent)    │ │  (Agent)    │ │  (Agent)    │
   └─────────────┘ └─────────────┘ └─────────────┘
          │               │               │
          └───────────────┼───────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ↓               ↓               ↓
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │  ChromaDB   │ │   SQLite    │ │    Cache    │
   │  Cluster    │ │   Master    │ │   (Redis)   │
   └─────────────┘ └─────────────┘ └─────────────┘
```

---

## 11. Best Practices

### 11.1 Code Organization
- Pisahkan concern dengan jelas (agent, rag, llm, tools, mcp)
- Gunakan dependency injection untuk testing
- Implementasi logging di setiap layer kritis

### 11.2 Performance Optimization
- Cache embeddings untuk query yang sama
- Batch processing untuk indexing dokumen besar
- Gunakan async I/O untuk operasi network-bound

### 11.3 Security
- Selalu validate input user
- Implementasi rate limiting
- Encrypt sensitive data di database
- Regular security audit untuk prompt injection vulnerabilities

### 11.4 Testing
- Unit tests untuk setiap modul
- Integration tests untuk pipeline lengkap
- Load testing untuk production readiness

---

## 12. Roadmap Pengembangan

### Phase 1: Foundation ✅
- [x] Setup struktur folder
- [x] Implementasi RAG dasar (indexer, embedder, retriever)
- [x] Integrasi llama.cpp untuk inference
- [x] Web interface dasar

### Phase 2: Agent Capabilities 🚧
- [ ] Implementasi planner untuk task decomposition
- [ ] Memory management untuk long-term context
- [ ] Executor untuk tool orchestration
- [ ] MCP integration untuk external tools

### Phase 3: Advanced Features 📋
- [ ] Multi-modal support (images, audio)
- [ ] Streaming response untuk UX lebih baik
- [ ] Advanced guardrails dengan ML-based detection
- [ ] Analytics dashboard untuk monitoring

### Phase 4: Production Ready 🎯
- [ ] Docker containerization
- [ ] Kubernetes deployment
- [ ] CI/CD pipeline
- [ ] Comprehensive testing suite
- [ ] Documentation lengkap

---

## 13. Kesimpulan

Arsitektur ini dirancang untuk **skalabilitas**, **modularitas**, dan **keamanan**. Dengan pemisahan concern yang jelas antara Agent, RAG, LLM, MCP, dan Tools, sistem dapat dengan mudah dikembangkan, di-maintain, dan di-deploy ke production.

**Keunggulan Utama:**
1. **Modular Design**: Setiap komponen dapat diganti/diupgrade tanpa mempengaruhi komponen lain
2. **Security First**: Multiple layers of protection dengan threat detection dan guardrails
3. **Flexible Tooling**: MCP memungkinkan integrasi dengan berbagai external tools
4. **Local-First**: Semua komponen dapat berjalan lokal untuk privasi data maksimal
5. **Production-Ready**: Struktur siap untuk scaling dan deployment

**Rekomendasi Selanjutnya:**
1. Implementasi unit tests untuk setiap modul
2. Setup CI/CD pipeline untuk automated testing dan deployment
3. Dokumentasi API untuk setiap endpoint
4. Performance benchmarking untuk optimasi lebih lanjut
