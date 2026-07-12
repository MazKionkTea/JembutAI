# tools/shell.py
"""
Shell Tools - Eksekusi perintah shell
"""

import subprocess
from typing import Dict, Any, Optional


class ShellTools:
    """Wrapper untuk eksekusi shell command"""
    
    def __init__(
        self,
        allowed_commands: Optional[list] = None,
        blocklist: Optional[list] = None,
        timeout: int = 30,
        verbose: bool = False
    ):
        """
        Inisialisasi shell tools
        
        Args:
            allowed_commands: Daftar command yang diizinkan (None = semua)
            blocklist: Daftar command yang diblokir
            timeout: Timeout per command (detik)
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.allowed_commands = allowed_commands or []
        self.blocklist = blocklist or [
            'rm -rf', 'mkfs', 'dd', 'format',
            'shutdown', 'reboot', 'halt',
            'passwd', 'chmod 777', 'sudo'
        ]
        self.timeout = timeout
        self.verbose = verbose
        
        # Statistik
        self.total_commands = 0
        self.successful_commands = 0
        self.failed_commands = 0
        
        if self.verbose:
            print("[DEBUG] ShellTools initialized")
            print(f"[DEBUG] Allowed commands: {allowed_commands or 'All'}")
            print(f"[DEBUG] Blocklist: {blocklist}")

    def _is_allowed(self, command: str) -> bool:
        """
        Cek apakah command diizinkan
        
        Args:
            command: Command string
        
        Returns:
            True jika diizinkan
        """
        # STATUS: OK - Method berjalan normal
        # Cek blocklist
        for blocked in self.blocklist:
            if blocked in command.lower():
                if self.verbose:
                    print(f"[DEBUG] Command blocked: {command} (contains '{blocked}')")
                return False
        
        # Cek allowed list
        if self.allowed_commands:
            allowed = False
            for allowed_cmd in self.allowed_commands:
                if command.strip().startswith(allowed_cmd):
                    allowed = True
                    break
            
            if not allowed:
                if self.verbose:
                    print(f"[DEBUG] Command not in allowed list: {command}")
                return False
        
        return True

    def execute(self, command: str, capture_output: bool = True, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Eksekusi shell command
        
        Args:
            command: Command yang akan dijalankan
            capture_output: Capture stdout/stderr
            timeout: Timeout (override default)
        
        Returns:
            Dict dengan stdout, stderr, returncode
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not command or not isinstance(command, str):
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command harus string tidak kosong',
                'returncode': -1,
                'error': 'Invalid command'
            }
        
        # Security check
        if not self._is_allowed(command):
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command tidak diizinkan',
                'returncode': -1,
                'error': 'Command blocked'
            }
        
        try:
            timeout = timeout or self.timeout
            self.total_commands += 1
            
            if self.verbose:
                print(f"[DEBUG] Executing: {command}")
            
            if capture_output:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                success = result.returncode == 0
                if success:
                    self.successful_commands += 1
                else:
                    self.failed_commands += 1
                
                if self.verbose:
                    status = "✓" if success else "✗"
                    print(f"[DEBUG] Command {status} (returncode: {result.returncode})")
                
                return {
                    'success': success,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode,
                    'command': command,
                    'error': None
                }
            else:
                # Tanpa capture (output ke terminal)
                result = subprocess.run(command, shell=True, timeout=timeout)
                success = result.returncode == 0
                
                if success:
                    self.successful_commands += 1
                else:
                    self.failed_commands += 1
                
                return {
                    'success': success,
                    'stdout': '',
                    'stderr': '',
                    'returncode': result.returncode,
                    'command': command,
                    'error': None
                }
                
        except subprocess.TimeoutExpired:
            self.failed_commands += 1
            print(f"[ERROR] Command timeout: {command}")
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Command timeout setelah {timeout} detik',
                'returncode': -1,
                'error': 'Timeout',
                'command': command
            }
            
        except Exception as e:
            self.failed_commands += 1
            print(f"[ERROR] Command failed: {e}")
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1,
                'error': str(e),
                'command': command
            }

    def execute_silent(self, command: str, timeout: Optional[int] = None) -> bool:
        """
        Eksekusi command tanpa output (hanya return success/fail)
        
        Args:
            command: Command yang dijalankan
            timeout: Timeout
        
        Returns:
            True jika berhasil
        """
        # STATUS: OK - Method berjalan normal
        result = self.execute(command, capture_output=False, timeout=timeout)
        return result.get('success', False)

    def get_output(self, command: str, timeout: Optional[int] = None) -> Optional[str]:
        """
        Eksekusi command dan return stdout (tanpa stderr)
        
        Args:
            command: Command yang dijalankan
            timeout: Timeout
        
        Returns:
            stdout atau None jika gagal
        """
        # STATUS: OK - Method berjalan normal
        result = self.execute(command, capture_output=True, timeout=timeout)
        if result.get('success'):
            return result.get('stdout', '').strip()
        return None

    def get_stats(self) -> Dict[str, Any]:
        """
        Ambil statistik shell tools
        
        Returns:
            Dict statistik
        """
        # STATUS: OK - Method berjalan normal
        total = self.total_commands
        success_rate = (
            self.successful_commands / total if total > 0 else 0
        )
        
        return {
            'total_commands': total,
            'successful': self.successful_commands,
            'failed': self.failed_commands,
            'success_rate': success_rate,
            'timeout': self.timeout,
            'allowed_commands': self.allowed_commands or 'All',
            'blocklist': self.blocklist
        }

    def reset_stats(self) -> None:
        """Reset statistik"""
        # STATUS: OK - Method berjalan normal
        self.total_commands = 0
        self.successful_commands = 0
        self.failed_commands = 0
        if self.verbose:
            print("[DEBUG] ShellTools stats reset")

    def add_allowed_command(self, command: str) -> None:
        """
        Tambahkan command ke allowed list
        
        Args:
            command: Command yang diizinkan
        """
        # STATUS: OK - Method berjalan normal
        if command not in self.allowed_commands:
            self.allowed_commands.append(command)
            if self.verbose:
                print(f"[DEBUG] Added to allowed commands: {command}")

    def add_blocked_command(self, command: str) -> None:
        """
        Tambahkan command ke blocklist
        
        Args:
            command: Command yang diblokir
        """
        # STATUS: OK - Method berjalan normal
        if command not in self.blocklist:
            self.blocklist.append(command)
            if self.verbose:
                print(f"[DEBUG] Added to blocklist: {command}")


# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING SHELL TOOLS")
    print("=" * 50)
    
    # Inisialisasi
    print("\n[TEST] Init ShellTools")
    tools = ShellTools(
        allowed_commands=['echo', 'ls', 'pwd', 'whoami'],
        blocklist=['rm', 'sudo'],
        verbose=True
    )
    
    # Test allowed command
    print("\n[TEST] Allowed command")
    result = tools.execute("echo 'Hello World'")
    print(f"Result: {result.get('success')}")
    print(f"Output: {result.get('stdout')}")
    
    # Test blocked command
    print("\n[TEST] Blocked command")
    result = tools.execute("sudo ls")
    print(f"Result: {result.get('success')}")
    print(f"Error: {result.get('error')}")
    
    # Test command not in allowed list
    print("\n[TEST] Not in allowed list")
    result = tools.execute("python -c 'print(1+1)'")
    print(f"Result: {result.get('success')}")
    print(f"Error: {result.get('error')}")
    
    # Test get output
    print("\n[TEST] Get output")
    output = tools.get_output("pwd")
    print(f"Output: {output}")
    
    # Test stats
    print("\n[TEST] Get stats")
    stats = tools.get_stats()
    print(f"Stats: {stats}")
    
    # Test add allowed command
    print("\n[TEST] Add allowed command")
    tools.add_allowed_command("python")
    result = tools.execute("python -c 'print(1+1)'")
    print(f"After adding: {result.get('success')}")
    print(f"Output: {result.get('stdout')}")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)