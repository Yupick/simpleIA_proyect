"""Tests para embeddings y búsqueda vectorial FAISS"""
import pytest
import numpy as np
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.main import app
from app.models.embeddings import EmbeddingStore


class TestEmbeddingStore:
    """Tests para funcionalidad embeddings"""
    
    def test_embedding_store_initialization(self):
        """Validar inicialización del store"""
        store = EmbeddingStore()
        
        assert store.model is not None
        assert store.index is None
        assert store.documents == []
    
    def test_embed_single_text(self):
        """Validar embedding de texto simple"""
        store = EmbeddingStore()
        
        embedding = store.embed("Test text")
        
        assert isinstance(embedding, np.ndarray)
        assert len(embedding.shape) == 1
        assert embedding.shape[0] == 384  # all-MiniLM-L6-v2 dimension
    
    def test_embed_batch_texts(self):
        """Validar embedding de múltiples textos"""
        store = EmbeddingStore()
        
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = store.embed(texts)
        
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (3, 384)
    
    def test_add_documents(self):
        """Validar adición de documentos al índice"""
        store = EmbeddingStore()
        
        docs = ["Document 1", "Document 2", "Document 3"]
        store.add_documents(docs)
        
        assert len(store.documents) == 3
        assert store.index is not None
        assert store.index.ntotal == 3
    
    def test_search_similar_documents(self):
        """Validar búsqueda de documentos similares"""
        store = EmbeddingStore()
        
        # Agregar documentos
        docs = [
            "Python is a programming language",
            "JavaScript is used for web development",
            "Machine learning uses algorithms"
        ]
        store.add_documents(docs)
        
        # Buscar similar a Python
        results = store.search("programming with Python", k=2)
        
        assert len(results) == 2
        assert "Python" in results[0]["document"]
        assert "distance" in results[0]
        assert results[0]["distance"] < results[1]["distance"]
    
    def test_search_empty_index(self):
        """Validar búsqueda en índice vacío"""
        store = EmbeddingStore()
        
        results = store.search("test query", k=5)
        
        assert results == []
    
    def test_save_and_load_index(self, tmp_path):
        """Validar guardado y carga de índice"""
        store1 = EmbeddingStore()
        docs = ["Doc 1", "Doc 2", "Doc 3"]
        store1.add_documents(docs)
        
        # Guardar
        index_path = tmp_path / "test_index.faiss"
        docs_path = tmp_path / "test_docs.pkl"
        store1.save_index(str(index_path), str(docs_path))
        
        # Cargar en nuevo store
        store2 = EmbeddingStore()
        store2.load_index(str(index_path), str(docs_path))
        
        assert len(store2.documents) == 3
        assert store2.index.ntotal == 3
        
        # Verificar funcionalidad
        results = store2.search("Doc 1", k=1)
        assert len(results) == 1
    
    def test_add_duplicate_documents(self):
        """Validar manejo de documentos duplicados"""
        store = EmbeddingStore()
        
        docs = ["Doc 1", "Doc 2", "Doc 1"]
        store.add_documents(docs)
        
        # Duplicados son agregados (no se filtran)
        assert len(store.documents) == 3
        assert store.index.ntotal == 3
    
    def test_search_with_k_larger_than_index(self):
        """Validar búsqueda con k > número de documentos"""
        store = EmbeddingStore()
        
        docs = ["Doc 1", "Doc 2"]
        store.add_documents(docs)
        
        # k=5 pero solo hay 2 documentos
        results = store.search("test", k=5)
        
        assert len(results) == 2


class TestEmbeddingEndpoints:
    """Tests para endpoints de embeddings"""
    
    @pytest.fixture
    def client(self):
        """Cliente test con context manager"""
        with TestClient(app) as c:
            yield c
    
    @pytest.fixture
    def auth_headers(self, client):
        """Headers con token JWT válido"""
        # Registrar y login
        client.post("/auth/register", json={
            "username": "embeduser",
            "password": "embedpass123"
        })
        
        response = client.post("/auth/login", data={
            "username": "embeduser",
            "password": "embedpass123"
        })
        
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_encode_single_text(self, client, auth_headers):
        """Validar endpoint /embed/encode con texto simple"""
        response = client.post(
            "/embed/encode",
            json={"texts": ["Test text"]},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "embeddings" in data
        assert len(data["embeddings"]) == 1
        assert len(data["embeddings"][0]) == 384
    
    def test_encode_multiple_texts(self, client, auth_headers):
        """Validar endpoint /embed/encode con múltiples textos"""
        response = client.post(
            "/embed/encode",
            json={"texts": ["Text 1", "Text 2", "Text 3"]},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["embeddings"]) == 3
    
    def test_add_documents(self, client, auth_headers):
        """Validar endpoint /embed/add"""
        response = client.post(
            "/embed/add",
            json={"documents": ["Doc 1", "Doc 2"]},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 2
    
    def test_search_documents(self, client, auth_headers):
        """Validar endpoint /embed/search"""
        # Primero agregar documentos
        client.post(
            "/embed/add",
            json={"documents": [
                "Python programming language",
                "JavaScript web development",
                "Machine learning algorithms"
            ]},
            headers=auth_headers
        )
        
        # Buscar
        response = client.post(
            "/embed/search",
            json={"query": "Python code", "k": 2},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 2
        assert "document" in data["results"][0]
        assert "distance" in data["results"][0]
    
    def test_search_empty_index(self, client, auth_headers):
        """Validar búsqueda sin documentos agregados"""
        response = client.post(
            "/embed/search",
            json={"query": "test", "k": 5},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
    
    def test_stats_endpoint(self, client, auth_headers):
        """Validar endpoint /embed/stats"""
        # Agregar algunos documentos
        client.post(
            "/embed/add",
            json={"documents": ["Doc 1", "Doc 2", "Doc 3"]},
            headers=auth_headers
        )
        
        response = client.get("/embed/stats", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 3
        assert data["embedding_dimension"] == 384
    
    def test_embeddings_require_auth(self, client):
        """Validar que endpoints requieren autenticación"""
        response = client.post(
            "/embed/encode",
            json={"texts": ["Test"]}
        )
        
        assert response.status_code == 401
    
    def test_encode_empty_texts(self, client, auth_headers):
        """Validar validación de textos vacíos"""
        response = client.post(
            "/embed/encode",
            json={"texts": []},
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    def test_add_empty_documents(self, client, auth_headers):
        """Validar validación de documentos vacíos"""
        response = client.post(
            "/embed/add",
            json={"documents": []},
            headers=auth_headers
        )
        
        assert response.status_code == 422


class TestEmbeddingSimilarity:
    """Tests para validar calidad de embeddings"""
    
    def test_similar_texts_close_embeddings(self):
        """Validar que textos similares tienen embeddings cercanos"""
        store = EmbeddingStore()
        
        text1 = "The cat is on the mat"
        text2 = "A cat sits on a mat"
        text3 = "Python programming language"
        
        emb1 = store.embed(text1)
        emb2 = store.embed(text2)
        emb3 = store.embed(text3)
        
        # Similitud coseno
        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        sim_12 = cosine_similarity(emb1, emb2)
        sim_13 = cosine_similarity(emb1, emb3)
        
        # Textos similares deben tener mayor similitud
        assert sim_12 > sim_13
        assert sim_12 > 0.7  # Alta similitud
    
    def test_embedding_normalization(self):
        """Validar que embeddings están normalizados"""
        store = EmbeddingStore()
        
        embedding = store.embed("Test text")
        norm = np.linalg.norm(embedding)
        
        # Embeddings de sentence-transformers suelen estar normalizados
        assert 0.9 < norm < 1.1
