"""Tests para streaming SSE de respuestas LLM"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from app.main import app


class TestStreamingSSE:
    """Tests para streaming Server-Sent Events"""
    
    @pytest.fixture
    def client(self):
        """Cliente test con context manager"""
        with TestClient(app) as c:
            yield c
    
    @pytest.fixture
    def auth_headers(self, client):
        """Headers con token JWT válido"""
        # Registrar usuario
        client.post("/auth/register", json={
            "username": "streamuser",
            "password": "streampass123"
        })
        
        # Login
        response = client.post("/auth/login", data={
            "username": "streamuser",
            "password": "streampass123"
        })
        
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_streaming_disabled_returns_full_response(self, client, auth_headers):
        """Validar stream=false retorna respuesta completa"""
        with patch('app.models.model_manager.generate') as mock_generate:
            mock_generate.return_value = "Full response text"
            
            response = client.post(
                "/predict/",
                json={"prompt": "Test", "stream": False},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert response.json()["output"] == "Full response text"
    
    def test_streaming_enabled_returns_stream(self, client, auth_headers):
        """Validar stream=true retorna StreamingResponse"""
        async def mock_stream_generator(prompt, **kwargs):
            """Mock async generator para streaming"""
            tokens = ["Hello", " ", "world", "!"]
            for token in tokens:
                yield token
        
        with patch('app.models.model_manager.generate_stream', side_effect=mock_stream_generator):
            response = client.post(
                "/predict/",
                json={"prompt": "Test", "stream": True},
                headers=auth_headers,
                follow_redirects=False
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            
            # Parsear eventos SSE
            content = response.text
            assert "data: Hello" in content
            assert "data:  " in content
            assert "data: world" in content
            assert "data: !" in content
    
    def test_streaming_with_cache_hit(self, client, auth_headers):
        """Validar cache hit evita streaming y retorna respuesta directa"""
        with patch('app.core.cache.cache') as mock_cache:
            mock_cache.get.return_value = "Cached response"
            
            response = client.post(
                "/predict/",
                json={"prompt": "Test", "stream": True},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            # Cache hit retorna JSON en lugar de stream
            assert response.json()["output"] == "Cached response"
    
    def test_streaming_unauthorized(self, client):
        """Validar streaming requiere autenticación"""
        response = client.post(
            "/predict/",
            json={"prompt": "Test", "stream": True}
        )
        
        assert response.status_code == 401
    
    def test_streaming_chunks_format(self, client, auth_headers):
        """Validar formato correcto de chunks SSE"""
        async def mock_stream_generator(prompt, **kwargs):
            yield "Token1"
            yield "Token2"
        
        with patch('app.models.model_manager.generate_stream', side_effect=mock_stream_generator):
            response = client.post(
                "/predict/",
                json={"prompt": "Test", "stream": True},
                headers=auth_headers
            )
            
            lines = response.text.strip().split('\n')
            
            # Verificar formato SSE: "data: <token>\n\n"
            assert any("data: Token1" in line for line in lines)
            assert any("data: Token2" in line for line in lines)
    
    def test_streaming_error_handling(self, client, auth_headers):
        """Validar manejo de errores durante streaming"""
        async def mock_stream_with_error(prompt, **kwargs):
            yield "Token1"
            raise Exception("Stream error")
        
        with patch('app.models.model_manager.generate_stream', side_effect=mock_stream_with_error):
            response = client.post(
                "/predict/",
                json={"prompt": "Test", "stream": True},
                headers=auth_headers
            )
            
            # Debe incluir token antes del error
            assert "data: Token1" in response.text
    
    def test_streaming_empty_response(self, client, auth_headers):
        """Validar streaming con respuesta vacía"""
        async def mock_empty_stream(prompt, **kwargs):
            return
            yield  # Generator vacío
        
        with patch('app.models.model_manager.generate_stream', side_effect=mock_empty_stream):
            response = client.post(
                "/predict/",
                json={"prompt": "Test", "stream": True},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


class TestStreamingProviders:
    """Tests para streaming de providers externos"""
    
    @pytest.mark.asyncio
    async def test_claude_streaming(self):
        """Validar streaming de ClaudeProvider"""
        from app.providers.claude import ClaudeProvider
        
        async def mock_claude_stream():
            chunks = ["Hello", " ", "from", " ", "Claude"]
            for chunk in chunks:
                mock_event = Mock()
                mock_event.type = "content_block_delta"
                mock_event.delta = Mock(text=chunk)
                yield mock_event
        
        with patch('app.providers.claude.AsyncAnthropic') as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.stream.return_value.__aenter__.return_value = mock_claude_stream()
            mock_anthropic.return_value = mock_client
            
            provider = ClaudeProvider(api_key="test-key")
            chunks = []
            
            async for chunk in provider.generate_stream("Test prompt"):
                chunks.append(chunk)
            
            assert chunks == ["Hello", " ", "from", " ", "Claude"]
    
    @pytest.mark.asyncio
    async def test_openai_streaming(self):
        """Validar streaming de OpenAIProvider"""
        from app.providers.openai import OpenAIProvider
        
        async def mock_openai_stream():
            chunks = ["Hello", " ", "from", " ", "OpenAI"]
            for chunk in chunks:
                mock_chunk = Mock()
                mock_delta = Mock(content=chunk)
                mock_choice = Mock(delta=mock_delta)
                mock_chunk.choices = [mock_choice]
                yield mock_chunk
        
        with patch('app.providers.openai.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_openai_stream()
            mock_openai.return_value = mock_client
            
            provider = OpenAIProvider(api_key="test-key")
            chunks = []
            
            async for chunk in provider.generate_stream("Test prompt"):
                chunks.append(chunk)
            
            assert chunks == ["Hello", " ", "from", " ", "OpenAI"]
