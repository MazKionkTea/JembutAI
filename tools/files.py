# tools/files.py
"""
File Tools - Wrapper untuk operasi file menggunakan MCP Filesystem Server
"""

from typing import Optional, List, Dict, Any


class FileTools:
    """Wrapper untuk operasi file"""
    
    def __init__(self, filesystem_server, verbose: bool = False):
        """
        Inisialisasi file tools
        
        Args:
            filesystem_server: Instance FileSystemServer
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.server = filesystem_server
        self.verbose = verbose
        
        if self.verbose:
            print("[DEBUG] FileTools initialized")

    def read(self, path: str, encoding: str = 'utf-8') -> str:
        """Baca file"""
        # STATUS: OK - Method berjalan normal
        return self.server.read_file(path, encoding)

    def write(self, path: str, content: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """Tulis file"""
        # STATUS: OK - Method berjalan normal
        return self.server.write_file(path, content, encoding)

    def append(self, path: str, content: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """Append ke file"""
        # STATUS: OK - Method berjalan normal
        return self.server.append_file(path, content, encoding)

    def list(self, path: str = ".", include_hidden: bool = False) -> List[Dict[str, Any]]:
        """List direktori"""
        # STATUS: OK - Method berjalan normal
        return self.server.list_directory(path, include_hidden)

    def search(self, path: str = ".", pattern: str = "*", recursive: bool = True) -> List[Dict[str, Any]]:
        """Cari file"""
        # STATUS: OK - Method berjalan normal
        return self.server.search_files(path, pattern, recursive)

    def count_pdf(self, path: str = ".") -> int:
        """Hitung file PDF"""
        # STATUS: OK - Method berjalan normal
        return self.server.count_pdf(path)

    def rename(self, old_path: str, new_path: str, overwrite: bool = False) -> Dict[str, Any]:
        """Rename file"""
        # STATUS: OK - Method berjalan normal
        return self.server.rename_file(old_path, new_path, overwrite)

    def delete(self, path: str, force: bool = False) -> Dict[str, Any]:
        """Hapus file"""
        # STATUS: OK - Method berjalan normal
        return self.server.delete_file(path, force)

    def info(self, path: str) -> Dict[str, Any]:
        """Info file"""
        # STATUS: OK - Method berjalan normal
        return self.server.get_file_info(path)

    def mkdir(self, path: str, exist_ok: bool = True) -> Dict[str, Any]:
        """Buat direktori"""
        # STATUS: OK - Method berjalan normal
        return self.server.create_directory(path, exist_ok)


# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING FILE TOOLS")
    print("=" * 50)
    
    from mcp.filesystem_server import FileSystemServer
    
    server = FileSystemServer(base_path="./test_tools", verbose=False)
    tools = FileTools(server, verbose=True)
    
    # Test write
    print("\n[TEST] Write file")
    tools.write("test.txt", "Hello from FileTools!")
    
    # Test read
    print("\n[TEST] Read file")
    content = tools.read("test.txt")
    print(f"Content: {content}")
    
    # Test list
    print("\n[TEST] List directory")
    items = tools.list(".")
    print(f"Items: {len(items)}")
    
    # Test search
    print("\n[TEST] Search")
    results = tools.search(".", "*.txt")
    print(f"Found: {len(results)} txt files")
    
    # Test info
    print("\n[TEST] File info")
    info = tools.info("test.txt")
    print(f"Info: {info}")
    
    # Cleanup
    import shutil
    shutil.rmtree("./test_tools")
    print("\nCleanup done")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)