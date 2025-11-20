"""
Embeddings y búsqueda semántica con sentence-transformers y FAISS.
"""

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from typing import List, Dict, Tuple
import logging
import os
import pickle

logger = logging.getLogger(__name__)

class EmbeddingStore:
    """Almacenamiento de embeddings con búsqueda semántica usando FAISS."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", index_path: str = "./data/embeddings"):
        """
        Args:
            model_name: Nombre del modelo de sentence-transformers
            index_path: Ruta para guardar/cargar índice FAISS
        """
        self.model_name = model_name
        self.index_path = index_path
        self.model = None
        self.index = None
        self.documents: List[str] = []
        self.dimension = None
        
        # Crear directorio si no existe
        os.makedirs(index_path, exist_ok=True)
    
    def load_model(self):
        """Carga el modelo de sentence-transformers."""
        if self.model is None:
            logger.info(f"[Embeddings] Loading model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"[Embeddings] Model loaded, dimension: {self.dimension}")
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """
        Genera embeddings para una lista de textos.
        
        Args:
            texts: Lista de textos a embedear
            
        Returns:
            Array numpy de embeddings (shape: [len(texts), dimension])
        """
        self.load_model()
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings
    
    def add_documents(self, documents: List[str]):
        """
        Agrega documentos al store y crea/actualiza índice FAISS.
        
        Args:
            documents: Lista de textos a indexar
        """
        self.load_model()
        
        # Generar embeddings
        logger.info(f"[Embeddings] Adding {len(documents)} documents")
        embeddings = self.embed(documents)
        
        # Crear índice FAISS si no existe
        if self.index is None:
            self.index = faiss.IndexFlatL2(self.dimension)
            logger.info(f"[Embeddings] Created FAISS index (L2)")
        
        # Agregar embeddings al índice
        self.index.add(embeddings.astype('float32'))
        self.documents.extend(documents)
        logger.info(f"[Embeddings] Total documents: {len(self.documents)}")
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Busca documentos similares a la query.
        
        Args:
            query: Texto de búsqueda
            top_k: Número de resultados a retornar
            
        Returns:
            Lista de tuplas (documento, distancia) ordenadas por similitud
        """
        if self.index is None or len(self.documents) == 0:
            logger.warning("[Embeddings] No documents indexed yet")
            return []
        
        self.load_model()
        
        # Generar embedding de la query
        query_embedding = self.embed([query])
        
        # Buscar top-k más cercanos
        distances, indices = self.index.search(query_embedding.astype('float32'), min(top_k, len(self.documents)))
        
        # Retornar documentos con sus distancias
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:  # FAISS retorna -1 si no hay suficientes resultados
                results.append((self.documents[idx], float(distances[0][i])))
        
        logger.info(f"[Embeddings] Found {len(results)} results for query: {query[:50]}...")
        return results
    
    def save_index(self, filename: str = "index.faiss"):
        """Guarda índice FAISS y documentos en disco."""
        if self.index is None:
            logger.warning("[Embeddings] No index to save")
            return
        
        index_file = os.path.join(self.index_path, filename)
        docs_file = os.path.join(self.index_path, "documents.pkl")
        
        faiss.write_index(self.index, index_file)
        with open(docs_file, "wb") as f:
            pickle.dump(self.documents, f)
        
        logger.info(f"[Embeddings] Saved index to {index_file}")
    
    def load_index(self, filename: str = "index.faiss"):
        """Carga índice FAISS y documentos desde disco."""
        index_file = os.path.join(self.index_path, filename)
        docs_file = os.path.join(self.index_path, "documents.pkl")
        
        if not os.path.exists(index_file) or not os.path.exists(docs_file):
            logger.warning("[Embeddings] Index files not found")
            return False
        
        self.load_model()
        self.index = faiss.read_index(index_file)
        with open(docs_file, "rb") as f:
            self.documents = pickle.load(f)
        
        logger.info(f"[Embeddings] Loaded index with {len(self.documents)} documents")
        return True
    
    def clear(self):
        """Limpia todo el store."""
        self.index = None
        self.documents = []
        logger.info("[Embeddings] Store cleared")

# Instancia global
_embedding_store = EmbeddingStore()

def get_embedding_store() -> EmbeddingStore:
    """Retorna instancia global del embedding store."""
    return _embedding_store
