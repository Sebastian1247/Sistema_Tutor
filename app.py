"""Punto de entrada:  streamlit run app.py

Sólo acomoda las regiones de la página. La lógica está en el paquete tutor/;
el estado, las acciones y las vistas en tutor/ui/.
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
vistas.generacion()                      # avance o error al generar un problema
vistas.resultado()                       # decisión del sistema difuso, al terminar

p = st.session_state.problema
bloqueado = p is None or st.session_state.terminado     # sin problema o ya terminado

# En pantallas chicas Streamlit apila las columnas
col_problema, col_codigo = st.columns([2, 3], gap="medium")
with col_problema:
    vistas.problema_y_tutor(p, bloqueado)
with col_codigo:
    vistas.editor_y_consola(p, bloqueado)

vistas.historial()
