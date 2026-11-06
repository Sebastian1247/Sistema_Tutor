"""Modelos del dominio: el problema, sus casos de prueba y el resultado.

``Problema`` y ``CasoPrueba`` también son el contrato que el LLM está obligado
a cumplir: las descripciones de sus campos se envían como esquema JSON en la
salida estructurada (ver ``tutor.llm``).
"""

from dataclasses import dataclass

from pydantic import BaseModel, Field


class CasoPrueba(BaseModel):
    """Un caso de prueba: lo que recibe el programa y lo que debe imprimir."""

    entrada: str = Field(description="Texto que recibe el programa por input(). "
                                     "Si son varias líneas, sepáralas con \\n")
    salida: str = Field(description="Texto EXACTO que imprime una solución correcta")


class Problema(BaseModel):
    """Un problema de programación con su solución de referencia."""

    titulo: str = Field(description="Título corto del problema")
    descripcion: str = Field(description="SOLO el enunciado del problema, en español y en "
                                         "Markdown. NO incluyas secciones de entrada, salida "
                                         "ni ejemplos: esos van en sus propios campos")
    formato_entrada: str = Field(description="Qué datos recibe el programa, línea por línea")
    formato_salida: str = Field(description="Qué debe imprimir exactamente")
    ejemplo_entrada: str = Field(description="Ejemplo de entrada")
    ejemplo_salida: str = Field(description="Salida correspondiente al ejemplo")
    casos_prueba: list[CasoPrueba] = Field(description="Entre 3 y 5 casos; al menos uno límite")
    codigo_inicial: str = Field(description="Plantilla mínima en Python, SIN la solución")
    solucion: str = Field(description="Solución completa de referencia en Python. "
                                      "No se muestra al estudiante")


@dataclass
class Resultado:
    """Decisión del sistema difuso al terminar un problema.

    Attributes:
        resuelto: True si el estudiante pasó todos los casos; False si se rindió.
        tiempo: Minutos usados (``TIEMPO_MAXIMO`` si se rindió).
        errores: Errores contados (al menos ``ERRORES_MAXIMOS`` si se rindió).
        ayudas: Preguntas que respondió el tutor.
        valor: Salida nítida de la inferencia (centroide), entre 0 y 10.
        recomendado: Nivel que corresponde a ``valor``.
        siguiente: Nivel del próximo problema (máximo un escalón de diferencia).
    """

    resuelto: bool
    tiempo: float
    errores: int
    ayudas: int
    valor: float
    recomendado: str
    siguiente: str

    def fila_historial(self, titulo, nivel):
        """Convierte el resultado en una fila de la tabla del historial.

        Args:
            titulo: Título del problema terminado.
            nivel: Nivel con el que se planteó el problema.

        Returns:
            Diccionario con una columna por dato, listo para ``st.dataframe``.
        """
        return {
            "problema": titulo,
            "nivel": nivel,
            "resuelto": "sí" if self.resuelto else "no",
            "tiempo (min)": round(self.tiempo, 1),
            "errores": self.errores,
            "ayudas": self.ayudas,
            "salida difusa": round(self.valor, 2),
            "recomendado": self.recomendado,
            "siguiente": self.siguiente,
        }
