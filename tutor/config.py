"""Configuración central del sistema tutor.

Reúne las constantes que comparten varios módulos para que cada valor se
defina en un solo lugar. Los modelos de Groq se pueden cambiar desde el
archivo ``.env`` sin tocar el código.
"""

import os

from dotenv import load_dotenv

# Debe ejecutarse antes de os.getenv para que las variables del .env existan.
load_dotenv()

NIVELES = ["novato", "intermedio", "avanzado"]

# Universos de las entradas del sistema difuso. "Me rindo" se evalúa con el
# peor caso: TIEMPO_MAXIMO y al menos ERRORES_MAXIMOS.
TIEMPO_MAXIMO = 60.0  # minutos
ERRORES_MAXIMOS = 15
AYUDAS_MAXIMAS = 10

# Problemas que se piden al LLM antes de rendirse cuando la solución no sirve.
INTENTOS_GENERACION = 2

# Modelos de Groq; se usan estos valores si no están definidos en el .env.
MODELO_PROBLEMAS = os.getenv("MODELO_PROBLEMAS", "openai/gpt-oss-120b")
MODELO_CHAT = os.getenv("MODELO_CHAT", "openai/gpt-oss-20b")

MAX_HISTORIAL = 20  # mensajes del chat que se envían al tutor
TIMEOUT_LLM = 30  # segundos por llamada; Groq reintenta 429, timeouts y 5xx
