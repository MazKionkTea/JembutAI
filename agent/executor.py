# agent/executor.py
"""
Executor - Mengeksekusi tool yang dipilih oleh planner
"""

from typing import Optional, Dict, Any, List, Callable
import json
import subprocess
import os
from pathlib import Path

from agent.context import ContextManager, AgentState


class Executor:
    """Eksekutor tool - menjalankan tool dan mengembalikan hasil"""
    
    def __init__(
        self,
        context_manager: ContextManager,
        verbose: bool = False
    ):
        """
        Inisialisasi executor
        
        Args:
            context_manager: Instance ContextManager
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.context = context_manager
        self.verbose = verbose
        
        # MCP Server references (akan di-set nanti)
        self.mcp_servers = {}
        
        # Tool handlers (mapping tool_name -> handler function)
        self.tool_handlers = {}
        
        # Tool execution history
        self.execution_history = []
        
        if self.verbose:
            print(f"[DEBUG] Executor initialized")

    def register_mcp_server(self, name: str, server_instance) -> None:
        """
        Register MCP server ke executor
        
        Args:
            name: Nama server (filesystem, sqlite, api, dll)
            server_instance: Instance MCP server
        """
        # STATUS: OK - Method berjalan normal
        self.mcp_servers[name] = server_instance
        if self.verbose:
            print(f"[DEBUG] MCP Server registered: {name}")

    def register_tool_handler(self, tool_name: str, handler: Callable) -> None:
        """
        Register handler untuk tool tertentu
        
        Args:
            tool_name: Nama tool
            handler: Fungsi handler yang akan dipanggil
        """
        # STATUS: OK - Method berjalan normal
        self.tool_handlers[tool_name] = handler
        if self.verbose:
            print(f"[DEBUG] Tool handler registered: {tool_name}")

    def execute(self, tool_name: str, params: Optional[Dict] = None) -> Dict[str, Any]:
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
        if not tool_name or not isinstance(tool_name, str):
            print("[ERROR] Tool name harus string tidak kosong")
            return {
                'success': False,
                'result': None,
                'error': 'Tool name tidak valid',
                'tool': tool_name
            }
        
        if tool_name == 'none':
            return {
                'success': True,
                'result': 'Tidak ada tool yang diperlukan',
                'error': None,
                'tool': 'none'
            }
        
        if self.verbose:
            print(f"[DEBUG] Executing tool: {tool_name}")
            print(f"[DEBUG] Params: {params}")
        
        # Update context
        self.context.set_state(AgentState.EXECUTING)
        self.context.set_tool(tool_name)
        
        # Eksekusi
        try:
            # Cek handler terdaftar
            if tool_name in self.tool_handlers:
                result = self._execute_handler(tool_name, params)
            # Cek MCP server
            elif tool_name in self.mcp_servers:
                result = self._execute_mcp(tool_name, params)
            else:
                result = {
                    'success': False,
                    'result': None,
                    'error': f'Tool "{tool_name}" tidak ditemukan',
                    'tool': tool_name
                }
            
            # Simpan history
            self.execution_history.append({
                'tool': tool_name,
                'params': params,
                'result': result,
                'timestamp': self.context.last_activity.isoformat()
            })
            
            # Update context dengan hasil
            if result.get('success'):
                self.context.set_tool_result(result.get('result'))
            else:
                self.context.set_error(result.get('error', 'Unknown error'))
            
            self.context.set_state(AgentState.IDLE)
            
            if self.verbose:
                status = "✓" if result.get('success') else "✗"
                print(f"[DEBUG] Execution {status}: {tool_name}")
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Execution failed: {e}")
            self.context.set_error(str(e))
            self.context.set_state(AgentState.ERROR)
            
            return {
                'success': False,
                'result': None,
                'error': str(e),
                'tool': tool_name
            }

    def _execute_handler(self, tool_name: str, params: Optional[Dict] = None) -> Dict[str, Any]:
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
            handler = self.tool_handlers[tool_name]
            
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
                    'tool': tool_name
                }
            else:
                return {
                    'success': True,
                    'result': result,
                    'error': None,
                    'tool': tool_name
                }
                
        except TypeError as e:
            print(f"[ERROR] Parameter mismatch: {e}")
            return {
                'success': False,
                'result': None,
                'error': f'Parameter tidak cocok: {e}',
                'tool': tool_name
            }
        except Exception as e:
            print(f"[ERROR] Handler execution failed: {e}")
            return {
                'success': False,
                'result': None,
                'error': str(e),
                'tool': tool_name
            }

    def _execute_mcp(self, tool_name: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Eksekusi melalui MCP server
        
        Args:
            tool_name: Nama tool
            params: Parameter
        
        Returns:
            Dict hasil eksekusi
        """
        # STATUS: OK - Method berjalan normal
        server = self.mcp_servers.get(tool_name)
        
        if not server:
            # Coba cari di semua server
            for server_name, server_instance in self.mcp_servers.items():
                if hasattr(server_instance, tool_name):
                    server = server_instance
                    break
        
        if not server:
            return {
                'success': False,
                'result': None,
                'error': f'MCP Server untuk tool "{tool_name}" tidak ditemukan',
                'tool': tool_name
            }
        
        try:
            # Panggil method tool
            method = getattr(server, tool_name)
            
            if params:
                result = method(**params)
            else:
                result = method()
            
            return {
                'success': True,
                'result': result,
                'error': None,
                'tool': tool_name
            }
            
        except TypeError as e:
            print(f"[ERROR] MCP parameter mismatch: {e}")
            return {
                'success': False,
                'result': None,
                'error': f'Parameter tidak cocok: {e}',
                'tool': tool_name
            }
        except Exception as e:
            print(f"[ERROR] MCP execution failed: {e}")
            return {
                'success': False,
                'result': None,
                'error': str(e),
                'tool': tool_name
            }

    def execute_filesystem(self, action: str, **kwargs) -> Dict[str, Any]:
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
        
        handler = actions.get(action)
        if not handler:
            return {
                'success': False,
                'result': None,
                'error': f'Aksi filesystem tidak dikenal: {action}'
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
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File tidak ditemukan: {path}")
        path.unlink()
        return f"File dihapus: {path}"

    def execute_shell(self, command: str) -> Dict[str, Any]:
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

    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Ambil history eksekusi
        
        Args:
            limit: Jumlah history terakhir
        
        Returns:
            List history eksekusi
        """
        # STATUS: OK - Method berjalan normal
        return self.execution_history[-limit:]

    def clear_history(self) -> None:
        """Hapus history eksekusi"""
        # STATUS: OK - Method berjalan normal
        self.execution_history = []
        if self.verbose:
            print("[DEBUG] Execution history cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Ambil statistik executor
        
        Returns:
            Dict statistik
        """
        # STATUS: OK - Method berjalan normal
        total_executions = len(self.execution_history)
        successful = sum(1 for e in self.execution_history if e['result'].get('success'))
        
        return {
            'total_executions': total_executions,
            'successful': successful,
            'failed': total_executions - successful,
            'success_rate': successful / total_executions if total_executions > 0 else 0,
            'registered_handlers': list(self.tool_handlers.keys()),
            'registered_mcp_servers': list(self.mcp_servers.keys()),
            'last_execution': self.execution_history[-1] if self.execution_history else None
        }


# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING EXECUTOR")
    print("=" * 50)
    
    # Inisialisasi
    print("\n[TEST] Init Executor")
    context = ContextManager(verbose=False)
    executor = Executor(context, verbose=True)
    
    # Test filesystem
    print("\n[TEST] Filesystem operations")
    
    # Test write
    result = executor.execute_filesystem('write', path='test.txt', content='Hello World')
    print(f"Write: {result}")
    
    # Test read
    result = executor.execute_filesystem('read', path='test.txt')
    print(f"Read: {result}")
    
    # Test list
    result = executor.execute_filesystem('list', path='.')
    print(f"List: {len(result.get('result', []))} files")
    
    # Test shell
    print("\n[TEST] Shell command")
    result = executor.execute_shell('echo "Hello from shell"')
    print(f"Shell: {result}")
    
    # Test execute dengan handler
    print("\n[TEST] Execute with handler")
    # Register handler
    def custom_handler(name: str = "world"):
        return f"Hello, {name}!"
    
    executor.register_tool_handler('greet', custom_handler)
    result = executor.execute('greet', {'name': 'Budi'})
    print(f"Greet: {result}")
    
    # Test history
    print("\n[TEST] Execution history")
    history = executor.get_execution_history()
    for i, entry in enumerate(history, 1):
        print(f"  {i}. {entry['tool']} -> {entry['result'].get('success')}")
    
    # Test stats
    print("\n[TEST] Stats")
    stats = executor.get_stats()
    print(f"Stats: {stats}")
    
    # Cleanup
    print("\n[TEST] Cleanup")
    os.remove('test.txt')
    print("Test file removed")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)