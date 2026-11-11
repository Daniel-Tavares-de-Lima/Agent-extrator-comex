import random
from datetime import date
from decimal import Decimal

from extrator.schemas import BillOfLading, Conteiner, Invoice, ItemInvoice, ItemPacking, PackingList
from extrator.synthetic import gerar_conjunto
from extrator.validators import (
    conteiner_valido, digito_iso6346, status, validar_bl, validar_conjunto,
    validar_invoice, validar_packing_list,
)


def _codigos(ps):
    return {p.codigo for p in ps}


def test_digito_iso6346_com_numero_conhecido():
    # CSQU3054383 é o exemplo da própria norma ISO 6346
    assert digito_iso6346("CSQU305438") == 3
    assert conteiner_valido("CSQU3054383") == (True, "")
    assert conteiner_valido("CSQU 305438-3") == (True, "")  # com espaço e hífen
    assert conteiner_valido("CSQU3054384") == (False, "DIGITO")
    assert conteiner_valido("CSQ3054383") == (False, "FORMATO")


def _invoice(total_geral="30.00", total_item="30.00"):
    return Invoice(
        numero="INV-1", data=date(2026, 1, 2), exportador="A", importador="B", incoterm="FOB",
        moeda="USD", total_geral=Decimal(total_geral),
        itens=[ItemInvoice(descricao="x", quantidade=Decimal(3), unidade="PCS",
                           preco_unitario=Decimal("10.00"), total=Decimal(total_item))],
    )


def test_invoice_correta_nao_tem_problema():
    assert validar_invoice(_invoice()) == []


def test_invoice_total_geral_errado():
    assert _codigos(validar_invoice(_invoice(total_geral="130.00"))) == {"TOTAL_GERAL_DIVERGENTE"}


def test_invoice_total_do_item_errado():
    assert "ITEM_TOTAL_INCONSISTENTE" in _codigos(validar_invoice(_invoice(total_item="31.00")))


def test_invoice_arredondamento_de_centavo_passa():
    inv = Invoice(
        numero="INV-1", data=date(2026, 1, 2), exportador="A", importador="B", incoterm="CIF",
        moeda="USD", total_geral=Decimal("123.46"),
        itens=[ItemInvoice(descricao="x", quantidade=Decimal(100), unidade="PCS",
                           preco_unitario=Decimal("1.2345"), total=Decimal("123.46"))],
    )
    assert validar_invoice(inv) == []


def test_packing_list_liquido_maior_que_bruto():
    pl = PackingList(
        invoice_numero="INV-1", volumes=1, peso_bruto_kg=Decimal(10), peso_liquido_kg=Decimal(12),
        cubagem_m3=Decimal(1), itens=[ItemPacking(descricao="x", quantidade=Decimal(1), peso_liquido_kg=Decimal(12))],
    )
    assert _codigos(validar_packing_list(pl)) == {"PESO_LIQUIDO_MAIOR_QUE_BRUTO"}


def test_bl_conteiner_duplicado_e_digito():
    bl = BillOfLading(
        numero="B1", armador="a", navio="n", data_embarque=date(2026, 1, 2), porto_carga="p",
        porto_descarga="q", embarcador="e", consignee="c", notify="c", volumes=1,
        peso_bruto_kg=Decimal(1),
        conteineres=[Conteiner(numero="CSQU3054383", lacre="1"), Conteiner(numero="CSQU3054383", lacre="2"),
                     Conteiner(numero="CSQU3054384", lacre="3")],
    )
    assert _codigos(validar_bl(bl)) == {"CONTEINER_DUPLICADO", "CONTEINER_DIGITO_INVALIDO"}


def test_conjunto_limpo_gerado_passa_sem_nenhum_erro():
    """Se o gerador e os validadores discordam, esse teste quebra."""
    rng = random.Random(1)
    for _ in range(50):
        g = gerar_conjunto(rng)
        ps = validar_conjunto(Invoice(**g["invoice"]), PackingList(**g["packing_list"]), BillOfLading(**g["bl"]))
        assert status(ps) == "ok", ps


def test_cada_defeito_injetado_e_acusado():
    from extrator.synthetic import DEFEITOS
    rng = random.Random(2)
    for defeito, codigo in DEFEITOS.items():
        for _ in range(20):
            g = gerar_conjunto(rng, defeito)
            ps = validar_conjunto(Invoice(**g["invoice"]), PackingList(**g["packing_list"]), BillOfLading(**g["bl"]))
            assert codigo in _codigos(ps), (defeito, ps)
            assert status(ps) == "revisar"
