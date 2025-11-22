#!/usr/bin/env python3
"""
Script para ejecutar todos los tests y generar informe completo.
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime

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
        env['PYTHONPATH'] = str(BASE_DIR)
        
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(BASE_DIR),
            env=env
        )
        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, output
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT: Test excedió 60 segundos"
    except Exception as e:
        return False, f"ERROR: {str(e)}"


def main():
    print("=" * 80)
    print(" EJECUCIÓN COMPLETA DE TESTS - SimpleIA Project")
    print("=" * 80)
    print(f" Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    results = []
    
    for test_file, description in TESTS:
        print(f"\n{'=' * 80}")
        print(f" TEST: {description}")
        print(f" Archivo: {test_file}")
        print("=" * 80)
        
        success, output = run_test(test_file)
        results.append((test_file, description, success, output))
        
        if success:
            print("✅ PASSED")
            # Mostrar últimas 20 líneas si pasó
            lines = output.split('\n')
            for line in lines[-20:]:
                if line.strip():
                    print(f"   {line}")
        else:
            print("❌ FAILED")
            # Mostrar últimas 50 líneas si falló
            lines = output.split('\n')
            for line in lines[-50:]:
                if line.strip():
                    print(f"   {line}")
    
    # Resumen final
    print("\n" + "=" * 80)
    print(" RESUMEN DE RESULTADOS")
    print("=" * 80)
    
    passed = sum(1 for _, _, success, _ in results if success)
    failed = len(results) - passed
    
    for test_file, description, success, _ in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f" {status} | {description}")
    
    print("=" * 80)
    print(f" Total: {len(results)} tests | ✅ {passed} passed | ❌ {failed} failed")
    print("=" * 80)
    
    # Guardar informe
    report_path = BASE_DIR / "test_report.txt"
    with open(report_path, 'w') as f:
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
    
    print(f"\n📄 Informe completo guardado en: {report_path}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
