# configurasi.py
"""
Global Configuration - Konfigurasi untuk seluruh aplikasi
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import dotenv


class Konfigurasi:
    """Konfigurasi global aplikasi"""
    
    def __init__(self):
        """Inisialisasi konfigurasi dengan default values"""
        # STATUS: OK - Constructor berjalan normal

        
        # ========== PATHS ==========
        self.BASE_DIR = Path(__file__).parent
        self.MODELS_DIR = self.BASE_DIR / "models"
        self.DATABASE_DIR = self.BASE_DIR / "database"
        self.DOCUMENTS_DIR = self.BASE_DIR / "documents"
        self.LOGS_DIR = self.BASE_DIR / "logs"
        self.CACHE_DIR = self.BASE_DIR / "cache"
        self.ENV = dotenv.load_dotenv(".env")
        
        # Buat direktori jika belum ada
        for dir_path in [self.MODELS_DIR, self.DATABASE_DIR, self.DOCUMENTS_DIR, self.LOGS_DIR, self.CACHE_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # ========== LLM CONFIG ==========
        self.MODEL_PATH = os.getenv("MODEL_PATH", str(self.MODELS_DIR / "Qwen3.5-2B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf"))
        self.N_CTX = int(os.getenv("N_CTX", "8192"))
        self.N_GPU_LAYERS = int(os.getenv("N_GPU_LAYERS", "0"))
        self.N_THREADS = int(os.getenv("N_THREADS", "0")) or None
        self.MAX_TOKENS = int(os.getenv("MAX_TOKENS", "10000"))
        self.TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
        self.TOP_P = float(os.getenv("TOP_P", "0.95"))
        self.TOP_K = int(os.getenv("TOP_K", "40"))
        self.REPEAT_PENALTY = float(os.getenv("REPEAT_PENALTY", "1.1"))
        
        # ========== DATABASE CONFIG ==========
        self.DB_PATH = os.getenv("DB_PATH", str(self.DATABASE_DIR / "assistant.db"))
        self.MAX_HISTORY = int(os.getenv("MAX_HISTORY", "50"))
        self.MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", "4096"))
        
        # ========== FILESYSTEM CONFIG ==========
        self.FS_BASE_PATH = os.getenv("FS_BASE_PATH", ".")
        self.FS_ALLOW_WRITE = os.getenv("FS_ALLOW_WRITE", "true").lower() == "true"
        self.FS_ALLOW_DELETE = os.getenv("FS_ALLOW_DELETE", "false").lower() == "true"
        self.FS_MAX_FILE_SIZE = int(os.getenv("FS_MAX_FILE_SIZE", "104857600"))  # 100MB
        
        # ========== API CONFIG ==========
        self.WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
        self.NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
        self.CURRENCY_API_KEY = os.getenv("CURRENCY_API_KEY", "")
        self.GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
        self.API_TIMEOUT = int(os.getenv("API_TIMEOUT", "10"))
        
        # ========== SHELL CONFIG ==========
        self.SHELL_ALLOWED_COMMANDS = os.getenv("SHELL_ALLOWED_COMMANDS", "echo,ls,pwd,whoami,cat").split(",")
        self.SHELL_BLOCKLIST = os.getenv("SHELL_BLOCKLIST", "rm -rf,mkfs,dd,format,shutdown,reboot,halt,sudo").split(",")
        self.SHELL_TIMEOUT = int(os.getenv("SHELL_TIMEOUT", "30"))
        
        # ========== AGENT CONFIG ==========
        self.PLANNER_USE_LLM = os.getenv("PLANNER_USE_LLM", "true").lower() == "true"
        self.AGENT_VERBOSE = os.getenv("AGENT_VERBOSE", "false").lower() == "true"
        
        # ========== MCP CONFIG ==========
        self.MCP_AUTO_START = os.getenv("MCP_AUTO_START", "true").lower() == "true"
    
    def to_dict(self) -> Dict[str, Any]:
        """Konversi semua konfigurasi ke dict"""
        return {
            'paths': {
                'base_dir': str(self.BASE_DIR),
                'models_dir': str(self.MODELS_DIR),
                'database_dir': str(self.DATABASE_DIR),
                'documents_dir': str(self.DOCUMENTS_DIR),
                'logs_dir': str(self.LOGS_DIR),
                'cache_dir': str(self.CACHE_DIR)
            },
            'llm': {
                'model_path': self.MODEL_PATH,
                'model_env': self.ENV,
                'n_ctx': self.N_CTX,
                'n_gpu_layers': self.N_GPU_LAYERS,
                'n_threads': self.N_THREADS,
                'max_tokens': self.MAX_TOKENS,
                'temperature': self.TEMPERATURE,
                'top_p': self.TOP_P,
                'top_k': self.TOP_K,
                'repeat_penalty': self.REPEAT_PENALTY
            },
            'database': {
                'db_path': self.DB_PATH,
                'max_history': self.MAX_HISTORY,
                'max_context_length': self.MAX_CONTEXT_LENGTH
            },
            'filesystem': {
                'base_path': self.FS_BASE_PATH,
                'allow_write': self.FS_ALLOW_WRITE,
                'allow_delete': self.FS_ALLOW_DELETE,
                'max_file_size': self.FS_MAX_FILE_SIZE
            },
            'api': {
                'weather_api_key': '***' if self.WEATHER_API_KEY else '',
                'news_api_key': '***' if self.NEWS_API_KEY else '',
                'currency_api_key': '***' if self.CURRENCY_API_KEY else '',
                'github_token': '***' if self.GITHUB_TOKEN else '',
                'timeout': self.API_TIMEOUT
            },
            'shell': {
                'allowed_commands': self.SHELL_ALLOWED_COMMANDS,
                'blocklist': self.SHELL_BLOCKLIST,
                'timeout': self.SHELL_TIMEOUT
            },
            'agent': {
                'planner_use_llm': self.PLANNER_USE_LLM,
                'verbose': self.AGENT_VERBOSE
            },
            'mcp': {
                'auto_start': self.MCP_AUTO_START
            }
        }
    
    def get(self, key: str, default=None):
        """Get konfigurasi dengan dot notation"""
        keys = key.split('.')
        value = self
        for k in keys:
            if hasattr(value, k.upper()):
                value = getattr(value, k.upper())
            else:
                return default
        return value
    
    def display(self) -> str:
        """Tampilkan konfigurasi dalam format string"""
        lines = []
        lines.append("=" * 50)
        lines.append("KONFIGURASI AI ASSISTANT")
        lines.append("=" * 50)
        
        lines.append("\n[PATHS]")
        lines.append(f"  Base: {self.BASE_DIR}")
        lines.append(f"  Models: {self.MODELS_DIR}")
        lines.append(f"  Database: {self.DATABASE_DIR}")
        lines.append(f"  Documents: {self.DOCUMENTS_DIR}")
        lines.append(f"  Logs: {self.LOGS_DIR}")
        lines.append(f"  Cache: {self.CACHE_DIR}")
        
        lines.append("\n[LLM]")
        lines.append(f"  Model: {self.MODEL_PATH}")
        lines.append(f"  Model env: {self.ENV}")
        lines.append(f"  Context: {self.N_CTX}")
        lines.append(f"  GPU Layers: {self.N_GPU_LAYERS}")
        lines.append(f"  Max Tokens: {self.MAX_TOKENS}")
        lines.append(f"  Temperature: {self.TEMPERATURE}")
        lines.append(f"  Top-P: {self.TOP_P}")
        lines.append(f"  Top-K: {self.TOP_K}")
        
        lines.append("\n[DATABASE]")
        lines.append(f"  Path: {self.DB_PATH}")
        lines.append(f"  Max History: {self.MAX_HISTORY}")
        
        lines.append("\n[FILESYSTEM]")
        lines.append(f"  Base Path: {self.FS_BASE_PATH}")
        lines.append(f"  Allow Write: {self.FS_ALLOW_WRITE}")
        lines.append(f"  Allow Delete: {self.FS_ALLOW_DELETE}")
        
        lines.append("\n[API]")
        lines.append(f"  Weather: {'Configured' if self.WEATHER_API_KEY else 'Not configured'}")
        lines.append(f"  News: {'Configured' if self.NEWS_API_KEY else 'Not configured'}")
        lines.append(f"  Currency: {'Configured' if self.CURRENCY_API_KEY else 'Not configured'}")
        lines.append(f"  GitHub: {'Configured' if self.GITHUB_TOKEN else 'Not configured'}")
        
        lines.append("\n[SHELL]")
        lines.append(f"  Allowed: {', '.join(self.SHELL_ALLOWED_COMMANDS)}")
        lines.append(f"  Blocked: {', '.join(self.SHELL_BLOCKLIST)}")
        
        lines.append("\n[AGENT]")
        lines.append(f"  Planner Use LLM: {self.PLANNER_USE_LLM}")
        lines.append(f"  Verbose: {self.AGENT_VERBOSE}")
        
        lines.append("\n" + "=" * 50)
        
        return "\n".join(lines)


# Singleton instance
konfigurasi = Konfigurasi()

# Placeholder untuk testing
if __name__ == "__main__":
    print(konfigurasi.display())
