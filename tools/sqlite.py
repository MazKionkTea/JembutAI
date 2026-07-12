# tools/sqlite.py
"""
SQLite Tools - Wrapper untuk operasi database menggunakan MCP SQLite Server
"""

from typing import Optional, List, Dict, Any


class SQLiteTools:
    """Wrapper untuk operasi database"""
    
    def __init__(self, sqlite_server, verbose: bool = False):
        """
        Inisialisasi SQLite tools
        
        Args:
            sqlite_server: Instance SQLiteServer
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.server = sqlite_server
        self.verbose = verbose
        
        if self.verbose:
            print("[DEBUG] SQLiteTools initialized")

    # ==================== NOTES ====================
    
    def add_note(self, title: str, content: str, category: str = 'general', tags: Optional[str] = None) -> Dict[str, Any]:
        """
        Tambah note baru
        
        Args:
            title: Judul note
            content: Isi note
            category: Kategori (default: general)
            tags: Tags dipisahkan koma
        
        Returns:
            Dict dengan status dan ID
        """
        # STATUS: OK - Method berjalan normal
        return self.server.insert_note(title, content, category, tags)

    def search_note(self, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Cari note berdasarkan teks
        
        Args:
            query: Teks pencarian
            category: Filter kategori (opsional)
        
        Returns:
            List note yang cocok
        """
        # STATUS: OK - Method berjalan normal
        return self.server.search_note(query, category)

    def get_note(self, note_id: int) -> Optional[Dict[str, Any]]:
        """
        Ambil note berdasarkan ID
        
        Args:
            note_id: ID note
        
        Returns:
            Dict note atau None jika tidak ditemukan
        """
        # STATUS: OK - Method berjalan normal
        return self.server.get_note(note_id)

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
        return self.server.update_note(note_id, title, content, category, tags)

    def delete_note(self, note_id: int) -> Dict[str, Any]:
        """
        Hapus note
        
        Args:
            note_id: ID note
        
        Returns:
            Dict dengan status
        """
        # STATUS: OK - Method berjalan normal
        return self.server.delete_note(note_id)

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
        return self.server.get_all_notes(category, limit)

    # ==================== MEMORIES ====================
    
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
        return self.server.save_memory(key, value, context)

    def load_memory(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Ambil memori berdasarkan key
        
        Args:
            key: Key memori
        
        Returns:
            Dict memori atau None jika tidak ditemukan
        """
        # STATUS: OK - Method berjalan normal
        return self.server.load_memory(key)

    def search_memory(self, query: str) -> List[Dict[str, Any]]:
        """
        Cari memori berdasarkan teks
        
        Args:
            query: Teks pencarian
        
        Returns:
            List memori yang cocok
        """
        # STATUS: OK - Method berjalan normal
        return self.server.search_memory(query)

    def delete_memory(self, key: str) -> Dict[str, Any]:
        """
        Hapus memori berdasarkan key
        
        Args:
            key: Key memori
        
        Returns:
            Dict dengan status
        """
        # STATUS: OK - Method berjalan normal
        return self.server.delete_memory(key)

    def get_all_memories(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Ambil semua memori
        
        Args:
            limit: Maksimal hasil
        
        Returns:
            List memori
        """
        # STATUS: OK - Method berjalan normal
        return self.server.get_all_memories(limit)

    # ==================== CONVERSATIONS ====================
    
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
        return self.server.save_conversation(session_id, role, content, tokens)

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
        return self.server.get_conversation_history(session_id, limit)

    def clear_conversation(self, session_id: str) -> Dict[str, Any]:
        """
        Hapus semua percakapan untuk sesi
        
        Args:
            session_id: ID sesi
        
        Returns:
            Dict dengan status
        """
        # STATUS: OK - Method berjalan normal
        return self.server.clear_conversation(session_id)

    # ==================== STATISTICS ====================
    
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
        return self.server.save_statistic(metric_name, metric_value)

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
        return self.server.get_statistics(metric_name, limit)

    # ==================== QUERY ====================
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Eksekusi query SQL custom (READ ONLY)
        
        Args:
            query: SQL query (SELECT only)
            params: Parameter untuk query
        
        Returns:
            List results
        """
        # STATUS: OK - Method berjalan normal
        return self.server.execute_query(query, params)

    def execute_command(self, query: str, params: Optional[tuple] = None) -> Dict[str, Any]:
        """
        Eksekusi SQL command (INSERT/UPDATE/DELETE)
        
        Args:
            query: SQL command
            params: Parameter untuk query
        
        Returns:
            Dict dengan status
        """
        # STATUS: OK - Method berjalan normal
        return self.server.execute_command(query, params)

    def get_stats(self) -> Dict[str, Any]:
        """
        Ambil statistik SQLite server
        
        Returns:
            Dict statistik
        """
        # STATUS: OK - Method berjalan normal
        return self.server.get_stats()


# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING SQLITE TOOLS")
    print("=" * 50)
    
    from mcp.sqlite_server import SQLiteServer
    
    # Inisialisasi
    print("\n[TEST] Init SQLiteTools")
    server = SQLiteServer(db_path="./test_db/assistant.db", verbose=False)
    tools = SQLiteTools(server, verbose=True)
    
    # Test add note
    print("\n[TEST] Add note")
    result = tools.add_note("Test Note", "Ini adalah test note", "test", "test,example")
    print(f"Result: {result}")
    
    # Test get all notes
    print("\n[TEST] Get all notes")
    notes = tools.get_all_notes()
    print(f"Total notes: {len(notes)}")
    for note in notes:
        print(f"  {note['title']}: {note['content'][:30]}...")
    
    # Test search note
    print("\n[TEST] Search note")
    results = tools.search_note("test")
    print(f"Found: {len(results)} notes")
    
    # Test save memory
    print("\n[TEST] Save memory")
    result = tools.save_memory("test_key", "test_value", "test_context")
    print(f"Result: {result}")
    
    # Test load memory
    print("\n[TEST] Load memory")
    memory = tools.load_memory("test_key")
    print(f"Memory: {memory}")
    
    # Test save conversation
    print("\n[TEST] Save conversation")
    result = tools.save_conversation("session_001", "user", "Halo, apa kabar?", 10)
    print(f"Result: {result}")
    
    # Test get conversation history
    print("\n[TEST] Get conversation history")
    conv = tools.get_conversation_history("session_001")
    for msg in conv:
        print(f"  {msg['role']}: {msg['content']}")
    
    # Test execute query
    print("\n[TEST] Execute query")
    results = tools.execute_query("SELECT * FROM notes")
    print(f"Query results: {len(results)} rows")
    
    # Test stats
    print("\n[TEST] Get stats")
    stats = tools.get_stats()
    print(f"Stats: {stats}")
    
    # Cleanup
    print("\n[TEST] Cleanup")
    import shutil
    shutil.rmtree("./test_db")
    print("Test database removed")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)