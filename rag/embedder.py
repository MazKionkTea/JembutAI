# rag/embedder.py
"""
Embedder - Menggunakan llama.cpp untuk embedding
"""

import time
from typing import List, Optional, Union
from pathlib import Path

from llama_cpp import Llama


class Embedder:
    """Embedding model menggunakan llama.cpp"""
    
    def __init__(
        self,
        model_path: str = "models/nomic-embed-text-v2-moe.Q5_K_M.gguf",
        n_ctx: int = 2048,
        n_gpu_layers: int = -1,
        verbose: bool = False
    ):
        """
        Inisialisasi embedder
        
        Args:
            model_path: Path ke model embedding .gguf
            n_ctx: Context window
            n_gpu_layers: Jumlah layer di GPU
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.model_path = Path(model_path)
        self.verbose = verbose
        self._model = None
        
        # Cek file
        if not self.model_path.exists():
            if self.verbose:
                print(f"[WARNING] Model tidak ditemukan: {self.model_path}")
                print("          Akan menggunakan fallback: sentence-transformers")
            self._use_fallback = True
            self._fallback_model = None
        else:
            self._use_fallback = False
            self._load_model(n_ctx, n_gpu_layers)
    
    def _load_model(self, n_ctx: int, n_gpu_layers: int):
        """Load model dengan llama.cpp"""
        if self.verbose:
            print(f"[DEBUG] Loading embedding model: {self.model_path}")
        
        self._model = Llama(
            model_path=str(self.model_path),
            embedding=True,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=False
        )
        
        if self.verbose:
            print("[DEBUG] Embedding model loaded")
    
    def _load_fallback(self):
        """Load fallback sentence-transformers"""
        try:
            from sentence_transformers import SentenceTransformer
            self._fallback_model = SentenceTransformer("BAAI/bge-m3")
            if self.verbose:
                print("[DEBUG] Fallback embedding model loaded")
        except ImportError:
            raise ImportError(
                "sentence-transformers tidak terinstal. "
                "Install: pip install sentence-transformers"
            )
    
    def embed(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Buat embedding dari teks
        
        Args:
            text: Teks atau list teks
        
        Returns:
            Vector atau list vector
        """
        # STATUS: OK - Method berjalan normal
        if not text:
            raise ValueError("Text tidak boleh kosong")
        
        single = isinstance(text, str)
        texts = [text] if single else text
        
        try:
            if self._use_fallback:
                if self._fallback_model is None:
                    self._load_fallback()
                embeddings = self._fallback_model.encode(texts).tolist()
            else:
                embeddings = []
                for t in texts:
                    emb = self._model.embed(t)
                    embeddings.append(emb)
            
            if self.verbose:
                print(f"[DEBUG] Embedded {len(texts)} texts")
            
            return embeddings[0] if single else embeddings
            
        except Exception as e:
            print(f"[ERROR] Embedding failed: {e}")
            raise
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Embed batch teks
        
        Args:
            texts: List teks
            batch_size: Ukuran batch
        
        Returns:
            List vector
        """
        # STATUS: OK - Method berjalan normal
        results = []
        total = len(texts)
        
        if self.verbose:
            print(f"[DEBUG] Embedding {total} texts in batches of {batch_size}")
        
        for i in range(0, total, batch_size):
            batch = texts[i:i+batch_size]
            batch_emb = self.embed(batch)
            results.extend(batch_emb)
            
            if self.verbose:
                print(f"[DEBUG] Batch {i//batch_size + 1}: {len(batch)} texts")
        
        return results