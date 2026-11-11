from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .erros import ExtracaoErro
from .schemas import SCHEMAS
from .validators import Problema, status, validar_conjunto

Extrator = Callable[[Path, str], BaseModel]


def processar(pdfs: dict[str, Path], extrair: Extrator) -> dict:
    """Extrai cada PDF, valida, e devolve JSON com status "ok" ou "revisar".

    Se um documento não extrai, os demais seguem e o conjunto vai para revisão.
    """
    docs: dict[str, BaseModel] = {}
    problemas: list[Problema] = []
    for tipo in SCHEMAS:
        pdf = pdfs.get(tipo)
        if pdf is None:
            continue
        try:
            docs[tipo] = extrair(pdf, tipo)
        except (ValidationError, ExtracaoErro) as e:
            problemas.append(Problema("EXTRACAO_FALHOU", f"{tipo}: {e}", campo=tipo))

    problemas += validar_conjunto(docs.get("invoice"), docs.get("packing_list"), docs.get("bl"))
    return {
        "status": status(problemas),
        "documentos": {t: d.model_dump(mode="json") for t, d in docs.items()},
        "problemas": [asdict(p) for p in problemas],
    }
