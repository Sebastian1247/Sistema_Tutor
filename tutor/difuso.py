"""Sistema de inferencia difusa Mamdani para asignar el nivel del estudiante.

Entradas : tiempo (min), errores, ayudas
Salida   : nivel recomendado para el siguiente problema
"""

import warnings

import matplotlib.pyplot as plt
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

from tutor import config

# =====================================================================
# Pasos 2 y 3: universos y funciones de pertenencia
# =====================================================================

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

# =====================================================================
# Paso 4: base de reglas (27 = 3 x 3 x 3)
# Criterio: bueno = 2, regular = 1, malo = 0
#           suma >= 5 -> avanzado | 3-4 -> intermedio | <= 2 -> novato
# Excepción (veto): si ayudas es "muchas" -> novato, porque muchas ayudas
# indican que el estudiante dependió del tutor (las pruebas del chatbot
# mostraron que con ~7 preguntas puede revelar la solución).
# =====================================================================

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

# Paso 5: el sistema (Mamdani: AND = min, implicación = min, agregación = max)
sistema = ctrl.ControlSystem(reglas)


# =====================================================================
# Funciones de uso
# =====================================================================

def recortar(t, e, a):
    """Recorta las entradas a su universo (ej. 80 min se evalúa como 60)."""
    return (float(np.clip(t, 0, config.TIEMPO_MAXIMO)),
            float(np.clip(e, 0, config.ERRORES_MAXIMOS)),
            float(np.clip(a, 0, config.AYUDAS_MAXIMAS)))


def fuzzificar(variable, valor):
    """Grado de pertenencia de un valor a cada término de una variable."""
    return {nombre: float(fuzz.interp_membership(variable.universe, termino.mf, valor))
            for nombre, termino in variable.terms.items()}


def inferir(t, e, a):
    """Ejecuta la inferencia completa. Devuelve (valor nítido, etiqueta, simulación)."""
    t, e, a = recortar(t, e, a)
    simulacion = ctrl.ControlSystemSimulation(sistema)
    simulacion.input["tiempo"] = t
    simulacion.input["errores"] = e
    simulacion.input["ayudas"] = a
    simulacion.compute()                                       # pasos 1 a 6

    valor = simulacion.output["nivel"]                         # centroide
    grados = fuzzificar(nivel, valor)                          # paso 7
    etiqueta = max(grados, key=grados.get)
    return valor, etiqueta, simulacion


def tabla_fuzzificacion(t, e, a):
    """Paso 1 en forma de tabla: una fila por término de cada entrada."""
    t, e, a = recortar(t, e, a)
    filas = []
    for variable, valor in [(tiempo, t), (errores, e), (ayudas, a)]:
        for termino, grado in fuzzificar(variable, valor).items():
            filas.append({"variable": variable.label, "valor": valor,
                          "término": termino, "grado": round(grado, 3)})
    return filas


def reglas_activadas(t, e, a):
    """Reglas con fuerza > 0, para mostrarlas en la interfaz.
    Fuerza de una regla = mínimo de los grados de sus antecedentes (AND)."""
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
    """Intervalo de la salida donde cada nivel tiene pertenencia > 0 (para la interfaz)."""
    u = nivel.universe
    return {nombre: (float(u[termino.mf > 0].min()), float(u[termino.mf > 0].max()))
            for nombre, termino in nivel.terms.items()}


def figura_salida(t, e, a):
    """Conjunto agregado de la salida y el centroide, como figura de matplotlib.
    La interfaz recibe la figura y no necesita saber que el motor es skfuzzy."""
    _, _, simulacion = inferir(t, e, a)
    with warnings.catch_warnings():
        # skfuzzy llama a fig.show(), que avisa cuando el backend no tiene ventanas
        warnings.filterwarnings("ignore", message=".*non-interactive.*")
        nivel.view(sim=simulacion)
    return plt.gcf()
