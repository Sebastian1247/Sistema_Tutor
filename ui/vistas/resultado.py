import matplotlib.pyplot as plt
import streamlit as st

from difuso import graficas, sistema
from ui import acciones


def mostrar():
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
                  on_click=acciones.nuevo_problema)

    with c2:
        figura = graficas.figura_salida(r.tiempo, r.errores, r.ayudas)
        st.pyplot(figura)
        plt.close(figura)

    with st.expander("Ver el detalle de la inferencia"):
        st.markdown("**1. Fuzzificación** (grado de pertenencia de cada entrada)")
        st.dataframe(sistema.tabla_fuzzificacion(r.tiempo, r.errores, r.ayudas),
                     hide_index=True)

        st.markdown("**2. Reglas activadas** (fuerza = mínimo de los antecedentes)")
        st.dataframe(sistema.reglas_activadas(r.tiempo, r.errores, r.ayudas), hide_index=True)

        st.markdown("**3 y 4. Agregación** (máximo de los conjuntos recortados) y "
                    "**defuzzificación** por centroide: ver la gráfica.")
