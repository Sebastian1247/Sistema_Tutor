"""Generación de problemas con Groq + LangChain."""

from functools import lru_cache

from langchain_core.prompts import ChatPromptTemplate

import config
from dominio.modelos import Problema
from llm.cliente import cargar_prompt, crear_modelo, invocar

TEMAS_POR_NIVEL = {
    "novato": "variables, input/print, operadores, if/else y ciclos for/while sencillos",
    "intermedio": "listas, diccionarios, cadenas, funciones y ciclos anidados",
    "avanzado": "recursión, comprensiones de listas, clases, ordenamiento y búsqueda",
}

PROMPT = ChatPromptTemplate.from_messages([
    ("system", cargar_prompt("problema_sistema")),
    ("human", cargar_prompt("problema_usuario")),
])


@lru_cache(maxsize=1)
def _crear_cadena():
    modelo = crear_modelo(config.MODELO_PROBLEMAS,
                          temperatura=0.7,             # variedad sin perder coherencia
                          max_tokens=4096)
    return PROMPT | modelo.with_structured_output(Problema, method="json_schema")


def generar_problema(nivel, titulos_previos=()):
    return invocar(_crear_cadena(), {
        "nivel": nivel,
        "temas": TEMAS_POR_NIVEL[nivel],
        "previos": ", ".join(titulos_previos) or "ninguno",
    })


# Prueba rápida sin Streamlit (1 llamada a Groq):  python -m llm.generador
if __name__ == "__main__":
    print(generar_problema("novato").model_dump_json(indent=2))
