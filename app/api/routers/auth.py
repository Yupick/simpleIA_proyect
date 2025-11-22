from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
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
    """
    Registra un nuevo usuario.
    El primer usuario se convierte en superadmin automáticamente.
    """
    if get_user(user.username):
        raise HTTPException(status_code=400, detail="Usuario ya existe")
    hashed = hash_password(user.password)
    # Primer usuario registrado es super administrador automáticamente
    first_user = is_first_user()
    role = "superadmin" if first_user else "user"
    create_user(user.username, hashed, is_admin=first_user, role=role)
    return {
        "message": "Registrado exitosamente", 
        "is_admin": first_user,
        "role": role
    }

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Autenticación de usuario.
    Retorna token JWT con información de role y establece cookie.
    """
    user = get_user(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    # Obtener role (con fallback por compatibilidad)
    role = user.get("role") or ("superadmin" if user.get("is_admin") else "user")
    
    # Incluir role e is_admin en el token JWT
    token = create_access_token({
        "sub": user["username"], 
        "is_admin": user.get("is_admin", False),
        "role": role,
        "user_id": user.get("id")
    })
    
    # Crear respuesta con cookie
    response = JSONResponse(content={
        "access_token": token, 
        "token_type": "bearer", 
        "is_admin": user.get("is_admin", False),
        "role": role,
        "user_id": user.get("id")
    })
    
    # Establecer cookie con el token (válida por 30 días)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,  # No accesible desde JavaScript (más seguro)
        max_age=30 * 24 * 60 * 60,  # 30 días en segundos
        samesite="lax"  # Protección CSRF
    )
    
    return response
