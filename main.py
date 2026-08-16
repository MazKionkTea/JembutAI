# main.py
"""
AI Assistant - Main Entry Point
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from konfigurasi.konfigurasi import konfigurasi
from llm.loader import LLMLoader
from llm.inference import InferenceEngine
from llm.prompt import PromptTemplates
from agen.agen import AgentAI
from agen.konteks import PengelolaKonteks
from agen.memori import PengelolaMemori
from agen.perencana import Perencana
from agen.eksekutor import Eksekutor
from mcp.filesystem_server import FileSystemServer
from mcp.sqlite_server import SQLiteServer
from mcp.api_server import APIServer
from mcp.launcher import MCPLauncher
from tools.files import FileTools
from tools.sqlite import SQLiteTools
from tools.shell import ShellTools


class AIAssistant:
    def __init__(self):
        print("=" * 60)
        print("🤖 AI ASSISTANT - Personal AI Agent")
        print("=" * 60)
        print(f"\n📋 Model: {config.MODEL_PATH}")
        print(f"   Database: {config.DB_PATH}\n")
        
        self.llm = None
        self.agent = None
        self.mcp = None
        self.is_running = False
        self.embedder = None
        self.indexer = None
        self.retriever = None
        self.context_builder = None
        self.prompt_builder = None
        self.threat_detector = None
        
        self._init_components()
    
    def _init_components(self):
        print("🔧 Inisialisasi komponen...")
        
        # 1. LLM
        print("   ├─ LLM Engine...", end=" ", flush=True)
        self._init_llm()
        print("✓" if self.llm else "✗")
        
        # 2. MCP
        print("   ├─ MCP Servers...", end=" ", flush=True)
        self._init_mcp()
        print("✓")
        
        # 3. RAG
        print("   ├─ RAG Components...", end=" ", flush=True)
        self._init_rag()
        print("✓")
        
        # 4. Agent
        print("   └─ AI Agent...", end=" ", flush=True)
        self._init_agent()
        print("✓")
        
        print("\n✅ Siap!\n")
    
    def _init_llm(self):
        try:
            if not Path(config.MODEL_PATH).exists():
                print(f"⚠️ Model tidak ada: {config.MODEL_PATH}")
                self.llm = None
                return
            
            loader = LLMLoader(
                model_path=config.MODEL_PATH,
                n_ctx=config.N_CTX,
                n_gpu_layers=config.N_GPU_LAYERS,
                n_threads=config.N_THREADS,
                verbose=config.AGENT_VERBOSE
            )
            
            loader.load()
            prompts = PromptTemplates()
            
            self.llm = InferenceEngine(
                loader=loader,
                prompt_templates=prompts,
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
                top_p=config.TOP_P,
                top_k=config.TOP_K,
                repeat_penalty=config.REPEAT_PENALTY,
                verbose=config.AGENT_VERBOSE
            )
            
        except Exception as e:
            print(f"⚠️ {str(e)[:50]}...")
            self.llm = None
    
    def _init_mcp(self):
        self.mcp = MCPLauncher(verbose=config.AGENT_VERBOSE)
        
        fs_server = FileSystemServer(
            base_path=config.FS_BASE_PATH,
            allow_write=config.FS_ALLOW_WRITE,
            allow_delete=config.FS_ALLOW_DELETE,
            max_file_size=config.FS_MAX_FILE_SIZE,
            verbose=config.AGENT_VERBOSE
        )
        self.mcp.register_server('filesystem', fs_server)
        
        db_server = SQLiteServer(
            db_path=config.DB_PATH,
            verbose=config.AGENT_VERBOSE
        )
        self.mcp.register_server('database', db_server)
        
        api_server = APIServer(
            weather_api_key=config.WEATHER_API_KEY,
            news_api_key=config.NEWS_API_KEY,
            currency_api_key=config.CURRENCY_API_KEY,
            github_token=config.GITHUB_TOKEN,
            timeout=config.API_TIMEOUT,
            verbose=config.AGENT_VERBOSE
        )
        self.mcp.register_server('api', api_server)
        
        if config.MCP_AUTO_START:
            self.mcp.start_all()
    
    def _init_rag(self):
        try:
            from rag import Embedder, Indexer, Retriever, ContextBuilder, PromptBuilder, ThreatDetector
            
            # Cek model embedding
            embed_model_path = config.MODELS_DIR / "nomic-embed-text-v2-moe.Q5_K_M.gguf"

            # Embedder - auto fallback ke sentence-transformers
            self.embedder = Embedder(
                model_path=str(embed_model_path) if embed_model_path.exists() else "",
                n_ctx=5120,
                n_gpu_layers=0,
                verbose=config.AGENT_VERBOSE
            )
            
            # Indexer
            self.indexer = Indexer(
                chroma_path="chroma_db",
                collection_name="knowledge",
                embedder=self.embedder,
                verbose=config.AGENT_VERBOSE
            )
            
            # Retriever
            self.retriever = Retriever(
                chroma_client=self.indexer.client,
                collection_name="knowledge",
                embedder=self.embedder,
                verbose=config.AGENT_VERBOSE
            )
            
            # Context Builder
            self.context_builder = ContextBuilder(
                max_chars=4000,
                include_sources=True,
                include_similarity=False,
                verbose=config.AGENT_VERBOSE
            )
            
            # Prompt Builder
            self.prompt_builder = PromptBuilder(verbose=config.AGENT_VERBOSE)

            # Threat Detector
            self.threat_detector = ThreatDetector(verbose=config.AGENT_VERBOSE)

            print("ok", end=" ")
            
        except ImportError as e:
            print(f"⚠️ RAG module error: {e}")
            self.embedder = None
            self.indexer = None
            self.retriever = None
            self.context_builder = None
            self.prompt_builder = None
            self.threat_detector = None
        except Exception as e:
            print(f"⚠️ {str(e)[:30]}...")
            self.embedder = None
            self.indexer = None
            self.retriever = None
            self.context_builder = None
            self.prompt_builder = None
            self.threat_detector = None
    
    def _init_agent(self):
        memory = MemoryManager(
            db_path=config.DB_PATH,
            max_history=config.MAX_HISTORY,
            verbose=config.AGENT_VERBOSE
        )
        
        context = ContextManager(
            max_context_length=config.MAX_CONTEXT_LENGTH,
            verbose=config.AGENT_VERBOSE
        )
        
        planner = Planner(
            context_manager=context,
            use_llm=config.PLANNER_USE_LLM and self.llm is not None,
            verbose=config.AGENT_VERBOSE
        )
        if self.llm:
            planner.set_llm(self.llm)
        
        executor = Executor(
            context_manager=context,
            verbose=config.AGENT_VERBOSE
        )
        
        for name, server in self.mcp.get_all_servers().items():
            executor.register_mcp_server(name, server)
        
        self._register_tools(executor, planner)
        
        self.agent = AIAgent(
            memory_manager=memory,
            context_manager=context,
            planner=planner,
            executor=executor,
            llm=self.llm,
            verbose=config.AGENT_VERBOSE
        )
        
        self.agent.start_session()
    
    def _register_tools(self, executor, planner):
        fs_server = self.mcp.get_server('filesystem')
        if fs_server:
            file_tools = FileTools(fs_server, verbose=config.AGENT_VERBOSE)
            executor.register_tool_handler('read_file', file_tools.read)
            executor.register_tool_handler('write_file', file_tools.write)
            executor.register_tool_handler('list_files', file_tools.list)
            executor.register_tool_handler('search_files', file_tools.search)
            executor.register_tool_handler('count_pdf', file_tools.count_pdf)
            
            planner.add_tool('read_file', patterns=[r'baca\s+file'], keywords=['baca', 'file'])
            planner.add_tool('write_file', patterns=[r'tulis\s+file'], keywords=['tulis', 'file'])
            planner.add_tool('list_files', patterns=[r'list\s+file'], keywords=['list', 'daftar'])
            planner.add_tool('count_pdf', patterns=[r'hitung\s+pdf'], keywords=['pdf', 'hitung'])
        
        db_server = self.mcp.get_server('database')
        if db_server:
            sqlite_tools = SQLiteTools(db_server, verbose=config.AGENT_VERBOSE)
            executor.register_tool_handler('add_note', sqlite_tools.add_note)
            executor.register_tool_handler('search_note', sqlite_tools.search_note)
            executor.register_tool_handler('save_memory', sqlite_tools.save_memory)
            executor.register_tool_handler('load_memory', sqlite_tools.load_memory)
            
            planner.add_tool('add_note', patterns=[r'tambah\s+note'], keywords=['note', 'catatan'])
            planner.add_tool('search_note', patterns=[r'cari\s+note'], keywords=['cari', 'note'])
            planner.add_tool('save_memory', patterns=[r'ingat\s+'], keywords=['ingat', 'memori'])
        
        api_server = self.mcp.get_server('api')
        if api_server:
            weather_tools = WeatherTools(api_server, verbose=config.AGENT_VERBOSE)
            executor.register_tool_handler('weather', weather_tools.current)
            planner.add_tool('weather', patterns=[r'cuaca\s+'], keywords=['cuaca', 'suhu'])
            
            executor.register_tool_handler('wikipedia', api_server.wikipedia)
            planner.add_tool('wikipedia', patterns=[r'wikipedia\s+'], keywords=['wikipedia'])
        
        shell_tools = ShellTools(
            allowed_commands=config.SHELL_ALLOWED_COMMANDS,
            blocklist=config.SHELL_BLOCKLIST,
            timeout=config.SHELL_TIMEOUT,
            verbose=config.AGENT_VERBOSE
        )
        executor.register_tool_handler('shell', shell_tools.execute)
        planner.add_tool('shell', patterns=[r'jalankan\s+perintah'], keywords=['terminal', 'command'])
    
    def run(self):
        self.is_running = True
        print("=" * 60)
        print("💬 AI Assistant siap! Ketik 'exit' untuk keluar.")
        print("📌 Ketik 'skill' untuk aktifkan tool, 'chat' untuk nonaktifkan.")
        print("=" * 60)
        print()
        
        while self.is_running:
            try:
                user_input = input("\n🧑 Anda: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'keluar']:
                    print("\n👋 Sampai jumpa!")
                    break
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['skill', 'tools']:
                    if self.agent:
                        active = self.agent.toggle_planner(True)
                        print(f"\n🔧 Mode tool: {'AKTIF' if active else 'NONAKTIF'}")
                    continue
                
                if user_input.lower() in ['chat', 'normal']:
                    if self.agent:
                        active = self.agent.toggle_planner(False)
                        print(f"\n💬 Mode chat: {'AKTIF' if not active else 'NONAKTIF'}")
                    continue
                                
                if self.agent and self.llm:
                    result = self.agent.process(user_input, stream=True)
                    
                    if not result.get('success'):
                        print(f"Error: {result.get('error', 'Unknown error')}")
                    if result.get('tool_used'):
                        print(f"\n   🔧 Tool: {result['tool_used']}")
                    if result.get('tokens'):
                        print(f"   📊 Tokens: {result['tokens']}")
                    if result.get('total_latency'):
                        print(f"   ⏱️  Latency: {result['total_latency']:.2f}s")
                else:
                    print("Mode fallback: LLM tidak tersedia.")
                    print(f"Cek: {config.MODEL_PATH}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Sampai jumpa!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
    
    def shutdown(self):
        print("\n🛑 Shutting down...")
        self.is_running = False
        if self.mcp:
            try:
                self.mcp.stop_all()
            except:
                pass
        if self.llm:
            try:
                self.llm.loader.unload()
            except:
                pass
        print("✅ Shutdown complete.")


def main():
    assistant = None
    try:
        assistant = AIAssistant()
        assistant.run()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if assistant:
            try:
                assistant.shutdown()
            except:
                pass


if __name__ == "__main__":
    main()
