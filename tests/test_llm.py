"""Errores y prompts del LLM, con cadenas falsas: cero llamadas a Groq."""

import pytest
from langchain_core.exceptions import OutputParserException

from tutor import config, llm


class CadenaFalla:
    """Cadena de LangChain falsa cuyo ``invoke`` siempre lanza el error indicado."""

    def __init__(self, error):
        self.error = error

    def invoke(self, datos):
        raise self.error


@pytest.mark.parametrize("error, esperado", [
    (OutputParserException("JSON inválido"), llm.RespuestaInvalida),
    (TimeoutError("timeout"), llm.ErrorLLM),
    (ConnectionError("sin red"), llm.ErrorLLM),
])
def test_traduce_los_errores_del_proveedor(error, esperado):
    with pytest.raises(esperado):
        llm._invocar(CadenaFalla(error), {})


def test_respuesta_invalida_es_value_error_para_que_el_validador_reintente():
    assert issubclass(llm.RespuestaInvalida, ValueError)
    assert issubclass(llm.RespuestaInvalida, llm.ErrorLLM)
    assert not issubclass(llm.ErrorCuota, ValueError)        # la cuota no se reintenta


@pytest.mark.parametrize("nivel", config.NIVELES)
def test_el_prompt_lleva_los_criterios_del_nivel(nivel):
    criterios = llm.PROMPTS["problema"]["criterios"][nivel]
    texto = llm.PROMPT_PROBLEMA.format(**llm.datos_prompt_problema(nivel, ["Par o impar"]))
    assert f"nivel {nivel}" in texto
    assert all(valor in texto for valor in criterios.values())
    assert "No repitas estos problemas: Par o impar" in texto


def test_el_modelo_tiene_timeout():
    modelo = llm._crear_modelo(config.MODELO_CHAT, temperatura=0, max_tokens=10)
    assert modelo.request_timeout == config.TIMEOUT_LLM
