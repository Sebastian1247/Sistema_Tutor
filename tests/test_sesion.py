import pytest

from tutor import config, sesion

NIVELES = config.NIVELES


# --- nivel adaptativo: máximo un escalón por problema ---

@pytest.mark.parametrize("actual", NIVELES)
@pytest.mark.parametrize("recomendado", NIVELES)
def test_siguiente_nivel_cambia_maximo_un_escalon(actual, recomendado):
    siguiente = sesion.siguiente_nivel(actual, recomendado)
    i, j, k = NIVELES.index(actual), NIVELES.index(recomendado), NIVELES.index(siguiente)
    assert abs(k - i) <= 1
    if j == i:
        assert k == i
    else:
        assert (k - i) * (j - i) > 0      # se mueve hacia el recomendado


def test_de_novato_a_avanzado_pasa_por_intermedio():
    assert sesion.siguiente_nivel("novato", "avanzado") == "intermedio"
    assert sesion.siguiente_nivel("avanzado", "novato") == "intermedio"


# --- reloj ---

def test_minutos_sin_problema_es_cero():
    assert sesion.minutos_transcurridos(None) == 0.0


def test_el_reloj_corre_hasta_ahora_y_se_detiene_al_terminar():
    assert sesion.minutos_transcurridos(1000, ahora=1600) == pytest.approx(10)
    assert sesion.minutos_transcurridos(1000, fin=1300, ahora=9999) == pytest.approx(5)


# --- compilar, ejecutar, entregar ---

def test_compilar_con_error_cuenta_un_error():
    retro = sesion.procesar_compilacion("if True print(1)")
    assert not retro.ok and retro.cuenta_error


def test_compilar_correcto_no_cuenta_error():
    retro = sesion.procesar_compilacion("print(1)")
    assert retro.ok and not retro.cuenta_error


def test_ejecutar_con_error_de_sintaxis_reporta_la_compilacion():
    retro = sesion.procesar_ejecucion("print(", "")
    assert retro.cuenta_error
    assert "SyntaxError" in retro.mensaje


def test_ejecutar_sin_entrada_suficiente_agrega_sugerencia():
    retro = sesion.procesar_ejecucion("input()", "")
    assert retro.cuenta_error
    assert "Sugerencia" in retro.mensaje


def test_ejecutar_correcto():
    retro = sesion.procesar_ejecucion("print(input())", "hola")
    assert retro.ok and not retro.cuenta_error
    assert retro.mensaje.strip() == "hola"


def test_entrega_correcta_resuelve_sin_contar_error(problema):
    retro = sesion.procesar_entrega(problema.solucion, problema.casos_prueba)
    assert retro.resuelto and retro.ok and not retro.cuenta_error
    assert retro.mensaje == "Correcto: pasaste los 3 casos de prueba."


def test_entrega_parcial_cuenta_error_y_no_resuelve(problema):
    retro = sesion.procesar_entrega("print(0)", problema.casos_prueba)
    assert not retro.resuelto and retro.cuenta_error
    assert retro.mensaje.startswith("Incorrecto: pasaste 1 de 3")
    assert len(retro.resultados_pruebas) == 3


def test_entrega_que_no_compila_no_corre_las_pruebas(problema):
    retro = sesion.procesar_entrega("print(", problema.casos_prueba)
    assert retro.cuenta_error and not retro.resuelto
    assert retro.resultados_pruebas is None


# --- evaluación con el sistema difuso ---

def test_resolver_usa_el_tiempo_real():
    r = sesion.evaluar_desempeno(True, 10, 4, 1.5, "novato")
    assert r.tiempo == 10 and r.errores == 4
    assert r.valor == pytest.approx(6.74, abs=0.01)
    assert r.recomendado == "avanzado"
    assert r.siguiente == "intermedio"           # un solo escalón


def test_rendirse_se_evalua_con_el_peor_caso():
    r = sesion.evaluar_desempeno(False, 2, 1, 0, "intermedio")
    assert r.tiempo == config.TIEMPO_MAXIMO
    assert r.errores == config.ERRORES_MAXIMOS
    assert r.recomendado == "novato"
    assert r.siguiente == "novato"


def test_rendirse_conserva_los_errores_si_ya_eran_mas():
    assert sesion.evaluar_desempeno(False, 2, 20, 0, "novato").errores == 20


def test_fila_del_historial():
    fila = sesion.evaluar_desempeno(True, 10.04, 4, 1, "novato").fila_historial("Pares", "novato")
    assert fila["resuelto"] == "sí"
    assert fila["tiempo (min)"] == 10.0
    assert set(fila) == {"problema", "nivel", "resuelto", "tiempo (min)", "errores", "ayudas",
                         "salida difusa", "recomendado", "siguiente"}
