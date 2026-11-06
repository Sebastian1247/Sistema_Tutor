import streamlit as st

from ui import acciones


def mostrar(bloqueado):
    with st.container(border=True, height=400):
        st.subheader(":robot: Tutor")

        with st.container(height=230):
            if not st.session_state.chat:
                st.caption("Pregunta lo que necesites. Cada pregunta cuenta como una ayuda.")
            for mensaje in st.session_state.chat:
                with st.chat_message(mensaje["role"]):
                    st.markdown(mensaje["content"])

        with st.form("form_chat", clear_on_submit=True, border=False):
            c1, c2 = st.columns([4, 1])
            c1.text_input("Pregunta", key="pregunta", label_visibility="collapsed",
                          placeholder="¿Por qué me sale TypeError?")
            c2.form_submit_button("Enviar", on_click=acciones.al_preguntar, disabled=bloqueado)
