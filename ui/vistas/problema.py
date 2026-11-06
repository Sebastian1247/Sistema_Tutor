import streamlit as st

from ui import acciones


def mostrar(p):
    st.button(":game_die: Nuevo problema", on_click=acciones.nuevo_problema)
    if st.session_state.error_llm:
        st.error(st.session_state.error_llm)

    with st.container(border=True, height=400):
        if p is None:
            st.subheader(":notebook_with_decorative_cover: Problema")
            st.info("Elige el nivel en la barra lateral y presiona **Nuevo problema**.")
            return

        st.subheader(f":notebook_with_decorative_cover: {p.titulo}")
        st.caption(f"Nivel: {st.session_state.nivel_problema}")
        st.markdown(p.descripcion)
        st.markdown(f"**Entrada:** {p.formato_entrada}")
        st.markdown(f"**Salida:** {p.formato_salida}")
        e1, e2 = st.columns(2)
        e1.markdown("**Ejemplo de entrada**")
        e1.code(p.ejemplo_entrada or "(ninguna)", language="text")
        e2.markdown("**Ejemplo de salida**")
        e2.code(p.ejemplo_salida, language="text")
        if st.session_state.correcciones:            # transparencia del validador
            with st.expander(f":warning: El validador corrigió {len(st.session_state.correcciones)} "
                             "salida(s) generadas por el LLM"):
                for correccion in st.session_state.correcciones:
                    st.caption(correccion)
