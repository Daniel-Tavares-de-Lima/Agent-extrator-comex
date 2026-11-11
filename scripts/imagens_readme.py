"""Gera as imagens do README a partir dos dados sintéticos (nada de documento real).

Uso (na raiz do projeto, depois de `python -m extrator gerar-sujo`):
    python scripts/imagens_readme.py
"""
import io
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader

from extrator import sujo

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "docs" / "img"
LARGURA_COLUNA = 620
TOPO_PT = 470  # a invoice ocupa só a parte de cima da folha


def _fonte(tam: int, negrito: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(sujo.FONTES / ("VeraBd.ttf" if negrito else "Vera.ttf")), tam)


def _recorte_topo(img: Image.Image) -> Image.Image:
    altura = round(img.size[1] * TOPO_PT / sujo.ALTURA)
    corte = img.crop((0, 0, img.size[0], altura))
    return corte.resize((LARGURA_COLUNA, round(altura * LARGURA_COLUNA / img.size[0])), Image.LANCZOS)


def comparacao() -> None:
    """A mesma invoice nos três tipos de PDF, lado a lado."""
    gab = json.loads((RAIZ / "data/sujo/gabarito/T001.json").read_text(encoding="utf-8"))
    folha = sujo._invoice(gab, "en", random.Random(1))
    colunas = [("tabela: PDF com texto", sujo._rasterizar(folha, 150))]
    for nome, chave in (("scan leve: só imagem", "scan_leve"), ("scan pesado: só imagem", "scan_pesado")):
        cfg = sujo.VARIANTES[chave]
        img = sujo._degradar(sujo._rasterizar(folha, cfg["dpi"]), random.Random(3), cfg, "en")
        colunas.append((nome, img))

    recortes = [(t, _recorte_topo(i)) for t, i in colunas]
    margem, titulo = 16, 40
    h = max(r.size[1] for _, r in recortes)
    tela = Image.new("RGB", (len(recortes) * (LARGURA_COLUNA + margem) + margem, h + titulo + margem), (255, 255, 255))
    d = ImageDraw.Draw(tela)
    for i, (t, r) in enumerate(recortes):
        x = margem + i * (LARGURA_COLUNA + margem)
        d.text((x, titulo - 12), t, font=_fonte(18, True), fill=(0, 69, 106), anchor="ls")
        tela.paste(r, (x, titulo))
        d.rectangle([x, titulo, x + r.size[0] - 1, titulo + r.size[1] - 1], outline=(129, 130, 130))
    tela.save(SAIDA / "mesma_invoice_tres_tipos.jpg", quality=85)


def digito_trocado() -> None:
    """Recorte ampliado do scan pesado (P001): o contêiner e o lacre onde o Claude errou um dígito."""
    pagina = PdfReader(str(RAIZ / "data/sujo/pdf/P001_bl.pdf")).pages[0]
    img = Image.open(io.BytesIO(pagina.images[0].data))
    esc = img.size[0] / sujo.LARGURA  # pixels por ponto
    corte = img.crop((round(30 * esc), round(305 * esc), round(565 * esc), round(385 * esc)))
    corte = corte.resize((corte.size[0] * 2, corte.size[1] * 2), Image.LANCZOS)
    tela = Image.new("RGB", (corte.size[0] + 32, corte.size[1] + 120), (255, 255, 255))
    d = ImageDraw.Draw(tela)
    d.text((16, 28), "Scan pesado (recorte ampliado): onde o Claude errou", font=_fonte(18, True), fill=(0, 69, 106), anchor="ls")
    tela.paste(corte, (16, 44))
    y = corte.size[1] + 70
    gab = json.loads((RAIZ / "data/sujo/gabarito/P001.json").read_text(encoding="utf-8"))["bl"]["conteineres"][0]
    d.text((16, y), f"Impresso:  contêiner {gab['numero']}   lacre {gab['lacre']}", font=_fonte(15), fill=(0, 0, 0), anchor="ls")
    d.text((16, y + 26), "Lido:        contêiner DEMU8044250   lacre SL274259   (dígito trocado em cada um)",
           font=_fonte(15), fill=(180, 30, 30), anchor="ls")
    tela.save(SAIDA / "digito_trocado_scan_pesado.jpg", quality=88)


if __name__ == "__main__":
    SAIDA.mkdir(parents=True, exist_ok=True)
    comparacao()
    digito_trocado()
    print("imagens em", SAIDA)
