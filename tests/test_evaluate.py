import pytest

from extrator import evaluate, synthetic
from extrator.simulado import ExtratorSimulado


@pytest.fixture(scope="module")
def dados(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("dados")
    synthetic.gerar(n=15, n_defeitos=5, saida=pasta, seed=7)
    return pasta


def test_gera_pdfs_e_gabaritos(dados):
    assert len(list((dados / "pdf").glob("*.pdf"))) == 45
    assert len(list((dados / "gabarito").glob("*.json"))) == 15


def test_extrator_perfeito_acerta_tudo_e_pega_todos_os_defeitos(dados):
    r = evaluate.avaliar(dados, ExtratorSimulado(dados, taxa_erro=0.0))
    assert all(v == 1.0 for v in r["acerto_por_documento"].values())
    assert all(v == 1.0 for v in r["acerto_por_campo"].values())
    assert r["defeitos"] == {"injetados": 5, "detectados": 5}
    assert r["falsos_alarmes"] == 0
    assert r["conjuntos_com_erro_de_extracao"] == 0
    assert r["erros_silenciosos"] == 0


def test_extrator_com_ruido_perde_acerto_e_conta_erros_silenciosos(dados):
    r = evaluate.avaliar(dados, ExtratorSimulado(dados, taxa_erro=0.1, seed=3))
    assert min(r["acerto_por_campo"].values()) < 1.0
    assert all(v < 1.0 for v in r["acerto_por_documento"].values())
    assert r["conjuntos_com_erro_de_extracao"] > 0
    # erro que passa sem revisão nunca pode ser maior que o total de conjuntos com erro
    assert 0 <= r["erros_silenciosos"] <= r["conjuntos_com_erro_de_extracao"]


def test_achatar_e_normalizar():
    assert evaluate.achatar({"a": [{"b": "1"}], "c": 2}) == {"a[0].b": "1", "c": 2}
    assert evaluate._igual("1234.5", "1234.50")
    assert evaluate._igual("  ACME   Ltda ", "acme ltda")
    assert not evaluate._igual("1234.5", "1234.6")
