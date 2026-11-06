"""Callbacks de los botones (se ejecutan antes de redibujar la página).

Son adaptadores delgados: leen st.session_state, llaman a la lógica de nucleo/
o llm/ y guardan el resultado. Las reglas de negocio no viven aquí.
"""

import time

import streamlit as st

from llm import generador, tutor
from llm.cliente import ErrorCuota
from nucleo import generacion, sesion
from ui import estado

MENSAJE_CUOTA_PROBLEMA = ("Se alcanzó el límite del plan gratuito de Groq. "
                          "Espera un minuto e intenta de nuevo; si persiste, "
                          "se agotó la cuota del día.")
MENSAJE_CUOTA_TUTOR = ("Se alcanzó el límite del plan gratuito de Groq. "
                       "Espera un minuto y vuelve a preguntar.")


def nuevo_problema():
    nivel = st.session_state.nivel
    try:
        with st.spinner(f"Generando y validando un problema de nivel {nivel}..."):
            problema, correcciones = generacion.generar_problema_validado(
                nivel, st.session_state.titulos_previos, generar=generador.generar_problema)
    except ErrorCuota:
        st.session_state.error_llm = MENSAJE_CUOTA_PROBLEMA
        return
    except Exception as error:
        st.session_state.error_llm = f"No se pudo generar el problema: {error}"
        return
    estado.reiniciar_problema(problema, correcciones, nivel)


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
        estado.minutos_transcurridos(),
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
            respuesta = tutor.pedir_ayuda(
                st.session_state.chat,
                st.session_state.problema,
                st.session_state.nivel_problema,
                st.session_state.codigo,
                st.session_state.consola,
            )
        st.session_state.ayudas += 1
    except ErrorCuota:
        respuesta = MENSAJE_CUOTA_TUTOR
    except Exception as error:
        respuesta = f"No pude responder: {error}"

    st.session_state.chat.append({"role": "assistant", "content": respuesta})
