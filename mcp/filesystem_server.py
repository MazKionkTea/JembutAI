# mcp/filesystem_server.py
"""
MCP Filesystem Server - Menyediakan akses ke sistem file lokal
"""

import os
import shutil
import fnmatch
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime


class FileSystemServer:
    """MCP Server untuk operasi filesystem"""
    
    def __init__(
        self,
        base_path: str = ".",
        allow_write: bool = True,
        allow_delete: bool = False,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        verbose: bool = False
    ):
        """
        Inisialisasi filesystem server
        
        Args:
            base_path: Base directory untuk operasi file
            allow_write: Izinkan write operation
            allow_delete: Izinkan delete operation
            max_file_size: Maksimal ukuran file yang dibaca (bytes)
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.base_path = Path(base_path).resolve()
        self.allow_write = allow_write
        self.allow_delete = allow_delete
        self.max_file_size = max_file_size
        self.verbose = verbose
        
        # Buat base_path jika belum ada
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Statistik
        self.total_reads = 0
        self.total_writes = 0
        self.total_deletes = 0
        self.total_errors = 0
        
        if self.verbose:
            print(f"[DEBUG] FileSystemServer initialized")
            print(f"[DEBUG] Base path: {self.base_path}")
            print(f"[DEBUG] Allow write: {allow_write}, Allow delete: {allow_delete}")

    def _resolve_path(self, path: str) -> Path:
        """
        Resolve path dan validasi berada di dalam base_path
        
        Args:
            path: Path relatif atau absolut
        
        Returns:
            Path yang sudah di-resolve
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not path or not isinstance(path, str):
            raise ValueError("Path harus string tidak kosong")
        
        # Gabungkan dengan base_path
        full_path = (self.base_path / path).resolve()
        
        # Cek apakah masih di dalam base_path (security)
        try:
            full_path.relative_to(self.base_path)
        except ValueError:
            raise PermissionError(f"Akses ke luar base_path tidak diizinkan: {full_path}")
        
        return full_path

    def _validate_file_size(self, path: Path) -> None:
        """
        Validasi ukuran file tidak melebihi batas
        
        Args:
            path: Path file
        """
        # STATUS: OK - Method berjalan normal
        if path.exists() and path.is_file():
            size = path.stat().st_size
            if size > self.max_file_size:
                raise ValueError(f"File terlalu besar: {size} bytes (max: {self.max_file_size})")

    def read_file(self, path: str, encoding: str = 'utf-8') -> str:
        """
        Baca isi file
        
        Args:
            path: Path file
            encoding: Encoding file
        
        Returns:
            Isi file sebagai string
        """
        # STATUS: OK - Method berjalan normal
        try:
            full_path = self._resolve_path(path)
            
            if not full_path.exists():
                raise FileNotFoundError(f"File tidak ditemukan: {path}")
            
            if not full_path.is_file():
                raise IsADirectoryError(f"Path adalah direktori: {path}")
            
            # Validasi ukuran
            self._validate_file_size(full_path)
            
            # Baca file
            content = full_path.read_text(encoding=encoding)
            self.total_reads += 1
            
            if self.verbose:
                print(f"[DEBUG] File read: {path} ({len(content)} chars)")
            
            return content
            
        except Exception as e:
            self.total_errors += 1
            print(f"[ERROR] Failed to read file {path}: {e}")
            raise

    def write_file(self, path: str, content: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """
        Tulis content ke file
        
        Args:
            path: Path file
            content: Isi file
            encoding: Encoding file
        
        Returns:
            Dict dengan status dan metadata
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not self.allow_write:
            raise PermissionError("Write operation tidak diizinkan")
        
        try:
            full_path = self._resolve_path(path)
            
            # Buat direktori jika belum ada
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Tulis file
            full_path.write_text(content, encoding=encoding)
            self.total_writes += 1
            
            if self.verbose:
                print(f"[DEBUG] File written: {path} ({len(content)} chars)")
            
            return {
                'success': True,
                'path': str(full_path),
                'size': len(content),
                'encoding': encoding,
                'message': f"File berhasil ditulis: {path}"
            }
            
        except Exception as e:
            self.total_errors += 1
            print(f"[ERROR] Failed to write file {path}: {e}")
            raise

    def append_file(self, path: str, content: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """
        Append content ke file (tambahkan di akhir)
        
        Args:
            path: Path file
            content: Isi yang ditambahkan
            encoding: Encoding file
        
        Returns:
            Dict dengan status dan metadata
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not self.allow_write:
            raise PermissionError("Write operation tidak diizinkan")
        
        try:
            full_path = self._resolve_path(path)
            
            # Buat direktori jika belum ada
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Append ke file
            with open(full_path, 'a', encoding=encoding) as f:
                f.write(content)
            
            self.total_writes += 1
            
            if self.verbose:
                print(f"[DEBUG] File appended: {path} ({len(content)} chars)")
            
            return {
                'success': True,
                'path': str(full_path),
                'size': len(content),
                'encoding': encoding,
                'message': f"Content berhasil ditambahkan ke: {path}"
            }
            
        except Exception as e:
            self.total_errors += 1
            print(f"[ERROR] Failed to append file {path}: {e}")
            raise

    def list_directory(self, path: str = ".", include_hidden: bool = False) -> List[Dict[str, Any]]:
        """
        List isi direktori
        
        Args:
            path: Path direktori
            include_hidden: Sertakan file hidden
        
        Returns:
            List dict dengan info file/direktori
        """
        # STATUS: OK - Method berjalan normal
        try:
            full_path = self._resolve_path(path)
            
            if not full_path.exists():
                raise FileNotFoundError(f"Direktori tidak ditemukan: {path}")
            
            if not full_path.is_dir():
                raise NotADirectoryError(f"Path bukan direktori: {path}")
            
            items = []
            for item in full_path.iterdir():
                # Filter hidden
                if not include_hidden and item.name.startswith('.'):
                    continue
                
                stat = item.stat()
                items.append({
                    'name': item.name,
                    'path': str(item),
                    'is_file': item.is_file(),
                    'is_dir': item.is_dir(),
                    'size': stat.st_size if item.is_file() else 0,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
            
            # Sort: directories first, then files
            items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            
            if self.verbose:
                print(f"[DEBUG] Listed directory: {path} ({len(items)} items)")
            
            return items
            
        except Exception as e:
            self.total_errors += 1
            print(f"[ERROR] Failed to list directory {path}: {e}")
            raise

    def search_files(self, path: str = ".", pattern: str = "*", recursive: bool = True) -> List[Dict[str, Any]]:
        """
        Cari file dengan pattern
        
        Args:
            path: Path direktori
            pattern: Pattern matching (wildcard: *.pdf, test*.txt, dll)
            recursive: Cari di subdirektori
        
        Returns:
            List dict dengan info file yang ditemukan
        """
        # STATUS: OK - Method berjalan normal
        try:
            full_path = self._resolve_path(path)
            
            if not full_path.exists():
                raise FileNotFoundError(f"Direktori tidak ditemukan: {path}")
            
            if not full_path.is_dir():
                raise NotADirectoryError(f"Path bukan direktori: {path}")
            
            results = []
            
            if recursive:
                # Cari di semua subdirektori
                for root, dirs, files in os.walk(full_path):
                    for file in files:
                        if fnmatch.fnmatch(file, pattern):
                            file_path = Path(root) / file
                            stat = file_path.stat()
                            results.append({
                                'name': file,
                                'path': str(file_path),
                                'size': stat.st_size,
                                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                'relative_path': str(file_path.relative_to(self.base_path))
                            })
            else:
                # Cari hanya di direktori ini
                for item in full_path.iterdir():
                    if item.is_file() and fnmatch.fnmatch(item.name, pattern):
                        stat = item.stat()
                        results.append({
                            'name': item.name,
                            'path': str(item),
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'relative_path': str(item.relative_to(self.base_path))
                        })
            
            if self.verbose:
                print(f"[DEBUG] Search completed: {pattern} in {path} ({len(results)} files)")
            
            return results
            
        except Exception as e:
            self.total_errors += 1
            print(f"[ERROR] Failed to search files in {path}: {e}")
            raise

    def count_files(self, path: str = ".", extension: Optional[str] = None, recursive: bool = True) -> int:
        """
        Hitung jumlah file berdasarkan ekstensi
        
        Args:
            path: Path direktori
            extension: Ekstensi file (misal: .pdf, .txt), None = semua
            recursive: Cari di subdirektori
        
        Returns:
            Jumlah file
        """
        # STATUS: OK - Method berjalan normal
        try:
            full_path = self._resolve_path(path)
            
            if not full_path.exists():
                raise FileNotFoundError(f"Direktori tidak ditemukan: {path}")
            
            if not full_path.is_dir():
                raise NotADirectoryError(f"Path bukan direktori: {path}")
            
            count = 0
            if recursive:
                for root, dirs, files in os.walk(full_path):
                    for file in files:
                        if extension is None or file.endswith(extension):
                            count += 1
            else:
                for item in full_path.iterdir():
                    if item.is_file():
                        if extension is None or item.name.endswith(extension):
                            count += 1
            
            if self.verbose:
                ext_display = extension or 'all'
                print(f"[DEBUG] Count files: {path} ({ext_display}) = {count}")
            
            return count
            
        except Exception as e:
            self.total_errors += 1
            print(f"[ERROR] Failed to count files in {path}: {e}")
            raise

    def count_pdf(self, path: str = ".") -> int:
        """
        Hitung jumlah file PDF (shortcut)
        
        Args:
            path: Path direktori
        
        Returns:
            Jumlah file PDF
        """
        # STATUS: OK - Method berjalan normal
        return self.count_files(path, extension='.pdf')

    def rename_file(self, old_path: str, new_path: str, overwrite: bool = False) -> Dict[str, Any]:
        """
        Rename atau move file
        
        Args:
            old_path: Path file lama
            new_path: Path file baru
            overwrite: Overwrite jika file sudah ada
        
        Returns:
            Dict dengan status dan metadata
        """
        # STATUS: OK - Method berjalan normal
        try:
            full_old = self._resolve_path(old_path)
            full_new = self._resolve_path(new_path)
            
            if not full_old.exists():
                raise FileNotFoundError(f"File tidak ditemukan: {old_path}")
            
            if not full_old.is_file():
                raise IsADirectoryError(f"Path adalah direktori: {old_path}")
            
            if full_new.exists() and not overwrite:
                raise FileExistsError(f"File sudah ada: {new_path}")
            
            # Buat direktori baru jika belum ada
            full_new.parent.mkdir(parents=True, exist_ok=True)
            
            # Rename
            shutil.move(str(full_old), str(full_new))
            
            if self.verbose:
                print(f"[DEBUG] File renamed: {old_path} → {new_path}")
            
            return {
                'success': True,
                'old_path': str(full_old),
                'new_path': str(full_new),
                'message': f"File berhasil di-rename: {old_path} → {new_path}"
            }
            
        except Exception as e:
            self.total_errors += 1
            print(f"[ERROR] Failed to rename file: {e}")
            raise

    def delete_file(self, path: str, force: bool = False) -> Dict[str, Any]:
        """
        Hapus file
        
        Args:
            path: Path file
            force: Force delete (ignore errors)
        
        Returns:
            Dict dengan status dan metadata
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not self.allow_delete:
            raise PermissionError("Delete operation tidak diizinkan")
        
        try:
            full_path = self._resolve_path(path)
            
            if not full_path.exists():
                raise FileNotFoundError(f"File tidak ditemukan: {path}")
            
            if not full_path.is_file():
                raise IsADirectoryError(f"Path adalah direktori: {path}")
            
            # Hapus
            full_path.unlink()
            self.total_deletes += 1
            
            if self.verbose:
                print(f"[DEBUG] File deleted: {path}")
            
            return {
                'success': True,
                'path': str(full_path),
                'message': f"File berhasil dihapus: {path}"
            }
            
        except Exception as e:
            self.total_errors += 1
            if force:
                print(f"[WARNING] Force delete failed for {path}: {e}")
                return {
                    'success': False,
                    'path': path,
                    'error': str(e),
                    'message': f"Gagal menghapus file: {path}"
                }
            else:
                print(f"[ERROR] Failed to delete file {path}: {e}")
                raise

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """
        Ambil informasi file
        
        Args:
            path: Path file
        
        Returns:
            Dict dengan info file
        """
        # STATUS: OK - Method berjalan normal
        try:
            full_path = self._resolve_path(path)
            
            if not full_path.exists():
                raise FileNotFoundError(f"File tidak ditemukan: {path}")
            
            stat = full_path.stat()
            
            info = {
                'name': full_path.name,
                'path': str(full_path),
                'exists': True,
                'is_file': full_path.is_file(),
                'is_dir': full_path.is_dir(),
                'size': stat.st_size if full_path.is_file() else 0,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'parent': str(full_path.parent),
                'extension': full_path.suffix if full_path.is_file() else None
            }
            
            if self.verbose:
                print(f"[DEBUG] File info: {path}")
            
            return info
            
        except Exception as e:
            self.total_errors += 1
            print(f"[ERROR] Failed to get file info {path}: {e}")
            raise

    def create_directory(self, path: str, exist_ok: bool = True) -> Dict[str, Any]:
        """
        Buat direktori baru
        
        Args:
            path: Path direktori
            exist_ok: Tidak error jika sudah ada
        
        Returns:
            Dict dengan status dan metadata
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not self.allow_write:
            raise PermissionError("Write operation tidak diizinkan")
        
        try:
            full_path = self._resolve_path(path)
            
            full_path.mkdir(parents=True, exist_ok=exist_ok)
            
            if self.verbose:
                print(f"[DEBUG] Directory created: {path}")
            
            return {
                'success': True,
                'path': str(full_path),
                'message': f"Direktori berhasil dibuat: {path}"
            }
            
        except Exception as e:
            self.total_errors += 1
            print(f"[ERROR] Failed to create directory {path}: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        Ambil statistik filesystem server
        
        Returns:
            Dict statistik
        """
        # STATUS: OK - Method berjalan normal
        return {
            'total_reads': self.total_reads,
            'total_writes': self.total_writes,
            'total_deletes': self.total_deletes,
            'total_errors': self.total_errors,
            'base_path': str(self.base_path),
            'allow_write': self.allow_write,
            'allow_delete': self.allow_delete,
            'max_file_size': self.max_file_size
        }


# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING FILESYSTEM SERVER")
    print("=" * 50)
    
    # Inisialisasi
    print("\n[TEST] Init FileSystemServer")
    server = FileSystemServer(
        base_path="./test_fs",
        allow_write=True,
        allow_delete=True,
        verbose=True
    )
    
    # Test write file
    print("\n[TEST] Write file")
    result = server.write_file("test.txt", "Hello, MCP Filesystem Server!")
    print(f"Write result: {result}")
    
    # Test read file
    print("\n[TEST] Read file")
    content = server.read_file("test.txt")
    print(f"Content: {content}")
    
    # Test list directory
    print("\n[TEST] List directory")
    items = server.list_directory(".")
    print(f"Items: {len(items)}")
    for item in items[:3]:
        print(f"  {item['name']} ({'file' if item['is_file'] else 'dir'})")
    
    # Test count pdf
    print("\n[TEST] Count PDF")
    # Buat dummy pdf
    server.write_file("dummy.pdf", "Dummy PDF content")
    pdf_count = server.count_pdf(".")
    print(f"PDF count: {pdf_count}")
    
    # Test search
    print("\n[TEST] Search files")
    results = server.search_files(".", "*.txt")
    print(f"Found: {len(results)} txt files")
    
    # Test file info
    print("\n[TEST] File info")
    info = server.get_file_info("test.txt")
    print(f"Info: {info}")
    
    # Test rename
    print("\n[TEST] Rename file")
    result = server.rename_file("test.txt", "renamed.txt")
    print(f"Rename result: {result}")
    
    # Test delete
    print("\n[TEST] Delete file")
    result = server.delete_file("renamed.txt")
    print(f"Delete result: {result}")
    server.delete_file("dummy.pdf")
    
    # Test stats
    print("\n[TEST] Get stats")
    stats = server.get_stats()
    print(f"Stats: {stats}")
    
    # Cleanup
    print("\n[TEST] Cleanup")
    import shutil
    shutil.rmtree("./test_fs")
    print("Test directory removed")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)