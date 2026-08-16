# agent/context.py
"""
Context Management - Mengelola state dan konteks percakapan agen
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class StatusAgen(Enum):
    """Status agen"""
    IDLE = "idle"
    PROCESSING = "processing"
    PLANNING = "planning"
    EXECUTING = "executing"
    RESPONDING = "responding"
    WAITING = "waiting"
    ERROR = "error"


class PengelolaKonteks:
    """Manajemen konteks dan state agen"""
    
    def __init__(
        self,
        panjang_konteks_maksimal: int = 10000,
        verbose: bool = False
    ):
        """
        Inisialisasi context manager
        
        Args:
            max_context_length: Maksimal panjang konteks (characters)
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.panjang_konteks_maksimal = panjang_konteks_maksimal
        self.verbose = verbose
        
        # State saat ini
        self.status = StatusAgen.IDLE
        self.pertanyaan_saat_ini = ""
        self.tool_saat_ini = None
        self.hasil_tool_saat_ini = None
        
        # Konteks percakapan
        self.konteks_percakapan = []
        self.konteks_sistem = {}
        self.konteks_dari_pengguna = {}
        
        # Metadata
        self.sesi_mulai = datetime.now()
        self.aktivitas_terakhir = datetime.now()
        self.total_interaksi = 0
        
        # Error tracking
        self.last_error = None
        
        if self.verbose:
            print(f"[DEBUG] ContextManager initialized")
            print(f"[DEBUG] Max context length: {panjang_konteks_maksimal}")

    def status_konteks_agen(self, status_baru: StatusAgen) -> None:
        """
        Ubah status agen
        
        Args:
            new_state: Status baru
        """
        # STATUS: OK - Method berjalan normal
        status_lama = self.status
        self.status = status_baru
        self.aktivitas_terakhir = datetime.now()
        
        if self.verbose:
            print(f"[DEBUG] State changed: {status_lama.value} → {status_baru.value}")

    def agen_siap(self) -> bool:
        """
        Cek apakah agen siap menerima perintah 
        Returns:
            True jika siap
        """
        # STATUS: OK - Method berjalan normal
        return self.status in [StatusAgen.IDLE, StatusAgen.WAITING]

    def agen_sibuk(self) -> bool:
        """
        Cek apakah agen sedang sibuk
        Returns:
            True jika sibuk
        """
        # STATUS: OK - Method berjalan normal
        return self.status not in [StatusAgen.IDLE, StatusAgen.WAITING, StatusAgen.ERROR]

    def pertanyaan_pengguna(self, pertanyaan: str) -> None:
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not pertanyaan or not isinstance(pertanyaan, str):
            print("[ERROR] Question harus string tidak kosong")
            return
        
        self.pertanyaan_saat_ini = pertanyaan
        self.aktivitas_terakhir = datetime.now()
        self.total_interaksi += 1
        
        if self.verbose:
            print(f"[DEBUG] Question set: {pertanyaan[:50]}...")

    def tool_yang_digunakan(self, nama_tool: str) -> None:
        """
        Set tool yang akan digunakan
        
        Args:
            tool_name: Nama tool
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not nama_tool or not isinstance(nama_tool, str):
            print("[ERROR] Tool name harus string tidak kosong")
            return
        
        self.tool_saat_ini = nama_tool
        self.aktivitas_terakhir = datetime.now()
        
        if self.verbose:
            print(f"[DEBUG] Tool set: {nama_tool}")


    def hasil_tool_yang_digunakan(self, hasil: Any) -> None:
        """
        Set hasil dari tool
        Args:
            result: Hasil tool (bisa string, dict, list, dll)
        """
        # STATUS: OK - Method berjalan normal
        self.hasil_tool_saat_ini = hasil
        self.aktivitas_terakhir = datetime.now()
        
        if self.verbose:
            preview_hasil = str(hasil)[:50] if hasil else "None"
            print(f"[DEBUG] Tool result set: {preview_hasil}...")


    def ambil_konteks_saat_ini(self) -> Dict[str, Any]:
        """
        Ambil konteks saat ini
        Returns:
            Dict dengan semua konteks
        """
        # STATUS: OK - Method berjalan normal
        return {
            'state': self.status.value,
            'question': self.pertanyaan_saat_ini,
            'tool': self.tool_saat_ini,
            'tool_result': self.hasil_tool_saat_ini,
            'conversation': self.konteks_percakapan[-10:],  # Last 10
            'system': self.konteks_sistem,
            'user': self.konteks_dari_pengguna,
            'interactions': self.total_interaksi,
            'session_duration': str(datetime.now() - self.sesi_mulai),
            'last_activity': self.aktivitas_terakhir.isoformat()
        }

    def tambahkan_ke_konteks(
        self,
        role: str,
        isi_pesan: str,
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
        
        if not isi_pesan or not isinstance(isi_pesan, str):
            print("[ERROR] Content harus string tidak kosong")
            return
        
        # Buat entry
        entry = {
            'role': role,
            'content': isi_pesan,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        # Tambahkan ke konteks
        self.konteks_percakapan.append(entry)
        
        # Batasi panjang konteks
        self.potong_konteks()
        
        if self.verbose:
            print(f"[DEBUG] Added to context: {role} - {isi_pesan[:30]}...")


    def ambil_konteks_terakhir(self, n: int = 5) -> List[Dict[str, Any]]:
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
        
        return self.konteks_percakapan[-n:]

    def ambil_konteks_saat_ini_string(
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
        if include_system and self.konteks_sistem:
            for key, value in self.konteks_sistem.items():
                context_lines.append(f"[System] {key}: {value}")
        
        # Conversation context
        konteks = self.konteks_percakapan
        if n:
            konteks = konteks[-n:]
        
        for entry in konteks:
            role = entry['role'].capitalize()
            isi_pesan = entry['content']
            context_lines.append(f"{role}: {isi_pesan}")
        
        return "\n".join(context_lines)

    def konteks_sistem_yang_disiapkan(self, key: str, value: Any) -> None:
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
        
        self.konteks_sistem[key] = value
        self.aktivitas_terakhir = datetime.now()
        
        if self.verbose:
            print(f"[DEBUG] System context set: {key} = {str(value)[:30]}...")

    def ambil_konteks_sistem_yang_disiapkan(self, key: str) -> Any:
        """
        Ambil system context
        Args:
            key: Key konteks
        Returns:
            Value konteks, None jika tidak ada
        """
        # STATUS: OK - Method berjalan normal
        return self.konteks_sistem.get(key)

    def siapkan_konteks_dari_pengguna(self, key: str, value: Any) -> None:
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
        
        self.konteks_dari_pengguna[key] = value
        self.aktivitas_terakhir = datetime.now()
        
        if self.verbose:
            print(f"[DEBUG] User context set: {key} = {str(value)[:30]}...")


    def ambil_konteks_dari_pengguna(self, key: str) -> Any:
        """
        Ambil user context
        Args:
            key: Key konteks
        Returns:
            Value konteks, None jika tidak ada
        """
        # STATUS: OK - Method berjalan normal
        return self.konteks_dari_pengguna.get(key)


    def pesan_error(self, error: str) -> None:
        """
        Set error dan ubah state ke ERROR
        Args:
            error: Pesan error
        """
        # STATUS: OK - Method berjalan normal
        self.last_error = error
        self.status = StatusAgen.ERROR
        self.aktivitas_terakhir = datetime.now()
        
        print(f"[ERROR] Context error: {error}")


    def hapus_pesan_error(self) -> None:
        """Hapus error dan reset state ke IDLE"""
        # STATUS: OK - Method berjalan normal
        self.last_error = None
        self.status = StatusAgen.IDLE
        self.aktivitas_terakhir = datetime.now()
        
        if self.verbose:
            print("[DEBUG] Error cleared, state reset to IDLE")


    def bersihkan_konteks(self) -> None:
        """Hapus semua konteks percakapan (tapi pertahankan system context)"""
        # STATUS: OK - Method berjalan normal
        self.konteks_percakapan = []
        self.pertanyaan_saat_ini = ""
        self.tool_saat_ini = None
        self.hasil_tool_saat_ini = None
        self.total_interaksi = 0
        self.aktivitas_terakhir = datetime.now()
        
        if self.verbose:
            print("[DEBUG] Conversation context cleared")


    def reset(self) -> None:
        """Reset semua konteks (termasuk system dan user)"""
        # STATUS: OK - Method berjalan normal
        self.konteks_percakapan = []
        self.konteks_sistem = {}
        self.konteks_dari_pengguna = {}
        self.pertanyaan_saat_ini = ""
        self.tool_saat_ini = None
        self.hasil_tool_saat_ini = None
        self.total_interaksi = 0
        self.last_error = None
        self.status = StatusAgen.IDLE
        self.sesi_mulai = datetime.now()
        self.aktivitas_terakhir = datetime.now()
        
        if self.verbose:
            print("[DEBUG] All context reset")


    def potong_konteks(self) -> None:
        """Potong konteks jika melebihi batas"""
        # STATUS: OK - Method berjalan normal
        # Hitung total panjang konteks
        total_length = 0
        for entry in self.konteks_percakapan:
            total_length += len(entry['content'])
        
        # Jika melebihi batas, hapus dari awal
        if total_length > self.panjang_konteks_maksimal:
            removed = 0
            while total_length > self.panjang_konteks_maksimal and self.konteks_percakapan:
                removed_entry = self.konteks_percakapan.pop(0)
                total_length -= len(removed_entry['content'])
                removed += 1
            
            if self.verbose:
                print(f"[DEBUG] Truncated context: removed {removed} entries")


    def status_konteks_terakhir(self) -> Dict[str, Any]:
        """
        Ambil statistik context
        Returns:
            Dict statistik
        """
        # STATUS: OK - Method berjalan normal
        return {
            'state': self.status.value,
            'total_interactions': self.total_interaksi,
            'context_entries': len(self.konteks_percakapan),
            'context_length': sum(len(e['content']) for e in self.konteks_percakapan),
            'system_context_keys': list(self.konteks_sistem.keys()),
            'user_context_keys': list(self.konteks_dari_pengguna.keys()),
            'session_duration': str(datetime.now() - self.sesi_mulai),
            'has_error': self.last_error is not None,
            'last_error': self.last_error,
            'is_ready': self.agen_siap(),
            'is_busy': self.agen_sibuk()
        }


# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING CONTEXT MANAGER")
    print("=" * 50)
    
    # Inisialisasi
    print("\n[TEST] Init ContextManager")
    konteks = PengelolaKonteks(verbose=True)
    
    # Test state
    print("\n[TEST] State management")
    print(f"Initial state: {konteks.status_konteks_terakhir()}")
    konteks.status_konteks_agen(StatusAgen.PLANNING)
    print(f"State after set: {konteks.status_konteks_terakhir()}")
    print(f"Is ready? {konteks.agen_siap()}")
    print(f"Is busy? {konteks.agen_sibuk()}")
    
    # Test set question
    print("\n[TEST] Set question")
    konteks.pertanyaan_pengguna("Apa cuaca hari ini?")
    
    # Test set tool
    print("\n[TEST] Set tool")
    konteks.tool_yang_digunakan("weather")
    konteks.hasil_tool_yang_digunakan("Jakarta: 32°C, Cerah")
    
    # Test add to context
    print("\n[TEST] Add to context")
    konteks.tambahkan_ke_konteks("user", "Apa cuaca hari ini?")
    konteks.tambahkan_ke_konteks("assistant", "Saya akan cek cuaca")
    konteks.tambahkan_ke_konteks("tool", "weather result: 32°C, Cerah")
    konteks.tambahkan_ke_konteks("assistant", "Cuaca hari ini cerah dengan suhu 32°C")
    
    # Test get recent context
    print("\n[TEST] Get recent context")
    recent = konteks.ambil_konteks_terakhir(2)
    for entry in recent:
        print(f"  {entry['role']}: {entry['content']}")
    
    # Test get context string
    print("\n[TEST] Get context string")
    context_str = konteks.ambil_konteks_saat_ini_string(n=3)
    print(f"Context string:\n{context_str}")
    
    # Test system context
    print("\n[TEST] System context")
    konteks.konteks_sistem_yang_disiapkan("user_name", "Budi")
    konteks.konteks_sistem_yang_disiapkan("language", "Indonesia")
    print(f"System context: {konteks.konteks_sistem}")
    
    # Test user context
    print("\n[TEST] User context")
    konteks.siapkan_konteks_dari_pengguna("preference", "informal")
    print(f"User context: {konteks.konteks_dari_pengguna}")
    
    # Test error
    print("\n[TEST] Error handling")
    konteks.pesan_error("Model not responding")
    print(f"State after error: {konteks.status_konteks_terakhir()}")
    konteks.hapus_pesan_error()
    print(f"State after clear: {konteks.status_konteks_terakhir()}")
    
    # Test stats
    print("\n[TEST] Get stats")
    stats = konteks.status_konteks_terakhir()
    print(f"Stats: {stats}")
    
    # Test clear
    print("\n[TEST] Clear context")
    konteks.bersihkan_konteks()
    print(f"Context entries after clear: {len(konteks.konteks_percakapan)}")
    
    # Test reset
    print("\n[TEST] Reset all")
    konteks.reset()
    print(f"State after reset: {konteks.status_konteks_terakhir()}")
    print(f"System context after reset: {konteks.konteks_sistem}")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)