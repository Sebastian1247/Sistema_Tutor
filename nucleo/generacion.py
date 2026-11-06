"""Obtiene un problema cuya solución de referencia funciona.

El generador se recibe como parámetro (inyección de dependencias): así este
módulo no depende del LLM y se prueba con un generador falso, sin gastar cuota.
"""

import config
from nucleo import validador


def generar_problema_validado(nivel, titulos_previos, generar,
                              intentos=config.INTENTOS_GENERACION):
    """generar(nivel, titulos_previos) -> Problema.
    Regresa (problema, correcciones). Lanza ValueError si ningún intento sirve."""
    ultimo_error = None
    for _ in range(intentos):
        problema = generar(nivel, titulos_previos)
        try:
            return validador.validar_problema(problema)
        except ValueError as error:
            ultimo_error = error
    raise ValueError(f"el LLM generó {intentos} problemas cuya solución "
                     f"no funciona ({ultimo_error})")
