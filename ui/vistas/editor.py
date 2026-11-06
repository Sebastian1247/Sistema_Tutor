import streamlit as st
from streamlit_ace import st_ace

from ui import acciones


def mostrar(p, bloqueado):
    st.subheader(":memo: Editor de código")
    codigo = st_ace(
        value=p.codigo_inicial if p else "# Escribe tu solución aquí\n",
        language="python",
        theme="monokai",
        height=300,
        tab_size=4,
        auto_update=True,
        readonly=st.session_state.terminado,         # no se edita al terminar
        key=f"editor_{st.session_state.id_problema}",
    )
    if codigo is not None:
        st.session_state.codigo = codigo

    b1, b2, b3, b4 = st.columns(4)
    b1.button(":gear: Compilar", on_click=acciones.al_compilar, disabled=bloqueado)
    b2.button(":arrow_forward: Ejecutar", on_click=acciones.al_ejecutar, disabled=bloqueado)
    b3.button(":white_check_mark: Entregar", on_click=acciones.al_entregar, disabled=bloqueado,
              type="primary", help="Corre los casos de prueba. Si pasas todos, el problema "
                                   "se da por resuelto.")
    b4.button(":white_flag: Me rindo", on_click=acciones.al_rendirse, disabled=bloqueado)
