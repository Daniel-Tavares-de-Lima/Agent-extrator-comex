import argparse
import json
from pathlib import Path

from . import evaluate, synthetic
from .erros import LimiteDeUso
from .pipeline import processar

EXTRATORES = ["simulado", "claude-code", "claude-api"]


def _criar_extrator(nome: str, dados: Path, taxa_erro: float, modo: str = "auto",
                    modelo: str = "haiku", esforco: str = "low"):
    if nome == "claude-api":
        from .extractor import ExtratorClaude
        return ExtratorClaude(), "Eval com Claude (API)"
    if nome == "claude-code":
        from .extractor_cli import ExtratorClaudeCode
        return (ExtratorClaudeCode(modo=modo, modelo=modelo, esforco=esforco),
                f"Eval com Claude via Claude Code (modelo {modelo}, esforço {esforco}, modo {modo})")
    from .simulado import ExtratorSimulado
    return ExtratorSimulado(dados, taxa_erro), f"Eval SIMULADO (taxa de erro {taxa_erro:.0%}). Não mede o Claude."


def main() -> None:
    ap = argparse.ArgumentParser(prog="extrator")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gerar", help="gera documentos sintéticos e gabarito")
    g.add_argument("--n", type=int, default=40)
    g.add_argument("--defeitos", type=int, default=10, help="quantos dos conjuntos saem com defeito injetado")
    g.add_argument("--saida", type=Path, default=Path("data/sintetico"))
    g.add_argument("--seed", type=int, default=42)

    s = sub.add_parser("gerar-sujo", help="gera PDFs com layout real e escaneados (ruído, rotação, carimbo)")
    s.add_argument("--n", type=int, default=6, help="conjuntos por variante (tabela, scan_leve, scan_pesado)")
    s.add_argument("--saida", type=Path, default=Path("data/sujo"))
    s.add_argument("--seed", type=int, default=7)

    a = sub.add_parser("avaliar", help="mede acerto por campo contra o gabarito")
    a.add_argument("--extrator", choices=EXTRATORES, default="simulado")
    a.add_argument("--dados", type=Path, default=Path("data/sintetico"))
    a.add_argument("--limite", type=int, default=None, help="avalia só N conjuntos espaçados (gasta menos)")
    a.add_argument("--modo", choices=["auto", "texto", "pdf"], default="auto", help="só para claude-code")
    a.add_argument("--modelo", default="haiku", help="só para claude-code: haiku, sonnet, opus ou nome completo")
    a.add_argument("--esforco", default="low", choices=["low", "medium", "high", "xhigh", "max"],
                   help="só para claude-code")
    a.add_argument("--taxa-erro", type=float, default=0.03, help="só para o simulado")
    a.add_argument("--saida", type=Path, default=Path("results"))

    p = sub.add_parser("processar", help="extrai e valida um conjunto de PDFs")
    p.add_argument("--extrator", choices=["claude-code", "claude-api"], default="claude-code")
    p.add_argument("--modo", choices=["auto", "texto", "pdf"], default="auto", help="só para claude-code")
    p.add_argument("--modelo", default="haiku", help="só para claude-code")
    p.add_argument("--esforco", default="low", choices=["low", "medium", "high", "xhigh", "max"],
                   help="só para claude-code")
    p.add_argument("--invoice", type=Path, required=True)
    p.add_argument("--packing-list", type=Path, required=True)
    p.add_argument("--bl", type=Path, required=True)

    args = ap.parse_args()

    if args.cmd == "gerar":
        ids = synthetic.gerar(args.n, args.defeitos, args.saida, args.seed)
        print(f"{len(ids)} conjuntos em {args.saida} ({args.defeitos} com defeito injetado)")

    elif args.cmd == "gerar-sujo":
        from . import sujo
        ids = sujo.gerar_sujo(args.n, args.saida, args.seed)
        print(f"{len(ids)} conjuntos em {args.saida} ({', '.join(sujo.VARIANTES)}; "
              "1 com defeito injetado por variante)")

    elif args.cmd == "avaliar":
        extrair, titulo = _criar_extrator(args.extrator, args.dados, args.taxa_erro, args.modo,
                                          args.modelo, args.esforco)
        r = evaluate.avaliar(args.dados, extrair, args.limite)
        args.saida.mkdir(parents=True, exist_ok=True)
        (args.saida / f"relatorio_{args.extrator}.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        md = evaluate.formatar_markdown(r, titulo)
        (args.saida / f"relatorio_{args.extrator}.md").write_text(md, encoding="utf-8")
        print(md)
        if hasattr(extrair, "custo_lista_usd"):
            t = extrair.resumo_tokens()
            print(f"{t['chamadas']} chamadas. Tokens por chamada: média {t['media']:,.0f}, mediana {t['mediana']:,.0f}, "
                  f"mínimo {t['minimo']:,}, máximo {t['maximo']:,}, total {t['total']:,}.")
            print(f"Equivale a US$ {extrair.custo_lista_usd:.2f} a preço de lista "
                  "(na assinatura não é cobrado, mas conta no limite de uso).")

    elif args.cmd == "processar":
        extrair, _ = _criar_extrator(args.extrator, Path("."), 0.0, args.modo, args.modelo, args.esforco)
        pdfs = {"invoice": args.invoice, "packing_list": args.packing_list, "bl": args.bl}
        print(json.dumps(processar(pdfs, extrair), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except LimiteDeUso as e:
        raise SystemExit(f"O limite de uso acabou. Espere renovar e rode de novo.\nMensagem: {e}")
    except TypeError as e:
        # O SDK levanta TypeError quando não acha credencial. Falha logo, com mensagem clara.
        if "authentication method" not in str(e):
            raise
        raise SystemExit(
            "Sem credencial da Anthropic neste terminal (extrator claude-api).\n"
            "Sem chave de API, use --extrator claude-code, que usa o login da sua assinatura."
        )
