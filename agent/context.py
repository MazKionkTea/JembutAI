# agent/context.py
"""
Context Management - Mengelola state dan konteks percakapan agen
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AgentState(Enum):
    """Status agen"""
    IDLE = "idle"
    PROCESSING = "processing"
    PLANNING = "planning"
    EXECUTING = "executing"
    RESPONDING = "responding"
    WAITING = "waiting"
    ERROR = "error"


class ContextManager:
    """Manajemen konteks dan state agen"""
    
    def __init__(
        self,
        max_context_length: int = 4096,
        verbose: bool = False
    ):
        """
        Inisialisasi context manager
        
        Args:
            max_context_length: Maksimal panjang konteks (characters)
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.max_context_length = max_context_length
        self.verbose = verbose
        
        # State saat ini
        self.state = AgentState.IDLE
        self.current_question = ""
        self.current_tool = None
        self.current_tool_result = None
        
        # Konteks percakapan
        self.conversation_context = []
        self.system_context = {}
        self.user_context = {}
        
        # Metadata
        self.session_start = datetime.now()
        self.last_activity = datetime.now()
        self.total_interactions = 0
        
        # Error tracking
        self.last_error = None
        
        if self.verbose:
            print(f"[DEBUG] ContextManager initialized")
            print(f"[DEBUG] Max context length: {max_context_length}")

    def set_state(self, new_state: AgentState) -> None:
        """
        Ubah status agen
        
        Args:
            new_state: Status baru
        """
        # STATUS: OK - Method berjalan normal
        old_state = self.state
        self.state = new_state
        self.last_activity = datetime.now()
        
        if self.verbose:
            print(f"[DEBUG] State changed: {old_state.value} → {new_state.value}")

    def get_state(self) -> str:
        """
        Ambil status saat ini
        
        Returns:
            String status
        """
        # STATUS: OK - Method berjalan normal
        return self.state.value

    def is_ready(self) -> bool:
        """
        Cek apakah agen siap menerima perintah
        
        Returns:
            True jika siap
        """
        # STATUS: OK - Method berjalan normal
        return self.state in [AgentState.IDLE, AgentState.WAITING]

    def is_busy(self) -> bool:
        """
        Cek apakah agen sedang sibuk
        
        Returns:
            True jika sibuk
        """
        # STATUS: OK - Method berjalan normal
        return self.state not in [AgentState.IDLE, AgentState.WAITING, AgentState.ERROR]

    def set_question(self, question: str) -> None:
        """
        Set pertanyaan saat ini
        
        Args:
            question: Pertanyaan user
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not question or not isinstance(question, str):
            print("[ERROR] Question harus string tidak kosong")
            return
        
        self.current_question = question
        self.last_activity = datetime.now()
        self.total_interactions += 1
        
        if self.verbose:
            print(f"[DEBUG] Question set: {question[:50]}...")

    def set_tool(self, tool_name: str) -> None:
        """
        Set tool yang akan digunakan
        
        Args:
            tool_name: Nama tool
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not tool_name or not isinstance(tool_name, str):
            print("[ERROR] Tool name harus string tidak kosong")
            return
        
        self.current_tool = tool_name
        self.last_activity = datetime.now()
        
        if self.verbose:
            print(f"[DEBUG] Tool set: {tool_name}")

    def set_tool_result(self, result: Any) -> None:
        """
        Set hasil dari tool
        
        Args:
            result: Hasil tool (bisa string, dict, list, dll)
        """
        # STATUS: OK - Method berjalan normal
        self.current_tool_result = result
        self.last_activity = datetime.now()
        
        if self.verbose:
            result_preview = str(result)[:50] if result else "None"
            print(f"[DEBUG] Tool result set: {result_preview}...")

    def get_current_context(self) -> Dict[str, Any]:
        """
        Ambil konteks saat ini
        
        Returns:
            Dict dengan semua konteks
        """
        # STATUS: OK - Method berjalan normal
        return {
            'state': self.state.value,
            'question': self.current_question,
            'tool': self.current_tool,
            'tool_result': self.current_tool_result,
            'conversation': self.conversation_context[-10:],  # Last 10
            'system': self.system_context,
            'user': self.user_context,
            'interactions': self.total_interactions,
            'session_duration': str(datetime.now() - self.session_start),
            'last_activity': self.last_activity.isoformat()
        }

    def add_to_context(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Tambahkan pesan ke konteks percakapan
        
        Args:
            role: 'user', 'assistant', 'system', atau 'tool'
            content: Isi pesan
            metadata: Metadata tambahan
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if role not in ['user', 'assistant', 'system', 'tool']:
            print(f"[ERROR] Invalid role: {role}")
            return
        
        if not content or not isinstance(content, str):
            print("[ERROR] Content harus string tidak kosong")
            return
        
        # Buat entry
        entry = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        # Tambahkan ke konteks
        self.conversation_context.append(entry)
        
        # Batasi panjang konteks
        self._truncate_context()
        
        if self.verbose:
            print(f"[DEBUG] Added to context: {role} - {content[:30]}...")

    def get_recent_context(self, n: int = 5) -> List[Dict[str, Any]]:
        """
        Ambil N konteks terakhir
        
        Args:
            n: Jumlah konteks yang diambil
        
        Returns:
            List konteks terakhir
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not isinstance(n, int) or n < 1:
            print(f"[ERROR] n harus integer positif, mendapat: {n}")
            return []
        
        return self.conversation_context[-n:]

    def get_context_string(
        self,
        n: Optional[int] = None,
        include_system: bool = True
    ) -> str:
        """
        Ambil konteks dalam format string
        
        Args:
            n: Jumlah pesan terakhir (None = semua)
            include_system: Sertakan system context
        
        Returns:
            String konteks
        """
        # STATUS: OK - Method berjalan normal
        context_lines = []
        
        # System context
        if include_system and self.system_context:
            for key, value in self.system_context.items():
                context_lines.append(f"[System] {key}: {value}")
        
        # Conversation context
        context = self.conversation_context
        if n:
            context = context[-n:]
        
        for entry in context:
            role = entry['role'].capitalize()
            content = entry['content']
            context_lines.append(f"{role}: {content}")
        
        return "\n".join(context_lines)

    def set_system_context(self, key: str, value: Any) -> None:
        """
        Set system context
        
        Args:
            key: Key konteks
            value: Value konteks
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not key or not isinstance(key, str):
            print("[ERROR] Key harus string tidak kosong")
            return
        
        self.system_context[key] = value
        self.last_activity = datetime.now()
        
        if self.verbose:
            print(f"[DEBUG] System context set: {key} = {str(value)[:30]}...")

    def get_system_context(self, key: str) -> Any:
        """
        Ambil system context
        
        Args:
            key: Key konteks
        
        Returns:
            Value konteks, None jika tidak ada
        """
        # STATUS: OK - Method berjalan normal
        return self.system_context.get(key)

    def set_user_context(self, key: str, value: Any) -> None:
        """
        Set user context
        
        Args:
            key: Key konteks
            value: Value konteks
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not key or not isinstance(key, str):
            print("[ERROR] Key harus string tidak kosong")
            return
        
        self.user_context[key] = value
        self.last_activity = datetime.now()
        
        if self.verbose:
            print(f"[DEBUG] User context set: {key} = {str(value)[:30]}...")

    def get_user_context(self, key: str) -> Any:
        """
        Ambil user context
        
        Args:
            key: Key konteks
        
        Returns:
            Value konteks, None jika tidak ada
        """
        # STATUS: OK - Method berjalan normal
        return self.user_context.get(key)

    def set_error(self, error: str) -> None:
        """
        Set error dan ubah state ke ERROR
        
        Args:
            error: Pesan error
        """
        # STATUS: OK - Method berjalan normal
        self.last_error = error
        self.state = AgentState.ERROR
        self.last_activity = datetime.now()
        
        print(f"[ERROR] Context error: {error}")

    def clear_error(self) -> None:
        """Hapus error dan reset state ke IDLE"""
        # STATUS: OK - Method berjalan normal
        self.last_error = None
        self.state = AgentState.IDLE
        self.last_activity = datetime.now()
        
        if self.verbose:
            print("[DEBUG] Error cleared, state reset to IDLE")

    def clear_context(self) -> None:
        """Hapus semua konteks percakapan (tapi pertahankan system context)"""
        # STATUS: OK - Method berjalan normal
        self.conversation_context = []
        self.current_question = ""
        self.current_tool = None
        self.current_tool_result = None
        self.total_interactions = 0
        self.last_activity = datetime.now()
        
        if self.verbose:
            print("[DEBUG] Conversation context cleared")

    def reset(self) -> None:
        """Reset semua konteks (termasuk system dan user)"""
        # STATUS: OK - Method berjalan normal
        self.conversation_context = []
        self.system_context = {}
        self.user_context = {}
        self.current_question = ""
        self.current_tool = None
        self.current_tool_result = None
        self.total_interactions = 0
        self.last_error = None
        self.state = AgentState.IDLE
        self.session_start = datetime.now()
        self.last_activity = datetime.now()
        
        if self.verbose:
            print("[DEBUG] All context reset")

    def _truncate_context(self) -> None:
        """Potong konteks jika melebihi batas"""
        # STATUS: OK - Method berjalan normal
        # Hitung total panjang konteks
        total_length = 0
        for entry in self.conversation_context:
            total_length += len(entry['content'])
        
        # Jika melebihi batas, hapus dari awal
        if total_length > self.max_context_length:
            removed = 0
            while total_length > self.max_context_length and self.conversation_context:
                removed_entry = self.conversation_context.pop(0)
                total_length -= len(removed_entry['content'])
                removed += 1
            
            if self.verbose:
                print(f"[DEBUG] Truncated context: removed {removed} entries")

    def get_stats(self) -> Dict[str, Any]:
        """
        Ambil statistik context
        
        Returns:
            Dict statistik
        """
        # STATUS: OK - Method berjalan normal
        return {
            'state': self.state.value,
            'total_interactions': self.total_interactions,
            'context_entries': len(self.conversation_context),
            'context_length': sum(len(e['content']) for e in self.conversation_context),
            'system_context_keys': list(self.system_context.keys()),
            'user_context_keys': list(self.user_context.keys()),
            'session_duration': str(datetime.now() - self.session_start),
            'has_error': self.last_error is not None,
            'last_error': self.last_error,
            'is_ready': self.is_ready(),
            'is_busy': self.is_busy()
        }


# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING CONTEXT MANAGER")
    print("=" * 50)
    
    # Inisialisasi
    print("\n[TEST] Init ContextManager")
    context = ContextManager(verbose=True)
    
    # Test state
    print("\n[TEST] State management")
    print(f"Initial state: {context.get_state()}")
    context.set_state(AgentState.PLANNING)
    print(f"State after set: {context.get_state()}")
    print(f"Is ready? {context.is_ready()}")
    print(f"Is busy? {context.is_busy()}")
    
    # Test set question
    print("\n[TEST] Set question")
    context.set_question("Apa cuaca hari ini?")
    
    # Test set tool
    print("\n[TEST] Set tool")
    context.set_tool("weather")
    context.set_tool_result("Jakarta: 32°C, Cerah")
    
    # Test add to context
    print("\n[TEST] Add to context")
    context.add_to_context("user", "Apa cuaca hari ini?")
    context.add_to_context("assistant", "Saya akan cek cuaca")
    context.add_to_context("tool", "weather result: 32°C, Cerah")
    context.add_to_context("assistant", "Cuaca hari ini cerah dengan suhu 32°C")
    
    # Test get recent context
    print("\n[TEST] Get recent context")
    recent = context.get_recent_context(2)
    for entry in recent:
        print(f"  {entry['role']}: {entry['content']}")
    
    # Test get context string
    print("\n[TEST] Get context string")
    context_str = context.get_context_string(n=3)
    print(f"Context string:\n{context_str}")
    
    # Test system context
    print("\n[TEST] System context")
    context.set_system_context("user_name", "Budi")
    context.set_system_context("language", "Indonesia")
    print(f"System context: {context.system_context}")
    
    # Test user context
    print("\n[TEST] User context")
    context.set_user_context("preference", "informal")
    print(f"User context: {context.user_context}")
    
    # Test error
    print("\n[TEST] Error handling")
    context.set_error("Model not responding")
    print(f"State after error: {context.get_state()}")
    context.clear_error()
    print(f"State after clear: {context.get_state()}")
    
    # Test stats
    print("\n[TEST] Get stats")
    stats = context.get_stats()
    print(f"Stats: {stats}")
    
    # Test clear
    print("\n[TEST] Clear context")
    context.clear_context()
    print(f"Context entries after clear: {len(context.conversation_context)}")
    
    # Test reset
    print("\n[TEST] Reset all")
    context.reset()
    print(f"State after reset: {context.get_state()}")
    print(f"System context after reset: {context.system_context}")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)