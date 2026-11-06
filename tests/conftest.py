import pytest

from tutor.modelos import CasoPrueba, Problema

SOLUCION_PARES = (
    "n = input().strip()\n"
    "print(sum(1 for d in n if int(d) % 2 == 0))\n"
)


def crear_problema(solucion=SOLUCION_PARES, casos=None, ejemplo=("48392", "3")):
    """Problema armado a mano: así las pruebas no dependen del LLM."""
    if casos is None:
        casos = [("48392", "3"), ("13579", "0"), ("0", "1")]
    return Problema(
        titulo="Dígitos pares",
        descripcion="Cuenta cuántos dígitos pares tiene un número.",
        formato_entrada="Un entero positivo",
        formato_salida="La cantidad de dígitos pares",
        ejemplo_entrada=ejemplo[0],
        ejemplo_salida=ejemplo[1],
        casos_prueba=[CasoPrueba(entrada=e, salida=s) for e, s in casos],
        codigo_inicial="n = input()\n",
        solucion=solucion,
    )


@pytest.fixture
def problema():
    return crear_problema()
