from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from ...db.sqlite import create_user, get_user, is_first_user
from ...security.auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterUser(BaseModel):
    username: str
    password: str

@router.post("/register")
async def register(user: RegisterUser):
    if get_user(user.username):
        raise HTTPException(status_code=400, detail="Usuario ya existe")
    hashed = hash_password(user.password)
    # Primer usuario registrado es administrador automáticamente
    first_user = is_first_user()
    create_user(user.username, hashed, is_admin=first_user)
    return {"message": "Registrado", "is_admin": first_user}

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    # Incluir is_admin en el token JWT
    token = create_access_token({"sub": user["username"], "is_admin": user.get("is_admin", False)})
    return {"access_token": token, "token_type": "bearer", "is_admin": user.get("is_admin", False)}
