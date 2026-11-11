import json

from pypdf import PdfReader

from extrator import evaluate, sujo
from extrator.simulado import ExtratorSimulado


def _texto(caminho) -> str:
    return "".join(p.extract_text() or "" for p in PdfReader(str(caminho)).pages)


def test_gera_tres_variantes_com_gabarito(tmp_path):
    ids = sujo.gerar_sujo(2, tmp_path, seed=1)
    assert ids == ["T001", "T002", "L001", "L002", "P001", "P002"]
    for id_ in ids:
        gab = json.loads((tmp_path / "gabarito" / f"{id_}.json").read_text(encoding="utf-8"))
        assert gab["variante"] in sujo.VARIANTES
        for tipo in ("invoice", "packing_list", "bl"):
            assert (tmp_path / "pdf" / f"{id_}_{tipo}.pdf").stat().st_size > 0
    # só o último de cada variante leva defeito
    defeitos = [json.loads((tmp_path / "gabarito" / f"{i}.json").read_text(encoding="utf-8"))["defeito"] for i in ids]
    assert [d is not None for d in defeitos] == [False, True, False, True, False, True]


def test_tabela_tem_texto_com_os_valores_e_scan_nao_tem(tmp_path):
    sujo.gerar_sujo(1, tmp_path, seed=1)
    gab = json.loads((tmp_path / "gabarito" / "T001.json").read_text(encoding="utf-8"))
    texto = _texto(tmp_path / "pdf" / "T001_invoice.pdf")
    assert gab["invoice"]["numero"] in texto and gab["invoice"]["exportador"] in texto
    assert "Customer PO" in texto  # campo que não está no schema
    for id_ in ("L001", "P001"):
        for tipo in ("invoice", "packing_list", "bl"):
            assert _texto(tmp_path / "pdf" / f"{id_}_{tipo}.pdf").strip() == ""


def test_geracao_e_reprodutivel(tmp_path):
    sujo.gerar_sujo(1, tmp_path / "a", seed=5)
    sujo.gerar_sujo(1, tmp_path / "b", seed=5)
    for arq in (tmp_path / "a" / "gabarito").glob("*.json"):
        assert arq.read_bytes() == (tmp_path / "b" / "gabarito" / arq.name).read_bytes()


def test_avaliar_separa_resultado_por_variante(tmp_path):
    sujo.gerar_sujo(1, tmp_path, seed=1)
    r = evaluate.avaliar(tmp_path, ExtratorSimulado(tmp_path, 0.0))
    assert set(r["por_variante"]) == set(sujo.VARIANTES)
    assert all(v["conjuntos"] == 1 and v["corretos"] == 1 for v in r["por_variante"].values())
    assert "## Por tipo de PDF" in evaluate.formatar_markdown(r, "x")
