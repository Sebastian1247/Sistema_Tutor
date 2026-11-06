"""Punto de entrada:  streamlit run app.py

Sólo acomoda las regiones de la página. La lógica está en nucleo/, difuso/ y
llm/; el estado y los callbacks en ui/.
"""

import matplotlib
matplotlib.use("Agg")                    # gráficas sin ventanas (Streamlit las dibuja)

import streamlit as st

st.set_page_config(page_title="Tutor de Python", page_icon=":snake:", layout="wide")

from ui import estado
from ui.vistas import barra_lateral, chat, consola, editor, metricas, problema, resultado

estado.iniciar_estado()
barra_lateral.mostrar()

st.title(":snake: Tutor de programación en Python")
metricas.mostrar()

p = st.session_state.problema
bloqueado = p is None or st.session_state.terminado     # sin problema o ya terminado

# --- Fila 1: problema | chatbot ---
col_problema, col_chat = st.columns([3, 2])
with col_problema:
    problema.mostrar(p)
with col_chat:
    chat.mostrar(bloqueado)

# --- Fila 2: editor | ejecución ---
col_editor, col_consola = st.columns([3, 2])
with col_editor:
    editor.mostrar(p, bloqueado)
with col_consola:
    consola.mostrar()

resultado.mostrar()
