class ExtracaoErro(Exception):
    """A extração não chegou a um JSON utilizável (API, recusa, corte ou validação)."""


class LimiteDeUso(Exception):
    """O limite da assinatura/API acabou. Para tudo: continuar só geraria falhas falsas no eval."""
