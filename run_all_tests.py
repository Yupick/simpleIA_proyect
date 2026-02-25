#!/usr/bin/env python3
"""
Script para ejecutar todos los tests y generar informe completo.
"""

import subprocess
import sys
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
TESTS_DIR = BASE_DIR / "tests"

# Tests a ejecutar (en orden de prioridad)
TESTS = [
    ("test_chat_integration.py", "Integración Chat + LLM + AI Actions"),
    ("test_ai_actions.py", "AI Actions (IntentParser + ActionExecutor)"),
    ("test_auth.py", "Autenticación y JWT"),
    ("test_providers.py", "Providers (OpenAI/Claude/HF)"),
    ("test_m4_integration.py", "Integración M4 (Multi-tenant)"),
]


def run_test(test_file: str) -> tuple[bool, str]:
    """Ejecuta un test y retorna (éxito, output)."""
    test_path = TESTS_DIR / test_file
    if not test_path.exists():
        return False, f"Test no encontrado: {test_file} (buscado en {test_path})"

    try:
        # Usar PYTHONPATH para que los imports funcionen
        env = subprocess.os.environ.copy()
        env["PYTHONPATH"] = str(BASE_DIR)

        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(BASE_DIR),
            env=env,
        )
        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, output
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT: Test excedió 60 segundos"
    except Exception as e:
        return False, f"ERROR: {str(e)}"


def main():
    logger.info("%s", "=" * 80)
    logger.info(" EJECUCIÓN COMPLETA DE TESTS - SimpleIA Project")
    logger.info("%s", "=" * 80)
    logger.info(" Fecha: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("%s", "=" * 80)
    logger.info("")

    results = []

    for test_file, description in TESTS:
        logger.info("\n%s", "=" * 80)
        logger.info(" TEST: %s", description)
        logger.info(" Archivo: %s", test_file)
        logger.info("%s", "=" * 80)

        success, output = run_test(test_file)
        results.append((test_file, description, success, output))

        if success:
            logger.info("✅ PASSED")
            # Mostrar últimas 20 líneas si pasó
            lines = output.split("\n")
            for line in lines[-20:]:
                if line.strip():
                    logger.info("   %s", line)
        else:
            logger.error("❌ FAILED")
            # Mostrar últimas 50 líneas si falló
            lines = output.split("\n")
            for line in lines[-50:]:
                if line.strip():
                    logger.error("   %s", line)

    # Resumen final
    logger.info("\n%s", "=" * 80)
    logger.info(" RESUMEN DE RESULTADOS")
    logger.info("%s", "=" * 80)

    passed = sum(1 for _, _, success, _ in results if success)
    failed = len(results) - passed

    for test_file, description, success, _ in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(" %s | %s", status, description)

    logger.info("%s", "=" * 80)
    logger.info(
        " Total: %s tests | ✅ %s passed | ❌ %s failed", len(results), passed, failed
    )
    logger.info("%s", "=" * 80)

    # Guardar informe
    report_path = BASE_DIR / "test_report.txt"
    with open(report_path, "w") as f:
        f.write("=" * 80 + "\n")
        f.write(" INFORME DE TESTS - SimpleIA Project\n")
        f.write("=" * 80 + "\n")
        f.write(f" Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        for test_file, description, success, output in results:
            f.write(f"\n{'=' * 80}\n")
            f.write(f" TEST: {description}\n")
            f.write(f" Archivo: {test_file}\n")
            f.write(f" Estado: {'PASSED' if success else 'FAILED'}\n")
            f.write("=" * 80 + "\n")
            f.write(output)
            f.write("\n\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write(" RESUMEN\n")
        f.write("=" * 80 + "\n")
        f.write(f" Total: {len(results)} tests\n")
        f.write(f" Passed: {passed}\n")
        f.write(f" Failed: {failed}\n")
        f.write("=" * 80 + "\n")

    logger.info("\n📄 Informe completo guardado en: %s", report_path)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
