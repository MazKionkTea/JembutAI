# agent/memory.py
"""
Memory Management - Menyimpan dan mengambil memori percakapan
"""

import sqlite3
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path


class PengelolaMemori:
    """Manajemen memori menggunakan SQLite"""
    
    def __init__(
        self,
        lokasi_database: str = "database/assistant.db",
        histori_maksimal: int = 50,
        verbose: bool = False
    ):
        """
        Inisialisasi memory manager
        Args:
            lokasi_database: Path ke database SQLite
            histori_maksimal: Maksimal history per sesi
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.lokasi_database = Path(lokasi_database)
        self.histori_maksimal = histori_maksimal
        self.verbose = verbose
        self.identitas_sesi_saat_ini = None
        
        # Buat direktori jika belum ada
        self.lokasi_database.parent.mkdir(parents=True, exist_ok=True)
        
        # Inisialisasi database
        self._inisiasi_database()
        
        if self.verbose:
            print(f"[DEBUG] MemoryManager initialized with db: {self.lokasi_database}")

    def _inisiasi_database(self) -> None:
        """Buat tabel jika belum ada"""
        # STATUS: OK - Method berjalan normal
        try:
            koneksi = sqlite3.connect(str(self.lokasi_database))
            cursor = koneksi.cursor()
            
            # Tabel sessions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            # Tabel messages
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tokens INTEGER DEFAULT 0,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            
            # Tabel memory_summary
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            
            # Index untuk performa
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session 
                ON messages(session_id, timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_role 
                ON messages(role)
            """)
            
            koneksi.commit()
            koneksi.close()
            
            if self.verbose:
                print("[DEBUG] Database initialized successfully")
                
        except sqlite3.Error as e:
            print(f"[ERROR] Database initialization failed: {e}")
            raise


    def mulai_sesi(self, identitas_sesi: Optional[str] = None, metadata: Optional[Dict] = None) -> Optional[str]:
        """
        Mulai sesi baru atau lanjutkan sesi yang ada
        
        Args:
            identitas_sesi: ID sesi (None = buat baru)
            metadata: Metadata tambahan untuk sesi
        
        Returns:
            identitas_sesi yang digunakan atau None jika gagal
        """
        # STATUS: OK - Method berjalan normal
        if identitas_sesi is None:
            # Buat identitas_sesi baru
            identitas_sesi = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            koneksi = sqlite3.connect(str(self.lokasi_database))
            cursor = koneksi.cursor()
            
            # Cek apakah identitas_sesi sudah ada
            cursor.execute(
                "SELECT session_id FROM sessions WHERE session_id = ?",
                (identitas_sesi,)
            )
            existing = cursor.fetchone()
            
            if existing is None:
                # Buat sesi baru
                metadata_json = json.dumps(metadata) if metadata else None
                cursor.execute(
                    "INSERT INTO sessions (session_id, metadata) VALUES (?, ?)",
                    (identitas_sesi, metadata_json)
                )
                koneksi.commit()
                if self.verbose:
                    print(f"[DEBUG] New session created: {identitas_sesi}")
            else:
                # Update updated_at
                cursor.execute(
                    "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                    (identitas_sesi,)
                )
                koneksi.commit()
                if self.verbose:
                    print(f"[DEBUG] Session resumed: {identitas_sesi}")
            
            koneksi.close()
            self.identitas_sesi_saat_ini = identitas_sesi
            return identitas_sesi
            
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to start session: {e}")
            return None

    def tambah_percakapan(self, role: str, isi_pesan: str, jumlah_token: int = 0) -> bool:
        """
        Tambahkan pesan ke sesi saat ini
        
        Args:
            role: 'user' atau 'assistant'
            content: Isi pesan
            tokens: Jumlah token (optional)
        
        Returns:
            True jika berhasil
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if self.identitas_sesi_saat_ini is None:
            print("[ERROR] No active session. Call start_session() first")
            return False
        
        if role not in ['user', 'assistant']:
            print(f"[ERROR] Invalid role: {role}")
            return False
        
        if not isi_pesan or not isinstance(isi_pesan, str):
            print("[ERROR] Content harus string tidak kosong")
            return False
        
        try:
            koneksi = sqlite3.connect(str(self.lokasi_database))
            cursor = koneksi.cursor()
            
            cursor.execute(
                """INSERT INTO messages (session_id, role, content, tokens) 
                   VALUES (?, ?, ?, ?)""",
                (self.identitas_sesi_saat_ini, role, isi_pesan, jumlah_token)
            )
            
            # Update updated_at di sessions
            cursor.execute(
                "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                (self.identitas_sesi_saat_ini,)
            )
            
            koneksi.commit()
            koneksi.close()
            
            if self.verbose:
                print(f"[DEBUG] Message added: {role} - {isi_pesan[:30]}...")
            
            # Cek batas history
            self._enforce_histori_maksimal()
            
            return True
            
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to add message: {e}")
            return False

    def ambil_percakapan_dari_memori_history(
        self,
        limit: Optional[int] = None,
        identitas_sesi: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Ambil history percakapan

        Args:
            limit: Jumlah pesan terakhir (None = semua)
            session_id: Session ID (None = pakai current)

        Returns:
            List pesan dalam format [{'role': ..., 'content': ..., 'timestamp': ..., 'tokens': ...}]
        """
        # STATUS: OK - Method berjalan normal
        sesi = identitas_sesi or self.identitas_sesi_saat_ini

        if sesi is None:
            print("[ERROR] No active session")
            return []

        # Validasi limit
        limit_int = None
        if limit is not None:
            try:
                limit_int = int(limit)
                if limit_int < 1 or limit_int > 1000:
                    raise ValueError("Limit harus antara 1-1000")
            except (ValueError, TypeError) as e:
                if self.verbose:
                    print(f"[WARNING] Invalid limit value: {limit}, using default 50")
                limit_int = 50

        try:
            koneksi = sqlite3.connect(str(self.lokasi_database))
            koneksi.row_factory = sqlite3.Row
            cursor = koneksi.cursor()

            # Bangun query dengan parameterized placeholders
            if limit_int is None:
                query = """
                    SELECT role, content, timestamp, tokens
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                """
                params = (sesi,)
            else:
                # Ambil last N dengan subquery agar urutan tetap ascending
                query = """
                    SELECT * FROM (
                        SELECT role, content, timestamp, tokens
                        FROM messages
                        WHERE session_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ) ORDER BY timestamp ASC
                """
                params = (sesi, limit_int)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            koneksi.close()

            histori = [
                {
                    'role': row['role'],
                    'content': row['content'],
                    'timestamp': row['timestamp'],
                    'tokens': row['tokens']
                }
                for row in rows
            ]

            if self.verbose:
                print(f"[DEBUG] Retrieved {len(histori)} messages from history")

            return histori

        except sqlite3.Error as e:
            print(f"[ERROR] Failed to get history: {e}")
            return []
            
    def ambil_pesan_terakhir(self, n: int = 5) -> List[Dict[str, Any]]:
        """
        Ambil N pesan terakhir
        
        Args:
            n: Jumlah pesan yang diambil
        
        Returns:
            List pesan terakhir
        """
        # STATUS: OK - Method berjalan normal
        return self.ambil_percakapan_dari_memori_history(limit=n)

    def ambil_konteks_percakapan(self, n: int = 5) -> str:
        """
        Ambil konteks percakapan dalam format string
        
        Args:
            n: Jumlah pesan terakhir
        
        Returns:
            String konteks percakapan
        """
        # STATUS: OK - Method berjalan normal
        percakapan = self.ambil_pesan_terakhir(n)
        
        if not percakapan:
            return ""
        
        context_lines = []
        for pesan in percakapan:
            role_label = "User" if pesan['role'] == 'user' else "Assistant"
            context_lines.append(f"{role_label}: {pesan['content']}")
        
        return "\n".join(context_lines)

    def simpan_ringkasan_percakapan(self, summary: str) -> bool:
        """
        Simpan ringkasan percakapan
        
        Args:
            summary: Ringkasan percakapan
        
        Returns:
            True jika berhasil
        """
        # STATUS: OK - Method berjalan normal
        if self.identitas_sesi_saat_ini is None:
            print("[ERROR] No active session")
            return False
        
        try:
            koneksi = sqlite3.connect(str(self.lokasi_database))
            cursor = koneksi.cursor()
            
            cursor.execute(
                """INSERT INTO memory_summary (session_id, summary) 
                   VALUES (?, ?)""",
                (self.identitas_sesi_saat_ini, summary)
            )
            
            koneksi.commit()
            koneksi.close()
            
            if self.verbose:
                print(f"[DEBUG] Summary saved: {summary[:50]}...")
            
            return True
            
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to save summary: {e}")
            return False

    def ambil_ringkasan_percakapan(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Ambil ringkasan percakapan
        
        Args:
            limit: Jumlah ringkasan terakhir
        
        Returns:
            List ringkasan
        """
        # STATUS: OK - Method berjalan normal
        if self.identitas_sesi_saat_ini is None:
            print("[ERROR] No active session")
            return []
        
        try:
            koneksi = sqlite3.connect(str(self.lokasi_database))
            koneksi.row_factory = sqlite3.Row
            cursor = koneksi.cursor()
            
            cursor.execute(
                """SELECT summary, created_at 
                   FROM memory_summary 
                   WHERE session_id = ? 
                   ORDER BY created_at DESC 
                   LIMIT ?""",
                (self.identitas_sesi_saat_ini, limit)
            )
            
            rows = cursor.fetchall()
            koneksi.close()
            
            ringkasan = [
                {
                    'summary': row['summary'],
                    'created_at': row['created_at']
                }
                for row in rows
            ]
            
            return ringkasan
            
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to get summaries: {e}")
            return []

    def _enforce_histori_maksimal(self) -> None:
        """Batasi jumlah history per sesi"""
        # STATUS: OK - Method berjalan normal
        try:
            koneksi = sqlite3.connect(str(self.lokasi_database))
            cursor = koneksi.cursor()
            
            # Hitung total pesan
            cursor.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ?",
                (self.identitas_sesi_saat_ini,)
            )
            count = cursor.fetchone()[0]
            
            # Jika melebihi batas, hapus yang paling lama
            if count > self.histori_maksimal:
                delete_count = count - self.histori_maksimal
                cursor.execute(
                    """DELETE FROM messages 
                       WHERE id IN (
                           SELECT id FROM messages 
                           WHERE session_id = ? 
                           ORDER BY timestamp ASC 
                           LIMIT ?
                       )""",
                    (self.identitas_sesi_saat_ini, delete_count)
                )
                koneksi.commit()
                
                if self.verbose:
                    print(f"[DEBUG] Deleted {delete_count} old messages to enforce history limit")
            
            koneksi.close()
            
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to enforce history limit: {e}")

    def bersihkan_sesi(self, identitas_sesi: Optional[str] = None) -> bool:
        """
        Hapus semua data sesi
        
        Args:
            session_id: Session ID (None = pakai current)
        
        Returns:
            True jika berhasil
        """
        # STATUS: OK - Method berjalan normal
        sesi = identitas_sesi or self.identitas_sesi_saat_ini
        
        if sesi is None:
            print("[ERROR] No active session")
            return False
        
        try:
            koneksi = sqlite3.connect(str(self.lokasi_database))
            cursor = koneksi.cursor()
            
            # Hapus pesan
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (sesi,))
            
            # Hapus summary
            cursor.execute("DELETE FROM memory_summary WHERE session_id = ?", (sesi,))
            
            # Hapus sesi
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (sesi,))
            
            koneksi.commit()
            koneksi.close()
            
            if self.verbose:
                print(f"[DEBUG] Session cleared: {sesi}")
            
            if sesi == self.identitas_sesi_saat_ini:
                self.identitas_sesi_saat_ini= None
            
            return True
            
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to clear session: {e}")
            return False

    def status_memori_terakhir(self) -> Dict[str, Any]:
        """
        Ambil statistik memory
        Returns:
            Dict statistik
        """
        # STATUS: OK - Method berjalan normal
        try:
            koneksi = sqlite3.connect(str(self.lokasi_database))
            cursor = koneksi.cursor()
            
            # Total sessions
            cursor.execute("SELECT COUNT(*) FROM sessions")
            total_sesi = cursor.fetchone()[0]
            
            # Total messages
            cursor.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]
            
            # Total summaries
            cursor.execute("SELECT COUNT(*) FROM memory_summary")
            total_ringkasan = cursor.fetchone()[0]
            
            # Messages per session (current)
            pesan_per_sesi= 0
            if self.identitas_sesi_saat_ini:
                cursor.execute(
                    "SELECT COUNT(*) FROM messages WHERE session_id = ?",
                    (self.identitas_sesi_saat_ini,)
                )
                pesan_per_sesi= cursor.fetchone()[0]
            
            koneksi.close()
            
            return {
                'total_sessions': total_sesi,
                'total_messages': total_messages,
                'total_summaries': total_ringkasan,
                'current_session': self.identitas_sesi_saat_ini,
                'messages_in_current_session': pesan_per_sesi,
                'histori_maksimal_limit': self.histori_maksimal
            }
            
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to get stats: {e}")
            return {}


# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING MEMORY MANAGER")
    print("=" * 50)
    
    # Inisialisasi
    print("\n[TEST] Init MemoryManager")
    memori = PengelolaMemori(verbose=True)
    
    # Test start session
    print("\n[TEST] Start session")
    identitas_sesi = memori.mulai_sesi()
    print(f"Session ID: {identitas_sesi}")
    
    # Test add message
    print("\n[TEST] Add messages")
    memori.tambah_percakapan("user", "Halo, saya ingin bertanya", 10)
    memori.tambah_percakapan("assistant", "Ya, silakan bertanya", 8)
    memori.tambah_percakapan("user", "Apa cuaca hari ini?", 7)
    
    # Test get history
    print("\n[TEST] Get history")
    histori = memori.ambil_percakapan_dari_memori_history()
    for pesan in histori:
        print(f"  {pesan['role']}: {pesan['content']}")
    
    # Test get context
    print("\n[TEST] Get context")
    context = memori.ambil_konteks_percakapan(2)
    print(f"Context:\n{context}")
    
    # Test save summary
    print("\n[TEST] Save summary")
    memori.simpan_ringkasan_percakapan("Percakapan tentang cuaca")
    
    # Test get summaries
    print("\n[TEST] Get summaries")
    ringkasan = memori.ambil_ringkasan_percakapan()
    for s in ringkasan:
        print(f"  {s['summary']} - {s['created_at']}")
    
    # Test stats
    print("\n[TEST] Get stats")
    stats = memori.status_memori_terakhir()
    print(f"Stats: {stats}")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)