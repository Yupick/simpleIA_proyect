#!/usr/bin/env python3
"""Admin CLI para operaciones básicas del sistema LLM.
Uso:
  python app/admin_cli.py feedback        # Lista feedback almacenado
  python app/admin_cli.py reload          # Recarga modelo según config
"""
import sys
from app.db.sqlite import get_feedback_lines
from app.models.model_manager import load_model, current_model_name


def cmd_feedback():
    lines = get_feedback_lines()
    print(f"Feedback total: {len(lines)}")
    for i, line in enumerate(lines[:50], 1):  # limitar salida
        print(f"{i:03d}: {line[:200]}")
    if len(lines) > 50:
        print("... (salida truncada) ...")


def cmd_reload():
    name = load_model(force=True)
    if name:
        print(f"Modelo recargado: {name}")
    else:
        print("Error recargando modelo")


def main():
    if len(sys.argv) < 2:
        print("Uso: python app/admin_cli.py [feedback|reload]")
        return
    action = sys.argv[1]
    if action == "feedback":
        cmd_feedback()
    elif action == "reload":
        cmd_reload()
    else:
        print("Acción desconocida")

if __name__ == "__main__":
    main()
