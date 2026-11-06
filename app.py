import time
import warnings

import matplotlib
matplotlib.use("Agg")                    # gráficas sin ventanas (Streamlit las dibuja)
import matplotlib.pyplot as plt

import groq
import streamlit as st
from streamlit_ace import st_ace

import ejecutor
import fuzzy_nivel
import llm
import validador

warnings.filterwarnings("ignore", message=".*non-interactive.*")

st.set_page_config(page_title="Tutor de Python", page_icon=":snake:", layout="wide")

NIVELES = ["novato", "intermedio", "avanzado"]
INTENTOS_GENERACION = 2          # si la solución del LLM no funciona, se pide otro problema
TIEMPO_MAXIMO = 60.0             # min: con "Me rindo" se evalúa el peor caso
ERRORES_MAXIMOS = 15


# --- Estado de la sesión ---
def iniciar_estado():
    valores_iniciales = {
        "errores": 0,
        "ayudas": 0,
        "inicio": None,
        "fin": None,                # NUEVO: momento en que terminó el problema
        "codigo": "",
        "entrada": "",
        "consola": "Aquí aparecerá la salida de la ejecución del código.",
        "consola_ok": None,
        "nivel": "novato",
        "problema": None,
        "nivel_problema": None,
        "id_problema": 0,
        "titulos_previos": [],
        "error_llm": None,
        "chat": [],
        "correcciones": [],         # NUEVO: salidas del LLM corregidas por el validador
        "resultados_pruebas": None, # NUEVO: resultado de Entregar
        "terminado": False,         # NUEVO: el problema ya se resolvió o se abandonó
        "resultado": None,          # NUEVO: decisión del sistema difuso
        "historial": [],            # NUEVO: una fila por problema terminado
    }
    for clave, valor in valores_iniciales.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor


def minutos_transcurridos():
    if st.session_state.inicio is None:
        return 0.0
    fin = st.session_state.fin or time.time()       # CAMBIO: el reloj se detiene al terminar
    return (fin - st.session_state.inicio) / 60


def siguiente_nivel(actual, recomendado):
    """El nivel sube o baja como máximo un escalón por problema."""
    i, j = NIVELES.index(actual), NIVELES.index(recomendado)
    if j > i:
        return NIVELES[i + 1]
    if j < i:
        return NIVELES[i - 1]
    return actual


def generar_problema_validado(nivel):
    """Pide un problema al LLM y lo valida ejecutando su solución."""
    ultimo_error = None
    for _ in range(INTENTOS_GENERACION):
        problema = llm.generar_problema(nivel, st.session_state.titulos_previos)
        try:
            return validador.validar_problema(problema)
        except ValueError as error:
            ultimo_error = error
    raise ValueError(f"el LLM generó {INTENTOS_GENERACION} problemas cuya solución "
                     f"no funciona ({ultimo_error})")


# --- Callbacks (se ejecutan antes de redibujar la página) ---
def nuevo_problema():
    nivel = st.session_state.nivel
    try:
        with st.spinner(f"Generando y validando un problema de nivel {nivel}..."):
            problema, correcciones = generar_problema_validado(nivel)
    except groq.RateLimitError:
        st.session_state.error_llm = ("Se alcanzó el límite del plan gratuito de Groq. "
                                      "Espera un minuto e intenta de nuevo; si persiste, "
                                      "se agotó la cuota del día.")
        return
    except Exception as error:
        st.session_state.error_llm = f"No se pudo generar el problema: {error}"
        return

    st.session_state.error_llm = None
    st.session_state.problema = problema
    st.session_state.correcciones = correcciones
    st.session_state.nivel_problema = nivel
    st.session_state.titulos_previos.append(problema.titulo)
    st.session_state.id_problema += 1
    st.session_state.codigo = problema.codigo_inicial
    st.session_state.entrada = problema.ejemplo_entrada
    st.session_state.consola = "Aquí aparecerá la salida de la ejecución del código."
    st.session_state.consola_ok = None
    st.session_state.errores = 0
    st.session_state.ayudas = 0
    st.session_state.chat = []
    st.session_state.resultados_pruebas = None
    st.session_state.terminado = False
    st.session_state.resultado = None
    st.session_state.fin = None
    st.session_state.inicio = time.time()           # DESPUÉS de generar y validar


def al_compilar():
    ok, mensaje = ejecutor.compilar(st.session_state.codigo)
    st.session_state.consola = mensaje
    st.session_state.consola_ok = ok
    if not ok:
        st.session_state.errores += 1


def al_ejecutar():
    ok, mensaje = ejecutor.compilar(st.session_state.codigo)
    if not ok:
        st.session_state.consola = mensaje
        st.session_state.consola_ok = False
        st.session_state.errores += 1
        return

    ok, salida = ejecutor.ejecutar(st.session_state.codigo, st.session_state.entrada)
    if "EOFError" in salida:
        salida += ("\nSugerencia: tu programa usa input() pero no hay suficientes datos "
                   "en el cuadro de entrada. Escríbelos ahí, uno por línea.")
    st.session_state.consola = salida
    st.session_state.consola_ok = ok
    if not ok:
        st.session_state.errores += 1


def al_entregar():                                   # NUEVO
    ok, mensaje = ejecutor.compilar(st.session_state.codigo)
    if not ok:
        st.session_state.consola = mensaje
        st.session_state.consola_ok = False
        st.session_state.errores += 1
        return

    resultados = ejecutor.evaluar_pruebas(st.session_state.codigo,
                                          st.session_state.problema.casos_prueba)
    st.session_state.resultados_pruebas = resultados
    aprobados = sum(r["paso"] for r in resultados)

    if aprobados == len(resultados):
        st.session_state.consola = f"Correcto: pasaste los {len(resultados)} casos de prueba."
        st.session_state.consola_ok = True
        finalizar(resuelto=True)
    else:
        st.session_state.consola = (f"Incorrecto: pasaste {aprobados} de {len(resultados)} casos "
                                    "de prueba. Revisa los detalles abajo.")
        st.session_state.consola_ok = False
        st.session_state.errores += 1


def al_rendirse():                                   # NUEVO
    finalizar(resuelto=False)


def finalizar(resuelto):                             # NUEVO: aquí entra el sistema difuso
    st.session_state.fin = time.time()               # detiene el reloj

    if resuelto:
        tiempo = minutos_transcurridos()
    else:                                            # rendirse = peor caso
        tiempo = TIEMPO_MAXIMO
        st.session_state.errores = max(st.session_state.errores, ERRORES_MAXIMOS)

    errores = st.session_state.errores
    ayudas = st.session_state.ayudas
    valor, recomendado, _ = fuzzy_nivel.inferir(tiempo, errores, ayudas)
    siguiente = siguiente_nivel(st.session_state.nivel_problema, recomendado)

    st.session_state.resultado = {
        "resuelto": resuelto, "tiempo": tiempo, "errores": errores, "ayudas": ayudas,
        "valor": valor, "recomendado": recomendado, "siguiente": siguiente,
    }
    st.session_state.historial.append({
        "problema": st.session_state.problema.titulo,
        "nivel": st.session_state.nivel_problema,
        "resuelto": "sí" if resuelto else "no",
        "tiempo (min)": round(tiempo, 1),
        "errores": errores,
        "ayudas": ayudas,
        "salida difusa": round(valor, 2),
        "recomendado": recomendado,
        "siguiente": siguiente,
    })
    st.session_state.nivel = siguiente               # nivel del próximo problema
    st.session_state.terminado = True


def al_preguntar():
    pregunta = st.session_state.pregunta.strip()
    if not pregunta or st.session_state.problema is None:
        return

    st.session_state.chat.append({"role": "user", "content": pregunta})
    try:
        with st.spinner("El tutor está pensando..."):
            respuesta = llm.pedir_ayuda(
                st.session_state.chat,
                st.session_state.problema,
                st.session_state.nivel_problema,
                st.session_state.codigo,
                st.session_state.consola,
            )
        st.session_state.ayudas += 1
    except groq.RateLimitError:
        respuesta = ("Se alcanzó el límite del plan gratuito de Groq. "
                     "Espera un minuto y vuelve a preguntar.")
    except Exception as error:
        respuesta = f"No pude responder: {error}"

    st.session_state.chat.append({"role": "assistant", "content": respuesta})


iniciar_estado()

# --- Barra lateral ---
with st.sidebar:
    st.header(":gear: Configuración")
    st.selectbox("Nivel del siguiente problema", NIVELES, key="nivel",
                 help="Al terminar cada problema, el sistema difuso lo actualiza.")
    st.caption(f"Modelo de problemas: {llm.MODELO_PROBLEMAS}")
    st.caption(f"Modelo del tutor: {llm.MODELO_CHAT}")

    if st.session_state.historial:                   # NUEVO
        st.divider()
        st.subheader("Historial")
        st.dataframe(st.session_state.historial, hide_index=True)

st.title(":snake: Tutor de programación en Python")


@st.fragment(run_every=1)
def mostrar_metricas():
    m1, m2, m3 = st.columns(3)
    m1.metric(":hourglass_flowing_sand: Tiempo transcurrido", f"{minutos_transcurridos():.2f} min")
    m2.metric(":x: Errores", st.session_state.errores)
    m3.metric(":bulb: Ayudas solicitadas", st.session_state.ayudas)


mostrar_metricas()

p = st.session_state.problema
bloqueado = p is None or st.session_state.terminado     # NUEVO: sin problema o ya terminado

# --- Fila 1: problema | chatbot ---
col_problema, col_chat = st.columns([3, 2])

with col_problema:
    st.button(":game_die: Nuevo problema", on_click=nuevo_problema)
    if st.session_state.error_llm:
        st.error(st.session_state.error_llm)

    with st.container(border=True, height=400):
        if p is None:
            st.subheader(":notebook_with_decorative_cover: Problema")
            st.info("Elige el nivel en la barra lateral y presiona **Nuevo problema**.")
        else:
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
            if st.session_state.correcciones:         # NUEVO: transparencia del validador
                with st.expander(f":warning: El validador corrigió {len(st.session_state.correcciones)} "
                                 "salida(s) generadas por el LLM"):
                    for correccion in st.session_state.correcciones:
                        st.caption(correccion)

with col_chat:
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
            c2.form_submit_button("Enviar", on_click=al_preguntar, disabled=bloqueado)

# --- Fila 2: editor | ejecución ---
col_editor, col_consola = st.columns([3, 2])

with col_editor:
    st.subheader(":memo: Editor de código")
    codigo = st_ace(
        value=p.codigo_inicial if p else "# Escribe tu solución aquí\n",
        language="python",
        theme="monokai",
        height=300,
        tab_size=4,
        auto_update=True,
        readonly=st.session_state.terminado,         # NUEVO: no se edita al terminar
        key=f"editor_{st.session_state.id_problema}",
    )
    if codigo is not None:
        st.session_state.codigo = codigo

    b1, b2, b3, b4 = st.columns(4)                   # CAMBIO: 4 botones
    b1.button(":gear: Compilar", on_click=al_compilar, disabled=bloqueado)
    b2.button(":arrow_forward: Ejecutar", on_click=al_ejecutar, disabled=bloqueado)
    b3.button(":white_check_mark: Entregar", on_click=al_entregar, disabled=bloqueado,
              type="primary", help="Corre los casos de prueba. Si pasas todos, el problema "
                                   "se da por resuelto.")
    b4.button(":white_flag: Me rindo", on_click=al_rendirse, disabled=bloqueado)

with col_consola:
    st.subheader(":computer: Consola de ejecución")
    st.text_area("Entrada para el programa (lo que leerá input())", key="entrada", height=80)
    if st.session_state.consola_ok is True:
        st.success("Sin errores")
    elif st.session_state.consola_ok is False:
        st.error("Hubo un error")
    st.code(st.session_state.consola, language="text")

    if st.session_state.resultados_pruebas:          # NUEVO: detalle de cada caso
        for i, r in enumerate(st.session_state.resultados_pruebas, start=1):
            with st.expander(f"{':white_check_mark:' if r['paso'] else ':x:'} Caso {i}", expanded=not r["paso"]):
                st.caption("Entrada")
                st.code(r["entrada"] or "(vacía)", language="text")
                st.caption("Salida esperada")
                st.code(r["esperada"], language="text")
                st.caption("Tu salida")
                st.code(r["obtenida"], language="text")

# --- NUEVO: resultado del sistema difuso ---
if st.session_state.terminado and st.session_state.resultado:
    r = st.session_state.resultado
    st.divider()
    if r["resuelto"]:
        st.success(f":tada: ¡Problema resuelto en {r['tiempo']:.1f} min!")
    else:
        st.warning(":white_flag: Te rendiste. Se evaluó con el tiempo y los errores máximos.")

    c1, c2 = st.columns([2, 3])
    with c1:
        st.subheader(":brain: Decisión del sistema difuso")
        st.markdown(f"**Entradas:** tiempo = {r['tiempo']:.1f} min · "
                    f"errores = {r['errores']} · ayudas = {r['ayudas']}")
        st.markdown(f"**Salida (centroide):** {r['valor']:.2f} / 10")
        st.markdown(f"**Nivel recomendado:** {r['recomendado']}")
        st.markdown(f"**Nivel del siguiente problema:** {r['siguiente']}")
        if r["siguiente"] != r["recomendado"]:
            st.caption("El nivel cambia como máximo un escalón por problema.")
        st.button(":arrow_right: Siguiente problema", type="primary", on_click=nuevo_problema)

    with c2:
        _, _, simulacion = fuzzy_nivel.inferir(r["tiempo"], r["errores"], r["ayudas"])
        fuzzy_nivel.nivel.view(sim=simulacion)       # conjunto agregado + centroide
        figura = plt.gcf()
        st.pyplot(figura)
        plt.close(figura)

    with st.expander("Ver el detalle de la inferencia"):
        st.markdown("**1. Fuzzificación** (grado de pertenencia de cada entrada)")
        t, e, a = fuzzy_nivel.recortar(r["tiempo"], r["errores"], r["ayudas"])
        filas = []
        for variable, valor in [(fuzzy_nivel.tiempo, t), (fuzzy_nivel.errores, e),
                                (fuzzy_nivel.ayudas, a)]:
            for termino, grado in fuzzy_nivel.fuzzificar(variable, valor).items():
                filas.append({"variable": variable.label, "valor": valor,
                              "término": termino, "grado": round(grado, 3)})
        st.dataframe(filas, hide_index=True)

        st.markdown("**2. Reglas activadas** (fuerza = mínimo de los antecedentes)")
        st.dataframe(fuzzy_nivel.reglas_activadas(t, e, a), hide_index=True)

        st.markdown("**3 y 4. Agregación** (máximo de los conjuntos recortados) y "
                    "**defuzzificación** por centroide: ver la gráfica.")