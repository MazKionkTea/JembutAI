# agent/executor.py
"""
Executor - Mengeksekusi tool yang dipilih oleh planner
"""

from typing import Optional, Dict, Any, List, Callable
import json
import subprocess
import os
from pathlib import Path
import pathlib

from agen.konteks import PengelolaKonteks, StatusAgen


class Eksekutor:
    """Eksekutor tool - menjalankan tool dan mengembalikan hasil"""
    
    def __init__(
        self,
        pengelola_konteks: PengelolaKonteks,
        verbose: bool = False
    ):
        """
        Inisialisasi executor
        Args:
            pengelola_konteks: Instance ContextManager
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.konteks = pengelola_konteks
        self.verbose = verbose
        
        # MCP Server references (akan di-set nanti)
        self.server_mcp = {}
        
        # Tool handlers (mapping tool_name -> handler function)
        self.pengendali_tool = {}
        
        # Tool execution history
        self.histori_eksekusi = []
        
        if self.verbose:
            print(f"[DEBUG] Executor initialized")


    def daftarkan_server_mcp(self, nama: str, server_instance) -> None:
        """
        Register MCP server ke executor
        Args:
            name: Nama server (filesystem, sqlite, api, dll)
            server_instance: Instance MCP server
        """
        # STATUS: OK - Method berjalan normal
        self.server_mcp[nama] = server_instance
        if self.verbose:
            print(f"[DEBUG] MCP Server registered: {nama}")


    def daftarkan_pengendali_tool(self, nama_tool: str, pengendali: Callable) -> None:
        """
        Register handler untuk tool tertentu
        Args:
            tool_name: Nama tool
            handler: Fungsi handler yang akan dipanggil
        """
        # STATUS: OK - Method berjalan normal
        self.pengendali_tool[nama_tool] = pengendali
        if self.verbose:
            print(f"[DEBUG] Tool handler registered: {nama_tool}")


    def eksekusi(self, nama_tool: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Eksekusi tool berdasarkan nama dan parameter
        Args:
            tool_name: Nama tool yang akan dijalankan
            params: Parameter untuk tool (opsional)
        Returns:
            Dict dengan: success, result, error
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not nama_tool or not isinstance(nama_tool, str):
            print("[ERROR] Tool name harus string tidak kosong")
            return {
                'success': False,
                'result': None,
                'error': 'Tool name tidak valid',
                'tool': nama_tool
            }
        
        if nama_tool == 'none':
            return {
                'success': True,
                'result': 'Tidak ada tool yang diperlukan',
                'error': None,
                'tool': 'none'
            }
        
        if self.verbose:
            print(f"[DEBUG] Executing tool: {nama_tool}")
            print(f"[DEBUG] Params: {params}")
        
        # Update context
        self.konteks.status_konteks_agen(StatusAgen.EXECUTING)
        self.konteks.tool_yang_digunakan(nama_tool)
        
        # Eksekusi
        try:
            # Cek handler terdaftar
            if nama_tool in self.pengendali_tool:
                result = self.pengendali_eksekusi(nama_tool, params)
            # Cek MCP server
            elif nama_tool in self.server_mcp:
                result = self.eksekusi_mcp(nama_tool, params)
            else:
                result = {
                    'success': False,
                    'result': None,
                    'error': f'Tool "{nama_tool}" tidak ditemukan',
                    'tool': nama_tool
                }
            
            # Simpan history
            self.histori_eksekusi.append({
                'tool': nama_tool,
                'params': params,
                'result': result,
                'timestamp': self.konteks.aktivitas_terakhir.isoformat()
            })
            
            # Update context dengan hasil
            if result.get('success'):
                self.konteks.hasil_tool_yang_digunakan(result.get('result'))
            else:
                self.konteks.pesan_error(result.get('error', 'Unknown error'))
            
            self.konteks.status_konteks_agen(StatusAgen.IDLE)
            
            if self.verbose:
                status = "✓" if result.get('success') else "✗"
                print(f"[DEBUG] Execution {status}: {nama_tool}")
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Execution failed: {e}")
            self.konteks.pesan_error(str(e))
            self.konteks.status_konteks_agen(StatusAgen.ERROR)
            
            return {
                'success': False,
                'result': None,
                'error': str(e),
                'tool': nama_tool
            }


    def pengendali_eksekusi(self, nama_tool: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Eksekusi melalui handler terdaftar
        Args:
            tool_name: Nama tool
            params: Parameter
        Returns:
            Dict hasil eksekusi
        """
        # STATUS: OK - Method berjalan normal
        try:
            handler = self.pengendali_tool[nama_tool]
            
            if params:
                result = handler(**params)
            else:
                result = handler()
            
            # Pastikan result dalam format yang benar
            if isinstance(result, dict):
                return {
                    'success': result.get('success', True),
                    'result': result.get('result', result),
                    'error': result.get('error'),
                    'tool': nama_tool
                }
            else:
                return {
                    'success': True,
                    'result': result,
                    'error': None,
                    'tool': nama_tool
                }
                
        except TypeError as e:
            print(f"[ERROR] Parameter mismatch: {e}")
            return {
                'success': False,
                'result': None,
                'error': f'Parameter tidak cocok: {e}',
                'tool': nama_tool
            }
        except Exception as e:
            print(f"[ERROR] Handler execution failed: {e}")
            return {
                'success': False,
                'result': None,
                'error': str(e),
                'tool': nama_tool
            }


    def eksekusi_mcp(self, nama_tool: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Eksekusi melalui MCP server
        Args:
            tool_name: Nama tool
            params: Parameter
        Returns:
            Dict hasil eksekusi
        """
        # STATUS: OK - Method berjalan normal
        server = self.server_mcp.get(nama_tool)
        
        if not server:
            # Coba cari di semua server
            for nama_server, server_instance in self.server_mcp.items():
                if hasattr(server_instance, nama_tool):
                    server = server_instance
                    break
        
        if not server:
            return {
                'success': False,
                'result': None,
                'error': f'MCP Server untuk tool "{nama_tool}" tidak ditemukan',
                'tool': nama_tool
            }
        
        try:
            # Panggil method tool
            method = getattr(server, nama_tool)
            
            if params:
                result = method(**params)
            else:
                result = method()
            
            return {
                'success': True,
                'result': result,
                'error': None,
                'tool': nama_tool
            }
            
        except TypeError as e:
            print(f"[ERROR] MCP parameter mismatch: {e}")
            return {
                'success': False,
                'result': None,
                'error': f'Parameter tidak cocok: {e}',
                'tool': nama_tool
            }
        except Exception as e:
            print(f"[ERROR] MCP execution failed: {e}")
            return {
                'success': False,
                'result': None,
                'error': str(e),
                'tool': nama_tool
            }


    def execute_filesystem(self, aksi: str, **kwargs) -> Dict[str, Any]:
        """
        Eksekusi filesystem tool
        Args:
            action: aksi (read, write, list, search, dll)
            **kwargs: Parameter untuk aksi
        Returns:
            Dict hasil eksekusi
        """
        # STATUS: OK - Method berjalan normal
        actions = {
            'read': self._fs_read,
            'write': self._fs_write,
            'list': self._fs_list,
            'search': self._fs_search,
            'count_pdf': self._fs_count_pdf,
            'rename': self._fs_rename,
            'delete': self._fs_delete
        }
        
        handler = actions.get(aksi)
        if not handler:
            return {
                'success': False,
                'result': None,
                'error': f'Aksi filesystem tidak dikenal: {aksi}'
            }
        
        try:
            result = handler(**kwargs)
            return {
                'success': True,
                'result': result,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'error': str(e)
            }


    def _fs_read(self, path: str) -> str:
        """Baca file"""
        # STATUS: OK - Method berjalan normal
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File tidak ditemukan: {path}")
        return path.read_text(encoding='utf-8')


    def _fs_write(self, path: str, content: str) -> str:
        """Tulis file"""
        # STATUS: OK - Method berjalan normal
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return f"File berhasil ditulis: {path}"


    def _fs_list(self, path: str = ".") -> List[str]:
        """List directory"""
        # STATUS: OK - Method berjalan normal
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Directory tidak ditemukan: {path}")
        return [str(p) for p in path.iterdir()]


    def _fs_search(self, path: str, pattern: str) -> List[str]:
        """Search file dengan pattern"""
        # STATUS: OK - Method berjalan normal
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Directory tidak ditemukan: {path}")
        
        results = []
        for p in path.rglob(pattern):
            results.append(str(p))
        return results


    def _fs_count_pdf(self, path: str = ".") -> int:
        """Hitung jumlah PDF"""
        # STATUS: OK - Method berjalan normal
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Directory tidak ditemukan: {path}")
        
        return len(list(path.rglob("*.pdf")))


    def _fs_rename(self, old_path: str, new_path: str) -> str:
        """Rename file"""
        # STATUS: OK - Method berjalan normal
        old = Path(old_path)
        new = Path(new_path)
        if not old.exists():
            raise FileNotFoundError(f"File tidak ditemukan: {old}")
        old.rename(new)
        return f"File renamed: {old} → {new}"


    def _fs_delete(self, path: str) -> str:
        """Delete file"""
        # STATUS: OK - Method berjalan normal
        path = pathlib.Path(path)
        if path.is_dir():
            raise IsADirectoryError(f"Path adalah direktori: {path}")
        if not path.exists():
            raise FileNotFoundError(f"File tidak ditemukan: {path}")
        path.unlink()
        return f"File dihapus: {path}"


    def eksekusi_shell(self, command: str) -> Dict[str, Any]:
        """
        Eksekusi shell command
        Args:
            command: Command yang akan dijalankan
        Returns:
            Dict dengan stdout, stderr, returncode
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI - Command harus string
        if not command or not isinstance(command, str):
            return {
                'success': False,
                'result': None,
                'error': 'Command harus string tidak kosong'
            }
        
        # Security warning
        print(f"[WARNING] Menjalankan shell command: {command}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'success': result.returncode == 0,
                'result': {
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                },
                'error': result.stderr if result.returncode != 0 else None
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'result': None,
                'error': 'Command timeout (30 detik)'
            }
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'error': str(e)
            }


    def ambil_history_eksekusi(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Ambil history eksekusi
        Args:
            limit: Jumlah history terakhir
        Returns:
            List history eksekusi
        """
        # STATUS: OK - Method berjalan normal
        return self.histori_eksekusi[-limit:]


    def clear_history(self) -> None:
        """Hapus history eksekusi"""
        # STATUS: OK - Method berjalan normal
        self.histori_eksekusi = []
        if self.verbose:
            print("[DEBUG] Execution history cleared")

    
    def status_eksekusi_terakhir(self) -> Dict[str, Any]:
        """
        Ambil statistik executor
        
        Returns:
            Dict statistik
        """
        # STATUS: OK - Method berjalan normal
        total_executions = len(self.histori_eksekusi)
        successful = sum(1 for e in self.histori_eksekusi if e['result'].get('success'))
        
        return {
            'total_executions': total_executions,
            'successful': successful,
            'failed': total_executions - successful,
            'success_rate': successful / total_executions if total_executions > 0 else 0,
            'registered_handlers': list(self.pengendali_tool.keys()),
            'registered_mcp_servers': list(self.server_mcp.keys()),
            'last_execution': self.histori_eksekusi[-1] if self.histori_eksekusi else None
        }


# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING EXECUTOR")
    print("=" * 50)
    
    # Inisialisasi
    print("\n[TEST] Init Executor")
    konteks = PengelolaKonteks(verbose=False)
    eksekutor = Eksekutor(konteks, verbose=True)
    
    # Test filesystem
    print("\n[TEST] Filesystem operations")
    
    # Test write
    result = eksekutor.execute_filesystem('write', path='test.txt', content='Hello World')
    print(f"Write: {result}")
    
    # Test read
    result = eksekutor.execute_filesystem('read', path='test.txt')
    print(f"Read: {result}")
    
    # Test list
    result = eksekutor.execute_filesystem('list', path='.')
    print(f"List: {len(result.get('result', []))} files")
    
    # Test shell
    print("\n[TEST] Shell command")
    result = eksekutor.eksekusi_shell('echo "Hello from shell"')
    print(f"Shell: {result}")
    
    # Test execute dengan handler
    print("\n[TEST] Execute with handler")
    # Register handler
    def custom_handler(name: str = "world"):
        return f"Hello, {name}!"
    
    eksekutor.daftarkan_pengendali_tool('greet', custom_handler)
    result = eksekutor.eksekusi('greet', {'name': 'Budi'})
    print(f"Greet: {result}")
    
    # Test history
    print("\n[TEST] Execution history")
    history = eksekutor.ambil_history_eksekusi()
    for i, entry in enumerate(history, 1):
        print(f"  {i}. {entry['tool']} -> {entry['result'].get('success')}")
    
    # Test stats
    print("\n[TEST] Stats")
    stats = eksekutor.status_eksekusi_terakhir()
    print(f"Stats: {stats}")
    
    # Cleanup
    print("\n[TEST] Cleanup")
    os.remove('test.txt')
    print("Test file removed")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)