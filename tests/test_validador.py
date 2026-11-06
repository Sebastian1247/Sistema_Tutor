"""Pruebas del validador: problemas generados y fuga de la solución en el tutor.

El generador y el tutor se sustituyen por versiones falsas: cero llamadas a Groq.
"""

import pytest

from tutor import llm, validador
from tests.conftest import SOLUCION_PARES, crear_problema


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
    problema = crear_problema(solucion=solucion, casos=[("2\\n3", "5\\n6")],
                              ejemplo=("1\\n1", "2\\n1"))
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


# --- generar_problema_validado: con un generador falso, cero llamadas a Groq ---

class GeneradorFalso:
    """Sustituto de ``llm.generar_problema``: entrega (o lanza) los elementos en orden."""

    def __init__(self, problemas):
        self.problemas = list(problemas)
        self.llamadas = []

    def __call__(self, nivel, titulos_previos):
        self.llamadas.append((nivel, list(titulos_previos)))
        siguiente = self.problemas.pop(0)
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente


def test_generacion_primer_intento_valido():
    generar = GeneradorFalso([crear_problema()])
    problema, correcciones = validador.generar_problema_validado("novato", ["Otro"], generar)
    assert problema.titulo == "Dígitos pares"
    assert correcciones == []
    assert generar.llamadas == [("novato", ["Otro"])]


def test_generacion_reintenta_si_la_solucion_no_funciona():
    generar = GeneradorFalso([crear_problema(solucion="print(("), crear_problema()])
    problema, _ = validador.generar_problema_validado("novato", [], generar)
    assert problema.solucion != "print(("
    assert len(generar.llamadas) == 2


def test_generacion_reintenta_si_el_json_es_invalido():
    generar = GeneradorFalso([llm.RespuestaInvalida("json_validate_failed"), crear_problema()])
    problema, _ = validador.generar_problema_validado("novato", [], generar)
    assert problema.titulo == "Dígitos pares"
    assert len(generar.llamadas) == 2


def test_generacion_no_reintenta_un_fallo_de_red():
    # Groq ya reintentó por su cuenta; se propaga para usar el banco local
    generar = GeneradorFalso([llm.ErrorLLM("sin conexión"), crear_problema()])
    with pytest.raises(llm.ErrorLLM):
        validador.generar_problema_validado("novato", [], generar)
    assert len(generar.llamadas) == 1


def test_generacion_se_rinde_despues_de_los_intentos_configurados():
    generar = GeneradorFalso([crear_problema(solucion="print((")] * 3)
    with pytest.raises(ValueError, match="en 2 intentos"):
        validador.generar_problema_validado("novato", [], generar, intentos=2)
    assert len(generar.llamadas) == 2


# --- fuga de la solución en las respuestas del tutor ---

FUGA = f"Aquí tienes:\n\n```python\n{SOLUCION_PARES}```\n"
PISTA = "Recorre cada dígito con un for. ¿Cómo sabes si un dígito es par?"
EJEMPLO_OTRO_CONTEXTO = "Por ejemplo:\n\n```python\nfor letra in 'hola':\n    print(letra)\n```"


def test_extraer_bloques_de_codigo():
    texto = "a\n```python\nx = 1\n```\nb\n```\ny = 2\n```"
    assert validador.extraer_codigo(texto) == ["x = 1", "y = 2"]


def test_detecta_la_solucion_completa(problema):
    assert validador.revela_solucion(FUGA, problema)


def test_una_pista_o_un_ejemplo_de_otro_contexto_no_es_fuga(problema):
    assert not validador.revela_solucion(PISTA, problema)
    assert not validador.revela_solucion(EJEMPLO_OTRO_CONTEXTO, problema)


def test_detecta_cuando_solo_completa_el_cuerpo_de_la_funcion():
    # "Sólo completa el cuerpo": el bloque no imprime nada por sí solo, pero junto
    # con el código del estudiante resuelve el problema
    estudiante = "def pares(n):\n    pass\n\n\nprint(pares(input().strip()))\n"
    problema = crear_problema(solucion="def pares(n):\n    return sum(int(d) % 2 == 0 for d in n)"
                                       "\n\n\nprint(pares(input().strip()))\n")
    cuerpo = "```python\ndef pares(n):\n    return sum(1 for d in n if int(d) % 2 == 0)\n```"
    assert validador.revela_solucion(cuerpo, problema, estudiante)
    assert not validador.revela_solucion(cuerpo, problema, "")


class TutorFalso:
    """Sustituto de ``llm.pedir_ayuda``: entrega las respuestas en orden y guarda historiales."""

    def __init__(self, respuestas):
        self.respuestas, self.historiales = list(respuestas), []

    def __call__(self, historial, problema, nivel, codigo, consola):
        self.historiales.append(historial)
        return self.respuestas.pop(0)


def test_filtro_deja_pasar_una_pista(problema):
    tutor = TutorFalso([PISTA])
    assert validador.respuesta_segura(tutor, [], problema, "novato", "", "") == (PISTA, PISTA, "ok")


def test_filtro_regenera_si_la_respuesta_revela_la_solucion(problema):
    tutor = TutorFalso([FUGA, PISTA])
    final, original, estado = validador.respuesta_segura(tutor, [], problema, "novato", "", "")
    assert (final, original, estado) == (PISTA, FUGA, "regenerada")
    assert tutor.historiales[1][-1]["content"] == validador.AVISO_REGENERAR


def test_filtro_usa_la_pista_fija_si_vuelve_a_revelarla(problema):
    tutor = TutorFalso([FUGA, FUGA])
    final, _, estado = validador.respuesta_segura(tutor, [], problema, "novato", "", "")
    assert (final, estado) == (validador.PISTA_FIJA, "reemplazada")
