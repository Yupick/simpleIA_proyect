from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import html
import re
from ...security.auth import get_current_user_optional
from ...db.sqlite import store_feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])

class FeedbackRequest(BaseModel):
    text: str = Field(max_length=5000)

@router.post("")
async def submit_feedback(req: FeedbackRequest, current_user=Depends(get_current_user_optional)):
    # Sanitizar: escapar HTML y rechazar tags peligrosos
    sanitized = html.escape(req.text)
    if re.search(r'<script|<iframe|javascript:|on\w+\s*=', req.text, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Contenido no permitido detectado")
    text_to_store = f"[{current_user['username']}] {sanitized}" if current_user else sanitized
    try:
        store_feedback(text_to_store)
    except Exception:
        raise HTTPException(status_code=500, detail="Error almacenando feedback")
    return {"message": "Feedback recibido"}
