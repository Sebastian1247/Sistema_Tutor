from tutor import ejecutor
from tutor.modelos import CasoPrueba


# --- compilar ---

def test_compilar_editor_vacio():
    assert ejecutor.compilar("   \n") == (False, "El editor está vacío.")


def test_compilar_codigo_correcto():
    ok, mensaje = ejecutor.compilar("print('hola')")
    assert ok
    assert "Compilación correcta" in mensaje


def test_compilar_error_de_sintaxis_indica_linea_y_marca():
    ok, mensaje = ejecutor.compilar("x = 1\nif x > 0\n    print(x)")
    assert not ok
    assert "SyntaxError en la línea 2" in mensaje
    assert "if x > 0" in mensaje
    assert "^" in mensaje


# --- ejecutar ---

def test_ejecutar_lee_la_entrada():
    ok, salida = ejecutor.ejecutar("a = int(input())\nb = int(input())\nprint(a + b)", "2\n3")
    assert ok
    assert salida.strip() == "5"


def test_ejecutar_sin_salida():
    assert ejecutor.ejecutar("x = 1") == (True, "(el programa no imprimió nada)")


def test_ejecutar_error_en_tiempo_de_ejecucion_oculta_la_ruta_temporal():
    ok, salida = ejecutor.ejecutar("print(1 / 0)")
    assert not ok
    assert "ZeroDivisionError" in salida
    assert "tu_programa.py" in salida


def test_ejecutar_sin_datos_suficientes_da_eoferror():
    ok, salida = ejecutor.ejecutar("input()\ninput()", "uno")
    assert not ok
    assert "EOFError" in salida


def test_ejecutar_ciclo_infinito_se_corta(monkeypatch):
    monkeypatch.setattr(ejecutor, "LIMITE_SEGUNDOS", 1)
    ok, salida = ejecutor.ejecutar("while True:\n    pass")
    assert not ok
    assert "Tiempo agotado" in salida


def test_ejecutar_acepta_unicode():
    ok, salida = ejecutor.ejecutar("print(input() + ' ñandú')", "año")
    assert ok
    assert salida.strip() == "año ñandú"


def test_el_programa_no_ve_las_variables_secretas(monkeypatch):
    # Clave falsa: la prueba nunca usa ni imprime la clave real
    monkeypatch.setenv("GROQ_API_KEY", "clave-falsa-de-prueba")
    ok, salida = ejecutor.ejecutar("import os\nprint(os.environ.get('GROQ_API_KEY'))")
    assert ok
    assert salida.strip() == "None"


# --- normalizar y evaluar_pruebas ---

def test_normalizar_ignora_espacios_finales_y_lineas_vacias_externas():
    assert ejecutor.normalizar("\na  \n  b\t\n\n") == "a\n  b"


def test_evaluar_pruebas_detecta_casos_que_pasan_y_que_fallan():
    casos = [CasoPrueba(entrada="2", salida="4"), CasoPrueba(entrada="3", salida="9")]
    resultados = ejecutor.evaluar_pruebas("n = int(input())\nprint(n * 2)", casos)
    assert [r["paso"] for r in resultados] == [True, False]
    assert resultados[1]["obtenida"].strip() == "6"


def test_evaluar_pruebas_falla_si_el_programa_truena_aunque_imprima_lo_esperado():
    casos = [CasoPrueba(entrada="", salida="4")]
    resultados = ejecutor.evaluar_pruebas("print(4)\nraise SystemExit(1)", casos)
    assert not resultados[0]["paso"]
