"""Chatbot tutor: da pistas sin revelar la solución."""

from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

import config
from llm.cliente import cargar_prompt, crear_modelo, invocar

PROMPT_TUTOR = ChatPromptTemplate.from_messages([
    ("system", cargar_prompt("tutor_sistema")),
    MessagesPlaceholder("historial"),
])


@lru_cache(maxsize=1)
def _crear_cadena_tutor():
    modelo = crear_modelo(config.MODELO_CHAT,
                          temperatura=0.3,             # explicaciones consistentes
                          max_tokens=1024)             # respuestas cortas
    return PROMPT_TUTOR | modelo | StrOutputParser()


def pedir_ayuda(historial, problema, nivel, codigo, consola):
    """historial: lista de {'role': 'user'|'assistant', 'content': texto}."""
    texto_problema = (f"{problema.titulo}\n{problema.descripcion}\n"
                      f"Entrada: {problema.formato_entrada}\n"
                      f"Salida: {problema.formato_salida}")
    return invocar(_crear_cadena_tutor(), {
        "nivel": nivel,
        "problema": texto_problema,
        "codigo": codigo or "(vacío)",
        "consola": consola,
        "historial": historial[-config.MAX_HISTORIAL:],   # sólo los últimos mensajes
    })
