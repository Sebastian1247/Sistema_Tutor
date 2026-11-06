"""Gráficas del sistema difuso como figuras de matplotlib (sin Streamlit).

La interfaz pide una figura y no necesita saber que el motor es skfuzzy.
"""

import warnings

import matplotlib.pyplot as plt

from difuso import sistema


def figura_salida(t, e, a):
    """Conjunto agregado de la salida y el centroide para estas entradas."""
    _, _, simulacion = sistema.inferir(t, e, a)
    with warnings.catch_warnings():
        # skfuzzy llama a fig.show(), que avisa cuando el backend no tiene ventanas
        warnings.filterwarnings("ignore", message=".*non-interactive.*")
        sistema.nivel.view(sim=simulacion)
    return plt.gcf()
