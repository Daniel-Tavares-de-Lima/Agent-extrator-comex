"""Gera conjuntos sintéticos (invoice + packing list + BL) em PDF, com gabarito em JSON.

Todos os nomes são fictícios. Alguns conjuntos saem com um defeito injetado de
propósito (total errado, dígito de contêiner errado...) para testar os validadores.
"""
import json
import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .schemas import BillOfLading, Conteiner, Invoice, ItemInvoice, ItemPacking, PackingList
from .validators import digito_iso6346

CENTAVO = Decimal("0.01")

EXPORTADORES = [
    "Shenzhen Exemplo Electronics Co., Ltd.",
    "Guangzhou Modelo Trading Co., Ltd.",
    "Ningbo Ficticio Machinery Co., Ltd.",
    "Hamburg Beispiel Maschinen GmbH",
    "Milano Esempio Tessuti S.r.l.",
]
IMPORTADORES = ["Importadora Exemplo Ltda", "Comercial Modelo S.A.", "Distribuidora Ficticia Ltda"]
PRODUTOS = [
    ("LED panel light 40W", "PCS", 3.5, 9.0),
    ("Stainless steel valve DN50", "PCS", 12.0, 40.0),
    ("Cotton fabric 150 g/m2", "MTR", 1.2, 3.8),
    ("Hydraulic hose 1/2 inch", "MTR", 0.9, 4.5),
    ("Electric motor 1.5 kW", "PCS", 45.0, 120.0),
    ("Plastic injection mold part", "PCS", 6.0, 22.0),
    ("Lithium battery pack 12V", "PCS", 15.0, 38.0),
    ("Ceramic tile 60x60", "SQM", 4.0, 9.5),
]
ARMADORES = ["Oceano Azul Lines", "Atlantico Sul Shipping", "Meridian Container Line"]
NAVIOS = ["OA PIONEER", "ATLANTICO STAR", "MERIDIAN SPIRIT", "SUL HORIZON"]
PORTOS_CARGA = ["Shanghai", "Ningbo", "Shenzhen", "Hamburg", "Genoa"]
PORTOS_DESCARGA = ["Suape", "Santos", "Itapoa"]
PREFIXOS_CONTEINER = ["XYZU", "DEMU", "TSTU"]
INCOTERMS = ["FOB", "CFR", "CIF", "EXW", "FCA"]

# defeito injetado -> código que o validador tem que acusar
DEFEITOS = {
    "total_geral": "TOTAL_GERAL_DIVERGENTE",
    "digito_conteiner": "CONTEINER_DIGITO_INVALIDO",
    "peso_bl": "PESO_BRUTO_DIVERGENTE",
    "invoice_citada": "PL_INVOICE_DIVERGENTE",
    "liquido_maior": "PESO_LIQUIDO_MAIOR_QUE_BRUTO",
}


def _dec(x: float | Decimal) -> Decimal:
    return Decimal(str(x)).quantize(CENTAVO, ROUND_HALF_UP)


def _numero_conteiner(rng: random.Random) -> str:
    prefixo = rng.choice(PREFIXOS_CONTEINER) + f"{rng.randint(0, 999999):06d}"
    return prefixo + str(digito_iso6346(prefixo))


def gerar_conjunto(rng: random.Random, defeito: str | None = None) -> dict:
    """Devolve o gabarito: três documentos (dict JSON) e os códigos esperados dos validadores."""
    exportador = rng.choice(EXPORTADORES)
    importador = rng.choice(IMPORTADORES)
    num = rng.randint(1000, 9999)
    data_inv = date(2026, 1, 1) + timedelta(days=rng.randint(0, 300))

    itens, itens_pl = [], []
    for desc, un, pmin, pmax in rng.sample(PRODUTOS, rng.randint(2, 4)):
        qtd = rng.randint(50, 2000)
        preco = _dec(rng.uniform(pmin, pmax))
        itens.append(ItemInvoice(
            descricao=desc, quantidade=Decimal(qtd), unidade=un,
            preco_unitario=preco, total=_dec(Decimal(qtd) * preco),
        ))
        itens_pl.append(ItemPacking(
            descricao=desc, quantidade=Decimal(qtd),
            peso_liquido_kg=_dec(rng.uniform(0.2, 3.0) * qtd),
        ))

    total_geral = sum((i.total for i in itens), Decimal("0"))
    liquido = sum((i.peso_liquido_kg for i in itens_pl), Decimal("0"))
    bruto = _dec(liquido * Decimal("1.12") + 150)
    invoice_citada = f"INV-{num}"

    if defeito == "total_geral":
        total_geral += Decimal("100.00")
    if defeito == "invoice_citada":
        invoice_citada = f"INV-{num + 1}"
    if defeito == "liquido_maior":
        bruto = _dec(liquido - 10)

    invoice = Invoice(
        numero=f"INV-{num}", data=data_inv, exportador=exportador, importador=importador,
        incoterm=rng.choice(INCOTERMS), moeda="USD", itens=itens, total_geral=total_geral,
    )
    volumes = rng.randint(10, 300)
    pl = PackingList(
        invoice_numero=invoice_citada, volumes=volumes, peso_bruto_kg=bruto,
        peso_liquido_kg=liquido, cubagem_m3=_dec(rng.uniform(5, 60)), itens=itens_pl,
    )

    conteineres = []
    for _ in range(rng.randint(1, 3)):
        numero = _numero_conteiner(rng)
        if defeito == "digito_conteiner" and not conteineres:
            numero = numero[:-1] + str((int(numero[-1]) + 1) % 10)
        conteineres.append(Conteiner(numero=numero, lacre=f"SL{rng.randint(100000, 999999)}"))

    peso_bl = bruto * Decimal("1.05") if defeito == "peso_bl" else bruto
    bl = BillOfLading(
        numero=f"OAL{rng.randint(10000000, 99999999)}",
        armador=rng.choice(ARMADORES), navio=rng.choice(NAVIOS),
        data_embarque=data_inv + timedelta(days=rng.randint(3, 20)),
        porto_carga=rng.choice(PORTOS_CARGA), porto_descarga=rng.choice(PORTOS_DESCARGA),
        embarcador=exportador, consignee=importador, notify=importador,
        volumes=volumes, peso_bruto_kg=_dec(peso_bl), conteineres=conteineres,
    )

    return {
        "invoice": invoice.model_dump(mode="json"),
        "packing_list": pl.model_dump(mode="json"),
        "bl": bl.model_dump(mode="json"),
        "defeito": defeito,
        "problemas_esperados": [DEFEITOS[defeito]] if defeito else [],
    }


# ---------- PDF ----------
def _num(valor: str, lang: str) -> str:
    """Formata 1234.5 como '1,234.50' (en) ou '1.234,50' (pt)."""
    texto = f"{Decimal(valor):,.2f}"
    if lang == "pt":
        texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return texto


def _data(iso: str, lang: str) -> str:
    d = date.fromisoformat(iso)
    return d.strftime("%d/%m/%Y") if lang == "pt" else d.strftime("%b %d, %Y")


def _pdf(caminho: Path, titulo: str, linhas: list[str]) -> None:
    c = canvas.Canvas(str(caminho), pagesize=A4)
    _, altura = A4
    y = altura - 60
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, titulo)
    c.setFont("Helvetica", 10)
    y -= 30
    for linha in linhas:
        if y < 60:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = altura - 60
        c.drawString(50, y, linha)
        y -= 15
    c.save()


def renderizar(gab: dict, pasta: Path, id_: str, lang: str) -> None:
    inv, pl, bl = gab["invoice"], gab["packing_list"], gab["bl"]
    rot = {
        "en": dict(inv="COMMERCIAL INVOICE", no="Invoice No", dt="Date", ex="Exporter", im="Importer",
                   it="Terms", cur="Currency", tot="TOTAL", pl="PACKING LIST", vol="Packages",
                   gw="Gross weight (kg)", nw="Net weight (kg)", cbm="Volume (m3)", bl="BILL OF LADING"),
        "pt": dict(inv="FATURA COMERCIAL", no="Fatura nº", dt="Data", ex="Exportador", im="Importador",
                   it="Condição", cur="Moeda", tot="TOTAL", pl="ROMANEIO", vol="Volumes",
                   gw="Peso bruto (kg)", nw="Peso líquido (kg)", cbm="Cubagem (m3)", bl="CONHECIMENTO DE EMBARQUE"),
    }[lang]

    l = [f"{rot['no']}: {inv['numero']}", f"{rot['dt']}: {_data(inv['data'], lang)}",
         f"{rot['ex']}: {inv['exportador']}", f"{rot['im']}: {inv['importador']}",
         f"{rot['it']}: {inv['incoterm']}    {rot['cur']}: {inv['moeda']}", "",
         "Description | Qty | Unit | Unit price | Amount"]
    for it in inv["itens"]:
        l.append(f"{it['descricao']} | {_num(it['quantidade'], lang)} | {it['unidade']} | "
                 f"{_num(it['preco_unitario'], lang)} | {_num(it['total'], lang)}")
    l += ["", f"{rot['tot']}: {inv['moeda']} {_num(inv['total_geral'], lang)}"]
    _pdf(pasta / f"{id_}_invoice.pdf", rot["inv"], l)

    l = [f"Invoice: {pl['invoice_numero']}", f"{rot['vol']}: {pl['volumes']}",
         f"{rot['gw']}: {_num(pl['peso_bruto_kg'], lang)}", f"{rot['nw']}: {_num(pl['peso_liquido_kg'], lang)}",
         f"{rot['cbm']}: {_num(pl['cubagem_m3'], lang)}", "", "Description | Qty | Net weight (kg)"]
    for it in pl["itens"]:
        l.append(f"{it['descricao']} | {_num(it['quantidade'], lang)} | {_num(it['peso_liquido_kg'], lang)}")
    _pdf(pasta / f"{id_}_packing_list.pdf", rot["pl"], l)

    l = [f"B/L No: {bl['numero']}", f"Carrier: {bl['armador']}", f"Vessel: {bl['navio']}",
         f"Shipped on board: {_data(bl['data_embarque'], lang)}",
         f"Port of loading: {bl['porto_carga']}", f"Port of discharge: {bl['porto_descarga']}",
         f"Shipper: {bl['embarcador']}", f"Consignee: {bl['consignee']}", f"Notify: {bl['notify']}",
         f"{rot['vol']}: {bl['volumes']}", f"{rot['gw']}: {_num(bl['peso_bruto_kg'], lang)}", "",
         "Container | Seal"]
    for c in bl["conteineres"]:
        l.append(f"{c['numero']} | {c['lacre']}")
    _pdf(pasta / f"{id_}_bl.pdf", rot["bl"], l)


def gerar(n: int, n_defeitos: int, saida: Path, seed: int = 42) -> list[str]:
    """Gera n conjuntos; os últimos n_defeitos saem com um defeito injetado."""
    pdfs, gabs = saida / "pdf", saida / "gabarito"
    pdfs.mkdir(parents=True, exist_ok=True)
    gabs.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    tipos_defeito = list(DEFEITOS)
    ids = []
    for i in range(n):
        defeito = tipos_defeito[i % len(tipos_defeito)] if i >= n - n_defeitos else None
        gab = gerar_conjunto(rng, defeito)
        id_ = f"S{i + 1:03d}"
        renderizar(gab, pdfs, id_, "pt" if i % 2 else "en")
        (gabs / f"{id_}.json").write_text(json.dumps(gab, ensure_ascii=False, indent=2), encoding="utf-8")
        ids.append(id_)
    return ids
