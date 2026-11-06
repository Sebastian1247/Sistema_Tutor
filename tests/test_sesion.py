import pytest

from tutor import config, difuso, sesion

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


# --- la decisión SIEMPRE sale de la inferencia Mamdani ---

def test_el_sistema_es_mamdani_con_centroide():
    assert difuso.nivel.defuzzify_method == "centroid"
    assert len(difuso.REGLAS) == 27


@pytest.mark.parametrize("resuelto, minutos, errores, ayudas", [
    (True, 10, 4, 1), (True, 3, 0, 0), (True, 25, 7, 3), (True, 2, 0, 8), (False, 5, 2, 1),
])
def test_evaluar_desempeno_usa_la_inferencia_mamdani(resuelto, minutos, errores, ayudas):
    r = sesion.evaluar_desempeno(resuelto, minutos, errores, ayudas, "intermedio")
    valor, etiqueta, _ = difuso.inferir(r.tiempo, r.errores, r.ayudas)
    assert r.valor == valor
    assert r.recomendado == etiqueta


def test_la_explicacion_no_cambia_la_decision():
    r = sesion.evaluar_desempeno(True, 10, 4, 1, "novato")
    antes = (r.valor, r.recomendado, r.siguiente)
    sesion.explicar_resultado(r, "novato")
    assert (r.valor, r.recomendado, r.siguiente) == antes


# --- explicación en lenguaje simple ---

def test_explicacion_al_subir_de_nivel():
    r = sesion.evaluar_desempeno(True, 10, 4, 1, "novato")
    texto = sesion.explicar_resultado(r, "novato")
    assert texto.startswith("**Subes a intermedio.**")
    assert "tiempo corto" in texto and "4 errores (algunos)" in texto and "1 ayuda (pocas)" in texto
    assert "un escalón" in texto                  # recomendó avanzado, sube sólo a intermedio
    assert f"{r.valor:.1f} de 10" in texto        # el puntaje es el de la inferencia


def test_explicacion_al_rendirse():
    r = sesion.evaluar_desempeno(False, 2, 1, 0, "intermedio")
    texto = sesion.explicar_resultado(r, "intermedio")
    assert texto.startswith("**Bajas a novato.**")
    assert "Te rendiste" in texto and "60 min" in texto


def test_explicacion_menciona_el_veto_por_muchas_ayudas():
    r = sesion.evaluar_desempeno(True, 2, 0, 8, "novato")
    texto = sesion.explicar_resultado(r, "novato")
    assert texto.startswith("**Te mantienes en novato.**")
    assert "dependiste del tutor" in texto


# --- pistas de errores y etapa de la consola ---

@pytest.mark.parametrize("codigo, tipo", [
    ("print(x)", "NameError"),
    ("print([1][3])", "IndexError"),
    ("print('a' + 1)", "TypeError"),
    ("print(int('hola'))", "ValueError"),
])
def test_pista_segun_el_tipo_de_error(codigo, tipo):
    retro = sesion.procesar_ejecucion(codigo, "")
    assert sesion.pista_error(retro.mensaje) == sesion.PISTAS_ERRORES[tipo]


def test_pista_de_error_de_sintaxis():
    retro = sesion.procesar_compilacion("if True print(1)")
    assert sesion.pista_error(retro.mensaje) == sesion.PISTAS_ERRORES["SyntaxError"]


def test_sin_pista_si_no_hay_error_conocido():
    assert sesion.pista_error("Incorrecto: pasaste 1 de 3 casos de prueba.") is None
    assert sesion.pista_error("Tiempo agotado: el programa tardó más de 5 s.") is None


def test_etapa_de_cada_accion(problema):
    assert sesion.procesar_compilacion("print(1)").etapa == "compilacion"
    assert sesion.procesar_ejecucion("print(", "").etapa == "compilacion"
    assert sesion.procesar_ejecucion("print(1)", "").etapa == "ejecucion"
    assert sesion.procesar_entrega("print(0)", problema.casos_prueba).etapa == "entrega"


def test_zonas_de_nivel_de_la_salida():
    zonas = difuso.zonas_nivel()
    assert list(zonas) == ["novato", "intermedio", "avanzado"]
    assert zonas["novato"][0] == 0 and zonas["avanzado"][1] == 10
