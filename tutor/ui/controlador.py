"""Controlador de la interfaz: estado de la sesión y acciones del estudiante.

Son adaptadores delgados: leen st.session_state, llaman a la lógica (sesion,
validador, llm) y guardan el resultado. Las reglas de negocio no viven aquí.
"""

import time

import streamlit as st

from tutor import llm, sesion, validador

CONSOLA_INICIAL = "Aquí aparecerá la salida de tu programa."

MENSAJE_CUOTA_PROBLEMA = ("Se alcanzó el límite del plan gratuito de Groq. "
                          "Espera un minuto e intenta de nuevo; si persiste, "
                          "se agotó la cuota del día.")
MENSAJE_CUOTA_TUTOR = ("Se alcanzó el límite del plan gratuito de Groq. "
                       "Espera un minuto y vuelve a preguntar.")

VALORES_INICIALES = {
    "errores": 0,
    "ayudas": 0,
    "inicio": None,
    "fin": None,                # momento en que terminó el problema
    "codigo": "",
    "entrada": "",
    "consola": CONSOLA_INICIAL,
    "consola_ok": None,
    "consola_etapa": None,      # compilacion | ejecucion | entrega
    "nivel": "novato",
    "nivel_sugerido": None,     # lo que decidió el sistema difuso
    "problema": None,
    "nivel_problema": None,
    "id_problema": 0,
    "titulos_previos": [],
    "generando": False,         # se pidió un problema y falta generarlo
    "error_llm": None,          # {"mensaje": para el estudiante, "detalle": técnico}
    "chat": [],
    "correcciones": [],         # salidas del LLM corregidas por el validador
    "resultados_pruebas": None, # resultado de Entregar
    "terminado": False,         # el problema ya se resolvió o se abandonó
    "resultado": None,          # decisión del sistema difuso (modelos.Resultado)
    "historial": [],            # una fila por problema terminado
}


# =====================================================================
# Estado de la sesión
# =====================================================================

def iniciar_estado():
    for clave, valor in VALORES_INICIALES.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor


def _reiniciar_problema(problema, correcciones, nivel):
    """Deja la sesión lista para un problema nuevo (reloj incluido)."""
    estado = st.session_state
    estado.error_llm = None
    estado.problema = problema
    estado.correcciones = correcciones
    estado.nivel_problema = nivel
    estado.titulos_previos.append(problema.titulo)
    estado.id_problema += 1
    estado.codigo = problema.codigo_inicial
    estado.entrada = problema.ejemplo_entrada
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
    estado.inicio = time.time()           # DESPUÉS de generar y validar


def minutos_transcurridos():
    return sesion.minutos_transcurridos(st.session_state.inicio, st.session_state.fin)


# =====================================================================
# Generar un problema
# =====================================================================

def al_pedir_problema():
    """Callback del botón: sólo marca la petición. La generación se hace al dibujar
    la página (generar_pendiente) para mostrar el avance en su lugar, no arriba."""
    st.session_state.generando = True
    st.session_state.error_llm = None


def generar_pendiente(avance):
    """avance: un st.status donde se informa cada paso. Regresa True si hubo problema."""
    # Se consume la bandera ANTES de llamar al LLM: si el estudiante interrumpe la
    # página a la mitad, no se vuelve a gastar una llamada sola.
    st.session_state.generando = False
    nivel = st.session_state.nivel
    intentos = 0

    def generar(nivel, titulos_previos):
        # Envuelve al generador real para informar el avance: el validador lo recibe
        # por inyección de dependencias y no se entera de la interfaz.
        nonlocal intentos
        intentos += 1
        reintento = f" (intento {intentos})" if intentos > 1 else ""
        avance.update(label=f"Pidiendo un problema de nivel {nivel} al LLM{reintento}...")
        problema = llm.generar_problema(nivel, titulos_previos)
        avance.update(label=f"Validando la solución de referencia con "
                            f"{len(problema.casos_prueba)} casos de prueba...")
        return problema

    try:
        problema, correcciones = validador.generar_problema_validado(
            nivel, st.session_state.titulos_previos, generar=generar)
    except llm.ErrorCuota as error:
        _error_generacion(MENSAJE_CUOTA_PROBLEMA, error)
    except llm.ErrorLLM as error:
        _error_generacion("El servicio del LLM no respondió bien (sin conexión o respuesta "
                          "inválida). Revisa tu conexión e intenta de nuevo.", error)
    except ValueError as error:
        _error_generacion("El LLM generó problemas cuya solución de referencia no funciona, "
                          "así que se descartaron. Intenta de nuevo.", error)
    except Exception as error:
        _error_generacion("Ocurrió un error inesperado al generar el problema.", error)
    else:
        _reiniciar_problema(problema, correcciones, nivel)
        return True
    return False


def _error_generacion(mensaje, error):
    st.session_state.error_llm = {"mensaje": mensaje,
                                  "detalle": f"{type(error).__name__}: {error}"}


# =====================================================================
# Compilar, ejecutar, entregar, rendirse
# =====================================================================

def _mostrar_en_consola(retro):
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
    _mostrar_en_consola(sesion.procesar_compilacion(st.session_state.codigo))


def al_ejecutar():
    _mostrar_en_consola(sesion.procesar_ejecucion(st.session_state.codigo,
                                                  st.session_state.entrada))


def al_entregar():
    retro = sesion.procesar_entrega(st.session_state.codigo,
                                    st.session_state.problema.casos_prueba)
    _mostrar_en_consola(retro)
    if retro.resuelto:
        _finalizar(resuelto=True)


def al_rendirse():
    _finalizar(resuelto=False)


def _finalizar(resuelto):
    """Aquí entra el sistema difuso (inferencia Mamdani en sesion.evaluar_desempeno)."""
    st.session_state.fin = time.time()               # detiene el reloj
    resultado = sesion.evaluar_desempeno(
        resuelto,
        minutos_transcurridos(),
        st.session_state.errores,
        st.session_state.ayudas,
        st.session_state.nivel_problema,
    )
    st.session_state.errores = resultado.errores     # al rendirse sube al máximo
    st.session_state.resultado = resultado
    st.session_state.historial.append(
        resultado.fila_historial(st.session_state.problema.titulo,
                                 st.session_state.nivel_problema))
    st.session_state.nivel = resultado.siguiente     # nivel del próximo problema
    st.session_state.nivel_sugerido = resultado.siguiente
    st.session_state.terminado = True


# =====================================================================
# Chat con el tutor
# =====================================================================

def preguntar(pregunta):
    """Regresa (respuesta, aviso). Sólo un intercambio exitoso entra al historial
    y cuenta como ayuda: los errores de conexión no contaminan lo que ve el LLM."""
    historial = st.session_state.chat + [{"role": "user", "content": pregunta}]
    try:
        respuesta = llm.pedir_ayuda(
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

    st.session_state.chat = historial + [{"role": "assistant", "content": respuesta}]
    st.session_state.ayudas += 1
    return respuesta, None
