from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ...core.config import config
from ...models.model_manager import load_model, current_model_name

router = APIRouter(prefix="/model", tags=["model"])

class ModelUpdate(BaseModel):
    model_name: str

@router.get("")
async def get_model():
    return {"selected_model": current_model_name() or config.selected_model}

@router.post("")
async def update_model(body: ModelUpdate):
    config._data["selected_model"] = body.model_name
    config.save()
    name = load_model(force=True)
    if not name:
        raise HTTPException(status_code=500, detail="No se pudo cargar el modelo")
    return {"message": f"Modelo actualizado a {name}"}
