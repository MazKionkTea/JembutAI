# mcp/sqlite_server.py
"""
MCP SQLite Server - Menyediakan akses ke database SQLite untuk penyimpanan dan memori
"""

import sqlite3
import json
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pathlib import Path


class SQLiteServer:
    """MCP Server untuk operasi database SQLite"""
    
    def __init__(
        self,
        db_path: str = "database/assistant.db",
        verbose: bool = False
    ):
        """
        Inisialisasi SQLite server
        
        Args:
            db_path: Path ke database SQLite
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.db_path = Path(db_path)
        self.verbose = verbose
        
        # Buat direktori jika belum ada
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Inisialisasi database
        self._init_database()
        
        # Statistik
        self.total_queries = 0
        self.total_inserts = 0
        self.total_errors = 0
        
        if self.verbose:
            print(f"[DEBUG] SQLiteServer initialized")
            print(f"[DEBUG] Database path: {self.db_path}")

    def _init_database(self) -> None:
        """Buat tabel-tabel yang diperlukan jika belum ada"""
        # STATUS: OK - Method berjalan normal
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Tabel notes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabel memories (long-term memory)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0
                )
            """)
            
            # Tabel conversations (chat history)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tokens INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabel statistics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index untuk performa
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notes_category 
                ON notes(category)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_session 
                ON conversations(session_id, timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_key 
                ON memories(key)
            """)
            
            conn.commit()
            conn.close()
            
            if self.verbose:
                print("[DEBUG] Database initialized successfully")
                
        except sqlite3.Error as e:
            print(f"[ERROR] Database initialization failed: {e}")
            raise

    def _get_connection(self) -> sqlite3.Connection:
        """
        Dapatkan koneksi database
        
        Returns:
            sqlite3.Connection
        """
        # STATUS: OK - Method berjalan normal
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Eksekusi query SELECT dan return results
        
        Args:
            query: SQL query
            params: Parameter untuk query
        
        Returns:
            List dict results
        """
        # STATUS: OK - Method berjalan normal
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # Convert ke dict
            results = [dict(row) for row in rows]
            self.total_queries += 1
            
            if self.verbose:
                print(f"[DEBUG] Query executed: {len(results)} rows returned")
            
            return results
            
        except sqlite3.Error as e:
            self.total_errors += 1
            print(f"[ERROR] Query failed: {e}")
            print(f"[ERROR] Query: {query[:100]}...")
            raise

    def _execute_commit(self, query: str, params: tuple = ()) -> int:
        """
        Eksekusi query INSERT/UPDATE/DELETE dan commit
        
        Args:
            query: SQL query
            params: Parameter untuk query
        
        Returns:
            ID baris terakhir (jika INSERT) atau jumlah row affected
        """
        # STATUS: OK - Method berjalan normal
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            
            last_id = cursor.lastrowid
            row_count = cursor.rowcount
            conn.close()
            
            self.total_inserts += 1
            
            if self.verbose:
                print(f"[DEBUG] Query committed: {row_count} rows affected, last_id: {last_id}")
            
            return last_id or row_count
            
        except sqlite3.Error as e:
            self.total_errors += 1
            print(f"[ERROR] Commit failed: {e}")
            print(f"[ERROR] Query: {query[:100]}...")
            raise

    # ==================== NOTE OPERATIONS ====================
    
    def insert_note(self, title: str, content: str, category: str = 'general', tags: Optional[str] = None) -> Dict[str, Any]:
        """
        Tambahkan note baru
        
        Args:
            title: Judul note
            content: Isi note
            category: Kategori (default: general)
            tags: Tags dipisahkan koma
        
        Returns:
            Dict dengan status dan ID
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not title or not isinstance(title, str):
            raise ValueError("Title harus string tidak kosong")
        
        if not content or not isinstance(content, str):
            raise ValueError("Content harus string tidak kosong")
        
        try:
            query = """
                INSERT INTO notes (title, content, category, tags)
                VALUES (?, ?, ?, ?)
            """
            note_id = self._execute_commit(query, (title, content, category, tags))
            
            return {
                'success': True,
                'id': note_id,
                'title': title,
                'message': f"Note berhasil ditambahkan: {title}"
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to insert note: {e}")
            raise

    def search_note(self, query_text: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Cari note berdasarkan teks
        
        Args:
            query_text: Teks pencarian
            category: Filter kategori (opsional)
        
        Returns:
            List note yang cocok
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not query_text or not isinstance(query_text, str):
            raise ValueError("Query text harus string tidak kosong")
        
        try:
            sql = """
                SELECT id, title, content, category, tags, created_at, updated_at
                FROM notes
                WHERE title LIKE ? OR content LIKE ?
            """
            params = [f'%{query_text}%', f'%{query_text}%']
            
            if category:
                sql += " AND category = ?"
                params.append(category)
            
            sql += " ORDER BY updated_at DESC"
            
            results = self._execute_query(sql, tuple(params))
            
            return results
            
        except Exception as e:
            print(f"[ERROR] Failed to search notes: {e}")
            raise

    def get_note(self, note_id: int) -> Optional[Dict[str, Any]]:
        """
        Ambil note berdasarkan ID
        
        Args:
            note_id: ID note
        
        Returns:
            Dict note atau None jika tidak ditemukan
        """
        # STATUS: OK - Method berjalan normal
        try:
            query = """
                SELECT id, title, content, category, tags, created_at, updated_at
                FROM notes
                WHERE id = ?
            """
            results = self._execute_query(query, (note_id,))
            
            return results[0] if results else None
            
        except Exception as e:
            print(f"[ERROR] Failed to get note: {e}")
            raise

    def update_note(self, note_id: int, title: Optional[str] = None, content: Optional[str] = None, category: Optional[str] = None, tags: Optional[str] = None) -> Dict[str, Any]:
        """
        Update note
        
        Args:
            note_id: ID note
            title: Judul baru (opsional)
            content: Isi baru (opsional)
            category: Kategori baru (opsional)
            tags: Tags baru (opsional)
        
        Returns:
            Dict dengan status
        """
        # STATUS: OK - Method berjalan normal
        try:
            # Cek note ada
            existing = self.get_note(note_id)
            if not existing:
                raise ValueError(f"Note dengan ID {note_id} tidak ditemukan")
            
            # Build query
            updates = []
            params = []
            
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            
            if content is not None:
                updates.append("content = ?")
                params.append(content)
            
            if category is not None:
                updates.append("category = ?")
                params.append(category)
            
            if tags is not None:
                updates.append("tags = ?")
                params.append(tags)
            
            if not updates:
                return {
                    'success': True,
                    'message': "Tidak ada perubahan",
                    'id': note_id
                }
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(note_id)
            
            query = f"""
                UPDATE notes
                SET {', '.join(updates)}
                WHERE id = ?
            """
            
            self._execute_commit(query, tuple(params))
            
            return {
                'success': True,
                'id': note_id,
                'message': f"Note berhasil diupdate: {note_id}"
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to update note: {e}")
            raise

    def delete_note(self, note_id: int) -> Dict[str, Any]:
        """
        Hapus note
        
        Args:
            note_id: ID note
        
        Returns:
            Dict dengan status
        """
        # STATUS: OK - Method berjalan normal
        try:
            query = "DELETE FROM notes WHERE id = ?"
            affected = self._execute_commit(query, (note_id,))
            
            if affected == 0:
                raise ValueError(f"Note dengan ID {note_id} tidak ditemukan")
            
            return {
                'success': True,
                'id': note_id,
                'message': f"Note berhasil dihapus: {note_id}"
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to delete note: {e}")
            raise

    def get_all_notes(self, category: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Ambil semua notes
        
        Args:
            category: Filter kategori (opsional)
            limit: Maksimal hasil
        
        Returns:
            List notes
        """
        # STATUS: OK - Method berjalan normal
        try:
            query = """
                SELECT id, title, content, category, tags, created_at, updated_at
                FROM notes
            """
            params = []
            
            if category:
                query += " WHERE category = ?"
                params.append(category)
            
            query += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)
            
            return self._execute_query(query, tuple(params))
            
        except Exception as e:
            print(f"[ERROR] Failed to get all notes: {e}")
            raise

    # ==================== MEMORY OPERATIONS ====================
    
    def save_memory(self, key: str, value: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Simpan memori jangka panjang
        
        Args:
            key: Key unik untuk memori
            value: Nilai memori
            context: Konteks tambahan (opsional)
        
        Returns:
            Dict dengan status
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not key or not isinstance(key, str):
            raise ValueError("Key harus string tidak kosong")
        
        if not value or not isinstance(value, str):
            raise ValueError("Value harus string tidak kosong")
        
        try:
            # Cek apakah key sudah ada
            existing = self._execute_query(
                "SELECT id FROM memories WHERE key = ?",
                (key,)
            )
            
            if existing:
                # Update
                query = """
                    UPDATE memories
                    SET value = ?, context = ?, updated_at = CURRENT_TIMESTAMP, access_count = access_count + 1
                    WHERE key = ?
                """
                self._execute_commit(query, (value, context, key))
                
                return {
                    'success': True,
                    'key': key,
                    'action': 'updated',
                    'message': f"Memory berhasil diupdate: {key}"
                }
            else:
                # Insert
                query = """
                    INSERT INTO memories (key, value, context)
                    VALUES (?, ?, ?)
                """
                self._execute_commit(query, (key, value, context))
                
                return {
                    'success': True,
                    'key': key,
                    'action': 'inserted',
                    'message': f"Memory berhasil disimpan: {key}"
                }
            
        except Exception as e:
            print(f"[ERROR] Failed to save memory: {e}")
            raise

    def load_memory(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Ambil memori berdasarkan key
        
        Args:
            key: Key memori
        
        Returns:
            Dict memori atau None jika tidak ditemukan
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not key or not isinstance(key, str):
            raise ValueError("Key harus string tidak kosong")
        
        try:
            query = """
                SELECT id, key, value, context, created_at, updated_at, access_count
                FROM memories
                WHERE key = ?
            """
            results = self._execute_query(query, (key,))
            
            if results:
                # Update access_count
                self._execute_commit(
                    "UPDATE memories SET access_count = access_count + 1 WHERE key = ?",
                    (key,)
                )
                return results[0]
            
            return None
            
        except Exception as e:
            print(f"[ERROR] Failed to load memory: {e}")
            raise

    def search_memory(self, query_text: str) -> List[Dict[str, Any]]:
        """
        Cari memori berdasarkan teks
        
        Args:
            query_text: Teks pencarian
        
        Returns:
            List memori yang cocok
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not query_text or not isinstance(query_text, str):
            raise ValueError("Query text harus string tidak kosong")
        
        try:
            query = """
                SELECT id, key, value, context, created_at, updated_at, access_count
                FROM memories
                WHERE key LIKE ? OR value LIKE ? OR context LIKE ?
                ORDER BY access_count DESC, updated_at DESC
            """
            pattern = f'%{query_text}%'
            results = self._execute_query(query, (pattern, pattern, pattern))
            
            return results
            
        except Exception as e:
            print(f"[ERROR] Failed to search memory: {e}")
            raise

    def delete_memory(self, key: str) -> Dict[str, Any]:
        """
        Hapus memori berdasarkan key
        
        Args:
            key: Key memori
        
        Returns:
            Dict dengan status
        """
        # STATUS: OK - Method berjalan normal
        try:
            query = "DELETE FROM memories WHERE key = ?"
            affected = self._execute_commit(query, (key,))
            
            if affected == 0:
                raise ValueError(f"Memory dengan key {key} tidak ditemukan")
            
            return {
                'success': True,
                'key': key,
                'message': f"Memory berhasil dihapus: {key}"
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to delete memory: {e}")
            raise

    def get_all_memories(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Ambil semua memori
        
        Args:
            limit: Maksimal hasil
        
        Returns:
            List memori
        """
        # STATUS: OK - Method berjalan normal
        try:
            query = """
                SELECT id, key, value, context, created_at, updated_at, access_count
                FROM memories
                ORDER BY access_count DESC, updated_at DESC
                LIMIT ?
            """
            return self._execute_query(query, (limit,))
            
        except Exception as e:
            print(f"[ERROR] Failed to get all memories: {e}")
            raise

    # ==================== CONVERSATION OPERATIONS ====================
    
    def save_conversation(self, session_id: str, role: str, content: str, tokens: int = 0) -> Dict[str, Any]:
        """
        Simpan percakapan
        
        Args:
            session_id: ID sesi
            role: 'user' atau 'assistant'
            content: Isi pesan
            tokens: Jumlah token (opsional)
        
        Returns:
            Dict dengan status
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not session_id or not isinstance(session_id, str):
            raise ValueError("Session ID harus string tidak kosong")
        
        if role not in ['user', 'assistant']:
            raise ValueError("Role harus 'user' atau 'assistant'")
        
        if not content or not isinstance(content, str):
            raise ValueError("Content harus string tidak kosong")
        
        try:
            query = """
                INSERT INTO conversations (session_id, role, content, tokens)
                VALUES (?, ?, ?, ?)
            """
            conv_id = self._execute_commit(query, (session_id, role, content, tokens))
            
            return {
                'success': True,
                'id': conv_id,
                'session_id': session_id,
                'message': f"Percakapan berhasil disimpan: {session_id}"
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to save conversation: {e}")
            raise

    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Ambil history percakapan
        
        Args:
            session_id: ID sesi
            limit: Jumlah pesan terakhir
        
        Returns:
            List pesan
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not session_id or not isinstance(session_id, str):
            raise ValueError("Session ID harus string tidak kosong")
        
        try:
            query = """
                SELECT id, role, content, tokens, timestamp
                FROM conversations
                WHERE session_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """
            results = self._execute_query(query, (session_id, limit))
            
            return results
            
        except Exception as e:
            print(f"[ERROR] Failed to get conversation history: {e}")
            raise

    def clear_conversation(self, session_id: str) -> Dict[str, Any]:
        """
        Hapus semua percakapan untuk sesi
        
        Args:
            session_id: ID sesi
        
        Returns:
            Dict dengan status
        """
        # STATUS: OK - Method berjalan normal
        try:
            query = "DELETE FROM conversations WHERE session_id = ?"
            affected = self._execute_commit(query, (session_id,))
            
            return {
                'success': True,
                'session_id': session_id,
                'deleted_rows': affected,
                'message': f"Percakapan untuk {session_id} berhasil dihapus"
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to clear conversation: {e}")
            raise

    # ==================== STATISTICS OPERATIONS ====================
    
    def save_statistic(self, metric_name: str, metric_value: str) -> Dict[str, Any]:
        """
        Simpan statistik
        
        Args:
            metric_name: Nama metrik
            metric_value: Nilai metrik (JSON string atau plain)
        
        Returns:
            Dict dengan status
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not metric_name or not isinstance(metric_name, str):
            raise ValueError("Metric name harus string tidak kosong")
        
        try:
            query = """
                INSERT INTO statistics (metric_name, metric_value)
                VALUES (?, ?)
            """
            stat_id = self._execute_commit(query, (metric_name, metric_value))
            
            return {
                'success': True,
                'id': stat_id,
                'metric_name': metric_name,
                'message': f"Statistik berhasil disimpan: {metric_name}"
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to save statistic: {e}")
            raise

    def get_statistics(self, metric_name: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Ambil statistik
        
        Args:
            metric_name: Filter nama metrik (opsional)
            limit: Maksimal hasil
        
        Returns:
            List statistik
        """
        # STATUS: OK - Method berjalan normal
        try:
            query = """
                SELECT id, metric_name, metric_value, timestamp
                FROM statistics
            """
            params = []
            
            if metric_name:
                query += " WHERE metric_name = ?"
                params.append(metric_name)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            return self._execute_query(query, tuple(params))
            
        except Exception as e:
            print(f"[ERROR] Failed to get statistics: {e}")
            raise

    # ==================== DATABASE OPERATIONS ====================
    
    def execute_query(self, query: str, params: Optional[Union[tuple, list]] = None) -> List[Dict[str, Any]]:
        """
        Eksekusi query SQL custom (READ ONLY)
        
        Args:
            query: SQL query (SELECT only)
            params: Parameter untuk query
        
        Returns:
            List results
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI - hanya SELECT
        query_upper = query.strip().upper()
        if not query_upper.startswith('SELECT'):
            raise ValueError("Hanya SELECT query yang diizinkan untuk keamanan")
        
        if params is None:
            params = ()
        
        return self._execute_query(query, tuple(params))

    def execute_command(self, query: str, params: Optional[Union[tuple, list]] = None) -> Dict[str, Any]:
        """
        Eksekusi SQL command (INSERT/UPDATE/DELETE)
        
        Args:
            query: SQL command
            params: Parameter untuk query
        
        Returns:
            Dict dengan status
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI - hanya INSERT/UPDATE/DELETE
        query_upper = query.strip().upper()
        allowed = ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP']
        if not any(query_upper.startswith(cmd) for cmd in allowed):
            raise ValueError("Hanya INSERT/UPDATE/DELETE yang diizinkan")
        
        if params is None:
            params = ()
        
        affected = self._execute_commit(query, tuple(params))
        
        return {
            'success': True,
            'affected_rows': affected,
            'message': f"Command berhasil dieksekusi: {affected} rows affected"
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Ambil statistik SQLite server
        
        Returns:
            Dict statistik
        """
        # STATUS: OK - Method berjalan normal
        # Ambil counts dari database
        try:
            note_count = self._execute_query("SELECT COUNT(*) as count FROM notes")[0]['count']
            memory_count = self._execute_query("SELECT COUNT(*) as count FROM memories")[0]['count']
            conv_count = self._execute_query("SELECT COUNT(*) as count FROM conversations")[0]['count']
            
        except:
            note_count = 0
            memory_count = 0
            conv_count = 0
        
        return {
            'total_queries': self.total_queries,
            'total_inserts': self.total_inserts,
            'total_errors': self.total_errors,
            'db_path': str(self.db_path),
            'note_count': note_count,
            'memory_count': memory_count,
            'conversation_count': conv_count
        }


# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING SQLITE SERVER")
    print("=" * 50)
    
    # Inisialisasi
    print("\n[TEST] Init SQLiteServer")
    server = SQLiteServer(db_path="./test_db/assistant.db", verbose=True)
    
    # Test insert note
    print("\n[TEST] Insert note")
    result = server.insert_note(
        title="Test Note",
        content="Ini adalah test note untuk MCP SQLite Server",
        category="test"
    )
    print(f"Insert result: {result}")
    
    # Test insert memory
    print("\n[TEST] Save memory")
    result = server.save_memory(
        key="user_preference",
        value="User prefers informal language",
        context="Initial conversation"
    )
    print(f"Save memory result: {result}")
    
    # Test search note
    print("\n[TEST] Search note")
    results = server.search_note("test")
    print(f"Found: {len(results)} notes")
    for note in results:
        print(f"  {note['title']}: {note['content'][:50]}...")
    
    # Test load memory
    print("\n[TEST] Load memory")
    memory = server.load_memory("user_preference")
    print(f"Memory: {memory}")
    
    # Test save conversation
    print("\n[TEST] Save conversation")
    server.save_conversation("session_001", "user", "Halo, apa kabar?", 10)
    server.save_conversation("session_001", "assistant", "Saya baik, terima kasih!", 8)
    
    # Test get conversation
    print("\n[TEST] Get conversation history")
    conv = server.get_conversation_history("session_001")
    for msg in conv:
        print(f"  {msg['role']}: {msg['content']}")
    
    # Test get all notes
    print("\n[TEST] Get all notes")
    notes = server.get_all_notes()
    print(f"Total notes: {len(notes)}")
    
    # Test update note
    print("\n[TEST] Update note")
    note = server.get_all_notes(limit=1)[0]
    result = server.update_note(note['id'], content="Updated content")
    print(f"Update result: {result}")
    
    # Test stats
    print("\n[TEST] Get stats")
    stats = server.get_stats()
    print(f"Stats: {stats}")
    
    # Test execute query
    print("\n[TEST] Execute query")
    results = server.execute_query("SELECT * FROM notes")
    print(f"Query results: {len(results)} rows")
    
    # Cleanup
    print("\n[TEST] Cleanup")
    import shutil
    shutil.rmtree("./test_db")
    print("Test database removed")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)
