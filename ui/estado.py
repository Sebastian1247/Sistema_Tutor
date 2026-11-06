"""Estado de la sesión de Streamlit: qué claves existen y cómo se reinician."""

import time

import streamlit as st

from nucleo import sesion

CONSOLA_INICIAL = "Aquí aparecerá la salida de la ejecución del código."

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
    "resultado": None,          # decisión del sistema difuso (dominio.modelos.Resultado)
    "historial": [],            # una fila por problema terminado
}


def iniciar_estado():
    for clave, valor in VALORES_INICIALES.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor


def reiniciar_problema(problema, correcciones, nivel):
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
