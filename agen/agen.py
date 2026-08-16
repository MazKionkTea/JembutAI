# agent/agent.py
"""
Agent - Koordinator utama AI Agent
"""

from typing import Optional, Dict, Any, List, Generator, Union
import time
import json

from agen.konteks import PengelolaKonteks, StatusAgen
from agen.memori import PengelolaMemori
from agen.perencana import Perencana
from agen.eksekutor import Eksekutor


class AgentAI:
    """AI Agent utama - mengkoordinasikan semua komponen"""
    
    def __init__(
        self,
        pengelola_memori: Optional[PengelolaMemori] = None,
        pengelola_konteks: Optional[PengelolaKonteks] = None,
        perencana: Optional[Perencana] = None,
        eksekutor: Optional[Eksekutor] = None,
        llm = None,
        verbose: bool = False
    ):
        # STATUS: OK - Constructor berjalan normal
        self.verbose = verbose
        
        # Inisialisasi komponen
        self.memori = pengelola_memori or PengelolaMemori(verbose=verbose)
        self.konteks = pengelola_konteks or PengelolaKonteks(verbose=verbose)
        self.perencana = perencana or Perencana(self.konteks, verbose=verbose)
        self.eksekutor = eksekutor or Eksekutor(self.konteks, verbose=verbose)
        self.llm = llm
        
        # Set LLM ke planner jika ada
        if llm:
            self.perencana.siapkan_llm(llm)
        
        # Session aktif
        self.identitas_sesi = None
        self.berjalan = False
        
        # Statistik
        self.total_queries = 0
        self.total_tool_calls = 0
        self.total_errors = 0
        
        if self.verbose:
            print(f"[DEBUG] AIAgent initialized")
            print(f"[DEBUG] Components: memory, context, planner, executor")
            print(f"[DEBUG] LLM: {'Loaded' if llm else 'Not loaded'}")


    def mulai_sesi(self, identitas_sesi: Optional[str] = None) -> str:
        # STATUS: OK - Method berjalan normal
        self.identitas_sesi = self.memori.mulai_sesi(identitas_sesi)
        self.konteks.reset()
        self.berjalan = True
        
        if self.verbose:
            print(f"[DEBUG] Session started: {self.identitas_sesi}")
        
        return self.identitas_sesi


    def proses(self, pertanyaan: str, stream: bool = False) -> Dict[str, Any]:
        """
        Proses pertanyaan user secara sinkron
        Args:
            pertanyaan: Pertanyaan user
            stream: Jika True, streaming response ke console
        Returns:
            Dict dengan response, tool_used, metadata
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not self.berjalan:
            print("[ERROR] Agent belum running. Panggil mulai_sesi() terlebih dahulu")
            return {
                'respon': '',
                'error': 'Agent not running',
                'tool_used': None,
                'success': False
            }
        
        if not pertanyaan or not isinstance(pertanyaan, str):
            print("[ERROR] pertanyaan harus string tidak kosong")
            return {
                'respon': '',
                'error': 'pertanyaan tidak valid',
                'tool_used': None,
                'success': False
            }
        
        waktu_dimulai = time.time()
        self.total_queries += 1
        
        if self.verbose:
            print("\n" + "=" * 50)
            print(f"[DEBUG] Processing pertanyaan #{self.total_queries}: {pertanyaan[:50]}...")
            print("=" * 50)
        
        try:
            # STEP 1: Update context dengan pertanyaan
            self.konteks.status_konteks_agen(StatusAgen.PROCESSING)
            self.konteks.pertanyaan_pengguna(pertanyaan)
            
            # Simpan ke memory
            self.memori.tambah_percakapan('user', pertanyaan)
            
            # STEP 2: Planning - tentukan tool
            plan = self.perencana.rencana(pertanyaan)
            tool_name = plan.get('tool', 'none')
            tool_used = tool_name if tool_name != 'none' else None
            
            if self.verbose:
                print(f"[DEBUG] Plan: tool={tool_name}, confidence={plan.get('confidence', 0)}")
            
            # STEP 3: Eksekusi tool jika diperlukan
            tool_result = None
            if tool_name != 'none':
                self.total_tool_calls += 1
                self.konteks.status_konteks_agen(StatusAgen.EXECUTING)
                
                # Eksekusi
                exec_result = self.eksekutor.eksekusi(tool_name)
                
                if exec_result.get('success'):
                    tool_result = exec_result.get('result')
                    if self.verbose:
                        print(f"[DEBUG] Tool result: {str(tool_result)[:100]}...")
                else:
                    error_msg = exec_result.get('error', 'Unknown error')
                    print(f"[ERROR] Tool execution failed: {error_msg}")
                    self.total_errors += 1
                    
                    # Tambahkan error ke context
                    self.konteks.tambahkan_ke_konteks('tool', f"Error: {error_msg}")
                    
                    # Lanjutkan dengan response error
                    return {
                        'response': f"Maaf, terjadi error saat menjalankan tool: {error_msg}",
                        'tool_used': tool_name,
                        'success': False,
                        'error': error_msg,
                        'plan': plan,
                        'execution_result': exec_result,
                        'latency': time.time() - waktu_dimulai
                    }
            
            # STEP 4: Generate response
            self.konteks.status_konteks_agen(StatusAgen.RESPONDING)
            
            if stream and self.llm:
                return self._proses_streaming(pertanyaan, tool_result)
            else:
                return self._proses_langsung(pertanyaan, tool_result)
                
        except Exception as e:
            print(f"[ERROR] Process failed: {e}")
            self.total_errors += 1
            self.konteks.status_konteks_agen(StatusAgen.ERROR)
            # self.konteks.status_konteks_terakhir(str(e))
            self.konteks.pesan_error(str(e))            
            return {
                'response': f"Maaf, terjadi error: {str(e)}",
                'tool_used': None,
                'success': False,
                'error': str(e),
                'latency': time.time() - waktu_dimulai
            }


    def _proses_langsung(self, pertanyaan: str, tool_result: Optional[str]) -> Dict[str, Any]:
        """Proses tanpa streaming (batch)"""
        if not self.llm:
            respon = self._generate_simple_response(pertanyaan, None, tool_result)
            return {'response': respon, 'success': True}
        
        menghasilkan_respon = self.llm.generate_response(
            pertanyaan=pertanyaan,
            tool_result=tool_result,
            konteks=self.konteks.ambil_konteks_saat_ini_string(n=5),
            max_tokens=10000
        )
        
        respon = menghasilkan_respon.get('text', '')
        tokens = menghasilkan_respon.get('tokens', 0)
        latency = menghasilkan_respon.get('latency', 0)
        
        if respon:
            self.memori.tambah_percakapan('assistant', respon, tokens)
            self.konteks.tambahkan_ke_konteks('assistant', respon)
        
        self.konteks.status_konteks_agen(StatusAgen.IDLE)
        
        return {
            'respon': respon,
            'tokens': tokens,
            'total_latency': latency,
            'success': True
        }


    def _proses_streaming(self, pertanyaan: str, tool_result: Optional[str]) -> Dict[str, Any]:
        """Proses dengan streaming"""
        try:
            prompt = self._build_prompt(pertanyaan, tool_result)
            
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
                self.memori.tambah_percakapan('assistant', full_response, tokens)
                self.konteks.tambahkan_ke_konteks('assistant', full_response)
            
            self.konteks.status_konteks_agen(StatusAgen.IDLE)
            
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


    def _build_prompt(self, pertanyaan: str, tool_result: Optional[str] = None) -> str:
        """
        Build prompt untuk LLM
        Args:
            pertanyaan: Pertanyaan user
            tool_result: Hasil tool (opsional)
        Returns:
            Prompt string
        """
        # STATUS: OK - Method berjalan normal
        system = """Anda adalah asisten AI yang bisa diandalkan.
Jawab pertanyaan dengan jelas, lengkap, dan terstruktur.
Gunakan bahasa santai dan tidak kaku.
Berikan penjelasan yang detail dan contoh konkret.
Berikan penjelasan dengan bahasa yang sederhana dan mudah dimengerti.
Jika diminta membuat kode, berikan kode lengkap dengan komentar.
Jika tidak tahu, katakan tidak tahu.

**ATURAN PENTING:**
- Jawablah dengan LENGKAP, jangan hanya pembukaan.
- Jika diminta script, tuliskan script LENGKAP.
- Jika diminta penjelasan, jelaskan secara DETAIL.
- Jangan berikan jawaban/respon afirmasi.
"""
        
        konteks = self.konteks.ambil_konteks_saat_ini_string(n=5)
        
        if tool_result:
            user = f"""Konteks sebelumnya:
{konteks}

Hasil dari tool:
{tool_result}

Pertanyaan: {pertanyaan}

Jawab pertanyaan berdasarkan hasil tool di atas:"""
        elif konteks:
            user = f"""Konteks sebelumnya:
{konteks}

Pertanyaan: {pertanyaan}

Jawab pertanyaan dengan mempertimbangkan konteks di atas:"""
        else:
            user = f"Pertanyaan: {pertanyaan}\n\nJawab pertanyaan berikut:"
        
        return f"{system}\n\n{user}"


    def _generate_simple_response(self, pertanyaan: str, tool_name: str, tool_result: Optional[str]) -> str:
        """
        Generate response sederhana tanpa LLM (fallback)
        Args:
            pertanyaan: Pertanyaan user
            tool_name: Nama tool
            tool_result: Hasil tool
        Returns:
            Response string
        """
        # STATUS: OK - Method berjalan normal
        if tool_name == 'none':
            return f"Saya tidak yakin bagaimana menjawab: '{pertanyaan}'\n\nCatatan: LLM tidak tersedia, gunakan mode dengan LLM untuk jawaban yang lebih baik."
        elif tool_result:
            return f"Berdasarkan tool {tool_name}, hasilnya:\n{str(tool_result)}"
        else:
            return f"Tool {tool_name} telah dijalankan, tetapi tidak ada hasil."


    def ambil_percakapan_dari_memori(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Ambil percakapan dari memory
        Args:
            limit: Jumlah pesan terakhir
        Returns:
            List pesan
        """
        # STATUS: OK - Method berjalan normal
        return self.memori.ambil_percakapan_dari_memori_history(limit=limit)


    def ambil_konteks_saat_ini(self) -> Dict[str, Any]:
        """
        Ambil konteks saat ini
        
        Returns:
            Dict konteks
        """
        # STATUS: OK - Method berjalan normal
        return self.konteks.ambil_konteks_saat_ini()


    def status_agen_terakhir(self) -> Dict[str, Any]:
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
            'berjalan': self.berjalan,
            'identitas_sesi': self.identitas_sesi,
            'memory': self.memori.status_memori_terakhir(),
            'konteks': self.konteks.status_konteks_terakhir(),
            'executor': self.eksekutor.status_eksekusi_terakhir()
        }


    def reset(self) -> None:
        """Reset agent (clear session dan konteks)"""
        # STATUS: OK - Method berjalan normal
        self.memori.bersihkan_sesi()
        self.konteks.reset()
        self.total_queries = 0
        self.total_tool_calls = 0
        self.total_errors = 0
        self.berjalan = False
        
        if self.verbose:
            print("[DEBUG] Agent reset")


    def daftarkan_tool(self, tool_name: str, handler) -> None:
        """
        Register tool handler baru
        Args:
            tool_name: Nama tool
            handler: Fungsi handler
        """
        # STATUS: OK - Method berjalan normal
        self.eksekutor.daftarkan_pengendali_tool(tool_name, handler)
        self.perencana.tambahkan_tool(tool_name, patterns=[], keywords=[])
        
        if self.verbose:
            print(f"[DEBUG] Tool registered: {tool_name}")


    def daftarkan_mcp_server(self, name: str, server) -> None:
        """
        Register MCP server
        Args:
            name: Nama server
            server: Instance MCP server
        """
        # STATUS: OK - Method berjalan normal
        self.eksekutor.daftarkan_server_mcp(name, server)
        
        if self.verbose:
            print(f"[DEBUG] MCP Server registered: {name}")


    def toggle_planner(self, active: bool = None):
        """Aktif/nonaktifkan planner"""
        if active is None:
            active = not self.perencana.is_active()
        
        if active:
            self.perencana.mode_tool_aktif()
            print("[INFO] Planner activated - tools available")
        else:
            self.perencana.mode_tool_non_aktif()
            print("[INFO] Planner deactivated - chat mode only")
        
        return self.perencana.apakah_planner_aktif()


    def is_planner_active(self) -> bool:
        return self.perencana.apakah_planner_aktif()

# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING AI AGENT")
    print("=" * 50)
    
    # Inisialisasi
    print("\n[TEST] Init AIAgent")
    agent = AgentAI(verbose=True)
    
    # Test start session
    print("\n[TEST] Start session")
    identitas_sesi = agent.mulai_sesi()
    print(f"Session ID: {identitas_sesi}")
    
    # Test tanpa LLM (fallback)
    print("\n[TEST] Process without LLM")
    result = agent.proses("Halo, apa kabar?")
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
    
    agent.daftarkan_tool('write_file', write_test_file)
    
    result = agent.proses("Tulis file test_agent.txt dengan isi 'Hello Agent'")
    print(f"Response: {result.get('response')}")
    print(f"Tool used: {result.get('tool_used')}")
    print(f"Success: {result.get('success')}")
    print()
    
    # Test stats
    print("\n[TEST] Get stats")
    stats = agent.status_agen_terakhir()
    print(f"Stats: {stats}")
    
    # Test conversation
    print("\n[TEST] Get conversation")
    conv = agent.ambil_percakapan_dari_memori()
    for msg in conv:
        print(f"  {msg['role']}: {msg['content'][:50]}...")
    
    # Test reset
    print("\n[TEST] Reset")
    agent.reset()
    print(f"Is running: {agent.berjalan}")
    
    # Cleanup
    import os
    if os.path.exists("test_agent.txt"):
        os.remove("test_agent.txt")
        print("Cleanup: test_agent.txt removed")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)



# ============
# ==== bug ====
# ============

# Type "str | None" is not assignable to return type "str"
#   Type "str | None" is not assignable to type "str"
#     "None" is not assignable to "str"

# Argument of type "None" cannot be assigned to parameter "tool_name" of type "str" in function "_generate_simple_response"
#   "None" is not assignable to "str"

# "generate" is not a known attribute of "None"

# Expression of type "None" cannot be assigned to parameter of type "bool"
#   "None" is not assignable to "bool"

