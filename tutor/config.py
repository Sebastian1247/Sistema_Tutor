"""Configuración central del sistema tutor.

Un solo lugar para las constantes que comparten varios módulos (antes estaban
repetidas en app.py y fuzzy_nivel.py).
"""

import os

from dotenv import load_dotenv

load_dotenv()   # lee las variables del archivo .env (debe ir ANTES de os.getenv)

NIVELES = ["novato", "intermedio", "avanzado"]

# Universos del sistema difuso. "Me rindo" se evalúa con el peor caso.
TIEMPO_MAXIMO = 60.0             # min
ERRORES_MAXIMOS = 15
AYUDAS_MAXIMAS = 10

INTENTOS_GENERACION = 2          # si la solución del LLM no funciona, se pide otro problema

# Modelos de Groq. Se leen del .env; si no están, se usan estos valores por defecto
MODELO_PROBLEMAS = os.getenv("MODELO_PROBLEMAS", "openai/gpt-oss-120b")
MODELO_CHAT = os.getenv("MODELO_CHAT", "openai/gpt-oss-20b")

MAX_HISTORIAL = 20               # mensajes del chat que se mandan al tutor
TIMEOUT_LLM = 30                 # s por llamada; Groq reintenta 2 veces (429, timeout, 5xx)
