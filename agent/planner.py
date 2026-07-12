# agent/planner.py
"""
Planner - Menentukan langkah dan tool yang dibutuhkan berdasarkan pertanyaan user
"""

from typing import Optional, List, Dict, Any, Tuple
import json
import re

from agent.context import ContextManager, AgentState


class Planner:
    """Perencana tugas - menentukan tool apa yang dibutuhkan"""
    
    def __init__(
        self,
        context_manager: ContextManager,
        available_tools: Optional[List[str]] = None,
        use_llm: bool = True,
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
        self.context = context_manager
        self.use_llm = use_llm
        self.verbose = verbose
        self.llm = None  # Akan di-set nanti
        self.active = False  # ← DEFAULT: PLANNER NONAKTIF
        
        # Tool registry
        self.available_tools = available_tools or [
            'filesystem',
            'database',
            # 'weather',
            # 'wikipedia',
            # 'news',
            # 'currency',
            # 'translate',
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
            # 'weather': [
            #     r'cuaca|suhu|temperature|weather|hujan|cerah|panas|dingin',
            #     r'(berapa|bagaimana)\s*(cuaca|suhu)'
            # ],
            # 'wikipedia': [
            #     r'wikipedia|wiki|ensiklopedia',
            #     r'cari\s+(tentang|informasi)'
            # ],
            # 'news': [
            #     r'berita|news|terkini|headline'
            # ],
            # 'currency': [
            #     r'mata\s*uang|currency|kurs|rupiah|dolar|euro|yen|convert|konversi'
            # ],
            # 'translate': [
            #     r'terjemah|translate|artikan|bahasa'
            # ],
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
            # 'weather': ['cuaca', 'suhu', 'temperatur', 'weather'],
            # 'wikipedia': ['wikipedia', 'wiki', 'ensiklopedia'],
            # 'news': ['berita', 'news', 'headline'],
            # 'currency': ['mata uang', 'kurs', 'rupiah', 'dolar'],
            # 'translate': ['terjemah', 'translate', 'bahasa'],
            'github': ['github', 'repo'],
            'shell': ['terminal', 'command', 'jalankan']
        }
        
        # Prioritas tool (semakin kecil = prioritas lebih tinggi)
        self.tool_priority = {
            'filesystem': 2,
            'database': 3,
            # 'weather': 1,
            # 'wikipedia': 1,
            # 'news': 1,
            # 'currency': 1,
            # 'translate': 1,
            'github': 1,
            'shell': 4,  # Prioritas rendah karena berbahaya
            'none': 5
        }
        
        if self.verbose:
            print(f"[DEBUG] Planner initialized")
            print(f"[DEBUG] Available tools: {self.available_tools}")
            print(f"[DEBUG] Use LLM: {self.use_llm}")

    def set_llm(self, llm) -> None:
        """
        Set LLM instance untuk planning berbasis AI
        
        Args:
            llm: Instance InferenceEngine
        """
        # STATUS: OK - Method berjalan normal
        self.llm = llm
        if self.verbose:
            print("[DEBUG] LLM set for planner")

    def plan(self, question: str) -> Dict[str, Any]:
        """
        Tentukan langkah yang diperlukan untuk menjawab pertanyaan
        
        Args:
            question: Pertanyaan user
        
        Returns:
            Dict dengan: tool, confidence, reasoning
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI        
        if not question or not isinstance(question, str):
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
            print(f"[DEBUG] Planning for: {question[:50]}...")
        
        # Update context
        self.context.set_state(AgentState.PLANNING)
        self.context.set_question(question)
        
        # Pilih tool
        if self.use_llm and self.llm:
            result = self._plan_with_llm(question)
        else:
            result = self._plan_with_rules(question)
        
        # Log hasil
        if self.verbose:
            print(f"[DEBUG] Plan result: tool={result['tool']}, confidence={result['confidence']:.2f}")
            print(f"[DEBUG] Reasoning: {result['reasoning']}")
        
        # Update context
        if result['tool'] != 'none':
            self.context.set_tool(result['tool'])
        else:
            self.context.set_tool(None)
        
        self.context.set_state(AgentState.IDLE)
        
        return result

    def _plan_with_rules(self, question: str) -> Dict[str, Any]:
        """
        Planning berbasis aturan (rule-based)
        
        Args:
            question: Pertanyaan user
        
        Returns:
            Dict hasil planning
        """
        # STATUS: OK - Method berjalan normal
        question_lower = question.lower()
        
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

    def _plan_with_llm(self, question: str) -> Dict[str, Any]:
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
            return self._plan_with_rules(question)
        
        try:
            # Buat prompt
            tools_list = ', '.join([t for t in self.available_tools if t != 'none'])
            prompt = f"""Pertanyaan user: {question}

Tools yang tersedia: {tools_list}

Pilih tool yang paling sesuai untuk menjawab pertanyaan di atas.
Jika tidak perlu tool, jawab "none".

Format output: JSON
{{"tool": "nama_tool", "reasoning": "alasan singkat"}}

Pilihan tool:"""
            
            # Generate dengan LLM
            result = self.llm.generate(
                prompt=prompt,
                max_tokens=200,
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
                    if tool not in self.available_tools:
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
            for tool in self.available_tools:
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
            return self._plan_with_rules(question)

    def needs_tool(self, question: str) -> Tuple[bool, Optional[str]]:
        """
        Cek apakah pertanyaan membutuhkan tool
        
        Args:
            question: Pertanyaan user
        
        Returns:
            (needs_tool, tool_name)
        """
        # STATUS: OK - Method berjalan normal
        result = self.plan(question)
        tool = result.get('tool', 'none')
        
        needs = tool != 'none' and result.get('confidence', 0) > 0.3
        
        if self.verbose:
            print(f"[DEBUG] Needs tool? {needs} -> {tool if needs else 'none'}")
        
        return needs, tool if needs else None

    def add_tool(self, tool_name: str, patterns: List[str], keywords: List[str]) -> None:
        """
        Tambahkan tool baru ke planner
        
        Args:
            tool_name: Nama tool
            patterns: List regex pattern
            keywords: List keyword
        """
        # STATUS: OK - Method berjalan normal
        if tool_name not in self.available_tools:
            self.available_tools.append(tool_name)
        
        if patterns:
            self.tool_patterns[tool_name] = patterns
        
        if keywords:
            self.tool_keywords[tool_name] = keywords
        
        # Set prioritas default
        if tool_name not in self.tool_priority:
            self.tool_priority[tool_name] = 3
        
        if self.verbose:
            print(f"[DEBUG] Tool added: {tool_name}")

    def get_tool_capabilities(self, tool_name: str) -> Dict[str, Any]:
        """
        Ambil kemampuan tool
        
        Args:
            tool_name: Nama tool
        
        Returns:
            Dict kemampuan tool
        """
        # STATUS: OK - Method berjalan normal
        return {
            'name': tool_name,
            'patterns': self.tool_patterns.get(tool_name, []),
            'keywords': self.tool_keywords.get(tool_name, []),
            'priority': self.tool_priority.get(tool_name, 3)
        }

    def activate(self):
        """Aktifkan planner (mode tool)"""
        self.active = True
        if self.verbose:
            print("[DEBUG] Planner activated")

    def deactivate(self):
        """Nonaktifkan planner (mode chat biasa)"""
        self.active = False
        if self.verbose:
            print("[DEBUG] Planner deactivated")

    def is_active(self) -> bool:
        """Cek apakah planner aktif"""
        return self.active


# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING PLANNER")
    print("=" * 50)
    
    # Inisialisasi
    print("\n[TEST] Init Planner")
    context = ContextManager(verbose=False)
    planner = Planner(context, verbose=True)
    
    # Test cases
    test_questions = [
        # ("Apa cuaca di Jakarta hari ini?", "weather"),
        ("Baca file report.pdf", "filesystem"),
        ("Ingatkan saya tentang meeting", "database"),
        # ("Cari informasi tentang AI di Wikipedia", "wikipedia"),
        # ("Berita terbaru tentang Indonesia", "news"),
        # ("Halo, apa kabar?", "none"),
        # ("Convert 100 USD ke Rupiah", "currency"),
        # ("Terjemahkan 'hello' ke bahasa Indonesia", "translate"),
        ("Jalankan perintah ls -la", "shell"),
        ("Apa itu Python?", "none")
    ]
    
    print("\n[TEST] Planning tests")
    for question, expected in test_questions:
        result = planner.plan(question)
        status = "✓" if result['tool'] == expected else "✗"
        print(f"{status} Q: {question[:40]}...")
        print(f"   Tool: {result['tool']} (expected: {expected})")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Reasoning: {result['reasoning']}")
        print()
    
    # Test needs_tool
    print("\n[TEST] Needs tool tests")
    for question, _ in test_questions[:3]:
        needs, tool = planner.needs_tool(question)
        print(f"Q: {question[:30]}...")
        print(f"  Needs tool: {needs}, Tool: {tool}")
        print()
    
    # Test add tool
    print("\n[TEST] Add custom tool")
    planner.add_tool(
        "calculator",
        patterns=[r'hitung|kalkulasi|calculate|math'],
        keywords=['hitung', 'kalkulasi', 'math']
    )
    print(f"Tools available: {planner.available_tools}")
    
    # Test get capabilities
    print("\n[TEST] Get tool capabilities")
    caps = planner.get_tool_capabilities("weather")
    print(f"Weather capabilities: {caps}")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)