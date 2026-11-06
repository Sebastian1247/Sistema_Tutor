"""Prueba manual del sistema difuso: imprime casos de ejemplo y muestra las gráficas.

Uso:
    python -m scripts.probar_fuzzy

Las pruebas automáticas del sistema difuso están en ``tests/test_difuso.py``.
"""

import matplotlib.pyplot as plt

from tutor.difuso import ayudas, errores, fuzzificar, inferir, nivel, tiempo

# Paso 1: fuzzificación (compara con la tabla del ejemplo a mano)
print("tiempo = 10  ->", fuzzificar(tiempo, 10))
print("errores = 4  ->", fuzzificar(errores, 4))
print("ayudas = 1.5 ->", fuzzificar(ayudas, 1.5))
print()

casos = [
    (3, 0, 0, "rápido, sin errores ni ayudas"),
    (10, 4, 1.5, "ejemplo resuelto a mano"),
    (18, 5, 3, "todo regular"),
    (2, 0, 8, "rápido pero con muchas ayudas (veto)"),
    (45, 10, 7, "lento, muchos errores y ayudas"),
]
for t, e, a, descripcion in casos:
    valor, etiqueta, _ = inferir(t, e, a)
    print(f"t={t:>4} e={e:>4} a={a:>4} -> nivel={valor:5.2f} ({etiqueta:10}) {descripcion}")

tiempo.view()
errores.view()
ayudas.view()
_, _, simulacion = inferir(10, 4, 1.5)
nivel.view(sim=simulacion)
plt.show()
