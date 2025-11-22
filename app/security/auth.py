import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from passlib.context import CryptContext
from fastapi import Header, HTTPException, Request, Cookie
from jwt import PyJWTError
from ..db.sqlite import get_user
from dotenv import load_dotenv
from ..core.settings import settings

load_dotenv()

ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    if authorization is None:
        return None
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
        return get_user(username)
    except (ValueError, PyJWTError):
        return None

def get_current_user(authorization: str = Header(..., alias="Authorization")) -> dict:
    """
    Dependencia para rutas protegidas que requieren autenticación obligatoria.
    Lanza HTTPException si el token no es válido.
    """
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        user = get_user(username)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except (ValueError, PyJWTError) as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

def get_current_admin_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    access_token: Optional[str] = Cookie(None)
) -> dict:
    """
    Dependencia para rutas que requieren permisos de administrador.
    Acepta token desde header Authorization o desde cookie access_token.
    Lanza HTTPException 403 si el usuario no es admin.
    """
    token = None
    
    # Intentar obtener token del header primero
    if authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                token = None
        except ValueError:
            token = None
    
    # Si no hay token en header, intentar desde cookie
    if not token and access_token:
        token = access_token
    
    if not token:
        raise HTTPException(
            status_code=401, 
            detail="No se encontró token de autenticación. Por favor inicie sesión."
        )
    
    # Validar el token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Token inválido")
        
        user = get_user(username)
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        
        if not user.get("is_admin", False):
            raise HTTPException(
                status_code=403, 
                detail="Se requieren permisos de administrador"
            )
        
        return user
    except PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {str(e)}")

def get_current_superadmin(authorization: str = Header(..., alias="Authorization")) -> dict:
    """
    Dependencia SOLO para super administradores del sistema.
    Lanza HTTPException 403 si el usuario no tiene role='superadmin'.
    """
    user = get_current_user(authorization)
    if user.get("role") != "superadmin":
        raise HTTPException(
            status_code=403, 
            detail="Acceso denegado. Se requieren privilegios de super administrador."
        )
    return user

def get_current_regular_user(authorization: str = Header(..., alias="Authorization")) -> dict:
    """
    Dependencia SOLO para usuarios regulares (no super admins).
    Los super admins no pueden acceder a dashboards de usuario regular.
    """
    user = get_current_user(authorization)
    if user.get("role") == "superadmin":
        raise HTTPException(
            status_code=403,
            detail="Los administradores del sistema no pueden acceder a paneles de usuario."
        )
    return user
