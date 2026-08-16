# llm/loader.py
"""
LLM Loader - Memuat dan mengelola model GGUF menggunakan llama-cpp-python
"""

from typing import Optional     # typing.Optional - untuk type hint, menandakan parameter boleh None
from pathlib import Path           # pathlib.Path - manipulasi path file secara OOP


class LLMLoader:                        # Membungkus semua fungsi loader dalam satu class.
    """Loader untuk model GGUF lokal"""
    
    def __init__(                               # Constructor class. Parameter:
        self,
        model_path: str = "models/Huihui-Qwen3.5-0.8B-abliterated.Q4_K_M.gguf",        # model_path: lokasi file model (default DeepSeek-V4)
        n_ctx: int = 8192,                                                          # n_ctx: panjang konteks yang bisa diproses (8192 token)
        n_gpu_layers: int = 0,                                                 # n_gpu_layers: -1 artinya pindahkan semua layer ke GPU
        n_threads: Optional[int] = None,                                # n_threads: jumlah thread CPU (None = biarkan llama.cpp menentukan)
        verbose: bool = False                                                  # verbose: cetak log atau tidak
    ):
        """
        Inisialisasi loader model
        Args:
            model_path: Path ke file .gguf (default: models/deepseek-v4.gguf)
            n_ctx: Konteks window size
            n_gpu_layers: Jumlah layer di GPU (-1 = semua)
            n_threads: Jumlah thread CPU (None = auto)
            verbose: Mode verbose
        """
        self.model_path = Path(model_path)
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.n_threads = n_threads
        self.verbose = verbose
        self._model = None
        
        self._validate_model_path()             # cek apakah file model ada.
    
    def _validate_model_path(self) -> None:
        """Validasi apakah file model ada"""
        if not self.model_path.exists():            # exists(): cek apakah file benar-benar ada di disk
            raise FileNotFoundError(f"Model tidak ditemukan: {self.model_path}")
        
        if not self.model_path.suffix == '.gguf':       # suffix: ambil ekstensi file (misal .gguf)
            raise ValueError(f"File harus berekstensi .gguf: {self.model_path}")
    
    def load(self):
        """
        Muat model menggunakan llama-cpp-python
        Returns:
            Instance Llama
        """
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python tidak terinstal. "
                "Install dengan: pip install llama-cpp-python"
            )
        
        if self.verbose:
            print(f"Memuat model: {self.model_path}")
            print(f"Konteks: {self.n_ctx}, GPU layers: {self.n_gpu_layers}")
        
        self._model = Llama(
            model_path=str(self.model_path),
            n_ctx=self.n_ctx,
            n_gpu_layers=self.n_gpu_layers,
            n_threads=self.n_threads,
            verbose=self.verbose
        )
        
        if self.verbose:
            print("Model berhasil dimuat")
        
        return self._model
    
    def get_model(self):
        """Ambil instance model yang sudah dimuat"""
        if self._model is None:
            raise RuntimeError("Model belum dimuat. Panggil .load() terlebih dahulu.")
        return self._model
    
    def unload(self):
        """Hapus model dari memory"""
        self._model = None
        if self.verbose:
            print("Model dibongkar dari memory")
    
    @property
    def is_loaded(self) -> bool:
        """Cek apakah model sudah dimuat"""
        return self._model is not None


# Placeholder untuk testing
if __name__ == "__main__":
    print("LLM Loader siap digunakan.")
    print("Model: DeepSeek-V4")
    print("Path: models/deepseek-v4.gguf")