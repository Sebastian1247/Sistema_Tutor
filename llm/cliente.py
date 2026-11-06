"""Acceso a Groq: crea los modelos, carga los prompts y traduce sus errores.

Es el único módulo que conoce el SDK de groq. El resto del sistema sólo ve
ErrorCuota y ErrorLLM, así que cambiar de proveedor afecta a este archivo.
"""

from pathlib import Path

import groq
from langchain_groq import ChatGroq

CARPETA_PROMPTS = Path(__file__).parent / "prompts"


class ErrorLLM(Exception):
    """El LLM no pudo responder (red, respuesta inválida, etc.)."""


class ErrorCuota(ErrorLLM):
    """Se alcanzó el límite del plan gratuito de Groq (HTTP 429)."""


def cargar_prompt(nombre):
    """Lee llm/prompts/<nombre>.txt. El texto del prompt es contenido, no código."""
    return (CARPETA_PROMPTS / f"{nombre}.txt").read_text(encoding="utf-8").rstrip("\n")


def crear_modelo(modelo, temperatura, max_tokens):
    return ChatGroq(
        model=modelo,
        temperature=temperatura,
        max_retries=2,                                 # reintenta fallos momentáneos
        max_tokens=max_tokens,                         # incluye los tokens de razonamiento
        reasoning_effort="low",                        # razonar poco = menos tokens
    )


def invocar(cadena, datos):
    """Ejecuta una cadena de LangChain traduciendo los errores del proveedor."""
    try:
        return cadena.invoke(datos)
    except groq.RateLimitError as error:
        raise ErrorCuota(str(error)) from error
    except Exception as error:
        raise ErrorLLM(str(error)) from error
