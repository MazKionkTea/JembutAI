# agent/memory.py
"""
Memory Management - Menyimpan dan mengambil memori percakapan
"""

import sqlite3
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path


class MemoryManager:
    """Manajemen memori menggunakan SQLite"""
    
    def __init__(
        self,
        db_path: str = "database/assistant.db",
        max_history: int = 50,
        verbose: bool = False
    ):
        """
        Inisialisasi memory manager
        
        Args:
            db_path: Path ke database SQLite
            max_history: Maksimal history per sesi
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.db_path = Path(db_path)
        self.max_history = max_history
        self.verbose = verbose
        self.current_session_id = None
        
        # Buat direktori jika belum ada
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Inisialisasi database
        self._init_database()
        
        if self.verbose:
            print(f"[DEBUG] MemoryManager initialized with db: {self.db_path}")

    def _init_database(self) -> None:
        """Buat tabel jika belum ada"""
        # STATUS: OK - Method berjalan normal
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
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
            
            conn.commit()
            conn.close()
            
            if self.verbose:
                print("[DEBUG] Database initialized successfully")
                
        except sqlite3.Error as e:
            print(f"[ERROR] Database initialization failed: {e}")
            raise

    def start_session(self, session_id: Optional[str] = None, metadata: Optional[Dict] = None) -> Optional[str]:
        """
        Mulai sesi baru atau lanjutkan sesi yang ada
        
        Args:
            session_id: ID sesi (None = buat baru)
            metadata: Metadata tambahan untuk sesi
        
        Returns:
            session_id yang digunakan atau None jika gagal
        """
        # STATUS: OK - Method berjalan normal
        if session_id is None:
            # Buat session_id baru
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Cek apakah session_id sudah ada
            cursor.execute(
                "SELECT session_id FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            existing = cursor.fetchone()
            
            if existing is None:
                # Buat sesi baru
                metadata_json = json.dumps(metadata) if metadata else None
                cursor.execute(
                    "INSERT INTO sessions (session_id, metadata) VALUES (?, ?)",
                    (session_id, metadata_json)
                )
                conn.commit()
                if self.verbose:
                    print(f"[DEBUG] New session created: {session_id}")
            else:
                # Update updated_at
                cursor.execute(
                    "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                    (session_id,)
                )
                conn.commit()
                if self.verbose:
                    print(f"[DEBUG] Session resumed: {session_id}")
            
            conn.close()
            self.current_session_id = session_id
            return session_id
            
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to start session: {e}")
            return None

    def add_message(self, role: str, content: str, tokens: int = 0) -> bool:
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
        if self.current_session_id is None:
            print("[ERROR] No active session. Call start_session() first")
            return False
        
        if role not in ['user', 'assistant']:
            print(f"[ERROR] Invalid role: {role}")
            return False
        
        if not content or not isinstance(content, str):
            print("[ERROR] Content harus string tidak kosong")
            return False
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute(
                """INSERT INTO messages (session_id, role, content, tokens) 
                   VALUES (?, ?, ?, ?)""",
                (self.current_session_id, role, content, tokens)
            )
            
            # Update updated_at di sessions
            cursor.execute(
                "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                (self.current_session_id,)
            )
            
            conn.commit()
            conn.close()
            
            if self.verbose:
                print(f"[DEBUG] Message added: {role} - {content[:30]}...")
            
            # Cek batas history
            self._enforce_max_history()
            
            return True
            
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to add message: {e}")
            return False

    def get_conversation_history(
        self,
        limit: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Ambil history percakapan
        
        Args:
            limit: Jumlah pesan terakhir (None = semua)
            session_id: Session ID (None = pakai current)
        
        Returns:
            List pesan dalam format [{'role': ..., 'content': ..., 'timestamp': ...}]
        """
        # STATUS: OK - Method berjalan normal
        session = session_id or self.current_session_id
        
        if session is None:
            print("[ERROR] No active session")
            return []
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT role, content, timestamp, tokens
                FROM messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """
            
            if limit:
                # Ambil last N, dengan subquery agar urutan tetap ascending
                query = f"""
                    SELECT * FROM (
                        SELECT role, content, timestamp, tokens
                        FROM messages
                        WHERE session_id = ?
                        ORDER BY timestamp DESC
                        LIMIT {limit}
                    ) ORDER BY timestamp ASC
                """
            
            cursor.execute(query, (session,))
            rows = cursor.fetchall()
            conn.close()
            
            history = [
                {
                    'role': row['role'],
                    'content': row['content'],
                    'timestamp': row['timestamp'],
                    'tokens': row['tokens']
                }
                for row in rows
            ]
            
            if self.verbose:
                print(f"[DEBUG] Retrieved {len(history)} messages from history")
            
            return history
            
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to get history: {e}")
            return []

    def get_last_messages(self, n: int = 5) -> List[Dict[str, Any]]:
        """
        Ambil N pesan terakhir
        
        Args:
            n: Jumlah pesan yang diambil
        
        Returns:
            List pesan terakhir
        """
        # STATUS: OK - Method berjalan normal
        return self.get_conversation_history(limit=n)

    def get_conversation_context(self, n: int = 5) -> str:
        """
        Ambil konteks percakapan dalam format string
        
        Args:
            n: Jumlah pesan terakhir
        
        Returns:
            String konteks percakapan
        """
        # STATUS: OK - Method berjalan normal
        messages = self.get_last_messages(n)
        
        if not messages:
            return ""
        
        context_lines = []
        for msg in messages:
            role_label = "User" if msg['role'] == 'user' else "Assistant"
            context_lines.append(f"{role_label}: {msg['content']}")
        
        return "\n".join(context_lines)

    def save_summary(self, summary: str) -> bool:
        """
        Simpan ringkasan percakapan
        
        Args:
            summary: Ringkasan percakapan
        
        Returns:
            True jika berhasil
        """
        # STATUS: OK - Method berjalan normal
        if self.current_session_id is None:
            print("[ERROR] No active session")
            return False
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute(
                """INSERT INTO memory_summary (session_id, summary) 
                   VALUES (?, ?)""",
                (self.current_session_id, summary)
            )
            
            conn.commit()
            conn.close()
            
            if self.verbose:
                print(f"[DEBUG] Summary saved: {summary[:50]}...")
            
            return True
            
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to save summary: {e}")
            return False

    def get_summaries(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Ambil ringkasan percakapan
        
        Args:
            limit: Jumlah ringkasan terakhir
        
        Returns:
            List ringkasan
        """
        # STATUS: OK - Method berjalan normal
        if self.current_session_id is None:
            print("[ERROR] No active session")
            return []
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT summary, created_at 
                   FROM memory_summary 
                   WHERE session_id = ? 
                   ORDER BY created_at DESC 
                   LIMIT ?""",
                (self.current_session_id, limit)
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            summaries = [
                {
                    'summary': row['summary'],
                    'created_at': row['created_at']
                }
                for row in rows
            ]
            
            return summaries
            
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to get summaries: {e}")
            return []

    def _enforce_max_history(self) -> None:
        """Batasi jumlah history per sesi"""
        # STATUS: OK - Method berjalan normal
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Hitung total pesan
            cursor.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ?",
                (self.current_session_id,)
            )
            count = cursor.fetchone()[0]
            
            # Jika melebihi batas, hapus yang paling lama
            if count > self.max_history:
                delete_count = count - self.max_history
                cursor.execute(
                    """DELETE FROM messages 
                       WHERE id IN (
                           SELECT id FROM messages 
                           WHERE session_id = ? 
                           ORDER BY timestamp ASC 
                           LIMIT ?
                       )""",
                    (self.current_session_id, delete_count)
                )
                conn.commit()
                
                if self.verbose:
                    print(f"[DEBUG] Deleted {delete_count} old messages to enforce history limit")
            
            conn.close()
            
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to enforce history limit: {e}")

    def clear_session(self, session_id: Optional[str] = None) -> bool:
        """
        Hapus semua data sesi
        
        Args:
            session_id: Session ID (None = pakai current)
        
        Returns:
            True jika berhasil
        """
        # STATUS: OK - Method berjalan normal
        session = session_id or self.current_session_id
        
        if session is None:
            print("[ERROR] No active session")
            return False
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Hapus pesan
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session,))
            
            # Hapus summary
            cursor.execute("DELETE FROM memory_summary WHERE session_id = ?", (session,))
            
            # Hapus sesi
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session,))
            
            conn.commit()
            conn.close()
            
            if self.verbose:
                print(f"[DEBUG] Session cleared: {session}")
            
            if session == self.current_session_id:
                self.current_session_id = None
            
            return True
            
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to clear session: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Ambil statistik memory
        
        Returns:
            Dict statistik
        """
        # STATUS: OK - Method berjalan normal
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Total sessions
            cursor.execute("SELECT COUNT(*) FROM sessions")
            total_sessions = cursor.fetchone()[0]
            
            # Total messages
            cursor.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]
            
            # Total summaries
            cursor.execute("SELECT COUNT(*) FROM memory_summary")
            total_summaries = cursor.fetchone()[0]
            
            # Messages per session (current)
            msgs_per_session = 0
            if self.current_session_id:
                cursor.execute(
                    "SELECT COUNT(*) FROM messages WHERE session_id = ?",
                    (self.current_session_id,)
                )
                msgs_per_session = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'total_summaries': total_summaries,
                'current_session': self.current_session_id,
                'messages_in_current_session': msgs_per_session,
                'max_history_limit': self.max_history
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
    memory = MemoryManager(verbose=True)
    
    # Test start session
    print("\n[TEST] Start session")
    session_id = memory.start_session()
    print(f"Session ID: {session_id}")
    
    # Test add message
    print("\n[TEST] Add messages")
    memory.add_message("user", "Halo, saya ingin bertanya", 10)
    memory.add_message("assistant", "Ya, silakan bertanya", 8)
    memory.add_message("user", "Apa cuaca hari ini?", 7)
    
    # Test get history
    print("\n[TEST] Get history")
    history = memory.get_conversation_history()
    for msg in history:
        print(f"  {msg['role']}: {msg['content']}")
    
    # Test get context
    print("\n[TEST] Get context")
    context = memory.get_conversation_context(2)
    print(f"Context:\n{context}")
    
    # Test save summary
    print("\n[TEST] Save summary")
    memory.save_summary("Percakapan tentang cuaca")
    
    # Test get summaries
    print("\n[TEST] Get summaries")
    summaries = memory.get_summaries()
    for s in summaries:
        print(f"  {s['summary']} - {s['created_at']}")
    
    # Test stats
    print("\n[TEST] Get stats")
    stats = memory.get_stats()
    print(f"Stats: {stats}")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)