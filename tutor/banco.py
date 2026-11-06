"""Banco local de problemas, respaldo cuando el LLM no está disponible.

``problema_del_banco`` tiene la misma firma que ``llm.generar_problema``, así
que ``validador.generar_problema_validado`` lo usa igual: es otro generador.
Los problemas siguen los criterios de dificultad de ``prompts.toml``.
"""

import json
import random
from functools import lru_cache
from pathlib import Path

from tutor.modelos import Problema

RUTA_BANCO = Path(__file__).parent / "banco_problemas.json"


@lru_cache(maxsize=1)
def cargar_banco():
    """Lee el banco (una sola vez por proceso).

    Returns:
        Diccionario ``{nivel: [Problema, ...]}``.
    """
    datos = json.loads(RUTA_BANCO.read_text(encoding="utf-8"))
    return {nivel: [Problema(**p) for p in problemas] for nivel, problemas in datos.items()}


def problema_del_banco(nivel, titulos_previos=()):
    """Elige al azar un problema del nivel que no se haya visto en la sesión.

    Args:
        nivel: Nivel del problema.
        titulos_previos: Títulos ya vistos. Si ya se vieron todos los del nivel,
            se repite uno.

    Returns:
        Una copia del problema, porque el validador la modifica.
    """
    problemas = cargar_banco()[nivel]
    nuevos = [p for p in problemas if p.titulo not in titulos_previos]
    return random.choice(nuevos or problemas).model_copy(deep=True)
