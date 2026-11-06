"""Controlador de la interfaz: estado de la sesión y acciones del estudiante.

Las funciones de este módulo son adaptadores delgados: leen
``st.session_state``, llaman a la lógica (``sesion``, ``validador``, ``llm``,
``banco``) y guardan el resultado. Las reglas del tutor no viven aquí.
"""

import time

import streamlit as st

from tutor import banco, llm, sesion, validador

CONSOLA_INICIAL = "Aquí aparecerá la salida de tu programa."

MENSAJE_CUOTA_TUTOR = ("Se alcanzó el límite del plan gratuito de Groq. "
                       "Espera un minuto y vuelve a preguntar.")

# Claves de st.session_state y su valor al abrir la página.
VALORES_INICIALES = {
    "errores": 0,
    "ayudas": 0,
    "inicio": None,  # marca de tiempo en que apareció el problema
    "fin": None,  # marca de tiempo en que terminó el problema
    "codigo": "",
    "consola": CONSOLA_INICIAL,
    "consola_ok": None,
    "consola_etapa": None,  # "compilacion", "ejecucion" o "entrega"
    "nivel": "novato",  # nivel del siguiente problema
    "nivel_sugerido": None,  # último nivel que decidió el sistema difuso
    "problema": None,
    "nivel_problema": None,
    "id_problema": 0,
    "titulos_previos": [],
    "generando": False,  # se pidió un problema y falta generarlo
    "error_llm": None,  # {"mensaje": para el estudiante, "detalle": técnico}
    "aviso_generacion": None,  # motivo por el que el problema vino del banco local
    "chat": [],
    "correcciones": [],  # salidas esperadas que corrigió el validador
    "resultados_pruebas": None,  # resultado de cada caso al entregar
    "terminado": False,  # el problema ya se resolvió o se abandonó
    "resultado": None,  # modelos.Resultado del último problema
    "historial": [],  # una fila por problema terminado
}


# --- Estado de la sesión ---

def iniciar_estado():
    """Crea en ``st.session_state`` las claves que todavía no existen."""
    for clave, valor in VALORES_INICIALES.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor


def _reiniciar_problema(problema, correcciones, nivel):
    """Deja la sesión lista para un problema nuevo e inicia el reloj."""
    estado = st.session_state
    estado.error_llm = None
    estado.problema = problema
    estado.correcciones = correcciones
    estado.nivel_problema = nivel
    estado.titulos_previos.append(problema.titulo)
    estado.id_problema += 1
    estado.codigo = problema.codigo_inicial
    estado.consola = CONSOLA_INICIAL
    estado.consola_ok = None
    estado.consola_etapa = None
    estado.errores = 0
    estado.ayudas = 0
    estado.chat = []
    estado.resultados_pruebas = None
    estado.terminado = False
    estado.resultado = None
    estado.fin = None
    estado.inicio = time.time()  # después de generar y validar: la espera no cuenta


def clave_entrada():
    """Regresa la clave del cuadro de entrada del problema actual.

    Hay una clave por problema (igual que el editor) para que el cuadro arranque
    con el ejemplo sin escribir en ``session_state`` antes de que el widget
    exista: Streamlit borra ese valor si la página se reinicia con ``st.rerun``
    antes de dibujarlo.
    """
    return f"entrada_{st.session_state.id_problema}"


def minutos_transcurridos():
    """Regresa los minutos que lleva el problema actual."""
    return sesion.minutos_transcurridos(st.session_state.inicio, st.session_state.fin)


# --- Generar un problema ---

def al_pedir_problema():
    """Marca que se pidió un problema (callback de los botones).

    La generación se hace al dibujar la página, en ``generar_pendiente``, para
    mostrar el avance junto al área del problema.
    """
    st.session_state.generando = True
    st.session_state.error_llm = None
    st.session_state.aviso_generacion = None


def generar_pendiente(avance):
    """Genera el problema pedido; si el LLM falla, usa el banco local.

    Args:
        avance: Elemento ``st.status`` donde se informa cada paso.

    Returns:
        True si se obtuvo un problema; False si falló también el banco local.
    """
    # La bandera se consume antes de llamar al LLM: si el estudiante interrumpe
    # la página a la mitad, no se gasta otra llamada automáticamente.
    st.session_state.generando = False
    nivel = st.session_state.nivel
    intentos = 0

    def generar(nivel, titulos_previos):
        # Envuelve al generador real para informar el avance; el validador lo
        # recibe por inyección de dependencias y no conoce la interfaz.
        nonlocal intentos
        intentos += 1
        reintento = f" (intento {intentos})" if intentos > 1 else ""
        avance.update(label=f"Pidiendo un problema de nivel {nivel} al LLM{reintento}...")
        problema = llm.generar_problema(nivel, titulos_previos)
        avance.update(label=f"Validando la solución de referencia con "
                            f"{len(problema.casos_prueba)} casos de prueba...")
        return problema

    previos = st.session_state.titulos_previos
    try:
        problema, correcciones = validador.generar_problema_validado(nivel, previos, generar)
        aviso = None
    except (llm.ErrorLLM, ValueError) as error:
        # Sin LLM (cuota, red o respuestas inválidas) se usa el banco local: otro
        # generador con la misma firma que pasa por el mismo validador.
        avance.update(label="Sin LLM: tomando un problema del banco local...")
        try:
            problema, correcciones = validador.generar_problema_validado(
                nivel, previos, banco.problema_del_banco)
        except Exception as error_banco:
            _error_generacion("No se pudo obtener un problema del LLM ni del banco local.",
                              error_banco)
            return False
        aviso = _motivo_respaldo(error)
        if problema.titulo in previos:
            aviso += " Ya viste todos los problemas de este nivel del banco; este se repite."
    except Exception as error:
        _error_generacion("Ocurrió un error inesperado al generar el problema.", error)
        return False

    _reiniciar_problema(problema, correcciones, nivel)
    st.session_state.aviso_generacion = aviso
    return True


def _motivo_respaldo(error):
    """Explica al estudiante por qué el problema vino del banco local."""
    if isinstance(error, llm.ErrorCuota):
        motivo = "Se alcanzó el límite del plan gratuito de Groq"
    elif isinstance(error, ValueError):  # incluye llm.RespuestaInvalida
        motivo = "El LLM no generó un problema válido"
    else:
        motivo = "No hubo conexión con el LLM"
    return f"{motivo}, así que se usó un problema del banco local."


def _error_generacion(mensaje, error):
    """Guarda un error de generación: el mensaje para el estudiante y el detalle técnico."""
    st.session_state.error_llm = {"mensaje": mensaje,
                                  "detalle": f"{type(error).__name__}: {error}"}


# --- Compilar, ejecutar, entregar y rendirse ---

def _mostrar_en_consola(retro):
    """Copia una ``Retroalimentacion`` al estado de la consola y cuenta el error si aplica."""
    st.session_state.consola = retro.mensaje
    st.session_state.consola_ok = retro.ok
    st.session_state.consola_etapa = retro.etapa
    if retro.resultados_pruebas is not None:
        st.session_state.resultados_pruebas = retro.resultados_pruebas
    if retro.cuenta_error:
        st.session_state.errores += 1
        st.toast("Se contó un error (+1). Los errores influyen en tu siguiente nivel.",
                 icon=":material/error:")


def al_compilar():
    """Callback de Compilar."""
    _mostrar_en_consola(sesion.procesar_compilacion(st.session_state.codigo))


def al_ejecutar():
    """Callback de Ejecutar: usa la entrada que escribió el estudiante."""
    _mostrar_en_consola(sesion.procesar_ejecucion(st.session_state.codigo,
                                                  st.session_state.get(clave_entrada(), "")))


def al_entregar():
    """Callback de Entregar: si pasa todos los casos, el problema termina."""
    retro = sesion.procesar_entrega(st.session_state.codigo,
                                    st.session_state.problema.casos_prueba)
    _mostrar_en_consola(retro)
    if retro.resuelto:
        _finalizar(resuelto=True)


def al_rendirse():
    """Callback de "Sí, me rindo"."""
    _finalizar(resuelto=False)


def _finalizar(resuelto):
    """Termina el problema y aplica el sistema difuso (inferencia Mamdani).

    Un problema se evalúa una sola vez: si ya terminó, no hace nada.
    """
    if st.session_state.terminado:
        return
    st.session_state.fin = time.time()  # detiene el reloj
    resultado = sesion.evaluar_desempeno(
        resuelto,
        minutos_transcurridos(),
        st.session_state.errores,
        st.session_state.ayudas,
        st.session_state.nivel_problema,
    )
    st.session_state.errores = resultado.errores  # al rendirse sube al máximo
    st.session_state.resultado = resultado
    st.session_state.historial.append(
        resultado.fila_historial(st.session_state.problema.titulo,
                                 st.session_state.nivel_problema))
    st.session_state.nivel = resultado.siguiente
    st.session_state.nivel_sugerido = resultado.siguiente
    st.session_state.terminado = True


# --- Chat con el tutor ---

def preguntar(pregunta):
    """Envía una pregunta al tutor, filtrando las respuestas que revelan la solución.

    Sólo un intercambio exitoso entra al historial y cuenta como ayuda; un error
    de conexión no deja mensajes que después lea el LLM.

    Args:
        pregunta: Texto que escribió el estudiante.

    Returns:
        Tupla ``(respuesta, aviso)``: la respuesta del tutor o, si falló, None y
        un aviso para el estudiante.
    """
    historial = st.session_state.chat + [{"role": "user", "content": pregunta}]
    try:
        respuesta, _, _ = validador.respuesta_segura(
            llm.pedir_ayuda,
            historial,
            st.session_state.problema,
            st.session_state.nivel_problema,
            st.session_state.codigo,
            st.session_state.consola,
        )
    except llm.ErrorCuota:
        return None, MENSAJE_CUOTA_TUTOR
    except Exception:
        return None, ("El tutor no pudo responder (sin conexión o error del servicio). "
                      "Tu pregunta no contó como ayuda; vuelve a escribirla.")

    # Sólo la respuesta final entra al historial: la que revelaba la solución no
    # se muestra ni se vuelve a enviar al LLM. El filtro no se anuncia, para no
    # indicarle al estudiante qué preguntas "casi funcionan".
    st.session_state.chat = historial + [{"role": "assistant", "content": respuesta}]
    st.session_state.ayudas += 1
    return respuesta, None
