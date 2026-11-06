"""Todo lo que habla con Groq: generador de problemas y chatbot tutor.

Es el único módulo que conoce groq y LangChain. El resto del sistema sólo ve
generar_problema, pedir_ayuda, ErrorCuota y ErrorLLM, así que cambiar de
proveedor afecta a este archivo. Los textos de los prompts están en prompts.toml.
"""

import tomllib
from functools import lru_cache
from pathlib import Path

import groq
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq

from tutor import config
from tutor.modelos import Problema

with open(Path(__file__).parent / "prompts.toml", "rb") as archivo:
    PROMPTS = tomllib.load(archivo)


def _texto(seccion, clave):
    return PROMPTS[seccion][clave].rstrip("\n")


class ErrorLLM(Exception):
    """El LLM no pudo responder (red, respuesta inválida, etc.)."""


class ErrorCuota(ErrorLLM):
    """Se alcanzó el límite del plan gratuito de Groq (HTTP 429)."""


def _crear_modelo(modelo, temperatura, max_tokens):
    return ChatGroq(
        model=modelo,
        temperature=temperatura,
        max_retries=2,                                 # reintenta fallos momentáneos
        max_tokens=max_tokens,                         # incluye los tokens de razonamiento
        reasoning_effort="low",                        # razonar poco = menos tokens
    )


def _invocar(cadena, datos):
    """Ejecuta una cadena de LangChain traduciendo los errores del proveedor."""
    try:
        return cadena.invoke(datos)
    except groq.RateLimitError as error:
        raise ErrorCuota(str(error)) from error
    except Exception as error:
        raise ErrorLLM(str(error)) from error


# =====================================================================
# Generador de problemas
# =====================================================================

PROMPT_PROBLEMA = ChatPromptTemplate.from_messages([
    ("system", _texto("problema", "sistema")),
    ("human", _texto("problema", "usuario")),
])


@lru_cache(maxsize=1)
def _cadena_problema():
    modelo = _crear_modelo(config.MODELO_PROBLEMAS,
                           temperatura=0.7,            # variedad sin perder coherencia
                           max_tokens=4096)
    return PROMPT_PROBLEMA | modelo.with_structured_output(Problema, method="json_schema")


def generar_problema(nivel, titulos_previos=()):
    return _invocar(_cadena_problema(), {
        "nivel": nivel,
        "temas": PROMPTS["problema"]["temas"][nivel],
        "previos": ", ".join(titulos_previos) or "ninguno",
    })


# =====================================================================
# Chatbot tutor
# =====================================================================

PROMPT_TUTOR = ChatPromptTemplate.from_messages([
    ("system", _texto("tutor", "sistema")),
    MessagesPlaceholder("historial"),
])


@lru_cache(maxsize=1)
def _cadena_tutor():
    modelo = _crear_modelo(config.MODELO_CHAT,
                           temperatura=0.3,            # explicaciones consistentes
                           max_tokens=1024)            # respuestas cortas
    return PROMPT_TUTOR | modelo | StrOutputParser()


def pedir_ayuda(historial, problema, nivel, codigo, consola):
    """historial: lista de {'role': 'user'|'assistant', 'content': texto}."""
    texto_problema = (f"{problema.titulo}\n{problema.descripcion}\n"
                      f"Entrada: {problema.formato_entrada}\n"
                      f"Salida: {problema.formato_salida}")
    return _invocar(_cadena_tutor(), {
        "nivel": nivel,
        "problema": texto_problema,
        "codigo": codigo or "(vacío)",
        "consola": consola,
        "historial": historial[-config.MAX_HISTORIAL:],   # sólo los últimos mensajes
    })


# Prueba rápida sin Streamlit (1 llamada a Groq):  python -m tutor.llm
if __name__ == "__main__":
    print(generar_problema("novato").model_dump_json(indent=2))
