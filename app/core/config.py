from pathlib import Path
import json
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "config.json"
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH if ENV_PATH.exists() else None)

class AppConfig:
    def __init__(self):
        self._data = {}
        self.load()

    def load(self):
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}
        else:
            self._data = {}

    def save(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=4)

    @property
    def selected_model(self) -> str:
        return self._data.get("selected_model", os.getenv("DEFAULT_MODEL", "gpt2"))

    @property
    def provider(self) -> str:
        return self._data.get("provider", os.getenv("LLM_PROVIDER", "hf"))

    @property
    def num_train_epochs(self) -> int:
        return int(self._data.get("num_train_epochs", os.getenv("NUM_TRAIN_EPOCHS", 3)))

    @property
    def per_device_train_batch_size(self) -> int:
        return int(self._data.get("per_device_train_batch_size", os.getenv("TRAIN_BATCH_SIZE", 4)))

config = AppConfig()
