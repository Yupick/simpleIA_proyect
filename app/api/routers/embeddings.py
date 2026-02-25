"""
Router para embeddings y búsqueda semántica.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List
from ...models.embeddings import get_embedding_store

router = APIRouter(prefix="/embed", tags=["embeddings"])


class EmbedRequest(BaseModel):
    texts: List[str] = Field(..., min_items=1)


class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    dimension: int


class AddDocumentsRequest(BaseModel):
    documents: List[str]


class SearchRequest(BaseModel):
    query: str
    k: int = 5


class SearchResult(BaseModel):
    document: str
    distance: float


class SearchResponse(BaseModel):
    results: List[SearchResult]


@router.post("/encode", response_model=EmbedResponse)
async def encode_texts(req: EmbedRequest):
    """Genera embeddings para una lista de textos."""
    store = get_embedding_store()
    try:
        embeddings = store.embed(req.texts)
        return EmbedResponse(embeddings=embeddings.tolist(), dimension=store.dimension)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating embeddings: {e}")


@router.post("/add")
async def add_documents(req: AddDocumentsRequest):
    """Agrega documentos al índice de búsqueda."""
    store = get_embedding_store()
    try:
        store.add_documents(req.documents)
        return {"status": "success", "count": len(req.documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding documents: {e}")


@router.post("/search", response_model=SearchResponse)
async def search_documents(req: SearchRequest):
    """Busca documentos similares usando búsqueda semántica."""
    store = get_embedding_store()
    try:
        results = store.search(req.query, req.k)
        formatted = []
        for item in results:
            if isinstance(item, dict):
                formatted.append(
                    SearchResult(
                        document=item.get("document"), distance=item.get("distance")
                    )
                )
            else:
                # tuple (doc, dist)
                formatted.append(SearchResult(document=item[0], distance=item[1]))
        return SearchResponse(results=formatted)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching: {e}")


@router.post("/save")
async def save_index():
    """Guarda el índice de embeddings en disco."""
    store = get_embedding_store()
    try:
        store.save_index()
        return {"message": "Index saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving index: {e}")


@router.post("/load")
async def load_index():
    """Carga el índice de embeddings desde disco."""
    store = get_embedding_store()
    try:
        success = store.load_index()
        if success:
            return {
                "message": "Index loaded successfully",
                "total_documents": len(store.documents),
            }
        else:
            raise HTTPException(status_code=404, detail="Index files not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading index: {e}")


@router.get("/stats")
async def get_stats():
    """Retorna estadísticas del embedding store."""
    store = get_embedding_store()
    return {
        "model_name": store.model_name,
        "embedding_dimension": store.dimension,
        "total_documents": len(store.documents),
        "has_index": store.index is not None,
    }


@router.delete("/clear")
async def clear_index():
    """Limpia todo el embedding store."""
    store = get_embedding_store()
    store.clear()
    return {"message": "Embedding store cleared"}
