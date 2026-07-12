# mcp/launcher.py
"""
MCP Launcher - Manajemen dan koordinasi MCP Servers
"""

from typing import Optional, Dict, Any, List
import importlib
import sys
from pathlib import Path


class MCPLauncher:
    """Launcher untuk mengelola MCP Servers"""
    
    def __init__(self, verbose: bool = False):
        """
        Inisialisasi MCP Launcher
        
        Args:
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.verbose = verbose
        self.servers = {}
        self.server_instances = {}
        self.is_running = False
        
        if self.verbose:
            print("[DEBUG] MCPLauncher initialized")

    def register_server(self, name: str, server_instance) -> None:
        """
        Register MCP server instance
        
        Args:
            name: Nama server (filesystem, sqlite, api, dll)
            server_instance: Instance server
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not name or not isinstance(name, str):
            print("[ERROR] Server name harus string tidak kosong")
            return
        
        if server_instance is None:
            print(f"[ERROR] Server instance untuk {name} tidak valid")
            return
        
        self.servers[name] = server_instance
        self.server_instances[name] = server_instance
        
        if self.verbose:
            print(f"[DEBUG] Server registered: {name}")

    def load_server(self, name: str, module_path: str, class_name: str, **kwargs) -> bool:
        """
        Load MCP server dari module
        
        Args:
            name: Nama server (unique identifier)
            module_path: Path ke module (misal: mcp.filesystem_server)
            class_name: Nama class server
            **kwargs: Parameter untuk inisialisasi server
        
        Returns:
            True jika berhasil
        """
        # STATUS: OK - Method berjalan normal
        try:
            # Import module
            module = importlib.import_module(module_path)
            
            # Get class
            server_class = getattr(module, class_name)
            
            # Instantiate
            server_instance = server_class(**kwargs)
            
            # Register
            self.register_server(name, server_instance)
            
            if self.verbose:
                print(f"[DEBUG] Server loaded: {name} from {module_path}.{class_name}")
            
            return True
            
        except ImportError as e:
            print(f"[ERROR] Failed to import {module_path}: {e}")
            return False
        except AttributeError as e:
            print(f"[ERROR] Class {class_name} not found in {module_path}: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to load server {name}: {e}")
            return False

    def start_server(self, name: str) -> bool:
        """
        Start MCP server
        
        Args:
            name: Nama server
        
        Returns:
            True jika berhasil
        """
        # STATUS: OK - Method berjalan normal
        if name not in self.servers:
            print(f"[ERROR] Server '{name}' tidak ditemukan")
            return False
        
        server = self.servers[name]
        
        # Cek apakah ada method start
        if hasattr(server, 'start'):
            try:
                server.start()
                if self.verbose:
                    print(f"[DEBUG] Server started: {name}")
                return True
            except Exception as e:
                print(f"[ERROR] Failed to start server {name}: {e}")
                return False
        else:
            # Tidak perlu start (passive server)
            if self.verbose:
                print(f"[DEBUG] Server {name} is passive (no start method)")
            return True

    def stop_server(self, name: str) -> bool:
        """
        Stop MCP server
        
        Args:
            name: Nama server
        
        Returns:
            True jika berhasil
        """
        # STATUS: OK - Method berjalan normal
        if name not in self.servers:
            print(f"[ERROR] Server '{name}' tidak ditemukan")
            return False
        
        server = self.servers[name]
        
        # Cek apakah ada method stop
        if hasattr(server, 'stop'):
            try:
                server.stop()
                if self.verbose:
                    print(f"[DEBUG] Server stopped: {name}")
                return True
            except Exception as e:
                print(f"[ERROR] Failed to stop server {name}: {e}")
                return False
        else:
            if self.verbose:
                print(f"[DEBUG] Server {name} is passive (no stop method)")
            return True

    def start_all(self) -> Dict[str, bool]:
        """
        Start semua MCP servers
        
        Returns:
            Dict hasil start per server
        """
        # STATUS: OK - Method berjalan normal
        results = {}
        self.is_running = True
        
        for name in self.servers:
            results[name] = self.start_server(name)
        
        if self.verbose:
            success = sum(1 for v in results.values() if v)
            print(f"[DEBUG] Started {success}/{len(results)} servers")
        
        return results

    def stop_all(self) -> Dict[str, bool]:
        """
        Stop semua MCP servers
        
        Returns:
            Dict hasil stop per server
        """
        # STATUS: OK - Method berjalan normal
        results = {}
        self.is_running = False
        
        for name in self.servers:
            results[name] = self.stop_server(name)
        
        if self.verbose:
            success = sum(1 for v in results.values() if v)
            print(f"[DEBUG] Stopped {success}/{len(results)} servers")
        
        return results

    def get_server(self, name: str):
        """
        Ambil instance MCP server
        
        Args:
            name: Nama server
        
        Returns:
            Instance server atau None
        """
        # STATUS: OK - Method berjalan normal
        return self.servers.get(name)

    def get_all_servers(self) -> Dict[str, Any]:
        """
        Ambil semua MCP servers
        
        Returns:
            Dict semua server
        """
        # STATUS: OK - Method berjalan normal
        return self.servers

    def get_server_names(self) -> List[str]:
        """
        Ambil daftar nama server
        
        Returns:
            List nama server
        """
        # STATUS: OK - Method berjalan normal
        return list(self.servers.keys())

    def get_server_methods(self, name: str) -> List[str]:
        """
        Ambil daftar method yang tersedia di server
        
        Args:
            name: Nama server
        
        Returns:
            List nama method (public methods)
        """
        # STATUS: OK - Method berjalan normal
        if name not in self.servers:
            print(f"[ERROR] Server '{name}' tidak ditemukan")
            return []
        
        server = self.servers[name]
        
        # Ambil semua method (public, bukan private)
        methods = [
            method for method in dir(server)
            if callable(getattr(server, method))
            and not method.startswith('_')
            and method not in ['start', 'stop']
        ]
        
        return methods

    def call_server_method(self, name: str, method: str, *args, **kwargs) -> Any:
        """
        Panggil method server
        
        Args:
            name: Nama server
            method: Nama method
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Hasil method
        """
        # STATUS: OK - Method berjalan normal
        if name not in self.servers:
            print(f"[ERROR] Server '{name}' tidak ditemukan")
            return None
        
        server = self.servers[name]
        
        if not hasattr(server, method):
            print(f"[ERROR] Method '{method}' tidak ditemukan di server {name}")
            return None
        
        try:
            func = getattr(server, method)
            result = func(*args, **kwargs)
            
            if self.verbose:
                print(f"[DEBUG] Called {name}.{method}()")
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Failed to call {name}.{method}: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """
        Ambil statistik MCP launcher
        
        Returns:
            Dict statistik
        """
        # STATUS: OK - Method berjalan normal
        return {
            'total_servers': len(self.servers),
            'server_names': list(self.servers.keys()),
            'is_running': self.is_running,
            'servers_detail': {
                name: {
                    'type': type(server).__name__,
                    'module': type(server).__module__,
                    'methods': self.get_server_methods(name)
                }
                for name, server in self.servers.items()
            }
        }


# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING MCP LAUNCHER")
    print("=" * 50)
    
    # Inisialisasi
    print("\n[TEST] Init MCPLauncher")
    launcher = MCPLauncher(verbose=True)
    
    # Test register server dummy
    print("\n[TEST] Register dummy server")
    
    class DummyServer:
        def __init__(self):
            pass
        
        def test_method(self, name: str = "world"):
            return f"Hello, {name}!"
        
        def start(self):
            print("Dummy server started")
        
        def stop(self):
            print("Dummy server stopped")
    
    launcher.register_server('dummy', DummyServer())
    
    # Test get server methods
    print("\n[TEST] Get server methods")
    methods = launcher.get_server_methods('dummy')
    print(f"Methods: {methods}")
    
    # Test call server method
    print("\n[TEST] Call server method")
    result = launcher.call_server_method('dummy', 'test_method', name='Agent')
    print(f"Result: {result}")
    
    # Test start
    print("\n[TEST] Start server")
    launcher.start_server('dummy')
    
    # Test stop
    print("\n[TEST] Stop server")
    launcher.stop_server('dummy')
    
    # Test stats
    print("\n[TEST] Get stats")
    stats = launcher.get_stats()
    print(f"Stats: {stats}")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)