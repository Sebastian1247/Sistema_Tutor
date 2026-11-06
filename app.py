"""Punto de entrada:  streamlit run app.py

Sólo acomoda las regiones de la página. La lógica está en el paquete tutor/;
el estado, los callbacks y las vistas en tutor/ui/.
"""

import matplotlib
matplotlib.use("Agg")                    # gráficas sin ventanas (Streamlit las dibuja)

import streamlit as st

st.set_page_config(page_title="Tutor de Python", page_icon=":snake:", layout="wide")

from tutor.ui import controlador, vistas

controlador.iniciar_estado()
vistas.barra_lateral()

st.title(":snake: Tutor de programación en Python")
vistas.metricas()

p = st.session_state.problema
bloqueado = p is None or st.session_state.terminado     # sin problema o ya terminado

# --- Fila 1: problema | chatbot ---
col_problema, col_chat = st.columns([3, 2])
with col_problema:
    vistas.problema(p)
with col_chat:
    vistas.chat(bloqueado)

# --- Fila 2: editor | ejecución ---
col_editor, col_consola = st.columns([3, 2])
with col_editor:
    vistas.editor(p, bloqueado)
with col_consola:
    vistas.consola()

vistas.resultado()
