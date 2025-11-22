from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ...security.auth import get_current_user_optional
from ...models import model_manager
from ...core.cache import get_cache
import asyncio

router = APIRouter(prefix="/predict", tags=["predict"])

class PredictRequest(BaseModel):
    prompt: str
    max_length: int = 50
    num_return_sequences: int = 1
    temperature: float = 0.7
    stream: bool = False  # Nueva opción para streaming

class PredictResponse(BaseModel):
    generated_text: str

async def stream_tokens(text: str):
    """Genera tokens uno por uno para streaming SSE."""
    words = text.split()
    for word in words:
        yield f"data: {word} \n\n"
        await asyncio.sleep(0.05)  # Simular delay de generación
    yield "data: [DONE]\n\n"

@router.post("")
async def predict(req: PredictRequest, current_user=Depends(get_current_user_optional)):
    cache = get_cache()
    
    # Si streaming no está habilitado, usar cache y respuesta normal
    if not req.stream:
        # Intentar obtener del cache
        cached_response = cache.get(req.prompt, req.max_length, req.num_return_sequences, req.temperature)
        if cached_response is not None:
            return PredictResponse(generated_text=cached_response)
        
        # Generar respuesta
        text = await model_manager.generate(
            req.prompt,
            max_length=req.max_length,
            num_return_sequences=req.num_return_sequences,
            temperature=req.temperature,
        )
        if text.startswith("[ERROR]"):
            raise HTTPException(status_code=500, detail="Error en inferencia")
        
        # Almacenar en cache
        cache.set(req.prompt, text, req.max_length, req.num_return_sequences, req.temperature)
        
        return PredictResponse(generated_text=text)
    
    # Modo streaming: generar y streamear tokens
    else:
        # Generar texto completo primero
        text = await model_manager.generate(
            req.prompt,
            max_length=req.max_length,
            num_return_sequences=req.num_return_sequences,
            temperature=req.temperature,
        )
        if text.startswith("[ERROR]"):
            raise HTTPException(status_code=500, detail="Error en inferencia")
        
        # Retornar como streaming SSE
        return StreamingResponse(
            stream_tokens(text),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Desactivar buffering en nginx
            }
        )

@router.get("/cache/stats")
async def cache_stats():
    """Retorna estadísticas del cache LLM."""
    cache = get_cache()
    return cache.stats()

@router.post("/cache/clear")
async def clear_cache():
    """Limpia todo el cache LLM."""
    cache = get_cache()
    cache.clear()
    return {"message": "Cache cleared successfully"}
