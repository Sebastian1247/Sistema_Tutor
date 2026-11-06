"""Pruebas del banco local de problemas."""

import pytest

from tutor import banco, config, ejecutor, validador

PROBLEMAS = [(nivel, p) for nivel, lista in banco.cargar_banco().items() for p in lista]


def test_al_menos_cinco_problemas_por_nivel():
    banco_completo = banco.cargar_banco()
    assert set(banco_completo) == set(config.NIVELES)
    assert all(len(banco_completo[nivel]) >= 5 for nivel in config.NIVELES)


def test_titulos_unicos():
    titulos = [p.titulo for _, p in PROBLEMAS]
    assert len(titulos) == len(set(titulos))


@pytest.mark.parametrize("nivel, problema", PROBLEMAS, ids=[p.titulo for _, p in PROBLEMAS])
def test_cada_problema_pasa_el_validador_sin_correcciones(nivel, problema):
    copia = problema.model_copy(deep=True)
    _, correcciones = validador.validar_problema(copia)
    assert correcciones == []                        # las salidas esperadas son correctas
    assert 3 <= len(copia.casos_prueba) <= 5


@pytest.mark.parametrize("nivel, problema", PROBLEMAS, ids=[p.titulo for _, p in PROBLEMAS])
def test_el_codigo_inicial_no_resuelve_el_problema(nivel, problema):
    resultados = ejecutor.evaluar_pruebas(problema.codigo_inicial, problema.casos_prueba)
    assert not all(r["paso"] for r in resultados)


def test_no_repite_problemas_de_la_sesion():
    vistos = []
    for _ in range(5):
        vistos.append(banco.problema_del_banco("novato", vistos).titulo)
    assert len(set(vistos)) == 5


def test_si_ya_se_vieron_todos_repite_uno():
    todos = [p.titulo for p in banco.cargar_banco()["avanzado"]]
    assert banco.problema_del_banco("avanzado", todos).titulo in todos


def test_regresa_una_copia():
    problema = banco.problema_del_banco("intermedio")
    problema.titulo = "modificado"
    assert "modificado" not in [p.titulo for p in banco.cargar_banco()["intermedio"]]
