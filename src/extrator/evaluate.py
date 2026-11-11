"""Eval: compara o extraído com o gabarito campo a campo e confere se os defeitos foram pegos."""
import json
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .pipeline import Extrator, processar
from .schemas import SCHEMAS


def achatar(obj: Any, prefixo: str = "") -> dict[str, Any]:
    """{'itens': [{'total': '5'}]} vira {'itens[0].total': '5'}."""
    if isinstance(obj, dict):
        saida: dict[str, Any] = {}
        for k, v in obj.items():
            saida.update(achatar(v, f"{prefixo}.{k}" if prefixo else k))
        return saida
    if isinstance(obj, list):
        saida = {}
        for i, v in enumerate(obj):
            saida.update(achatar(v, f"{prefixo}[{i}]"))
        return saida
    return {prefixo: obj}


def _normalizar(v: Any) -> Any:
    if isinstance(v, str):
        texto = re.sub(r"\s+", " ", v).strip()
        try:
            return Decimal(texto)  # "1234.5" e "1234.50" são o mesmo valor
        except InvalidOperation:
            return texto.casefold()
    if isinstance(v, int) and not isinstance(v, bool):
        return Decimal(v)
    return v


def _igual(a: Any, b: Any) -> bool:
    return _normalizar(a) == _normalizar(b)


def _campo_generico(caminho: str) -> str:
    return re.sub(r"\[\d+\]", "[]", caminho)


def avaliar(pasta_dados: Path, extrair: Extrator, limite: int | None = None) -> dict:
    """`limite` avalia só uma amostra de N conjuntos, espaçados, para gastar menos."""
    pasta = Path(pasta_dados)
    acertos: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # campo -> [certos, total]
    docs_certos: dict[str, list[int]] = {t: [0, 0] for t in SCHEMAS}
    conjuntos, falsos_alarmes, defeitos_total, defeitos_pegos, revisados = [], 0, 0, 0, 0
    com_erro, erros_silenciosos = 0, 0
    por_variante: dict[str, dict[str, int]] = defaultdict(lambda: {"conjuntos": 0, "corretos": 0, "erros_silenciosos": 0})

    gabaritos = sorted((pasta / "gabarito").glob("*.json"))
    if limite:
        gabaritos = gabaritos[:: max(1, len(gabaritos) // limite)][:limite]
    for arq in gabaritos:
        id_ = arq.stem
        gab = json.loads(arq.read_text(encoding="utf-8"))
        pdfs = {t: pasta / "pdf" / f"{id_}_{t}.pdf" for t in SCHEMAS}
        saida = processar(pdfs, extrair)

        conjunto_correto = True
        for tipo in SCHEMAS:
            esperado = achatar(gab[tipo])
            obtido = achatar(saida["documentos"].get(tipo, {}))
            todos_os_campos = set(esperado) | set(obtido)
            tudo_certo = True
            for caminho in todos_os_campos:
                chave = f"{tipo}.{_campo_generico(caminho)}"
                certo = caminho in esperado and caminho in obtido and _igual(esperado[caminho], obtido[caminho])
                acertos[chave][0] += int(certo)
                acertos[chave][1] += 1
                tudo_certo &= certo
            docs_certos[tipo][0] += int(tudo_certo)
            docs_certos[tipo][1] += 1
            conjunto_correto &= tudo_certo

        codigos = {p["codigo"] for p in saida["problemas"] if p["severidade"] == "erro"}
        esperados = set(gab["problemas_esperados"])
        revisados += saida["status"] == "revisar"
        if esperados:
            defeitos_total += 1
            defeitos_pegos += esperados <= codigos
        elif saida["status"] == "revisar" and conjunto_correto:
            falsos_alarmes += 1  # extração perfeita, conjunto limpo, e mesmo assim foi para revisão
        silencioso = not conjunto_correto and saida["status"] == "ok"  # o erro perigoso: passou sem revisão
        if not conjunto_correto:
            com_erro += 1
            erros_silenciosos += silencioso
        v = por_variante[gab.get("variante", "padrao")]
        v["conjuntos"] += 1
        v["corretos"] += conjunto_correto
        v["erros_silenciosos"] += silencioso
        conjuntos.append({"id": id_, "status": saida["status"], "esperados": sorted(esperados), "obtidos": sorted(codigos)})

    n = len(gabaritos)
    return {
        "conjuntos": n,
        "acerto_por_documento": {t: _taxa(c) for t, c in docs_certos.items()},
        "acerto_por_campo": {k: _taxa(v) for k, v in sorted(acertos.items(), key=lambda kv: _taxa(kv[1]))},
        "taxa_revisao": revisados / n if n else 0.0,
        "defeitos": {"injetados": defeitos_total, "detectados": defeitos_pegos},
        "falsos_alarmes": falsos_alarmes,
        "conjuntos_com_erro_de_extracao": com_erro,
        "erros_silenciosos": erros_silenciosos,
        "por_variante": dict(por_variante),
        "detalhe": conjuntos,
    }


def _taxa(par: list[int]) -> float:
    return par[0] / par[1] if par[1] else 0.0


def formatar_markdown(r: dict, titulo: str) -> str:
    l = [f"# {titulo}", "", f"Conjuntos avaliados: {r['conjuntos']}", "", "## Acerto por documento", "",
         "| Documento | Acerto (todos os campos corretos) |", "|---|---|"]
    l += [f"| {t} | {v:.1%} |" for t, v in r["acerto_por_documento"].items()]
    d = r["defeitos"]
    l += ["", "## Revisão humana", "",
          f"- Conjuntos enviados para revisão: {r['taxa_revisao']:.1%}",
          f"- Defeitos injetados detectados: {d['detectados']} de {d['injetados']}",
          f"- Conjuntos com algum erro de extração: {r['conjuntos_com_erro_de_extracao']}",
          f"- **Erros de extração que passaram sem revisão: {r['erros_silenciosos']}** (o número que mais importa)",
          f"- Falsos alarmes (extração perfeita, conjunto limpo, marcado para revisão): {r['falsos_alarmes']}",
          ]
    if len(r.get("por_variante", {})) > 1:
        l += ["", "## Por tipo de PDF", "", "| Tipo | Conjuntos | Conjuntos 100% corretos | Erros silenciosos |", "|---|---|---|---|"]
        l += [f"| {k} | {v['conjuntos']} | {v['corretos']} | {v['erros_silenciosos']} |"
              for k, v in r["por_variante"].items()]
    l += ["", "## Acerto por campo (do pior para o melhor)", "", "| Campo | Acerto |", "|---|---|"]
    l += [f"| `{k}` | {v:.1%} |" for k, v in r["acerto_por_campo"].items()]
    return "\n".join(l) + "\n"
