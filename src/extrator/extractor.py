"""Extrator que manda o PDF para o Claude e recebe o JSON no schema do documento."""
import base64
import os
from pathlib import Path

import anthropic
from pydantic import BaseModel, ValidationError

from .erros import ExtracaoErro
from .schemas import SCHEMAS

MODELO_PADRAO = os.environ.get("EXTRATOR_MODELO", "claude-opus-5-5")

NOMES = {
    "invoice": "Commercial Invoice",
    "packing_list": "Packing List",
    "bl": "Bill of Lading (BL)",
}

PROMPT = """Extraia os dados do {nome} em anexo para o schema pedido.

Regras:
- Copie o que está impresso. Não corrija, não some, não deduza. Se o documento \
traz um total errado, devolva o total errado: a conferência é feita depois, por código.
- Datas em AAAA-MM-DD. Valores e pesos com ponto decimal e sem separador de milhar.
- Mantenha os números de documento, contêiner e lacre exatamente como aparecem.
- Navio: só o nome, sem o número da viagem (de "OA PIONEER V.045E" devolva "OA PIONEER").
- Não invente. Se um campo de texto não está no documento, devolva string vazia: \
o documento será marcado para revisão humana.
"""


class ExtratorClaude:
    def __init__(self, modelo: str = MODELO_PADRAO, client=None, tentativas: int = 2):
        self.modelo = modelo
        self.client = client or anthropic.Anthropic()
        self.tentativas = tentativas

    def __call__(self, pdf: Path, tipo: str) -> BaseModel:
        schema = SCHEMAS[tipo]
        b64 = base64.standard_b64encode(Path(pdf).read_bytes()).decode("ascii")
        conteudo = [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
            {"type": "text", "text": PROMPT.format(nome=NOMES[tipo])},
        ]

        ultimo_erro: ValidationError | None = None
        for _ in range(self.tentativas):
            try:
                resp = self.client.messages.parse(
                    model=self.modelo,
                    max_tokens=16000,
                    messages=[{"role": "user", "content": conteudo}],
                    output_format=schema,
                )
            except ValidationError as e:
                # Uma segunda chance, mostrando o que falhou.
                ultimo_erro = e
                conteudo = conteudo[:2] + [{
                    "type": "text",
                    "text": f"A resposta anterior não passou na validação:\n{e}\nCorrija e responda de novo.",
                }]
                continue
            except anthropic.APIError as e:
                raise ExtracaoErro(f"erro da API: {e}") from e

            if resp.stop_reason == "refusal":
                raise ExtracaoErro("a API recusou o pedido (stop_reason=refusal)")
            if resp.stop_reason == "max_tokens":
                raise ExtracaoErro("resposta cortada por max_tokens")
            if resp.parsed_output is None:
                raise ExtracaoErro("resposta sem saída estruturada")
            return resp.parsed_output

        raise ultimo_erro  # type: ignore[misc]
