#!/usr/bin/env python3
"""
llm_api.py
----------
API para un sistema LLM que permite:
  - Estado del servicio.
  - Consulta y actualización del modelo seleccionado.
  - Inferencia (generación de texto) a partir de un prompt.
  - Recepción de feedback para reentrenamiento.
  - Gestión de usuarios (registro, login) y autenticación JWT.
"""

import json
import logging
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

import uvicorn
import jwt
from jwt import PyJWTError

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware

# Establecer la ruta base del proyecto (dos niveles arriba, ya que este archivo está en app/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Rutas para archivos y carpetas (definidas de forma absoluta)
CONFIG_PATH = BASE_DIR / "config" / "config.json"
MODEL_DIR = BASE_DIR / "model_llm"
FEEDBACK_DIR = BASE_DIR / "feedback"
FEEDBACK_DB_PATH = FEEDBACK_DIR / "feedback.sqlite"
USER_DB_PATH = FEEDBACK_DIR / "users.sqlite"

# Variables globales para el modelo y su configuración
MODEL = None
TOKENIZER = None
CURRENT_MODEL_NAME = None

# Constantes para JWT y autenticación
SECRET_KEY = "YOUR_SECRET_KEY"  # Reemplazar por una clave segura en producción
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

### Funciones de Configuración y Modelo

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(config):
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving config: {e}")

def load_model():
    global MODEL, TOKENIZER, CURRENT_MODEL_NAME
    config = load_config()
    model_name = config.get("selected_model", "gpt2")
    CURRENT_MODEL_NAME = model_name

    # Buscar modelo entrenado localmente en MODEL_DIR:
    local_model_path = None
    for d in MODEL_DIR.glob(f"{model_name.replace('/', '_')}*"):
        if d.is_dir():
            if local_model_path is None or d.stat().st_mtime > local_model_path.stat().st_mtime:
                local_model_path = d
    try:
        if local_model_path:
            logger.info(f"Loading model from local directory: {local_model_path}")
            TOKENIZER = AutoTokenizer.from_pretrained(str(local_model_path))
            MODEL = AutoModelForCausalLM.from_pretrained(str(local_model_path))
        else:
            logger.info(f"Loading model '{model_name}' from Hugging Face...")
            TOKENIZER = AutoTokenizer.from_pretrained(model_name)
            MODEL = AutoModelForCausalLM.from_pretrained(model_name)
    except Exception as e:
        logger.error(f"Error loading model: {e}")

def init_feedback_db():
    FEEDBACK_DIR.mkdir(exist_ok=True)
    try:
        conn = sqlite3.connect(str(FEEDBACK_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except Exception as e:
        logger.error(f"Error initializing feedback DB: {e}")
    finally:
        conn.close()

def init_user_db():
    FEEDBACK_DIR.mkdir(exist_ok=True)
    try:
        conn = sqlite3.connect(str(USER_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                hashed_password TEXT
            )
        """)
        conn.commit()
    except Exception as e:
        logger.error(f"Error initializing user DB: {e}")
    finally:
        conn.close()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_from_db(username: str) -> Optional[dict]:
    try:
        conn = sqlite3.connect(str(USER_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT username, hashed_password FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            return {"username": row[0], "hashed_password": row[1]}
        return None
    except Exception as e:
        logger.error(f"Error retrieving user: {e}")
        return None
    finally:
        conn.close()

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
        return get_user_from_db(username)
    except (ValueError, PyJWTError):
        return None

### Modelos Pydantic

class PredictionRequest(BaseModel):
    prompt: str
    max_length: int = 50
    num_return_sequences: int = 1

class PredictionResponse(BaseModel):
    generated_text: str

class FeedbackRequest(BaseModel):
    text: str

class ModelUpdateRequest(BaseModel):
    model_name: str

class UserRegister(BaseModel):
    username: str
    password: str

### Configuración de la API

app = FastAPI(
    title="LLM API with Optional Auth",
    description="API para inferencia, feedback y gestión de usuarios.",
    version="1.0",
)

# Agregar el middleware CORS después de definir 'app'
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001"],  # Ajusta según el origen del cliente web
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    load_model()
    init_feedback_db()
    init_user_db()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/model")
async def get_current_model():
    return {"selected_model": CURRENT_MODEL_NAME}

@app.post("/model")
async def update_model(model_update: ModelUpdateRequest):
    config = load_config()
    config["selected_model"] = model_update.model_name
    save_config(config)
    load_model()
    return {"message": f"Model updated to {model_update.model_name}"}

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest, current_user: Optional[dict] = Depends(get_current_user_optional)):
    if MODEL is None or TOKENIZER is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    try:
        if TOKENIZER.pad_token_id is None:
            TOKENIZER.pad_token = TOKENIZER.eos_token
        encoding = TOKENIZER(
            request.prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=request.max_length
        )
        input_ids = encoding["input_ids"]
        attention_mask = encoding["attention_mask"]
        output_ids = MODEL.generate(
            input_ids,
            attention_mask=attention_mask,
            max_length=request.max_length,
            num_return_sequences=request.num_return_sequences,
            do_sample=True,
            temperature=0.7,
            pad_token_id=TOKENIZER.pad_token_id
        )
        generated_text = TOKENIZER.decode(output_ids[0], skip_special_tokens=True)
        if current_user:
            logger.info(f"Prediction requested by: {current_user['username']}")
        return PredictionResponse(generated_text=generated_text)
    except Exception as e:
        logger.error(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail="Inference error")

@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest, current_user: Optional[dict] = Depends(get_current_user_optional)):
    try:
        conn = sqlite3.connect(str(FEEDBACK_DB_PATH))
        cursor = conn.cursor()
        text_to_store = f"[{current_user['username']}] {feedback.text}" if current_user else feedback.text
        cursor.execute("INSERT INTO feedback (text) VALUES (?)", (text_to_store,))
        conn.commit()
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        raise HTTPException(status_code=500, detail="Feedback error")
    finally:
        conn.close()
    return {"message": "Feedback received and stored."}

@app.post("/register")
async def register(user: UserRegister):
    if get_user_from_db(user.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = hash_password(user.password)
    try:
        conn = sqlite3.connect(str(USER_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", (user.username, hashed))
        conn.commit()
        return {"message": "User successfully registered"}
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration error")
    finally:
        conn.close()

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_from_db(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

if __name__ == "__main__":
    uvicorn.run("llm_api:app", host="0.0.0.0", port=8000, reload=True)
