import streamlit as st

import config


def mostrar():
    with st.sidebar:
        st.header(":gear: Configuración")
        st.selectbox("Nivel del siguiente problema", config.NIVELES, key="nivel",
                     help="Al terminar cada problema, el sistema difuso lo actualiza.")
        st.caption(f"Modelo de problemas: {config.MODELO_PROBLEMAS}")
        st.caption(f"Modelo del tutor: {config.MODELO_CHAT}")

        if st.session_state.historial:
            st.divider()
            st.subheader("Historial")
            st.dataframe(st.session_state.historial, hide_index=True)
