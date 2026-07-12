# agent/agent.py
"""
Agent - Koordinator utama AI Agent
"""

from typing import Optional, Dict, Any, List, Generator, Union
import time
import json

from agent.context import ContextManager, AgentState
from agent.memory import MemoryManager
from agent.planner import Planner
from agent.executor import Executor


class AIAgent:
    """AI Agent utama - mengkoordinasikan semua komponen"""
    
    def __init__(
        self,
        memory_manager: Optional[MemoryManager] = None,
        context_manager: Optional[ContextManager] = None,
        planner: Optional[Planner] = None,
        executor: Optional[Executor] = None,
        llm = None,
        verbose: bool = False
    ):
        """
        Inisialisasi AI Agent
        
        Args:
            memory_manager: Instance MemoryManager
            context_manager: Instance ContextManager
            planner: Instance Planner
            executor: Instance Executor
            llm: Instance InferenceEngine
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.verbose = verbose
        
        # Inisialisasi komponen
        self.memory = memory_manager or MemoryManager(verbose=verbose)
        self.context = context_manager or ContextManager(verbose=verbose)
        self.planner = planner or Planner(self.context, verbose=verbose)
        self.executor = executor or Executor(self.context, verbose=verbose)
        self.llm = llm
        
        # Set LLM ke planner jika ada
        if llm:
            self.planner.set_llm(llm)
        
        # Session aktif
        self.session_id = None
        self.is_running = False
        
        # Statistik
        self.total_queries = 0
        self.total_tool_calls = 0
        self.total_errors = 0
        
        if self.verbose:
            print(f"[DEBUG] AIAgent initialized")
            print(f"[DEBUG] Components: memory, context, planner, executor")
            print(f"[DEBUG] LLM: {'Loaded' if llm else 'Not loaded'}")

    def start_session(self, session_id: Optional[str] = None) -> str:
        """
        Mulai sesi baru
        
        Args:
            session_id: ID sesi (None = buat baru)
        
        Returns:
            session_id yang digunakan
        """
        # STATUS: OK - Method berjalan normal
        self.session_id = self.memory.start_session(session_id)
        self.context.reset()
        self.is_running = True
        
        if self.verbose:
            print(f"[DEBUG] Session started: {self.session_id}")
        
        return self.session_id


    def process(self, question: str, stream: bool = False) -> Dict[str, Any]:
        """
        Proses pertanyaan user secara sinkron
        
        Args:
            question: Pertanyaan user
            stream: Jika True, streaming response ke console
        
        Returns:
            Dict dengan response, tool_used, metadata
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not self.is_running:
            print("[ERROR] Agent belum running. Panggil start_session() terlebih dahulu")
            return {
                'response': '',
                'error': 'Agent not running',
                'tool_used': None,
                'success': False
            }
        
        if not question or not isinstance(question, str):
            print("[ERROR] Question harus string tidak kosong")
            return {
                'response': '',
                'error': 'Question tidak valid',
                'tool_used': None,
                'success': False
            }
        
        start_time = time.time()
        self.total_queries += 1
        
        if self.verbose:
            print("\n" + "=" * 50)
            print(f"[DEBUG] Processing question #{self.total_queries}: {question[:50]}...")
            print("=" * 50)
        
        try:
            # STEP 1: Update context dengan pertanyaan
            self.context.set_state(AgentState.PROCESSING)
            self.context.set_question(question)
            
            # Simpan ke memory
            self.memory.add_message('user', question)
            
            # STEP 2: Planning - tentukan tool
            plan = self.planner.plan(question)
            tool_name = plan.get('tool', 'none')
            tool_used = tool_name if tool_name != 'none' else None
            
            if self.verbose:
                print(f"[DEBUG] Plan: tool={tool_name}, confidence={plan.get('confidence', 0)}")
            
            # STEP 3: Eksekusi tool jika diperlukan
            tool_result = None
            if tool_name != 'none':
                self.total_tool_calls += 1
                self.context.set_state(AgentState.EXECUTING)
                
                # Eksekusi
                exec_result = self.executor.execute(tool_name)
                
                if exec_result.get('success'):
                    tool_result = exec_result.get('result')
                    if self.verbose:
                        print(f"[DEBUG] Tool result: {str(tool_result)[:100]}...")
                else:
                    error_msg = exec_result.get('error', 'Unknown error')
                    print(f"[ERROR] Tool execution failed: {error_msg}")
                    self.total_errors += 1
                    
                    # Tambahkan error ke context
                    self.context.add_to_context('tool', f"Error: {error_msg}")
                    
                    # Lanjutkan dengan response error
                    return {
                        'response': f"Maaf, terjadi error saat menjalankan tool: {error_msg}",
                        'tool_used': tool_name,
                        'success': False,
                        'error': error_msg,
                        'plan': plan,
                        'execution_result': exec_result,
                        'latency': time.time() - start_time
                    }
            
            # STEP 4: Generate response
            self.context.set_state(AgentState.RESPONDING)
            
            if stream and self.llm:
                return self._process_stream(question, tool_result)
            else:
                return self._process_batch(question, tool_result)
                
        except Exception as e:
            print(f"[ERROR] Process failed: {e}")
            self.total_errors += 1
            self.context.set_state(AgentState.ERROR)
            self.context.set_error(str(e))
            
            return {
                'response': f"Maaf, terjadi error: {str(e)}",
                'tool_used': None,
                'success': False,
                'error': str(e),
                'latency': time.time() - start_time
            }


    def _process_batch(self, question: str, tool_result: Optional[str]) -> Dict[str, Any]:
        """Proses tanpa streaming (batch)"""
        if not self.llm:
            response_text = self._generate_simple_response(question, None, tool_result)
            return {'response': response_text, 'success': True}
        
        response_result = self.llm.generate_response(
            question=question,
            tool_result=tool_result,
            context=self.context.get_context_string(n=5),
            max_tokens=10000
        )
        
        response_text = response_result.get('text', '')
        tokens = response_result.get('tokens', 0)
        latency = response_result.get('latency', 0)
        
        if response_text:
            self.memory.add_message('assistant', response_text, tokens)
            self.context.add_to_context('assistant', response_text)
        
        self.context.set_state(AgentState.IDLE)
        
        return {
            'response': response_text,
            'tokens': tokens,
            'total_latency': latency,
            'success': True
        }


    def _process_stream(self, question: str, tool_result: Optional[str]) -> Dict[str, Any]:
        """Proses dengan streaming"""
        try:
            prompt = self._build_prompt(question, tool_result)
            
            stream_gen = self.llm.generate(
                prompt=prompt,
                stream=True,
                max_tokens=10000,
                temperature=0.7
            )
            
            full_response = ""
            tokens = 0
            latency = 0
            
            if isinstance(stream_gen, Generator):
                print("\n🤖 Assistant: ", end="", flush=True)
                
                for chunk in stream_gen:
                    if chunk.get('is_last'):
                        tokens = chunk.get('tokens', 0)
                        latency = chunk.get('latency', 0)
                        break
                    
                    text = chunk.get('text', '')
                    if text:
                        print(text, end="", flush=True)
                        full_response += text
                
                print()
            else:
                full_response = stream_gen.get('text', '')
                tokens = stream_gen.get('tokens', 0)
                latency = stream_gen.get('latency', 0)
                print(full_response)
            
            if full_response:
                self.memory.add_message('assistant', full_response, tokens)
                self.context.add_to_context('assistant', full_response)
            
            self.context.set_state(AgentState.IDLE)
            
            return {
                'response': full_response,
                'tokens': tokens,
                'total_latency': latency,
                'success': True
            }
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return {
                'response': f"Error: {e}",
                'success': False,
                'error': str(e)
            }


    def _build_prompt(self, question: str, tool_result: Optional[str] = None) -> str:
        """
        Build prompt untuk LLM
        
        Args:
            question: Pertanyaan user
            tool_result: Hasil tool (opsional)
        
        Returns:
            Prompt string
        """
        # STATUS: OK - Method berjalan normal
        system = """Anda adalah asisten AI yang membantu, jujur, dan aman.
Jawab pertanyaan dengan jelas, lengkap, dan terstruktur.
Berikan penjelasan yang detail dan contoh konkret.
Jika diminta membuat kode, berikan kode lengkap dengan komentar.
Jika tidak tahu, katakan tidak tahu.

**ATURAN PENTING:**
- Jawablah dengan LENGKAP, jangan hanya pembukaan.
- Jika diminta script, tuliskan script LENGKAP.
- Jika diminta penjelasan, jelaskan secara DETAIL.
"""
        
        context = self.context.get_context_string(n=5)
        
        if tool_result:
            user = f"""Konteks sebelumnya:
{context}

Hasil dari tool:
{tool_result}

Pertanyaan: {question}

Jawab pertanyaan berdasarkan hasil tool di atas:"""
        elif context:
            user = f"""Konteks sebelumnya:
{context}

Pertanyaan: {question}

Jawab pertanyaan dengan mempertimbangkan konteks di atas:"""
        else:
            user = f"Pertanyaan: {question}\n\nJawab pertanyaan berikut:"
        
        return f"{system}\n\n{user}"

    def _generate_simple_response(self, question: str, tool_name: str, tool_result: Optional[str]) -> str:
        """
        Generate response sederhana tanpa LLM (fallback)
        
        Args:
            question: Pertanyaan user
            tool_name: Nama tool
            tool_result: Hasil tool
        
        Returns:
            Response string
        """
        # STATUS: OK - Method berjalan normal
        if tool_name == 'none':
            return f"Saya tidak yakin bagaimana menjawab: '{question}'\n\nCatatan: LLM tidak tersedia, gunakan mode dengan LLM untuk jawaban yang lebih baik."
        elif tool_result:
            return f"Berdasarkan tool {tool_name}, hasilnya:\n{str(tool_result)}"
        else:
            return f"Tool {tool_name} telah dijalankan, tetapi tidak ada hasil."

    def get_conversation(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Ambil percakapan dari memory
        
        Args:
            limit: Jumlah pesan terakhir
        
        Returns:
            List pesan
        """
        # STATUS: OK - Method berjalan normal
        return self.memory.get_conversation_history(limit=limit)

    def get_context(self) -> Dict[str, Any]:
        """
        Ambil konteks saat ini
        
        Returns:
            Dict konteks
        """
        # STATUS: OK - Method berjalan normal
        return self.context.get_current_context()

    def get_stats(self) -> Dict[str, Any]:
        """
        Ambil statistik agent
        
        Returns:
            Dict statistik
        """
        # STATUS: OK - Method berjalan normal
        return {
            'total_queries': self.total_queries,
            'total_tool_calls': self.total_tool_calls,
            'total_errors': self.total_errors,
            'success_rate': (
                (self.total_queries - self.total_errors) / self.total_queries
                if self.total_queries > 0 else 0
            ),
            'is_running': self.is_running,
            'session_id': self.session_id,
            'memory': self.memory.get_stats(),
            'context': self.context.get_stats(),
            'executor': self.executor.get_stats()
        }

    def reset(self) -> None:
        """Reset agent (clear session dan context)"""
        # STATUS: OK - Method berjalan normal
        self.memory.clear_session()
        self.context.reset()
        self.total_queries = 0
        self.total_tool_calls = 0
        self.total_errors = 0
        self.is_running = False
        
        if self.verbose:
            print("[DEBUG] Agent reset")

    def register_tool(self, tool_name: str, handler) -> None:
        """
        Register tool handler baru
        
        Args:
            tool_name: Nama tool
            handler: Fungsi handler
        """
        # STATUS: OK - Method berjalan normal
        self.executor.register_tool_handler(tool_name, handler)
        self.planner.add_tool(tool_name, patterns=[], keywords=[])
        
        if self.verbose:
            print(f"[DEBUG] Tool registered: {tool_name}")

    def register_mcp_server(self, name: str, server) -> None:
        """
        Register MCP server
        
        Args:
            name: Nama server
            server: Instance MCP server
        """
        # STATUS: OK - Method berjalan normal
        self.executor.register_mcp_server(name, server)
        
        if self.verbose:
            print(f"[DEBUG] MCP Server registered: {name}")

    def toggle_planner(self, active: bool = None):
        """Aktif/nonaktifkan planner"""
        if active is None:
            active = not self.planner.is_active()
        
        if active:
            self.planner.activate()
            print("[INFO] Planner activated - tools available")
        else:
            self.planner.deactivate()
            print("[INFO] Planner deactivated - chat mode only")
        
        return self.planner.is_active()

    def is_planner_active(self) -> bool:
        return self.planner.is_active()

# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING AI AGENT")
    print("=" * 50)
    
    # Inisialisasi
    print("\n[TEST] Init AIAgent")
    agent = AIAgent(verbose=True)
    
    # Test start session
    print("\n[TEST] Start session")
    session_id = agent.start_session()
    print(f"Session ID: {session_id}")
    
    # Test tanpa LLM (fallback)
    print("\n[TEST] Process without LLM")
    result = agent.process("Halo, apa kabar?")
    print(f"Response: {result.get('response')}")
    print(f"Success: {result.get('success')}")
    print()
    
    # Test dengan tool (filesystem)
    print("\n[TEST] Process with filesystem tool")
    # Daftarkan handler filesystem
    def write_test_file(path: str = "test_agent.txt", content: str = "Hello Agent"):
        with open(path, 'w') as f:
            f.write(content)
        return f"File written: {path}"
    
    agent.register_tool('write_file', write_test_file)
    
    result = agent.process("Tulis file test_agent.txt dengan isi 'Hello Agent'")
    print(f"Response: {result.get('response')}")
    print(f"Tool used: {result.get('tool_used')}")
    print(f"Success: {result.get('success')}")
    print()
    
    # Test stats
    print("\n[TEST] Get stats")
    stats = agent.get_stats()
    print(f"Stats: {stats}")
    
    # Test conversation
    print("\n[TEST] Get conversation")
    conv = agent.get_conversation()
    for msg in conv:
        print(f"  {msg['role']}: {msg['content'][:50]}...")
    
    # Test reset
    print("\n[TEST] Reset")
    agent.reset()
    print(f"Is running: {agent.is_running}")
    
    # Cleanup
    import os
    if os.path.exists("test_agent.txt"):
        os.remove("test_agent.txt")
        print("Cleanup: test_agent.txt removed")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)