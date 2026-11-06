# Sistema tutor inteligente de programación en Python

Proyecto de la materia **Introducción a la Inteligencia Artificial** (Maestría en Ciencias de la Computación).

El tutor propone problemas de programación en Python y ajusta su dificultad al estudiante:

- Un **sistema de inferencia difusa Mamdani** (scikit-fuzzy) usa el **tiempo**, los **errores** y las **ayudas** del estudiante para decidir el nivel del siguiente problema: novato, intermedio o avanzado.
- Un **LLM** (Groq, vía LangChain) **genera los problemas** de cada nivel y funciona como **tutor** en un chat que da pistas, nunca la solución.

## Funcionalidades

- **Problemas generados por el LLM** con criterios de dificultad por nivel. Antes de mostrar un problema se ejecuta su solución de referencia: si una salida esperada está mal calculada se corrige, y si la solución falla se pide otro problema.
- **Banco local de 15 problemas validados** (5 por nivel). Se usa si no hay internet, si se acaba la cuota gratuita o si el LLM no genera un problema válido. No repite problemas en la sesión.
- **Editor y consola:** compilar (revisar la sintaxis), ejecutar con la entrada del estudiante y entregar contra los casos de prueba. El código del estudiante corre en un proceso aparte, con un límite de 5 s y sin acceso a la clave de la API.
- **Chat con el tutor:** el prompt prohíbe dar la solución. Además, un **filtro** ejecuta el código de cada respuesta contra los casos de prueba: si lo resuelve, la respuesta se bloquea y se reemplaza por una pista.
- **Nivel adaptativo:** al terminar un problema (entregarlo correctamente o rendirse) el sistema difuso calcula el nivel recomendado. El nivel cambia **como máximo un escalón** por problema, y la interfaz explica en lenguaje simple por qué sube o baja.
- **Historial** de la sesión con las entradas y la decisión del sistema difuso.

## El sistema difuso

| Variable | Universo | Términos |
|---|---|---|
| tiempo (entrada) | 0–60 min | corto, medio, largo |
| errores (entrada) | 0–15 | pocos, algunos, muchos |
| ayudas (entrada) | 0–10 | pocas, algunas, muchas |
| nivel (salida) | 0–10 | novato, intermedio, avanzado |

- **27 reglas (3 × 3 × 3).** Cada entrada vale bueno = 2, regular = 1 o malo = 0. Si la suma es 5 o más, el consecuente es avanzado; si es 3 o 4, intermedio; si es 2 o menos, novato.
- **Veto:** si las ayudas son *muchas*, el consecuente es novato, porque el estudiante dependió del tutor.
- **Inferencia Mamdani:** AND = mínimo, implicación = mínimo, agregación = máximo y defuzzificación por **centroide**.
- **Ejemplo:** tiempo = 10, errores = 4, ayudas = 1.5 → 6.74 → avanzado.
- **Rendirse** se evalúa con el peor caso: 60 min y al menos 15 errores.

## Estructura

```
app.py                     punto de entrada de Streamlit (sólo acomoda las regiones)
tutor/                     paquete del proyecto
  config.py                constantes compartidas y modelos de Groq
  modelos.py               Problema, CasoPrueba y Resultado
  ejecutor.py              compilar, ejecutar y evaluar casos de prueba
  validador.py             valida lo que produce el LLM (problemas y respuestas del tutor)
  sesion.py                reglas del flujo: errores, entrega, rendirse, nivel y explicación
  difuso.py                sistema de inferencia difusa Mamdani
  llm.py                   generador de problemas y tutor (único módulo que usa Groq/LangChain)
  prompts.toml             textos de los prompts y criterios de dificultad por nivel
  banco.py                 banco local de problemas
  banco_problemas.json     15 problemas validados
  ui/controlador.py        estado de la sesión y acciones de los botones
  ui/vistas.py             una función por región de la pantalla
tests/                     pruebas con pytest (ninguna llama al LLM)
scripts/probar_fuzzy.py    prueba manual del sistema difuso con gráficas
scripts/evaluar_tutor.py   mide si el tutor revela la solución (llama a Groq)
docs/                      presentación, guiones, evaluación del tutor y figuras
```

Regla de dependencias: Streamlit sólo se usa en `app.py` y `tutor/ui/`, y Groq/LangChain sólo en `tutor/llm.py`.

## Instalación

Requiere Python 3.13.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt   # sólo para correr las pruebas
```

Crea un archivo `.env` en la raíz con tu clave de Groq:

```
GROQ_API_KEY=tu_clave
# Opcionales (valores por defecto):
# MODELO_PROBLEMAS=openai/gpt-oss-120b
# MODELO_CHAT=openai/gpt-oss-20b
```

## Uso

```bash
streamlit run app.py
```

1. Presiona **Generar mi primer problema** (empiezas en novato; puedes cambiarlo en la barra lateral).
2. Escribe tu solución y usa **Compilar**, **Ejecutar** y **Entregar**. Puedes preguntarle al tutor en la pestaña *Tutor*.
3. Al entregar correctamente, o al rendirte, aparece la decisión del sistema difuso y el botón **Siguiente problema**.

## Pruebas

```bash
python -m pytest -p no:cacheprovider
```

Son 129 pruebas. Ninguna llama a Groq: el generador y el tutor se reciben como parámetros y en las pruebas se sustituyen por versiones falsas. Cubren el ejecutor, el validador y la detección de fugas, el sistema difuso (incluido el caso 10, 4, 1.5 → 6.74 avanzado), las reglas del flujo, el banco local y el respaldo de punta a punta en la interfaz.

## Evaluación del tutor

```bash
python -m scripts.evaluar_tutor --limite 6     # empieza con pocos casos
python -m scripts.evaluar_tutor --limite 12
```

El script prueba 12 casos en 6 categorías: petición directa, presión, petición disfrazada, pregunta de concepto, diagnóstico de error y contaminación por historial. Una respuesta cuenta como **fuga** si su código pasa todos los casos de prueba del problema. Con 12 llamadas reales hubo **0 fugas sin filtro y 0 con filtro**. El detalle está en [docs/evaluacion_tutor.md](docs/evaluacion_tutor.md).

**Limitación:** la métrica no detecta fugas parciales, como dar la línea corregida en el texto o un "ejemplo parecido" a un cambio de la solución.

## Límites del plan gratuito de Groq

30 solicitudes por minuto, 1 000 al día y 8 000 tokens por minuto por modelo. Cada problema usa 1 llamada, o 2 si el primero no pasa la validación. Cada pregunta al tutor usa 1, o 2 si el filtro regenera la respuesta. Si se agota la cuota, los problemas salen del banco local.
