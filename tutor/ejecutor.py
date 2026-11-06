"""Compilación y ejecución aislada del código del estudiante.

El código del estudiante y la solución que genera el LLM son código no
confiable: se ejecutan en un proceso aparte, con tiempo límite y sin acceso a
las variables de entorno del tutor (donde está ``GROQ_API_KEY``).
"""

import os
import subprocess
import sys
import tempfile

LIMITE_SEGUNDOS = 5

# Variables mínimas para que Python arranque en Windows. Copiar os.environ
# completo expondría GROQ_API_KEY, que load_dotenv carga ahí.
VARIABLES_PERMITIDAS = ("SYSTEMROOT", "PATH", "TEMP", "TMP")


def _entorno_seguro():
    """Regresa el entorno del proceso hijo, sólo con las variables permitidas."""
    return {nombre: os.environ[nombre] for nombre in VARIABLES_PERMITIDAS
            if nombre in os.environ}


def compilar(codigo):
    """Revisa la sintaxis del código sin ejecutarlo.

    Args:
        codigo: Código fuente en Python.

    Returns:
        Tupla ``(ok, mensaje)``. Si hay un error de sintaxis, el mensaje indica
        la línea y marca la columna con ``^``.
    """
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
    """Ejecuta el código en un proceso aparte.

    Args:
        codigo: Código fuente en Python.
        entrada: Texto que el programa leerá con ``input()``.

    Returns:
        Tupla ``(ok, salida)``: ``ok`` es True si el programa terminó sin error;
        ``salida`` junta stdout y stderr (con la ruta temporal oculta).
    """
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as archivo:
        archivo.write(codigo)
        ruta = archivo.name

    try:
        # -I aísla al programa: ignora las variables PYTHON* y el directorio
        # actual. Por eso la codificación se fija con -X utf8 y no con
        # PYTHONIOENCODING; sin ella, en Windows la salida sale en cp1252 y una
        # "ñ" rompe la lectura.
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
    """Normaliza una salida para compararla con la esperada.

    Quita los espacios al final de cada línea y las líneas vacías al inicio y
    al final, que no deben contar como diferencia.
    """
    return "\n".join(linea.rstrip() for linea in texto.strip().splitlines())


def evaluar_pruebas(codigo, casos):
    """Ejecuta el código con cada caso de prueba y compara la salida.

    Args:
        codigo: Código fuente en Python.
        casos: Objetos con atributos ``entrada`` y ``salida`` (``CasoPrueba``).

    Returns:
        Lista con un diccionario por caso: ``entrada``, ``esperada``,
        ``obtenida`` y ``paso`` (True si terminó sin error y la salida coincide).
    """
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
