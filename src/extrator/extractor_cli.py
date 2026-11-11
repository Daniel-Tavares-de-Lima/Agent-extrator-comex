"""Extrator que usa o Claude Code em modo `claude -p`, com o login da assinatura (sem chave de API).

Dois modos:
- texto: o texto do PDF é extraído aqui (pypdf) e vai no prompt. Sem ferramentas, cerca de 4 mil tokens por chamada.
- pdf:   o Claude lê o PDF com a ferramenta Read (serve para PDF escaneado). Cerca de 11 mil tokens por chamada.
- auto (padrão): usa texto e cai para pdf quando o PDF não tem texto.

As opções de linha de comando tiram as ferramentas e os conectores que o Claude Code carregaria
por padrão (sem elas, uma chamada passa de 100 mil tokens).
"""
import json
import shutil
import statistics
import subprocess
from pathlib import Path

from pydantic import BaseModel, ValidationError
from pypdf import PdfReader

from .erros import ExtracaoErro, LimiteDeUso
from .extractor import NOMES, PROMPT
from .schemas import SCHEMAS

SISTEMA = "Você extrai dados de documentos de comércio exterior. Responda só com o JSON pedido."
MIN_CARACTERES_TEXTO = 50  # abaixo disso, trata o PDF como escaneado


def _texto_pdf(pdf: Path) -> str:
    try:
        return "\n".join(p.extract_text() or "" for p in PdfReader(str(pdf)).pages)
    except Exception:  # PDF corrompido ou fora do padrão: o modo pdf tenta de outro jeito
        return ""


class ExtratorClaudeCode:
    def __init__(self, modelo: str | None = "haiku", esforco: str | None = "low", timeout: int = 300,
                 tentativas: int = 2, modo: str = "auto", executavel: str | None = None):
        if modo not in ("auto", "texto", "pdf"):
            raise ValueError(f"modo inválido: {modo}")
        self.executavel = executavel or shutil.which("claude")
        if not self.executavel:
            raise RuntimeError("Claude Code (comando `claude`) não encontrado no PATH.")
        self.modelo = modelo  # alias ("haiku", "sonnet", "opus") ou nome completo; None usa o padrão do Claude Code
        self.esforco = esforco  # low | medium | high | xhigh | max; None usa o padrão
        self.timeout = timeout
        self.tentativas = tentativas
        self.modo = modo
        self.chamadas = 0
        self.custo_lista_usd = 0.0  # preço de lista equivalente; na assinatura não é cobrado, mas conta no limite
        self.tokens_por_chamada: list[int] = []

    def resumo_tokens(self) -> dict:
        t = self.tokens_por_chamada
        if not t:
            return {}
        return {"chamadas": len(t), "media": statistics.mean(t), "mediana": statistics.median(t),
                "minimo": min(t), "maximo": max(t), "total": sum(t)}

    def __call__(self, pdf: Path, tipo: str) -> BaseModel:
        schema = SCHEMAS[tipo]
        pdf = Path(pdf).resolve()
        texto = "" if self.modo == "pdf" else _texto_pdf(pdf)
        if len(texto.strip()) < MIN_CARACTERES_TEXTO:
            if self.modo == "texto":
                raise ExtracaoErro("PDF sem texto (escaneado?). Use o modo pdf ou auto.")
            texto = ""  # auto: cai para a leitura do PDF

        extra = ""
        ultimo_erro: ValidationError | None = None
        for _ in range(self.tentativas):
            saida = self._executar(pdf, tipo, texto, extra)
            try:
                return schema.model_validate(saida)
            except ValidationError as e:
                ultimo_erro = e
                extra = f"\nA resposta anterior não passou na validação:\n{e}\nCorrija e responda de novo."
        raise ultimo_erro  # type: ignore[misc]

    def _executar(self, pdf: Path, tipo: str, texto: str, extra: str) -> dict:
        base = PROMPT.format(nome=NOMES[tipo])
        cmd = [self.executavel, "-p"]
        if texto:
            entrada = f"{base}{extra}\n\nTEXTO DO DOCUMENTO:\n{texto}"
            ferramentas = ["--tools", ""]
        else:
            cmd.append(f"Leia o arquivo PDF {pdf} com a ferramenta Read.\n\n{base}{extra}")
            entrada = None
            ferramentas = ["--tools", "Read", "--allowedTools", "Read", "--add-dir", str(pdf.parent)]
        cmd += [
            "--output-format", "json",
            "--json-schema", json.dumps(SCHEMAS[tipo].model_json_schema()),
            *ferramentas,
            "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence",
            "--system-prompt", SISTEMA,
        ]
        if self.modelo:
            cmd += ["--model", self.modelo]
        if self.esforco:
            cmd += ["--effort", self.esforco]

        try:
            r = subprocess.run(cmd, input=entrada, capture_output=True, text=True, encoding="utf-8",
                               timeout=self.timeout)
        except subprocess.TimeoutExpired as e:
            raise ExtracaoErro(f"claude demorou mais de {self.timeout}s") from e
        try:
            d = json.loads(r.stdout)
        except json.JSONDecodeError as e:
            raise ExtracaoErro(f"saída inesperada do claude (código {r.returncode}): {(r.stderr or r.stdout)[:200]}") from e

        self.chamadas += 1
        self.custo_lista_usd += d.get("total_cost_usd") or 0
        u = d.get("usage") or {}
        self.tokens_por_chamada.append(sum(
            u.get(k) or 0 for k in
            ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
        ))
        if d.get("is_error"):
            msg = str(d.get("result") or "")
            if d.get("api_error_status") == 429 or "limit" in msg.lower():
                raise LimiteDeUso(msg)
            raise ExtracaoErro(msg or "erro do claude")

        saida = d.get("structured_output")
        if saida is None:
            try:
                saida = json.loads(d.get("result") or "")
            except json.JSONDecodeError as e:
                raise ExtracaoErro("resposta sem JSON") from e
        return saida
