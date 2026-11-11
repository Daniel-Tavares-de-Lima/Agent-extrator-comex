"""Extrator falso: devolve o gabarito com erros sorteados.

Serve para rodar o eval sem chamar API e provar que a régua funciona.
Os números que ele produz NÃO dizem nada sobre a acurácia do Claude.
"""
import json
import random
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .schemas import SCHEMAS

_NUMERO = re.compile(r"^-?\d+(\.\d+)?$")


class ExtratorSimulado:
    def __init__(self, pasta_dados: Path, taxa_erro: float = 0.0, seed: int = 0):
        self.gabaritos = Path(pasta_dados) / "gabarito"
        self.taxa_erro = taxa_erro
        self.rng = random.Random(seed)

    def __call__(self, pdf: Path, tipo: str) -> BaseModel:
        id_ = Path(pdf).name.split("_")[0]
        gab = json.loads((self.gabaritos / f"{id_}.json").read_text(encoding="utf-8"))
        return SCHEMAS[tipo].model_validate(self._ruido(gab[tipo]))

    def _ruido(self, valor: Any) -> Any:
        if isinstance(valor, dict):
            return {k: self._ruido(v) for k, v in valor.items()}
        if isinstance(valor, list):
            return [self._ruido(v) for v in valor]
        if self.rng.random() >= self.taxa_erro:
            return valor
        if isinstance(valor, str) and _NUMERO.match(valor):
            return str(round(float(valor) + 1, 2))
        if isinstance(valor, str) and len(valor) > 1:
            return valor[:-1]
        if isinstance(valor, int):
            return valor + 1
        return valor
