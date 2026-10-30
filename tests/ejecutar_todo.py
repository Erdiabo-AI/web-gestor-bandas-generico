"""Ejecuta todas las pruebas y resume el resultado.

Uso (desde la carpeta del proyecto):  .venv\\Scripts\\python tests\\ejecutar_todo.py
Usa la BBDD de .env con datos temporales (@e2e.test) que se borran al terminar.
"""
import os
import subprocess
import sys

CARPETA = os.path.dirname(os.path.abspath(__file__))
PRUEBAS = ["test_general.py", "test_miembros.py", "test_concurrencia.py", "test_dos_lineas.py"]

entorno = dict(os.environ, PYTHONIOENCODING="utf-8")
fallidas = []
for prueba in PRUEBAS:
    print(f"\n=== {prueba}")
    r = subprocess.run([sys.executable, os.path.join(CARPETA, prueba)], cwd=CARPETA, env=entorno,
                       capture_output=True, text=True, encoding="utf-8")
    lineas = [l for l in r.stdout.splitlines() if l.strip()]
    for l in lineas:
        if l.startswith("FAIL") or l.startswith("RESULTADO"):
            print(l)
    print(f"({sum(l.startswith('OK') for l in lineas)} comprobaciones correctas)")
    if r.returncode != 0:
        fallidas.append(prueba)
        if r.stderr.strip():
            print(r.stderr.strip()[-2000:])

print("\n" + ("TODAS LAS PRUEBAS OK" if not fallidas else f"FALLAN: {', '.join(fallidas)}"))
sys.exit(1 if fallidas else 0)
