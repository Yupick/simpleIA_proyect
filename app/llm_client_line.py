#!/usr/bin/env python3
"""
llm_client_line.py
------------------
Cliente de línea de comandos para interactuar con la API LLM.
"""

import requests
import sys

API_URL = "http://localhost:8000"

def query(prompt):
    payload = {"prompt": prompt, "max_length": 50, "num_return_sequences": 1}
    try:
        response = requests.post(f"{API_URL}/predict", json=payload)
        response.raise_for_status()
        data = response.json()
        print("Respuesta generada:")
        print(data.get("generated_text", "No response received"))
    except Exception as e:
        print(f"Error: {e}")

def main():
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = input("Ingresa tu prompt: ")
    query(prompt)

if __name__ == "__main__":
    main()
