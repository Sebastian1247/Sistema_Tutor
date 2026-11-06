"""Valida un problema generado por el LLM ejecutando su solución de referencia.

Idea: el LLM puede equivocarse al calcular "de cabeza" las salidas esperadas
(ej. 48392 -> dijo 2 dígitos pares, son 3). Ejecutar la solución es más
confiable que su aritmética mental, así que:
  - si la solución no compila o truena  -> el problema se descarta
  - si la solución da otra salida       -> se corrige la salida esperada
"""

import ejecutor


def _arreglar_saltos(texto):
    """A veces el LLM escribe '\\n' como texto en lugar de un salto de línea real."""
    return texto.replace("\\n", "\n")


def validar_problema(problema):
    """Regresa (problema, correcciones). Lanza ValueError si la solución no sirve."""
    correcciones = []

    # 1. Normalizar saltos de línea
    problema.ejemplo_entrada = _arreglar_saltos(problema.ejemplo_entrada)
    problema.ejemplo_salida = _arreglar_saltos(problema.ejemplo_salida)
    for caso in problema.casos_prueba:
        caso.entrada = _arreglar_saltos(caso.entrada)
        caso.salida = _arreglar_saltos(caso.salida)

    # 2. La solución debe compilar
    ok, mensaje = ejecutor.compilar(problema.solucion)
    if not ok:
        raise ValueError(f"La solución de referencia no compila: {mensaje}")

    # 3. Ejecutar la solución con cada caso de prueba
    for i, caso in enumerate(problema.casos_prueba, start=1):
        ok, salida = ejecutor.ejecutar(problema.solucion, caso.entrada)
        if not ok:
            raise ValueError(f"La solución de referencia falla en el caso {i}")
        if ejecutor.normalizar(salida) != ejecutor.normalizar(caso.salida):
            correcciones.append(f"Caso {i}: el LLM esperaba '{caso.salida.strip()}', "
                                f"la solución da '{salida.strip()}'")
            caso.salida = salida.strip()

    # 4. Lo mismo con el ejemplo que ve el estudiante
    ok, salida = ejecutor.ejecutar(problema.solucion, problema.ejemplo_entrada)
    if not ok:
        raise ValueError("La solución de referencia falla con el ejemplo")
    if ejecutor.normalizar(salida) != ejecutor.normalizar(problema.ejemplo_salida):
        correcciones.append(f"Ejemplo: el LLM esperaba '{problema.ejemplo_salida.strip()}', "
                            f"la solución da '{salida.strip()}'")
        problema.ejemplo_salida = salida.strip()

    return problema, correcciones