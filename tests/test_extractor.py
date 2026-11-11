from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from extrator.erros import ExtracaoErro
from extrator.extractor import ExtratorClaude
from extrator.schemas import Invoice


class ClienteFalso:
    """Imita client.messages.parse devolvendo respostas ou erros em sequência."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []
        self.messages = SimpleNamespace(parse=self._parse)

    def _parse(self, **kwargs):
        self.chamadas.append(kwargs)
        r = self.respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def _pdf(tmp_path: Path) -> Path:
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF-1.4 teste")
    return p


def _resp(parsed, stop="end_turn"):
    return SimpleNamespace(parsed_output=parsed, stop_reason=stop)


def _erro_validacao() -> ValidationError:
    try:
        Invoice.model_validate({})
    except ValidationError as e:
        return e


def test_envia_pdf_e_devolve_objeto(tmp_path):
    obj = object()
    cliente = ClienteFalso([_resp(obj)])
    out = ExtratorClaude(client=cliente)(_pdf(tmp_path), "invoice")
    assert out is obj
    chamada = cliente.chamadas[0]
    conteudo = chamada["messages"][0]["content"]
    assert conteudo[0]["type"] == "document"
    assert conteudo[0]["source"]["media_type"] == "application/pdf"
    assert chamada["output_format"] is Invoice


def test_tenta_de_novo_quando_validacao_falha(tmp_path):
    obj = object()
    cliente = ClienteFalso([_erro_validacao(), _resp(obj)])
    out = ExtratorClaude(client=cliente)(_pdf(tmp_path), "invoice")
    assert out is obj
    assert len(cliente.chamadas) == 2
    assert "não passou na validação" in cliente.chamadas[1]["messages"][0]["content"][-1]["text"]


def test_desiste_depois_das_tentativas(tmp_path):
    cliente = ClienteFalso([_erro_validacao(), _erro_validacao()])
    with pytest.raises(ValidationError):
        ExtratorClaude(client=cliente)(_pdf(tmp_path), "invoice")
    assert len(cliente.chamadas) == 2


@pytest.mark.parametrize("stop", ["refusal", "max_tokens"])
def test_recusa_e_corte_viram_erro(tmp_path, stop):
    cliente = ClienteFalso([_resp(None, stop)])
    with pytest.raises(ExtracaoErro):
        ExtratorClaude(client=cliente)(_pdf(tmp_path), "invoice")
