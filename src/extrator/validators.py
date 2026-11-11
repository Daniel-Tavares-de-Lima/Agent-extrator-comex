"""Regras de negócio. Cada falha vira um Problema com código, para o eval poder contar."""
import re
import string
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .schemas import BillOfLading, Invoice, PackingList

CENTAVO = Decimal("0.01")
TOLERANCIA_PESO_REL = Decimal("0.01")  # 1% entre packing list e BL

# Moedas comuns em comex. Moeda fora da lista não é erro de formato, vai para revisão.
MOEDAS = {
    "USD", "EUR", "BRL", "CNY", "GBP", "JPY", "CHF", "CAD", "AUD", "MXN",
    "ARS", "CLP", "COP", "INR", "KRW", "SGD", "HKD", "TWD", "THB", "VND",
    "TRY", "ZAR", "AED", "SEK", "NOK", "DKK", "PLN",
}


@dataclass(frozen=True)
class Problema:
    codigo: str
    mensagem: str
    severidade: str = "erro"  # "erro" manda para revisão; "aviso" só registra
    campo: str = ""


def status(problemas: list[Problema]) -> str:
    return "revisar" if any(p.severidade == "erro" for p in problemas) else "ok"


def _norm(texto: str) -> str:
    return re.sub(r"[^a-z0-9]", "", texto.casefold())


# ---------- contêiner (ISO 6346) ----------
def _valores_letras() -> dict[str, int]:
    valores, n = {}, 10
    for letra in string.ascii_uppercase:
        if n % 11 == 0:
            n += 1
        valores[letra] = n
        n += 1
    return valores


_LETRAS = _valores_letras()


def digito_iso6346(prefixo: str) -> int:
    """Dígito verificador dos 10 primeiros caracteres (4 letras + 6 dígitos)."""
    soma = sum(
        (_LETRAS[c] if c.isalpha() else int(c)) * (2 ** i) for i, c in enumerate(prefixo)
    )
    return soma % 11 % 10


def conteiner_valido(numero: str) -> tuple[bool, str]:
    n = re.sub(r"[^A-Za-z0-9]", "", numero).upper()
    if not re.fullmatch(r"[A-Z]{3}[UJZ]\d{7}", n):
        return False, "FORMATO"
    if digito_iso6346(n[:10]) != int(n[10]):
        return False, "DIGITO"
    return True, ""


# ---------- por documento ----------
def validar_invoice(inv: Invoice) -> list[Problema]:
    ps: list[Problema] = []
    for i, it in enumerate(inv.itens):
        esperado = (it.quantidade * it.preco_unitario).quantize(CENTAVO, ROUND_HALF_UP)
        if abs(esperado - it.total) > CENTAVO:
            ps.append(Problema(
                "ITEM_TOTAL_INCONSISTENTE",
                f"item {i + 1}: quantidade x preço = {esperado}, documento diz {it.total}",
                campo=f"itens[{i}].total",
            ))
    soma = sum((it.total for it in inv.itens), Decimal("0"))
    if abs(soma - inv.total_geral) > CENTAVO:
        ps.append(Problema(
            "TOTAL_GERAL_DIVERGENTE",
            f"soma dos itens = {soma}, total geral do documento = {inv.total_geral}",
            campo="total_geral",
        ))
    if inv.moeda not in MOEDAS:
        ps.append(Problema("MOEDA_DESCONHECIDA", f"moeda {inv.moeda} fora da lista", campo="moeda"))
    return ps


def validar_packing_list(pl: PackingList) -> list[Problema]:
    ps: list[Problema] = []
    if pl.peso_liquido_kg > pl.peso_bruto_kg:
        ps.append(Problema(
            "PESO_LIQUIDO_MAIOR_QUE_BRUTO",
            f"líquido {pl.peso_liquido_kg} kg maior que bruto {pl.peso_bruto_kg} kg",
            campo="peso_liquido_kg",
        ))
    soma = sum((it.peso_liquido_kg for it in pl.itens), Decimal("0"))
    if abs(soma - pl.peso_liquido_kg) > CENTAVO:
        ps.append(Problema(
            "SOMA_PESO_ITENS_DIVERGENTE",
            f"soma dos itens = {soma} kg, total do documento = {pl.peso_liquido_kg} kg",
            campo="peso_liquido_kg",
        ))
    return ps


def validar_bl(bl: BillOfLading) -> list[Problema]:
    ps: list[Problema] = []
    vistos: set[str] = set()
    for i, c in enumerate(bl.conteineres):
        ok, motivo = conteiner_valido(c.numero)
        campo = f"conteineres[{i}].numero"
        if not ok and motivo == "FORMATO":
            ps.append(Problema("CONTEINER_FORMATO_INVALIDO", f"{c.numero}: formato inválido", campo=campo))
        elif not ok:
            ps.append(Problema("CONTEINER_DIGITO_INVALIDO", f"{c.numero}: dígito verificador não confere", campo=campo))
        chave = re.sub(r"[^A-Za-z0-9]", "", c.numero).upper()
        if chave in vistos:
            ps.append(Problema("CONTEINER_DUPLICADO", f"{c.numero} aparece mais de uma vez", campo=campo))
        vistos.add(chave)
    return ps


# ---------- entre documentos ----------
def validar_cruzado(
    inv: Invoice | None, pl: PackingList | None, bl: BillOfLading | None
) -> list[Problema]:
    ps: list[Problema] = []
    if inv and pl:
        if _norm(pl.invoice_numero) != _norm(inv.numero):
            ps.append(Problema(
                "PL_INVOICE_DIVERGENTE",
                f"packing list cita invoice {pl.invoice_numero}, a invoice é {inv.numero}",
                campo="invoice_numero",
            ))
        qtd_inv = sum((i.quantidade for i in inv.itens), Decimal("0"))
        qtd_pl = sum((i.quantidade for i in pl.itens), Decimal("0"))
        if qtd_inv != qtd_pl:
            ps.append(Problema(
                "QUANTIDADE_DIVERGENTE",
                f"quantidade total: invoice {qtd_inv}, packing list {qtd_pl}",
            ))
    if pl and bl:
        maior = max(pl.peso_bruto_kg, bl.peso_bruto_kg)
        if abs(pl.peso_bruto_kg - bl.peso_bruto_kg) > maior * TOLERANCIA_PESO_REL:
            ps.append(Problema(
                "PESO_BRUTO_DIVERGENTE",
                f"peso bruto: packing list {pl.peso_bruto_kg} kg, BL {bl.peso_bruto_kg} kg",
                campo="peso_bruto_kg",
            ))
        if pl.volumes != bl.volumes:
            ps.append(Problema(
                "VOLUMES_DIVERGENTES",
                f"volumes: packing list {pl.volumes}, BL {bl.volumes}",
                campo="volumes",
            ))
    if inv and bl:
        if _norm(bl.embarcador) != _norm(inv.exportador):
            ps.append(Problema(
                "EMBARCADOR_DIFERENTE_DO_EXPORTADOR",
                f"BL: {bl.embarcador}; invoice: {inv.exportador}",
                severidade="aviso",
            ))
        if _norm(bl.consignee) != _norm(inv.importador):
            ps.append(Problema(
                "CONSIGNEE_DIFERENTE_DO_IMPORTADOR",
                f"BL: {bl.consignee}; invoice: {inv.importador}",
                severidade="aviso",
            ))
    return ps


def validar_conjunto(
    inv: Invoice | None, pl: PackingList | None, bl: BillOfLading | None
) -> list[Problema]:
    ps: list[Problema] = []
    if inv:
        ps += validar_invoice(inv)
    if pl:
        ps += validar_packing_list(pl)
    if bl:
        ps += validar_bl(bl)
    return ps + validar_cruzado(inv, pl, bl)
