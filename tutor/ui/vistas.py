"""Vistas: una función por región de la pantalla. Sólo dibujan; las acciones
de los botones están en controlador.py."""

import matplotlib.pyplot as plt
import streamlit as st
from streamlit_ace import st_ace

from tutor import config, difuso
from tutor.ui import controlador


def barra_lateral():
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


@st.fragment(run_every=1)
def metricas():
    m1, m2, m3 = st.columns(3)
    m1.metric(":hourglass_flowing_sand: Tiempo transcurrido",
              f"{controlador.minutos_transcurridos():.2f} min")
    m2.metric(":x: Errores", st.session_state.errores)
    m3.metric(":bulb: Ayudas solicitadas", st.session_state.ayudas)


def problema(p):
    st.button(":game_die: Nuevo problema", on_click=controlador.nuevo_problema)
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


def chat(bloqueado):
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
            c2.form_submit_button("Enviar", on_click=controlador.al_preguntar,
                                  disabled=bloqueado)


def editor(p, bloqueado):
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
    b1.button(":gear: Compilar", on_click=controlador.al_compilar, disabled=bloqueado)
    b2.button(":arrow_forward: Ejecutar", on_click=controlador.al_ejecutar, disabled=bloqueado)
    b3.button(":white_check_mark: Entregar", on_click=controlador.al_entregar, disabled=bloqueado,
              type="primary", help="Corre los casos de prueba. Si pasas todos, el problema "
                                   "se da por resuelto.")
    b4.button(":white_flag: Me rindo", on_click=controlador.al_rendirse, disabled=bloqueado)


def consola():
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


def resultado():
    """Decisión del sistema difuso al terminar el problema."""
    r = st.session_state.resultado
    if not (st.session_state.terminado and r):
        return

    st.divider()
    if r.resuelto:
        st.success(f":tada: ¡Problema resuelto en {r.tiempo:.1f} min!")
    else:
        st.warning(":white_flag: Te rendiste. Se evaluó con el tiempo y los errores máximos.")

    c1, c2 = st.columns([2, 3])
    with c1:
        st.subheader(":brain: Decisión del sistema difuso")
        st.markdown(f"**Entradas:** tiempo = {r.tiempo:.1f} min · "
                    f"errores = {r.errores} · ayudas = {r.ayudas}")
        st.markdown(f"**Salida (centroide):** {r.valor:.2f} / 10")
        st.markdown(f"**Nivel recomendado:** {r.recomendado}")
        st.markdown(f"**Nivel del siguiente problema:** {r.siguiente}")
        if r.siguiente != r.recomendado:
            st.caption("El nivel cambia como máximo un escalón por problema.")
        st.button(":arrow_right: Siguiente problema", type="primary",
                  on_click=controlador.nuevo_problema)

    with c2:
        figura = difuso.figura_salida(r.tiempo, r.errores, r.ayudas)
        st.pyplot(figura)
        plt.close(figura)

    with st.expander("Ver el detalle de la inferencia"):
        st.markdown("**1. Fuzzificación** (grado de pertenencia de cada entrada)")
        st.dataframe(difuso.tabla_fuzzificacion(r.tiempo, r.errores, r.ayudas),
                     hide_index=True)

        st.markdown("**2. Reglas activadas** (fuerza = mínimo de los antecedentes)")
        st.dataframe(difuso.reglas_activadas(r.tiempo, r.errores, r.ayudas), hide_index=True)

        st.markdown("**3 y 4. Agregación** (máximo de los conjuntos recortados) y "
                    "**defuzzificación** por centroide: ver la gráfica.")
