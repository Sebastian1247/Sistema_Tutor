"""Respaldo con el banco local, de punta a punta en la interfaz (AppTest, sin Groq)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tutor import banco, llm

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.mark.parametrize("error, motivo", [
    (llm.ErrorCuota("429"), "límite del plan gratuito"),
    (llm.ErrorLLM("sin conexión"), "No hubo conexión"),
    (llm.RespuestaInvalida("json_validate_failed"), "no generó un problema válido"),
])
def test_sin_llm_se_usa_el_banco_local(monkeypatch, error, motivo):
    def generar_falla(nivel, titulos_previos=()):
        raise error

    monkeypatch.setattr(llm, "generar_problema", generar_falla)
    at = AppTest.from_file(APP, default_timeout=60).run()
    next(b for b in at.button if "Generar" in b.label).click().run()

    titulos_banco = [p.titulo for p in banco.cargar_banco()["novato"]]
    assert at.session_state.problema.titulo in titulos_banco
    assert motivo in at.session_state.aviso_generacion
    assert any(motivo in i.value for i in at.info)
    assert at.session_state.error_llm is None
    assert not at.exception
