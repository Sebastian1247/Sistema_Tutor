"""Reglas del flujo de un problema, sin Streamlit.

Aquí vive lo que antes estaba dentro de los callbacks de app.py: qué cuenta
como error, qué pasa al entregar, cómo se evalúa "me rindo" y cuánto puede
cambiar el nivel. Son funciones puras (reciben datos y regresan datos), por eso
se pueden probar con pytest.
"""

import time
from dataclasses import dataclass

from tutor import config, difuso, ejecutor
from tutor.modelos import Resultado


@dataclass
class Retroalimentacion:
    """Lo que la consola debe mostrar después de una acción del estudiante."""
    ok: bool
    mensaje: str
    cuenta_error: bool = False
    resultados_pruebas: list | None = None     # sólo al entregar
    resuelto: bool = False


def minutos_transcurridos(inicio, fin=None, ahora=None):
    """El reloj se detiene al terminar (fin). ahora se inyecta en las pruebas."""
    if inicio is None:
        return 0.0
    fin = fin or ahora or time.time()
    return (fin - inicio) / 60


def siguiente_nivel(actual, recomendado):
    """El nivel sube o baja como máximo un escalón por problema."""
    i, j = config.NIVELES.index(actual), config.NIVELES.index(recomendado)
    if j > i:
        return config.NIVELES[i + 1]
    if j < i:
        return config.NIVELES[i - 1]
    return actual


def procesar_compilacion(codigo):
    ok, mensaje = ejecutor.compilar(codigo)
    return Retroalimentacion(ok, mensaje, cuenta_error=not ok)


def procesar_ejecucion(codigo, entrada):
    """Compila antes de ejecutar: un error de sintaxis se reporta igual que al compilar."""
    compilacion = procesar_compilacion(codigo)
    if not compilacion.ok:
        return compilacion

    ok, salida = ejecutor.ejecutar(codigo, entrada)
    if "EOFError" in salida:
        salida += ("\nSugerencia: tu programa usa input() pero no hay suficientes datos "
                   "en el cuadro de entrada. Escríbelos ahí, uno por línea.")
    return Retroalimentacion(ok, salida, cuenta_error=not ok)


def procesar_entrega(codigo, casos):
    """Corre los casos de prueba. Resuelve el problema sólo si pasan todos."""
    compilacion = procesar_compilacion(codigo)
    if not compilacion.ok:
        return compilacion

    resultados = ejecutor.evaluar_pruebas(codigo, casos)
    aprobados = sum(r["paso"] for r in resultados)
    if aprobados == len(resultados):
        return Retroalimentacion(True, f"Correcto: pasaste los {len(resultados)} casos de prueba.",
                                 resultados_pruebas=resultados, resuelto=True)
    return Retroalimentacion(False, f"Incorrecto: pasaste {aprobados} de {len(resultados)} casos "
                                    "de prueba. Revisa los detalles abajo.",
                             cuenta_error=True, resultados_pruebas=resultados)


def evaluar_desempeno(resuelto, minutos, errores, ayudas, nivel_problema):
    """Aplica el sistema difuso. Rendirse se evalúa con el peor caso:
    tiempo máximo y al menos los errores máximos."""
    if resuelto:
        tiempo = minutos
    else:
        tiempo = config.TIEMPO_MAXIMO
        errores = max(errores, config.ERRORES_MAXIMOS)

    valor, recomendado, _ = difuso.inferir(tiempo, errores, ayudas)
    return Resultado(
        resuelto=resuelto, tiempo=tiempo, errores=errores, ayudas=ayudas,
        valor=valor, recomendado=recomendado,
        siguiente=siguiente_nivel(nivel_problema, recomendado),
    )
