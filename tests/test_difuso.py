"""Pruebas del sistema de inferencia difusa Mamdani."""

import pytest

from tutor import difuso


def test_ejemplo_resuelto_a_mano():
    """(tiempo=10, errores=4, ayudas=1.5) -> 6.74, avanzado."""
    valor, etiqueta, _ = difuso.inferir(10, 4, 1.5)
    assert valor == pytest.approx(6.74, abs=0.01)
    assert etiqueta == "avanzado"


def test_fuzzificacion_del_ejemplo_a_mano():
    assert difuso.fuzzificar(difuso.tiempo, 10) == pytest.approx(
        {"corto": 2 / 7, "medio": 0.2, "largo": 0.0})
    assert difuso.fuzzificar(difuso.errores, 4) == pytest.approx(
        {"pocos": 0.0, "algunos": 2 / 3, "muchos": 0.0})
    assert difuso.fuzzificar(difuso.ayudas, 1.5) == pytest.approx(
        {"pocas": 0.5, "algunas": 0.25, "muchas": 0.0})


def test_veto_por_muchas_ayudas():
    valor, etiqueta, _ = difuso.inferir(2, 0, 8)
    assert etiqueta == "novato"
    assert valor < 3


def test_todo_regular_da_intermedio():
    valor, etiqueta, _ = difuso.inferir(18, 5, 3)
    assert valor == pytest.approx(5.0, abs=0.01)
    assert etiqueta == "intermedio"


@pytest.mark.parametrize("entradas, esperado", [
    ((0, 0, 0), "avanzado"),          # el mejor caso
    ((60, 15, 10), "novato"),         # el peor caso
    ((60, 15, 0), "novato"),          # "me rindo" sin ayudas
])
def test_extremos(entradas, esperado):
    _, etiqueta, _ = difuso.inferir(*entradas)
    assert etiqueta == esperado


def test_recortar_lleva_las_entradas_a_su_universo():
    assert difuso.recortar(80, -1, 12) == (60.0, 0.0, 10.0)
    assert difuso.inferir(80, 20, 15)[0] == pytest.approx(difuso.inferir(60, 15, 10)[0])


def test_reglas_activadas_del_ejemplo_a_mano():
    activas = difuso.reglas_activadas(10, 4, 1.5)
    fuerzas = {r["regla"]: r["fuerza"] for r in activas}
    # R4: corto ∧ algunos ∧ pocas = min(0.286, 0.667, 0.5)
    assert fuerzas == pytest.approx({"R4": 0.286, "R5": 0.25, "R13": 0.2, "R14": 0.2})
    assert [r["fuerza"] for r in activas] == sorted(fuerzas.values(), reverse=True)


def test_tabla_fuzzificacion_tiene_una_fila_por_termino():
    filas = difuso.tabla_fuzzificacion(10, 4, 1.5)
    assert len(filas) == 9
    assert {f["variable"] for f in filas} == {"tiempo", "errores", "ayudas"}
