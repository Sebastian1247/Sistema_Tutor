"""Conceptos del dominio: el problema, sus casos de prueba y el resultado de resolverlo.

Problema y CasoPrueba también son el "contrato" que el LLM está obligado a
devolver: las descripciones de los campos se envían en el esquema JSON.
"""

from dataclasses import dataclass

from pydantic import BaseModel, Field


class CasoPrueba(BaseModel):
    entrada: str = Field(description="Texto que recibe el programa por input(). "
                                     "Si son varias líneas, sepáralas con \\n")
    salida: str = Field(description="Texto EXACTO que imprime una solución correcta")


class Problema(BaseModel):
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
    """Decisión del sistema difuso al terminar un problema."""
    resuelto: bool
    tiempo: float           # min (60 si se rindió)
    errores: int
    ayudas: int
    valor: float            # salida nítida (centroide) en [0, 10]
    recomendado: str        # nivel que sugiere el sistema difuso
    siguiente: str          # nivel del próximo problema (máximo un escalón)

    def fila_historial(self, titulo, nivel):
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
