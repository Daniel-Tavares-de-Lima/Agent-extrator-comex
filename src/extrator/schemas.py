"""Schemas dos três documentos. Aqui só vai estrutura e tipo.

Regras de negócio (soma, dígito do contêiner, cruzamento entre documentos)
ficam em validators.py, para que um valor errado no documento vire
"revisar" com motivo, e não uma exceção que joga o dado fora.
"""
from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Incoterm(str, Enum):
    EXW = "EXW"
    FCA = "FCA"
    FAS = "FAS"
    FOB = "FOB"
    CFR = "CFR"
    CIF = "CIF"
    CPT = "CPT"
    CIP = "CIP"
    DAP = "DAP"
    DPU = "DPU"
    DDP = "DDP"


# ---------- Invoice ----------
class ItemInvoice(Base):
    descricao: str = Field(min_length=1)
    quantidade: Decimal = Field(gt=0)
    unidade: str = Field(min_length=1)
    preco_unitario: Decimal = Field(ge=0)
    total: Decimal = Field(ge=0)


class Invoice(Base):
    numero: str = Field(min_length=1)
    data: date
    exportador: str = Field(min_length=1)
    importador: str = Field(min_length=1)
    incoterm: Incoterm
    moeda: str = Field(pattern=r"^[A-Z]{3}$")
    itens: list[ItemInvoice] = Field(min_length=1)
    total_geral: Decimal = Field(ge=0)


# ---------- Packing List ----------
class ItemPacking(Base):
    descricao: str = Field(min_length=1)
    quantidade: Decimal = Field(gt=0)
    peso_liquido_kg: Decimal = Field(ge=0)


class PackingList(Base):
    invoice_numero: str = Field(min_length=1)
    volumes: int = Field(gt=0)
    peso_bruto_kg: Decimal = Field(gt=0)
    peso_liquido_kg: Decimal = Field(ge=0)
    cubagem_m3: Decimal = Field(ge=0)
    itens: list[ItemPacking] = Field(min_length=1)


# ---------- Bill of Lading ----------
class Conteiner(Base):
    numero: str = Field(min_length=1)
    lacre: str = Field(min_length=1)


class BillOfLading(Base):
    numero: str = Field(min_length=1)
    armador: str = Field(min_length=1)
    navio: str = Field(min_length=1)
    data_embarque: date
    porto_carga: str = Field(min_length=1)
    porto_descarga: str = Field(min_length=1)
    embarcador: str = Field(min_length=1)
    consignee: str = Field(min_length=1)
    notify: str = Field(min_length=1)
    volumes: int = Field(gt=0)
    peso_bruto_kg: Decimal = Field(gt=0)
    conteineres: list[Conteiner] = Field(min_length=1)


SCHEMAS: dict[str, type[Base]] = {
    "invoice": Invoice,
    "packing_list": PackingList,
    "bl": BillOfLading,
}
