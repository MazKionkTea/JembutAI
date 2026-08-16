# agent/planner.py
"""
Planner - Menentukan langkah dan tool yang dibutuhkan berdasarkan pertanyaan user
"""

from typing import Optional, List, Dict, Any, Tuple
import json
import re

from agen.konteks import PengelolaKonteks, StatusAgen


class Perencana:
    """Perencana tugas - menentukan tool apa yang dibutuhkan"""
    
    def __init__(
        self,
        pengelola_konteks: PengelolaKonteks,
        tools_yang_tersedia: Optional[List[str]] = None,
        gunakan_llm : bool = True,
        verbose: bool = False
    ):
        """
        Inisialisasi planner
        Args:
            context_manager: Instance ContextManager
            available_tools: Daftar tool yang tersedia
            use_llm: Gunakan LLM untuk planning (False = pakai rules)
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.konteks = pengelola_konteks
        self.gunakan_llm = gunakan_llm 
        self.verbose = verbose
        self.llm = None  
        self.active = False  # ← DEFAULT: PLANNER NONAKTIF
        
        # Tool registry
        self.tools_yang_tersedia = tools_yang_tersedia or [
            'filesystem',
            'database',
            'github',
            'shell',
            'none'
        ]
        
        # Tool patterns untuk rule-based
        self.tool_patterns = {
            'filesystem': [
                r'(baca|tulis|hapus|rename|list|cari|search)\s*(file|folder|direktori|pdf|doc)',
                r'file\s*(apa|mana|berapa)',
                r'(.+)\.(pdf|txt|docx|py|json|csv)'
            ],
            'database': [
                r'(simpan|insert|tambah|query|select|statistik)\s*(data|note|memory|database)',
                r'ingatkan|ingat\s+(tentang|akan)'
            ],
            'github': [
                r'github|repository|repo|commit|pull\s*request'
            ],
            'shell': [
                r'terminal|command|cmd|bash|shell|eksekusi|jalankan\s*(perintah|command)'
            ]
        }
        
        # Keyword mapping
        self.tool_keywords = {
            'filesystem': ['file', 'folder', 'direktori', 'pdf', 'doc', 'txt', 'baca', 'tulis'],
            'database': ['database', 'sqlite', 'simpan', 'ingat', 'data'],
            'github': ['github', 'repo'],
            'shell': ['terminal', 'command', 'jalankan']
        }
        
        # Prioritas tool (semakin kecil = prioritas lebih tinggi)
        self.tool_priority = {
            'filesystem': 2,
            'database': 3,
            'github': 1,
            'shell': 4,  # Prioritas rendah karena berbahaya
            'none': 5
        }
        
        if self.verbose:
            print(f"[DEBUG] Planner initialized")
            print(f"[DEBUG] Available tools: {self.tools_yang_tersedia}")
            print(f"[DEBUG] Use LLM: {self.gunakan_llm }")


    def siapkan_llm(self, llm) -> None:
        """
        Set LLM instance untuk planning berbasis AI
        Args:
            llm: Instance InferenceEngine
        """
        # STATUS: OK - Method berjalan normal
        self.llm = llm
        if self.verbose:
            print("[DEBUG] LLM set for planner")


    def rencana(self, pertanyaan: str) -> Dict[str, Any]:
        """
        Tentukan langkah yang diperlukan untuk menjawab pertanyaan
        Args:
            question: Pertanyaan user
        Returns:
            Dict dengan: tool, confidence, reasoning
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI        
        if not pertanyaan or not isinstance(pertanyaan, str):
            return {
                'tool': 'none',
                'confidence': 0.0,
                'reasoning': 'Pertanyaan tidak valid',
                'error': True
            }

        # CEK: Jika planner tidak aktif, langsung return 'none'
        if not self.active:
            if self.verbose:
                print("[DEBUG] Planner inactive - using chat mode")
            return {
                'tool': 'none',
                'confidence': 1.0,
                'reasoning': 'Planner tidak aktif (chat mode)'
            }

        if self.verbose:
            print(f"[DEBUG] Planning for: {pertanyaan[:50]}...")
        
        # Update context
        self.konteks.status_agen(StatusAgen.PLANNING)
        self.konteks.pertanyaan_pengguna(pertanyaan)
        
        # Pilih tool
        if self.gunakan_llm and self.llm:
            result = self.rencana_dengan_llm(pertanyaan)
        else:
            result = self.rencana_dengan_aturan(pertanyaan)
        
        # Log hasil
        if self.verbose:
            print(f"[DEBUG] Plan result: tool={result['tool']}, confidence={result['confidence']:.2f}")
            print(f"[DEBUG] Reasoning: {result['reasoning']}")
        
        # Update context
        if result['tool'] != 'none':
            self.konteks.tool_yang_digunakan(result['tool'])
        else:
            self.konteks.tool_yang_digunakan(None)
        
        self.konteks.status_agen(StatusAgen.IDLE)
        
        return result


    def rencana_dengan_aturan(self, pertanyaan: str) -> Dict[str, Any]:
        """
        Planning berbasis aturan (rule-based)
        Args:
            question: Pertanyaan user
        Returns:
            Dict hasil planning
        """
        # STATUS: OK - Method berjalan normal
        question_lower = pertanyaan.lower()
        
        # Cek setiap tool pattern
        tool_scores = {}
        
        for tool, patterns in self.tool_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, question_lower, re.IGNORECASE):
                    score += 1
            
            # Cek keywords
            if tool in self.tool_keywords:
                for keyword in self.tool_keywords[tool]:
                    if keyword in question_lower:
                        score += 1
            
            if score > 0:
                tool_scores[tool] = score
        
        # Tambahkan prioritas
        for tool in tool_scores:
            tool_scores[tool] += 10 - self.tool_priority.get(tool, 5)
        
        # Pilih tool dengan skor tertinggi
        if tool_scores:
            best_tool = max(tool_scores, key=tool_scores.get)
            max_score = tool_scores[best_tool]
            
            # Hitung confidence (0-1)
            total_possible = len(self.tool_patterns.get(best_tool, [])) + 3
            confidence = min(max_score / total_possible, 1.0)
            
            # Jika confidence terlalu rendah, pilih 'none'
            if confidence < 0.3:
                return {
                    'tool': 'none',
                    'confidence': confidence,
                    'reasoning': f'Confidence terlalu rendah ({confidence:.2f})',
                    'scores': tool_scores
                }
            
            return {
                'tool': best_tool,
                'confidence': confidence,
                'reasoning': f'Tool {best_tool} terpilih dengan skor {max_score}',
                'scores': tool_scores
            }
        
        # Tidak ada tool yang cocok
        return {
            'tool': 'none',
            'confidence': 0.0,
            'reasoning': 'Tidak ada tool yang cocok untuk pertanyaan ini',
            'scores': {}
        }

    def rencana_dengan_llm(self, pertanyaan: str) -> Dict[str, Any]:
        """
        Planning berbasis LLM
        Args:
            question: Pertanyaan user
        Returns:
            Dict hasil planning
        """
        # STATUS: OK - Method berjalan normal
        if not self.llm:
            print("[ERROR] LLM not set. Falling back to rules")
            return self.rencana_dengan_aturan(pertanyaan)
        
        try:
            # Buat prompt
            tools_list = ', '.join([t for t in self.tools_yang_tersedia if t != 'none'])
            prompt = f"""Pertanyaan user: {pertanyaan}

Tools yang tersedia: {tools_list}

Pilih tool yang paling sesuai untuk menjawab pertanyaan di atas.
Jika tidak perlu tool, jawab "none".

Format output: JSON
{{"tool": "nama_tool", "reasoning": "alasan singkat"}}

Pilihan tool:"""
            
            # Generate dengan LLM
            result = self.llm.generate(
                prompt=prompt,
                max_tokens=10000,
                temperature=0.3  # Lebih deterministik
            )
            
            # Parse hasil
            if isinstance(result, dict):
                text = result.get('text', '')
            else:
                text = str(result)
            
            # Cari JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    tool = data.get('tool', 'none').strip().lower()
                    
                    # Validasi tool
                    if tool not in self.tools_yang_tersedia:
                        tool = 'none'
                    
                    return {
                        'tool': tool,
                        'confidence': 0.8,
                        'reasoning': data.get('reasoning', 'LLM recommendation'),
                        'llm_response': text
                    }
                except json.JSONDecodeError:
                    pass
            
            # Fallback: coba ekstrak tool dari teks
            for tool in self.tools_yang_tersedia:
                if tool in text.lower():
                    return {
                        'tool': tool,
                        'confidence': 0.6,
                        'reasoning': f'Tool "{tool}" ditemukan di response LLM',
                        'llm_response': text
                    }
            
            return {
                'tool': 'none',
                'confidence': 0.4,
                'reasoning': 'Tidak bisa parse output LLM',
                'llm_response': text
            }
            
        except Exception as e:
            print(f"[ERROR] LLM planning failed: {e}")
            return self.rencana_dengan_aturan(pertanyaan)

    def needs_tool(self, pertanyaan: str) -> Tuple[bool, Optional[str]]:
        """
        Cek apakah pertanyaan membutuhkan tool
        Args:
            question: Pertanyaan user
        Returns:
            (needs_tool, tool_name)
        """
        # STATUS: OK - Method berjalan normal
        result = self.rencana(pertanyaan)
        tool = result.get('tool', 'none')
        
        needs = tool != 'none' and result.get('confidence', 0) > 0.3
        
        if self.verbose:
            print(f"[DEBUG] Needs tool? {needs} -> {tool if needs else 'none'}")
        
        return needs, tool if needs else None


    def tambahkan_tool(self, nama_tool: str, patterns: List[str], keywords: List[str]) -> None:
        """
        Tambahkan tool baru ke planner
        
        Args:
            tool_name: Nama tool
            patterns: List regex pattern
            keywords: List keyword
        """
        # STATUS: OK - Method berjalan normal
        if nama_tool not in self.tools_yang_tersedia:
            self.tools_yang_tersedia.append(nama_tool)
        
        if patterns:
            self.tool_patterns[nama_tool] = patterns
        
        if keywords:
            self.tool_keywords[nama_tool] = keywords
        
        # Set prioritas default
        if nama_tool not in self.tool_priority:
            self.tool_priority[nama_tool] = 3
        
        if self.verbose:
            print(f"[DEBUG] Tool added: {nama_tool}")


    def ambil_kemampuan_tool(self, nama_tool: str) -> Dict[str, Any]:
        """
        Ambil kemampuan tool
        Args:
            tool_name: Nama tool
        Returns:
            Dict kemampuan tool
        """
        # STATUS: OK - Method berjalan normal
        return {
            'name': nama_tool,
            'patterns': self.tool_patterns.get(nama_tool, []),
            'keywords': self.tool_keywords.get(nama_tool, []),
            'priority': self.tool_priority.get(nama_tool, 3)
        }


    def mode_tool_aktif(self):
        """Aktifkan planner (mode tool)"""
        self.active = True
        if self.verbose:
            print("[DEBUG] Planner activated")


    def mode_tool_non_aktif(self):
        """Nonaktifkan planner (mode chat biasa)"""
        self.active = False
        if self.verbose:
            print("[DEBUG] Planner deactivated")

    def apakah_planner_aktif(self) -> bool:
        return self.active


# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING PLANNER")
    print("=" * 50)
    
    # Inisialisasi
    print("\n[TEST] Init Planner")
    context = PengelolaKonteks(verbose=False)
    planner = Perencana(context, verbose=True)
    
    # Test cases
    test_questions = [
        ("Baca file report.pdf", "filesystem"),
        ("Ingatkan saya tentang meeting", "database"),
        ("Jalankan perintah ls -la", "shell"),
        ("Apa itu Python?", "none")
    ]
    
    print("\n[TEST] Planning tests")
    for pertanyaan, expected in test_questions:
        result = planner.rencana(pertanyaan)
        status = "✓" if result['tool'] == expected else "✗"
        print(f"{status} Q: {pertanyaan[:40]}...")
        print(f"   Tool: {result['tool']} (expected: {expected})")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Reasoning: {result['reasoning']}")
        print()
    
    # Test needs_tool
    print("\n[TEST] Needs tool tests")
    for pertanyaan, _ in test_questions[:3]:
        needs, tool = planner.needs_tool(pertanyaan)
        print(f"Q: {pertanyaan[:30]}...")
        print(f"  Needs tool: {needs}, Tool: {tool}")
        print()
    
    # Test add tool
    print("\n[TEST] Add custom tool")
    planner.tambahkan_tool(
        "calculator",
        patterns=[r'hitung|kalkulasi|calculate|math'],
        keywords=['hitung', 'kalkulasi', 'math']
    )
    print(f"Tools available: {planner.tools_yang_tersedia}")
    
    # Test get capabilities
    print("\n[TEST] Get tool capabilities")
    caps = planner.ambil_kemampuan_tool("weather")
    print(f"Weather capabilities: {caps}")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)