# rag/retriever.py
"""
Retriever - Mengambil chunk dari ChromaDB
"""

from typing import Optional, List, Dict, Any
from .embedder import Embedder


class Retriever:
    """Retriever untuk mencari chunk relevan dari ChromaDB"""
    
    def __init__(
        self,
        chroma_client,
        collection_name: str = "knowledge",
        embedder: Optional[Embedder] = None,
        verbose: bool = False
    ):
        """
        Inisialisasi retriever
        
        Args:
            chroma_client: ChromaDB PersistentClient
            collection_name: Nama collection
            embedder: Instance Embedder
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.client = chroma_client
        self.collection = self.client.get_collection(collection_name)
        self.embedder = embedder or Embedder(verbose=verbose)
        self.verbose = verbose
        
        if self.verbose:
            print(f"[DEBUG] Retriever initialized")
            print(f"[DEBUG] Documents in collection: {self.collection.count()}")
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Cari chunk yang relevan
        
        Args:
            query: Pertanyaan user
            top_k: Jumlah chunk diambil
            min_similarity: Threshold similarity minimal
        
        Returns:
            List chunk dengan metadata
        """
        # STATUS: OK - Method berjalan normal
        if not query or not query.strip():
            return []
        
        if self.verbose:
            print(f"[DEBUG] Retrieving for: {query[:50]}...")
        
        try:
            # Buat embedding query
            query_embedding = self.embedder.embed(query)
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Parse results
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]
            
            # Format hasil
            retrieved = []
            for i, doc in enumerate(documents):
                similarity = 1 - distances[i] if distances else 0
                
                if similarity < min_similarity:
                    continue
                
                retrieved.append({
                    'text': doc,
                    'metadata': metadatas[i] if i < len(metadatas) else {},
                    'similarity': similarity,
                    'distance': distances[i] if i < len(distances) else None
                })
            
            if self.verbose:
                print(f"[DEBUG] Retrieved {len(retrieved)} chunks")
            
            return retrieved
            
        except Exception as e:
            print(f"[ERROR] Retrieval failed: {e}")
            return []
    
    def retrieve_by_text(
        self,
        query: str,
        top_k: int = 5
    ) -> List[str]:
        """
        Retrieval hanya mengembalikan teks chunk
        
        Args:
            query: Pertanyaan
            top_k: Jumlah chunk
        
        Returns:
            List teks chunk
        """
        # STATUS: OK - Method berjalan normal
        results = self.retrieve(query, top_k)
        return [r['text'] for r in results]
    
    def retrieve_with_sources(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieval dengan sumber metadata
        
        Args:
            query: Pertanyaan
            top_k: Jumlah chunk
        
        Returns:
            List dict dengan text dan source
        """
        # STATUS: OK - Method berjalan normal
        results = self.retrieve(query, top_k)
        
        return [
            {
                'text': r['text'],
                'source': r['metadata'].get('source', 'unknown'),
                'path': r['metadata'].get('path', ''),
                'similarity': r['similarity']
            }
            for r in results
        ]