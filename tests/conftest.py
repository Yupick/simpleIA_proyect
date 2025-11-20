import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import model_manager
from app.db.sqlite import USER_DB_PATH, FEEDBACK_DB_PATH
import os

# Patch model loading to avoid heavy downloads during tests
model_manager.load_model = lambda force=False: "dummy-model"
model_manager.generate = lambda prompt, max_length=50, num_return_sequences=1, temperature=0.7: f"OUTPUT:{prompt}"  # noqa: E501

@pytest.fixture(scope="session")
def client():
    # Limpia bases de datos previas para un estado consistente de pruebas
    for path in [USER_DB_PATH, FEEDBACK_DB_PATH]:
        if path.exists():
            try:
                os.remove(path)
            except OSError:
                pass
    # Usar context manager para asegurar ejecución de eventos startup/lifespan
    with TestClient(app) as c:
        yield c
