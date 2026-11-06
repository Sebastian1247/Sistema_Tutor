import streamlit as st

from ui import estado


@st.fragment(run_every=1)
def mostrar():
    m1, m2, m3 = st.columns(3)
    m1.metric(":hourglass_flowing_sand: Tiempo transcurrido",
              f"{estado.minutos_transcurridos():.2f} min")
    m2.metric(":x: Errores", st.session_state.errores)
    m3.metric(":bulb: Ayudas solicitadas", st.session_state.ayudas)
