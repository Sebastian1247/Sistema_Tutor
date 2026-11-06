"""El reintento de generación se prueba con un generador falso: cero llamadas a Groq."""

import pytest

from nucleo import generacion
from tests.conftest import crear_problema


class GeneradorFalso:
    def __init__(self, problemas):
        self.problemas = list(problemas)
        self.llamadas = []

    def __call__(self, nivel, titulos_previos):
        self.llamadas.append((nivel, list(titulos_previos)))
        return self.problemas.pop(0)


def test_primer_intento_valido():
    generar = GeneradorFalso([crear_problema()])
    problema, correcciones = generacion.generar_problema_validado("novato", ["Otro"], generar)
    assert problema.titulo == "Dígitos pares"
    assert correcciones == []
    assert generar.llamadas == [("novato", ["Otro"])]


def test_reintenta_si_la_solucion_no_funciona():
    generar = GeneradorFalso([crear_problema(solucion="print(("), crear_problema()])
    problema, _ = generacion.generar_problema_validado("novato", [], generar)
    assert problema.solucion != "print(("
    assert len(generar.llamadas) == 2


def test_se_rinde_despues_de_los_intentos_configurados():
    generar = GeneradorFalso([crear_problema(solucion="print((")] * 3)
    with pytest.raises(ValueError, match="generó 2 problemas"):
        generacion.generar_problema_validado("novato", [], generar, intentos=2)
    assert len(generar.llamadas) == 2
