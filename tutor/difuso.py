"""Sistema de inferencia difusa Mamdani que asigna el nivel del estudiante.

Entradas: tiempo (minutos), errores y ayudas. Salida: nivel recomendado para
el siguiente problema (novato, intermedio o avanzado).

Operadores Mamdani: AND = mínimo, implicación = mínimo, agregación = máximo y
defuzzificación por centroide.
"""

import warnings

import matplotlib.pyplot as plt
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

from tutor import config

# --- Universos y funciones de pertenencia ---

tiempo = ctrl.Antecedent(np.linspace(0, config.TIEMPO_MAXIMO, 601), "tiempo")
errores = ctrl.Antecedent(np.linspace(0, config.ERRORES_MAXIMOS, 151), "errores")
ayudas = ctrl.Antecedent(np.linspace(0, config.AYUDAS_MAXIMAS, 101), "ayudas")
nivel = ctrl.Consequent(np.linspace(0, 10, 1001), "nivel", defuzzify_method="centroid")

tiempo["corto"] = fuzz.trapmf(tiempo.universe, [0, 0, 5, 12])
tiempo["medio"] = fuzz.trimf(tiempo.universe, [8, 18, 30])
tiempo["largo"] = fuzz.trapmf(tiempo.universe, [25, 40, 60, 60])

errores["pocos"] = fuzz.trapmf(errores.universe, [0, 0, 1, 3])
errores["algunos"] = fuzz.trimf(errores.universe, [2, 5, 8])
errores["muchos"] = fuzz.trapmf(errores.universe, [6, 10, 15, 15])

ayudas["pocas"] = fuzz.trapmf(ayudas.universe, [0, 0, 1, 2])
ayudas["algunas"] = fuzz.trimf(ayudas.universe, [1, 3, 5])
ayudas["muchas"] = fuzz.trapmf(ayudas.universe, [4, 6, 10, 10])

nivel["novato"] = fuzz.trapmf(nivel.universe, [0, 0, 2, 4])
nivel["intermedio"] = fuzz.trimf(nivel.universe, [3, 5, 7])
nivel["avanzado"] = fuzz.trapmf(nivel.universe, [6, 8, 10, 10])

# --- Base de reglas: 27 = 3 x 3 x 3 ---
#
# Cada entrada vale bueno = 2, regular = 1 o malo = 0, y el consecuente sale
# de la suma: >= 5 avanzado, 3-4 intermedio, <= 2 novato.
# Veto: si las ayudas son "muchas" el consecuente es novato, porque muchas
# ayudas indican que el estudiante dependió del tutor (en las pruebas del
# chatbot, con unas 7 preguntas llegaba a revelar la solución).

#         tiempo    errores    ayudas      ->  nivel          puntos
REGLAS = [
    ("corto", "pocos",   "pocas",   "avanzado"),     # R1   6
    ("corto", "pocos",   "algunas", "avanzado"),     # R2   5
    ("corto", "pocos",   "muchas",  "novato"),       # R3   4 -> veto
    ("corto", "algunos", "pocas",   "avanzado"),     # R4   5
    ("corto", "algunos", "algunas", "intermedio"),   # R5   4
    ("corto", "algunos", "muchas",  "novato"),       # R6   3 -> veto
    ("corto", "muchos",  "pocas",   "intermedio"),   # R7   4
    ("corto", "muchos",  "algunas", "intermedio"),   # R8   3
    ("corto", "muchos",  "muchas",  "novato"),       # R9   2
    ("medio", "pocos",   "pocas",   "avanzado"),     # R10  5
    ("medio", "pocos",   "algunas", "intermedio"),   # R11  4
    ("medio", "pocos",   "muchas",  "novato"),       # R12  3 -> veto
    ("medio", "algunos", "pocas",   "intermedio"),   # R13  4
    ("medio", "algunos", "algunas", "intermedio"),   # R14  3
    ("medio", "algunos", "muchas",  "novato"),       # R15  2
    ("medio", "muchos",  "pocas",   "intermedio"),   # R16  3
    ("medio", "muchos",  "algunas", "novato"),       # R17  2
    ("medio", "muchos",  "muchas",  "novato"),       # R18  1
    ("largo", "pocos",   "pocas",   "intermedio"),   # R19  4
    ("largo", "pocos",   "algunas", "intermedio"),   # R20  3
    ("largo", "pocos",   "muchas",  "novato"),       # R21  2
    ("largo", "algunos", "pocas",   "intermedio"),   # R22  3
    ("largo", "algunos", "algunas", "novato"),       # R23  2
    ("largo", "algunos", "muchas",  "novato"),       # R24  1
    ("largo", "muchos",  "pocas",   "novato"),       # R25  2
    ("largo", "muchos",  "algunas", "novato"),       # R26  1
    ("largo", "muchos",  "muchas",  "novato"),       # R27  0
]

reglas = [
    ctrl.Rule(tiempo[t] & errores[e] & ayudas[a], nivel[c], label=f"R{i}")
    for i, (t, e, a, c) in enumerate(REGLAS, start=1)
]

# scikit-fuzzy usa por defecto los operadores Mamdani (mín, mín, máx).
sistema = ctrl.ControlSystem(reglas)


# --- Funciones de uso ---

def recortar(t, e, a):
    """Recorta las entradas a su universo (por ejemplo, 80 min se evalúa como 60).

    Returns:
        Tupla ``(tiempo, errores, ayudas)`` como ``float``.
    """
    return (float(np.clip(t, 0, config.TIEMPO_MAXIMO)),
            float(np.clip(e, 0, config.ERRORES_MAXIMOS)),
            float(np.clip(a, 0, config.AYUDAS_MAXIMAS)))


def fuzzificar(variable, valor):
    """Calcula el grado de pertenencia de un valor a cada término de una variable.

    Args:
        variable: ``Antecedent`` o ``Consequent`` de scikit-fuzzy.
        valor: Valor nítido dentro del universo de la variable.

    Returns:
        Diccionario ``{término: grado}`` con grados entre 0 y 1.
    """
    return {nombre: float(fuzz.interp_membership(variable.universe, termino.mf, valor))
            for nombre, termino in variable.terms.items()}


def inferir(t, e, a):
    """Ejecuta la inferencia Mamdani completa.

    Args:
        t: Tiempo en minutos.
        e: Errores.
        a: Ayudas.

    Returns:
        Tupla ``(valor, etiqueta, simulacion)``: ``valor`` es la salida nítida
        (centroide), ``etiqueta`` el término de salida con mayor pertenencia en
        ese valor y ``simulacion`` la ``ControlSystemSimulation`` usada.
    """
    t, e, a = recortar(t, e, a)
    simulacion = ctrl.ControlSystemSimulation(sistema)
    simulacion.input["tiempo"] = t
    simulacion.input["errores"] = e
    simulacion.input["ayudas"] = a
    simulacion.compute()  # fuzzificación, reglas, implicación, agregación y centroide

    valor = simulacion.output["nivel"]
    grados = fuzzificar(nivel, valor)
    etiqueta = max(grados, key=grados.get)
    return valor, etiqueta, simulacion


def tabla_fuzzificacion(t, e, a):
    """Regresa la fuzzificación de las tres entradas como filas de una tabla.

    Returns:
        Lista con una fila por término: ``variable``, ``valor``, ``término`` y ``grado``.
    """
    t, e, a = recortar(t, e, a)
    filas = []
    for variable, valor in [(tiempo, t), (errores, e), (ayudas, a)]:
        for termino, grado in fuzzificar(variable, valor).items():
            filas.append({"variable": variable.label, "valor": valor,
                          "término": termino, "grado": round(grado, 3)})
    return filas


def reglas_activadas(t, e, a):
    """Regresa las reglas con fuerza mayor que cero, de la más fuerte a la más débil.

    La fuerza de una regla es el mínimo de los grados de sus antecedentes (AND).

    Returns:
        Lista de diccionarios con la regla, sus antecedentes, su consecuente y su fuerza.
    """
    t, e, a = recortar(t, e, a)
    gt, ge, ga = fuzzificar(tiempo, t), fuzzificar(errores, e), fuzzificar(ayudas, a)
    activas = []
    for i, (rt, re, ra, consecuente) in enumerate(REGLAS, start=1):
        fuerza = min(gt[rt], ge[re], ga[ra])
        if fuerza > 0:
            activas.append({
                "regla": f"R{i}",
                "SI tiempo es": rt,
                "Y errores son": re,
                "Y ayudas son": ra,
                "ENTONCES nivel es": consecuente,
                "fuerza": round(fuerza, 3),
            })
    return sorted(activas, key=lambda r: r["fuerza"], reverse=True)


def zonas_nivel():
    """Regresa el intervalo de la salida donde cada nivel tiene pertenencia mayor que cero.

    Returns:
        Diccionario ``{nivel: (inicio, fin)}``.
    """
    u = nivel.universe
    return {nombre: (float(u[termino.mf > 0].min()), float(u[termino.mf > 0].max()))
            for nombre, termino in nivel.terms.items()}


def figura_salida(t, e, a):
    """Dibuja el conjunto agregado de la salida y el centroide.

    La interfaz recibe una figura de matplotlib y no necesita conocer scikit-fuzzy.

    Returns:
        ``matplotlib.figure.Figure``; quien la reciba debe cerrarla con ``plt.close``.
    """
    _, _, simulacion = inferir(t, e, a)
    with warnings.catch_warnings():
        # scikit-fuzzy llama a fig.show(), que avisa cuando el backend no tiene ventanas.
        warnings.filterwarnings("ignore", message=".*non-interactive.*")
        nivel.view(sim=simulacion)
    return plt.gcf()
