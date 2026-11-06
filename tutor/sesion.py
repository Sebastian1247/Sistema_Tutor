"""Reglas del flujo de un problema, independientes de la interfaz.

Define qué cuenta como error, qué pasa al entregar, cómo se evalúa "me rindo"
y cuánto puede cambiar el nivel. Son funciones puras (reciben datos y regresan
datos), por lo que se prueban sin Streamlit y sin el LLM.
"""

import re
import time
from dataclasses import dataclass

from tutor import config, difuso, ejecutor
from tutor.modelos import Resultado


@dataclass
class Retroalimentacion:
    """Lo que la consola debe mostrar después de una acción del estudiante.

    Attributes:
        ok: True si la acción terminó sin errores.
        mensaje: Texto para la consola.
        cuenta_error: True si la acción suma un error al estudiante.
        resultados_pruebas: Resultado de cada caso de prueba (sólo al entregar).
        resuelto: True si la entrega pasó todos los casos.
        etapa: Etapa que produjo el mensaje: ``"compilacion"``, ``"ejecucion"``
            o ``"entrega"``.
    """

    ok: bool
    mensaje: str
    cuenta_error: bool = False
    resultados_pruebas: list | None = None
    resuelto: bool = False
    etapa: str = "compilacion"


def minutos_transcurridos(inicio, fin=None, ahora=None):
    """Calcula los minutos que lleva el problema.

    Args:
        inicio: Marca de tiempo (``time.time()``) en que apareció el problema,
            o None si todavía no hay problema.
        fin: Marca de tiempo en que terminó; si existe, el reloj se detiene ahí.
        ahora: Marca de tiempo actual. Se puede fijar en las pruebas.

    Returns:
        Minutos transcurridos (0.0 si no hay problema).
    """
    if inicio is None:
        return 0.0
    fin = fin or ahora or time.time()
    return (fin - inicio) / 60


def siguiente_nivel(actual, recomendado):
    """Mueve el nivel hacia el recomendado, como máximo un escalón por problema.

    Args:
        actual: Nivel del problema que se terminó.
        recomendado: Nivel que decidió el sistema difuso.

    Returns:
        Nivel del siguiente problema.
    """
    i, j = config.NIVELES.index(actual), config.NIVELES.index(recomendado)
    if j > i:
        return config.NIVELES[i + 1]
    if j < i:
        return config.NIVELES[i - 1]
    return actual


def procesar_compilacion(codigo):
    """Revisa la sintaxis; un error de sintaxis cuenta como error del estudiante."""
    ok, mensaje = ejecutor.compilar(codigo)
    return Retroalimentacion(ok, mensaje, cuenta_error=not ok)


def procesar_ejecucion(codigo, entrada):
    """Compila y, si no hay errores de sintaxis, ejecuta el código.

    Args:
        codigo: Código del estudiante.
        entrada: Texto que leerá ``input()``.

    Returns:
        ``Retroalimentacion`` de la compilación si falló, o de la ejecución. Si
        el programa pidió más datos de los que había, el mensaje lo sugiere.
    """
    compilacion = procesar_compilacion(codigo)
    if not compilacion.ok:
        return compilacion

    ok, salida = ejecutor.ejecutar(codigo, entrada)
    if "EOFError" in salida:
        salida += ("\nSugerencia: tu programa usa input() pero no hay suficientes datos "
                   "en el cuadro de entrada. Escríbelos ahí, uno por línea.")
    return Retroalimentacion(ok, salida, cuenta_error=not ok, etapa="ejecucion")


def procesar_entrega(codigo, casos):
    """Ejecuta los casos de prueba; el problema se resuelve sólo si pasan todos.

    Args:
        codigo: Código del estudiante.
        casos: Casos de prueba del problema.

    Returns:
        ``Retroalimentacion`` con el resultado de cada caso. Una entrega
        incorrecta cuenta como error.
    """
    compilacion = procesar_compilacion(codigo)
    if not compilacion.ok:
        return compilacion

    resultados = ejecutor.evaluar_pruebas(codigo, casos)
    aprobados = sum(r["paso"] for r in resultados)
    if aprobados == len(resultados):
        return Retroalimentacion(True, f"Correcto: pasaste los {len(resultados)} casos de prueba.",
                                 resultados_pruebas=resultados, resuelto=True, etapa="entrega")
    return Retroalimentacion(False, f"Incorrecto: pasaste {aprobados} de {len(resultados)} casos "
                                    "de prueba. Revisa la pestaña de casos de prueba.",
                             cuenta_error=True, resultados_pruebas=resultados, etapa="entrega")


# Explican qué significa cada tipo de error, no dónde está ni cómo arreglarlo:
# eso le toca al estudiante, o al tutor (y entonces sí cuenta como ayuda).
PISTAS_ERRORES = {
    "SyntaxError": "Python no entiende cómo está escrita una línea. Revisa los dos puntos (:) "
                   "al final de if, for, while y def, y que cada paréntesis o comilla que abres "
                   "se cierre.",
    "IndentationError": "La sangría (los espacios al inicio de la línea) no es consistente. Las "
                        "líneas dentro de un mismo if, for o def deben tener la misma sangría.",
    "NameError": "Usaste un nombre que no está definido. Revisa mayúsculas y minúsculas, y que "
                 "la variable exista antes de usarla.",
    "UnboundLocalError": "Dentro de una función usaste una variable antes de asignarle un valor.",
    "TypeError": "Combinaste tipos de datos incompatibles, por ejemplo texto con número. "
                 "Recuerda que input() siempre regresa texto.",
    "ValueError": "El dato tiene un contenido que no se puede convertir, por ejemplo int('hola'). "
                  "Revisa qué llega desde input().",
    "IndexError": "Pediste una posición que no existe. En una lista o cadena las posiciones van "
                  "de 0 a len() - 1.",
    "KeyError": "Buscaste en un diccionario una clave que no existe.",
    "ZeroDivisionError": "Hubo una división entre cero.",
    "AttributeError": "Usaste un método o atributo que ese tipo de dato no tiene.",
    "RecursionError": "La función se llama a sí misma demasiadas veces: revisa que exista un "
                      "caso base y que se alcance.",
    "ModuleNotFoundError": "Intentaste importar un módulo que no existe.",
}


def pista_error(salida):
    """Busca una pista para el último error de Python que aparece en la salida.

    Args:
        salida: Texto de la consola (traceback o mensaje de compilación).

    Returns:
        La pista del tipo de error, o None si no hay error conocido.
    """
    tipos = re.findall(r"^(\w+(?:Error|Exception))\b", salida, re.MULTILINE)
    return PISTAS_ERRORES.get(tipos[-1]) if tipos else None


def evaluar_desempeno(resuelto, minutos, errores, ayudas, nivel_problema):
    """Decide el nivel del siguiente problema con la inferencia Mamdani.

    El nivel recomendado siempre sale de ``difuso.inferir``. Rendirse se evalúa
    con el peor caso: tiempo máximo y al menos los errores máximos.

    Args:
        resuelto: True si el estudiante pasó todos los casos; False si se rindió.
        minutos: Tiempo que tardó.
        errores: Errores contados durante el problema.
        ayudas: Preguntas que respondió el tutor.
        nivel_problema: Nivel del problema que se terminó.

    Returns:
        ``Resultado`` con las entradas usadas, la salida nítida, el nivel
        recomendado y el nivel del siguiente problema.
    """
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


def _cantidad(n, singular, plural):
    """Regresa ``n`` con la palabra en singular o plural (``"1 ayuda"``, ``"2 ayudas"``)."""
    return f"{n} {singular if n == 1 else plural}"


def explicar_resultado(resultado, nivel_problema):
    """Explica en lenguaje simple la decisión de la inferencia Mamdani.

    Sólo describe la decisión con los mismos grados de pertenencia y reglas del
    sistema difuso; no la modifica.

    Args:
        resultado: ``Resultado`` de ``evaluar_desempeno``.
        nivel_problema: Nivel del problema que se terminó.

    Returns:
        Texto en Markdown para el banner de resultado.
    """
    t, e, a = difuso.recortar(resultado.tiempo, resultado.errores, resultado.ayudas)
    # Término con mayor grado de pertenencia de cada entrada ("corto", "algunos"...).
    termino = {nombre: max(grados, key=grados.get) for nombre, grados in [
        ("tiempo", difuso.fuzzificar(difuso.tiempo, t)),
        ("errores", difuso.fuzzificar(difuso.errores, e)),
        ("ayudas", difuso.fuzzificar(difuso.ayudas, a)),
    ]}
    errores = _cantidad(resultado.errores, "error", "errores")
    ayudas = _cantidad(resultado.ayudas, "ayuda", "ayudas")

    i = config.NIVELES.index(nivel_problema)
    j = config.NIVELES.index(resultado.siguiente)
    accion = "Subes a" if j > i else "Bajas a" if j < i else "Te mantienes en"
    frases = [f"**{accion} {resultado.siguiente}.**"]

    if resultado.resuelto:
        frases.append(f"Resolviste en {resultado.tiempo:.1f} min (tiempo {termino['tiempo']}), "
                      f"con {errores} ({termino['errores']}) y {ayudas} ({termino['ayudas']}).")
    else:
        frases.append(f"Te rendiste, así que se evaluó el peor caso: {resultado.tiempo:.0f} min "
                      f"y {errores}, con {ayudas} ({termino['ayudas']}).")

    activas = difuso.reglas_activadas(t, e, a)
    if activas:
        regla = activas[0]  # la de mayor fuerza
        frases.append(f"La regla que más pesó: tiempo {regla['SI tiempo es']}, "
                      f"{regla['Y errores son']} errores y {regla['Y ayudas son']} ayudas "
                      f"→ {regla['ENTONCES nivel es']}.")
        if regla["Y ayudas son"] == "muchas":
            frases.append("Pediste muchas ayudas: eso indica que dependiste del tutor, "
                          "por eso se recomienda novato.")
    frases.append(f"Al combinar las {len(activas)} reglas activas el puntaje fue "
                  f"{resultado.valor:.1f} de 10, que corresponde a {resultado.recomendado}.")

    if resultado.siguiente != resultado.recomendado:
        frases.append(f"El nivel cambia como máximo un escalón por problema, por eso pasas a "
                      f"{resultado.siguiente} y no directo a {resultado.recomendado}.")
    return " ".join(frases)
