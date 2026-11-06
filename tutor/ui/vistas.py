"""Vistas de la interfaz: una función por región de la pantalla.

Las vistas sólo dibujan. Las acciones de los botones están en
``tutor.ui.controlador`` y las reglas del tutor en ``tutor.sesion``.
"""

import matplotlib.pyplot as plt
import streamlit as st
from streamlit_ace import st_ace

from tutor import config, difuso, sesion
from tutor.ui import controlador

COLORES_NIVEL = {"novato": "green", "intermedio": "orange", "avanzado": "violet"}

# Título de la consola según (etapa, ok) de la última Retroalimentacion.
TITULOS_CONSOLA = {
    ("compilacion", True): "Compilar: no hay errores de sintaxis.",
    ("compilacion", False): "Error de sintaxis: el código no se ejecutó.",
    ("ejecucion", True): "Ejecutar: el programa terminó sin errores.",
    ("ejecucion", False): "Ejecutar: el programa terminó con un error.",
    ("entrega", True): "Entregar: pasaste todos los casos de prueba.",
    ("entrega", False): "Entregar: no pasaste todos los casos de prueba.",
}

COMO_FUNCIONA = f"""
1. Lee el problema y escribe tu solución en el editor.
2. **Compilar** revisa la sintaxis, **Ejecutar** corre tu programa con la entrada que
   escribas y **Entregar** lo prueba con los casos de prueba.
3. Se miden tu **tiempo**, tus **errores** (cada compilación o ejecución con error y cada
   entrega incorrecta) y tus **ayudas** (cada pregunta que el tutor responde).
4. Al terminar, un sistema de lógica difusa (inferencia Mamdani) combina esas tres medidas
   y decide tu siguiente nivel. Sube o baja como máximo un nivel por problema.
5. **Me rindo** termina el problema y se evalúa con el peor caso
   ({config.TIEMPO_MAXIMO:.0f} min y {config.ERRORES_MAXIMOS} errores).

Las pistas que aparecen bajo un error de Python no cuentan como ayuda.
"""


def _badge_nivel(nivel):
    """Dibuja el nivel como una insignia de color."""
    st.badge(nivel.capitalize(), color=COLORES_NIVEL[nivel])


# --- Barra lateral y encabezado ---

def barra_lateral():
    """Dibuja la barra lateral: nivel, ayuda, historial resumido y créditos."""
    with st.sidebar:
        st.subheader("Tu nivel")
        _badge_nivel(st.session_state.nivel)
        st.caption("Nivel de tu siguiente problema. Lo ajusta el sistema difuso cada vez "
                   "que terminas uno.")
        sugerido = st.session_state.nivel_sugerido
        if sugerido and sugerido != st.session_state.nivel:
            st.caption(f":warning: Lo elegiste manualmente; el sistema sugería **{sugerido}**.")
        with st.expander("Cambiar nivel manualmente"):
            st.selectbox("Nivel del siguiente problema", config.NIVELES, key="nivel")

        with st.expander(":question: ¿Cómo funciona?"):
            st.markdown(COMO_FUNCIONA)

        if st.session_state.historial:
            st.subheader("Historial")
            st.dataframe([{"#": i, "nivel": f["nivel"], "resuelto": f["resuelto"],
                           "siguiente": f["siguiente"]}
                          for i, f in enumerate(st.session_state.historial, start=1)],
                         hide_index=True)

        with st.expander(":information_source: Acerca de"):
            st.caption(f"Problemas generados con {config.MODELO_PROBLEMAS} y tutor con "
                       f"{config.MODELO_CHAT} (Groq). Nivel asignado con un sistema difuso "
                       "Mamdani de 3 entradas y 27 reglas.")


@st.fragment(run_every=1)
def metricas():
    """Dibuja tiempo, errores y ayudas; se redibuja sola cada segundo."""
    m1, m2, m3 = st.columns(3)
    m1.metric(":hourglass_flowing_sand: Tiempo", f"{controlador.minutos_transcurridos():.1f} min",
              border=True, help="Corre desde que aparece el problema hasta que lo entregas "
                                "correctamente o te rindes.")
    m2.metric(":x: Errores", st.session_state.errores, border=True,
              help="Suma 1 cada compilación o ejecución con error y cada entrega incorrecta.")
    m3.metric(":bulb: Ayudas", st.session_state.ayudas, border=True,
              help="Suma 1 cada pregunta que el tutor responde.")


# --- Generación del problema y resultado (arriba, donde mira el estudiante) ---

def generacion():
    """Genera el problema pendiente mostrando el avance, y muestra avisos o errores."""
    if st.session_state.generando:
        with st.status("Preparando tu problema...", expanded=False) as avance:
            listo = controlador.generar_pendiente(avance)
            avance.update(label="Problema listo" if listo else "No se pudo generar el problema",
                          state="complete" if listo else "error")
        if listo:
            st.rerun()  # redibuja la página completa con el problema nuevo

    if st.session_state.aviso_generacion and not st.session_state.terminado:
        st.info(f":package: {st.session_state.aviso_generacion}")

    error = st.session_state.error_llm
    if error:
        with st.container(border=True):
            st.error(error["mensaje"])
            st.button(":arrows_counterclockwise: Reintentar",
                      on_click=controlador.al_pedir_problema)
            with st.expander("Detalle técnico"):
                st.code(error["detalle"], language="text")


def resultado():
    """Dibuja la decisión del sistema difuso cuando el problema terminó."""
    r = st.session_state.resultado
    if not (st.session_state.terminado and r):
        return

    with st.container(border=True):
        if r.resuelto:
            st.success(f":tada: ¡Problema resuelto en {r.tiempo:.1f} min!")
        else:
            st.warning(":white_flag: Te rendiste. Se evaluó con el peor caso.")

        c1, c2 = st.columns([3, 1], vertical_alignment="center")
        with c1:
            st.markdown(sesion.explicar_resultado(r, st.session_state.nivel_problema))
            st.progress(r.valor / 10, text=f"Puntaje del sistema difuso: {r.valor:.2f} de 10")
            st.caption(" · ".join(f"{nombre} {a:.0f}–{b:.0f}"
                                  for nombre, (a, b) in difuso.zonas_nivel().items())
                       + " (las zonas se traslapan: así funciona la lógica difusa)")
        with c2:
            st.button(":arrow_right: Siguiente problema", type="primary", width="stretch",
                      on_click=controlador.al_pedir_problema,
                      disabled=st.session_state.generando)

        with st.expander(":brain: Ver cómo decidió el sistema difuso (inferencia Mamdani)"):
            d1, d2 = st.columns([2, 3])
            with d1:
                st.markdown(f"**Entradas:** tiempo = {r.tiempo:.1f} min · "
                            f"errores = {r.errores} · ayudas = {r.ayudas}")
                st.markdown("**1. Fuzzificación** (grado de pertenencia de cada entrada)")
                st.dataframe(difuso.tabla_fuzzificacion(r.tiempo, r.errores, r.ayudas),
                             hide_index=True)
            with d2:
                figura = difuso.figura_salida(r.tiempo, r.errores, r.ayudas)
                st.pyplot(figura)
                plt.close(figura)
            st.markdown("**2. Reglas activadas** (fuerza = mínimo de los antecedentes)")
            st.dataframe(difuso.reglas_activadas(r.tiempo, r.errores, r.ayudas),
                         hide_index=True)
            st.markdown("**3 y 4. Agregación** (máximo de los conjuntos recortados) y "
                        f"**defuzzificación** por centroide = {r.valor:.2f}: ver la gráfica.")


# --- Columna izquierda: problema y tutor ---

def problema_y_tutor(p, bloqueado):
    """Dibuja la bienvenida, o el problema y el chat en pestañas.

    Args:
        p: ``Problema`` actual, o None si todavía no hay.
        bloqueado: True si no se puede interactuar (sin problema o ya terminado).
    """
    if p is None:
        with st.container(border=True):
            st.subheader(":wave: Bienvenido")
            st.markdown("Empiezas en nivel **novato**; puedes cambiarlo en la barra lateral. "
                        "Abre **¿Cómo funciona?** para ver cómo se mide tu avance.")
            st.button(":game_die: Generar mi primer problema", type="primary",
                      on_click=controlador.al_pedir_problema,
                      disabled=st.session_state.generando)
        return

    pestana_problema, pestana_tutor = st.tabs([":notebook_with_decorative_cover: Problema",
                                               ":robot: Tutor"])
    with pestana_problema:
        _problema(p)
    with pestana_tutor:
        _chat(bloqueado)


def _problema(p):
    """Dibuja el enunciado, los ejemplos y las correcciones del validador."""
    st.subheader(p.titulo)
    _badge_nivel(st.session_state.nivel_problema)
    st.markdown(p.descripcion)
    st.markdown(f"**Entrada:** {p.formato_entrada}")
    st.markdown(f"**Salida:** {p.formato_salida}")
    e1, e2 = st.columns(2)
    e1.markdown("**Ejemplo de entrada**")
    e1.code(p.ejemplo_entrada or "(ninguna)", language="text")
    e2.markdown("**Ejemplo de salida**")
    e2.code(p.ejemplo_salida, language="text")
    if st.session_state.correcciones:  # transparencia: qué corrigió el validador
        with st.expander(f":warning: El validador corrigió {len(st.session_state.correcciones)} "
                         "salida(s) generadas por el LLM"):
            for correccion in st.session_state.correcciones:
                st.caption(correccion)


def _chat(bloqueado):
    """Dibuja la conversación con el tutor y procesa la pregunta nueva."""
    mensajes = st.container(height=380, autoscroll=True)
    with mensajes:
        if not st.session_state.chat:
            st.caption("Pregunta lo que necesites: el tutor da pistas, no la solución. "
                       "Cada pregunta respondida cuenta como una ayuda.")
        for mensaje in st.session_state.chat:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje["content"])

    pregunta = st.chat_input("¿Por qué me sale TypeError?", disabled=bloqueado)
    if pregunta:
        with mensajes:
            with st.chat_message("user"):
                st.markdown(pregunta)
            with st.chat_message("assistant"):
                with st.spinner("El tutor está pensando..."):
                    respuesta, aviso = controlador.preguntar(pregunta)
                if aviso:
                    st.warning(aviso)
                else:
                    st.markdown(respuesta)


# --- Columna derecha: editor y consola ---

def editor_y_consola(p, bloqueado):
    """Dibuja el editor, los botones de acción y la consola.

    Args:
        p: ``Problema`` actual, o None si todavía no hay.
        bloqueado: True si los botones deben estar deshabilitados.
    """
    codigo = st_ace(
        value=p.codigo_inicial if p else "# Escribe tu solución aquí\n",
        language="python",
        theme="monokai",
        height=300,
        tab_size=4,
        auto_update=True,
        readonly=st.session_state.terminado,  # no se edita un problema terminado
        key=f"editor_{st.session_state.id_problema}",  # editor nuevo por problema
    )
    if codigo is not None:
        st.session_state.codigo = codigo

    with st.container(horizontal=True, wrap=True):
        st.button(":mag: Compilar", on_click=controlador.al_compilar, disabled=bloqueado,
                  help="Revisa la sintaxis sin ejecutar.")
        st.button(":arrow_forward: Ejecutar", on_click=controlador.al_ejecutar,
                  disabled=bloqueado, help="Corre tu programa con la entrada de la consola.")
        st.button(":white_check_mark: Entregar", on_click=controlador.al_entregar,
                  disabled=bloqueado, type="primary",
                  help="Corre los casos de prueba. Si pasas todos, el problema se da por resuelto.")
        with st.popover(":white_flag: Me rindo", disabled=bloqueado):
            st.markdown(f"¿Seguro? El problema termina y se evalúa con el **peor caso**: "
                        f"{config.TIEMPO_MAXIMO:.0f} min y al menos "
                        f"{config.ERRORES_MAXIMOS} errores.")
            st.button("Sí, me rindo", on_click=controlador.al_rendirse, type="primary",
                      disabled=bloqueado)

    _consola()


def _consola():
    """Dibuja la consola: entrada, salida, pista de error y resultado de cada caso."""
    resultados = st.session_state.resultados_pruebas
    titulo_casos = ":test_tube: Casos de prueba"
    if resultados:
        titulo_casos += f" ({sum(r['paso'] for r in resultados)}/{len(resultados)})"
    pestana_salida, pestana_casos = st.tabs([":computer: Salida", titulo_casos])

    with pestana_salida:
        ok = st.session_state.consola_ok
        if ok is not None:
            titulo = TITULOS_CONSOLA[(st.session_state.consola_etapa, ok)]
            if ok:
                st.success(titulo)
            else:
                st.error(titulo)
        # Entrada y salida lado a lado: los botones quedan pegados al editor y el
        # resultado de cada acción se ve sin desplazarse.
        c_entrada, c_salida = st.columns([2, 3])
        p = st.session_state.problema
        c_entrada.text_area("Entrada para Ejecutar (lo que leerá input(), un dato por línea)",
                            value=p.ejemplo_entrada if p else "", height=120,
                            key=controlador.clave_entrada())
        with c_salida:
            st.caption("Salida")
            st.code(st.session_state.consola, language="text")
        if ok is False:
            pista = sesion.pista_error(st.session_state.consola)
            if pista:
                st.info(f":bulb: **Pista:** {pista}")

    with pestana_casos:
        if not resultados:
            st.caption("Aquí verás el resultado de cada caso cuando presiones Entregar.")
        for i, r in enumerate(resultados or [], start=1):
            with st.expander(f"{':white_check_mark:' if r['paso'] else ':x:'} Caso {i}",
                             expanded=not r["paso"]):
                st.caption("Entrada")
                st.code(r["entrada"] or "(vacía)", language="text")
                st.caption("Salida esperada")
                st.code(r["esperada"], language="text")
                st.caption("Tu salida")
                st.code(r["obtenida"], language="text")


def historial():
    """Dibuja la tabla completa del historial de la sesión, si hay problemas terminados."""
    if st.session_state.historial:
        with st.expander("Historial completo de la sesión"):
            st.dataframe(st.session_state.historial, hide_index=True)
