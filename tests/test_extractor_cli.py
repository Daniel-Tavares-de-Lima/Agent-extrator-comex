import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from extrator import extractor_cli
from extrator.erros import ExtracaoErro, LimiteDeUso
from extrator.extractor_cli import ExtratorClaudeCode

INVOICE_OK = {
    "numero": "INV-1", "data": "2026-01-02", "exportador": "A", "importador": "B", "incoterm": "FOB",
    "moeda": "USD", "total_geral": 30,
    "itens": [{"descricao": "x", "quantidade": 3, "unidade": "PCS", "preco_unitario": 10, "total": 30}],
}


def _saida(**campos):
    d = {"is_error": False, "total_cost_usd": 0.03, "structured_output": INVOICE_OK}
    d.update(campos)
    return SimpleNamespace(stdout=json.dumps(d), stderr="", returncode=0)


@pytest.fixture
def pdf(tmp_path):
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF-1.4")
    return p


def _extrator(monkeypatch, respostas, chamadas=None, **kwargs_extrator):
    fila = list(respostas)
    ex = ExtratorClaudeCode(executavel="claude-falso", **kwargs_extrator)
    ex.kws = []  # argumentos nomeados de cada subprocess.run (para conferir o `input`)

    def falso(cmd, **kw):
        if chamadas is not None:
            chamadas.append(cmd)
        ex.kws.append(kw)
        r = fila.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(extractor_cli.subprocess, "run", falso)
    return ex


def test_devolve_objeto_validado_e_soma_custo(monkeypatch, pdf):
    chamadas = []
    ex = _extrator(monkeypatch, [_saida()], chamadas)
    inv = ex(pdf, "invoice")
    assert inv.numero == "INV-1" and str(inv.total_geral) == "30"
    assert ex.chamadas == 1 and ex.custo_lista_usd == pytest.approx(0.03)
    cmd = chamadas[0]
    # as opções que enxugam o consumo precisam estar presentes
    for flag in ("--strict-mcp-config", "--disable-slash-commands", "--tools", "--json-schema"):
        assert flag in cmd


TEXTO_LONGO = "Fatura nº INV-1 " * 10


def test_modo_auto_usa_texto_sem_ferramentas(monkeypatch, pdf):
    monkeypatch.setattr(extractor_cli, "_texto_pdf", lambda p: TEXTO_LONGO)
    chamadas = []
    ex = _extrator(monkeypatch, [_saida()], chamadas)
    assert ex(pdf, "invoice").numero == "INV-1"
    cmd = chamadas[0]
    assert cmd[1] == "-p" and cmd[2] == "--output-format"  # o prompt não vai como argumento
    assert cmd[cmd.index("--tools") + 1] == ""  # nenhuma ferramenta
    assert "--allowedTools" not in cmd
    assert TEXTO_LONGO in ex.kws[0]["input"]


def test_modo_auto_sem_texto_cai_para_leitura_do_pdf(monkeypatch, pdf):
    monkeypatch.setattr(extractor_cli, "_texto_pdf", lambda p: "")
    chamadas = []
    ex = _extrator(monkeypatch, [_saida()], chamadas)
    ex(pdf, "invoice")
    cmd = chamadas[0]
    assert cmd[cmd.index("--tools") + 1] == "Read"
    assert ex.kws[0]["input"] is None


def test_modo_texto_recusa_pdf_sem_texto(monkeypatch, pdf):
    monkeypatch.setattr(extractor_cli, "_texto_pdf", lambda p: "")
    ex = _extrator(monkeypatch, [], modo="texto")
    with pytest.raises(ExtracaoErro):
        ex(pdf, "invoice")


def test_padrao_e_haiku_com_esforco_baixo(monkeypatch, pdf):
    chamadas = []
    ex = _extrator(monkeypatch, [_saida()], chamadas)
    ex(pdf, "invoice")
    cmd = chamadas[0]
    assert cmd[cmd.index("--model") + 1] == "haiku"
    assert cmd[cmd.index("--effort") + 1] == "low"


def test_modelo_e_esforco_podem_ser_trocados_ou_omitidos(monkeypatch, pdf):
    chamadas = []
    ex = _extrator(monkeypatch, [_saida()], chamadas, modelo=None, esforco=None)
    ex(pdf, "invoice")
    assert "--model" not in chamadas[0] and "--effort" not in chamadas[0]


def test_modo_invalido():
    with pytest.raises(ValueError):
        ExtratorClaudeCode(executavel="x", modo="qualquer")


def test_resumo_de_tokens_tem_media_e_mediana(monkeypatch, pdf):
    def com_uso(n):
        return _saida(usage={"input_tokens": 0, "cache_creation_input_tokens": n,
                             "cache_read_input_tokens": 0, "output_tokens": 0})
    ex = _extrator(monkeypatch, [com_uso(1000), com_uso(2000), com_uso(6000)])
    for _ in range(3):
        ex(pdf, "invoice")
    r = ex.resumo_tokens()
    assert r["chamadas"] == 3 and r["media"] == 3000 and r["mediana"] == 2000
    assert r["minimo"] == 1000 and r["maximo"] == 6000 and r["total"] == 9000


def test_usa_result_quando_nao_ha_structured_output(monkeypatch, pdf):
    ex = _extrator(monkeypatch, [_saida(structured_output=None, result=json.dumps(INVOICE_OK))])
    assert ex(pdf, "invoice").numero == "INV-1"


def test_tenta_de_novo_quando_validacao_falha(monkeypatch, pdf):
    ruim = dict(INVOICE_OK, incoterm="XXX")
    chamadas = []
    ex = _extrator(monkeypatch, [_saida(structured_output=ruim), _saida()], chamadas)
    assert ex(pdf, "invoice").numero == "INV-1"
    assert "não passou na validação" in chamadas[1][2]


def test_desiste_depois_das_tentativas(monkeypatch, pdf):
    ruim = dict(INVOICE_OK, incoterm="XXX")
    ex = _extrator(monkeypatch, [_saida(structured_output=ruim), _saida(structured_output=ruim)])
    with pytest.raises(ValidationError):
        ex(pdf, "invoice")


def test_limite_de_uso_para_tudo(monkeypatch, pdf):
    ex = _extrator(monkeypatch, [_saida(is_error=True, result="Usage limit reached", structured_output=None)])
    with pytest.raises(LimiteDeUso):
        ex(pdf, "invoice")


def test_erro_generico_vira_extracao_erro(monkeypatch, pdf):
    ex = _extrator(monkeypatch, [_saida(is_error=True, result="algo deu errado", structured_output=None)])
    with pytest.raises(ExtracaoErro):
        ex(pdf, "invoice")


def test_saida_que_nao_e_json_vira_extracao_erro(monkeypatch, pdf):
    ex = _extrator(monkeypatch, [SimpleNamespace(stdout="lixo", stderr="boom", returncode=1)])
    with pytest.raises(ExtracaoErro):
        ex(pdf, "invoice")
