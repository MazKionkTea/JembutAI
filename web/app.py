# web/app.py
"""
Flask Web Interface untuk AI Assistant
"""

import sys
import json
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_cors import CORS

# Tambahkan parent path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from llm.loader import LLMLoader
from llm.inference import InferenceEngine
from llm.prompt import PromptTemplates
from agent.memory import MemoryManager
from agent.context import ContextManager
from agent.planner import Planner
from agent.executor import Executor
from agent.agent import AIAgent
from mcp.filesystem_server import FileSystemServer
from mcp.sqlite_server import SQLiteServer
from mcp.api_server import APIServer
from mcp.launcher import MCPLauncher
from tools.files import FileTools
from tools.sqlite import SQLiteTools
from tools.weather import WeatherTools
from tools.shell import ShellTools

# RAG Components
try:
    from rag import (
        Embedder, Indexer, Retriever,
        ContextBuilder, PromptBuilder,
        ThreatDetector,
        validate_question,
        build_safe_context,
        validate_answer
    )
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("[WARNING] RAG module not available")

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static'  # URL prefix untuk static files
)

# ============================================
# GLOBAL STATE
# ============================================

class WebAIAssistant:
    """Wrapper untuk AI Assistant di Web"""
    
    def __init__(self):
        self.llm = None
        self.agent = None
        self.mcp = None
        self.is_ready = False
        
        # RAG
        self.embedder = None
        self.indexer = None
        self.retriever = None
        self.context_builder = None
        self.prompt_builder = None
        self.threat_detector = None
        
        # Session
        self.current_session_id = None
        
        self._init_components()
    
    def _init_components(self):
        """Inisialisasi semua komponen"""
        print("=" * 60)
        print("🤖 Web AI Assistant - Initializing...")
        print("=" * 60)
        
        try:
            # 1. LLM
            self._init_llm()
            
            # 2. MCP
            self._init_mcp()
            
            # 3. RAG
            if RAG_AVAILABLE:
                self._init_rag()
            
            # 4. Agent
            self._init_agent()
            
            self.is_ready = True
            print("\n✅ Web AI Assistant ready!\n")
            
        except Exception as e:
            print(f"\n❌ Failed to initialize: {e}")
            import traceback
            traceback.print_exc()
    
    def _init_llm(self):
        """Inisialisasi LLM"""
        try:
            loader = LLMLoader(
                model_path=config.MODEL_PATH,
                n_ctx=config.N_CTX,
                n_gpu_layers=config.N_GPU_LAYERS,
                n_threads=config.N_THREADS,
                verbose=False
            )
            
            if not Path(config.MODEL_PATH).exists():
                print(f"⚠️  Model not found: {config.MODEL_PATH}")
                self.llm = None
                return
            
            model = loader.load()
            prompts = PromptTemplates()
            
            self.llm = InferenceEngine(
                loader=loader,
                prompt_templates=prompts,
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
                top_p=config.TOP_P,
                top_k=config.TOP_K,
                repeat_penalty=config.REPEAT_PENALTY,
                verbose=False
            )
            print("   ├─ LLM Engine: ok")
            
        except Exception as e:
            print(f"   ├─ LLM Engine: error {e}")
            self.llm = None
    
    def _init_mcp(self):
        """Inisialisasi MCP Servers"""
        try:
            self.mcp = MCPLauncher(verbose=False)
            
            # Filesystem
            fs_server = FileSystemServer(
                base_path=config.FS_BASE_PATH,
                allow_write=config.FS_ALLOW_WRITE,
                allow_delete=config.FS_ALLOW_DELETE,
                max_file_size=config.FS_MAX_FILE_SIZE,
                verbose=False
            )
            self.mcp.register_server('filesystem', fs_server)
            
            # SQLite
            db_server = SQLiteServer(
                db_path=config.DB_PATH,
                verbose=False
            )
            self.mcp.register_server('database', db_server)
            
            # API
            api_server = APIServer(
                weather_api_key=config.WEATHER_API_KEY,
                news_api_key=config.NEWS_API_KEY,
                currency_api_key=config.CURRENCY_API_KEY,
                github_token=config.GITHUB_TOKEN,
                timeout=config.API_TIMEOUT,
                verbose=False
            )
            self.mcp.register_server('api', api_server)
            
            if config.MCP_AUTO_START:
                self.mcp.start_all()
            
            print("   ├─ MCP Servers: ok")
            
        except Exception as e:
            print(f"   ├─ MCP Servers: error {e}")
    
    def _init_rag(self):
        """Inisialisasi RAG"""
        try:
            embed_model_path = config.MODELS_DIR / "nomic-embed-text-v2-moe.Q5_K_M.gguf"
            
            if embed_model_path.exists():
                self.embedder = Embedder(
                    model_path=str(embed_model_path),
                    n_ctx=512,
                    n_gpu_layers=-1,
                    verbose=False
                )
            else:
                self.embedder = Embedder(
                    model_path="",
                    verbose=False
                )
            
            self.indexer = Indexer(
                chroma_path="chroma_db",
                collection_name="knowledge",
                embedder=self.embedder,
                verbose=False
            )
            
            self.retriever = Retriever(
                chroma_client=self.indexer.client,
                collection_name="knowledge",
                embedder=self.embedder,
                verbose=False
            )
            
            self.context_builder = ContextBuilder(
                max_chars=4000,
                include_sources=True,
                verbose=False
            )
            
            self.prompt_builder = PromptBuilder(verbose=False)
            self.threat_detector = ThreatDetector(verbose=False)
            
            print("   ├─ RAG Components: ok")
            
        except Exception as e:
            print(f"   ├─ RAG Components: error {e}")
            self.embedder = None
    
    def _init_agent(self):
        """Inisialisasi AI Agent"""
        try:
            memory = MemoryManager(
                db_path=config.DB_PATH,
                max_history=config.MAX_HISTORY,
                verbose=False
            )
            
            context = ContextManager(
                max_context_length=config.MAX_CONTEXT_LENGTH,
                verbose=False
            )
            
            planner = Planner(
                context_manager=context,
                use_llm=config.PLANNER_USE_LLM and self.llm is not None,
                verbose=False
            )
            if self.llm:
                planner.set_llm(self.llm)
            
            executor = Executor(
                context_manager=context,
                verbose=False
            )
            
            # Register MCP servers
            for name, server in self.mcp.get_all_servers().items():
                executor.register_mcp_server(name, server)
            
            # Register tools
            self._register_tools(executor, planner)
            
            self.agent = AIAgent(
                memory_manager=memory,
                context_manager=context,
                planner=planner,
                executor=executor,
                llm=self.llm,
                verbose=False
            )
            
            self.current_session_id = self.agent.start_session()
            print("   └─ AI Agent: ok")
            
        except Exception as e:
            print(f"   └─ AI Agent: error {e}")
    
    def _register_tools(self, executor, planner):
        """Register tools"""
        fs_server = self.mcp.get_server('filesystem')
        if fs_server:
            file_tools = FileTools(fs_server, verbose=False)
            executor.register_tool_handler('read_file', file_tools.read)
            executor.register_tool_handler('write_file', file_tools.write)
            executor.register_tool_handler('list_files', file_tools.list)
            executor.register_tool_handler('search_files', file_tools.search)
        
        db_server = self.mcp.get_server('database')
        if db_server:
            sqlite_tools = SQLiteTools(db_server, verbose=False)
            executor.register_tool_handler('add_note', sqlite_tools.add_note)
            executor.register_tool_handler('search_note', sqlite_tools.search_note)
            executor.register_tool_handler('save_memory', sqlite_tools.save_memory)
        
        api_server = self.mcp.get_server('api')
        if api_server:
            weather_tools = WeatherTools(api_server, verbose=False)
            executor.register_tool_handler('weather', weather_tools.current)
        
        shell_tools = ShellTools(verbose=False)
        executor.register_tool_handler('shell', shell_tools.execute)
    
    def process_question(self, question: str, use_rag: bool = True):
        """Proses pertanyaan"""
        if not self.is_ready or not self.agent:
            return {
                'success': False,
                'response': 'AI Assistant belum siap.',
                'error': 'Not ready'
            }
        
        try:
            # Threat detection
            if self.threat_detector:
                threat = self.threat_detector.analyze(question)
                if threat.is_high_risk():
                    return {
                        'success': False,
                        'response': 'Pertanyaan tidak aman.',
                        'error': 'Threat detected',
                        'threat_score': threat.score
                    }
            
            # RAG retrieval jika ada
            context = None
            if use_rag and self.retriever and self.context_builder:
                chunks = self.retriever.retrieve(question, top_k=3)
                if chunks:
                    context = self.context_builder.build(chunks)
            
            # Proses dengan agent
            if context:
                # Inject context ke prompt
                # (modifikasi sesuai kebutuhan)
                pass
            
            result = self.agent.process(question)
            
            return {
                'success': True,
                'response': result.get('response', ''),
                'tool_used': result.get('tool_used'),
                'tokens': result.get('tokens', 0),
                'latency': result.get('total_latency', 0)
            }
            
        except Exception as e:
            return {
                'success': False,
                'response': f'Error: {str(e)}',
                'error': str(e)
            }
    
    def process_stream(self, question: str):
        """Proses pertanyaan dengan streaming"""
        if not self.is_ready or not self.agent:
            yield json.dumps({'error': 'Not ready', 'is_last': True})
            return
        
        try:
            # Threat detection
            if self.threat_detector:
                threat = self.threat_detector.analyze(question)
                if threat.is_high_risk():
                    yield json.dumps({
                        'error': 'Threat detected',
                        'is_last': True,
                        'response': 'Pertanyaan tidak aman.'
                    })
                    return
            
            # RAG
            context = None
            if self.retriever and self.context_builder:
                chunks = self.retriever.retrieve(question, top_k=3)
                if chunks:
                    context = self.context_builder.build(chunks)
            
            # Simulate streaming response
            # Untuk streaming penuh, perlu modifikasi agent.process_stream()
            result = self.agent.process(question)
            response = result.get('response', '')
            
            # Stream per kata
            words = response.split()
            for i, word in enumerate(words):
                yield json.dumps({
                    'text': word + (' ' if i < len(words) - 1 else ''),
                    'is_last': i == len(words) - 1,
                    'tool_used': result.get('tool_used') if i == 0 else None,
                    'tokens': result.get('tokens', 0) if i == len(words) - 1 else 0
                })
                time.sleep(0.02)
            
        except Exception as e:
            yield json.dumps({'error': str(e), 'is_last': True})


# ============================================
# INITIALIZE ASSISTANT
# ============================================

assistant = WebAIAssistant()


# ============================================
# FLASK ROUTES
# ============================================

@app.route('/')
def index():
    """Halaman utama"""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint chat (non-streaming)"""
    data = request.get_json()
    question = data.get('message', '').strip()
    use_rag = data.get('use_rag', True)
    
    if not question:
        return jsonify({'error': 'Pertanyaan kosong'}), 400
    
    result = assistant.process_question(question, use_rag)
    return jsonify(result)


@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """Endpoint chat (streaming)"""
    data = request.get_json()
    question = data.get('message', '').strip()
    use_rag = data.get('use_rag', True)
    
    if not question:
        return jsonify({'error': 'Pertanyaan kosong'}), 400
    
    def generate():
        for chunk in assistant.process_stream(question):
            yield f"data: {chunk}\n\n"
        yield "data: {\"is_last\": true}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/history', methods=['GET'])
def get_history():
    """Ambil history percakapan"""
    if assistant.agent:
        history = assistant.agent.get_conversation(limit=20)
        return jsonify({
            'success': True,
            'history': history
        })
    return jsonify({'success': False, 'error': 'Agent not ready'})


@app.route('/api/clear', methods=['POST'])
def clear_history():
    """Clear history"""
    if assistant.agent:
        assistant.agent.reset()
        assistant.current_session_id = assistant.agent.start_session()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Agent not ready'})


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Ambil statistik"""
    if assistant.agent:
        stats = assistant.agent.get_stats()
        return jsonify(stats)
    return jsonify({'error': 'Agent not ready'})


@app.route('/api/models', methods=['GET'])
def get_models():
    """List model tersedia"""
    models = []
    model_dir = config.MODELS_DIR
    if model_dir.exists():
        for f in model_dir.glob('*.gguf'):
            models.append({
                'name': f.name,
                'path': str(f),
                'size': f.stat().st_size
            })
    return jsonify({'models': models})


# ============================================
# RUN SERVER
# ============================================

if __name__ == '__main__':
    print("\n🚀 Starting Web Server...")
    print(f"   http://localhost:5000")
    print("   Press Ctrl+C to stop\n")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )
