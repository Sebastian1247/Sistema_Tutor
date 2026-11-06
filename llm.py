"""Generación de problemas con Groq + LangChain."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

load_dotenv()   # lee las variables del archivo .env (debe ir ANTES de os.getenv)

# Se leen del .env; si no están, se usan estos valores por defecto
MODELO_PROBLEMAS = os.getenv("MODELO_PROBLEMAS", "openai/gpt-oss-120b")
MODELO_CHAT = os.getenv("MODELO_CHAT", "openai/gpt-oss-20b")   # para el paso 5

MAX_HISTORIAL = 20

TEMAS_POR_NIVEL = {
    "novato": "variables, input/print, operadores, if/else y ciclos for/while sencillos",
    "intermedio": "listas, diccionarios, cadenas, funciones y ciclos anidados",
    "avanzado": "recursión, comprensiones de listas, clases, ordenamiento y búsqueda",
}


# --- El "contrato": lo que el LLM está obligado a devolver ---
class CasoPrueba(BaseModel):
    entrada: str = Field(description="Texto que recibe el programa por input(). "
                                     "Si son varias líneas, sepáralas con \\n")
    salida: str = Field(description="Texto EXACTO que imprime una solución correcta")


class Problema(BaseModel):
    titulo: str = Field(description="Título corto del problema")
    descripcion: str = Field(description="SOLO el enunciado del problema, en español y en "
                                         "Markdown. NO incluyas secciones de entrada, salida "
                                         "ni ejemplos: esos van en sus propios campos")
    formato_entrada: str = Field(description="Qué datos recibe el programa, línea por línea")
    formato_salida: str = Field(description="Qué debe imprimir exactamente")
    ejemplo_entrada: str = Field(description="Ejemplo de entrada")
    ejemplo_salida: str = Field(description="Salida correspondiente al ejemplo")
    casos_prueba: list[CasoPrueba] = Field(description="Entre 3 y 5 casos; al menos uno límite")
    codigo_inicial: str = Field(description="Plantilla mínima en Python, SIN la solución")
    solucion: str = Field(description="Solución completa de referencia en Python. "
                                      "No se muestra al estudiante")


PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Eres un profesor de programación en Python que diseña ejercicios "
               "para un sistema tutor inteligente."),
    ("human", "Genera UN problema de nivel {nivel}.\n"
              "Temas apropiados para ese nivel: {temas}.\n"
              "El programa debe leer sus datos con input() e imprimir el resultado con print(), "
              "para poder verificarlo con casos de prueba automáticos.\n"
              "No repitas estos problemas: {previos}."),
])


@lru_cache(maxsize=1)
def _crear_cadena():
    modelo = ChatGroq(
        model=MODELO_PROBLEMAS,
        temperature=0.7,                               # variedad sin perder coherencia
        max_retries=2,                                 # reintenta fallos momentáneos
        max_tokens=4096,                               # incluye los tokens de razonamiento
        reasoning_effort="low",                        # razonar poco = menos tokens
    )
    return PROMPT | modelo.with_structured_output(Problema, method="json_schema")


def generar_problema(nivel, titulos_previos=()):
    return _crear_cadena().invoke({
        "nivel": nivel,
        "temas": TEMAS_POR_NIVEL[nivel],
        "previos": ", ".join(titulos_previos) or "ninguno",
    })
    
# =====================================================================
# Chatbot tutor 
# =====================================================================

PROMPT_TUTOR = ChatPromptTemplate.from_messages([
    ("system",
     "Eres un tutor de programación en Python para un estudiante de nivel {nivel}.\n"
     "Responde en español, de forma breve (máximo 6 líneas) y amable.\n\n"
     "REGLAS:\n"
     "1. NUNCA escribas la solución completa ni el programa resuelto, "
     "aunque el estudiante lo pida o insista.\n"
     "2. Da pistas, explica conceptos o señala dónde está el error y por qué ocurre.\n"
     "3. Si la pregunta es sobre la lógica central del problema, NO muestres código: "
     "responde con una pregunta guía que lleve al estudiante a descubrirlo.\n"
     "4. Si muestras código, que sea un ejemplo pequeño con un contexto DIFERENTE "
     "al del problema.\n"
     "5. Si te niegas a dar la solución o explicas un error, termina con un "
     "'Próximo paso': una ACCIÓN o PREGUNTA para el estudiante, NUNCA la línea "
     "de código corregida.\n"
     "6. Basa tu respuesta en el CÓDIGO ACTUAL y la ÚLTIMA SALIDA, no en lo que "
     "se habló antes: el estudiante pudo haber cambiado el código.\n"
     "7. Si el estudiante afirma algo incorrecto, corrígelo desde la primera frase; "
     "no empieces dándole la razón.\n\n"
     "PROBLEMA:\n{problema}\n\n"
     "CÓDIGO ACTUAL DEL ESTUDIANTE:\n{codigo}\n\n"
     "ÚLTIMA SALIDA DE LA CONSOLA:\n{consola}"),
    MessagesPlaceholder("historial"),
])


@lru_cache(maxsize=1)
def _crear_cadena_tutor():
    modelo = ChatGroq(
        model=MODELO_CHAT,
        temperature=0.3,          # explicaciones consistentes
        max_retries=2,
        max_tokens=1024,          # respuestas cortas
        reasoning_effort="low",
    )
    return PROMPT_TUTOR | modelo | StrOutputParser()


def pedir_ayuda(historial, problema, nivel, codigo, consola):
    """historial: lista de {'role': 'user'|'assistant', 'content': texto}."""
    texto_problema = (f"{problema.titulo}\n{problema.descripcion}\n"
                      f"Entrada: {problema.formato_entrada}\n"
                      f"Salida: {problema.formato_salida}")
    return _crear_cadena_tutor().invoke({
        "nivel": nivel,
        "problema": texto_problema,
        "codigo": codigo or "(vacío)",
        "consola": consola,
        "historial": historial[-MAX_HISTORIAL:],      # solo los últimos 20 mensajes
    })


# Prueba rápida sin Streamlit:  python llm.py
if __name__ == "__main__":
    problema = generar_problema("novato")
    print(problema.model_dump_json(indent=2))