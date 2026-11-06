"""Compilación y ejecución del código del estudiante."""

import os
import subprocess
import sys
import tempfile

LIMITE_SEGUNDOS = 5

# El programa del estudiante (y la solución del LLM) corre con un entorno mínimo:
# si se copiara os.environ, podría leer GROQ_API_KEY, que load_dotenv carga ahí.
VARIABLES_PERMITIDAS = ("SYSTEMROOT", "PATH", "TEMP", "TMP")


def _entorno_seguro():
    return {nombre: os.environ[nombre] for nombre in VARIABLES_PERMITIDAS
            if nombre in os.environ}


def compilar(codigo):
    """Revisa la sintaxis sin ejecutar. Regresa (ok, mensaje)."""
    if not codigo.strip():
        return False, "El editor está vacío."
    try:
        compile(codigo, "<tu código>", "exec")
        return True, "Compilación correcta: no hay errores de sintaxis."
    except SyntaxError as error:
        linea = (error.text or "").rstrip()
        marca = " " * max((error.offset or 1) - 1, 0) + "^"
        return False, (f"{type(error).__name__} en la línea {error.lineno}: {error.msg}\n"
                       f"    {linea}\n"
                       f"    {marca}")


def ejecutar(codigo, entrada=""):
    """Corre el código en un proceso aparte. Regresa (ok, salida)."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as archivo:
        archivo.write(codigo)
        ruta = archivo.name

    try:
        # -I aísla al programa (ignora variables PYTHON* y el directorio actual), por eso
        # la codificación se fija con -X utf8 y no con PYTHONIOENCODING: sin esto, en
        # Windows la salida sale en cp1252 y una "ñ" rompe la lectura.
        proceso = subprocess.run(
            [sys.executable, "-I", "-X", "utf8", ruta],
            input=entrada,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=LIMITE_SEGUNDOS,
            env=_entorno_seguro(),
        )
        salida = proceso.stdout + proceso.stderr.replace(ruta, "tu_programa.py")
        if not salida:
            salida = "(el programa no imprimió nada)"
        return proceso.returncode == 0, salida

    except subprocess.TimeoutExpired:
        return False, (f"Tiempo agotado: el programa tardó más de {LIMITE_SEGUNDOS} s. "
                       "¿Hay un ciclo infinito?")
    finally:
        os.remove(ruta)


def normalizar(texto):
    """Ignora espacios al final de cada línea y líneas vacías al inicio/final."""
    return "\n".join(linea.rstrip() for linea in texto.strip().splitlines())


def evaluar_pruebas(codigo, casos):
    """Ejecuta el código con cada caso de prueba y compara la salida.
    casos: lista de objetos con atributos .entrada y .salida
    Regresa una lista de diccionarios, uno por caso."""
    resultados = []
    for caso in casos:
        ok, salida = ejecutar(codigo, caso.entrada)
        resultados.append({
            "entrada": caso.entrada,
            "esperada": caso.salida,
            "obtenida": salida,
            "paso": ok and normalizar(salida) == normalizar(caso.salida),
        })
    return resultados
