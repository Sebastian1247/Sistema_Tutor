import pytest

from nucleo import validador
from tests.conftest import crear_problema


def test_problema_correcto_no_requiere_correcciones(problema):
    _, correcciones = validador.validar_problema(problema)
    assert correcciones == []


def test_corrige_la_salida_esperada_que_el_llm_calculo_mal():
    # El LLM dijo que 48392 tiene 2 dígitos pares; son 3 (4, 8 y 2)
    problema = crear_problema(casos=[("48392", "2"), ("13579", "0")], ejemplo=("48392", "2"))
    problema, correcciones = validador.validar_problema(problema)
    assert problema.casos_prueba[0].salida == "3"
    assert problema.ejemplo_salida == "3"
    assert len(correcciones) == 2
    assert correcciones[0].startswith("Caso 1:")
    assert correcciones[1].startswith("Ejemplo:")


def test_arregla_saltos_de_linea_escritos_como_texto():
    solucion = "a = int(input())\nb = int(input())\nprint(a + b)\nprint(a * b)"
    problema = crear_problema(solucion=solucion, casos=[("2\\n3", "5\\n6")], ejemplo=("1\\n1", "2\\n1"))
    problema, correcciones = validador.validar_problema(problema)
    assert problema.casos_prueba[0].entrada == "2\n3"
    assert problema.casos_prueba[0].salida == "5\n6"
    assert problema.ejemplo_entrada == "1\n1"
    assert correcciones == []


def test_descarta_solucion_que_no_compila():
    with pytest.raises(ValueError, match="no compila"):
        validador.validar_problema(crear_problema(solucion="print(("))


def test_descarta_solucion_que_truena_en_un_caso():
    solucion = "n = int(input())\nprint(10 // n)"
    with pytest.raises(ValueError, match="falla en el caso 2"):
        validador.validar_problema(crear_problema(solucion=solucion,
                                                  casos=[("2", "5"), ("0", "?")],
                                                  ejemplo=("5", "2")))


def test_descarta_solucion_que_truena_con_el_ejemplo():
    solucion = "n = int(input())\nprint(10 // n)"
    with pytest.raises(ValueError, match="con el ejemplo"):
        validador.validar_problema(crear_problema(solucion=solucion,
                                                  casos=[("2", "5")], ejemplo=("0", "?")))
