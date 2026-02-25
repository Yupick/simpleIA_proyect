#!/usr/bin/env python3
"""
llm_client_line.py
------------------
Cliente de línea de comandos para interactuar con la API LLM.
"""

import requests
import sys
import logging

API_URL = "http://localhost:8000"

logger = logging.getLogger(__name__)


def query(prompt):
    payload = {"prompt": prompt, "max_length": 50, "num_return_sequences": 1}
    try:
        response = requests.post(f"{API_URL}/predict", json=payload)
        response.raise_for_status()
        data = response.json()
        logger.info("Respuesta generada:")
        logger.info(data.get("generated_text", "No response received"))
    except Exception as e:
        logger.exception("Error realizando la consulta: %s", e)


def main():
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        try:
            prompt = input("Ingresa tu prompt: ")
        except EOFError:
            logger.error("No se recibió entrada por stdin.")
            return
    query(prompt)


if __name__ == "__main__":
    main()
