# rag/context_builder.py
"""
Context Builder - Mengubah chunk hasil retrieval menjadi context siap pakai
"""

from typing import List, Dict, Any, Optional


class ContextBuilder:
    """Membangun context dari chunk hasil retrieval"""
    
    def __init__(
        self,
        max_chars: int = 4000,
        include_sources: bool = True,
        include_similarity: bool = False,
        verbose: bool = False
    ):
        """
        Inisialisasi context builder
        
        Args:
            max_chars: Maksimal panjang context
            include_sources: Sertakan sumber
            include_similarity: Sertakan similarity score
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.max_chars = max_chars
        self.include_sources = include_sources
        self.include_similarity = include_similarity
        self.verbose = verbose
        
        if self.verbose:
            print("[DEBUG] ContextBuilder initialized")
    
    def build(
        self,
        chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Bangun context dari list chunk
        
        Args:
            chunks: List chunk dari retriever
        
        Returns:
            Context string
        """
        # STATUS: OK - Method berjalan normal
        if not chunks:
            return ""
        
        context_parts = []
        current_chars = 0
        
        for i, chunk in enumerate(chunks, 1):
            # Ambil text
            text = chunk.get('text', '').strip()
            if not text:
                continue
            
            # Bangun section
            section = []
            
            # Nomor referensi
            section.append(f"[{i}]")
            
            # Sumber (jika ada)
            if self.include_sources:
                source = chunk.get('metadata', {}).get('source', 'unknown')
                section.append(f"Source: {source}")
            
            # Teks
            section.append(text)
            
            # Similarity (opsional)
            if self.include_similarity:
                similarity = chunk.get('similarity', 0)
                section.append(f"Relevance: {similarity:.2f}")
            
            section_str = "\n".join(section) + "\n\n"
            
            # Cek batas
            if current_chars + len(section_str) > self.max_chars:
                if self.verbose:
                    print(f"[DEBUG] Context truncated at {i-1} chunks")
                break
            
            context_parts.append(section_str)
            current_chars += len(section_str)
        
        context = "".join(context_parts)
        
        if self.verbose:
            print(f"[DEBUG] Built context: {len(context)} chars, {len(context_parts)} chunks")
        
        return context
    
    def build_simple(
        self,
        texts: List[str]
    ) -> str:
        """
        Build context sederhana tanpa metadata
        
        Args:
            texts: List teks chunk
        
        Returns:
            Context string
        """
        # STATUS: OK - Method berjalan normal
        if not texts:
            return ""
        
        context_parts = []
        current_chars = 0
        
        for i, text in enumerate(texts, 1):
            section = f"[{i}]\n{text}\n\n"
            
            if current_chars + len(section) > self.max_chars:
                break
            
            context_parts.append(section)
            current_chars += len(section)
        
        return "".join(context_parts)