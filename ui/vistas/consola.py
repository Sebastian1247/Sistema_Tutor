import streamlit as st


def mostrar():
    st.subheader(":computer: Consola de ejecución")
    st.text_area("Entrada para el programa (lo que leerá input())", key="entrada", height=80)
    if st.session_state.consola_ok is True:
        st.success("Sin errores")
    elif st.session_state.consola_ok is False:
        st.error("Hubo un error")
    st.code(st.session_state.consola, language="text")

    if st.session_state.resultados_pruebas:          # detalle de cada caso
        for i, r in enumerate(st.session_state.resultados_pruebas, start=1):
            with st.expander(f"{':white_check_mark:' if r['paso'] else ':x:'} Caso {i}",
                             expanded=not r["paso"]):
                st.caption("Entrada")
                st.code(r["entrada"] or "(vacía)", language="text")
                st.caption("Salida esperada")
                st.code(r["esperada"], language="text")
                st.caption("Tu salida")
                st.code(r["obtenida"], language="text")
