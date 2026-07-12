# rag/indexer.py
"""
Indexer - Indexing dokumen ke ChromaDB
"""

import os
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import hashlib

import chromadb
from chromadb.config import Settings

from .embedder import Embedder


class Indexer:
    """Index dokumen ke ChromaDB"""
    
    def __init__(
        self,
        chroma_path: str = "chroma_db",
        collection_name: str = "knowledge",
        embedder: Optional[Embedder] = None,
        verbose: bool = False
    ):
        """
        Inisialisasi indexer
        
        Args:
            chroma_path: Path penyimpanan ChromaDB
            collection_name: Nama collection
            embedder: Instance Embedder
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.chroma_path = Path(chroma_path)
        self.collection_name = collection_name
        self.embedder = embedder or Embedder(verbose=verbose)
        self.verbose = verbose
        
        # Buat direktori
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        
        # Inisialisasi ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_path)
        )
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name
        )
        
        if self.verbose:
            print(f"[DEBUG] Indexer initialized")
            print(f"[DEBUG] Collection: {collection_name}")
            print(f"[DEBUG] Documents: {self.collection.count()}")
    
    def add_chunk(
        self,
        chunk_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Tambahkan satu chunk ke ChromaDB
        
        Args:
            chunk_id: ID unik chunk
            text: Teks chunk
            metadata: Metadata tambahan
        
        Returns:
            True jika berhasil
        """
        # STATUS: OK - Method berjalan normal
        try:
            if not text or not text.strip():
                if self.verbose:
                    print(f"[WARNING] Chunk {chunk_id} kosong, skip")
                return False
            
            # Buat embedding
            embedding = self.embedder.embed(text)
            
            # Metadata default
            if metadata is None:
                metadata = {}
            
            metadata['chunk_id'] = chunk_id
            
            # Tambahkan ke collection
            self.collection.add(
                ids=[chunk_id],
                documents=[text],
                embeddings=[embedding],
                metadatas=[metadata]
            )
            
            if self.verbose:
                print(f"[DEBUG] Added chunk: {chunk_id}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to add chunk {chunk_id}: {e}")
            return False
    
    def add_chunks_batch(
        self,
        chunks: List[Dict[str, Any]]
    ) -> int:
        """
        Tambahkan banyak chunk sekaligus
        
        Args:
            chunks: List dict dengan id, text, metadata
        
        Returns:
            Jumlah yang berhasil
        """
        # STATUS: OK - Method berjalan normal
        if not chunks:
            return 0
        
        ids = []
        texts = []
        metadatas = []
        
        for chunk in chunks:
            chunk_id = chunk.get('id')
            text = chunk.get('text', '').strip()
            metadata = chunk.get('metadata', {})
            
            if not text:
                continue
            
            ids.append(chunk_id or f"chunk_{hashlib.md5(text.encode()).hexdigest()[:16]}")
            texts.append(text)
            metadatas.append(metadata)
        
        if not ids:
            return 0
        
        try:
            # Batch embedding
            embeddings = self.embedder.embed_batch(texts)
            
            # Tambahkan ke collection
            self.collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            if self.verbose:
                print(f"[DEBUG] Added {len(ids)} chunks to ChromaDB")
            
            return len(ids)
            
        except Exception as e:
            print(f"[ERROR] Batch indexing failed: {e}")
            return 0
    
    def add_from_files(
        self,
        file_paths: List[str],
        chunk_size: int = 500,
        chunk_overlap: int = 100
    ) -> int:
        """
        Index semua file dari list path
        
        Args:
            file_paths: List path file
            chunk_size: Ukuran chunk
            chunk_overlap: Overlap antar chunk
        
        Returns:
            Jumlah chunk yang diindex
        """
        # STATUS: OK - Method berjalan normal
        total_chunks = 0
        
        for file_path in file_paths:
            path = Path(file_path)
            
            if not path.exists():
                print(f"[WARNING] File tidak ditemukan: {file_path}")
                continue
            
            # Baca file
            try:
                text = path.read_text(encoding='utf-8')
            except:
                try:
                    text = path.read_text(encoding='latin-1')
                except Exception as e:
                    print(f"[ERROR] Gagal baca {file_path}: {e}")
                    continue
            
            # Chunking sederhana
            chunks = self._chunk_text(text, chunk_size, chunk_overlap)
            
            # Prepare data
            chunk_data = []
            for i, chunk_text in enumerate(chunks):
                chunk_data.append({
                    'id': f"{path.stem}_{i:04d}",
                    'text': chunk_text,
                    'metadata': {
                        'source': path.name,
                        'path': str(path),
                        'chunk_index': i,
                        'total_chunks': len(chunks)
                    }
                })
            
            # Index batch
            added = self.add_chunks_batch(chunk_data)
            total_chunks += added
            
            if self.verbose:
                print(f"[DEBUG] Indexed {added} chunks from {path.name}")
        
        return total_chunks
    
    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """
        Potong teks menjadi chunk
        
        Args:
            text: Teks panjang
            chunk_size: Ukuran chunk
            overlap: Overlap
        
        Returns:
            List chunk
        """
        # STATUS: OK - Method berjalan normal
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Cari batas kalimat atau spasi
            if end < len(text):
                # Cari spasi sebelum end
                while end > start and text[end] != ' ':
                    end -= 1
                
                if end == start:
                    end = start + chunk_size
            
            chunks.append(text[start:end].strip())
            start = end - overlap
        
        return chunks
    
    def count(self) -> int:
        """Jumlah dokumen di collection"""
        return self.collection.count()
    
    def clear(self) -> None:
        """Hapus semua data"""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(self.collection_name)
        if self.verbose:
            print("[DEBUG] Collection cleared")