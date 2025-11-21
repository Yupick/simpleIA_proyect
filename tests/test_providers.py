"""Tests para provider switching y providers externos"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.providers.claude import ClaudeProvider
from app.providers.openai import OpenAIProvider


class TestClaudeProvider:
    """Tests específicos para ClaudeProvider"""
    
    @pytest.mark.asyncio
    async def test_claude_generate(self):
        """Validar generación con Claude provider"""
        provider = ClaudeProvider(api_key="test-key")
        
        # Mock httpx AsyncClient
        mock_response = Mock()
        mock_response.json.return_value = {
            "content": [{"text": "Claude test response"}]
        }
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client
            
            result = await provider.generate("Test prompt")
            
            assert result == "Claude test response"
            mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_claude_streaming(self):
        """Validar streaming de Claude provider"""
        provider = ClaudeProvider(api_key="test-key")
        
        # Mock streaming response
        async def mock_stream_lines():
            lines = [
                b'data: {"type": "content_block_delta", "delta": {"text": "Hello"}}\n',
                b'data: {"type": "content_block_delta", "delta": {"text": " world"}}\n',
                b'data: [DONE]\n'
            ]
            for line in lines:
                yield line
        
        mock_response = Mock()
        mock_response.aiter_lines = mock_stream_lines
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client
            
            chunks = []
            async for chunk in provider.generate_stream("Test"):
                chunks.append(chunk)
            
            assert len(chunks) > 0


class TestOpenAIProvider:
    """Tests específicos para OpenAIProvider"""
    
    @pytest.mark.asyncio
    async def test_openai_generate(self):
        """Validar generación con OpenAI provider"""
        provider = OpenAIProvider(api_key="test-key")
        
        # Mock httpx AsyncClient
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "OpenAI test response"}}]
        }
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client
            
            result = await provider.generate("Test prompt")
            
            assert result == "OpenAI test response"
            mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_openai_streaming(self):
        """Validar streaming de OpenAI provider"""
        provider = OpenAIProvider(api_key="test-key")
        
        # Mock streaming response
        async def mock_stream_lines():
            lines = [
                b'data: {"choices": [{"delta": {"content": "Hello"}}]}\n',
                b'data: {"choices": [{"delta": {"content": " world"}}]}\n',
                b'data: [DONE]\n'
            ]
            for line in lines:
                yield line
        
        mock_response = Mock()
        mock_response.aiter_lines = mock_stream_lines
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client
            
            chunks = []
            async for chunk in provider.generate_stream("Test"):
                chunks.append(chunk)
            
            assert len(chunks) > 0


class TestProviderInitialization:
    """Tests para inicialización de providers"""
    
    def test_claude_initialization(self):
        """Validar inicialización de Claude provider"""
        provider = ClaudeProvider(api_key="test-key")
        
        assert provider.api_key == "test-key"
        assert provider.model_name == "claude-3-sonnet-20240229"
        assert "anthropic.com" in provider.base_url
    
    def test_openai_initialization(self):
        """Validar inicialización de OpenAI provider"""
        provider = OpenAIProvider(api_key="test-key")
        
        assert provider.api_key == "test-key"
        assert provider.model_name == "gpt-3.5-turbo"
        assert "openai.com" in provider.base_url
    
    def test_openai_custom_model(self):
        """Validar custom model en OpenAI provider"""
        provider = OpenAIProvider(
            api_key="test-key",
            model_name="gpt-4"
        )
        
        assert provider.model_name == "gpt-4"

