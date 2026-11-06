"""Controlador de la interfaz: estado de la sesión y callbacks de los botones.

Los callbacks se ejecutan antes de redibujar la página. Son adaptadores
delgados: leen st.session_state, llaman a la lógica (sesion, validador, llm)
y guardan el resultado. Las reglas de negocio no viven aquí.
"""

import time

import streamlit as st

from tutor import llm, sesion, validador

CONSOLA_INICIAL = "Aquí aparecerá la salida de la ejecución del código."

MENSAJE_CUOTA_PROBLEMA = ("Se alcanzó el límite del plan gratuito de Groq. "
                          "Espera un minuto e intenta de nuevo; si persiste, "
                          "se agotó la cuota del día.")
MENSAJE_CUOTA_TUTOR = ("Se alcanzó el límite del plan gratuito de Groq. "
                       "Espera un minuto y vuelve a preguntar.")

VALORES_INICIALES = {
    "errores": 0,
    "ayudas": 0,
    "inicio": None,
    "fin": None,                # momento en que terminó el problema
    "codigo": "",
    "entrada": "",
    "consola": CONSOLA_INICIAL,
    "consola_ok": None,
    "nivel": "novato",
    "problema": None,
    "nivel_problema": None,
    "id_problema": 0,
    "titulos_previos": [],
    "error_llm": None,
    "chat": [],
    "correcciones": [],         # salidas del LLM corregidas por el validador
    "resultados_pruebas": None, # resultado de Entregar
    "terminado": False,         # el problema ya se resolvió o se abandonó
    "resultado": None,          # decisión del sistema difuso (modelos.Resultado)
    "historial": [],            # una fila por problema terminado
}


# =====================================================================
# Estado de la sesión
# =====================================================================

def iniciar_estado():
    for clave, valor in VALORES_INICIALES.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor


def _reiniciar_problema(problema, correcciones, nivel):
    """Deja la sesión lista para un problema nuevo (reloj incluido)."""
    estado = st.session_state
    estado.error_llm = None
    estado.problema = problema
    estado.correcciones = correcciones
    estado.nivel_problema = nivel
    estado.titulos_previos.append(problema.titulo)
    estado.id_problema += 1
    estado.codigo = problema.codigo_inicial
    estado.entrada = problema.ejemplo_entrada
    estado.consola = CONSOLA_INICIAL
    estado.consola_ok = None
    estado.errores = 0
    estado.ayudas = 0
    estado.chat = []
    estado.resultados_pruebas = None
    estado.terminado = False
    estado.resultado = None
    estado.fin = None
    estado.inicio = time.time()           # DESPUÉS de generar y validar


def minutos_transcurridos():
    return sesion.minutos_transcurridos(st.session_state.inicio, st.session_state.fin)


# =====================================================================
# Callbacks
# =====================================================================

def nuevo_problema():
    nivel = st.session_state.nivel
    try:
        with st.spinner(f"Generando y validando un problema de nivel {nivel}..."):
            problema, correcciones = validador.generar_problema_validado(
                nivel, st.session_state.titulos_previos, generar=llm.generar_problema)
    except llm.ErrorCuota:
        st.session_state.error_llm = MENSAJE_CUOTA_PROBLEMA
        return
    except Exception as error:
        st.session_state.error_llm = f"No se pudo generar el problema: {error}"
        return
    _reiniciar_problema(problema, correcciones, nivel)


def _mostrar_en_consola(retro):
    st.session_state.consola = retro.mensaje
    st.session_state.consola_ok = retro.ok
    if retro.resultados_pruebas is not None:
        st.session_state.resultados_pruebas = retro.resultados_pruebas
    if retro.cuenta_error:
        st.session_state.errores += 1


def al_compilar():
    _mostrar_en_consola(sesion.procesar_compilacion(st.session_state.codigo))


def al_ejecutar():
    _mostrar_en_consola(sesion.procesar_ejecucion(st.session_state.codigo,
                                                  st.session_state.entrada))


def al_entregar():
    retro = sesion.procesar_entrega(st.session_state.codigo,
                                    st.session_state.problema.casos_prueba)
    _mostrar_en_consola(retro)
    if retro.resuelto:
        _finalizar(resuelto=True)


def al_rendirse():
    _finalizar(resuelto=False)


def _finalizar(resuelto):
    """Aquí entra el sistema difuso."""
    st.session_state.fin = time.time()               # detiene el reloj
    resultado = sesion.evaluar_desempeno(
        resuelto,
        minutos_transcurridos(),
        st.session_state.errores,
        st.session_state.ayudas,
        st.session_state.nivel_problema,
    )
    st.session_state.errores = resultado.errores     # al rendirse sube al máximo
    st.session_state.resultado = resultado
    st.session_state.historial.append(
        resultado.fila_historial(st.session_state.problema.titulo,
                                 st.session_state.nivel_problema))
    st.session_state.nivel = resultado.siguiente     # nivel del próximo problema
    st.session_state.terminado = True


def al_preguntar():
    pregunta = st.session_state.pregunta.strip()
    if not pregunta or st.session_state.problema is None:
        return

    st.session_state.chat.append({"role": "user", "content": pregunta})
    try:
        with st.spinner("El tutor está pensando..."):
            respuesta = llm.pedir_ayuda(
                st.session_state.chat,
                st.session_state.problema,
                st.session_state.nivel_problema,
                st.session_state.codigo,
                st.session_state.consola,
            )
        st.session_state.ayudas += 1
    except llm.ErrorCuota:
        respuesta = MENSAJE_CUOTA_TUTOR
    except Exception as error:
        respuesta = f"No pude responder: {error}"

    st.session_state.chat.append({"role": "assistant", "content": respuesta})
