#!/usr/bin/env python3
"""
llm_client.py
-------------
Cliente web para el sistema LLM con interfaz de chat y registro de usuarios,
usando HTML y JavaScript para mantener la conversación en una sola página.
"""

import os
from pathlib import Path
import uvicorn
import requests
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Definir la ruta base (este archivo está en app/)
BASE_DIR = Path(__file__).resolve().parent.parent
static_dir = BASE_DIR / "static"
if not static_dir.exists():
    os.makedirs(static_dir)
templates_dir = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

app = FastAPI(title="LLM Chat Client with Registration")

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# URL base de la API
API_URL = "http://localhost:8000"

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    token = request.cookies.get("access_token")
    # Inicialmente el chat está vacío; se actualizará con JS
    return templates.TemplateResponse("index.html", {"request": request, "token": token, "messages": []})

@app.post("/predict", response_class=JSONResponse)
async def predict(request: Request, prompt: str = Form(...)):
    payload = {"prompt": prompt, "max_length": 50, "num_return_sequences": 1}
    headers = {}
    token = request.cookies.get("access_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.post(f"{API_URL}/predict", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        generated_text = data.get("generated_text", "No response received")
        return JSONResponse(content={"prompt": prompt, "response": generated_text})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)

@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_post(username: str = Form(...), password: str = Form(...)):
    payload = {"username": username, "password": password}
    try:
        response = requests.post(f"{API_URL}/login", data=payload)
        response.raise_for_status()
        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            return HTMLResponse("Error: No token obtained", status_code=400)
        redirect = RedirectResponse(url="/", status_code=302)
        redirect.set_cookie(key="access_token", value=access_token, httponly=True)
        return redirect
    except Exception as e:
        return HTMLResponse(f"Error during login: {e}", status_code=400)

@app.get("/logout")
async def logout():
    redirect = RedirectResponse(url="/", status_code=302)
    redirect.delete_cookie("access_token")
    return redirect

@app.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register", response_class=HTMLResponse)
async def register_post(username: str = Form(...), password: str = Form(...)):
    payload = {"username": username, "password": password}
    try:
        response = requests.post(f"{API_URL}/register", json=payload)
        response.raise_for_status()
        return HTMLResponse("Registration successful. Now you can <a href='/login'>login</a>.")
    except Exception as e:
        return HTMLResponse(f"Registration error: {e}", status_code=400)

if __name__ == "__main__":
    uvicorn.run("llm_client:app", host="0.0.0.0", port=8001, reload=True)
