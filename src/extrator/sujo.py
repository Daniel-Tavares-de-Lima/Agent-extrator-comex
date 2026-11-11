"""Gera conjuntos "sujos": layout de documento de verdade e PDF escaneado (só imagem).

Usa os mesmos dados e o mesmo gabarito de `synthetic`, mas desenha o documento como
uma folha com caixas, tabelas com grade, colunas e campos que não estão no schema
(dados bancários, PO, voyage...). Nas versões escaneadas a folha vira imagem, com
rotação, ruído, desfoque e carimbo, e o PDF fica sem camada de texto.
"""
import io
import json
import random
from datetime import date, timedelta
from pathlib import Path

import reportlab
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .synthetic import DEFEITOS, _data, _num, gerar_conjunto

LARGURA, ALTURA = A4
FONTES = Path(reportlab.__file__).parent / "fonts"

# prefixo do id -> configuração. Sem "dpi" = PDF com texto (tabela); com "dpi" = escaneado.
VARIANTES: dict[str, dict] = {
    "tabela": {"prefixo": "T"},
    "scan_leve": {"prefixo": "L", "dpi": 150, "rotacao": 1.0, "ruido": 10, "blur": 0.4,
                  "contraste": 0.95, "jpeg": 70, "sombra": 235, "carimbo": False},
    "scan_pesado": {"prefixo": "P", "dpi": 100, "rotacao": 2.5, "ruido": 28, "blur": 0.9,
                    "contraste": 0.8, "jpeg": 40, "sombra": 200, "carimbo": True},
}

ROT = {
    "en": dict(inv="COMMERCIAL INVOICE", orig="ORIGINAL", ex="Exporter / Seller", no="Invoice No.",
               dt="Date", im="Importer / Consignee", it="Terms of delivery", cur="Currency",
               desc="Description", qty="Quantity", un="Unit", pu="Unit price", amt="Amount",
               tot="TOTAL", pl="PACKING LIST", refinv="Ref. Invoice", vol="Packages",
               gw="Gross weight (kg)", nw="Net weight (kg)", cbm="Volume (m3)", cartons="Cartons"),
    "pt": dict(inv="FATURA COMERCIAL", orig="ORIGINAL", ex="Exportador / Vendedor", no="Fatura nº",
               dt="Data", im="Importador / Comprador", it="Condição de entrega", cur="Moeda",
               desc="Descrição", qty="Quantidade", un="Un.", pu="Preço unit.", amt="Valor",
               tot="TOTAL", pl="ROMANEIO", refinv="Fatura ref.", vol="Volumes",
               gw="Peso bruto (kg)", nw="Peso líquido (kg)", cbm="Cubagem (m3)", cartons="Caixas"),
}
ENDERECOS = ["Room 1203, Example Tower, 88 Demo Road", "Building 5, Modelo Industrial Park",
             "Via Esempio 14, Zona Industriale", "Beispielstrasse 22, Gewerbegebiet"]
PAISES = ["China", "Germany", "Italy"]


class Folha:
    """Lista de operações de desenho em pontos (A4 = 595 x 842), y medido de cima para baixo."""

    def __init__(self) -> None:
        self.ops: list[tuple] = []

    def texto(self, x, y, s, tam=9.0, negrito=False, cinza=0.0, alinha="l"):
        self.ops.append(("t", x, y, str(s), tam, negrito, cinza, alinha))

    def linha(self, x1, y1, x2, y2, esp=0.6):
        self.ops.append(("l", x1, y1, x2, y2, esp))

    def caixa(self, x, y, w, h, esp=0.6, fundo=None):
        self.ops.append(("c", x, y, w, h, esp, fundo))

    def campo(self, x, y, w, h, rotulo, valor, tam=9.0):
        self.caixa(x, y, w, h)
        self.texto(x + 4, y + 9, rotulo, 6.5, cinza=0.45)
        self.texto(x + 4, y + h - 8, valor, tam, negrito=True)

    def tabela(self, x, y, colunas, cabecalho, linhas, h=18) -> float:
        """colunas = [(largura, 'l'|'r')]. Devolve o y logo abaixo da tabela."""
        total = sum(w for w, _ in colunas)
        for i, textos in enumerate([cabecalho] + linhas):
            topo = y + i * h
            self.caixa(x, topo, total, h, fundo=0.88 if i == 0 else None)
            cx = x
            for (w, al), s in zip(colunas, textos):
                px = cx + 4 if al == "l" else cx + w - 4
                self.texto(px, topo + h - 6, s, 8.5, negrito=i == 0, alinha=al)
                cx += w
        cx = x
        for w, _ in colunas[:-1]:
            cx += w
            self.linha(cx, y, cx, y + h * (len(linhas) + 1))
        return y + h * (len(linhas) + 1)


def _cabecalho(f: Folha, nome: str, titulo: str, rng: random.Random) -> None:
    f.texto(40, 55, nome, 12, True)
    f.texto(40, 68, rng.choice(ENDERECOS), 7.5, cinza=0.4)
    f.texto(40, 78, f"Tel: +00 {rng.randint(100, 999)} {rng.randint(1000, 9999)} {rng.randint(1000, 9999)}",
            7.5, cinza=0.4)
    f.texto(555, 55, titulo, 15, True, alinha="r")


def _rodape(f: Folha, y: float, linhas: list[str]) -> None:
    for i, s in enumerate(linhas):
        f.texto(40, y + i * 11, s, 7.5, cinza=0.4)
    f.texto(297, 815, "Page 1 of 1", 7, cinza=0.5, alinha="c")


def _invoice(gab: dict, lang: str, rng: random.Random) -> Folha:
    inv, r, f = gab["invoice"], ROT[lang], Folha()
    _cabecalho(f, inv["exportador"], r["inv"], rng)
    f.caixa(500, 62, 55, 14)
    f.texto(527, 72, r["orig"], 7, True, alinha="c")
    f.campo(40, 95, 300, 36, r["ex"], inv["exportador"])
    f.campo(340, 95, 107, 36, r["no"], inv["numero"])
    f.campo(447, 95, 108, 36, r["dt"], _data(inv["data"], lang))
    f.campo(40, 131, 300, 36, r["im"], inv["importador"])
    f.campo(340, 131, 107, 36, r["it"], inv["incoterm"])
    f.campo(447, 131, 108, 36, r["cur"], inv["moeda"])
    f.campo(40, 167, 300, 36, "Customer PO", f"PO-{rng.randint(1000, 9999)}")
    f.campo(340, 167, 107, 36, "Country of origin", rng.choice(PAISES))
    f.campo(447, 167, 108, 36, "Payment terms", "T/T 30 days")

    colunas = [(25, "l"), (215, "l"), (60, "r"), (40, "l"), (80, "r"), (95, "r")]
    cab = ["No.", r["desc"], r["qty"], r["un"], r["pu"], r["amt"]]
    linhas = [[str(i + 1), it["descricao"], _num(it["quantidade"], lang), it["unidade"],
               _num(it["preco_unitario"], lang), _num(it["total"], lang)]
              for i, it in enumerate(inv["itens"])]
    y = f.tabela(40, 225, colunas, cab, linhas)
    f.caixa(365, y + 6, 190, 22, fundo=0.92)
    f.texto(371, y + 21, r["tot"], 9, True)
    f.texto(551, y + 21, f"{inv['moeda']} {_num(inv['total_geral'], lang)}", 10, True, alinha="r")
    _rodape(f, y + 70, [f"Bank: Example Bank Ltd  |  SWIFT EXMPCNBK  |  Account {rng.randint(10**9, 10**10 - 1)}",
                        "Marks & numbers: N/M", "Signed: ______________________"])
    return f


def _packing(gab: dict, lang: str, rng: random.Random) -> Folha:
    pl, inv, r, f = gab["packing_list"], gab["invoice"], ROT[lang], Folha()
    _cabecalho(f, inv["exportador"], r["pl"], rng)
    f.campo(40, 95, 300, 36, r["refinv"], pl["invoice_numero"])
    f.campo(340, 95, 107, 36, r["dt"], _data(inv["data"], lang))
    f.campo(447, 95, 108, 36, "Shipping marks", "N/M")

    colunas = [(25, "l"), (235, "l"), (70, "r"), (80, "r"), (105, "r")]
    cab = ["No.", r["desc"], r["qty"], r["cartons"], r["nw"]]
    linhas = [[str(i + 1), it["descricao"], _num(it["quantidade"], lang),
               str(max(1, int(float(it["quantidade"])) // rng.randint(20, 50))),
               _num(it["peso_liquido_kg"], lang)]
              for i, it in enumerate(pl["itens"])]
    y = f.tabela(40, 155, colunas, cab, linhas) + 14

    totais = [(r["vol"], str(pl["volumes"])), (r["gw"], _num(pl["peso_bruto_kg"], lang)),
              (r["nw"], _num(pl["peso_liquido_kg"], lang)), (r["cbm"], _num(pl["cubagem_m3"], lang))]
    for i, (rotulo, valor) in enumerate(totais):
        topo = y + i * 18
        f.caixa(355, topo, 200, 18, fundo=0.92 if i == 0 else None)
        f.texto(360, topo + 12, rotulo, 8)
        f.texto(551, topo + 12, valor, 9, True, alinha="r")
    _rodape(f, y + 100, ["Container load: FCL  |  Stuffed at: shipper's factory", "Signed: ______________________"])
    return f


def _bl(gab: dict, lang: str, rng: random.Random) -> Folha:
    bl, r, f = gab["bl"], ROT[lang], Folha()
    f.texto(40, 55, bl["armador"], 14, True)
    f.texto(40, 68, "Port-to-port  |  negotiable", 7.5, cinza=0.4)
    f.texto(555, 55, "BILL OF LADING", 13, True, alinha="r")

    f.campo(40, 90, 300, 48, "Shipper", bl["embarcador"])
    f.campo(40, 138, 300, 48, "Consignee", bl["consignee"])
    f.campo(40, 186, 300, 48, "Notify party", bl["notify"])
    f.campo(340, 90, 215, 32, "B/L No.", bl["numero"])
    f.campo(340, 122, 215, 32, "Vessel / Voyage", f"{bl['navio']}  V.{rng.randint(100, 999)}E")
    f.campo(340, 154, 215, 32, "Port of loading", bl["porto_carga"])
    f.campo(340, 186, 215, 32, "Port of discharge", bl["porto_descarga"])
    f.campo(340, 218, 215, 32, "Shipped on board", _data(bl["data_embarque"], lang))

    f.campo(40, 265, 215, 36, "Description of goods", "GENERAL CARGO, SAID TO CONTAIN")
    f.campo(255, 265, 100, 36, r["vol"], str(bl["volumes"]))
    f.campo(355, 265, 200, 36, r["gw"], f"{_num(bl['peso_bruto_kg'], lang)} KGS")

    colunas = [(200, "l"), (150, "l"), (165, "l")]
    linhas = [[c["numero"], c["lacre"], "40' HC"] for c in bl["conteineres"]]
    y = f.tabela(40, 320, colunas, ["Container No.", "Seal No.", "Size / type"], linhas)
    emissao = date.fromisoformat(bl["data_embarque"]) + timedelta(days=2)
    _rodape(f, y + 40, ["Freight: PREPAID  |  Number of original B(s)/L: THREE (3)",
                        f"Place and date of issue: {bl['porto_carga']}, {_data(emissao.isoformat(), lang)}"])
    return f


# ---------- saída 1: PDF com texto ----------
def _salvar_pdf_texto(f: Folha, caminho: Path) -> None:
    c = canvas.Canvas(str(caminho), pagesize=A4)
    for op in f.ops:
        if op[0] == "t":
            _, x, y, s, tam, neg, cinza, al = op
            c.setFont("Helvetica-Bold" if neg else "Helvetica", tam)
            c.setFillGray(cinza)
            {"l": c.drawString, "r": c.drawRightString, "c": c.drawCentredString}[al](x, ALTURA - y, s)
        elif op[0] == "l":
            _, x1, y1, x2, y2, esp = op
            c.setLineWidth(esp)
            c.setStrokeGray(0)
            c.line(x1, ALTURA - y1, x2, ALTURA - y2)
        else:
            _, x, y, w, h, esp, fundo = op
            c.setLineWidth(esp)
            c.setStrokeGray(0)
            if fundo is not None:
                c.setFillGray(fundo)
            c.rect(x, ALTURA - y - h, w, h, stroke=1, fill=0 if fundo is None else 1)
    c.save()


# ---------- saída 2: PDF escaneado (só imagem) ----------
def _rasterizar(f: Folha, dpi: int) -> Image.Image:
    esc = dpi / 72
    img = Image.new("RGB", (round(LARGURA * esc), round(ALTURA * esc)), (255, 255, 255))
    d = ImageDraw.Draw(img)
    fontes: dict[tuple, ImageFont.FreeTypeFont] = {}
    for op in f.ops:
        if op[0] == "t":
            _, x, y, s, tam, neg, cinza, al = op
            chave = (neg, round(tam * esc))
            if chave not in fontes:
                fontes[chave] = ImageFont.truetype(str(FONTES / ("VeraBd.ttf" if neg else "Vera.ttf")), chave[1])
            v = round(cinza * 255)
            d.text((x * esc, y * esc), s, font=fontes[chave], fill=(v, v, v), anchor={"l": "ls", "r": "rs", "c": "ms"}[al])
        elif op[0] == "l":
            _, x1, y1, x2, y2, esp = op
            d.line([x1 * esc, y1 * esc, x2 * esc, y2 * esc], fill=(0, 0, 0), width=max(1, round(esp * esc)))
        else:
            _, x, y, w, h, esp, fundo = op
            fill = None if fundo is None else (round(fundo * 255),) * 3
            d.rectangle([x * esc, y * esc, (x + w) * esc, (y + h) * esc], outline=(0, 0, 0),
                        width=max(1, round(esp * esc)), fill=fill)
    return img


def _carimbo(img: Image.Image, lang: str) -> None:
    esc = img.size[0] / LARGURA
    texto = "RECEBIDO" if lang == "pt" else "RECEIVED"
    camada = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    fonte = ImageFont.truetype(str(FONTES / "VeraBd.ttf"), round(34 * esc))
    cx, cy = img.size[0] * 0.66, img.size[1] * 0.88
    l, t, r, b = d.textbbox((cx, cy), texto, font=fonte, anchor="mm")
    d.rectangle([l - 12, t - 8, r + 12, b + 8], outline=(190, 30, 30, 150), width=max(2, round(2 * esc)))
    d.text((cx, cy), texto, font=fonte, fill=(190, 30, 30, 150), anchor="mm")
    camada = camada.rotate(14, resample=Image.BICUBIC)
    img.paste(camada, (0, 0), camada)


def _degradar(img: Image.Image, rng: random.Random, cfg: dict, lang: str) -> Image.Image:
    if cfg["carimbo"]:
        _carimbo(img, lang)
    w, h = img.size
    # sombra de papel: gradiente de um lado ao outro
    sombra = Image.linear_gradient("L").resize((w, h)).rotate(rng.choice([0, 90, 180, 270]))
    sombra = sombra.point(lambda v: 255 - round(v / 255 * (255 - cfg["sombra"]))).convert("RGB")
    img = ImageChops.multiply(img, sombra)
    img = ImageEnhance.Contrast(img).enhance(cfg["contraste"])
    angulo = rng.choice([-1, 1]) * rng.uniform(cfg["rotacao"] / 2, cfg["rotacao"])
    img = img.rotate(angulo, resample=Image.BICUBIC, fillcolor=(235, 235, 235))
    img = img.filter(ImageFilter.GaussianBlur(cfg["blur"]))
    ruido = Image.effect_noise(img.size, cfg["ruido"]).convert("RGB")
    return ImageChops.add(img, ruido, 1.0, -128)


def _salvar_pdf_scan(f: Folha, caminho: Path, cfg: dict, lang: str, rng: random.Random) -> None:
    img = _degradar(_rasterizar(f, cfg["dpi"]), rng, cfg, lang)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=cfg["jpeg"])
    buf.seek(0)
    c = canvas.Canvas(str(caminho), pagesize=A4)
    c.drawImage(ImageReader(buf), 0, 0, width=LARGURA, height=ALTURA)
    c.save()


def renderizar_sujo(gab: dict, pasta: Path, id_: str, lang: str, variante: str, rng: random.Random) -> None:
    cfg = VARIANTES[variante]
    for tipo, montar in (("invoice", _invoice), ("packing_list", _packing), ("bl", _bl)):
        folha = montar(gab, lang, rng)
        caminho = pasta / f"{id_}_{tipo}.pdf"
        if "dpi" in cfg:
            _salvar_pdf_scan(folha, caminho, cfg, lang, rng)
        else:
            _salvar_pdf_texto(folha, caminho)


def gerar_sujo(n_por_variante: int, saida: Path, seed: int = 7) -> list[str]:
    """Gera n conjuntos por variante; o último de cada variante sai com um defeito injetado."""
    pdfs, gabs = saida / "pdf", saida / "gabarito"
    pdfs.mkdir(parents=True, exist_ok=True)
    gabs.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    tipos_defeito = list(DEFEITOS)
    ids = []
    for k, (variante, cfg) in enumerate(VARIANTES.items()):
        for i in range(n_por_variante):
            defeito = tipos_defeito[(k + i) % len(tipos_defeito)] if i == n_por_variante - 1 else None
            gab = gerar_conjunto(rng, defeito)
            gab["variante"] = variante
            id_ = f"{cfg['prefixo']}{i + 1:03d}"
            renderizar_sujo(gab, pdfs, id_, "pt" if i % 2 else "en", variante, rng)
            (gabs / f"{id_}.json").write_text(json.dumps(gab, ensure_ascii=False, indent=2), encoding="utf-8")
            ids.append(id_)
    return ids
