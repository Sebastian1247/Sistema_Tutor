"""Acceso al LLM (Groq vía LangChain): generador de problemas y tutor.

Es el único módulo que usa ``groq`` y LangChain; el resto del sistema sólo
conoce ``generar_problema``, ``pedir_ayuda`` y las excepciones definidas aquí,
de modo que cambiar de proveedor afecta sólo a este archivo. Los textos de los
prompts están en ``prompts.toml``.

Manejo de errores:
    * Límite de solicitudes (429), timeouts y errores 5xx: el cliente de Groq
      reintenta ``max_retries`` veces; si sigue fallando se lanza
      ``ErrorCuota`` o ``ErrorLLM``.
    * JSON que no cumple el esquema: ``RespuestaInvalida``, que también es
      ``ValueError`` para que ``validador.generar_problema_validado`` lo cuente
      como un intento fallido y pida otro problema.
"""

import tomllib
from functools import lru_cache
from pathlib import Path

import groq
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq

from tutor import config
from tutor.modelos import Problema

with open(Path(__file__).parent / "prompts.toml", "rb") as archivo:
    PROMPTS = tomllib.load(archivo)


def _texto(seccion, clave):
    """Regresa un texto de ``prompts.toml`` sin el salto de línea final."""
    return PROMPTS[seccion][clave].rstrip("\n")


class ErrorLLM(Exception):
    """El LLM no pudo responder (sin conexión, error del servicio, etc.)."""


class ErrorCuota(ErrorLLM):
    """Se alcanzó el límite del plan gratuito de Groq (HTTP 429)."""


class RespuestaInvalida(ErrorLLM, ValueError):
    """El LLM respondió, pero no con un problema que cumpla el esquema JSON."""


def _crear_modelo(modelo, temperatura, max_tokens):
    """Crea el cliente de chat de Groq con la configuración común.

    Args:
        modelo: Nombre del modelo en Groq.
        temperatura: Aleatoriedad de las respuestas (0 = determinista).
        max_tokens: Tope de tokens de la respuesta, incluido el razonamiento.

    Returns:
        ``ChatGroq`` listo para usarse en una cadena de LangChain.
    """
    return ChatGroq(
        model=modelo,
        temperature=temperatura,
        max_retries=2,  # reintenta 429, timeouts y 5xx
        timeout=config.TIMEOUT_LLM,
        max_tokens=max_tokens,
        reasoning_effort="low",  # razonar poco gasta menos tokens del plan gratuito
    )


def _invocar(cadena, datos):
    """Ejecuta una cadena de LangChain y traduce los errores del proveedor.

    Args:
        cadena: Cadena de LangChain (prompt | modelo | parser).
        datos: Variables del prompt.

    Returns:
        La salida de la cadena (``Problema`` o texto).

    Raises:
        ErrorCuota: Si se alcanzó el límite del plan gratuito.
        RespuestaInvalida: Si la respuesta no cumple el esquema JSON.
        ErrorLLM: Ante cualquier otro error (red, timeout, servicio).
    """
    try:
        return cadena.invoke(datos)
    except groq.RateLimitError as error:
        raise ErrorCuota(str(error)) from error
    except OutputParserException as error:
        raise RespuestaInvalida(str(error)) from error
    except groq.BadRequestError as error:
        if "json_validate_failed" in str(error):  # Groq rechazó el JSON del modelo
            raise RespuestaInvalida(str(error)) from error
        raise ErrorLLM(str(error)) from error
    except Exception as error:
        raise ErrorLLM(str(error)) from error


# --- Generador de problemas ---

PROMPT_PROBLEMA = ChatPromptTemplate.from_messages([
    ("system", _texto("problema", "sistema")),
    ("human", _texto("problema", "usuario")),
])


@lru_cache(maxsize=1)
def _cadena_problema():
    """Crea (una sola vez) la cadena prompt -> modelo con salida estructurada ``Problema``."""
    modelo = _crear_modelo(config.MODELO_PROBLEMAS,
                           temperatura=0.7,  # variedad sin perder coherencia
                           max_tokens=4096)
    return PROMPT_PROBLEMA | modelo.with_structured_output(Problema, method="json_schema")


def datos_prompt_problema(nivel, titulos_previos=()):
    """Arma las variables del prompt de generación.

    Args:
        nivel: Nivel del problema.
        titulos_previos: Títulos ya vistos, para pedir que no se repitan.

    Returns:
        Diccionario con el nivel, sus criterios de dificultad y los títulos previos.
    """
    return {"nivel": nivel, **PROMPTS["problema"]["criterios"][nivel],
            "previos": ", ".join(titulos_previos) or "ninguno"}


def generar_problema(nivel, titulos_previos=()):
    """Pide al LLM un problema nuevo del nivel indicado.

    Args:
        nivel: ``"novato"``, ``"intermedio"`` o ``"avanzado"``.
        titulos_previos: Títulos ya vistos en la sesión.

    Returns:
        ``Problema`` sin validar (lo valida ``validador.validar_problema``).

    Raises:
        ErrorCuota, RespuestaInvalida, ErrorLLM: Ver ``_invocar``.
    """
    return _invocar(_cadena_problema(), datos_prompt_problema(nivel, titulos_previos))


# --- Tutor ---

PROMPT_TUTOR = ChatPromptTemplate.from_messages([
    ("system", _texto("tutor", "sistema")),
    MessagesPlaceholder("historial"),
])


@lru_cache(maxsize=1)
def _cadena_tutor():
    """Crea (una sola vez) la cadena prompt -> modelo -> texto del tutor."""
    modelo = _crear_modelo(config.MODELO_CHAT,
                           temperatura=0.3,  # explicaciones consistentes
                           max_tokens=1024)  # respuestas cortas
    return PROMPT_TUTOR | modelo | StrOutputParser()


def pedir_ayuda(historial, problema, nivel, codigo, consola):
    """Pide al tutor una respuesta para la conversación actual.

    Args:
        historial: Mensajes ``{"role": "user" | "assistant", "content": texto}``,
            terminando con la pregunta del estudiante.
        problema: ``Problema`` que está resolviendo el estudiante.
        nivel: Nivel del problema.
        codigo: Código actual del estudiante.
        consola: Última salida de la consola.

    Returns:
        Texto de la respuesta en Markdown.

    Raises:
        ErrorCuota, RespuestaInvalida, ErrorLLM: Ver ``_invocar``.
    """
    texto_problema = (f"{problema.titulo}\n{problema.descripcion}\n"
                      f"Entrada: {problema.formato_entrada}\n"
                      f"Salida: {problema.formato_salida}")
    return _invocar(_cadena_tutor(), {
        "nivel": nivel,
        "problema": texto_problema,
        "codigo": codigo or "(vacío)",
        "consola": consola,
        # Sólo los últimos mensajes y sólo rol y contenido.
        "historial": [{"role": m["role"], "content": m["content"]}
                      for m in historial[-config.MAX_HISTORIAL:]],
    })


if __name__ == "__main__":
    # Prueba rápida sin Streamlit (1 llamada a Groq): python -m tutor.llm
    print(generar_problema("novato").model_dump_json(indent=2))
